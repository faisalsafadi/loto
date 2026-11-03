"""Configuration FIGÉE du banc d'essai M4 (SPEC_V2 §4, jalon M4).

Paramètres validés par l'utilisateur le 2026-10-30, AVANT toute exécution. Toute modification
après lecture de résultats = nouvelle cellule journalisée POST_HOC, jamais un remplacement.
Le hachage de cette configuration est enregistré avec chaque lancement.

PRÉDICTIONS ÉCRITES AVANT EXÉCUTION (2026-10-30, calculs approchés à la main, loi normale) :
 P1. Faux positifs sous H0 : uniformity_global, consecutive_overlap, half_homogeneity proches de 5 % ;
     per_number_holm <= 5 % (test exact discret et Holm : conservateur, probablement 3 à 4,5 %).
 P2. Biais « un numéro », n = 3155 : per_number_holm ~12 % (+10 %), ~80 % (+20 %), ~100 % (+30 %).
     Biais minimal détectable à 80 % ~ 19-20 %, cohérent avec FINAL.md (16 à 20 %).
 P3. Biais « un numéro », n = 500 : per_number_holm < 25 % même à +30 % (80 % non atteint).
 P4. Dépendance, n = 3155 : consecutive_overlap ~100 % à tous les niveaux (SATURATION : les niveaux
     choisis ne permettent pas d'estimer le biais minimal). n = 500 : ~60 à 85 % à rho = 0,02, ~100 % au-delà.
 P5. Biais « paire » : aucun des 4 tests n'est spécifique aux paires. Une paire biaisée relève aussi les
     deux numéros concernés de +4,6 %, +9,3 %, +18,5 % (marginale induite) ; détection attendue faible,
     sauf m = 3 à n = 3155 (de l'ordre de 70 à 85 % via per_number_holm).
 P6. Rupture (seconde moitié seulement) : puissance faible (< 45 %) pour tous les tests, à n = 3155.
"""
import hashlib
import json

K = 6
N_MAX = 49
BASE_SEED = 42
ALPHA = 0.05

SIZES = (500, 3155)
N_REPS_NULL = 1000
N_REPS_BIAS = 200
N_CALIBRATION = 100_000
CHUNK_REPS = 25
CAL_CHUNK_REPS = 20

SPECIAL_NUMBER = 17
SPECIAL_PAIR = (8, 27)

# niveau = hausse relative de la fréquence (number, rupture), multiplicateur de la fréquence
# conjointe (pair), probabilité de reprise de chaque numéro du tirage précédent (dependence)
SCENARIOS = {
    "number": (0.10, 0.20, 0.30),
    "pair": (1.5, 2.0, 3.0),
    "dependence": (0.02, 0.05, 0.10),
    "rupture": (0.20, 0.30),
}

TESTS = ("uniformity_global", "per_number_holm", "consecutive_overlap", "half_homogeneity")
POWER_TARGET = 0.80

CONFIG = {
    "k": K, "n_max": N_MAX, "base_seed": BASE_SEED, "alpha": ALPHA,
    "sizes": list(SIZES), "n_reps_null": N_REPS_NULL, "n_reps_bias": N_REPS_BIAS,
    "n_calibration": N_CALIBRATION, "chunk_reps": CHUNK_REPS, "cal_chunk_reps": CAL_CHUNK_REPS,
    "special_number": SPECIAL_NUMBER, "special_pair": list(SPECIAL_PAIR),
    "scenarios": {k: list(v) for k, v in SCENARIOS.items()},
    "tests": list(TESTS), "power_target": POWER_TARGET,
}


def config_hash():
    return hashlib.sha256(json.dumps(CONFIG, sort_keys=True).encode("utf-8")).hexdigest()
