"""Serveur de l'application de jeu.

Livrable "application fonctionnelle" du projet : on joue contre le bot dans le
navigateur.

Choix technique : on utilise `http.server`, qui fait partie de la bibliotheque
standard de Python. Aucune installation supplementaire n'est donc necessaire —
ni Flask, ni Django, ni Gradio. Pour une application locale a un joueur, c'est
amplement suffisant, et ca garantit que le projet demarre du premier coup sur
la machine du jury.

(Ce serveur n'est PAS concu pour etre expose sur Internet : il n'a ni
authentification, ni limitation de debit, et ne gere qu'une partie a la fois.)

Lancement :
    python -m src.app.server
puis ouvrir http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import chess

from src.app.ui import PAGE
from src.engine.base import Bot
from src.engine.baselines import GreedyBot, MinimaxBot, RandomBot

# Les adversaires proposes dans l'interface. `factory` differe la creation :
# on ne construit le bot qu'au moment ou une partie commence.
AVAILABLE_BOTS: dict[str, dict] = {
    "random": {
        "label": "Aleatoire",
        "factory": lambda: RandomBot(),
    },
    "greedy": {
        "label": "Glouton",
        "factory": lambda: GreedyBot(),
    },
    "minimax2": {
        "label": "Minimax 2",
        "factory": lambda: MinimaxBot(depth=2),
    },
    "minimax3": {
        "label": "Minimax 3",
        "factory": lambda: MinimaxBot(depth=3),
    },
}

# Chemin par defaut des poids entraines.
CHECKPOINT = Path(__file__).resolve().parents[2] / "checkpoints" / "best.pt"


def register_transformer_if_available() -> None:
    """Ajoute le Transformer a la liste des adversaires s'il a ete entraine.

    L'application reste ainsi utilisable avant meme le premier entrainement :
    les baselines tiennent le plateau, et le Transformer apparait tout seul des
    que `checkpoints/best.pt` existe.
    """
    if not CHECKPOINT.exists():
        return

    def build() -> Bot:
        from src.engine.neural_bot import NeuralBot  # import tardif : torch est lourd

        return NeuralBot.from_checkpoint(CHECKPOINT, temperature=0.0)

    AVAILABLE_BOTS["transformer"] = {"label": "Transformer", "factory": build}

PIECE_SYMBOLS = {
    (chess.PAWN, chess.WHITE): "P", (chess.KNIGHT, chess.WHITE): "N",
    (chess.BISHOP, chess.WHITE): "B", (chess.ROOK, chess.WHITE): "R",
    (chess.QUEEN, chess.WHITE): "Q", (chess.KING, chess.WHITE): "K",
    (chess.PAWN, chess.BLACK): "p", (chess.KNIGHT, chess.BLACK): "n",
    (chess.BISHOP, chess.BLACK): "b", (chess.ROOK, chess.BLACK): "r",
    (chess.QUEEN, chess.BLACK): "q", (chess.KING, chess.BLACK): "k",
}


class GameSession:
    """La partie en cours. Une seule a la fois, protegee par un verrou.

    Le verrou est necessaire parce que le serveur est multi-thread : sans lui,
    deux requetes simultanees pourraient modifier l'echiquier en meme temps et
    le corrompre.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.board = chess.Board()
        self.bot: Bot = GreedyBot()
        self.player_color: chess.Color = chess.WHITE
        self.san_history: list[str] = []
        self.last_thoughts: list[dict] = []

    # -- Cycle de vie ------------------------------------------------------

    def new_game(self, bot_id: str, color: str) -> dict:
        with self._lock:
            config = AVAILABLE_BOTS.get(bot_id) or AVAILABLE_BOTS["greedy"]
            self.bot.close()
            self.bot = config["factory"]()
            self.player_color = chess.WHITE if color == "white" else chess.BLACK
            self.board = chess.Board()
            self.san_history = []
            self.last_thoughts = []

            if self.board.turn != self.player_color:
                self._play_bot_move()
            return self._snapshot()

    def play(self, uci: str) -> dict:
        with self._lock:
            move = chess.Move.from_uci(uci)
            if move not in self.board.legal_moves:
                raise ValueError(f"Coup illegal : {uci}")

            self._push(move)
            if not self.board.is_game_over(claim_draw=True):
                self._play_bot_move()
            return self._snapshot()

    # -- Interne -----------------------------------------------------------

    def _push(self, move: chess.Move) -> None:
        """Joue un coup en memorisant sa notation algebrique.

        Le SAN doit etre calcule AVANT de jouer le coup : il depend de la
        position de depart (pour savoir s'il faut preciser la colonne en cas
        d'ambiguite, ajouter "+" pour l'echec, etc.).
        """
        self.san_history.append(self.board.san(move))
        self.board.push(move)

    def _play_bot_move(self) -> None:
        # On interroge le bot AVANT qu'il joue, tant que la position est encore
        # celle sur laquelle il a reflechi.
        considered = self.bot.explain(self.board, top_k=4)
        chosen = self.bot.select_move(self.board)

        # Quand plusieurs coups sont a egalite parfaite (frequent en debut de
        # partie ou tout se vaut), le bot en tire un au hasard et il peut ne pas
        # figurer dans les 4 affiches. On l'ajoute alors explicitement : une
        # interface qui montre un raisonnement sans le coup joue est trompeuse.
        if considered and all(move != chosen for move, _ in considered):
            considered = [(chosen, considered[0][1])] + considered[:-1]

        self.last_thoughts = [
            {
                "san": self.board.san(move),
                "weight": round(weight, 4),
                "played": move == chosen,
            }
            for move, weight in considered
        ]
        self._push(chosen)

    def _status_text(self) -> str:
        board = self.board
        if board.is_checkmate():
            player_won = board.turn != self.player_color
            return "Echec et mat — vous gagnez !" if player_won else "Echec et mat — le bot gagne."
        if board.is_stalemate():
            return "Pat : match nul."
        if board.is_insufficient_material():
            return "Materiel insuffisant : match nul."
        if board.can_claim_threefold_repetition():
            return "Triple repetition : match nul."
        if board.can_claim_fifty_moves():
            return "Regle des 50 coups : match nul."
        if board.is_game_over(claim_draw=True):
            return "Partie terminee : match nul."
        if board.is_check():
            return "Echec ! A vous de jouer." if board.turn == self.player_color else "Echec au bot."
        return "A vous de jouer." if board.turn == self.player_color else "Le bot reflechit..."

    def _check_square(self) -> str | None:
        if not self.board.is_check():
            return None
        king = self.board.king(self.board.turn)
        return chess.square_name(king) if king is not None else None

    def _snapshot(self) -> dict:
        board = self.board
        squares = [None] * 64
        for square, piece in board.piece_map().items():
            squares[square] = PIECE_SYMBOLS[(piece.piece_type, piece.color)]

        last = board.move_stack[-1].uci() if board.move_stack else None

        return {
            "board": squares,
            "fen": board.fen(),
            "legal_moves": [move.uci() for move in board.legal_moves],
            "san": self.san_history,
            "last_move": last,
            "check_square": self._check_square(),
            "your_turn": board.turn == self.player_color,
            "game_over": board.is_game_over(claim_draw=True),
            "status": self._status_text(),
            "player_color": "white" if self.player_color == chess.WHITE else "black",
            "bot_name": self.bot.name,
            "thoughts": self.last_thoughts,
        }


SESSION = GameSession()


class Handler(BaseHTTPRequestHandler):
    """Routage minimal : la page en GET, l'etat du jeu en POST."""

    server_version = "ChessBotV1/1.0"

    def do_GET(self) -> None:  # noqa: N802 (nom impose par http.server)
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "corps de requete illisible"})
            return

        try:
            if self.path == "/api/bots":
                self._json(200, {
                    "bots": [{"id": key, "label": cfg["label"]} for key, cfg in AVAILABLE_BOTS.items()]
                })
            elif self.path == "/api/new":
                self._json(200, SESSION.new_game(payload.get("bot", "greedy"), payload.get("color", "white")))
            elif self.path == "/api/move":
                self._json(200, SESSION.play(payload["uci"]))
            else:
                self._json(404, {"error": "route inconnue"})
        except (ValueError, KeyError) as error:
            self._json(400, {"error": str(error)})

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        """Silence les logs d'acces, qui noient la console a chaque coup."""


def main() -> None:
    parser = argparse.ArgumentParser(description="Application de jeu Chess Bot v1.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    args = parser.parse_args()

    register_transformer_if_available()

    url = f"http://{args.host}:{args.port}"
    server = ThreadingHTTPServer((args.host, args.port), Handler)

    print("=" * 58)
    print("  Chess Bot v1 — application de jeu")
    print(f"  Ouvrez : {url}")
    print(f"  Adversaires : {', '.join(cfg['label'] for cfg in AVAILABLE_BOTS.values())}")
    print("  Arreter le serveur : Ctrl+C")
    print("=" * 58)

    if not args.no_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServeur arrete.")
    finally:
        server.server_close()
        SESSION.bot.close()


if __name__ == "__main__":
    main()
