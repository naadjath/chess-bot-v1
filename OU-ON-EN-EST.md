# Où on en est : récapitulatif du projet Chess Bot v1

*Dernière mise à jour : 14 août 2026. À garder sous les yeux pour continuer en autonomie.*

---

## Ce qui est FAIT (les 5 livrables existent)

| Livrable | État | Où c'est |
|---|---|---|
| Application de jeu | | `Jouer.bat` (double-clic) |
| Transformer entraîné | | `checkpoints/best.pt` (aussi sur ton Google Drive) |
| ELO face à Stockfish | | `results/elo_report.md` |
| Code documenté + tests | | tout le dossier `src/`, 32 tests |
| Rapport | brouillon | `RAPPORT.md` |

**Tout est sauvegardé sur GitHub :** https://github.com/naadjath/chess-bot-v1

---

## Les résultats (à connaître pour la soutenance)

- **Entraînement :** 4 époques sur 1 million de positions Lichess. Top-1 finale : **22,7 %**, top-5 : **51,7 %**.
- **Niveau du bot :** environ **230-300 Elo** (grand débutant).
- **Face à Stockfish 1320 :** 0 victoire, 4 nulles, 56 défaites → le bot est plus faible que le Stockfish minimum.
- **Le point fort à mettre en avant :** dans la position de départ, le bot propose des coups d'ouverture **corrects** (Cf3, Cc3, d4, c4) alors qu'on ne lui a jamais appris les règles. Il a appris en observant.
- **La limite à assumer :** le bot joue **passivement**, il fait beaucoup de nulles et ne conclut pas ses parties. Normal pour un petit modèle entraîné peu de temps.

---

## Comment lancer chaque chose

**Jouer / faire la démo :**
- Double-clic sur `Jouer.bat` → l'appli s'ouvre dans le navigateur.
- Pour la démo sans jouer : choisir **« Regarder le bot jouer »** → « Démarrer ». Deux bots s'affrontent, tu commentes.
- Zone **« Coups envisagés »** = l'intérieur du réseau qui s'affiche. C'est LA chose à montrer au jury.

**Relancer l'évaluation Elo (si besoin) :**
```
python -m scripts.evaluate --games 60
```

**Lancer les tests (pour prouver que le code marche) :**
```
python -m pytest tests/ -v
```

---

## Ce qu'il RESTE à faire (léger, faisable sur un modèle basique)

### Pour toi et Rajaa, dans le rapport (`RAPPORT.md`)
Cherche les crochets `[...]` et remplace :
- [ ] **Vos noms** et l'établissement (tout en haut)
- [ ] **La répartition du binôme** (chapitre 8) : qui a fait quoi
- [ ] **Vos difficultés vécues** (chapitre 8)
- [ ] **Le planning** réel du projet

### Figures à insérer dans le rapport
- [ ] La courbe d'entraînement (`courbes_entrainement.png`, sur ton Drive)
- [ ] Une capture de l'appli (l'échiquier + les coups envisagés)

### Soutenance
- [ ] Faire les **slides** (15-20)
- [ ] **Répéter** à voix haute 3 fois
- [ ] Préparer une **vidéo de secours** de la démo (au cas où le wifi lâche)
- [ ] Réviser les **questions du jury** (dans `GUIDE-PROJET.md`, partie 7)

### Pour Rajaa
- [ ] Qu'elle **clone le dépôt** et fasse au moins un commit (le prof regarde l'historique) :
  ```
  git clone https://github.com/naadjath/chess-bot-v1.git
  ```

---

## Les 3 phrases à retenir pour le jury

1. *« On modélise la position comme une séquence de 68 tokens, ce qui permet à l'attention du Transformer de relier directement deux cases éloignées, comme le fait une pièce à longue portée. »*
2. *« Le bot ne peut pas jouer un coup illégal : on masque à −∞ tous les coups hors des coups légaux avant de choisir. »*
3. *« Notre bot est faible, mais mesuré rigoureusement : Elo avec intervalles de confiance de Wilson, couleurs alternées, jeu de validation séparé. La rigueur prime sur la performance. »*

---

## Les fichiers importants

| Fichier | Rôle |
|---|---|
| `GUIDE-PROJET.md` | le sujet expliqué de A à Z |
| `DEMARRAGE.md` | installer Python, lire le code |
| `RAPPORT.md` | le rapport à compléter |
| `OU-ON-EN-EST.md` | ce fichier |
| `POUR RAJAA/` | les versions HTML à envoyer à Rajaa |
| `Jouer.bat` | lance l'appli |

Tout est sur GitHub. Rien ne peut se perdre. 
