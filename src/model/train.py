"""Entrainement du ChessTransformer.

La tache
--------
Classification multi-classes : entree = une position (68 tokens), sortie = un
coup parmi 1968. La fonction de perte est l'entropie croisee, exactement comme
pour classer des images.

Les metriques suivies
---------------------
  loss     : ce que l'optimiseur minimise.
  top-1    : le modele retrouve-t-il exactement le coup joue par l'humain ?
  top-5    : le bon coup est-il dans ses 5 propositions ?

ATTENTION A L'INTERPRETATION. Une top-1 de 40 % n'est pas un mauvais score. Dans
beaucoup de positions, plusieurs coups sont equivalents : le modele en propose
un autre que l'humain sans avoir tort. La top-1 mesure l'IMITATION, pas la
qualite de jeu. La seule mesure qui compte vraiment reste l'Elo constate en
parties reelles — c'est un point a expliquer clairement dans le rapport.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.model.dataset import InMemoryDataset, read_metadata, system_memory_report
from src.model.transformer import ChessTransformer, ModelConfig


@dataclass
class TrainConfig:
    """Hyperparametres d'entrainement."""

    dataset_dir: str = "data/processed"
    output_dir: str = "checkpoints"

    epochs: int = 4
    batch_size: int = 512
    learning_rate: float = 3e-4
    weight_decay: float = 0.01
    warmup_steps: int = 1000
    grad_clip: float = 1.0

    #: Sur CPU on reduit tout : c'est une repetition, pas un vrai entrainement.
    device: str = "auto"
    num_workers: int = 0
    seed: int = 0

    #: Evaluation sur la validation tous les N pas (0 = uniquement en fin d'epoque).
    eval_every: int = 0

    def resolve_device(self) -> torch.device:
        if self.device != "auto":
            return torch.device(self.device)
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@dataclass
class History:
    """Journal de l'entrainement, pour tracer les courbes du rapport."""

    steps: list[int] = field(default_factory=list)
    train_loss: list[float] = field(default_factory=list)
    val_loss: list[float] = field(default_factory=list)
    val_top1: list[float] = field(default_factory=list)
    val_top5: list[float] = field(default_factory=list)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def build_scheduler(optimizer: torch.optim.Optimizer, warmup: int, total: int):
    """Montee lineaire puis decroissance en cosinus.

    Pourquoi un warmup : au tout debut, les poids sont aleatoires et les
    gradients enormes. Demarrer a pleine vitesse d'apprentissage deregle le
    modele des les premiers pas. On monte donc progressivement.

    Pourquoi le cosinus ensuite : reduire doucement le pas en fin
    d'entrainement permet d'affiner la solution au lieu de tourner autour.
    """

    def lr_lambda(step: int) -> float:
        if step < warmup:
            return (step + 1) / max(1, warmup)
        progress = (step - warmup) / max(1, total - warmup)
        return 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device, max_batches: int = 0) -> dict:
    """Calcule loss, top-1 et top-5 sur un jeu de donnees."""
    model.eval()
    criterion = nn.CrossEntropyLoss()

    total_loss = correct1 = correct5 = seen = 0

    for index, (tokens, labels) in enumerate(loader):
        if max_batches and index >= max_batches:
            break
        tokens, labels = tokens.to(device), labels.to(device)
        logits = model(tokens)

        total_loss += criterion(logits, labels).item() * len(labels)
        top5 = logits.topk(5, dim=-1).indices
        correct1 += (top5[:, 0] == labels).sum().item()
        correct5 += (top5 == labels.unsqueeze(1)).any(dim=1).sum().item()
        seen += len(labels)

    model.train()
    if seen == 0:
        return {"loss": float("nan"), "top1": 0.0, "top5": 0.0}
    return {"loss": total_loss / seen, "top1": correct1 / seen, "top5": correct5 / seen}


def train(train_config: TrainConfig, model_config: ModelConfig | None = None) -> tuple[ChessTransformer, History]:
    torch.manual_seed(train_config.seed)
    device = train_config.resolve_device()

    train_set = InMemoryDataset(train_config.dataset_dir, "train")
    val_set = InMemoryDataset(train_config.dataset_dir, "val")

    print(system_memory_report())
    print(train_set)
    print(val_set)

    metadata = read_metadata(train_config.dataset_dir)
    if metadata:
        print(f"Dataset issu de {metadata.get('games_kept', '?')} parties")

    train_loader = DataLoader(
        train_set,
        batch_size=train_config.batch_size,
        shuffle=True,
        num_workers=train_config.num_workers,
        drop_last=True,
    )
    val_loader = DataLoader(val_set, batch_size=train_config.batch_size, shuffle=False)

    model = ChessTransformer(model_config).to(device)
    print(f"Modele : {model.num_parameters():,} parametres sur {device}".replace(",", " "))

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=train_config.learning_rate, weight_decay=train_config.weight_decay
    )
    total_steps = max(1, len(train_loader) * train_config.epochs)
    scheduler = build_scheduler(optimizer, min(train_config.warmup_steps, total_steps // 10), total_steps)
    criterion = nn.CrossEntropyLoss()

    # La precision mixte n'a d'interet que sur GPU : elle exploite les unites
    # de calcul demi-precision, absentes des CPU classiques.
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    history = History()
    output_dir = Path(train_config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    best_top1 = -1.0
    step = 0
    started = time.time()

    for epoch in range(1, train_config.epochs + 1):
        progress = tqdm(train_loader, desc=f"Epoque {epoch}/{train_config.epochs}", unit="lot")
        running_loss = 0.0

        for tokens, labels in progress:
            tokens, labels = tokens.to(device), labels.to(device)

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=use_amp):
                loss = criterion(model(tokens), labels)

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            # Sans ce clipping, un lot atypique peut produire un gradient enorme
            # qui detruit d'un coup des heures d'entrainement.
            nn.utils.clip_grad_norm_(model.parameters(), train_config.grad_clip)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            step += 1
            running_loss += loss.item()
            progress.set_postfix(loss=f"{running_loss / (progress.n + 1):.3f}",
                                 lr=f"{scheduler.get_last_lr()[0]:.1e}")

            if train_config.eval_every and step % train_config.eval_every == 0:
                metrics = evaluate(model, val_loader, device, max_batches=20)
                history.steps.append(step)
                history.train_loss.append(running_loss / (progress.n + 1))
                history.val_loss.append(metrics["loss"])
                history.val_top1.append(metrics["top1"])
                history.val_top5.append(metrics["top5"])

        metrics = evaluate(model, val_loader, device)
        history.steps.append(step)
        history.train_loss.append(running_loss / max(1, len(train_loader)))
        history.val_loss.append(metrics["loss"])
        history.val_top1.append(metrics["top1"])
        history.val_top5.append(metrics["top5"])

        print(
            f"  epoque {epoch} — val loss {metrics['loss']:.3f} · "
            f"top-1 {metrics['top1']:.1%} · top-5 {metrics['top5']:.1%}"
        )

        # On sauvegarde a chaque epoque : une session Colab peut etre coupee a
        # tout moment, et perdre l'entrainement entier serait dramatique.
        model.save(output_dir / "last.pt", extra={"epoch": epoch, "metrics": metrics})
        if metrics["top1"] > best_top1:
            best_top1 = metrics["top1"]
            model.save(output_dir / "best.pt", extra={"epoch": epoch, "metrics": metrics})

    history.save(output_dir / "history.json")
    print(f"\nTermine en {(time.time() - started) / 60:.1f} min — meilleure top-1 : {best_top1:.1%}")
    print(f"Poids enregistres dans {output_dir.resolve()}")
    return model, history
