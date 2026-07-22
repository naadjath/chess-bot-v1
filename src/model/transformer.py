"""Le modele : un Transformer encodeur qui choisit un coup d'echecs.

L'intuition
-----------
Un Transformer a ete concu pour traiter des SEQUENCES, et son mecanisme
d'attention permet a chaque element de la sequence de "regarder" tous les
autres. Or une position d'echecs, c'est 64 cases. On la traite donc comme une
sequence de 64 mots (plus 4 tokens de contexte : trait, roques, prise en
passant).

L'interet par rapport a un reseau convolutif : l'attention relie directement
deux cases eloignees. La case a1 peut "voir" h8 des la premiere couche, ce qui
correspond exactement a la facon dont une tour ou un fou agit sur l'echiquier.
Un CNN, lui, doit empiler des couches pour propager l'information d'un bout a
l'autre du plateau.

Le type de reseau
-----------------
C'est un encodeur seul (comme BERT), pas un decodeur (comme GPT) : on ne genere
pas une suite de mots, on classe une position parmi 1968 coups possibles. La
tache est donc, formellement, une CLASSIFICATION MULTI-CLASSES tout ce qu'il y
a de plus ordinaire — c'est le meme entrainement que "ranger une image parmi
1968 categories".
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import torch
import torch.nn as nn

from src.data.encoding import SEQ_LEN, VOCAB_TOKENS
from src.data.move_vocab import VOCAB_SIZE


@dataclass
class ModelConfig:
    """Hyperparametres de l'architecture.

    Les valeurs par defaut visent un modele d'environ 6,5 millions de
    parametres : assez expressif pour bien jouer, assez leger pour s'entrainer
    en quelques heures sur un GPU gratuit (Colab, Kaggle).
    """

    d_model: int = 256          # taille des vecteurs internes
    n_layers: int = 8           # nombre de couches d'attention empilees
    n_heads: int = 8            # "points de vue" d'attention en parallele
    d_ff: int = 1024            # taille du reseau feed-forward (4 x d_model)
    dropout: float = 0.1        # regularisation contre le surapprentissage
    seq_len: int = SEQ_LEN
    n_tokens: int = VOCAB_TOKENS
    n_moves: int = VOCAB_SIZE

    def to_dict(self) -> dict:
        return asdict(self)


class ChessTransformer(nn.Module):
    """Position d'echecs (68 tokens) -> score pour chacun des 1968 coups.

    Exemple
    -------
    >>> model = ChessTransformer()
    >>> tokens = torch.zeros(4, 68, dtype=torch.long)   # 4 positions vides
    >>> model(tokens).shape
    torch.Size([4, 1968])
    """

    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()
        cfg = self.config

        # Chaque token (contenu d'une case, droits de roque...) devient un
        # vecteur apprenable de dimension d_model.
        self.token_embedding = nn.Embedding(cfg.n_tokens, cfg.d_model)

        # L'attention est insensible a l'ordre : sans cet ajout, le modele ne
        # saurait pas QUELLE case il regarde. On apprend donc un vecteur par
        # position dans la sequence — c'est-a-dire, ici, par case de l'echiquier.
        self.position_embedding = nn.Parameter(torch.zeros(1, cfg.seq_len, cfg.d_model))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=cfg.d_model,
            nhead=cfg.n_heads,
            dim_feedforward=cfg.d_ff,
            dropout=cfg.dropout,
            activation="gelu",
            batch_first=True,
            # Pre-normalisation : la LayerNorm est placee AVANT l'attention.
            # L'entrainement est nettement plus stable sur les modeles profonds,
            # et on peut se passer d'un warmup agressif.
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=cfg.n_layers,
            # L'optimisation "nested tensor" de PyTorch ne sert qu'a ignorer le
            # remplissage des sequences de longueurs differentes. Nos positions
            # font TOUJOURS 68 tokens, il n'y a donc rien a ignorer : on la
            # desactive explicitement (elle est de toute facon incompatible avec
            # norm_first).
            enable_nested_tensor=False,
        )

        self.final_norm = nn.LayerNorm(cfg.d_model)
        self.head = nn.Linear(cfg.d_model, cfg.n_moves)

        self._init_weights()

    def _init_weights(self) -> None:
        nn.init.normal_(self.position_embedding, std=0.02)
        nn.init.normal_(self.token_embedding.weight, std=0.02)
        nn.init.zeros_(self.head.bias)
        nn.init.normal_(self.head.weight, std=0.02)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        tokens : (B, 68) entiers longs — B positions encodees.

        Returns
        -------
        (B, 1968) logits bruts. Ce ne sont PAS des probabilites : il faut
        d'abord masquer les coups illegaux, puis appliquer un softmax. Faire
        l'inverse redistribuerait de la probabilite sur des coups impossibles.
        """
        x = self.token_embedding(tokens) + self.position_embedding
        x = self.encoder(x)

        # Aggregation : on resume les 68 vecteurs en un seul. La moyenne donne
        # un poids egal a chaque case ; c'est simple, sans parametre, et cela
        # fonctionne bien ici car aucune case n'est a priori plus importante
        # qu'une autre. (Une alternative serait un token [CLS] dedie.)
        x = self.final_norm(x.mean(dim=1))
        return self.head(x)

    # -- Utilitaires -------------------------------------------------------

    def num_parameters(self, trainable_only: bool = True) -> int:
        params = self.parameters()
        if trainable_only:
            params = (p for p in params if p.requires_grad)
        return sum(p.numel() for p in params)

    def save(self, path: str | Path, extra: dict | None = None) -> None:
        """Enregistre les poids ET la configuration.

        Sauvegarder la config avec les poids evite le grand classique du "je ne
        sais plus avec quels hyperparametres ce fichier a ete produit".
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {"config": self.config.to_dict(), "state_dict": self.state_dict(), **(extra or {})},
            path,
        )

    @classmethod
    def load(cls, path: str | Path, map_location: str = "cpu") -> "ChessTransformer":
        checkpoint = torch.load(path, map_location=map_location, weights_only=False)
        model = cls(ModelConfig(**checkpoint["config"]))
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        return model


def describe(config: ModelConfig | None = None) -> str:
    """Petit resume a coller dans le rapport."""
    model = ChessTransformer(config)
    cfg = model.config
    return (
        f"ChessTransformer — {model.num_parameters():,} parametres\n".replace(",", " ")
        + f"  couches      : {cfg.n_layers}\n"
        + f"  d_model      : {cfg.d_model}\n"
        + f"  tetes        : {cfg.n_heads}\n"
        + f"  feed-forward : {cfg.d_ff}\n"
        + f"  sequence     : {cfg.seq_len} tokens\n"
        + f"  sorties      : {cfg.n_moves} coups"
    )


if __name__ == "__main__":
    print(describe())
