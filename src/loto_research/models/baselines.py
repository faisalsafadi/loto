"""Baselines (Cahier §23, IMPLEMENTATION_SPEC §32). Ordre imposé : random AVANT frequency ;
aucun autre modèle n'est évalué sans ces deux baselines (IMPLEMENTATION_SPEC §32)."""
import numpy as np

from loto_research.features.build import rolling_frequency_matrix
from loto_research.temporal.autocorrelation import build_presence_matrix
from loto_research.validation.schema import NUMBER_COLUMNS

P_UNIFORM = 6 / 49
FREQUENCY_BASELINE_ALPHA = 10.0  # pseudo-compte pré-enregistré (amendement A9), non ajusté sur les résultats


def random_baseline_predictions(n_draws):
    """p_hat(i,t) = 6/49 pour tout (t,i). Retourne un array (n_draws, 49)."""
    return np.full((n_draws, 49), P_UNIFORM)


def frequency_baseline_predictions(df, alpha=FREQUENCY_BASELINE_ALPHA):
    """p_hat(i,t) = (c_i(t) + alpha*6/49) / (n(t) + alpha), où c_i(t) = nb d'apparitions de i
    STRICTEMENT avant t, n(t) = nb de tirages strictement avant t. Lissage bayésien ancré sur la
    probabilité uniforme 6/49 (alpha pré-enregistré, PAS ajusté sur les résultats — amendement A9).

    Réutilise rolling_frequency_matrix (déjà testée en Phase 8) avec une fenêtre = n_draws, ce qui
    équivaut à un historique complet (start=max(t-n_draws,0)=0 pour tout t).

    Pour t=0 (premier tirage, aucun historique), p_hat = 6/49 pour tous les numéros (cas limite
    correct : alpha*6/49 / alpha = 6/49, identique au random baseline)."""
    d = df.sort_values("chronological_id").reset_index(drop=True)
    presence = build_presence_matrix(d, NUMBER_COLUMNS)
    n_draws = presence.shape[0]
    c_before = rolling_frequency_matrix(presence, windows=[n_draws])[n_draws]
    n_before = np.arange(n_draws).reshape(-1, 1)
    return (c_before + alpha * P_UNIFORM) / (n_before + alpha)
