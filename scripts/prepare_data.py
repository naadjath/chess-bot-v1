"""Construit le jeu de donnees d'entrainement a partir de parties PGN.

Deux usages
-----------

1. MODE DEMO — teste toute la chaine en 30 secondes, sans rien telecharger.
   Le script fait jouer les bots de reference entre eux, ecrit les parties en
   PGN, puis les transforme en dataset. Les donnees sont mediocres (des bots
   faibles), mais ce n'est pas le but : on verifie que le pipeline fonctionne.

       python -m scripts.prepare_data --demo-games 60

2. MODE REEL — a partir d'une archive Lichess.
   Telechargez un fichier mensuel sur https://database.lichess.org (format
   .pgn.zst), puis :

       pip install zstandard
       python -m scripts.prepare_data --input data/raw/lichess_2025-01.pgn.zst \
           --max-positions 1000000

   Inutile de decompresser l'archive : elle est lue en flux et le script
   s'arrete des qu'il a assez de positions. Quelques minutes suffisent, meme
   sur un fichier de 30 Go.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.pgn_parser import Filters, build_dataset, is_url  # noqa: E402
from src.engine.baselines import GreedyBot, MinimaxBot, RandomBot  # noqa: E402
from src.eval.match import play_match  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_demo_pgn(n_games: int, output: Path, seed: int = 0) -> Path:
    """Fabrique un PGN de demonstration en faisant jouer les baselines.

    On melange trois affrontements pour varier les positions : un dataset ou
    toutes les parties se ressemblent apprendrait au modele une seule facon de
    jouer.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    pairings = [
        (MinimaxBot(depth=2, seed=seed), GreedyBot(seed=seed + 1)),
        (MinimaxBot(depth=2, seed=seed + 2), RandomBot(seed=seed + 3)),
        (GreedyBot(seed=seed + 4), RandomBot(seed=seed + 5)),
    ]

    games = []
    per_pairing = max(2, n_games // len(pairings))
    for index, (bot, opponent) in enumerate(pairings):
        result = play_match(
            bot, opponent, n_games=per_pairing, opening_plies=6, seed=seed + index * 100
        )
        games.extend(result.games)
        bot.close()
        opponent.close()

    with output.open("w", encoding="utf-8") as handle:
        for game in games:
            # Le parser filtre sur l'Elo : on annote les parties de demo pour
            # qu'elles franchissent le filtre au lieu de le desactiver.
            game.headers["WhiteElo"] = "2000"
            game.headers["BlackElo"] = "2000"
            game.headers["TimeControl"] = "600+0"
            print(game, file=handle, end="\n\n")

    print(f"{len(games)} parties de demonstration ecrites dans {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Preparation du dataset d'entrainement.")
    parser.add_argument(
        "--input",
        nargs="*",
        default=[],
        help="fichiers PGN locaux OU URLs (.pgn, .gz, .zst) — les URLs sont lues en flux",
    )
    parser.add_argument("--demo-games", type=int, default=0, help="genere N parties de demo")
    parser.add_argument("--output", default="data/processed", help="dossier de sortie")
    parser.add_argument("--max-positions", type=int, default=1_000_000)
    parser.add_argument("--shard-size", type=int, default=250_000)
    parser.add_argument("--min-elo", type=int, default=2000)
    parser.add_argument("--min-time-control", type=int, default=180)
    parser.add_argument("--skip-opening-plies", type=int, default=8)
    parser.add_argument("--no-draws", action="store_true", help="exclure les parties nulles")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    # Les URLs restent des chaines : elles sont ouvertes en flux, pas ouvertes
    # comme des fichiers du disque.
    sources: list = [item if is_url(item) else Path(item) for item in args.input]

    if args.demo_games:
        demo_path = PROJECT_ROOT / "data" / "raw" / "demo.pgn"
        sources.append(generate_demo_pgn(args.demo_games, demo_path, seed=args.seed))

    if not sources:
        parser.error(
            "Aucune source. Utilisez --input chemin/vers/parties.pgn.zst "
            "ou --demo-games 60 pour tester le pipeline."
        )

    missing = [item for item in sources if not is_url(item) and not item.exists()]
    if missing:
        parser.error(f"Fichier(s) introuvable(s) : {', '.join(str(p) for p in missing)}")

    filters = Filters(
        min_elo=args.min_elo,
        min_time_control=args.min_time_control,
        skip_opening_plies=args.skip_opening_plies,
        keep_draws=not args.no_draws,
    )

    output_dir = Path(args.output)
    stats = build_dataset(
        sources,
        output_dir,
        filters=filters,
        max_positions=args.max_positions,
        shard_size=args.shard_size,
        seed=args.seed,
    )

    print()
    print("=" * 60)
    print(stats.summary())
    print("=" * 60)
    print(f"Dataset ecrit dans {output_dir.resolve()}")


if __name__ == "__main__":
    main()
