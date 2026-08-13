# Guide oral — soutenance Chess Bot v1

*Ce qu'il faut dire pour chaque diapo. A imprimer et garder en main.*

**Conseils generaux :**
- Parlez lentement, respirez entre les diapos.
- Ne lisez pas la diapo : elle est pour le jury, votre texte est ici.
- Repetez a voix haute au moins 3 fois, en chronometrant (visez 12-15 min).
- Repartissez-vous les diapos a deux, en alternance.

---

## Diapo 1 — Chess Bot v1
*Un Transformer qui joue aux echecs sans recherche*

**A l'ecran :**
- Projet de fin de Bachelor
- [Prenom NOM] & [Prenom NOM]
- [Etablissement] — 24 aout 2026

**A dire :**
> Bonjour. Nous allons vous presenter Chess Bot v1, un projet d'intelligence artificielle qui apprend a un reseau de neurones a jouer aux echecs. La particularite : notre bot ne calcule aucune variante, il choisit son coup directement en regardant la position. Je suis [X], voici [Y], et on se repartit la presentation.

---

## Diapo 2 — La question de depart

**A l'ecran :**
- Les moteurs classiques (Deep Blue, Stockfish) EXPLORENT des millions de positions.
- Notre bot, lui, ne cherche pas : il repond a l'instinct, comme un humain en blitz.
- Question : un Transformer peut-il jouer correctement SANS recherche ?

**A dire :**
> Depuis Deep Blue en 1997, les ordinateurs battent l'humain aux echecs en explorant des millions de positions a chaque coup — c'est de la force brute. Nous, on pose une question differente, inspiree d'un article de DeepMind de 2024 : est-ce qu'un reseau de neurones peut jouer correctement sans jamais explorer l'arbre des coups, juste en reconnaissant les bonnes positions ? C'est tout l'enjeu du projet.

---

## Diapo 3 — Contexte : les echecs et l'IA
*Un demi-siecle d'approches*

**A l'ecran :**
- 1997 — Deep Blue bat Kasparov : recherche alpha-beta massive.
- 2017 — AlphaZero : reseau de neurones + recherche (MCTS).
- 2020+ — Stockfish : alpha-beta + petit reseau d'evaluation.
- 2024 — DeepMind : un Transformer SEUL, sans recherche. Notre reference.

**A dire :**
> Petit tour d'horizon. Toutes les grandes approches ont un point commun : elles cherchent. Deep Blue, AlphaZero, Stockfish, tous explorent des coups futurs. En 2024, DeepMind montre qu'un Transformer seul, sans aucune recherche, peut atteindre un niveau de grand maitre. C'est l'article qui nous sert de reference, et qu'on adapte a notre echelle.

---

## Diapo 4 — Notre pari
*Une version reduite et assumee*

**A l'ecran :**
- DeepMind : 270 millions de parametres, 10 millions de parties, des TPU.
- Nous : 6,9 millions de parametres, 1 million de positions, un GPU gratuit.
- Objectif realiste : mesurer honnetement ce qu'un petit modele peut apprendre.

**A dire :**
> Attention, on ne refait pas DeepMind : eux avaient des moyens colossaux. Nous, on fait une version 40 fois plus petite, avec un GPU gratuit et quelques semaines. Notre objectif n'est pas de battre Stockfish, mais de construire toute la chaine proprement et de mesurer honnetement ce qu'un petit modele arrive a apprendre. La rigueur compte plus que la performance.

---

## Diapo 5 — Vue d'ensemble
*De la partie brute au bot qui joue*

**A l'ecran :**
- 1. Donnees : parties Lichess -> 1 million de positions.
- 2. Encodage : chaque position -> 68 nombres.
- 3. Modele : le Transformer choisit un coup parmi 1968.
- 4. Evaluation : matchs contre Stockfish -> Elo.

**A dire :**
> Voici le plan de la chaine, en quatre etapes. On recupere des parties de joueurs forts, on transforme chaque position en nombres, on entraine le Transformer a choisir un coup, et enfin on mesure son niveau en le faisant jouer contre Stockfish. Je vais detailler chaque etape.

---

## Diapo 6 — Etape 1 — Les donnees
*Apprendre de bons joueurs*

**A l'ecran :**
- Source : base ouverte Lichess (parties reelles).
- Filtres : joueurs > 2000 Elo, pas de bullet, parties terminees.
- Resultat : 1 000 000 de positions en ~5 minutes (lecture en flux).
- Principe : le bot imite les coups d'un joueur fort (clonage comportemental).

**A dire :**
> On part de la base publique de Lichess, qui contient des millions de parties reelles. On ne garde que les parties de joueurs forts, au-dessus de 2000 Elo, pour apprendre de bonnes decisions. On extrait un million de positions en cinq minutes grace a une lecture optimisee. L'idee, c'est le clonage comportemental : le modele apprend a imiter le coup joue par l'expert.

---

## Diapo 7 — Etape 2 — Encoder une position
*Une position = 68 nombres*

**A l'ecran :**
- 64 cases + trait + roques + prise en passant = 68 tokens.
- Chaque case est un mot ; l'attention relie les cases eloignees.
- Astuce : on retourne l'echiquier pour toujours jouer les blancs.
- -> le modele apprend 2 fois plus vite.

**A dire :**
> Un reseau ne comprend que des nombres. On transforme donc chaque position en 68 nombres : le contenu des 64 cases, plus quelques informations comme le trait et les roques. On traite l'echiquier comme une phrase de 68 mots, ce qui permet au mecanisme d'attention du Transformer de relier une case a l'autre bout du plateau. Detail malin : on retourne toujours l'echiquier du point de vue du joueur au trait, donc le modele n'a qu'une seule vue a apprendre, et il apprend deux fois plus vite.

---

## Diapo 8 — Etape 3 — Le modele
*Un Transformer encodeur*

**A l'ecran :**
- 8 couches d'attention, 6,86 millions de parametres.
- Entree : 68 tokens. Sortie : un score pour chacun des 1968 coups possibles.
- C'est une classification : ranger une position parmi 1968 categories.

**A dire :**
> Le coeur du projet : le Transformer. C'est le meme type de reseau que ceux qui traitent le langage, mais adapte aux echecs. Il a huit couches et presque sept millions de parametres. Il prend nos 68 nombres en entree et sort un score pour chacun des 1968 coups concevables. Formellement, c'est un probleme de classification tres classique : ranger une position dans la bonne categorie de coup.

---

## Diapo 9 — Choisir un coup legal
*Le bot ne triche jamais*

**A l'ecran :**
- Le reseau note les 1968 coups possibles.
- On met a -infini tous les coups ILLEGAUX dans la position.
- On garde le meilleur des coups restants.
- => impossible de jouer un coup illegal, par construction.

**A dire :**
> Une question classique du jury : et si le bot propose un coup impossible ? Reponse : c'est impossible par construction. Le reseau note les 1968 coups, mais avant de choisir, on elimine tous ceux qui sont illegaux dans la position en leur donnant un score de moins l'infini. Le bot ne peut donc structurellement jamais tricher.

---

## Diapo 10 — L'entrainement
*4 epoques sur 1 million de positions (GPU gratuit)*

**A l'ecran :**
- La perte descend de 7,6 (hasard) a 3,1.
- Exactitude top-1 : 22,7 % — top-5 : 51,7 %.
- Pas de surapprentissage (validation suivie separement).
- [Inserer ici la figure des courbes]

**A dire :**
> On entraine le modele sur GPU gratuit. La courbe de perte descend regulierement : le modele apprend. A la fin, il retrouve le coup exact du joueur dans 22,7 % des cas, et le bon coup est dans ses cinq premieres propositions une fois sur deux. Point important a comprendre : 22 %, ce n'est pas un mauvais score. Dans beaucoup de positions plusieurs coups se valent, donc le modele peut avoir raison en proposant autre chose que l'humain. Cette exactitude mesure l'imitation, pas la force reelle.

---

## Diapo 11 — Resultat 1 — Il a appris les ouvertures
*Dans la position de depart, le reseau propose :*

**A l'ecran :**
- d3 (32 %) · Cc3 (17 %) · Cf3 (14 %) · d4 (10 %) · c4 (8 %)
- Ce sont de vrais coups d'ouverture : developpement, centre.
- Aucune regle ne lui a ete enseignee — il a appris en observant.

**A dire :**
> Premier resultat, et c'est le plus parlant. Si on demande au reseau ce qu'il propose au tout premier coup, il repond : sortir les cavaliers, occuper le centre. Ce sont exactement les principes d'ouverture qu'on apprend a un debutant. Or on ne lui a JAMAIS explique une seule regle : il a deduit ces principes tout seul, juste en regardant des parties. Ca, c'est la preuve qu'il a vraiment appris quelque chose.

---

## Diapo 12 — Resultat 2 — Le niveau mesure
*60 parties par adversaire, intervalles de confiance a 95 %*

**A l'ecran :**
*(tableau des resultats Elo)*

**A dire :**
> Deuxieme resultat : le niveau reel, mesure en parties. On fait jouer le bot contre une echelle d'adversaires de force croissante, 60 parties chacun, avec des intervalles de confiance. Le verdict est honnete : notre bot tourne autour de 250 a 300 Elo, un niveau de tout debutant. Face a Stockfish, meme a son reglage le plus faible, il perd toutes ses parties. On donne toujours l'intervalle de confiance, jamais un chiffre seul.

---

## Diapo 13 — Analyse : forces et faiblesses

**A l'ecran :**
- + Il connait les principes d'ouverture.
- + Il ne joue jamais de coup illegal.
- - Il joue passivement : beaucoup de nulles, il ne conclut pas.
- - Sans recherche, il rate la tactique et les finales.

**A dire :**
> Qu'est-ce que ca nous apprend ? Le bot sait commencer une partie, mais il ne sait pas la finir : il tourne en rond et fait beaucoup de nulles, meme contre l'aleatoire. C'est logique : sans recherche, il joue a l'intuition et ne verifie jamais un calcul. C'est exactement la limite qu'on voulait etudier : la connaissance ne remplace pas totalement le calcul.

---

## Diapo 14 — L'application
*Jouer contre le bot, et voir dans sa tete*

**A l'ecran :**
- On joue contre le Transformer dans le navigateur.
- Mode spectateur : deux bots s'affrontent, on regarde.
- A chaque coup : les probabilites du reseau s'affichent.
- [Demo en direct ici]

**A dire :**
> On a aussi developpe une application pour jouer contre le bot. Le plus interessant, c'est cette zone qui montre, a chaque coup, les probabilites qui sortent du reseau : on voit litteralement l'interieur du modele reflechir. Je vous fais une courte demonstration. (Lancer le mode spectateur : deux bots jouent, commenter les coups envisages.)

---

## Diapo 15 — Limites et perspectives

**A l'ecran :**
- Passer a l'action-value (probabilite de gain de chaque coup), comme DeepMind.
- Annoter les donnees avec Stockfish : apprendre du meilleur coup, pas du coup humain.
- Ajouter une recherche legere guidee par le reseau.
- Entrainer plus longtemps (un abonnement GPU stable).

**A dire :**
> Avec plus de temps, on voit quatre pistes. Predire la probabilite de gagner de chaque coup plutot que d'imiter, comme DeepMind. Faire annoter nos donnees par Stockfish pour apprendre du meilleur coup. Ajouter une petite recherche guidee par le reseau, qui corrigerait la tactique. Et simplement entrainer plus longtemps, ce que les deconnexions du GPU gratuit nous ont empeche de faire.

---

## Diapo 16 — Gestion de projet
*Un binome, un depot Git*

**A l'ecran :**
- [Prenom] : donnees, encodage, modele, entrainement.
- [Prenom] : moteur, baselines, evaluation, application.
- Commun : rapport, documentation, soutenance.
- Difficultes : debit des donnees, saturation de l'Elo, deconnexions Colab.

**A dire :**
> Cote organisation, on s'est reparti le travail en deux axes : [X] sur les donnees et le modele, [Y] sur l'evaluation et l'application, et on a tout versionne sur Git. On a rencontre de vraies difficultes techniques : la lecture des donnees trop lente qu'on a accelere par vingt, le calcul d'Elo qui saturait a 100 % de victoires qu'on a corrige avec la methode de Wilson, et les deconnexions de Colab qu'on a contournees en sauvegardant sur le Drive.

---

## Diapo 17 — Conclusion

**A l'ecran :**
- Un Transformer apprend a jouer sans recherche, juste en observant.
- Niveau modeste (~250 Elo), mais principes d'ouverture reels.
- Chaine complete, testee, reproductible, mesuree rigoureusement.
- L'essentiel : la difference entre connaissance et calcul.

**A dire :**
> Pour conclure : on a montre qu'un petit Transformer peut apprendre a jouer aux echecs sans aucune recherche, uniquement en observant des parties. Son niveau reste modeste, mais il acquiert de vrais principes, et surtout toute la demarche est rigoureuse et reproductible. Au fond, ce projet illustre la difference entre la connaissance, ce que le reseau a memorise, et le calcul, qu'on a volontairement retire. Merci de votre attention, nous sommes prets pour vos questions.

---

## Diapo 18 — Merci
*Questions ?*

**A l'ecran :**
- github.com/naadjath/chess-bot-v1

**A dire :**
> Merci. (Garder en tete les reponses aux questions frequentes : pourquoi un Transformer plutot qu'un CNN, comment on garantit la fiabilite de l'Elo, est-ce qu'il peut jouer un coup illegal, qu'est-ce qui a ete le plus dur. Elles sont dans le guide du projet, partie 7.)

---
