"""Tests du modele et du bot neuronal.

Le test central est `test_model_can_overfit_a_tiny_batch`, connu sous le nom de
TEST DE SURAPPRENTISSAGE VOLONTAIRE. C'est le premier reflexe a avoir avant de
lancer un entrainement de plusieurs heures.

Le principe : on donne au modele une poignee d'exemples et on le laisse tourner
longtemps dessus. Il doit finir par les apprendre PAR COEUR, donc atteindre une
perte proche de zero. S'il n'y arrive pas, inutile de lancer le vrai
entrainement : il y a un bug (gradients qui ne circulent pas, cibles mal
alignees, taux d'apprentissage absurde...). Ce test coute quelques secondes et
economise des heures de calcul inutile.

Le second test verifie la propriete la plus importante du bot : il ne peut
jamais jouer un coup illegal, meme avec des poids purement aleatoires.
"""

from __future__ import annotations

import random

import chess
import pytest
import torch
import torch.nn as nn

from src.data.encoding import SEQ_LEN, VOCAB_TOKENS
from src.data.move_vocab import VOCAB_SIZE
from src.engine.neural_bot import NeuralBot
from src.model.transformer import ChessTransformer, ModelConfig

TINY = ModelConfig(d_model=32, n_layers=2, n_heads=4, d_ff=64, dropout=0.0)


def random_positions(count: int, seed: int = 0):
    rng = random.Random(seed)
    boards = []
    while len(boards) < count:
        board = chess.Board()
        for _ in range(rng.randint(0, 60)):
            if board.is_game_over():
                break
            board.push(rng.choice(list(board.legal_moves)))
        if not board.is_game_over():
            boards.append(board)
    return boards


# --- Architecture ------------------------------------------------------------


def test_forward_returns_one_score_per_move():
    model = ChessTransformer(TINY)
    tokens = torch.randint(0, VOCAB_TOKENS, (4, SEQ_LEN))
    assert model(tokens).shape == (4, VOCAB_SIZE)


def test_default_model_size_is_in_the_expected_range():
    """Le modele par defaut doit rester entrainable sur un GPU gratuit."""
    model = ChessTransformer()
    millions = model.num_parameters() / 1e6
    assert 5 < millions < 10, f"{millions:.1f} M de parametres, hors de la cible"


def test_save_and_load_preserves_predictions(tmp_path):
    model = ChessTransformer(TINY).eval()
    tokens = torch.randint(0, VOCAB_TOKENS, (2, SEQ_LEN))
    before = model(tokens)

    path = tmp_path / "model.pt"
    model.save(path)
    after = ChessTransformer.load(path)(tokens)

    assert torch.allclose(before, after, atol=1e-6)


# --- Le test qui valide la capacite d'apprentissage --------------------------


def test_model_can_overfit_a_tiny_batch():
    """Sur 24 exemples repetes, la perte doit s'effondrer vers zero."""
    torch.manual_seed(0)
    model = ChessTransformer(TINY)
    tokens = torch.randint(0, VOCAB_TOKENS, (24, SEQ_LEN))
    labels = torch.randint(0, VOCAB_SIZE, (24,))

    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3)
    criterion = nn.CrossEntropyLoss()

    first_loss = None
    for _ in range(300):
        optimizer.zero_grad()
        loss = criterion(model(tokens), labels)
        loss.backward()
        optimizer.step()
        if first_loss is None:
            first_loss = loss.item()

    final_loss = loss.item()
    assert first_loss > 7.0, "la perte initiale devrait valoir environ ln(1968) = 7.6"
    assert final_loss < 0.2, (
        f"le modele n'arrive pas a apprendre par coeur 24 exemples "
        f"(perte {first_loss:.2f} -> {final_loss:.2f}) : il y a un bug."
    )


# --- Le bot ------------------------------------------------------------------


@pytest.fixture(scope="module")
def bot() -> NeuralBot:
    torch.manual_seed(0)
    return NeuralBot(ChessTransformer(TINY), temperature=0.0)


def test_bot_never_plays_an_illegal_move(bot):
    """Meme avec des poids aleatoires, tous les coups sortis sont legaux.

    C'est la garantie apportee par le masquage a -inf. Elle ne depend pas de la
    qualite de l'entrainement, seulement de la structure du code.
    """
    for board in random_positions(60, seed=1):
        assert bot.select_move(board) in board.legal_moves


def test_probabilities_sum_to_one_over_legal_moves(bot):
    for board in random_positions(20, seed=2):
        moves, probabilities = bot._legal_distribution(board)
        assert set(moves) == set(board.legal_moves)
        assert probabilities.sum().item() == pytest.approx(1.0, abs=1e-5)


def test_explain_returns_sorted_legal_moves(bot):
    for board in random_positions(15, seed=3):
        explained = bot.explain(board, top_k=4)
        assert len(explained) == min(4, board.legal_moves.count())

        weights = [weight for _, weight in explained]
        assert weights == sorted(weights, reverse=True)
        for move, _ in explained:
            assert move in board.legal_moves


def test_temperature_introduces_variety():
    """A temperature nulle le bot est deterministe, au-dessus il varie.

    C'est indispensable pour l'evaluation : deux moteurs deterministes
    rejoueraient 100 fois exactement la meme partie, et l'echantillon
    statistique serait en realite de taille 1.
    """
    torch.manual_seed(0)
    model = ChessTransformer(TINY)
    board = chess.Board()

    strict = NeuralBot(model, temperature=0.0)
    assert len({strict.select_move(board).uci() for _ in range(8)}) == 1

    loose = NeuralBot(model, temperature=1.5, seed=0)
    assert len({loose.select_move(board).uci() for _ in range(40)}) > 1


def test_bot_plays_both_colours(bot):
    """Le bot doit jouer correctement avec les noirs (normalisation de couleur)."""
    board = chess.Board()
    for _ in range(12):
        if board.is_game_over():
            break
        move = bot.select_move(board)
        assert move in board.legal_moves
        board.push(move)
    assert board.ply() > 0
