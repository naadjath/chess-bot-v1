# Livrables : Chess Bot v1

**Projet de substitution au stage, SEIBOU Naadjath & LAKRA Rajaa, ECE**  
**Depot le 30 aout 2026, soutenance semaine du 31 aout 2026**

Un Transformer qui apprend a jouer aux echecs sans recherche, evalue face a
Stockfish. Ce dossier regroupe les livrables demandes.

Code source complet et historique du projet en ligne :
https://github.com/naadjath/chess-bot-v1

---

## Contenu du dossier

### 1-Application
`code-source.zip` : le code complet de l'application de jeu et de
l'entrainement. Pour lancer l'application : decompresser l'archive, installer
les dependances (`pip install -r requirements.txt`), puis lancer
`python -m src.app.server`.

### 2-Modele-entraine
`best.pt` : les poids du Transformer entraine (6,86 millions de parametres, 4
epoques sur 1 million de positions). `history.json` : les metriques
d'entrainement.

### 3-Evaluation-ELO
`Rapport-ELO.pdf` : le tableau d'Elo du bot face aux adversaires de reference
et a Stockfish bride, avec intervalles de confiance de Wilson a 95 %.
`parties-PGN/` : les parties jouees pendant la campagne d'evaluation.

### 4-Rapport
`Rapport.pdf` : le rapport complet du projet.

### 5-Documentation
`Documentation.pdf` : presentation du projet, installation et architecture.

### 6-Soutenance
`Soutenance.pdf` et `Soutenance.pptx` : le support de presentation.

---

## Resultats en bref

- Entrainement : 1 million de positions Lichess, 4 epoques. Top-1 : 22,7 %.
- Niveau du bot : environ 230 a 300 Elo.
- Le reseau a appris des principes d'ouverture sans qu'aucune regle ne lui ait
  ete enseignee.
- Evaluation rigoureuse : couleurs alternees, intervalles de confiance, jeu de
  validation separe par partie.
