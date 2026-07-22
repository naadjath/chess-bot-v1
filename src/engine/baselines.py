"""Les bots de reference (baselines).

A quoi ca sert ?
----------------
Dire "notre Transformer fait 1500 Elo" n'a de sens que compare a quelque chose.
Ces trois bots tres simples donnent une echelle de reference :

  RandomBot  (~250 Elo) : joue un coup legal au hasard.
                          Si le Transformer ne le bat pas, il n'a rien appris.
  GreedyBot  (~600 Elo) : prend la piece la plus chere accessible.
                          Le battre prouve qu'on comprend la valeur materielle.
  MinimaxBot (~1100 Elo): vraie recherche alpha-beta a faible profondeur.
                          Le battre prouve qu'on rivalise avec du calcul.

Ce sont aussi les premiers adversaires a utiliser pour deboguer : ils sont
instantanes et ne demandent aucune installation externe.
"""

from __future__ import annotations

import math
import random

import chess

from src.engine.base import Bot


def softmax_weights(
    scored: list[tuple[chess.Move, float]], top_k: int, temperature: float = 120.0
) -> list[tuple[chess.Move, float]]:
    """Transforme des scores en centipions en poids relatifs sommant a 1.

    `temperature` est exprimee en centipions : plus elle est grande, plus les
    poids sont uniformes. 120 signifie grossierement "un avantage d'un pion et
    demi rend un coup nettement dominant".

    Sert uniquement a l'affichage dans l'application, jamais au choix du coup.
    """
    if not scored:
        return []

    best = sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]
    top_score = best[0][1]
    exponentials = [math.exp((score - top_score) / temperature) for _, score in best]
    total = sum(exponentials)
    return [(move, value / total) for (move, _), value in zip(best, exponentials)]

# Valeur des pieces en centipions (1 pion = 100). Le roi vaut 0 : on ne peut
# pas le capturer, sa "valeur" est geree par la detection de mat.
PIECE_VALUES: dict[chess.PieceType, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

MATE_SCORE = 100_000


class RandomBot(Bot):
    """Joue un coup legal tire au hasard."""

    def __init__(self, seed: int | None = None, name: str = "random") -> None:
        self.name = name
        self._rng = random.Random(seed)

    def select_move(self, board: chess.Board) -> chess.Move:
        return self._rng.choice(list(board.legal_moves))


class GreedyBot(Bot):
    """Joue la capture la plus rentable, sinon un coup au hasard.

    "Glouton" (greedy) : il regarde un seul demi-coup en avant et prend le
    maximum immediat, sans se demander si la piece sera reprise juste apres.
    C'est exactement le genre d'erreur qui plafonne son niveau vers 600 Elo.
    """

    def __init__(self, seed: int | None = None, name: str = "greedy") -> None:
        self.name = name
        self._rng = random.Random(seed)

    def select_move(self, board: chess.Board) -> chess.Move:
        best_moves: list[chess.Move] = []
        best_gain = -1

        for move in board.legal_moves:
            board.push(move)
            is_mate = board.is_checkmate()
            board.pop()

            if is_mate:
                return move  # un mat en un, on ne cherche pas plus loin

            gain = 0
            captured = board.piece_at(move.to_square)
            if captured is not None:
                gain = PIECE_VALUES[captured.piece_type]
            elif board.is_en_passant(move):
                gain = PIECE_VALUES[chess.PAWN]

            if move.promotion:
                gain += PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]

            if gain > best_gain:
                best_gain, best_moves = gain, [move]
            elif gain == best_gain:
                best_moves.append(move)

        return self._rng.choice(best_moves)

    def _capture_gain(self, board: chess.Board, move: chess.Move) -> int:
        """Materiel gagne immediatement par un coup, en centipions."""
        gain = 0
        captured = board.piece_at(move.to_square)
        if captured is not None:
            gain = PIECE_VALUES[captured.piece_type]
        elif board.is_en_passant(move):
            gain = PIECE_VALUES[chess.PAWN]
        if move.promotion:
            gain += PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]
        return gain

    def explain(self, board: chess.Board, top_k: int = 4) -> list[tuple[chess.Move, float]]:
        scored = [(move, float(self._capture_gain(board, move))) for move in board.legal_moves]
        return softmax_weights(scored, top_k)


def material_evaluation(board: chess.Board) -> int:
    """Evalue une position en centipions, du point de vue du joueur au trait.

    Positif = le joueur au trait est mieux. C'est l'evaluation la plus simple
    possible : on compte juste le materiel. Aucune notion de structure de pions,
    de securite du roi ou d'activite des pieces.
    """
    if board.is_checkmate():
        return -MATE_SCORE  # c'est a nous de jouer et on est mat : perdu
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    for piece_type, value in PIECE_VALUES.items():
        score += value * len(board.pieces(piece_type, board.turn))
        score -= value * len(board.pieces(piece_type, not board.turn))
    return score


class MinimaxBot(Bot):
    """Recherche minimax avec elagage alpha-beta a profondeur fixe.

    Le principe du minimax : "je joue le coup qui maximise mon score, en
    supposant que l'adversaire repondra par le coup qui le minimise". On
    developpe l'arbre des variantes sur `depth` demi-coups, on evalue les
    feuilles au materiel, et on remonte.

    L'elagage alpha-beta est une optimisation exacte (il ne change PAS le coup
    choisi) : des qu'on sait qu'une branche est deja moins bonne qu'une autre
    deja examinee, on arrete de la fouiller.
    """

    def __init__(self, depth: int = 2, seed: int | None = None, name: str | None = None) -> None:
        self.depth = depth
        self.name = name or f"minimax-d{depth}"
        self._rng = random.Random(seed)

    def select_move(self, board: chess.Board) -> chess.Move:
        scored = self._root_scores(board)
        best_score = max(score for _, score in scored)
        best_moves = [move for move, score in scored if score == best_score]
        return self._rng.choice(best_moves)

    def explain(self, board: chess.Board, top_k: int = 4) -> list[tuple[chess.Move, float]]:
        return softmax_weights(self._root_scores(board), top_k)

    def _root_scores(self, board: chess.Board) -> list[tuple[chess.Move, float]]:
        """Evalue chaque coup jouable a la racine.

        Volontairement SANS elagage a ce niveau : on veut le score exact de tous
        les coups (pour pouvoir les afficher), pas seulement celui du meilleur.
        L'elagage reste actif dans les sous-arbres, ou il ne fausse rien.
        """
        scored: list[tuple[chess.Move, float]] = []
        for move in self._ordered_moves(board):
            board.push(move)
            # Le score revient du point de vue de l'adversaire : on l'inverse.
            score = -self._negamax(board, self.depth - 1, -MATE_SCORE * 2, MATE_SCORE * 2)
            board.pop()
            scored.append((move, float(score)))
        return scored

    def _negamax(self, board: chess.Board, depth: int, alpha: int, beta: int) -> int:
        """Negamax : une ecriture compacte du minimax.

        Astuce : au lieu d'alterner "maximiser" et "minimiser", on evalue
        toujours du point de vue du joueur au trait et on inverse le signe a
        chaque niveau. Le code est deux fois plus court, le resultat identique.
        """
        if depth == 0 or board.is_game_over(claim_draw=False):
            return material_evaluation(board)

        best = -MATE_SCORE * 2
        for move in self._ordered_moves(board):
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()

            best = max(best, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break  # elagage : l'adversaire n'ira jamais dans cette branche
        return best

    @staticmethod
    def _ordered_moves(board: chess.Board) -> list[chess.Move]:
        """Trie les coups : captures d'abord.

        L'elagage alpha-beta est bien plus efficace si on examine les coups
        prometteurs en premier. Regarder les captures avant le reste suffit a
        diviser le nombre de noeuds explores par plusieurs.
        """
        return sorted(board.legal_moves, key=lambda m: not board.is_capture(m))
