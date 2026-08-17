# Guide oral : soutenance Chess Bot v1

*Le script complet, diapo par diapo. A imprimer et garder en main.*

**Conseils :**
- Ne lisez pas la diapo au jury : elle est pour lui, ce texte est pour vous.
- Repetez a voix haute au moins 3 fois en chronometrant (visez 12-15 minutes).
- Alternez les diapos entre les deux membres du binome.

---

## Diapo 1 : Chess Bot v1

> Bonjour. Nous presentons Chess Bot v1 : un reseau de neurones qui choisit un coup d'echecs directement a partir de la position, sans explorer la moindre variante future. C'est cette absence de recherche qui rend le projet interessant, et on va vous montrer ce qu'un petit modele arrive a apprendre, et surtout ses limites. Je suis [X], voici [Y], on se repartit la presentation.

---

## Diapo 2 : INTRODUCTION



---

## Diapo 3 : ETAT DE L'ART



---

## Diapo 4 : POSITIONNEMENT



---

## Diapo 5 : COMMENT CA MARCHE



---

## Diapo 6 : DONNEES



---

## Diapo 7 : ENCODAGE



---

## Diapo 8 : ARCHITECTURE



---

## Diapo 9 : ARCHITECTURE



---

## Diapo 10 : ENTRAINEMENT

> Voici les courbes reelles de notre entrainement. A gauche, la perte : elle part de 7,6, qui correspond au hasard pur sur 1968 coups possibles (c'est le logarithme de 1968), et descend a 3,08 apres 4 epoques. Au milieu, la top-1 : la capacite du modele a retrouver exactement le coup joue par l'humain. Elle atteint 22,7 % en fin d'entrainement. A droite, la top-5 : le bon coup est dans les 5 premieres propositions du modele 51,7 % du temps. Point important a expliquer au jury : 22 % n'est pas un mauvais score, car dans beaucoup de positions plusieurs coups sont equivalents. Cette mesure evalue l'IMITATION, pas la force de jeu, c'est pour ca qu'on mesure aussi l'Elo par des vraies parties, sur la diapo suivante. Chaque epoque prend 8 a 9 minutes sur le GPU gratuit.

---

## Diapo 11 : RESULTATS

> C'est le resultat le plus parlant du projet. Si on demande au reseau ce qu'il joue au tout premier coup, avant meme d'avoir vu un seul coup de la partie, il repond d3, developper le cavalier en c3 ou en f3, jouer d4 ou c4. Ce sont exactement les principes qu'on enseigne a un debutant : sortir ses pieces, prendre le centre. Le modele n'a jamais recu une seule regle des echecs, ni comment une piece se deplace, ni ce qu'est un echec et mat. Il a uniquement regarde des parties de joueurs forts et en a deduit ces principes. C'est la preuve concrete qu'il a appris quelque chose de reel, et pas seulement memorise des positions.

---

## Diapo 12 : RESULTATS

> Deuxieme resultat, le plus important pour juger le projet : le niveau reel, mesure en faisant jouer le bot contre une echelle d'adversaires de force croissante, 60 parties chacun, avec un intervalle de confiance calcule par la methode de Wilson : on ne donne jamais un chiffre seul. Contre l'adversaire aleatoire, le bot obtient 47,5 %, un score statistiquement equivalent au hasard, autour de 230 Elo. Contre tous les adversaires plus structures, il perd presque systematiquement. Face a Stockfish bride a 1320, le reglage le plus faible que Stockfish accepte, il ne gagne aucune partie. Notre verdict honnete : le bot se situe autour de 250 a 300 Elo, un niveau de tout premier debutant. On assume ce resultat plutot que de le cacher.

---

## Diapo 13 : DISCUSSION



---

## Diapo 14 : LIVRABLE



---

## Diapo 15 : DISCUSSION



---

## Diapo 16 : ORGANISATION



---

## Diapo 17 : SYNTHESE



---

## Diapo 18 : Merci

> Merci de votre attention, nous sommes prets pour vos questions. (Reponses preparees : pourquoi un Transformer plutot qu'un reseau convolutif : l'attention relie directement deux cases eloignees, utile pour une piece a longue portee. Comment on garantit qu'aucun coup illegal n'est joue : masquage a moins l'infini avant le choix du maximum. Pourquoi l'Elo varie autant selon l'adversaire : les Elo des baselines sont des ordres de grandeur admis, pas des valeurs calibrees officiellement.)

---
