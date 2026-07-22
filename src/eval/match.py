"""Organisation des matchs entre deux bots.

Trois precautions methodologiques sont implementees ici. Elles paraissent
mineures mais ce sont elles qui rendent la mesure d'Elo credible ; il faut
savoir les justifier a la soutenance.

1. ALTERNANCE DES COULEURS
   Les blancs gagnent environ 55% des parties entre joueurs de meme niveau.
   Si notre bot jouait toujours les blancs, son Elo serait surestime d'environ
   35 points. On alterne donc strictement une partie sur deux.

2. VARIATION DES OUVERTURES
   Deux bots deterministes rejouent exactement la meme partie a l'infini : 100
   parties = 1 partie repetee 100 fois, et l'echantillon statistique est de
   taille 1. On impose donc quelques demi-coups aleatoires en debut de partie
   (meme position de depart pour les deux couleurs de la paire, pour rester
   equitable).

3. LIMITE DE COUPS
   Sans plafond, deux bots faibles peuvent se poursuivre indefiniment. Au-dela
   de `max_plies`, la partie est comptee nulle.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import chess
import chess.pgn
from tqdm import tqdm

from src.engine.base import Bot


@dataclass
class MatchResult:
    """Bilan d'une campagne, du point de vue du premier bot."""

    bot_name: str
    opponent_name: str
    wins: int = 0
    draws: int = 0
    losses: int = 0
    games: list[chess.pgn.Game] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.wins + self.draws + self.losses

    @property
    def score(self) -> float:
        return (self.wins + 0.5 * self.draws) / self.total if self.total else 0.0

    def summary(self) -> str:
        return (
            f"{self.bot_name} vs {self.opponent_name} : "
            f"{self.wins}V {self.draws}N {self.losses}D "
            f"({self.score:.1%} sur {self.total} parties)"
        )

    def save_pgn(self, path: str | Path) -> None:
        """Ecrit toutes les parties dans un fichier PGN (preuve + analyse)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for game in self.games:
                print(game, file=handle, end="\n\n")


def random_opening(rng: random.Random, plies: int) -> list[chess.Move]:
    """Tire une ouverture aleatoire mais jouable de `plies` demi-coups.

    On evite les coups qui perdent immediatement du materiel en refusant les
    captures : le but est de diversifier, pas de commencer avec une piece en
    moins.
    """
    board = chess.Board()
    moves: list[chess.Move] = []
    for _ in range(plies):
        quiet = [m for m in board.legal_moves if not board.is_capture(m)]
        candidates = quiet or list(board.legal_moves)
        if not candidates:
            break
        move = rng.choice(candidates)
        board.push(move)
        moves.append(move)
    return moves


def play_game(
    white: Bot,
    black: Bot,
    opening: list[chess.Move] | None = None,
    max_plies: int = 400,
    round_number: int = 1,
) -> tuple[str, chess.pgn.Game]:
    """Joue une partie complete.

    Returns
    -------
    (resultat, partie_pgn)
        resultat vaut "1-0", "0-1" ou "1/2-1/2".
    """
    board = chess.Board()
    for move in opening or []:
        board.push(move)

    while not board.is_game_over(claim_draw=True) and board.ply() < max_plies:
        bot = white if board.turn == chess.WHITE else black
        move = bot.select_move(board)

        # Filet de securite : un bot bugge ne doit pas corrompre la partie.
        if move not in board.legal_moves:
            raise ValueError(f"{bot.name} a propose un coup illegal : {move} dans {board.fen()}")

        board.push(move)

    if board.is_game_over(claim_draw=True):
        result = board.result(claim_draw=True)
    else:
        result = "1/2-1/2"  # limite de coups atteinte

    game = chess.pgn.Game.from_board(board)
    game.headers["White"] = white.name
    game.headers["Black"] = black.name
    game.headers["Result"] = result
    game.headers["Event"] = "Chess Bot v1 - evaluation"
    game.headers["Round"] = str(round_number)
    return result, game


def play_match(
    bot: Bot,
    opponent: Bot,
    n_games: int = 100,
    opening_plies: int = 4,
    max_plies: int = 400,
    seed: int = 0,
    keep_games: bool = True,
    show_progress: bool = True,
) -> MatchResult:
    """Fait jouer `n_games` parties entre deux bots, couleurs alternees.

    Les parties vont par paires : la meme ouverture aleatoire est jouee une fois
    avec `bot` en blancs, une fois avec `bot` en noirs. Cela neutralise a la
    fois l'avantage des blancs et la chance du tirage d'ouverture.
    """
    rng = random.Random(seed)
    result = MatchResult(bot_name=bot.name, opponent_name=opponent.name)

    iterator = range(n_games)
    if show_progress:
        iterator = tqdm(iterator, desc=f"{bot.name} vs {opponent.name}", unit="partie")

    opening: list[chess.Move] = []
    for game_index in iterator:
        bot_plays_white = game_index % 2 == 0

        # Nouvelle ouverture a chaque paire de parties.
        if bot_plays_white:
            opening = random_opening(rng, opening_plies)

        white, black = (bot, opponent) if bot_plays_white else (opponent, bot)
        outcome, game = play_game(
            white, black, opening=opening, max_plies=max_plies, round_number=game_index + 1
        )

        if outcome == "1/2-1/2":
            result.draws += 1
        elif (outcome == "1-0") == bot_plays_white:
            result.wins += 1
        else:
            result.losses += 1

        if keep_games:
            result.games.append(game)

    return result
