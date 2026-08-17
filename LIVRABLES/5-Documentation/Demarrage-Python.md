# Démarrage — pour quelqu'un qui n'a jamais fait de Python

**À lire par Naadjath ET Rajaa avant de toucher au code.**
Ce document part de zéro. Aucune connaissance préalable supposée. Si une étape ne marche pas chez toi, c'est une info utile — note l'erreur exacte, elle est presque toujours dans la liste des problèmes courants à la fin.

---

## 1. Le vocabulaire de base, en 3 minutes

Avant d'installer quoi que ce soit, il faut comprendre 6 mots. Ils reviendront tout le temps.

**Le terminal** (aussi appelé console, invite de commandes, PowerShell)
C'est une fenêtre noire où on tape des commandes au clavier au lieu de cliquer. Sur Windows : touche `Windows`, tape `PowerShell`, Entrée. Ça fait peur au début, mais on n'utilise que 4 commandes dans tout le projet :
- `cd chemin` → « va dans ce dossier » (change directory)
- `ls` → « montre-moi ce qu'il y a ici » (list)
- `python fichier.py` → « exécute ce fichier Python »
- `pip install truc` → « installe la bibliothèque truc »

**Python**
Le langage dans lequel on écrit le projet. Un fichier Python porte l'extension `.py`. C'est du texte, rien de plus — tu peux l'ouvrir dans le Bloc-notes. Python *lit* ce texte de haut en bas et exécute les instructions.

**Une bibliothèque** (ou *librairie*, ou *package*, ou *module*)
Du code écrit par d'autres qu'on réutilise au lieu de le réécrire. Exemple : `python-chess` contient déjà toutes les règles des échecs. On ne va pas recoder la prise en passant, quelqu'un l'a fait pour nous et l'a testé pendant 10 ans.

**pip**
Le programme qui installe les bibliothèques. `pip install chess` va chercher `python-chess` sur Internet et l'installe sur ton ordi.

**Un import**
La ligne en haut d'un fichier Python qui dit « j'ai besoin de cette bibliothèque ». Exemple : `import chess`. Sans cet import, écrire `chess.Board()` provoque une erreur.

**Git / GitHub**
Git enregistre l'historique de vos modifications ; GitHub héberge ça en ligne pour que vous travailliez à deux sans vous écraser mutuellement. **Le prof regardera cet historique** pour vérifier que vous avez travaillé toutes les deux — c'est pour ça qu'il faut commiter dès le premier jour, chacune de son côté.

---

## 2. Installation, étape par étape (Windows)

### Étape 2.1 — Vérifier Python

Ouvre PowerShell et tape :

```
python --version
```

**Si tu vois `Python 3.11.x`, `3.12.x`, `3.13.x` ou `3.14.x`** → parfait, passe à l'étape suivante.

**Si tu vois une erreur ou le Microsoft Store qui s'ouvre** → Python n'est pas installé. Va sur https://www.python.org/downloads/ et télécharge **Python 3.12**.

> ⚠️ **L'erreur n° 1 des débutants sous Windows** : pendant l'installation, il y a une petite case en bas du premier écran, **« Add python.exe to PATH »**. **Il faut la cocher.** Si tu l'oublies, le terminal ne trouvera jamais Python et tu passeras deux heures à ne pas comprendre pourquoi.

> 📌 **Pourquoi je recommande 3.12 et pas la toute dernière version** : PyTorch (la bibliothèque du réseau de neurones, dont on aura besoin en semaine 2) met plusieurs mois à supporter chaque nouvelle version de Python. Si `pip install torch` refuse de s'installer en te disant qu'il ne trouve aucune version compatible, c'est ça le problème → installe Python 3.12 en parallèle. Tout le code de la semaine 1 marche sur n'importe quelle version 3.10+.

### Étape 2.2 — Aller dans le dossier du projet

```
cd C:\Users\naadj\chess-bot-v1
```

Remplace le chemin par le tien si le projet est ailleurs. Astuce : dans l'explorateur de fichiers, clique dans la barre d'adresse, copie le chemin, et colle-le après `cd`.

Vérifie que tu es au bon endroit :

```
ls
```

Tu dois voir `src`, `tests`, `scripts`, `README.md`, etc. Si tu ne les vois pas, tu n'es pas dans le bon dossier.

### Étape 2.3 — Créer un environnement virtuel

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**C'est quoi un environnement virtuel ?** Une boîte isolée qui contient les bibliothèques d'UN projet. Sans ça, tous tes projets partagent les mêmes bibliothèques et finissent par se marcher dessus (le projet A veut la version 1.0, le projet B la version 2.0, et rien ne marche plus).

Quand c'est activé, ton terminal affiche `(.venv)` au début de la ligne. **Il faut réactiver l'environnement à chaque fois que tu ouvres un nouveau terminal.**

> 🔧 **Si PowerShell refuse en parlant de « scripts désactivés »** (erreur `UnauthorizedAccess`), tape ceci une seule fois puis réessaie :
> ```
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### Étape 2.4 — Installer les bibliothèques

```
pip install -r requirements.txt
```

`requirements.txt` est la liste des bibliothèques du projet. Cette commande les installe toutes d'un coup. Ça prend 1 à 3 minutes.

### Étape 2.5 — Installer Stockfish

Stockfish n'est **pas** une bibliothèque Python : c'est un programme séparé, un fichier `.exe`.

1. Va sur https://stockfishchess.org/download/
2. Télécharge la version Windows
3. Décompresse l'archive
4. Crée un dossier `bin` dans `chess-bot-v1`, et mets-y le fichier `.exe` renommé en `stockfish.exe`

Résultat attendu : `C:\Users\naadj\chess-bot-v1\bin\stockfish.exe`

Le projet le trouvera tout seul. (Il n'est pas obligatoire pour la semaine 1 : les baselines fonctionnent sans.)

---

## 3. Vérifier que tout marche

Trois commandes, dans l'ordre. **Ne passe à la suivante que si la précédente a réussi.**

### Test 1 — Les tests unitaires

```
python -m pytest tests/ -v
```

Attendu : **14 passed**. Ces tests vérifient que l'encodage des positions ne perd aucune information.

**Pourquoi on commence par ça ?** Parce que c'est le seul bug du projet qui ne fait rien planter. Si l'encodage est faux, le modèle s'entraîne quand même, la courbe descend quand même, et on ne comprend jamais pourquoi le bot joue mal. Ces tests sont notre filet de sécurité.

### Test 2 — Le vocabulaire des coups

```
python -m src.data.move_vocab
```

Attendu : `Taille du vocabulaire : 1968 coups` suivi de quelques exemples.

### Test 3 — Un vrai match

```
python -m scripts.run_match --bot greedy --opponent random --games 40
```

Ça fait jouer 40 parties entre le bot glouton et le bot aléatoire, puis affiche un Elo estimé. Attendu : le glouton gagne largement, autour de 700 Elo.

**Si ces 3 tests passent, votre environnement est bon et le milestone bloquant de la semaine 1 est atteint.** 🎉

---

## 4. Comment le projet est organisé

Tu vas voir plein de dossiers. Voilà à quoi sert chacun, dans l'ordre où on les utilise.

```
chess-bot-v1/
│
├── README.md            <- la vitrine du projet (installation + résultats)
├── GUIDE-PROJET.md      <- le guide complet du sujet (à lire en premier)
├── DEMARRAGE.md         <- ce fichier
├── requirements.txt     <- la liste des bibliothèques à installer
│
├── src/                 <- TOUT le code réutilisable du projet
│   │                       ("src" = source. C'est la convention universelle.)
│   │
│   ├── data/            <- transformer des échecs en nombres
│   │   ├── move_vocab.py    les 1968 coups possibles, numérotés
│   │   └── encoding.py      une position -> 68 nombres
│   │
│   ├── engine/          <- tout ce qui sait JOUER
│   │   ├── base.py          l'interface commune à tous les joueurs
│   │   ├── baselines.py     random, glouton, minimax
│   │   └── stockfish_bot.py le pont vers Stockfish
│   │
│   └── eval/            <- tout ce qui sait MESURER
│       ├── match.py         organiser des parties entre deux bots
│       └── elo.py           convertir un score en Elo + incertitude
│
├── scripts/             <- les programmes qu'on lance à la main
│   └── run_match.py         "fais jouer ce bot et donne-moi son Elo"
│
├── tests/               <- les vérifications automatiques
│   └── test_encoding.py
│
└── tools/               <- petits utilitaires
    └── build_html.py        convertit un .md en page web à envoyer
```

**La règle qui explique cette organisation :**
- `src/` = du code qui **ne fait rien tout seul**, il attend qu'on l'appelle. C'est une boîte à outils.
- `scripts/` = du code qu'on **lance**, qui utilise la boîte à outils pour produire un résultat.

C'est la séparation standard de tout projet Python sérieux, et c'est un des critères sur lesquels le prof vous notera.

---

## 5. Lire du code Python — les 5 choses à savoir

Tu n'as pas besoin de savoir tout écrire, mais il faut savoir **lire** le code du projet pour le défendre à la soutenance.

### 5.1 L'indentation remplace les accolades

En Python, ce qui appartient à un bloc est décalé vers la droite. Il n'y a pas de `{ }`.

```python
if score > 100:          # le ":" annonce un bloc
    print("on est mieux")  # ces 4 espaces disent "je suis DANS le if"
print("toujours affiché")  # revenu à gauche = hors du if
```

**Une indentation fausse = un programme faux.** C'est la source d'erreur n° 1 des débutants.

### 5.2 Une fonction = une machine à transformer

```python
def elo_diff_from_score(score):     # "def" = je définis une fonction
    """Différence d'Elo correspondant à un score observé."""   # <- docstring
    return -400 * log10(1 / score - 1)                          # <- résultat
```

- `def nom(paramètres):` déclare la fonction
- le texte entre `"""` est la **docstring** : la documentation. **C'est ça, « code documenté » dans les livrables.** Chaque fonction du projet en a une.
- `return` renvoie le résultat à celui qui a appelé la fonction

Pour l'utiliser : `elo_diff_from_score(0.66)` → renvoie `115.1`

### 5.3 Une classe = un objet avec une mémoire

Une fonction oublie tout entre deux appels. Une classe se souvient.

```python
class RandomBot(Bot):                      # RandomBot "hérite" de Bot
    def __init__(self, seed=None):         # constructeur : à la création
        self._rng = random.Random(seed)    # self = "moi", cet objet précis

    def select_move(self, board):          # une méthode = fonction de l'objet
        return self._rng.choice(list(board.legal_moves))
```

- `__init__` s'exécute une fois, à la création : `bot = RandomBot(seed=42)`
- `self` désigne l'objet lui-même. Il est toujours le premier paramètre des méthodes.
- `_rng` : le `_` au début signifie « usage interne, ne touchez pas de l'extérieur ». C'est une convention, pas une interdiction technique.

Dans le projet, chaque bot est une classe. `RandomBot`, `GreedyBot`, `MinimaxBot`, `StockfishBot` **ont tous une méthode `select_move`** — c'est ce qui permet au moteur de matchs de les faire s'affronter sans savoir lequel est lequel.

### 5.4 Les imports disent d'où vient chaque chose

```python
import chess                              # toute la bibliothèque
from src.engine.baselines import GreedyBot  # juste une chose précise
```

Le chemin `src.engine.baselines` suit exactement l'arborescence des dossiers : `src/engine/baselines.py`. Les points remplacent les slashs.

### 5.5 Le bloc magique de la fin des fichiers

```python
if __name__ == "__main__":
    main()
```

Traduction : « si ce fichier est **lancé directement**, exécute `main()` ; s'il est seulement **importé** par un autre fichier, ne fais rien ». C'est ce qui permet à un fichier d'être à la fois une boîte à outils et un programme lançable.

---

## 6. Travailler à deux sans se marcher dessus (Git)

### La toute première fois

```
git init
git add .
git commit -m "Initialisation du projet Chess Bot v1"
```

Puis créez un dépôt sur github.com (bouton « New repository », **privé**), et suivez les 2 lignes que GitHub vous affiche pour le relier.

Ensuite, l'autre personne récupère le projet avec :

```
git clone https://github.com/VOTRE-COMPTE/chess-bot-v1.git
```

### Le cycle quotidien — à faire **tous les jours**

```
git pull                              # 1. récupérer le travail de l'autre
                                      # 2. ... coder ...
git add .                             # 3. sélectionner ses modifications
git commit -m "Ajout du calcul d'Elo" # 4. enregistrer avec un message clair
git push                              # 5. envoyer à l'autre
```

**Les 4 règles à respecter :**
1. **`git pull` AVANT de commencer à coder**, toujours. Sinon vous partez d'une version périmée et vous créez des conflits.
2. **Commitez souvent** (plusieurs fois par jour), avec des messages qui décrivent le *quoi* : « Ajout du parser PGN », pas « modif ».
3. **Chacune commite depuis son propre compte.** Le prof regarde l'historique pour vérifier la répartition du travail dans le binôme. C'est un critère de notation.
4. **Ne commitez jamais les gros fichiers** (les PGN de Lichess font des dizaines de Go, les modèles entraînés des centaines de Mo). Le fichier `.gitignore` est déjà configuré pour les exclure.

---

## 7. Problèmes courants et solutions

| Message d'erreur | Ce que ça veut dire | Solution |
|---|---|---|
| `python n'est pas reconnu...` | Python n'est pas dans le PATH | Réinstaller Python en cochant « Add to PATH » |
| `ModuleNotFoundError: No module named 'chess'` | La bibliothèque n'est pas installée **dans l'environnement actif** | Vérifier que `(.venv)` s'affiche, puis `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'src'` | Tu lances le script depuis le mauvais dossier | Se placer à la racine du projet et utiliser `python -m scripts.run_match` (avec `-m`, sans `.py`) |
| `IndentationError` | Mélange d'espaces et de tabulations | Configurer l'éditeur en « 4 espaces », jamais de tabulation |
| `FileNotFoundError: Stockfish est introuvable` | Le `.exe` n'est pas au bon endroit | Le placer dans `chess-bot-v1/bin/stockfish.exe` |
| `UnauthorizedAccess` à l'activation du venv | PowerShell bloque les scripts | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| `pip` ne trouve aucune version de `torch` | Version de Python trop récente | Installer Python 3.12 et recréer le venv avec |
| `MemoryError` pendant la préparation des données | Trop de positions chargées d'un coup | Traiter en flux, par morceaux (voir semaine 2) |

**La méthode universelle face à une erreur Python :** la vraie cause est sur la **DERNIÈRE ligne** du message, pas la première. Python affiche d'abord le chemin par lequel il est passé (la *traceback*), et l'erreur réelle tout en bas. Lis de bas en haut.

---

## 8. Ce qu'il faut avoir fait avant de fermer ce document

- [ ] Python installé, `python --version` répond
- [ ] Environnement virtuel créé et activé (`(.venv)` visible)
- [ ] `pip install -r requirements.txt` passé sans erreur
- [ ] `python -m pytest tests/ -v` → **14 passed**
- [ ] `python -m scripts.run_match --bot greedy --opponent random --games 40` → un Elo s'affiche
- [ ] Git configuré, dépôt GitHub créé, **les deux membres ont poussé au moins un commit**
- [ ] `GUIDE-PROJET.md` lu en entier par les deux

Une fois cette liste cochée, vous n'êtes plus « deux personnes qui n'ont jamais fait de Python » : vous avez un projet qui tourne, testé, versionné. Le reste, c'est de l'ajout de briques sur une base saine.

---

*Prochaine étape : le parser PGN (transformer des parties Lichess en données d'entraînement), puis le Transformer.*
