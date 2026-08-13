"""Campagne d'evaluation complete du bot, et generation du rapport d'Elo.

Ce script produit le livrable "ELO approximatif constate face a Stockfish". Il
fait jouer le bot contre une echelle d'adversaires de force croissante :

    aleatoire  <  glouton  <  minimax-2  <  minimax-3  <  Stockfish 1320

Les baselines (dont l'Elo approximatif est admis) servent d'echelle graduee pour
situer le bot ; Stockfish fournit une borne superieure calibree. Pour chaque
affrontement on calcule l'Elo avec son intervalle de confiance de Wilson, et on
enregistre toutes les parties en PGN (preuve et analyse).

Usage :
    python -m scripts.evaluate --model checkpoints/best.pt --games 60
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine.neural_bot import NeuralBot  # noqa: E402
from src.eval.elo import estimate_elo  # noqa: E402
from src.eval.match import play_match  # noqa: E402
from scripts.run_match import build_bot  # noqa: E402

# L'echelle d'adversaires, avec leur Elo suppose (baselines) ou reel (Stockfish).
LADDER = [
    ("random", "Aleatoire"),
    ("greedy", "Glouton"),
    ("minimax:2", "Minimax profondeur 2"),
    ("minimax:3", "Minimax profondeur 3"),
    ("stockfish:1320", "Stockfish (bride 1320)"),
]


def run_campaign(model_path: str, games: int, seed: int, pgn_dir: Path) -> list[dict]:
    """Fait jouer le bot contre toute l'echelle et renvoie les resultats."""
    pgn_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    for spec, label in LADDER:
        try:
            opponent, opponent_elo = build_bot(spec, seed=seed + 500)
        except (FileNotFoundError, SystemExit) as error:
            print(f"  [ignore] {label} : {error}")
            continue

        bot = NeuralBot.from_checkpoint(model_path, temperature=0.2)
        print(f"\n=== {bot.name} vs {label} ({games} parties) ===")
        try:
            result = play_match(bot, opponent, n_games=games, seed=seed)
        finally:
            bot.close()
            opponent.close()

        estimate = estimate_elo(result.wins, result.draws, result.losses, opponent_elo)
        pgn_path = pgn_dir / f"vs_{spec.replace(':', '')}.pgn"
        result.save_pgn(pgn_path)

        print(f"  {result.summary()}")
        print(f"  {estimate.summary()}")

        rows.append({
            "label": label,
            "opponent_elo": opponent_elo,
            "wins": result.wins,
            "draws": result.draws,
            "losses": result.losses,
            "score": result.score,
            "estimate": estimate,
            "pgn": pgn_path,
        })

    return rows


def write_report(rows: list[dict], model_path: str, games: int, output: Path) -> None:
    """Ecrit le rapport d'Elo en Markdown, pret a coller dans le rapport final."""
    lines = [
        "# Rapport d'evaluation — Elo du Transformer",
        "",
        f"Modele : `{model_path}`  ",
        f"Parties par adversaire : {games}  ",
        "Couleurs alternees, ouvertures variees, intervalles de confiance de Wilson (95 %).",
        "",
        "| Adversaire | Elo adv. | V | N | D | Score | Elo estime (IC 95 %) |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]

    for row in rows:
        est = row["estimate"]
        if est.is_saturated and est.score <= 0.5:
            elo_txt = f"< {est.elo_high:.0f} (borne haute)"
        elif est.is_saturated:
            elo_txt = f"> {est.elo_low:.0f} (borne basse)"
        else:
            elo_txt = f"{est.elo:.0f} [{est.elo_low:.0f} ; {est.elo_high:.0f}]"
        lines.append(
            f"| {row['label']} | {row['opponent_elo']:.0f} | {row['wins']} | "
            f"{row['draws']} | {row['losses']} | {row['score']:.1%} | {elo_txt} |"
        )

    # Estimation de synthese : moyenne des Elo mesures (non satures).
    measured = [r["estimate"].elo for r in rows if not r["estimate"].is_saturated]
    lines += ["", "## Synthese", ""]
    if measured:
        lo, hi = min(measured), max(measured)
        lines.append(
            f"Les affrontements non satures situent le bot entre **{lo:.0f} et "
            f"{hi:.0f} Elo**. L'ecart reflete l'imprecision des Elo supposes des "
            "baselines, qui ne sont pas calibres officiellement."
        )
    else:
        lines.append("Tous les affrontements sont satures : le bot est trop faible pour l'echelle choisie.")

    saturated_losses = [r for r in rows if r["estimate"].is_saturated and r["score"] <= 0.5]
    if saturated_losses:
        weakest = min(saturated_losses, key=lambda r: r["opponent_elo"])
        lines.append(
            f"\nLe bot perd l'integralite de ses parties face a **{weakest['label']}** "
            f"(Elo ~{weakest['opponent_elo']:.0f}), ce qui constitue une borne "
            "superieure a son niveau."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nRapport ecrit : {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Campagne d'evaluation Elo du bot.")
    parser.add_argument("--model", default="checkpoints/best.pt")
    parser.add_argument("--games", type=int, default=60)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--pgn-dir", default="results/games")
    parser.add_argument("--report", default="results/elo_report.md")
    args = parser.parse_args()

    rows = run_campaign(args.model, args.games, args.seed, Path(args.pgn_dir))
    if rows:
        write_report(rows, args.model, args.games, Path(args.report))

    print("\n" + "=" * 60)
    print("Campagne terminee.")
    print("=" * 60)


if __name__ == "__main__":
    main()
