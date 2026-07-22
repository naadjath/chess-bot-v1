"""Stockfish, notre adversaire de reference et notre etalon Elo.

Stockfish est un moteur d'echecs externe : c'est un programme separe (un fichier
.exe sous Windows) avec lequel Python discute par le protocole texte UCI.
`python-chess` s'occupe de toute la plomberie via `chess.engine`.

Pourquoi le brider ?
--------------------
Stockfish a pleine puissance vaut environ 3600 Elo. Notre bot perdrait 200
parties sur 200, le score serait 0% et l'Elo serait mathematiquement
incalculable (log10 d'une division par zero). On le ramene donc a un niveau
comparable au notre grace a l'option officielle `UCI_LimitStrength` + `UCI_Elo`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import chess
import chess.engine

from src.engine.base import Bot

# Elo minimum accepte par Stockfish 16+. En dessous, il faut passer par
# l'option `Skill Level` (0 a 20), plus grossiere.
MIN_UCI_ELO = 1320


def find_stockfish(explicit_path: str | Path | None = None) -> str:
    """Localise l'executable Stockfish.

    Ordre de recherche : le chemin fourni, puis le dossier `bin/` du projet,
    puis le PATH systeme.
    """
    if explicit_path is not None:
        path = Path(explicit_path)
        if path.exists():
            return str(path)
        raise FileNotFoundError(f"Stockfish introuvable au chemin indique : {path}")

    project_root = Path(__file__).resolve().parents[2]
    for candidate in sorted(project_root.glob("bin/stockfish*")):
        if candidate.is_file():
            return str(candidate)

    found = shutil.which("stockfish")
    if found:
        return found

    raise FileNotFoundError(
        "Stockfish est introuvable.\n"
        "  1. Telechargez-le sur https://stockfishchess.org/download/\n"
        "  2. Placez l'executable dans le dossier bin/ du projet\n"
        "     (ex: chess-bot-v1/bin/stockfish.exe)"
    )


class StockfishBot(Bot):
    """Adversaire Stockfish, bride a un niveau Elo donne.

    S'utilise avec `with`, pour que le processus externe soit bien ferme :

    >>> with StockfishBot(elo=1400) as sf:      # doctest: +SKIP
    ...     move = sf.select_move(chess.Board())
    """

    def __init__(
        self,
        elo: int = 1400,
        think_time: float = 0.05,
        path: str | Path | None = None,
        threads: int = 1,
        hash_mb: int = 16,
        name: str | None = None,
    ) -> None:
        if elo < MIN_UCI_ELO:
            raise ValueError(
                f"Stockfish n'accepte pas UCI_Elo < {MIN_UCI_ELO}. "
                "Pour un adversaire plus faible, utilisez les baselines "
                "(RandomBot, GreedyBot, MinimaxBot)."
            )

        self.elo = elo
        self.think_time = think_time
        self.name = name or f"stockfish-{elo}"

        self._engine = chess.engine.SimpleEngine.popen_uci(find_stockfish(path))
        self._engine.configure(
            {
                "UCI_LimitStrength": True,
                "UCI_Elo": elo,
                "Threads": threads,
                "Hash": hash_mb,
            }
        )

    def select_move(self, board: chess.Board) -> chess.Move:
        result = self._engine.play(board, chess.engine.Limit(time=self.think_time))
        if result.move is None:
            raise RuntimeError("Stockfish n'a renvoye aucun coup.")
        return result.move

    def analyse_best_move(self, board: chess.Board, depth: int = 12) -> chess.Move:
        """Meilleur coup a pleine force, a profondeur fixe.

        Sert a annoter un dataset ("le professeur"), pas a jouer un match :
        cette methode ignore volontairement le bridage Elo.
        """
        info = self._engine.analyse(board, chess.engine.Limit(depth=depth))
        pv = info.get("pv")
        if not pv:
            raise RuntimeError("Stockfish n'a renvoye aucune variante.")
        return pv[0]

    def close(self) -> None:
        if getattr(self, "_engine", None) is not None:
            self._engine.quit()
            self._engine = None  # type: ignore[assignment]
