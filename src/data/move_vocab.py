"""Vocabulaire des coups : la correspondance coup UCI <-> index entier.

Pourquoi ce fichier existe
--------------------------
Notre reseau de neurones est un classifieur : il recoit une position et doit
sortir un score pour *chaque coup possible*. Il faut donc une liste figee et
ordonnee de tous les coups imaginables aux echecs, pour que l'index 42 designe
toujours le meme coup, a l'entrainement comme a l'inference.

On enumere geometriquement (sans regarder une position particuliere) :
  - les deplacements "de type dame"    : lignes, colonnes, diagonales -> 1456
  - les deplacements "de type cavalier": les 8 sauts en L              ->  336
  - les promotions de pion             : 4 pieces x 22 trajets x 2 cotes -> 176
                                                                  TOTAL = 1968

Certains de ces coups ne sont jamais legaux (ex : a1a8 pour un fou), ce n'est
pas grave : le masquage des coups illegaux s'en occupe a l'inference.
"""

from __future__ import annotations

import chess

# Les 8 directions d'une dame, en (delta_colonne, delta_ligne).
QUEEN_DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]

# Les 8 sauts d'un cavalier.
KNIGHT_DELTAS = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]

# Pieces de promotion, dans un ordre fixe.
PROMOTION_PIECES = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]


def _build_uci_list() -> list[str]:
    """Genere la liste ordonnee de tous les coups UCI possibles."""
    ucis: list[str] = []
    seen: set[str] = set()

    def add(from_sq: int, to_sq: int, promotion: int | None = None) -> None:
        uci = chess.Move(from_sq, to_sq, promotion=promotion).uci()
        if uci not in seen:
            seen.add(uci)
            ucis.append(uci)

    # 1) Deplacements type dame (couvre aussi tour, fou, roi, et les pions
    #    qui avancent ou capturent sans promotion).
    for from_sq in chess.SQUARES:
        f_file, f_rank = chess.square_file(from_sq), chess.square_rank(from_sq)
        for d_file, d_rank in QUEEN_DIRECTIONS:
            for distance in range(1, 8):
                t_file = f_file + d_file * distance
                t_rank = f_rank + d_rank * distance
                if 0 <= t_file <= 7 and 0 <= t_rank <= 7:
                    add(from_sq, chess.square(t_file, t_rank))

    # 2) Deplacements type cavalier.
    for from_sq in chess.SQUARES:
        f_file, f_rank = chess.square_file(from_sq), chess.square_rank(from_sq)
        for d_file, d_rank in KNIGHT_DELTAS:
            t_file, t_rank = f_file + d_file, f_rank + d_rank
            if 0 <= t_file <= 7 and 0 <= t_rank <= 7:
                add(from_sq, chess.square(t_file, t_rank))

    # 3) Promotions. Un pion blanc va de la 7e a la 8e rangee (tout droit ou en
    #    capturant en diagonale), un pion noir de la 2e a la 1ere.
    for from_rank, to_rank in ((6, 7), (1, 0)):
        for f_file in range(8):
            for d_file in (-1, 0, 1):
                t_file = f_file + d_file
                if not 0 <= t_file <= 7:
                    continue
                from_sq = chess.square(f_file, from_rank)
                to_sq = chess.square(t_file, to_rank)
                for piece in PROMOTION_PIECES:
                    add(from_sq, to_sq, promotion=piece)

    return ucis


class MoveVocab:
    """Table de correspondance bidirectionnelle coup UCI <-> index.

    Exemple
    -------
    >>> vocab = MoveVocab()
    >>> idx = vocab.index_of(chess.Move.from_uci("e2e4"))
    >>> vocab.move_at(idx).uci()
    'e2e4'
    """

    def __init__(self) -> None:
        self._ucis: list[str] = _build_uci_list()
        self._index: dict[str, int] = {uci: i for i, uci in enumerate(self._ucis)}

    def __len__(self) -> int:
        return len(self._ucis)

    def index_of(self, move: chess.Move) -> int:
        """Index d'un coup. Leve KeyError si le coup n'est pas au vocabulaire."""
        return self._index[move.uci()]

    def move_at(self, index: int) -> chess.Move:
        """Coup correspondant a un index."""
        return chess.Move.from_uci(self._ucis[index])

    def contains(self, move: chess.Move) -> bool:
        return move.uci() in self._index


# Instance partagee : le vocabulaire est identique partout dans le projet.
VOCAB = MoveVocab()
VOCAB_SIZE = len(VOCAB)


if __name__ == "__main__":
    print(f"Taille du vocabulaire : {VOCAB_SIZE} coups")
    for uci in ("e2e4", "g1f3", "e7e8q", "a1h8", "b7a8n"):
        print(f"  {uci:>6} -> index {VOCAB.index_of(chess.Move.from_uci(uci))}")
