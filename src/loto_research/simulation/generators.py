"""Générateurs de tirages simulés (M4). Chaque fonction renvoie un tableau booléen de présence
(reps, n_draws, 49) : True si le numéro est dans le tirage. Tous utilisent un numpy.random.Generator
passé en argument (jamais le générateur global) et tirent exactement 6 numéros distincts par tirage.
"""
import numpy as np
from scipy.optimize import brentq

from loto_research.simulation import bench_config as cfg

K = cfg.K
N_MAX = cfg.N_MAX


def _top_k_presence(keys, k=K):
    """Présence = les k plus petites clés de chaque tirage (dernier axe)."""
    idx = np.argpartition(keys, k - 1, axis=-1)[..., :k]
    x = np.zeros(keys.shape, dtype=bool)
    np.put_along_axis(x, idx, True, axis=-1)
    return x


def inclusion_probability(weight, k=K, n=N_MAX):
    """P(le numéro spécial est tiré) quand il a le poids `weight` et les n-1 autres le poids 1,
    en tirage successif sans remise (course d'exponentielles, équivalent à Plackett-Luce)."""
    j = np.arange(k)
    return float(1.0 - np.prod((n - 1 - j) / (n - 1 - j + weight)))


def weight_for_inclusion(target, k=K, n=N_MAX):
    """Poids à donner au numéro spécial pour que sa probabilité d'apparition soit `target`."""
    if abs(target - k / n) < 1e-15:
        return 1.0
    return float(brentq(lambda w: inclusion_probability(w, k, n) - target, 1e-6, 1e6))


def pair_mixture_q(m, k=K, n=N_MAX):
    """Probabilité de forcer la paire pour que sa fréquence conjointe soit multipliée par m."""
    p2 = k * (k - 1) / (n * (n - 1))
    return (m - 1.0) * p2 / (1.0 - p2)


def gen_null(rng, reps, n_draws):
    return _top_k_presence(rng.random((reps, n_draws, N_MAX)))


def gen_number(rng, reps, n_draws, delta, number=cfg.SPECIAL_NUMBER):
    """Fréquence d'un numéro relevée de `delta` (relatif) : p -> p * (1 + delta)."""
    w = weight_for_inclusion((K / N_MAX) * (1.0 + delta))
    keys = rng.standard_exponential((reps, n_draws, N_MAX))
    keys[:, :, number - 1] /= w
    return _top_k_presence(keys)


def gen_pair(rng, reps, n_draws, m, pair=cfg.SPECIAL_PAIR):
    """Fréquence conjointe de la paire multipliée par m : avec probabilité q le tirage contient la
    paire (+ 4 numéros uniformes), sinon il est uniforme. Les marginales des deux numéros montent
    aussi (inévitable pour tout biais de paire par mélange)."""
    q = pair_mixture_q(m)
    keys = rng.random((reps, n_draws, N_MAX))
    forced = rng.random((reps, n_draws)) < q
    for num in pair:
        keys[:, :, num - 1] = np.where(forced, -1.0, keys[:, :, num - 1])
    return _top_k_presence(keys)


def gen_dependence(rng, reps, n_draws, rho):
    """Chaque numéro du tirage précédent est repris avec probabilité rho ; le reste est complété
    uniformément parmi les numéros non repris."""
    x = np.zeros((reps, n_draws, N_MAX), dtype=bool)
    rows = np.arange(reps)[:, None]
    keys = rng.random((reps, N_MAX))
    prev = np.argpartition(keys, K - 1, axis=1)[:, :K]
    x[rows, 0, prev] = True
    for t in range(1, n_draws):
        keys = rng.random((reps, N_MAX))
        retained = rng.random((reps, K)) < rho
        keys[rows, prev] = np.where(retained, -1.0, keys[rows, prev])
        prev = np.argpartition(keys, K - 1, axis=1)[:, :K]
        x[rows, t, prev] = True
    return x


def gen_rupture(rng, reps, n_draws, delta, number=cfg.SPECIAL_NUMBER):
    """Biais « un numéro » appliqué seulement à la seconde moitié de la série."""
    w = weight_for_inclusion((K / N_MAX) * (1.0 + delta))
    keys = rng.standard_exponential((reps, n_draws, N_MAX))
    keys[:, n_draws // 2:, number - 1] /= w
    return _top_k_presence(keys)


def generate(scenario, level, rng, reps, n_draws):
    if scenario == "null":
        return gen_null(rng, reps, n_draws)
    if scenario == "number":
        return gen_number(rng, reps, n_draws, level)
    if scenario == "pair":
        return gen_pair(rng, reps, n_draws, level)
    if scenario == "dependence":
        return gen_dependence(rng, reps, n_draws, level)
    if scenario == "rupture":
        return gen_rupture(rng, reps, n_draws, level)
    raise ValueError(f"Scénario inconnu : {scenario}")
