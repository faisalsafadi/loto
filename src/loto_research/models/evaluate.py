"""Orchestration de l'évaluation Phase 9 (comparaison formelle des modèles, Cahier §27-28)."""
from loto_research.models import metrics as M


def pivot_to_matrix(df, value_column, chronological_ids):
    """Transforme un DataFrame long (chronological_id, number, value_column) en matrice
    (n_draws, 49) ordonnée par chronological_id croissant (fourni explicitement pour garantir un
    ordre identique entre toutes les matrices comparées) et number 1..49 croissant."""
    pivoted = df.pivot(index="chronological_id", columns="number", values=value_column)
    pivoted = pivoted.reindex(index=chronological_ids, columns=range(1, 50))
    return pivoted.to_numpy()


def evaluate_predictions(name, target_matrix, p_hat_matrix):
    logloss = M.log_loss_per_draw(target_matrix, p_hat_matrix)
    brier = M.brier_per_draw(target_matrix, p_hat_matrix)
    hits = M.top_k_hits_per_draw(target_matrix, p_hat_matrix, k=6)
    calib = M.calibration_table(target_matrix, p_hat_matrix)
    prob_diag = M.mean_probability_drawn_vs_not(target_matrix, p_hat_matrix)
    return {
        "name": name,
        "logloss_per_draw": logloss, "brier_per_draw": brier, "hits_per_draw": hits,
        "mean_logloss": float(logloss.mean()), "mean_brier": float(brier.mean()),
        "mean_hits_per_draw": float(hits.mean()),
        "hits_distribution": {int(k_): int((hits == k_).sum()) for k_ in range(7)},
        "calibration_table": calib, **prob_diag,
    }


def compare_models(results_a, results_b, metric_key="logloss_per_draw"):
    return M.paired_wilcoxon(results_a[metric_key], results_b[metric_key])
