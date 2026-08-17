"""Genere les images utilisees dans la presentation de soutenance.

Trois images produites a partir des VRAIES donnees du projet (pas de valeurs
inventees) :

  courbes_entrainement.png  — perte + top-1 + top-5 sur les 4 epoques reelles
  elo_resultats.png         — barres d'Elo avec intervalles de confiance,
                               a partir de results/elo_report.md
  ouverture_echiquier.png   — la position de depart + les coups proposes par
                               le reseau avec leurs probabilites reelles

Palette identique a l'application : encre / blanc casse / rose poudre.

    python tools/make_slide_assets.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "LIVRABLES" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#1C1A1B"
SOFT = "#5D5559"
ROSE = "#B8536E"
ROSE_LIGHT = "#E7C6CE"
LIGHT = "#F1ECEE"
WHITE = "#FFFFFF"
GRID = "#DDD6D9"

plt.rcParams.update({
    "font.family": "Segoe UI, DejaVu Sans",
    "text.color": INK,
    "axes.edgecolor": GRID,
    "axes.labelcolor": SOFT,
    "xtick.color": SOFT,
    "ytick.color": SOFT,
    "figure.facecolor": WHITE,
    "axes.facecolor": WHITE,
})

# Donnees reelles de l'entrainement final (4 epoques, 1M positions, GPU T4).
# Documentees dans RAPPORT.md, issues du journal Colab.
EPOCHS = [1, 2, 3, 4]
VAL_LOSS = [3.953, 3.391, 3.138, 3.081]
TOP1 = [12.6, 18.4, 21.9, 22.7]
TOP5 = [35.4, 45.4, 50.5, 51.7]
RANDOM_LOSS = 7.58  # ln(1968), le hasard pur

# Donnees reelles de la campagne d'evaluation (results/elo_report.md).
ELO_ROWS = [
    ("Aleatoire\n(~250 Elo)", 233, 146, 320, 47.5),
    ("Glouton\n(~600 Elo)", 202, 54, 349, 9.2),
    ("Minimax-2\n(~1100 Elo)", 392, 88, 695, 1.7),
    ("Minimax-3\n(~1300 Elo)", 592, 288, 895, 1.7),
    ("Stockfish 1320\n(bride)", 735, 507, 963, 3.3),
]

# Coups proposes par le reseau dans la position de depart (mesure reelle).
OPENING_MOVES = [("d3", 31.9), ("Cc3", 16.8), ("Cf3", 14.3), ("d4", 9.5), ("e3", 8.7), ("c4", 7.6)]


def training_curves() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))

    ax = axes[0]
    ax.plot(EPOCHS, VAL_LOSS, color=ROSE, marker="o", linewidth=2.5, markersize=7, zorder=3)
    ax.axhline(RANDOM_LOSS, color=SOFT, linestyle="--", linewidth=1.2, alpha=.6)
    ax.text(1, RANDOM_LOSS + 0.15, "hasard pur (ln 1968)", fontsize=9, color=SOFT)
    ax.set_title("Perte (validation)", fontsize=13, weight="bold", color=INK)
    ax.set_xlabel("Epoque")
    ax.set_ylim(0, 8.2)

    ax = axes[1]
    ax.plot(EPOCHS, TOP1, color=INK, marker="o", linewidth=2.5, markersize=7)
    ax.fill_between(EPOCHS, TOP1, color=INK, alpha=.06)
    ax.set_title("Exactitude top-1", fontsize=13, weight="bold", color=INK)
    ax.set_xlabel("Epoque")
    ax.set_ylabel("%")
    ax.set_ylim(0, 60)
    for x, y in zip(EPOCHS, TOP1):
        ax.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9, color=INK, weight="bold")

    ax = axes[2]
    ax.plot(EPOCHS, TOP5, color=ROSE, marker="o", linewidth=2.5, markersize=7)
    ax.fill_between(EPOCHS, TOP5, color=ROSE, alpha=.10)
    ax.set_title("Exactitude top-5", fontsize=13, weight="bold", color=INK)
    ax.set_xlabel("Epoque")
    ax.set_ylabel("%")
    ax.set_ylim(0, 60)
    for x, y in zip(EPOCHS, TOP5):
        ax.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9, color=ROSE, weight="bold")

    for ax in axes:
        ax.set_xticks(EPOCHS)
        ax.grid(alpha=.25, linewidth=.6)
        ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    path = OUT / "courbes_entrainement.png"
    plt.savefig(path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close()
    print("Ecrit :", path)


def elo_chart() -> None:
    fig, ax = plt.subplots(figsize=(11, 5.2))

    labels = [r[0] for r in ELO_ROWS]
    elos = [r[1] for r in ELO_ROWS]
    los = [r[1] - r[2] for r in ELO_ROWS]
    his = [r[3] - r[1] for r in ELO_ROWS]
    scores = [r[4] for r in ELO_ROWS]

    y = range(len(ELO_ROWS))
    bars = ax.barh(y, elos, xerr=[los, his], color=ROSE, alpha=.85,
                    error_kw=dict(ecolor=INK, capsize=5, elinewidth=1.4, capthick=1.4),
                    height=0.55, zorder=3)

    # Le texte va APRES la fin de la barre d'erreur (borne haute), jamais dessus.
    highs = [r[3] for r in ELO_ROWS]
    for i, (elo, score, high) in enumerate(zip(elos, scores, highs)):
        ax.text(high + 30, i, f"{elo} Elo  ·  score {score:.1f}%", va="center", fontsize=10.5,
                color=INK, weight="bold")

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("Elo estime (intervalle de confiance de Wilson, 95 %)")
    ax.set_xlim(0, 1350)
    ax.grid(axis="x", alpha=.25, linewidth=.6)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_title("Niveau du Transformer face a l'echelle d'adversaires (60 parties chacun)",
                  fontsize=13, weight="bold", color=INK, pad=14)

    plt.tight_layout()
    path = OUT / "elo_resultats.png"
    plt.savefig(path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close()
    print("Ecrit :", path)


def opening_figure() -> None:
    """Echiquier de depart (a gauche) + barres des coups proposes (a droite)."""
    fig, (ax_board, ax_bars) = plt.subplots(1, 2, figsize=(12, 5.3), gridspec_kw={"width_ratios": [1, 1.1]})

    # --- Echiquier, dessine directement (noir/blanc, comme l'appli) ---
    PIECES_RANK1 = ["♖", "♘", "♗", "♕", "♔", "♗", "♘", "♖"]
    for r in range(8):
        for c in range(8):
            color = LIGHT if (r + c) % 2 == 0 else SOFT
            ax_board.add_patch(Rectangle((c, r), 1, 1, facecolor=color, edgecolor="none"))
    for c in range(8):
        ax_board.text(c + .5, 1.5, "♙", ha="center", va="center", fontsize=22, color=WHITE,
                       path_effects=_stroke())
        ax_board.text(c + .5, 0.5, PIECES_RANK1[c], ha="center", va="center", fontsize=24, color=WHITE,
                       path_effects=_stroke())
        ax_board.text(c + .5, 6.5, "♟", ha="center", va="center", fontsize=22, color=INK)
    PIECES_RANK8 = ["♜", "♞", "♝", "♛", "♚", "♝", "♞", "♜"]
    for c in range(8):
        ax_board.text(c + .5, 7.5, PIECES_RANK8[c], ha="center", va="center", fontsize=24, color=INK)

    # Fleche vers le coup le plus probable : d3 -> case d3 (colonne d=3, rangee 2 -> index 2)
    ax_board.annotate("", xy=(3.5, 2.5), xytext=(3.5, 1.5),
                       arrowprops=dict(arrowstyle="-|>", color=ROSE, lw=3))

    ax_board.set_xlim(0, 8); ax_board.set_ylim(0, 8)
    ax_board.set_aspect("equal")
    ax_board.set_xticks([]); ax_board.set_yticks([])
    for spine in ax_board.spines.values():
        spine.set_visible(False)
    ax_board.set_title("Position de depart", fontsize=13, weight="bold", color=INK, pad=10)

    # --- Barres horizontales des coups proposes ---
    moves = [m for m, _ in OPENING_MOVES][::-1]
    probs = [p for _, p in OPENING_MOVES][::-1]
    colors = [ROSE if i == len(probs) - 1 else ROSE_LIGHT for i in range(len(probs))]
    bars = ax_bars.barh(moves, probs, color=colors, height=0.6, zorder=3)
    for m, p in zip(moves, probs):
        ax_bars.text(p + 0.7, m, f"{p:.1f}%", va="center", fontsize=11, color=INK, weight="bold")
    ax_bars.set_xlim(0, 38)
    ax_bars.set_xlabel("Probabilite donnee par le reseau")
    ax_bars.grid(axis="x", alpha=.25, linewidth=.6)
    ax_bars.spines[["top", "right", "left"]].set_visible(False)
    ax_bars.set_title("Coups envisages par le Transformer", fontsize=13, weight="bold", color=INK, pad=10)

    plt.tight_layout()
    path = OUT / "ouverture_echiquier.png"
    plt.savefig(path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close()
    print("Ecrit :", path)


def _stroke():
    import matplotlib.patheffects as pe
    return [pe.withStroke(linewidth=1.6, foreground=INK)]


if __name__ == "__main__":
    training_curves()
    elo_chart()
    opening_figure()
    print("\nImages pretes dans", OUT)
