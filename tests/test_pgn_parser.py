"""Tests du pipeline de donnees.

Le test central est `test_every_label_is_legal_in_its_own_position`. Il repond a
la seule question qui compte : le coup enregistre comme "bonne reponse"
est-il vraiment jouable dans la position enregistree comme "question" ?

Si la normalisation de couleur etait fausse (echiquier retourne mais pas le
coup, ou l'inverse), ce test echouerait — alors que l'entrainement, lui,
fonctionnerait sans broncher et produirait un bot incomprehensiblement mauvais.
C'est notre garde-fou contre le bug le plus couteux du projet.
"""

from __future__ import annotations

import io
import random

import chess
import chess.pgn
import numpy as np
import pytest

from src.data.encoding import SEQ_LEN, decode_board
from src.data.move_vocab import VOCAB, VOCAB_SIZE
from src.data.pgn_parser import (
    Filters,
    ParseStats,
    accept_game,
    build_dataset,
    extract_samples,
    load_split,
)

NO_FILTER = Filters(min_elo=0, min_time_control=0, skip_opening_plies=0)


def make_pgn(n_games: int = 6, seed: int = 0, elo: int = 2200) -> str:
    """Fabrique un PGN en memoire a partir de parties aleatoires."""
    rng = random.Random(seed)
    games = []

    for index in range(n_games):
        board = chess.Board()
        for _ in range(rng.randint(20, 50)):
            if board.is_game_over():
                break
            board.push(rng.choice(list(board.legal_moves)))

        game = chess.pgn.Game.from_board(board)
        game.headers["WhiteElo"] = str(elo)
        game.headers["BlackElo"] = str(elo)
        game.headers["TimeControl"] = "600+0"
        game.headers["Round"] = str(index + 1)

        # Une partie interrompue avant la fin porte le resultat "*", que le
        # parser rejette a juste titre (on ne sait pas qui a gagne). Comme nos
        # parties de test s'arretent arbitrairement, on leur attribue un
        # resultat pour tester les autres filtres.
        result = board.result(claim_draw=True)
        game.headers["Result"] = result if result != "*" else "1-0"
        games.append(str(game))

    return "\n\n".join(games) + "\n\n"


def read_games(pgn_text: str) -> list[chess.pgn.Game]:
    handle = io.StringIO(pgn_text)
    games = []
    while (game := chess.pgn.read_game(handle)) is not None:
        games.append(game)
    return games


# --- Le test critique --------------------------------------------------------


def test_every_label_is_legal_in_its_own_position():
    """Chaque coup-cible doit etre legal dans la position-source correspondante."""
    for game in read_games(make_pgn(12, seed=1)):
        for tokens, label in extract_samples(game, NO_FILTER):
            board = decode_board(tokens)
            move = VOCAB.move_at(int(label))
            assert move in board.legal_moves, (
                f"Coup {move.uci()} illegal dans la position reconstruite "
                f"{board.fen()} — la normalisation de couleur est cassee."
            )


def test_samples_have_expected_types_and_ranges():
    game = read_games(make_pgn(1, seed=2))[0]
    samples = list(extract_samples(game, NO_FILTER))
    assert samples, "aucune position extraite"

    for tokens, label in samples:
        assert tokens.shape == (SEQ_LEN,)
        assert tokens.dtype == np.uint8
        assert 0 <= label < VOCAB_SIZE


def test_skip_opening_plies_removes_the_right_count():
    game = read_games(make_pgn(1, seed=3))[0]
    total = len(list(extract_samples(game, NO_FILTER)))
    skipped = len(list(extract_samples(game, Filters(0, 0, skip_opening_plies=8))))
    assert skipped == max(0, total - 8)


# --- Filtres -----------------------------------------------------------------


def test_low_elo_games_are_rejected():
    game = read_games(make_pgn(1, seed=4, elo=1200))[0]
    stats = ParseStats()
    assert accept_game(game, Filters(min_elo=2000), stats) is False
    assert stats.rejected["elo trop faible"] == 1


def test_strong_games_are_accepted():
    game = read_games(make_pgn(1, seed=5, elo=2400))[0]
    assert accept_game(game, Filters(min_elo=2000, min_time_control=0), ParseStats()) is True


def test_bullet_games_are_rejected():
    game = read_games(make_pgn(1, seed=6, elo=2400))[0]
    game.headers["TimeControl"] = "60+0"
    stats = ParseStats()
    assert accept_game(game, Filters(min_elo=2000, min_time_control=180), stats) is False
    assert stats.rejected["cadence trop rapide"] == 1


# --- Ecriture et relecture ---------------------------------------------------


@pytest.fixture
def dataset_dir(tmp_path):
    pgn = tmp_path / "sample.pgn"
    pgn.write_text(make_pgn(20, seed=7), encoding="utf-8")
    out = tmp_path / "processed"
    build_dataset(
        [pgn],
        out,
        filters=Filters(min_elo=2000, min_time_control=0, skip_opening_plies=0),
        max_positions=10_000,
        shard_size=200,
        validation_fraction=0.2,
        seed=0,
    )
    return out


def test_dataset_roundtrip(dataset_dir):
    tokens, labels = load_split(dataset_dir, "train")
    assert len(tokens) == len(labels)
    assert tokens.shape[1] == SEQ_LEN
    assert labels.max() < VOCAB_SIZE

    # Les donnees relues doivent rester coherentes apres passage sur disque.
    for index in range(0, len(tokens), max(1, len(tokens) // 40)):
        board = decode_board(tokens[index])
        assert VOCAB.move_at(int(labels[index])) in board.legal_moves


def test_metadata_is_written(dataset_dir):
    import json

    metadata = json.loads((dataset_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["seq_len"] == SEQ_LEN
    assert metadata["vocab_size"] == VOCAB_SIZE
    assert metadata["positions_train"] > 0


def test_validation_split_is_not_empty(dataset_dir):
    train_tokens, _ = load_split(dataset_dir, "train")
    val_tokens, _ = load_split(dataset_dir, "val")
    assert len(val_tokens) > 0
    assert len(train_tokens) > len(val_tokens)
