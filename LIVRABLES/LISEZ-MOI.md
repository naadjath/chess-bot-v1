# Livrables — Chess Bot v1

**Projet de fin de Bachelor — [Prenom NOM] & [Prenom NOM] — 24 aout 2026**

Un Transformer qui apprend a jouer aux echecs *sans recherche*, evalue face a
Stockfish. Ce dossier regroupe l'ensemble des livrables demandes.

**Code source complet et historique du projet en ligne :**
https://github.com/naadjath/chess-bot-v1

---

## Contenu du dossier

### 1-Application
L'application de jeu (on joue contre le bot dans le navigateur, avec affichage
du raisonnement du reseau).
- `code-source.zip` : tout le code du projet.
- Pour lancer : decompresser, puis double-clic sur `Jouer.bat`
  (ou `python -m src.app.server`). Necessite Python 3 et `pip install -r requirements.txt`.

### 2-Modele-entraine
Les poids du Transformer entraine.
- `best.pt` : le modele (Transformer encodeur, 6,86 M de parametres, 4 epoques).
- `history.json` : les metriques d'entrainement (perte, top-1, top-5 par epoque).

### 3-Evaluation-ELO
Le livrable "ELO approximatif constate face a Stockfish".
- `Rapport-ELO.md` : le tableau d'Elo (bot contre baselines et Stockfish),
  avec intervalles de confiance de Wilson a 95 %.
- `parties-PGN/` : toutes les parties jouees, en format PGN (preuve et analyse).
- `journal-evaluation.txt` : la sortie brute de la campagne.

### 4-Rapport
- `Rapport.md` et `Rapport.html` : le rapport complet (9 chapitres).

### 5-Documentation
- `README` : presentation et mode d'emploi du projet.
- `Guide-du-projet` : le sujet explique de A a Z.
- `Demarrage-Python` : installation et prise en main.

### 6-Soutenance
- `Soutenance.pptx` : le diaporama (18 diapos ; le texte a dire est dans les
  notes de chaque diapo).
- `Guide-oral` : le script oral, diapo par diapo.

---

## Resultats en bref

- Entrainement : 1 million de positions Lichess, 4 epoques. Top-1 : 22,7 %.
- Niveau du bot : environ 230-300 Elo (grand debutant).
- Le reseau a appris des principes d'ouverture sans qu'aucune regle ne lui soit
  enseignee.
- Evaluation rigoureuse : couleurs alternees, intervalles de confiance, jeu de
  validation separe.

---

## A completer avant de rendre

- [ ] Remplacer `[Prenom NOM]` par vos noms (ici, dans le rapport, dans les slides).
- [ ] Repartition du binome et planning (rapport, chapitre 8).
- [ ] Inserer la courbe d'entrainement et une capture de l'application dans le rapport et les slides.
