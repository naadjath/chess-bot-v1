# Guide oral : soutenance Chess Bot v1

*Le script complet, diapo par diapo. A imprimer et garder en main.*

**Conseils :**
- Ne lisez pas la diapo au jury : elle est pour lui, ce texte est pour vous.
- Repetez a voix haute au moins 3 fois en chronometrant (visez 12-15 minutes).
- Alternez les diapos entre les deux membres du binome.
- Les passages entre crochets, comme [Prenom] ou [X], sont a personnaliser ou a jouer en direct.

---

## Diapo 1 : Chess Bot v1

> Bonjour. Nous presentons Chess Bot v1 : un reseau de neurones qui choisit un coup d'echecs directement a partir de la position, sans explorer la moindre variante future. C'est cette absence de recherche qui rend le projet interessant, et on va vous montrer ce qu'un petit modele arrive a apprendre, et surtout ses limites. Je suis [X], voici [Y], on se repartit la presentation.

---

## Diapo 2 : La question de depart

> Pour comprendre l'interet du projet, il faut d'abord voir ce qui rend les moteurs d'echecs actuels si forts. Deep Blue, Stockfish, tous cherchent : a chaque coup, ils explorent mentalement des millions de positions futures avant de se decider. C'est de la force brute, tres efficace, mais couteuse en calcul. Nous posons une question differente. Est-ce qu'un reseau de neurones peut jouer correctement sans jamais faire ce travail de recherche, juste en reconnaissant une position comme un joueur humain reconnait un motif familier ? C'est cette question qui guide tout le reste de la presentation.

---

## Diapo 3 : Contexte : les echecs et l'IA

> Petit rappel historique pour situer le projet. En 1997, Deep Blue bat Kasparov grace a une recherche massive et une evaluation ecrite a la main par des experts. En 2017, AlphaZero associe un reseau de neurones a une recherche arborescente, et apprend en jouant contre lui-meme des millions de fois. Aujourd'hui, Stockfish, le moteur le plus fort au monde, combine toujours une recherche tres optimisee et un petit reseau d'evaluation. A chaque fois, le point commun, c'est la recherche. Ce qui change tout en 2024, c'est cet article de DeepMind qui montre qu'un Transformer seul, sans la moindre recherche, peut atteindre un niveau de grand maitre. C'est notre reference directe : on s'inspire de cette demarche, a une echelle beaucoup plus modeste.

---

## Diapo 4 : Notre pari : une version reduite et assumee

> Il faut etre honnete sur l'echelle du projet des le depart. DeepMind travaille avec 270 millions de parametres, 10 millions de parties annotees par Stockfish, et des processeurs specialises TPU. Nous avons un modele 40 fois plus petit, 1 million de positions au lieu de 10, et un unique GPU gratuit accessible depuis un navigateur. La consequence, on l'assume completement : on ne cherche pas a battre Stockfish, et personne ne s'attend a ce qu'on y arrive. Notre objectif est different, et plus modeste : mesurer honnetement ce qu'un petit modele, avec des moyens accessibles a des etudiants, arrive reellement a apprendre, avec la meme rigueur scientifique qu'un vrai laboratoire.

---

## Diapo 5 : Vue d'ensemble

> Voici les quatre etapes de la chaine complete, du fichier de parties brutes jusqu'au coup joue par le bot. Premiere etape : on constitue un million de positions a partir de vraies parties de joueurs forts. Deuxieme etape : chaque position est transformee en 68 nombres, le seul langage que comprend un reseau de neurones. Troisieme etape, le coeur du projet : le Transformer regarde ces 68 nombres et attribue un score a chacun des 1968 coups possibles. Quatrieme etape : on evalue le resultat en faisant vraiment jouer le bot, et on en tire un score Elo. On va detailler chacune de ces quatre etapes sur les diapos suivantes.

---

## Diapo 6 : Etape 1 : les donnees

> On part de l'archive publique de Lichess de janvier 2024, lue directement en flux depuis internet : on ne telecharge jamais le fichier complet sur le disque, on s'arrete des qu'on a assez de positions. Sur 186 057 parties lues, on n'en garde que 14 456, moins de 8 pourcent. Pourquoi si peu ? On filtre sur l'Elo des deux joueurs, au moins 2000, sur la cadence, pour exclure le bullet ou l'on joue au reflexe sans reflechir, et sur les huit premiers coups de chaque partie, qui relevent surtout de la memorisation d'ouvertures plutot que de la reflexion. Un dernier point technique important : on separe l'entrainement et la validation PAR PARTIE, jamais par position isolee. Deux positions issues de la meme partie se ressemblent enormement ; les melanger aurait fausse notre mesure en laissant le modele etre evalue sur des situations presque deja vues.

---

## Diapo 7 : Etape 2 : encoder une position

> Un reseau de neurones ne comprend que des nombres, jamais un plateau. On transforme donc chaque position en 68 tokens : les 64 premiers decrivent le contenu de chaque case, zero pour une case vide, un a six pour les pieces du joueur au trait, sept a douze pour les pieces adverses. Les quatre derniers tokens portent le trait, les droits de roque et la prise en passant. Le detail le plus important a expliquer au jury : on retourne systematiquement l'echiquier pour que le modele voie toujours la position du point de vue du joueur qui doit jouer, comme s'il jouait toujours les blancs. Sans cette astuce, il faudrait apprendre deux fois la meme chose, une fois pour les blancs et une fois pour les noirs. Avec elle, chaque partie fournit deux fois plus d'exemples utiles.

---

## Diapo 8 : Etape 3 : le modele

> Voici le coeur du projet. Les 68 tokens entrent dans un Transformer encodeur, huit couches empilees, chacune avec huit tetes d'attention. Pourquoi un Transformer plutot qu'un reseau plus classique comme un CNN ? Parce que son mecanisme d'attention relie directement n'importe quelle case a n'importe quelle autre case, en une seule etape. C'est exactement le comportement d'une tour ou d'un fou, qui agissent a distance, alors qu'un reseau convolutif classique ne regarde d'abord que les cases voisines. En sortie, le modele produit un score pour chacun des 1968 coups possibles : c'est un probleme de classification, comme reconnaitre une image, sauf qu'ici on classe une position parmi 1968 categories de coup. Au total, 6 858 416 parametres, ce qui reste tres modeste face aux modeles de DeepMind.

---

## Diapo 9 : Choisir un coup legal

> Question que le jury pose presque toujours : est-ce que le bot peut proposer un coup impossible ? La reponse est non, et c'est garanti par construction, pas par une verification a posteriori. Le reseau calcule un score pour les 1968 coups du vocabulaire, y compris ceux qui n'ont aucun sens dans la position actuelle. Avant de choisir, on repere tous les coups illegaux dans cette position precise, et on remplace leur score par moins l'infini. Un score de moins l'infini ne peut mathematiquement jamais etre le plus grand : le coup illegal est donc ecarte de facon absolue, quelle que soit la position, sans exception possible.

---

## Diapo 10 : L'entrainement

> Voici les courbes reelles de notre entrainement, pas des chiffres illustratifs. A gauche, la perte : elle part de 7,6, qui correspond au hasard pur sur 1968 coups possibles, c'est le logarithme de 1968, et descend a 3,08 apres 4 epoques. Au milieu, la top-1 : la capacite du modele a retrouver exactement le coup joue par l'humain. Elle atteint 22,7 % en fin d'entrainement. A droite, la top-5 : le bon coup est dans les 5 premieres propositions du modele 51,7 % du temps. Point important a expliquer au jury si la question vient : 22 % n'est pas un mauvais score, car dans beaucoup de positions plusieurs coups se valent. Cette mesure evalue l'imitation, pas la force de jeu reelle, c'est pour ca qu'on mesure aussi l'Elo par de vraies parties, sur la diapo suivante. Chaque epoque prend 8 a 9 minutes sur le GPU gratuit.

---

## Diapo 11 : Il a appris les ouvertures

> C'est le resultat le plus parlant du projet, celui qu'on garde pour la fin de la partie technique. Si on demande au reseau ce qu'il joue au tout premier coup, avant meme d'avoir vu un seul coup de la partie, il repond d3, developper le cavalier en c3 ou en f3, jouer d4 ou c4. Ce sont exactement les principes qu'on enseigne a un debutant : sortir ses pieces, prendre le centre. Et voici le point cle : le modele n'a jamais recu une seule regle des echecs, ni comment une piece se deplace, ni ce qu'est un echec et mat. Il a uniquement regarde des parties de joueurs forts et en a deduit ces principes tout seul. C'est la preuve concrete qu'il a appris quelque chose de reel, et pas seulement memorise des positions par coeur.

---

## Diapo 12 : Le niveau mesure en parties reelles

> Deuxieme resultat, et le plus important pour juger honnetement le projet : le niveau reel, mesure en faisant vraiment jouer le bot, pas en extrapolant depuis la top-1. On l'a fait affronter une echelle d'adversaires de force croissante, 60 parties chacun, avec un intervalle de confiance calcule par la methode de Wilson : on ne donne jamais un chiffre seul, toujours une fourchette. Contre l'adversaire aleatoire, le bot obtient 47,5 %, un score statistiquement equivalent au hasard, autour de 230 Elo. Contre tous les adversaires plus structures, il perd presque systematiquement. Face a Stockfish bride a 1320, le reglage le plus faible que Stockfish accepte, il ne gagne aucune partie sur les 60 jouees. Notre verdict honnete : le bot se situe autour de 250 a 300 Elo, un niveau de tout premier debutant. On prefere assumer ce resultat plutot que de le maquiller.

---

## Diapo 13 : Analyse : ce que ca revele

> Que retenir de ces deux resultats mis cote a cote ? Il y a une vraie force : la connaissance des principes de base, developpement des pieces, occupation du centre, acquise sans la moindre regle explicite. Mais il y a aussi une faiblesse nette : un jeu passif. Cinquante et une nulles sur soixante parties contre l'aleatoire, c'est enorme. Le bot atteint souvent des positions gagnantes, mais il ne sait pas les convertir, il tourne en rond jusqu'a la regle des 50 coups ou la triple repetition. Notre interpretation : sans recherche, le modele reconnait des schemas mais ne verifie jamais une suite de coups a l'avance. Il sait QUOI faire au debut, pas COMMENT finir. Et les courbes montraient encore une progression a la quatrieme epoque, donc un entrainement plus long aurait probablement attenue ce probleme.

---

## Diapo 14 : L'application

> On a aussi construit une application de jeu complete, dans le navigateur, sans aucune dependance a installer. Deux facons de l'utiliser : le mode Jouer, ou on affronte directement le Transformer ou n'importe quel bot de reference, et le mode spectateur, ou deux bots s'affrontent tout seuls pendant qu'on regarde et qu'on commente, pratique pour une demonstration sans risquer de se tromper de coup en direct. Le detail le plus interessant : a chaque coup joue, les probabilites reellement calculees par le reseau s'affichent a l'ecran. On ne voit pas juste le resultat, on voit litteralement le modele hesiter entre plusieurs coups en temps reel. [Montrer une courte demonstration ici si possible.]

---

## Diapo 15 : Limites et perspectives

> Avec plus de temps, quatre pistes concretes permettraient d'ameliorer le bot. D'abord, changer d'objectif d'entrainement : predire la probabilite de gagner de chaque coup, comme fait DeepMind, plutot que d'imiter simplement le coup joue par l'humain. Ensuite, faire annoter nos donnees par Stockfish, pour apprendre du meilleur coup possible et pas seulement de celui qu'un humain a choisi, qui peut etre imparfait. Troisieme piste : ajouter une petite recherche, profondeur 2 ou 3, guidee par les propositions du reseau, ce qui corrigerait probablement l'essentiel des erreurs tactiques que le bot commet actuellement. Et enfin, tout simplement entrainer plus longtemps : nos courbes montaient encore a la fin, la limite venait des deconnexions de l'environnement gratuit, pas d'un plafond du modele.

---

## Diapo 16 : Gestion de projet

> Un mot sur l'organisation du binome. On s'est reparti le travail en deux axes clairs : [Prenom] a pris en charge les donnees et le modele, extraction, filtrage, encodage, architecture et entrainement du Transformer. [Prenom] s'est occupe de l'evaluation et de l'application, les moteurs de reference, le calcul d'Elo, la campagne contre Stockfish et l'interface de jeu. Le tout est versionne sur Git, avec un historique de commits qui retrace la progression. On a rencontre de vraies difficultes techniques, pas seulement conceptuelles : la lecture des donnees etait au depart 18 fois trop lente, corrigee en changeant de strategie de filtrage ; le calcul d'Elo donnait un resultat infini a 100 % de victoires, corrige avec la methode de Wilson ; et l'environnement Colab gratuit se deconnectait regulierement, ce qu'on a contourne en sauvegardant le modele sur Google Drive a chaque epoque.

---

## Diapo 17 : Conclusion

> Pour conclure. Nous avons montre qu'un Transformer, meme modeste, apprend a jouer aux echecs sans jamais explorer une seule variante future, juste en observant des parties d'un bon niveau. Le niveau atteint reste faible, autour de 250 Elo, mais il est reel : le modele a correctement acquis des principes d'ouverture, meme si sa fin de partie reste fragile. Surtout, la demarche est complete et rigoureuse du debut a la fin : chaine de traitement reproductible, encodage verifie par des tests automatiques, evaluation toujours accompagnee d'un intervalle de confiance. Le point que nous voulons que vous reteniez : ce projet illustre concretement la difference entre la connaissance, ce que le reseau a memorise en observant, et le calcul, la recherche qu'on a volontairement retiree. C'est cette absence de calcul qui explique a la fois ce que le modele reussit et ce qu'il rate.

---

## Diapo 18 : Merci

> Merci de votre attention, nous sommes prets pour vos questions. (Reponses preparees : pourquoi un Transformer plutot qu'un reseau convolutif : l'attention relie directement deux cases eloignees, utile pour une piece a longue portee. Comment on garantit qu'aucun coup illegal n'est joue : masquage a moins l'infini avant le choix du maximum. Pourquoi l'Elo varie autant selon l'adversaire : les Elo des baselines sont des ordres de grandeur admis, pas des valeurs calibrees officiellement.)

---
