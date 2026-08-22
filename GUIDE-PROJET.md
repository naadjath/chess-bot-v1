# Chess Bot v1, Guide complet du projet
**Naadjath & Rajaa, Projet de fin de Bachelor, Soutenance le 24 août 2026**

> Ce document est fait pour être lu par les deux membres du binôme. Il explique **ce qu'on nous demande vraiment**, **comment ça marche techniquement**, **ce qu'on construit concrètement**, et **le planning jour par jour**. Si tu lis une section et que tu ne comprends pas, c'est normal : lis-la deux fois, puis va voir la section "Vocabulaire" à la fin.

> **Où on en est réellement (22 août 2026).** Ce guide a été écrit en tout début
> de projet, comme un plan. Depuis, le projet est **terminé** : le modèle est
> entraîné, évalué face à Stockfish, l'application fonctionne, et les 5
> livrables sont prêts dans le dossier `LIVRABLES/`. Certains choix décrits
> ci-dessous comme des options (par exemple Gradio/Streamlit pour
> l'application) ont finalement été tranchés différemment dans le code réel :
> ce guide reste utile pour comprendre le *pourquoi*, mais pour l'état exact du
> projet, se référer à `README.md` et `RAPPORT.md` à la racine du dépôt.

---

## PARTIE 0 : Le décodage de l'énoncé

L'énoncé fait 6 lignes. Voilà ce qu'il y a derrière.

> *"Projet IA visant à concevoir un robot de jeu d'échecs, avec exploration des Transformers et évaluation face à Stockfish."*

Traduction : **on doit entraîner un réseau de neurones (un Transformer) à jouer aux échecs, puis mesurer son niveau en le faisant jouer contre Stockfish.**

Le mot important est **"robot"** = "bot" = un programme qui joue tout seul. Il n'y a **aucun robot physique**, aucune électronique, aucun bras mécanique. C'est un mauvais mot de traduction. On code un joueur automatique.

### La stack donnée trahit le sujet exact

| Outil | À quoi il sert ici |
|---|---|
| `python` | tout le projet |
| `torch` (PyTorch) | construire et entraîner le réseau de neurones |
| `flash-attn` | version optimisée du mécanisme d'attention des Transformers (accélère l'entraînement sur GPU récent) |
| `datasets` (HuggingFace) | charger / stocker des millions de positions d'échecs efficacement |
| `chess` (python-chess) | **la bibliothèque clé** : règles du jeu, coups légaux, lecture de parties PGN, échiquier |
| `stockfish` | le moteur d'échecs de référence, sert d'**adversaire** et de **professeur** |
| `scipy` | statistiques : intervalles de confiance sur le score, calcul d'Elo |
| `tqdm` | barres de progression (confort) |
| `psutil` | surveiller la RAM/CPU pendant l'entraînement (les datasets d'échecs sont énormes) |

Cette combinaison exacte = les dépendances du projet **`searchless_chess` de Google DeepMind**. Le papier associé s'appelle *"Grandmaster-Level Chess Without Search"* (février 2024). **C'est notre papier de référence, il faut le citer dans le rapport.**

### Ce que le prof veut voir, au fond

1. Que vous savez **manipuler un Transformer** avec PyTorch (pas juste appeler une API).
2. Que vous savez **construire un pipeline de données** (des parties brutes → un dataset propre → un modèle).
3. Que vous savez **évaluer scientifiquement** un modèle (pas "il a l'air de bien jouer", mais "1 340 Elo ± 60 sur 200 parties").
4. Que vous savez **livrer** : une appli qui tourne, du code propre, un rapport, une doc.

Le niveau final du bot compte **beaucoup moins** que la rigueur de la démarche. Un bot à 1 200 Elo bien mesuré et bien documenté > un bot à 1 800 Elo dont on ne sait pas d'où il sort.

---

## PARTIE 1 : Comment marche un bot d'échecs (les bases)

### 1.1 Le problème

À chaque tour, le bot reçoit une **position** et doit choisir **un coup parmi les coups légaux** (en moyenne ~30 possibilités). C'est tout. Un bot d'échecs = une fonction :

```
position  →  coup
```

Le reste (savoir quels coups sont légaux, détecter échec et mat, le roque, la prise en passant, la promotion, la nulle par répétition) est **entièrement géré par `python-chess`**. On ne code aucune règle. C'est un énorme soulagement, et c'est important de le dire : la difficulté du projet n'est pas dans les règles du jeu.

```python
import chess

board = chess.Board()          # position de départ
print(board.legal_moves)       # tous les coups légaux
board.push_san("e4")           # jouer un coup
board.is_checkmate()           # échec et mat ?
board.fen()                    # la position sous forme de texte
```

### 1.2 Les deux grandes familles de bots

**Famille A : la recherche (l'approche classique, celle de Stockfish)**
Le bot explore l'arbre des coups : « si je joue ça, il joue ça, alors je joue ça... ». Il descend 20-30 coups de profondeur, évalue les positions finales avec une fonction d'évaluation, et remonte le meilleur choix (algorithme **minimax + élagage alpha-bêta**). Stockfish analyse des dizaines de millions de positions par seconde. C'est de la force brute très optimisée.

**Famille B : le réseau de neurones (notre approche)**
Le bot **regarde la position** et sort directement un coup, comme un humain fort qui joue en blitz à l'instinct. Zéro exploration, zéro arbre. Un seul passage dans le réseau (~5 millisecondes).

**Le pari du projet** : est-ce qu'un Transformer peut jouer correctement **sans chercher** ? Réponse de DeepMind : oui, jusqu'à ~2 900 Elo avec 270M de paramètres et 10M de parties. Nous, avec un modèle 20× plus petit et un mois : on visera **1 200–1 700 Elo**, ce qui est déjà un joueur de club amateur correct.

### 1.3 Pourquoi un Transformer ?

Un Transformer, à la base, sert à traiter des **séquences** (des mots dans une phrase). Son mécanisme central, l'**attention**, permet à chaque élément de la séquence de « regarder » tous les autres et d'en tirer de l'information.

Or une position d'échecs, c'est **64 cases**. On peut la voir comme une séquence de 64 « mots », chaque mot étant le contenu de la case (vide, pion blanc, cavalier noir...). L'attention permet alors naturellement à la case e4 de « regarder » la case h7 et de comprendre qu'il y a une diagonale ouverte. C'est exactement le genre de relation longue distance qu'un réseau convolutif (CNN) capte mal et qu'un Transformer capte bien.

**Phrase à retenir pour la soutenance** : *« On modélise la position comme une séquence de 64 tokens, ce qui permet au mécanisme d'attention de capturer directement les relations à longue portée entre les pièces, diagonales, colonnes, batteries, sans avoir à les coder à la main. »*

---

## PARTIE 2 : L'architecture qu'on va construire

### 2.1 Vue d'ensemble du pipeline

```
   Parties Lichess (PGN)                Stockfish
   ~50 000 parties de joueurs forts     (le "professeur")
              |                              |
              v                              v
        [ 1. EXTRACTION ]  ->  (position FEN, meilleur coup)  x 1 000 000
              |
              v
        [ 2. ENCODAGE ]  ->  64 tokens + 4 tokens de contexte
              |
              v
        [ 3. TRANSFORMER ]  ->  8 couches, d_model=256, ~6M paramètres
              |
              v
        [ 4. TÊTE POLICY ]  ->  probabilité sur ~1968 coups possibles
              |
              v
        [ 5. MASQUAGE ]  ->  on annule les coups illégaux, on prend le max
              |
              v
           LE COUP JOUÉ
              |
              v
   [ 6. ÉVALUATION vs Stockfish ]  ->  Elo ± intervalle de confiance
              |
              v
   [ 7. APPLICATION WEB ]  ->  on joue contre le bot dans le navigateur
```

### 2.2 Étape 1 : Les données

**Source principale : la base ouverte de Lichess** → `https://database.lichess.org/`
Ce sont des dumps mensuels de **toutes** les parties jouées sur Lichess, en PGN compressé. Un mois = ~100 Go décompressé, plusieurs dizaines de millions de parties. **On ne prend pas tout.** On streame le fichier et on s'arrête quand on a ce qu'il faut.

**Filtres à appliquer (à justifier dans le rapport) :**
- Elo des deux joueurs > 2000 → on apprend d'un joueur fort, pas de la moyenne
- Cadence ≥ 5 minutes (pas de bullet) → moins de coups joués à l'arrache
- Partie terminée normalement (pas d'abandon au coup 3)
- On ignore les 8 premiers demi-coups (l'ouverture est de la mémorisation, pas du raisonnement), **optionnel, à tester**

**Ce qu'on extrait** : pour chaque coup joué dans chaque partie, une paire `(position avant le coup, coup joué)`. Une partie ≈ 80 demi-coups → **50 000 parties ≈ 4 millions d'exemples**. Largement suffisant.

**Source secondaire : Stockfish comme professeur.**
Au lieu d'apprendre du coup joué par l'humain (qui fait des erreurs), on peut demander à Stockfish « quel est le meilleur coup ici ? » à profondeur faible (10-12) et apprendre ça. Meilleure qualité, mais **beaucoup plus lent** (~50 ms/position → 1M positions = 14h de CPU). **Stratégie recommandée : faire les deux, et comparer les deux modèles dans le rapport.** C'est exactement le genre d'expérience comparative qui fait la différence à la soutenance.

> **Piège à éviter** : ne pas confondre les données d'entraînement et les données de test. On garde ~2% des parties de côté (`validation set`), jamais vues à l'entraînement, pour mesurer l'accuracy honnêtement.

### 2.3 Étape 2 : L'encodage de la position

Il faut transformer un échiquier en nombres. Voici notre schéma (simple, efficace, facile à expliquer) :

**68 tokens au total :**
- **Tokens 0 à 63** : les 64 cases, de a1 à h8. Chaque case reçoit un entier de 0 à 12 :
  `0` = vide, `1..6` = pion/cavalier/fou/tour/dame/roi **blancs**, `7..12` = les mêmes en **noirs**.
- **Token 64** : trait (0 = aux blancs, 1 = aux noirs)
- **Tokens 65-66** : droits de roque (4 bits encodés)
- **Token 67** : case de prise en passant (0-64)

**Astuce importante, la normalisation de couleur** : on entraîne le modèle à **toujours jouer les blancs**. Quand c'est aux noirs, on retourne l'échiquier (miroir vertical + inversion des couleurs) et on inverse le coup en sortie. Résultat : le modèle n'a qu'un seul point de vue à apprendre → il apprend **deux fois plus vite** avec la même quantité de données. C'est un choix technique à mentionner absolument, ça montre qu'on a réfléchi.

```python
import chess
import numpy as np

PIECE_TO_ID = {
    (chess.PAWN,   True): 1,  (chess.KNIGHT, True): 2,  (chess.BISHOP, True): 3,
    (chess.ROOK,   True): 4,  (chess.QUEEN,  True): 5,  (chess.KING,   True): 6,
    (chess.PAWN,  False): 7,  (chess.KNIGHT,False): 8,  (chess.BISHOP,False): 9,
    (chess.ROOK,  False):10,  (chess.QUEEN, False):11,  (chess.KING,  False):12,
}

def encode_board(board: chess.Board) -> np.ndarray:
    """Transforme une position en un vecteur de 68 entiers.

    On normalise toujours du point de vue du joueur au trait : si c'est aux
    noirs de jouer, on retourne l'echiquier pour que le modele voie toujours
    la meme chose ("je suis les blancs, je joue vers le haut").
    """
    if not board.turn:                    # aux noirs -> on retourne le plateau
        board = board.mirror()

    tokens = np.zeros(68, dtype=np.int64)
    for square, piece in board.piece_map().items():
        tokens[square] = PIECE_TO_ID[(piece.piece_type, piece.color)]

    tokens[64] = 0                        # apres normalisation, toujours "blancs au trait"
    tokens[65] = int(board.has_kingside_castling_rights(chess.WHITE)) \
               + 2 * int(board.has_queenside_castling_rights(chess.WHITE))
    tokens[66] = int(board.has_kingside_castling_rights(chess.BLACK)) \
               + 2 * int(board.has_queenside_castling_rights(chess.BLACK))
    tokens[67] = (board.ep_square + 1) if board.ep_square is not None else 0
    return tokens
```

### 2.4 Étape 3 : Le modèle

Un **Transformer encoder-only** (comme BERT, pas comme GPT : on ne génère pas de texte, on classe).

| Hyperparamètre | Valeur de départ | Pourquoi |
|---|---|---|
| `d_model` (dimension) | 256 | assez pour capturer la position, assez petit pour tenir sur un GPU gratuit |
| `n_layers` | 8 | profondeur raisonnable |
| `n_heads` | 8 | 8 « points de vue » d'attention en parallèle |
| `d_ff` | 1024 | 4 × d_model, standard |
| `dropout` | 0.1 | évite le surapprentissage |
| **Total** | **~6,5 M paramètres** | entraînable en ~4-8 h sur un GPU gratuit Colab/Kaggle |

```python
import torch
import torch.nn as nn

class ChessTransformer(nn.Module):
    """Encodeur Transformer : 68 tokens de position -> distribution sur les coups."""

    def __init__(self, n_moves=1968, d_model=256, n_layers=8, n_heads=8, d_ff=1024):
        super().__init__()
        self.token_emb = nn.Embedding(65, d_model)          # 65 valeurs possibles max par token
        self.pos_emb   = nn.Parameter(torch.zeros(1, 68, d_model))

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_ff,
            dropout=0.1, activation="gelu",
            batch_first=True, norm_first=True,              # pre-norm : entrainement plus stable
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.norm    = nn.LayerNorm(d_model)
        self.head    = nn.Linear(d_model, n_moves)          # la "tete policy"

    def forward(self, tokens):                              # tokens : (B, 68)
        x = self.token_emb(tokens) + self.pos_emb
        x = self.encoder(x)
        x = self.norm(x.mean(dim=1))                        # pooling moyen sur les 68 tokens
        return self.head(x)                                 # (B, 1968) logits bruts
```

**Sur `flash-attn`** : c'est une implémentation ultra-optimisée de l'attention. Elle exige un GPU **Ampere ou plus récent** (A100, RTX 30xx/40xx). Sur un T4 gratuit de Colab, elle ne s'installera pas. **Solution propre** : PyTorch intègre déjà les mêmes noyaux via `torch.nn.functional.scaled_dot_product_attention`, utilisé automatiquement par `nn.TransformerEncoderLayer`. → Dans le rapport, on écrit : *« flash-attn a été évalué mais nécessite une architecture Ampere+ ; nous utilisons l'implémentation équivalente intégrée à PyTorch 2.x (SDPA), qui sélectionne automatiquement le noyau memory-efficient disponible. »* Ça montre qu'on a compris l'outil au lieu de l'installer bêtement.

### 2.5 Étape 4 : La sortie : quel coup jouer ?

Le modèle sort un score pour **chacun des ~1968 coups possibles** au format UCI (`e2e4`, `g1f3`, `e7e8q`...). Ce vocabulaire est fixe : on le construit une fois pour toutes en énumérant tous les couples (case départ, case arrivée) géométriquement possibles + les promotions.

Puis, **le masquage des coups illégaux**, c'est LE détail qui fait qu'un bot neuronal ne triche jamais :

```python
def choose_move(model, board, move_vocab, temperature=0.0):
    """Choisit un coup legal. Le masquage garantit qu'on ne joue jamais illegal."""
    flipped = not board.turn
    tokens = torch.tensor(encode_board(board)).unsqueeze(0)

    with torch.no_grad():
        logits = model(tokens)[0]                    # (1968,)

    mask = torch.full_like(logits, float("-inf"))    # tout interdit par defaut...
    legal = list(board.legal_moves)
    for mv in legal:
        uci = (flip_move(mv) if flipped else mv).uci()
        mask[move_vocab[uci]] = 0.0                  # ...sauf les coups legaux

    scored = logits + mask
    if temperature > 0:                              # un peu d'aleatoire = parties variees
        probs = torch.softmax(scored / temperature, dim=-1)
        idx = torch.multinomial(probs, 1).item()
    else:
        idx = scored.argmax().item()                 # jeu deterministe = jeu le plus fort

    chosen = move_vocab.inv[idx]
    return unflip_move(chess.Move.from_uci(chosen)) if flipped else chess.Move.from_uci(chosen)
```

**Le bot ne peut structurellement pas jouer un coup illégal.** C'est une question de jury classique : *« et s'il propose un coup impossible ? »* → « Impossible par construction : on masque à −∞ tous les indices hors de `board.legal_moves` avant l'argmax. »

### 2.6 L'entraînement

Tâche : **classification multi-classes**. Entrée = position, cible = index du coup joué. Perte = **cross-entropy**. C'est tout, c'est le même entraînement que « classer une image parmi 1968 catégories ».

```
Optimiseur   : AdamW, lr = 3e-4, weight_decay = 0.01
Scheduler    : warmup 1000 pas puis cosine decay
Batch size   : 512 (ou 128 avec accumulation de gradient si la VRAM sature)
Précision    : mixed precision (bf16 / fp16) -> 2x plus rapide
Époques      : 3 à 5 sur ~2M positions
```

**Métriques à suivre pendant l'entraînement** (à mettre en graphique dans le rapport) :
- **loss** train et validation (courbe classique)
- **top-1 accuracy** : le modèle retrouve-t-il exactement le coup joué ? → attendu **35-50 %**
- **top-5 accuracy** : le bon coup est-il dans son top 5 ? → attendu **70-85 %**

**Point crucial à comprendre** : 40 % d'accuracy paraît nul, mais c'est très bon. Dans beaucoup de positions, plusieurs coups sont également bons, le modèle en propose un autre que l'humain, il n'a pas « tort ». **L'accuracy n'est pas la performance de jeu.** La vraie mesure, c'est l'Elo. Cette nuance, dite à la soutenance, montre une vraie maturité.

---

## PARTIE 3 : L'évaluation face à Stockfish (le livrable "ELO approximatif")

C'est le livrable le plus « scientifique » et celui qui est le plus souvent bâclé. Ne le bâclez pas : c'est là que vous gagnez des points.

### 3.1 Régler la force de Stockfish

Stockfish à pleine puissance ≈ 3 600 Elo. Il écraserait notre bot 200-0 et on n'apprendrait **rien** (score 0 % → Elo non calculable). Il faut **le brider** :

```python
engine = chess.engine.SimpleEngine.popen_uci("stockfish")
engine.configure({
    "UCI_LimitStrength": True,
    "UCI_Elo": 1400,          # bridage officiel, minimum 1320 selon les versions
    "Threads": 1,
    "Hash": 16,
})
result = engine.play(board, chess.engine.Limit(time=0.1))
```

Deux méthodes de bridage, à mentionner toutes les deux :
- `UCI_LimitStrength` + `UCI_Elo` → calibré par l'équipe Stockfish, **c'est celle à privilégier**
- `Skill Level` 0→20 → plus grossier, mais utile pour les niveaux très faibles

### 3.2 Le protocole de matchs

```
Pour chaque niveau de Stockfish dans [1320, 1500, 1700, 1900, 2100] :
    jouer 100 parties (50 en blancs, 50 en noirs, alterner strictement !)
    ouverture imposée depuis un livre d'ouvertures varié (sinon 100 parties identiques)
    limite : 200 coups max, puis nulle
    enregistrer chaque partie en PGN (preuve + analyse a posteriori)
```

**Pourquoi alterner les couleurs** : les blancs ont un avantage statistique (~55 %). Sans alternance, la mesure est biaisée. **Pourquoi varier les ouvertures** : deux moteurs déterministes rejouent la même partie 100 fois. On impose donc 3-4 coups d'ouverture tirés d'un livre, ou on met `temperature=0.3` sur le bot.

### 3.3 Le calcul de l'Elo (et l'intervalle de confiance)

Avec un score `S` (entre 0 et 1) sur N parties contre un adversaire d'Elo connu `R_opp` :

```
ΔElo = -400 × log10(1/S − 1)
Elo_bot = R_opp + ΔElo
```

Exemple : 100 parties contre SF-1400, 62 victoires / 8 nulles / 30 défaites → S = (62 + 0.5×8)/100 = 0,66
→ ΔElo = −400 × log10(1/0,66 − 1) = **+115** → **Elo_bot ≈ 1515**

**Mais un chiffre seul ne vaut rien sans son incertitude.** C'est là qu'intervient `scipy` :

```python
import numpy as np
from scipy import stats

def elo_from_score(score):
    score = np.clip(score, 1e-6, 1 - 1e-6)          # evite la division par zero
    return -400.0 * np.log10(1.0 / score - 1.0)

def elo_with_ci(wins, draws, losses, opponent_elo, confidence=0.95):
    """Elo estime + intervalle de confiance (approximation normale de Wald)."""
    n = wins + draws + losses
    score = (wins + 0.5 * draws) / n

    # variance du score par partie (1 = victoire, 0.5 = nulle, 0 = defaite)
    outcomes = np.array([1.0] * wins + [0.5] * draws + [0.0] * losses)
    se = outcomes.std(ddof=1) / np.sqrt(n)

    z = stats.norm.ppf(0.5 + confidence / 2)
    lo, hi = np.clip([score - z * se, score + z * se], 1e-6, 1 - 1e-6)

    return {
        "score":  score,
        "elo":    opponent_elo + elo_from_score(score),
        "elo_lo": opponent_elo + elo_from_score(lo),
        "elo_hi": opponent_elo + elo_from_score(hi),
        "games":  n,
    }
```

**Règle d'or** : ne jamais écrire « notre bot fait 1 515 Elo ». Écrire **« 1 515 Elo, IC 95 % [1 452 ; 1 581], sur 100 parties contre Stockfish bridé à 1 400 »**. Avec 100 parties l'intervalle fait facilement ±70 Elo : c'est normal, il faut le dire et l'assumer.

### 3.4 Les baselines obligatoires

Sans point de comparaison, un chiffre ne veut rien dire. Il faut **au minimum 3 adversaires de référence** :

| Baseline | Elo approximatif | Ce que ça prouve si on la bat |
|---|---|---|
| Bot aléatoire (coup légal au hasard) | ~250 | le modèle a appris quelque chose |
| Bot glouton (prend la pièce la plus chère) | ~600 | il comprend la valeur matérielle |
| Minimax profondeur 2 + éval matérielle | ~1100 | il rivalise avec de la recherche classique |
| Stockfish 1320 / 1500 / 1700 / 1900 | connu | mesure calibrée |

Le tableau final du rapport, avec ces 7 lignes et les intervalles de confiance, **c'est votre meilleure diapo de soutenance.**

---

## PARTIE 4 : Les 5 livrables, décodés

### 1. Application fonctionnelle
Il faut pouvoir **jouer contre le bot devant le jury**. Deux options :

- **Rapide et sûr (recommandé)** : **Gradio** ou **Streamlit**. `python-chess` génère un échiquier en SVG (`chess.svg.board(board)`), on l'affiche, l'utilisateur tape son coup ou clique. ~150 lignes, une journée de travail. Déployable gratuitement sur HuggingFace Spaces → **un lien public à donner au jury, énorme effet.**
- **Plus joli** : **FastAPI** en backend + **chessboard.js** en frontend (drag & drop des pièces). Plus classe, mais 2-3 jours et du JS.

**Fonctionnalités à prévoir** : choisir sa couleur, voir le coup joué par le bot, un bouton « nouvelle partie », l'affichage du top-3 des coups envisagés par le modèle avec leurs probabilités (**très impressionnant**, ça montre l'intérieur du réseau), et un mode « bot vs Stockfish » en spectateur.

### 2. ELO approximatif constaté face à Stockfish
= toute la Partie 3. Livrable concret : un fichier `results/elo_report.md` + les graphiques + les PGN de toutes les parties jouées (preuve de reproductibilité).

### 3. Code source documenté
Structure de repo attendue :

```
chess-bot-v1/
├── README.md                  # installation, usage, resultats en 1 page
├── requirements.txt
├── src/
│   ├── data/
│   │   ├── pgn_parser.py      # PGN -> (fen, coup)
│   │   ├── encoding.py        # position -> 68 tokens
│   │   └── move_vocab.py      # les 1968 coups UCI
│   ├── model/
│   │   └── transformer.py     # ChessTransformer
│   ├── train.py               # boucle d'entrainement
│   ├── engine/
│   │   ├── neural_bot.py      # le bot Transformer
│   │   └── baselines.py       # random, glouton, minimax
│   ├── eval/
│   │   ├── match.py           # organise les matchs
│   │   └── elo.py             # calcul Elo + IC
│   └── app/
│       └── main.py            # l'interface de jeu
├── notebooks/                 # exploration, courbes
├── tests/                     # pytest : encodage, legalite, vocab
├── results/                   # metriques, PGN, figures
└── docs/
```

« Documenté » = **docstrings sur chaque fonction publique** (format Google ou NumPy), **type hints**, un README qui permet à quelqu'un d'autre de tout relancer. Et **Git avec des commits réguliers des deux membres**, le prof regardera l'historique pour vérifier que le binôme a réellement travaillé à deux. Commitez tous les deux, dès le premier jour.

### 4. Rapport
Plan type (25-35 pages) :
1. **Introduction**, contexte, problématique : *« un Transformer peut-il jouer aux échecs sans recherche ? »*
2. **État de l'art**, Deep Blue (1997), AlphaZero (2017), Leela Chess Zero, Stockfish NNUE, **DeepMind searchless chess (2024)**
3. **Méthodologie**, données, encodage, architecture, entraînement. Justifier **chaque** choix.
4. **Expérimentations**, courbes de loss/accuracy, ablations (avec/sans normalisation de couleur, taille de modèle, quantité de données)
5. **Résultats**, le tableau Elo, l'analyse des parties (quelles erreurs typiques ? finales ? tactique ?)
6. **Limites et perspectives**, pas de recherche, faible en finale, données limitées ; pistes : action-value, MCTS léger, plus de données
7. **Conclusion** + **gestion de projet** (répartition binôme, planning, difficultés)
8. **Bibliographie**, le papier DeepMind, Attention Is All You Need, AlphaZero

### 5. Documentation
Distincte du rapport : c'est la doc **technique et utilisateur**. Un dossier `docs/` avec : guide d'installation, guide d'utilisation de l'app, description de l'API interne, comment relancer l'entraînement, comment relancer l'évaluation.

---

## PARTIE 5 : Le planning (22 juillet → 24 août)

**33 jours.** C'est jouable **si on ne se perd pas**. Règle absolue : **avoir un truc qui marche mal très tôt, plutôt qu'un truc parfait jamais fini.**

### Semaine 1 (22–28 juillet), Les fondations
- [ ] Repo Git créé, structure de dossiers, `requirements.txt`, les deux membres poussent un commit **jour 1**
- [ ] Environnement : Python 3.11, PyTorch, python-chess, Stockfish installé et appelable
- [ ] **Milestone bloquant** : un bot **aléatoire** qui joue une partie complète contre Stockfish, et le script d'Elo qui sort un chiffre. Même si c'est 0 %, le pipeline d'évaluation est en place.
- [ ] Télécharger un mois Lichess, écrire le parser PGN, produire **100 000 positions** en fichier
- [ ] Construire le vocabulaire des 1968 coups + les tests unitaires d'encodage/décodage

> Si à la fin de la semaine 1 vous n'avez pas le bot aléatoire qui joue contre Stockfish, **arrêtez tout le reste et faites ça.**

### Semaine 2 (29 juillet – 4 août), Le premier modèle
- [ ] `ChessTransformer` écrit, une passe forward qui tourne sur un batch factice
- [ ] Boucle d'entraînement complète, testée sur 10 000 positions (elle doit **overfitter**, si la loss ne descend pas vers 0 sur un petit jeu, il y a un bug)
- [ ] Entraînement réel sur 1M+ positions (Colab / Kaggle GPU)
- [ ] **Milestone** : le bot neuronal **bat le bot aléatoire à plus de 90 %**
- [ ] Baselines glouton et minimax-2 codées

### Semaine 3 (5–11 août), L'itération
- [ ] Entraînement sur le dataset complet, courbes propres
- [ ] Au moins **2 expériences comparatives** (ex : modèle petit vs grand, données humaines vs annotées Stockfish, avec/sans normalisation de couleur)
- [ ] Campagne d'évaluation complète : ~500 parties, tous les niveaux, PGN sauvegardés
- [ ] **Milestone** : le tableau Elo avec intervalles de confiance existe
- [ ] Démarrer l'application

### Semaine 4 (12–18 août), Livrables
- [ ] Application terminée et déployée (HuggingFace Spaces)
- [ ] Rédaction du rapport (le gros morceau, **commencez avant, écrivez au fil de l'eau**)
- [ ] Documentation, README, docstrings, nettoyage du code
- [ ] Figures finales

### Semaine 5 (19–24 août), Soutenance
- [ ] Diapos (15-20 slides)
- [ ] **Répétition à voix haute, chronométrée, au moins 3 fois**
- [ ] Prépa Q/R (section 7 ci-dessous)
- [ ] Plan B démo : une vidéo de secours de l'appli qui marche, au cas où le wifi lâche. **Toujours.**

---

## PARTIE 6 : Répartition Naadjath / Rajaa

Le principe : **chacune pilote une moitié, mais les deux comprennent tout.** À la soutenance, le jury pose une question sur la partie de l'autre, c'est un classique. Prévoyez un point de synchro de 30 min tous les 2-3 jours où chacune explique ce qu'elle a fait à l'autre.

| Axe A : Données & Modèle | Axe B : Moteur, Éval & Appli |
|---|---|
| Téléchargement + parsing PGN | Wrapper Stockfish (`chess.engine`) |
| Encodage position → tokens | Baselines : aléatoire, glouton, minimax |
| Vocabulaire des coups | Boucle de match + gestion des couleurs/ouvertures |
| Architecture Transformer | Calcul Elo + intervalles (scipy) |
| Boucle d'entraînement | Application de jeu (Gradio/FastAPI) |
| Courbes, ablations | Graphiques de résultats |

**Commun** : rapport, documentation, slides, README. Et **relecture croisée du code de l'autre** (via pull requests si vous voulez faire les choses bien, ça se voit dans l'historique Git et ça impressionne).

---

## PARTIE 7 : Les questions du jury (préparez-les !)

**« Pourquoi un Transformer plutôt qu'un CNN ? »**
→ L'attention capture directement les relations à longue portée entre pièces (diagonales, colonnes, batteries) sans biais de localité. Un CNN doit empiler des couches pour couvrir tout l'échiquier. Et le papier DeepMind 2024 valide l'approche.

**« Votre bot ne fait aucune recherche, ce n'est pas une limite énorme ? »**
→ C'est le sujet même du projet, et c'est un choix assumé : on teste si la connaissance peut remplacer le calcul. Limite réelle : la tactique profonde et les finales, où le modèle joue « à l'intuition » sans vérifier. C'est visible dans nos parties perdues, on l'a analysé. Perspective : un mini-alpha-bêta à profondeur 2-3 sur le top-3 des coups proposés par le réseau (« policy-guided search ») corrigerait l'essentiel.

**« Comment savez-vous que votre Elo est fiable ? »**
→ 500 parties, couleurs alternées, ouvertures variées, intervalles de confiance à 95 % calculés, et cohérence croisée entre plusieurs niveaux d'adversaires. On donne toujours l'intervalle, jamais le chiffre seul.

**« Votre accuracy est de 42 %, c'est faible non ? »**
→ Non : dans beaucoup de positions plusieurs coups sont équivalents. L'accuracy mesure l'imitation, pas la qualité de jeu. Notre top-5 est à 80 %, et surtout la métrique qui compte est l'Elo mesuré en parties réelles.

**« Est-ce qu'il peut jouer un coup illégal ? »**
→ Non, par construction : masquage à −∞ de tous les coups hors de `board.legal_moves` avant l'argmax.

**« Qu'est-ce qui a été le plus dur ? »**
→ Répondez sincèrement et techniquement (le volume de données et la RAM, le débogage silencieux de l'encodage, la calibration de Stockfish...). C'est une question sur votre honnêteté, pas un piège.

**« Qu'est-ce que vous feriez avec 3 mois de plus ? »**
→ Passer à l'action-value comme DeepMind (prédire la probabilité de gain de chaque coup plutôt qu'imiter), annoter tout le dataset avec Stockfish, monter à 50M paramètres, ajouter une recherche légère guidée par la policy, et faire jouer le bot sur Lichess via l'API bot pour obtenir un **Elo officiel** et non plus estimé.

---

## PARTIE 8 : Les pièges qui tuent les projets

1. **Vouloir reproduire DeepMind à l'identique.** Ils avaient 10M de parties, des TPU et 270M de paramètres. On fait une version réduite **et on l'assume dans le rapport**, c'est une force, pas une faiblesse.
2. **Tout coder avant de tester quoi que ce soit.** Faites tourner le pipeline complet avec un modèle nul dès la semaine 1.
3. **Bug silencieux dans l'encodage.** Le modèle apprendra quand même quelque chose et vous ne verrez rien. → **Test unitaire obligatoire** : `decode(encode(board)) == board` sur 10 000 positions aléatoires, et pareil pour les coups (`unflip(flip(move)) == move`).
4. **Oublier la validation.** Sans jeu de validation séparé, vous ne saurez pas si vous surapprenez.
5. **Négliger le rapport jusqu'au 20 août.** Écrivez au fil de l'eau : chaque expérience finie = 1 paragraphe écrit tout de suite.
6. **Saturer la RAM** en chargeant 4M de positions d'un coup. → format `datasets`/parquet avec chargement en streaming, et `psutil` pour surveiller (c'est **exactement** pour ça qu'il est dans la stack).
7. **Ne pas sauvegarder les checkpoints** du modèle. Colab coupe la session au bout de quelques heures. Sauvegardez sur Google Drive à chaque époque.

---

## PARTIE 9 : Vocabulaire

- **PGN** : format texte standard d'une partie (`1. e4 e5 2. Nf3 Nc6...`)
- **FEN** : format texte d'**une position** (`rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`)
- **UCI** : protocole de communication avec un moteur, et notation de coup (`e2e4`)
- **Elo** : échelle de niveau. +400 Elo ≈ on gagne 10 parties sur 11. Débutant ~800, club ~1600, expert ~2000, maître international ~2400, Stockfish ~3600.
- **Token** : une unité d'entrée du Transformer (ici, une case)
- **Embedding** : la conversion d'un token (un entier) en vecteur de nombres réels
- **Attention** : le mécanisme qui permet à chaque token de regarder tous les autres
- **Logits** : les scores bruts en sortie du réseau, avant le softmax
- **Policy** : la fonction position → distribution de probabilité sur les coups
- **Value** : la fonction position → probabilité de gagner
- **Action-value** : (position, coup) → probabilité de gagner (l'approche de DeepMind, la plus performante)
- **Behavioral cloning** : apprendre en imitant les coups d'un expert (notre approche principale)
- **Minimax / alpha-bêta** : l'algorithme de recherche classique
- **NNUE** : le petit réseau qu'utilise Stockfish pour évaluer les positions

---

## Références à citer

1. Ruoss et al., *Grandmaster-Level Chess Without Search*, DeepMind, 2024, **le papier central**
2. Vaswani et al., *Attention Is All You Need*, 2017, le Transformer
3. Silver et al., *Mastering Chess and Shogi by Self-Play (AlphaZero)*, 2017
4. Documentation `python-chess` : https://python-chess.readthedocs.io
5. Base de données Lichess : https://database.lichess.org
6. Documentation Stockfish / protocole UCI

---

*Document rédigé le 22 juillet 2026. À mettre à jour au fil du projet.*
