"""Conversion d'un score de match en difference d'Elo, avec incertitude.

La formule d'Elo
----------------
L'echelle Elo relie une difference de niveau a un score attendu :

    score_attendu = 1 / (1 + 10 ** (-diff_elo / 400))

Autrement dit : +400 Elo => on marque environ 10 points sur 11. En inversant :

    diff_elo = -400 * log10(1 / score - 1)

Pourquoi l'intervalle de confiance est obligatoire
--------------------------------------------------
Sur 100 parties, un score de 60% peut tres bien venir d'un vrai niveau de 52%
qui a eu de la chance. Annoncer "1515 Elo" sans marge d'erreur est une faute
methodologique que le jury releve immediatement. On annonce donc toujours :

    1515 Elo, IC 95% [1452 ; 1581], sur 100 parties contre Stockfish 1400.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

# Evite les infinis quand le score vaut exactement 0 ou 1.
_EPS = 1e-6


def expected_score(elo_diff: float) -> float:
    """Score attendu (entre 0 et 1) pour une difference d'Elo donnee."""
    return 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))


def elo_diff_from_score(score: float) -> float:
    """Difference d'Elo correspondant a un score observe."""
    clipped = float(np.clip(score, _EPS, 1.0 - _EPS))
    return -400.0 * float(np.log10(1.0 / clipped - 1.0))


def wilson_interval(score: float, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Intervalle de confiance de Wilson sur un score de match.

    Pourquoi Wilson et pas l'intervalle "normal" classique
    ------------------------------------------------------
    L'intervalle classique (Wald) est `score +/- z * ecart_type / sqrt(n)`. Il a
    deux defauts redhibitoires ici :

      - a 100% de victoires, l'ecart-type observe vaut 0, donc l'intervalle est
        [100% ; 100%], donc l'Elo estime est +infini. Absurde : gagner 40
        parties sur 40 ne prouve pas qu'on est infiniment fort.
      - il peut sortir de [0 ; 1] sur de petits echantillons.

    L'intervalle de Wilson corrige les deux : il reste toujours dans [0 ; 1] et
    donne une borne basse finie et sensee meme a 100% (ici : "au moins 91%
    de vrai niveau, donc au moins +400 Elo"). C'est la methode utilisee par les
    outils d'evaluation de moteurs d'echecs.

    Limite a mentionner dans le rapport : Wilson suppose des issues binaires
    (victoire/defaite). Avec des nulles, on l'applique au score moyen, ce qui
    est une approximation legerement conservatrice — donc prudente, ce qui est
    la bonne direction pour une erreur.
    """
    z = float(stats.norm.ppf(0.5 + confidence / 2.0))
    denominator = 1.0 + z**2 / n
    center = (score + z**2 / (2 * n)) / denominator
    half_width = (z / denominator) * float(np.sqrt(score * (1 - score) / n + z**2 / (4 * n**2)))
    low = float(np.clip(center - half_width, _EPS, 1 - _EPS))
    high = float(np.clip(center + half_width, _EPS, 1 - _EPS))
    return low, high


@dataclass
class EloEstimate:
    """Resultat complet d'une campagne de matchs contre un adversaire connu."""

    wins: int
    draws: int
    losses: int
    opponent_elo: float
    score: float
    elo: float
    elo_low: float
    elo_high: float
    confidence: float

    @property
    def games(self) -> int:
        return self.wins + self.draws + self.losses

    @property
    def margin(self) -> float:
        """Demi-largeur de l'intervalle, en points Elo."""
        return (self.elo_high - self.elo_low) / 2.0

    @property
    def is_saturated(self) -> bool:
        """True si le score vaut 0% ou 100% : l'Elo n'est alors pas mesurable.

        Dans ce cas il faut CHANGER D'ADVERSAIRE, pas ajouter des parties : un
        adversaire qu'on ne perd jamais ne donne aucune information sur notre
        niveau reel, seulement une borne.
        """
        return self.score >= 1.0 - _EPS or self.score <= _EPS

    def summary(self) -> str:
        bilan = (
            f"{self.wins}V / {self.draws}N / {self.losses}D sur {self.games} parties  "
            f"(score {self.score:.1%})  ->  "
        )
        if self.is_saturated and self.score > 0.5:
            return (
                bilan + f"Elo > {self.elo_low:.0f} (borne basse, IC {self.confidence:.0%}) "
                f"— adversaire trop faible, en prendre un plus fort"
            )
        if self.is_saturated:
            return (
                bilan + f"Elo < {self.elo_high:.0f} (borne haute, IC {self.confidence:.0%}) "
                f"— adversaire trop fort, en prendre un plus faible"
            )
        return (
            bilan + f"{self.elo:.0f} Elo, IC {self.confidence:.0%} "
            f"[{self.elo_low:.0f} ; {self.elo_high:.0f}] "
            f"vs adversaire {self.opponent_elo:.0f}"
        )


def estimate_elo(
    wins: int,
    draws: int,
    losses: int,
    opponent_elo: float,
    confidence: float = 0.95,
) -> EloEstimate:
    """Estime l'Elo d'un bot a partir de son bilan contre un adversaire connu.

    L'intervalle de confiance est calcule sur le SCORE (approximation normale
    de Wald), puis converti en Elo. On procede dans ce sens et pas l'inverse
    parce que la relation score -> Elo n'est pas lineaire : convertir les bornes
    du score donne un intervalle Elo correctement asymetrique.
    """
    n = wins + draws + losses
    if n == 0:
        raise ValueError("Aucune partie jouee : impossible d'estimer un Elo.")

    outcomes = np.array([1.0] * wins + [0.5] * draws + [0.0] * losses)
    score = float(outcomes.mean())
    low_score, high_score = wilson_interval(score, n, confidence)

    return EloEstimate(
        wins=wins,
        draws=draws,
        losses=losses,
        opponent_elo=opponent_elo,
        score=score,
        elo=opponent_elo + elo_diff_from_score(score),
        elo_low=opponent_elo + elo_diff_from_score(low_score),
        elo_high=opponent_elo + elo_diff_from_score(high_score),
        confidence=confidence,
    )


def games_needed_for_margin(target_margin_elo: float = 50.0) -> int:
    """Nombre approximatif de parties pour atteindre une precision donnee.

    Repere utile pour le rapport : avec un ecart-type de score d'environ 0.45
    (typique quand il y a des nulles), il faut de l'ordre de 300 parties pour
    descendre sous +/- 50 Elo, et environ 1200 pour +/- 25 Elo.
    """
    sigma = 0.45
    z = 1.96
    # Autour de 50% de score, dScore -> dElo vaut environ 400/ln(10) = 173.7.
    slope = 400.0 / np.log(10)
    n = (z * sigma * slope / target_margin_elo) ** 2
    return int(np.ceil(n))
