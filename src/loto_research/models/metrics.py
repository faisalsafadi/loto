"""Métriques d'évaluation des modèles (Cahier §28, IMPLEMENTATION_SPEC §39-41)."""
import numpy as np
import pandas as pd
from scipy import stats

EPS = 1e-12


def log_loss_per_draw(target, p_hat):
    """target, p_hat : arrays (n_draws, 49). Retourne un array (n_draws,) : log loss moyenne sur
    les 49 numéros de chaque tirage (clip pour éviter log(0))."""
    p = np.clip(p_hat, EPS, 1 - EPS)
    per_number = -(target * np.log(p) + (1 - target) * np.log(1 - p))
    return per_number.mean(axis=1)


def brier_per_draw(target, p_hat):
    """target, p_hat : arrays (n_draws, 49). Retourne un array (n_draws,)."""
    return ((p_hat - target) ** 2).mean(axis=1)


def top_k_hits_per_draw(target, p_hat, k=6):
    """Pour chaque tirage, nombre de numéros réellement tirés qui figurent dans les k numéros de
    plus forte probabilité prédite. Égalités départagées par numéro croissant (déterministe,
    documenté) : np.lexsort trie en priorité par -p_hat (donc p_hat décroissant), puis par indice
    croissant pour les ex-aequo."""
    n_draws, n_numbers = p_hat.shape
    hits = np.zeros(n_draws, dtype=int)
    for t in range(n_draws):
        order = np.lexsort((np.arange(n_numbers), -p_hat[t]))
        top_k_idx = order[:k]
        hits[t] = int(target[t, top_k_idx].sum())
    return hits


def mean_probability_drawn_vs_not(target, p_hat):
    """Diagnostic descriptif (Cahier §28 : « probabilité moyenne attribuée aux numéros réellement
    sortis »). N'est PAS un test formel."""
    return {
        "mean_p_drawn": float(p_hat[target == 1].mean()),
        "mean_p_not_drawn": float(p_hat[target == 0].mean()),
    }


def calibration_table(target, p_hat, n_bins=10):
    """Table de calibration (reliability) : bins à largeur égale sur [min,max] des p_hat observés."""
    flat_p = p_hat.flatten()
    flat_y = target.flatten()
    edges = np.linspace(flat_p.min(), flat_p.max(), n_bins + 1)
    edges[-1] += 1e-9
    bin_idx = np.clip(np.digitize(flat_p, edges) - 1, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue
        rows.append({
            "bin": b, "n": int(mask.sum()),
            "mean_predicted": float(flat_p[mask].mean()),
            "observed_frequency": float(flat_y[mask].mean()),
        })
    return pd.DataFrame(rows)


def paired_wilcoxon(metric_a, metric_b):
    """Test de Wilcoxon signé-rang apparié, au niveau du TIRAGE (unité d'observation indépendante,
    pas la ligne numéro — cf. dépendance structurelle documentée en Phase 8).
    H0 : la médiane des différences appariées (metric_a - metric_b) est nulle."""
    diff = np.asarray(metric_a) - np.asarray(metric_b)
    if np.allclose(diff, 0):
        return {"statistic": 0.0, "p_value": 1.0, "mean_diff": 0.0, "median_diff": 0.0, "n": int(len(diff))}
    stat, p = stats.wilcoxon(diff)
    return {"statistic": float(stat), "p_value": float(p), "mean_diff": float(diff.mean()),
            "median_diff": float(np.median(diff)), "n": int(len(diff))}


def bootstrap_mean_diff_ci(metric_a, metric_b, n_boot=2000, ci=0.95, seed=42):
    """Intervalle de confiance bootstrap (percentile) pour la différence moyenne appariée
    (metric_a - metric_b), au niveau du tirage. Rééchantillonnage avec remise des TIRAGES (donc
    des paires), ce qui respecte toute dépendance entre les deux séries puisqu'elles sont
    rééchantillonnées ensemble, paire par paire — pas indépendamment l'une de l'autre.

    Exigé par EXECUTION_PLAN Phase 10 (« BACKTEST_REPORT.md produit avec effect size, IC,
    p-value, p-value ajustée »). Pré-enregistré (amendement A10) : n_boot=2000, seed=42, ci=0.95."""
    rng = np.random.default_rng(seed)
    diff = np.asarray(metric_a) - np.asarray(metric_b)
    n = len(diff)
    boot_means = np.empty(n_boot)
    for b in range(n_boot):
        sample_idx = rng.integers(0, n, size=n)
        boot_means[b] = diff[sample_idx].mean()
    alpha = 1 - ci
    lower, upper = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"point_estimate": float(diff.mean()), "ci_lower": float(lower), "ci_upper": float(upper),
            "ci_level": ci, "n_boot": n_boot, "seed": seed}
