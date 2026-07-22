"""Encodage d'une position d'echecs en tenseur d'entiers pour le Transformer.

Format de sortie : 68 entiers.
  - indices  0..63 : contenu des 64 cases (a1 -> h8), valeurs 0..12
                     0 = vide, 1..6 = P N B R Q K du joueur au trait,
                     7..12 = P N B R Q K de l'adversaire
  - indice   64    : trait (toujours 0 apres normalisation, garde pour clarte)
  - indice   65    : droits de roque du joueur au trait   (0..3)
  - indice   66    : droits de roque de l'adversaire      (0..3)
  - indice   67    : case de prise en passant (0 = aucune, sinon 1 + numero de case)

Normalisation de couleur
------------------------
Le modele apprend TOUJOURS du point de vue du joueur au trait, comme s'il etait
les blancs. Quand c'est aux noirs de jouer, on retourne l'echiquier
(`board.mirror()` : symetrie verticale + inversion des couleurs) et on retourne
aussi le coup predit avant de le jouer.

Consequence : le modele n'a qu'une seule "vue" a apprendre au lieu de deux,
donc il apprend environ deux fois plus vite a quantite de donnees egale.
"""

from __future__ import annotations

import chess
import numpy as np

SEQ_LEN = 68
IDX_TURN = 64
IDX_CASTLING_US = 65
IDX_CASTLING_THEM = 66
IDX_EN_PASSANT = 67

# Nombre de valeurs distinctes qu'un token peut prendre (0..64 pour la prise
# en passant, qui est le token de plus grande amplitude). Sert a dimensionner
# la table d'embedding du modele.
VOCAB_TOKENS = 65

_PIECE_ORDER = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]
_PIECE_TO_ID = {piece: i + 1 for i, piece in enumerate(_PIECE_ORDER)}


def normalize(board: chess.Board) -> tuple[chess.Board, bool]:
    """Ramene la position au point de vue du joueur au trait.

    Returns
    -------
    (board_normalise, flipped)
        `flipped` vaut True si l'echiquier a ete retourne : il faudra alors
        appliquer `flip_move` au coup predit par le modele.
    """
    if board.turn == chess.WHITE:
        return board, False
    return board.mirror(), True


def flip_move(move: chess.Move) -> chess.Move:
    """Applique a un coup la meme symetrie verticale que `board.mirror()`."""
    return chess.Move(
        chess.square_mirror(move.from_square),
        chess.square_mirror(move.to_square),
        promotion=move.promotion,
        drop=move.drop,
    )


def _castling_bits(board: chess.Board, color: chess.Color) -> int:
    """2 bits : roque cote roi (1) + roque cote dame (2)."""
    return int(board.has_kingside_castling_rights(color)) + 2 * int(
        board.has_queenside_castling_rights(color)
    )


def encode_board(board: chess.Board) -> np.ndarray:
    """Encode une position deja normalisee en vecteur de 68 entiers.

    Attention : cette fonction suppose que c'est aux blancs de jouer. Utilisez
    `encode_position` qui gere la normalisation pour vous.
    """
    tokens = np.zeros(SEQ_LEN, dtype=np.int64)

    for square, piece in board.piece_map().items():
        base = _PIECE_TO_ID[piece.piece_type]
        tokens[square] = base if piece.color == chess.WHITE else base + 6

    tokens[IDX_TURN] = 0  # apres normalisation : toujours "a nous de jouer"
    tokens[IDX_CASTLING_US] = _castling_bits(board, chess.WHITE)
    tokens[IDX_CASTLING_THEM] = _castling_bits(board, chess.BLACK)
    tokens[IDX_EN_PASSANT] = 0 if board.ep_square is None else board.ep_square + 1

    return tokens


def encode_position(board: chess.Board) -> tuple[np.ndarray, bool]:
    """Normalise puis encode une position quelconque.

    Returns
    -------
    (tokens, flipped)
        `tokens` : vecteur numpy de 68 entiers, pret pour le modele.
        `flipped`: True s'il faudra retourner le coup predit.
    """
    normalized, flipped = normalize(board)
    return encode_board(normalized), flipped


def decode_board(tokens: np.ndarray) -> chess.Board:
    """Reconstruit une position a partir de son encodage.

    Sert uniquement aux tests : si `decode(encode(b))` ne redonne pas `b`, c'est
    que l'encodage perd de l'information — le bug le plus insidieux du projet.
    """
    board = chess.Board(None)  # echiquier vide
    board.turn = chess.WHITE

    for square in chess.SQUARES:
        value = int(tokens[square])
        if value == 0:
            continue
        color = chess.WHITE if value <= 6 else chess.BLACK
        piece_type = _PIECE_ORDER[(value - 1) % 6]
        board.set_piece_at(square, chess.Piece(piece_type, color))

    rights = 0
    us, them = int(tokens[IDX_CASTLING_US]), int(tokens[IDX_CASTLING_THEM])
    if us & 1:
        rights |= chess.BB_H1
    if us & 2:
        rights |= chess.BB_A1
    if them & 1:
        rights |= chess.BB_H8
    if them & 2:
        rights |= chess.BB_A8
    board.castling_rights = rights

    ep = int(tokens[IDX_EN_PASSANT])
    board.ep_square = None if ep == 0 else ep - 1

    return board
