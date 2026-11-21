import numpy as np
import pandas as pd

from loto_research.features.build import build_feature_dataset
from loto_research.features.leakage import test_no_future_features
from loto_research.validation.schema import NUMBER_COLUMNS


def _make_fake_draws(n, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        picked = sorted(rng.choice(np.arange(1, 50), size=6, replace=False).tolist())
        rows.append({**{f"n{j + 1}": v for j, v in enumerate(picked)},
                     "bonus": int(rng.integers(1, 50)), "chronological_id": i + 1})
    return pd.DataFrame(rows)


def _leaky_build_fn(df):
    """Fonction DÉLIBÉRÉMENT fautive : la feature est la somme du tirage COURANT lui-même, ce que
    la règle interdit. Sert à vérifier que le détecteur sait reconnaître une vraie fuite."""
    d = df.sort_values("chronological_id").reset_index(drop=True)
    rows = []
    for t in range(len(d)):
        current_sum = int(d.loc[t, NUMBER_COLUMNS].sum())  # FUITE volontaire : donnée du tirage t
        for number in range(1, 50):
            rows.append({"chronological_id": int(d["chronological_id"].iloc[t]),
                         "number": number, "leaky_feature": current_sum})
    return pd.DataFrame(rows)


def test_detector_catches_a_deliberately_leaky_feature():
    df = _make_fake_draws(30)
    result = test_no_future_features(df, _leaky_build_fn, n_checks=5, seed=0)
    assert result["passed"] is False
    assert len(result["failures"]) > 0


def test_detector_passes_the_real_build_function_on_small_synthetic_data():
    df = _make_fake_draws(60, seed=1)
    result = test_no_future_features(df, build_feature_dataset, n_checks=5, seed=2)
    assert result["passed"] is True
    assert result["failures"] == []
