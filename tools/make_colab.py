"""Genere le notebook Colab d'entrainement.

Pourquoi generer le notebook plutot que de l'ecrire a la main : un fichier
.ipynb est du JSON, penible a editer et facile a casser. On decrit ici les
cellules en Python, et ce script produit un notebook toujours valide.

    python tools/make_colab.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "notebooks" / "Entrainement_Colab.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip().splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip().splitlines(keepends=True),
    }


CELLS = [
    md("""
# Chess Bot v1 — entraînement du Transformer

**Projet de fin de Bachelor — Naadjath & Rajaa**

Ce notebook entraîne le modèle sur GPU gratuit. Il n'y a rien à installer sur votre
ordinateur : tout se passe sur les serveurs de Google.

## Avant de commencer : activer le GPU

`Exécution` → `Modifier le type d'exécution` → **T4 GPU** → `Enregistrer`.

Sans cette étape, l'entraînement tournerait sur processeur et prendrait des jours
au lieu de quelques dizaines de minutes.

## Déroulé

1. Vérifier le GPU
2. Récupérer le code du projet
3. Installer les dépendances
4. Préparer les données depuis Lichess *(~5 min)*
5. Entraîner le modèle
6. Tracer les courbes
7. Évaluer le bot
8. Récupérer les poids entraînés

> ⚠️ Une session Colab est effacée après ~90 min d'inactivité. Ne fermez pas
> l'onglet pendant l'entraînement, et **téléchargez les poids à la fin** (étape 8).
"""),

    md("## 1. Vérifier le GPU"),
    code("""
import torch, subprocess

print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                      "--format=csv,noheader"], capture_output=True, text=True).stdout or "Aucun GPU detecte")
print(f"PyTorch      : {torch.__version__}")
print(f"CUDA active  : {torch.cuda.is_available()}")

assert torch.cuda.is_available(), (
    "Aucun GPU. Execution > Modifier le type d'execution > T4 GPU, puis relancez cette cellule."
)
print("\\nGPU pret.")
"""),

    md("""
## 2. Récupérer le code

**Option A — depuis GitHub (recommandé).** L'adresse du dépôt est déjà renseignée,
il n'y a rien à modifier : exécutez simplement la cellule.

*(Si vous travaillez sur une copie personnelle du projet, remplacez `REPO_URL`
par l'adresse de votre propre dépôt.)*
"""),
    code("""
REPO_URL = "https://github.com/naadjath/chess-bot-v1.git"

import os, shutil
if os.path.exists("chess-bot-v1"):
    shutil.rmtree("chess-bot-v1")

!git clone --depth 1 {REPO_URL}
%cd chess-bot-v1
!ls
"""),

    md("""
**Option B — envoyer une archive ZIP.** Sur votre PC : clic droit sur le dossier
`chess-bot-v1` → *Envoyer vers* → *Dossier compressé*. Puis exécutez la cellule
ci-dessous et choisissez le fichier.

*(N'exécutez cette cellule que si vous n'avez pas utilisé l'option A.)*
"""),
    code("""
# Cette cellule est DESACTIVEE par defaut : elle ne sert que si vous n'avez pas
# utilise l'option A (git clone). Pour l'activer, passez la valeur a True.
UTILISER_OPTION_B = False

if UTILISER_OPTION_B:
    from google.colab import files
    import zipfile, os, shutil

    uploaded = files.upload()
    name = next(iter(uploaded))

    if os.path.exists("chess-bot-v1"):
        shutil.rmtree("chess-bot-v1")
    with zipfile.ZipFile(name) as archive:
        archive.extractall(".")

    target = "chess-bot-v1" if os.path.isdir("chess-bot-v1") else name.replace(".zip", "")
    os.chdir(target)
    print("Place dans :", os.getcwd())
    print(os.listdir())
else:
    print("Option B ignoree (vous avez utilise l'option A, c'est parfait).")
"""),

    md("## 3. Installer les dépendances"),
    code("""
!pip install -q chess zstandard
print("Installe.")

# On verifie que le projet est correctement importable avant d'aller plus loin.
from src.data.move_vocab import VOCAB_SIZE
from src.model.transformer import ChessTransformer

print(f"Vocabulaire : {VOCAB_SIZE} coups")
print(f"Modele      : {ChessTransformer().num_parameters():,} parametres".replace(",", " "))
"""),

    md("""
## 4. Préparer les données

Les archives Lichess sont **lues en flux** : on ne télécharge que les octets
nécessaires, et la lecture s'arrête dès qu'on a assez de positions. Le disque de
Colab n'est jamais rempli.

### Choisir le mois

La liste complète est sur [database.lichess.org](https://database.lichess.org).
Un mois récent contient beaucoup plus de parties de joueurs forts, donc le filtre
est atteint plus vite.

### Le compromis à comprendre

Le filtre `MIN_ELO` détermine la qualité du professeur imité. Plus il est élevé,
meilleures sont les données — mais moins il y a de parties qui passent, donc plus
la lecture est longue. Sur nos mesures, à Elo ≥ 2000, environ **0,6 %** des parties
sont retenues.
"""),
    code("""
MOIS           = "2024-01"      # voir database.lichess.org
MAX_POSITIONS  = 1_000_000      # 1 M suffit largement pour un modele de 7 M de parametres
MIN_ELO        = 2000           # niveau minimum des DEUX joueurs
MIN_CADENCE    = 180            # secondes : exclut le bullet

URL = f"https://database.lichess.org/standard/lichess_db_standard_rated_{MOIS}.pgn.zst"
print("Source :", URL)

import time
start = time.time()

# Commande volontairement sur UNE seule ligne : les continuations "\\" ne sont
# pas fiables dans les cellules shell de Colab.
!python -m scripts.prepare_data --input {URL} --max-positions {MAX_POSITIONS} --min-elo {MIN_ELO} --min-time-control {MIN_CADENCE} --output data/processed

print(f"\\nPreparation terminee en {(time.time() - start) / 60:.1f} min")
"""),

    md("""
### Vérifier les données avant d'entraîner

Une minute de vérification ici évite des heures d'entraînement sur des données
fausses. On reconstruit quelques positions à partir des nombres stockés et on
vérifie que le coup enregistré comme « bonne réponse » y est bien jouable.
"""),
    code("""
import json, chess
from src.data.encoding import decode_board
from src.data.move_vocab import VOCAB
from src.data.pgn_parser import load_split

metadata = json.load(open("data/processed/metadata.json", encoding="utf-8"))
print(json.dumps(metadata, indent=2, ensure_ascii=False))

tokens, labels = load_split("data/processed", "train")
print(f"\\nEntrainement : {len(labels):,} positions".replace(",", " "))

for index in (0, len(labels) // 3, len(labels) // 2, len(labels) - 1):
    board = decode_board(tokens[index])
    move = VOCAB.move_at(int(labels[index]))
    assert move in board.legal_moves, "PROBLEME : coup illegal dans sa propre position"
    print(f"  position {index:>8} -> coup {board.san(move):<7} OK")

print("\\nToutes les verifications passent : les donnees sont coherentes.")
"""),

    md("""
### À quoi ressemble une position du dataset ?

Utile pour le rapport : une figure vaut mieux qu'un paragraphe.
"""),
    code("""
import chess.svg
from IPython.display import display, HTML

# Echiquier en noir et blanc, comme un vrai jeu et comme notre application.
# Par defaut, python-chess dessine un plateau marron ; on impose notre palette.
ECHIQUIER_NB = {
    "square light": "#f0f0f0",          # cases claires
    "square dark": "#595959",           # cases foncees
    "square light lastmove": "#f0f0f0",
    "square dark lastmove": "#595959",
    "margin": "#ffffff",
    "coord": "#000000",
    "arrow green": "#b8536e",           # la fleche du coup, en rose
}

index = 12345
board = decode_board(tokens[index])
move = VOCAB.move_at(int(labels[index]))

print(f"Le joueur au trait a joue : {board.san(move)}")
display(HTML(chess.svg.board(
    board,
    arrows=[(move.from_square, move.to_square)],
    colors=ECHIQUIER_NB,
    size=340,
)))
"""),

    md("""
## 5. Entraîner

Le modèle par défaut fait **6,9 M de paramètres**. Sur un T4, comptez quelques
dizaines de minutes pour 4 époques sur 1 million de positions — la cellule
affiche le temps réel.

### Sécurité : sauvegarde sur votre Google Drive

Colab gratuit peut se **déconnecter à tout moment**, et tout ce qui est stocké sur
la machine est alors perdu. Pour ne jamais perdre le modèle, on l'enregistre
directement sur votre Google Drive, **à chaque époque**. Même si la session est
coupée, le meilleur modèle obtenu jusque-là reste sauvegardé.

> Au lancement, une fenêtre vous demandera d'autoriser l'accès à votre Drive :
> choisissez votre compte Google et cliquez sur *Autoriser*. C'est sûr — c'est
> votre propre Drive.

### Interpréter les chiffres pendant l'entraînement

- La perte part de **≈ 7,6** (= ln 1968, le hasard pur) et doit descendre.
- La **top-1** monte typiquement vers 35–50 %. **Ce n'est pas un mauvais score** :
  dans beaucoup de positions plusieurs coups sont équivalents, le modèle en
  propose un autre que l'humain sans avoir tort.
- La **top-5** monte vers 70–85 %.

La top-1 mesure l'**imitation**, pas la qualité de jeu. La seule mesure qui compte
vraiment est l'Elo constaté en parties réelles (étape 7).
"""),
    code("""
EPOQUES    = 4
BATCH      = 512
D_MODEL    = 256
COUCHES    = 8
TETES      = 8

# On branche Google Drive et on y enregistre les poids : ainsi, meme si Colab
# se deconnecte, le modele entraine survit et se retrouve dans votre Drive.
from google.colab import drive
drive.mount("/content/drive")

import os
DOSSIER_POIDS = "/content/drive/MyDrive/chess-bot-v1/checkpoints"
os.makedirs(DOSSIER_POIDS, exist_ok=True)
print("Les poids seront sauvegardes dans :", DOSSIER_POIDS)

import time
start = time.time()

!python -m scripts.train --epochs {EPOQUES} --batch-size {BATCH} --d-model {D_MODEL} --layers {COUCHES} --heads {TETES} --eval-every 200 --device cuda --output "{DOSSIER_POIDS}"

print(f"\\nEntrainement termine en {(time.time() - start) / 60:.1f} min")
print("Modele sauvegarde sur votre Drive — il ne sera pas perdu meme en cas de deconnexion.")
"""),

    md("""
## 6. Les courbes

Ces trois graphiques ont vocation à figurer directement dans le rapport.

**Ce qu'il faut y lire :** si la perte de validation remonte alors que celle
d'entraînement continue de descendre, c'est du **surapprentissage** — le modèle
mémorise au lieu de généraliser. Il faut alors plus de données, plus de dropout,
ou moins d'époques.
"""),
    code("""
import json, os
import matplotlib.pyplot as plt

os.makedirs("results", exist_ok=True)
# L'historique a ete sauvegarde sur le Drive, a cote des poids.
history = json.load(open(f"{DOSSIER_POIDS}/history.json", encoding="utf-8"))

fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))

axes[0].plot(history["steps"], history["train_loss"], label="entrainement")
axes[0].plot(history["steps"], history["val_loss"], label="validation")
axes[0].axhline(7.58, ls="--", c="gray", lw=1, label="hasard (ln 1968)")
axes[0].set_title("Perte")
axes[0].set_xlabel("pas d'optimisation")
axes[0].legend()

axes[1].plot(history["steps"], [v * 100 for v in history["val_top1"]], c="#b8536e")
axes[1].set_title("Exactitude top-1 (validation)")
axes[1].set_xlabel("pas d'optimisation")
axes[1].set_ylabel("%")

axes[2].plot(history["steps"], [v * 100 for v in history["val_top5"]], c="#1d3049")
axes[2].set_title("Exactitude top-5 (validation)")
axes[2].set_xlabel("pas d'optimisation")
axes[2].set_ylabel("%")

for ax in axes:
    ax.grid(alpha=.25)
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
# La figure va sur le Drive elle aussi, pour le rapport.
plt.savefig(f"{DOSSIER_POIDS}/courbes_entrainement.png", dpi=160, bbox_inches="tight")
plt.savefig("results/courbes_entrainement.png", dpi=160, bbox_inches="tight")
plt.show()

print(f"Meilleure top-1 : {max(history['val_top1']):.1%}")
print(f"Meilleure top-5 : {max(history['val_top5']):.1%}")
"""),

    md("""
## 7. Évaluer le bot entraîné

Premier verdict : le Transformer bat-il les bots de référence ? S'il ne bat pas
le bot **aléatoire**, c'est qu'il n'a rien appris et il faut chercher le problème
avant d'aller plus loin.

*(L'évaluation complète face à Stockfish se fait sur votre PC, avec l'exécutable
Stockfish installé — voir le README.)*
"""),
    code("""
!mkdir -p results

MODELE = f"neural:{DOSSIER_POIDS}/best.pt"
for adversaire in ["random", "greedy", "minimax:2"]:
    print(f"\\n{'=' * 66}")
    !python -m scripts.run_match --bot "{MODELE}" --opponent {adversaire} --games 40 --seed 1
"""),

    md("""
### Regarder le modèle réfléchir

On affiche les coups auxquels le réseau pense dans la position de départ, avec
leurs probabilités. Un modèle bien entraîné doit proposer des coups d'ouverture
raisonnables (e4, d4, Cf3, c4) — pas a3 ou h4.

C'est une excellente diapositive de soutenance.
"""),
    code("""
import chess
from src.engine.neural_bot import NeuralBot

bot = NeuralBot.from_checkpoint(f"{DOSSIER_POIDS}/best.pt", temperature=0.0)
board = chess.Board()

print("Position de depart — ce que le reseau propose :\\n")
for move, probability in bot.explain(board, top_k=8):
    barre = "#" * int(probability * 60)
    print(f"  {board.san(move):<6} {probability:6.1%}  {barre}")
"""),

    md("""
## 8. Récupérer les poids sur votre PC

**Bonne nouvelle : le modèle est déjà en sécurité sur votre Google Drive**
(dossier `MyDrive/chess-bot-v1/checkpoints`), il ne sera pas perdu.

Cette cellule le télécharge en plus sur votre ordinateur. Une fois téléchargé,
placez `best.pt` dans le dossier `checkpoints/` du projet sur votre PC : le
Transformer apparaîtra alors comme adversaire dans l'application de jeu.
"""),
    code("""
from google.colab import files
import os

for nom in ["best.pt", "history.json", "courbes_entrainement.png"]:
    chemin = f"{DOSSIER_POIDS}/{nom}"
    if os.path.exists(chemin):
        taille = os.path.getsize(chemin) / 1e6
        print(f"Telechargement de {nom} ({taille:.1f} Mo)")
        files.download(chemin)
    else:
        print(f"Absent : {nom}")
"""),

    md("""
---

## Et ensuite ?

1. **Placer `best.pt`** dans `checkpoints/` sur votre PC
2. **Lancer l'application** (`Jouer.bat`) : le Transformer est proposé comme adversaire
3. **Lancer l'évaluation complète** contre Stockfish :
   ```
   python -m scripts.run_match --bot neural --opponent stockfish:1320 --games 100 --pgn results/games/vs_sf1320.pgn
   python -m scripts.run_match --bot neural --opponent stockfish:1500 --games 100 --pgn results/games/vs_sf1500.pgn
   python -m scripts.run_match --bot neural --opponent stockfish:1700 --games 100 --pgn results/games/vs_sf1700.pgn
   ```
4. **Rédiger le rapport** avec les courbes et le tableau d'Elo

### Si les résultats sont décevants

| Symptôme | Cause probable | Remède |
|---|---|---|
| La perte ne descend pas | taux d'apprentissage trop élevé | `--lr 1e-4` |
| Top-1 sous 20 % | pas assez de données ou d'époques | plus de positions, plus d'époques |
| Val remonte, train descend | surapprentissage | plus de données, ou `--dropout 0.2` |
| Le bot perd contre l'aléatoire | bug, pas un souci d'entraînement | relancer `pytest tests/ -v` |
"""),
]


def main() -> None:
    notebook = {
        "cells": CELLS,
        "metadata": {
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
            "accelerator": "GPU",
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")

    code_cells = sum(1 for cell in CELLS if cell["cell_type"] == "code")
    print(f"Notebook ecrit : {OUTPUT}")
    print(f"  {len(CELLS)} cellules ({code_cells} de code)")


if __name__ == "__main__":
    main()
