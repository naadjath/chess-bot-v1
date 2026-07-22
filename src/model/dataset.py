"""Chargement du dataset pour PyTorch.

Deux strategies, selon la taille des donnees :

  InMemoryDataset  — charge tout en RAM. Simple et rapide. 1 million de
                     positions occupent environ 70 Mo (68 octets par position),
                     ce qui passe partout : c'est le choix par defaut.

  ShardDataset     — lit les tranches une par une. A utiliser au-dela de
                     ~20 millions de positions, quand la RAM devient limitante.

Le module `psutil` permet d'afficher la consommation reelle et de justifier ce
choix dans le rapport plutot que de le supposer.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import psutil
import torch
from torch.utils.data import Dataset

from src.data.pgn_parser import load_split


class InMemoryDataset(Dataset):
    """Toutes les positions d'un decoupage, chargees en memoire.

    Les tokens sont conserves en `uint8` (1 octet par token) et convertis en
    entiers longs uniquement au moment de former le lot. Garder le dataset en
    uint8 divise l'empreinte memoire par huit par rapport a du int64.
    """

    def __init__(self, dataset_dir: str | Path, split: str = "train") -> None:
        tokens, labels = load_split(dataset_dir, split)
        self.tokens = torch.from_numpy(np.ascontiguousarray(tokens))
        self.labels = torch.from_numpy(labels.astype(np.int64))
        self.split = split

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.tokens[index].long(), self.labels[index]

    @property
    def memory_mb(self) -> float:
        return (self.tokens.nbytes + self.labels.nbytes) / 1e6

    def __repr__(self) -> str:
        return f"<InMemoryDataset {self.split}: {len(self):,} positions, {self.memory_mb:.0f} Mo>".replace(",", " ")


def read_metadata(dataset_dir: str | Path) -> dict:
    path = Path(dataset_dir) / "metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def system_memory_report() -> str:
    """Etat de la RAM, a journaliser avant un gros entrainement."""
    memory = psutil.virtual_memory()
    process = psutil.Process().memory_info().rss / 1e9
    return (
        f"RAM systeme : {memory.available / 1e9:.1f} Go libres sur "
        f"{memory.total / 1e9:.1f} Go — processus : {process:.2f} Go"
    )
