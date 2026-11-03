"""Walk-forward strict, fenêtre expanding (amendement A10). Cahier §26, IMPLEMENTATION_SPEC §35.

Pseudo-code de référence (IMPLEMENTATION_SPEC §35) :
    for t in prediction_points:
        train = data[data.date < t]
        model.fit(train)
        prediction = model.predict_proba(current_features)
        freeze_prediction(prediction)
        observe_real_result()
        evaluate(prediction, real_result)

Choix pré-enregistrés (amendement A10, validés avant exécution) :
- Fenêtre EXPANDING (pas rolling) : H007 (stabilité temporelle) rejetée en Phase 5, aucune rupture
  ne justifie d'écarter arbitrairement des données anciennes.
- MIN_TRAIN_DRAWS = 500 (déjà présent dans configs/default.yaml depuis la Phase 0).
- baseline_random et frequency_baseline : pas de « réentraînement » au sens strict -- leurs
  formules sont nativement causales et à fenêtre expanding (déjà vérifié en Phase 8/9) ; on évalue
  simplement tous les points de prédiction de MIN_TRAIN_DRAWS+1 à n_draws.
- logistic_regression : réentraînement tous les LOGISTIC_RETRAIN_STEP=10 tirages (coût de
  réajustement répété non justifié vu la stabilité attendue des coefficients, cf. Phase 9).
"""
import numpy as np
import pandas as pd

from loto_research.models.baselines import frequency_baseline_predictions, random_baseline_predictions
from loto_research.models.logistic import FEATURE_COLUMNS, fit_and_predict

MIN_TRAIN_DRAWS = 500
LOGISTIC_RETRAIN_STEP = 10


def walk_forward_baselines(draws_df, feats_df, min_train=MIN_TRAIN_DRAWS):
    """Retourne (prediction_ids, p_random, p_frequency), chacun pour les tirages
    min_train+1 .. n_draws. Les deux baselines sont nativement expanding/causales : on extrait
    simplement la tranche d'évaluation de leurs prédictions déjà calculées sur tout l'historique."""
    n_draws = int(feats_df["chronological_id"].max())
    prediction_ids = np.arange(min_train + 1, n_draws + 1)

    p_random_full = random_baseline_predictions(n_draws)          # (n_draws, 49), indice 0 = tirage 1
    p_freq_full = frequency_baseline_predictions(draws_df)        # idem

    idx = prediction_ids - 1  # tirage chronological_id = k correspond à la ligne d'indice k-1
    return prediction_ids, p_random_full[idx], p_freq_full[idx]


def walk_forward_logistic(feats_df, min_train=MIN_TRAIN_DRAWS, retrain_step=LOGISTIC_RETRAIN_STEP,
                           verbose=False):
    """Walk-forward strict pour la régression logistique, réentraînée tous les `retrain_step`
    tirages. Retourne (prediction_ids, p_hat_matrix) pour les tirages min_train+1 .. n_draws.

    `feats_df` doit déjà avoir subi prepare_features() (colonne gap_current_adjusted présente) --
    appliqué par l'appelant, pas ici.

    À chaque checkpoint c (train = chronological_id <= c), le modèle ajusté est gelé et sert à
    prédire les tirages c+1 .. min(c+retrain_step, n_draws) -- jamais de donnée >= c+1 dans le
    train utilisé pour ces prédictions."""
    n_draws = int(feats_df["chronological_id"].max())
    prediction_ids = np.arange(min_train + 1, n_draws + 1)
    p_hat_rows = {}

    checkpoints = list(range(min_train, n_draws, retrain_step))
    for i, c in enumerate(checkpoints):
        train_df = feats_df[feats_df["chronological_id"] <= c]
        predict_until = min(c + retrain_step, n_draws)
        predict_ids = np.arange(c + 1, predict_until + 1)
        if len(predict_ids) == 0:
            continue
        predict_df = feats_df[feats_df["chronological_id"].isin(predict_ids)]

        _, _, p_flat = fit_and_predict(train_df, predict_df, feature_columns=FEATURE_COLUMNS)
        predict_df_pred = predict_df.copy()
        predict_df_pred["p_hat"] = p_flat
        pivoted = predict_df_pred.pivot(index="chronological_id", columns="number", values="p_hat")
        pivoted = pivoted.reindex(index=predict_ids, columns=range(1, 50))
        for pid, row in zip(predict_ids, pivoted.to_numpy()):
            p_hat_rows[int(pid)] = row

        if verbose and (i % 25 == 0 or i == len(checkpoints) - 1):
            print(f"    [walk-forward logistique] checkpoint {i + 1}/{len(checkpoints)} "
                  f"(train <= {c}, prédit {predict_ids[0]}-{predict_ids[-1]})")

    p_hat_matrix = np.vstack([p_hat_rows[pid] for pid in prediction_ids])
    return prediction_ids, p_hat_matrix
