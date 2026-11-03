import numpy as np
import pandas as pd

from loto_research.backtesting.walk_forward import walk_forward_baselines, walk_forward_logistic
from loto_research.models.baselines import frequency_baseline_predictions, random_baseline_predictions
from loto_research.models.logistic import FEATURE_COLUMNS


def test_walk_forward_baselines_prediction_ids_and_shapes():
    rng = np.random.default_rng(1)
    rows = []
    for d in range(1, 16):
        picked = sorted(rng.choice(np.arange(1, 50), size=6, replace=False).tolist())
        rows.append({**{f"n{i + 1}": v for i, v in enumerate(picked)}, "chronological_id": d})
    draws = pd.DataFrame(rows)
    feats = pd.DataFrame({"chronological_id": list(range(1, 16))})

    pred_ids, p_random, p_freq = walk_forward_baselines(draws, feats, min_train=10)

    assert list(pred_ids) == list(range(11, 16))
    assert p_random.shape == (5, 49)
    assert p_freq.shape == (5, 49)


def test_walk_forward_baselines_matches_direct_computation():
    rng = np.random.default_rng(2)
    rows = []
    for d in range(1, 16):
        picked = sorted(rng.choice(np.arange(1, 50), size=6, replace=False).tolist())
        rows.append({**{f"n{i + 1}": v for i, v in enumerate(picked)}, "chronological_id": d})
    draws = pd.DataFrame(rows)
    feats = pd.DataFrame({"chronological_id": list(range(1, 16))})

    pred_ids, p_random, p_freq = walk_forward_baselines(draws, feats, min_train=10)

    expected_random_full = random_baseline_predictions(15)
    expected_freq_full = frequency_baseline_predictions(draws)

    np.testing.assert_allclose(p_random, expected_random_full[10:15])
    np.testing.assert_allclose(p_freq, expected_freq_full[10:15])


def test_walk_forward_logistic_uses_expanding_causal_training_sets(monkeypatch):
    """Vérifie, sans ajuster un vrai modèle (fit_and_predict mocké), que chaque checkpoint
    n'entraîne JAMAIS sur des tirages > checkpoint, et que la taille d'entraînement croît de
    manière monotone (fenêtre expanding, jamais rétrécie)."""
    n_draws, n_numbers = 35, 49
    rows = []
    for d in range(1, n_draws + 1):
        for num in range(1, n_numbers + 1):
            rows.append({"chronological_id": d, "number": num, "target": 0,
                         **{c: 0.0 for c in FEATURE_COLUMNS}})
    feats = pd.DataFrame(rows)

    calls = []

    def fake_fit_and_predict(train_df, predict_df, feature_columns=None):
        calls.append({
            "train_max_id": int(train_df["chronological_id"].max()),
            "train_n_draws": train_df["chronological_id"].nunique(),
            "predict_min_id": int(predict_df["chronological_id"].min()),
            "predict_max_id": int(predict_df["chronological_id"].max()),
        })
        return None, None, np.zeros(len(predict_df))

    monkeypatch.setattr("loto_research.backtesting.walk_forward.fit_and_predict", fake_fit_and_predict)

    pred_ids, p_hat = walk_forward_logistic(feats, min_train=10, retrain_step=10)

    # Checkpoints attendus : 10, 20, 30 -> predictions [11-20], [21-30], [31-35]
    assert [c["train_max_id"] for c in calls] == [10, 20, 30]
    assert [c["predict_min_id"] for c in calls] == [11, 21, 31]
    assert [c["predict_max_id"] for c in calls] == [20, 30, 35]

    train_sizes = [c["train_n_draws"] for c in calls]
    assert train_sizes == [10, 20, 30]  # strictement croissant : fenetre expanding, jamais retrecie

    np.testing.assert_array_equal(pred_ids, np.arange(11, 36))
    assert p_hat.shape == (25, 49)


def test_walk_forward_logistic_prediction_ids_cover_full_range_without_gaps_or_duplicates(monkeypatch):
    n_draws, n_numbers = 47, 49
    rows = []
    for d in range(1, n_draws + 1):
        for num in range(1, n_numbers + 1):
            rows.append({"chronological_id": d, "number": num, "target": 0,
                         **{c: 0.0 for c in FEATURE_COLUMNS}})
    feats = pd.DataFrame(rows)

    def fake_fit_and_predict(train_df, predict_df, feature_columns=None):
        return None, None, np.zeros(len(predict_df))

    monkeypatch.setattr("loto_research.backtesting.walk_forward.fit_and_predict", fake_fit_and_predict)

    pred_ids, p_hat = walk_forward_logistic(feats, min_train=10, retrain_step=10)

    expected = np.arange(11, 48)  # 10+1 .. 47, dernier bloc partiel [41-47] de 7 tirages
    np.testing.assert_array_equal(pred_ids, expected)
    assert len(pred_ids) == len(set(pred_ids))  # aucun doublon
    assert p_hat.shape == (len(expected), 49)
