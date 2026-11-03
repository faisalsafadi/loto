"""Test des suites (runs test, Wald-Wolfowitz) — implémentation directe (Cahier §15, EXPLORATOIRE).

Implémenté à la main plutôt que via statsmodels.sandbox (API incertaine, module non stabilisé) :
la formule est standard et facilement vérifiable à la main sur un petit exemple.
"""
import numpy as np
from scipy.stats import norm


def runs_test(binary_sequence):
    """binary_sequence : séquence de 0/1. Sous H0 (ordre aléatoire), le nombre de suites R a pour
    espérance 2*n1*n2/n + 1 et variance 2*n1*n2*(2*n1*n2-n) / (n^2*(n-1)) (formule de Wald-Wolfowitz).
    """
    seq = np.asarray(binary_sequence).astype(int)
    n1 = int((seq == 1).sum())
    n2 = int((seq == 0).sum())
    n = n1 + n2
    if n1 == 0 or n2 == 0:
        return {"n1": n1, "n2": n2, "n": n, "n_runs": 1, "expected_runs": 1.0, "z": 0.0, "p_value": 1.0}
    n_runs = 1 + int((seq[1:] != seq[:-1]).sum())
    mean = 2 * n1 * n2 / n + 1
    var = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n ** 2 * (n - 1))
    z = (n_runs - mean) / var ** 0.5
    p_value = float(2 * (1 - norm.cdf(abs(z))))
    return {"n1": n1, "n2": n2, "n": n, "n_runs": n_runs, "expected_runs": mean, "z": float(z), "p_value": p_value}
