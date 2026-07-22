"""Interface commune a tous les joueurs du projet.

Tout ce qui sait jouer aux echecs dans ce projet — bot aleatoire, bot glouton,
minimax, Transformer, Stockfish — implemente cette meme interface. Le moteur de
matchs peut ainsi faire s'affronter n'importe quelle paire sans rien savoir de
leur fonctionnement interne.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import chess


class Bot(ABC):
    """Un joueur d'echecs automatique."""

    #: Nom affiche dans les rapports et les PGN.
    name: str = "bot"

    @abstractmethod
    def select_move(self, board: chess.Board) -> chess.Move:
        """Choisit un coup LEGAL dans la position donnee.

        Le bot ne doit jamais modifier `board` de facon durable : s'il explore
        des variantes, il doit remettre l'echiquier dans son etat initial
        (`board.pop()` apres chaque `board.push()`).
        """

    def explain(self, board: chess.Board, top_k: int = 4) -> list[tuple[chess.Move, float]]:
        """Coups envisages et leur poids relatif, pour affichage dans l'appli.

        Les poids sont normalises pour sommer a 1. Un bot qui ne sait pas
        expliquer son choix renvoie une liste vide — c'est le comportement par
        defaut, l'interface s'adapte.

        Cette methode n'a aucun role dans le jeu lui-meme : elle sert a rendre
        le raisonnement du bot visible, ce qui est precieux pour deboguer et
        pour la demonstration devant le jury.
        """
        return []

    def close(self) -> None:
        """Libere les ressources (processus externe, GPU...). Optionnel."""

    def __enter__(self) -> "Bot":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name!r}>"
