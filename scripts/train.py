"""Lance l'entrainement du ChessTransformer.

Exemples
--------
    # Repetition rapide sur les donnees de demo, sur CPU
    python -m scripts.train --epochs 2 --batch-size 64 --d-model 64 --layers 2

    # Entrainement reel (a lancer sur un GPU : Colab, Kaggle)
    python -m scripts.train --epochs 4 --batch-size 512

Sur GPU gratuit, comptez 4 a 8 heures pour 4 epoques sur 1 million de positions.
Les poids sont sauvegardes a chaque epoque : une session interrompue ne fait
perdre qu'une epoque, jamais tout l'entrainement.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.model.train import TrainConfig, train  # noqa: E402
from src.model.transformer import ModelConfig  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrainement du ChessTransformer.")

    data = parser.add_argument_group("donnees")
    data.add_argument("--dataset", default="data/processed")
    data.add_argument("--output", default="checkpoints")

    optim = parser.add_argument_group("optimisation")
    optim.add_argument("--epochs", type=int, default=4)
    optim.add_argument("--batch-size", type=int, default=512)
    optim.add_argument("--lr", type=float, default=3e-4)
    optim.add_argument("--weight-decay", type=float, default=0.01)
    optim.add_argument("--warmup", type=int, default=1000)
    optim.add_argument("--eval-every", type=int, default=0)
    optim.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    optim.add_argument("--seed", type=int, default=0)

    arch = parser.add_argument_group("architecture")
    arch.add_argument("--d-model", type=int, default=256)
    arch.add_argument("--layers", type=int, default=8)
    arch.add_argument("--heads", type=int, default=8)
    arch.add_argument("--d-ff", type=int, default=None, help="defaut : 4 x d_model")
    arch.add_argument("--dropout", type=float, default=0.1)

    args = parser.parse_args()

    model_config = ModelConfig(
        d_model=args.d_model,
        n_layers=args.layers,
        n_heads=args.heads,
        d_ff=args.d_ff or 4 * args.d_model,
        dropout=args.dropout,
    )
    train_config = TrainConfig(
        dataset_dir=args.dataset,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        warmup_steps=args.warmup,
        eval_every=args.eval_every,
        device=args.device,
        seed=args.seed,
    )

    train(train_config, model_config)


if __name__ == "__main__":
    main()
