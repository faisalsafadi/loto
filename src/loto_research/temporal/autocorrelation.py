"""Mémoire temporelle par numéro : autocorrélation lag-1 (Cahier §15/19). EXPLORATOIRE — non
pré-enregistrée avant Phase 1, à traiter comme HYPOTHESES.md POST_HOC si un résultat survit.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm


def lag1_autocorrelation_test(binary_series):
    """Test asymptotique standard de l'autocorrélation d'ordre 1 (Box-Jenkins) : sous H0 (i.i.d.),
    Var(rho_hat) ≈ 1/n, donc z = rho_hat * sqrt(n) suit approximativement une loi normale centrée
    réduite. Valide pour n grand (n≈3155 ici, largement suffisant).
    """
    x = np.asarray(binary_series, dtype=float)
    n = len(x)
    xm = x - x.mean()
    den = float(np.sum(xm ** 2))
    if den == 0:
        return {"n": n, "rho": 0.0, "z": 0.0, "p_value": 1.0}
    rho = float(np.sum(xm[:-1] * xm[1:]) / den)
    z = rho * n ** 0.5
    p_value = float(2 * (1 - norm.cdf(abs(z))))
    return {"n": n, "rho": rho, "z": z, "p_value": p_value}


def build_presence_matrix(df, columns, universe_size=49):
    """Matrice (n_tirages x 49) : 1 si le numéro (index+1) est présent dans le tirage, sinon 0."""
    d = df.sort_values("chronological_id")
    n = len(d)
    presence = np.zeros((n, universe_size), dtype=int)
    for col in columns:
        vals = d[col].to_numpy()
        presence[np.arange(n), vals - 1] = 1
    return presence


def per_number_autocorrelation(df, columns, universe_size=49):
    """Autocorrélation lag-1 pour chacun des `universe_size` numéros, sur sa série de présence/absence."""
    presence = build_presence_matrix(df, columns, universe_size)
    rows = [{"number": i + 1, **lag1_autocorrelation_test(presence[:, i])} for i in range(universe_size)]
    return pd.DataFrame(rows)
