"""Script d'evaluation : fait jouer un bot et estime son Elo.

C'EST LE MILESTONE BLOQUANT DE LA SEMAINE 1.
Tant que ce script ne tourne pas de bout en bout, on ne touche pas au
Transformer. Il valide toute la chaine : creation des bots -> matchs ->
comptage -> statistiques -> rapport.

Exemples d'utilisation (depuis la racine du projet)
---------------------------------------------------
    # Le bot glouton contre le bot aleatoire (aucune installation requise)
    python -m scripts.run_match --bot greedy --opponent random --games 100

    # Minimax contre Stockfish bride a 1400 (necessite Stockfish installe)
    python -m scripts.run_match --bot minimax --opponent stockfish:1400 --games 40

    # Le tournoi complet des baselines
    python -m scripts.run_match --tournament
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permet de lancer le script depuis la racine sans installer le paquet.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine.base import Bot  # noqa: E402
from src.engine.baselines import GreedyBot, MinimaxBot, RandomBot  # noqa: E402
from src.eval.elo import estimate_elo  # noqa: E402
from src.eval.match import play_match  # noqa: E402

# Elo suppose de chaque baseline. Ce sont des ordres de grandeur admis, pas des
# mesures officielles : a raffiner en les ancrant sur Stockfish bride.
BASELINE_ELO = {
    "random": 250.0,
    "greedy": 600.0,
    "minimax": 1100.0,
}


def build_bot(spec: str, seed: int = 0) -> tuple[Bot, float]:
    """Construit un bot a partir de son nom. Renvoie (bot, elo_suppose).

    Formats acceptes : "random", "greedy", "minimax", "minimax:3",
    "stockfish:1400".
    """
    name, _, argument = spec.partition(":")
    name = name.lower()

    if name == "random":
        return RandomBot(seed=seed), BASELINE_ELO["random"]
    if name == "greedy":
        return GreedyBot(seed=seed), BASELINE_ELO["greedy"]
    if name == "minimax":
        depth = int(argument) if argument else 2
        # Chaque demi-coup de profondeur supplementaire vaut grosso modo
        # +200 Elo tant qu'on reste a faible profondeur.
        return MinimaxBot(depth=depth, seed=seed), BASELINE_ELO["minimax"] + 200.0 * (depth - 2)
    if name == "stockfish":
        from src.engine.stockfish_bot import StockfishBot  # import tardif : evite l'erreur

        elo = int(argument) if argument else 1400
        return StockfishBot(elo=elo), float(elo)

    if name in ("neural", "transformer"):
        from src.engine.neural_bot import NeuralBot  # import tardif : torch est lourd

        checkpoint = argument or "checkpoints/best.pt"
        # Une petite temperature evite que deux moteurs deterministes rejouent
        # 100 fois la meme partie : l'echantillon serait de taille 1.
        bot = NeuralBot.from_checkpoint(checkpoint, temperature=0.3, seed=seed)
        return bot, 0.0  # son Elo est justement ce qu'on cherche a mesurer

    raise SystemExit(
        f"Bot inconnu : {spec!r}. Valeurs possibles : random, greedy, "
        "minimax[:profondeur], stockfish[:elo], neural[:chemin_du_checkpoint]"
    )


def run_single(args: argparse.Namespace) -> None:
    bot, _ = build_bot(args.bot, seed=args.seed)
    opponent, opponent_elo = build_bot(args.opponent, seed=args.seed + 1000)

    try:
        result = play_match(
            bot,
            opponent,
            n_games=args.games,
            opening_plies=args.opening_plies,
            seed=args.seed,
        )
    finally:
        bot.close()
        opponent.close()

    estimate = estimate_elo(result.wins, result.draws, result.losses, opponent_elo)

    print()
    print("=" * 72)
    print(result.summary())
    print(estimate.summary())
    print("=" * 72)

    if args.pgn:
        result.save_pgn(args.pgn)
        print(f"Parties enregistrees dans {args.pgn}")


def run_tournament(args: argparse.Namespace) -> None:
    """Tournoi de validation entre baselines : doit donner un classement coherent.

    Attendu : minimax > greedy > random, avec des ecarts nets. Si ce n'est pas
    le cas, il y a un bug dans les bots ou dans le moteur de matchs — et il vaut
    mieux le decouvrir maintenant qu'avec le Transformer.
    """
    pairs = [("greedy", "random"), ("minimax", "random"), ("minimax", "greedy")]

    for bot_spec, opponent_spec in pairs:
        bot, _ = build_bot(bot_spec, seed=args.seed)
        opponent, opponent_elo = build_bot(opponent_spec, seed=args.seed + 1000)
        try:
            result = play_match(bot, opponent, n_games=args.games, seed=args.seed)
        finally:
            bot.close()
            opponent.close()

        estimate = estimate_elo(result.wins, result.draws, result.losses, opponent_elo)
        print(f"  {result.summary()}")
        print(f"    -> {estimate.summary()}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluation d'un bot d'echecs.")
    parser.add_argument("--bot", default="greedy", help="bot a evaluer")
    parser.add_argument("--opponent", default="random", help="adversaire de reference")
    parser.add_argument("--games", type=int, default=100, help="nombre de parties")
    parser.add_argument("--opening-plies", type=int, default=4, help="demi-coups d'ouverture tires au hasard")
    parser.add_argument("--seed", type=int, default=0, help="graine aleatoire (reproductibilite)")
    parser.add_argument("--pgn", default=None, help="fichier ou enregistrer les parties")
    parser.add_argument("--tournament", action="store_true", help="tournoi entre baselines")

    args = parser.parse_args()
    if args.tournament:
        run_tournament(args)
    else:
        run_single(args)


if __name__ == "__main__":
    main()
