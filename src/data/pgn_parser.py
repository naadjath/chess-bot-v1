"""Des parties PGN vers un jeu de donnees d'entrainement.

Le probleme a resoudre
----------------------
Un Transformer ne sait pas lire une partie d'echecs. Il lui faut des paires
(entree, sortie) numeriques. Ici :

    entree  = une position, encodee en 68 entiers  (voir encoding.py)
    sortie  = l'index du coup joue, entre 0 et 1967 (voir move_vocab.py)

Une partie de 80 demi-coups produit donc 80 exemples d'entrainement. C'est ce
qui rend le dataset si vite enorme : 50 000 parties suffisent a depasser les
3 millions d'exemples.

L'approche s'appelle le CLONAGE COMPORTEMENTAL (behavioral cloning) : on
apprend au modele a reproduire les decisions d'un expert. Sa limite theorique
est le niveau de l'expert imite — d'ou l'importance des filtres de qualite
ci-dessous.

Le format de sortie
-------------------
Des fichiers `.npz` (format compresse de numpy) decoupes en tranches, plutot
qu'un seul fichier geant. Raison : on peut alors charger le dataset morceau par
morceau au lieu de le tenir entierement en RAM. Le module `psutil` sert
justement a surveiller qu'on ne sature pas la memoire.
"""

from __future__ import annotations

import gzip
import io
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import chess
import chess.pgn
import numpy as np
import psutil
from tqdm import tqdm

from src.data.encoding import SEQ_LEN, encode_board, flip_move, normalize
from src.data.move_vocab import VOCAB, VOCAB_SIZE


@dataclass
class Filters:
    """Criteres de selection des parties.

    Chaque filtre est un choix a justifier dans le rapport — c'est exactement le
    genre de decision que le jury demande d'expliquer.
    """

    #: Elo minimum des DEUX joueurs. On apprend d'un joueur fort, pas de la
    #: moyenne des joueurs en ligne.
    min_elo: int = 2000

    #: Cadence minimale en secondes. En bullet (1 minute), meme les bons joueurs
    #: jouent a l'instinct et bourdent : ce bruit degraderait l'apprentissage.
    min_time_control: int = 180

    #: On ignore les premiers demi-coups : l'ouverture est de la memorisation
    #: pure, pas du raisonnement sur la position. Mettre 0 pour tout garder.
    skip_opening_plies: int = 8

    #: Plafond par partie, pour eviter qu'une finale interminable pese autant
    #: que dix parties normales dans le dataset.
    max_plies_per_game: int = 200

    #: Parties nulles. Les garder apprend a tenir une position egale ; les
    #: exclure concentre l'apprentissage sur le jeu gagnant.
    keep_draws: bool = True


@dataclass
class ParseStats:
    """Compteurs de la passe d'extraction, pour le rapport."""

    games_seen: int = 0
    games_kept: int = 0
    positions: int = 0
    rejected: dict[str, int] = field(default_factory=dict)

    def reject(self, reason: str) -> None:
        self.rejected[reason] = self.rejected.get(reason, 0) + 1

    def summary(self) -> str:
        lines = [
            f"Parties lues     : {self.games_seen:,}".replace(",", " "),
            f"Parties gardees  : {self.games_kept:,}".replace(",", " "),
            f"Positions        : {self.positions:,}".replace(",", " "),
        ]
        if self.games_seen:
            rate = 100 * self.games_kept / self.games_seen
            lines.append(f"Taux de retention: {rate:.1f} %")
        for reason, count in sorted(self.rejected.items(), key=lambda kv: -kv[1]):
            lines.append(f"  rejet [{reason}] : {count:,}".replace(",", " "))
        return "\n".join(lines)


def _wrap_zstd(binary_stream) -> io.TextIOBase:
    try:
        import zstandard
    except ImportError as error:
        raise ImportError(
            "Cette source est compressee en zstandard. Installez la bibliotheque :\n"
            "    pip install zstandard"
        ) from error
    reader = zstandard.ZstdDecompressor().stream_reader(binary_stream)
    return io.TextIOWrapper(reader, encoding="utf-8", errors="replace")


def is_url(source: str | Path) -> bool:
    return str(source).startswith(("http://", "https://"))


def open_pgn(source: str | Path) -> io.TextIOBase:
    """Ouvre un PGN local ou distant, brut, gzippe (.gz) ou zstandard (.zst).

    Le cas interessant est l'URL. Les archives mensuelles de Lichess pesent
    plusieurs dizaines de gigaoctets une fois decompressees, et on n'en a besoin
    que des premieres parties. Plutot que de tout telecharger, on ouvre un flux
    HTTP, on le decompresse a la volee, et on ferme des qu'on a assez de
    positions. Seuls les octets reellement lus transitent sur le reseau —
    quelques centaines de megaoctets au lieu de trente gigaoctets.

    C'est ce qui rend l'entrainement possible sur Colab, dont le disque est
    limite et remis a zero a chaque session.
    """
    if is_url(source):
        import urllib.request

        request = urllib.request.Request(
            str(source), headers={"User-Agent": "chess-bot-v1/1.0 (projet etudiant)"}
        )
        stream = urllib.request.urlopen(request)  # noqa: S310 (URL fournie par l'utilisateur)
        if str(source).endswith(".zst"):
            return _wrap_zstd(stream)
        if str(source).endswith(".gz"):
            return io.TextIOWrapper(gzip.GzipFile(fileobj=stream), encoding="utf-8", errors="replace")
        return io.TextIOWrapper(stream, encoding="utf-8", errors="replace")

    path = Path(source)
    suffix = path.suffix.lower()

    if suffix == ".zst":
        return _wrap_zstd(path.open("rb"))
    if suffix == ".gz":
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def _base_time_control(value: str | None) -> int | None:
    """Extrait la duree de base d'un en-tete TimeControl ("300+3" -> 300)."""
    if not value or value == "-":
        return None
    try:
        return int(value.split("+")[0])
    except ValueError:
        return None


def accept_headers(headers, filters: Filters, stats: ParseStats) -> bool:
    """Decide si une partie merite d'entrer dans le dataset, d'apres ses en-tetes.

    On ne regarde QUE les en-tetes, jamais les coups. C'est ce qui permet au
    lecteur rapide (voir `_FastVisitor`) d'abandonner une partie avant meme
    d'avoir parse son premier coup — et comme plus de 98 % des parties sont
    rejetees, c'est la l'essentiel du gain de vitesse.
    """
    try:
        white_elo = int(headers.get("WhiteElo", 0))
        black_elo = int(headers.get("BlackElo", 0))
    except ValueError:
        stats.reject("elo illisible")
        return False

    if min(white_elo, black_elo) < filters.min_elo:
        stats.reject("elo trop faible")
        return False

    base = _base_time_control(headers.get("TimeControl"))
    if base is not None and base < filters.min_time_control:
        stats.reject("cadence trop rapide")
        return False

    result = headers.get("Result", "*")
    if result == "*":
        stats.reject("partie inachevee")
        return False
    if result == "1/2-1/2" and not filters.keep_draws:
        stats.reject("nulle exclue")
        return False

    # Une partie abandonnee au 3e coup n'apprend rien.
    if "Termination" in headers and headers["Termination"] in {"Abandoned", "Rules infraction"}:
        stats.reject("partie abandonnee")
        return False

    return True


def accept_game(game: chess.pgn.Game, filters: Filters, stats: ParseStats) -> bool:
    """Variante de `accept_headers` prenant un objet partie complet."""
    return accept_headers(game.headers, filters, stats)


#: Sentinelle renvoyee par le lecteur rapide pour une partie filtree. On ne peut
#: pas utiliser None : `read_game` renvoie deja None a la fin du fichier, et
#: confondre les deux ferait arreter la lecture au premier rejet.
SKIPPED = object()


class _FastVisitor(chess.pgn.BaseVisitor):
    """Lecteur de PGN qui ne construit pas l'arbre de la partie.

    Le lecteur par defaut de python-chess (`GameBuilder`) cree un objet noeud
    par demi-coup, avec ses variantes et ses commentaires. C'est complet, mais
    inutile ici : on ne veut qu'une liste de coups.

    Ce visiteur fait deux choses :
      1. il inspecte les en-tetes et abandonne la partie (chess.pgn.SKIP) des
         qu'un filtre echoue, avant de lire le moindre coup ;
      2. pour les parties retenues, il accumule simplement les coups.

    Mesure sur une archive Lichess : 392 parties/s avec le lecteur standard,
    8 282 parties/s avec celui-ci — un facteur 21. Cela ramene la preparation
    d'un million de positions de plusieurs heures a quelques minutes.
    """

    def __init__(self, filters: Filters, stats: ParseStats) -> None:
        super().__init__()
        self._filters = filters
        self._stats = stats
        self.headers: dict[str, str] = {}
        self.moves: list[chess.Move] = []
        self.skipped = False

    def begin_headers(self):
        self.headers = {}
        self.moves = []
        self.skipped = False
        return None

    def visit_header(self, name: str, value: str) -> None:
        self.headers[name] = value

    def end_headers(self):
        if not accept_headers(self.headers, self._filters, self._stats):
            self.skipped = True
            return chess.pgn.SKIP
        return None

    def visit_move(self, board: chess.Board, move: chess.Move) -> None:
        if len(self.moves) < self._filters.max_plies_per_game:
            self.moves.append(move)

    def handle_error(self, error: Exception) -> None:
        """Un PGN malforme ne doit pas interrompre la lecture de l'archive."""
        self.skipped = True
        self._stats.reject("pgn illisible")

    def result(self):
        return SKIPPED if self.skipped else self.moves


def samples_from_moves(
    moves: list[chess.Move], filters: Filters
) -> Iterator[tuple[np.ndarray, int]]:
    """Produit les paires (position encodee, index du coup joue) d'une partie.

    Point delicat : la NORMALISATION DE COULEUR. Quand c'est aux noirs de jouer,
    on retourne l'echiquier pour que le modele voie toujours la position "du
    bon cote"... et il faut alors retourner le coup EXACTEMENT de la meme
    facon, sinon on apprend au modele a jouer le coup miroir. C'est le bug le
    plus courant de ce type de pipeline, et il est silencieux.
    """
    board = chess.Board()

    for ply, move in enumerate(moves):
        if ply >= filters.max_plies_per_game:
            break

        if ply >= filters.skip_opening_plies:
            normalized, flipped = normalize(board)
            target = flip_move(move) if flipped else move

            if VOCAB.contains(target):
                yield encode_board(normalized).astype(np.uint8), VOCAB.index_of(target)

        board.push(move)


def extract_samples(
    game: chess.pgn.Game, filters: Filters
) -> Iterator[tuple[np.ndarray, int]]:
    """Variante de `samples_from_moves` prenant un objet partie complet."""
    board = game.board()

    for ply, move in enumerate(game.mainline_moves()):
        if ply >= filters.max_plies_per_game:
            break

        if ply >= filters.skip_opening_plies:
            normalized, flipped = normalize(board)
            target = flip_move(move) if flipped else move

            if VOCAB.contains(target):
                yield encode_board(normalized).astype(np.uint8), VOCAB.index_of(target)

        board.push(move)


def build_dataset(
    pgn_paths: list[str | Path],
    output_dir: str | Path,
    filters: Filters | None = None,
    max_positions: int = 1_000_000,
    shard_size: int = 250_000,
    validation_fraction: float = 0.02,
    seed: int = 0,
) -> ParseStats:
    """Lit des PGN et ecrit un dataset pret pour l'entrainement.

    Les positions de validation sont prelevees PAR PARTIE et non par position :
    deux positions d'une meme partie se ressemblent beaucoup, les melanger entre
    entrainement et validation reviendrait a s'auto-evaluer sur des donnees
    quasiment vues. C'est une fuite de donnees classique, et elle gonfle
    artificiellement les scores.
    """
    filters = filters or Filters()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = ParseStats()
    rng = np.random.default_rng(seed)
    process = psutil.Process()

    buffers: dict[str, list] = {"train": [], "val": []}
    shard_counts: dict[str, int] = {"train": 0, "val": 0}
    written: dict[str, int] = {"train": 0, "val": 0}

    def flush(split: str, force: bool = False) -> None:
        rows = buffers[split]
        if not rows or (len(rows) < shard_size and not force):
            return
        tokens = np.stack([token for token, _ in rows]).astype(np.uint8)
        labels = np.array([label for _, label in rows], dtype=np.int16)
        path = output_dir / f"{split}_{shard_counts[split]:03d}.npz"
        np.savez_compressed(path, tokens=tokens, labels=labels)
        written[split] += len(rows)
        shard_counts[split] += 1
        rows.clear()

    progress = tqdm(total=max_positions, unit="pos", desc="Extraction")

    for pgn_path in pgn_paths:
        with open_pgn(pgn_path) as handle:
            # `read_game` attend une FABRIQUE de visiteurs (il l'appelle pour
            # chaque partie), pas un visiteur deja construit. On lui passe donc
            # une petite fonction qui capture nos filtres et nos compteurs.
            def new_visitor() -> _FastVisitor:
                return _FastVisitor(filters, stats)

            while stats.positions < max_positions:
                moves = chess.pgn.read_game(handle, Visitor=new_visitor)

                if moves is None:
                    break  # fin du fichier

                stats.games_seen += 1
                if moves is SKIPPED:
                    continue  # filtree sur ses en-tetes, ses coups n'ont pas ete lus

                split = "val" if rng.random() < validation_fraction else "train"
                added = 0
                for tokens, label in samples_from_moves(moves, filters):
                    buffers[split].append((tokens, label))
                    added += 1

                if added:
                    stats.games_kept += 1
                    stats.positions += added
                    progress.update(added)

                flush("train")
                flush("val")

                if stats.games_seen % 2000 == 0:
                    memory_mb = process.memory_info().rss / 1e6
                    progress.set_postfix_str(f"RAM {memory_mb:.0f} Mo")

    progress.close()
    flush("train", force=True)
    flush("val", force=True)

    metadata = {
        "positions_train": written["train"],
        "positions_val": written["val"],
        "seq_len": SEQ_LEN,
        "vocab_size": VOCAB_SIZE,
        "filters": filters.__dict__,
        "sources": [str(p) for p in pgn_paths],
        "games_seen": stats.games_seen,
        "games_kept": stats.games_kept,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return stats


def load_split(dataset_dir: str | Path, split: str = "train") -> tuple[np.ndarray, np.ndarray]:
    """Recharge un decoupage complet en memoire.

    Pratique pour les petits datasets et les tests. Pour un entrainement sur
    plusieurs millions de positions, mieux vaut lire les tranches une par une.
    """
    dataset_dir = Path(dataset_dir)
    shards = sorted(dataset_dir.glob(f"{split}_*.npz"))
    if not shards:
        raise FileNotFoundError(f"Aucune tranche '{split}' dans {dataset_dir}")

    token_blocks, label_blocks = [], []
    for shard in shards:
        with np.load(shard) as data:
            token_blocks.append(data["tokens"])
            label_blocks.append(data["labels"])

    return np.concatenate(token_blocks), np.concatenate(label_blocks)
