"""Tests de l'encodage — les plus importants du projet.

Pourquoi ces tests sont critiques
---------------------------------
Un bug dans l'encodage ne fait PAS planter le programme. Le modele s'entraine
quand meme, la loss descend quand meme, et on ne s'apercoit de rien... sauf que
le bot joue mal sans qu'on comprenne pourquoi. C'est le pire scenario du projet.

La parade : verifier que l'encodage est reversible. Si on peut reconstruire la
position exacte a partir des 68 tokens, c'est qu'aucune information n'a ete
perdue.

Lancer les tests :  python -m pytest tests/ -v
"""

from __future__ import annotations

import random

import chess
import pytest

from src.data.encoding import (
    SEQ_LEN,
    decode_board,
    encode_board,
    encode_position,
    flip_move,
    normalize,
)
from src.data.move_vocab import VOCAB, VOCAB_SIZE


def random_positions(count: int, seed: int = 0, max_plies: int = 60):
    """Genere des positions variees en jouant des parties aleatoires."""
    rng = random.Random(seed)
    positions = []
    while len(positions) < count:
        board = chess.Board()
        for _ in range(rng.randint(0, max_plies)):
            if board.is_game_over():
                break
            board.push(rng.choice(list(board.legal_moves)))
        positions.append(board.copy())
    return positions


def test_encoding_has_expected_shape():
    tokens = encode_board(chess.Board())
    assert tokens.shape == (SEQ_LEN,)
    assert tokens.min() >= 0


def test_encoding_is_reversible():
    """decode(encode(position)) doit redonner la position exacte."""
    for board in random_positions(500, seed=1):
        normalized, _ = normalize(board)
        rebuilt = decode_board(encode_board(normalized))

        assert rebuilt.piece_map() == normalized.piece_map()
        assert rebuilt.castling_rights == normalized.castling_rights
        assert rebuilt.ep_square == normalized.ep_square


def test_normalization_makes_black_look_like_white():
    """Apres normalisation, c'est toujours aux blancs de jouer."""
    for board in random_positions(200, seed=2):
        normalized, flipped = normalize(board)
        assert normalized.turn == chess.WHITE
        assert flipped == (board.turn == chess.BLACK)


def test_flip_move_is_its_own_inverse():
    """Retourner deux fois un coup redonne le coup d'origine."""
    for board in random_positions(200, seed=3):
        for move in board.legal_moves:
            assert flip_move(flip_move(move)) == move


def test_flipped_moves_stay_legal():
    """Un coup legal, retourne avec l'echiquier, reste legal.

    C'est LE test qui valide toute la mecanique de normalisation : si on peut
    retourner la position, choisir un coup dans le repere retourne, puis le
    retourner de nouveau et le jouer, alors la normalisation est correcte.
    """
    for board in random_positions(200, seed=4):
        if board.is_game_over():
            continue
        normalized, flipped = normalize(board)
        for move in board.legal_moves:
            mirrored = flip_move(move) if flipped else move
            assert mirrored in normalized.legal_moves


def test_encode_position_reports_flip_correctly():
    board = chess.Board()
    _, flipped = encode_position(board)
    assert flipped is False

    board.push_san("e4")
    _, flipped = encode_position(board)
    assert flipped is True


# --- Vocabulaire des coups ---------------------------------------------------


def test_vocab_size_is_1968():
    assert VOCAB_SIZE == 1968


def test_vocab_roundtrip():
    for uci in ("e2e4", "g1f3", "a1a8", "h1a8", "e7e8q", "b2a1n"):
        move = chess.Move.from_uci(uci)
        assert VOCAB.move_at(VOCAB.index_of(move)) == move


def test_vocab_covers_every_legal_move():
    """Aucun coup legal ne doit manquer au vocabulaire.

    Si ce test echoue, le modele serait incapable de jouer certains coups :
    catastrophe silencieuse garantie.
    """
    for board in random_positions(300, seed=5):
        for move in board.legal_moves:
            assert VOCAB.contains(move), f"Coup absent du vocabulaire : {move.uci()}"


@pytest.mark.parametrize("fen", [
    chess.STARTING_FEN,
    "8/8/8/8/8/8/8/K6k w - - 0 1",                                   # finale nue
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1",      # trait aux noirs
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",                          # tous les roques
    "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",  # prise en passant
])
def test_specific_positions_roundtrip(fen):
    board = chess.Board(fen)
    normalized, _ = normalize(board)
    rebuilt = decode_board(encode_board(normalized))
    assert rebuilt.piece_map() == normalized.piece_map()
    assert rebuilt.castling_rights == normalized.castling_rights
    assert rebuilt.ep_square == normalized.ep_square
