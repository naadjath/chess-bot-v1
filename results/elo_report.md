# Evaluation Elo du Transformer

Modele : `checkpoints/best.pt`  
Parties par adversaire : 60  
Couleurs alternees, ouvertures variees, intervalles de confiance de Wilson (95 %).

| Adversaire | Elo adv. | V | N | D | Score | Elo estime (IC 95 %) |
|---|---:|---:|---:|---:|---:|---|
| Aleatoire | 250 | 3 | 51 | 6 | 47.5% | 233 [146 ; 320] |
| Glouton | 600 | 0 | 11 | 49 | 9.2% | 202 [54 ; 349] |
| Minimax profondeur 2 | 1100 | 0 | 2 | 58 | 1.7% | 392 [88 ; 695] |
| Minimax profondeur 3 | 1300 | 0 | 2 | 58 | 1.7% | 592 [288 ; 895] |
| Stockfish (bride 1320) | 1320 | 0 | 4 | 56 | 3.3% | 735 [507 ; 963] |

## Synthese

Les affrontements non satures situent le bot entre **202 et 735 Elo**. L'ecart reflete l'imprecision des Elo supposes des baselines, qui ne sont pas calibres officiellement.
