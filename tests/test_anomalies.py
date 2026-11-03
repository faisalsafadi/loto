import numpy as np
import pandas as pd

from loto_research.anomalies.frequency_anomalies import classify_anomaly_level, per_number_binomial_test
from loto_research.anomalies.position_bias import position_uniformity_tests

NUMBER_COLUMNS = [f"n{i}" for i in range(1, 7)]


def _make_fake_draws(n=300, seed=0):
    """Tirages uniformes synthétiques, PAS triés (simule un ordre de tirage), pour tester la mécanique."""
    rng = np.random.default_rng(seed)
    rows = [
        {f"n{i + 1}": v for i, v in enumerate(rng.choice(np.arange(1, 50), size=6, replace=False))}
        for _ in range(n)
    ]
    return pd.DataFrame(rows)


def test_per_number_binomial_test_covers_all_49_numbers():
    df = _make_fake_draws(300)
    res = per_number_binomial_test(df, NUMBER_COLUMNS, p=6 / 49)
    assert len(res) == 49
    assert res["count"].sum() == 300 * 6
    assert res["raw_p_value"].between(0, 1).all()


def test_per_number_binomial_test_detects_planted_bias():
    """Un numéro forcé à apparaître dans 100% des tirages doit avoir un p-value minuscule.

    L'injection du biais doit PRÉSERVER la distinction des 6 numéros par tirage (comme le garantit
    V003 en Phase 2 sur les vraies données) : on échange, on n'écrase pas brutalement, sinon le
    numéro 7 pourrait apparaître deux fois dans une même ligne et count > n ferait échouer binomtest.
    """
    df = _make_fake_draws(300)
    for idx, row in df.iterrows():
        other_cols = ["n2", "n3", "n4", "n5", "n6"]
        others = row[other_cols].tolist()
        if 7 in others:
            pos = others.index(7)
            df.loc[idx, other_cols[pos]] = row["n1"]  # échange : garde 6 numéros distincts
        df.loc[idx, "n1"] = 7
    res = per_number_binomial_test(df, NUMBER_COLUMNS, p=6 / 49)
    row7 = res.loc[res["number"] == 7].iloc[0]
    assert row7["count"] == 300  # exactement une fois par tirage, aucun doublon introduit
    assert row7["raw_p_value"] < 1e-10
    assert classify_anomaly_level(row7["raw_p_value"]) == "B"


def test_classify_anomaly_level_boundary():
    assert classify_anomaly_level(0.04) == "B"
    assert classify_anomaly_level(0.06) == "A"


def test_position_uniformity_tests_returns_one_row_per_column():
    df = _make_fake_draws(300)
    res = position_uniformity_tests(df)
    assert len(res) == 6
    assert set(res["position"]) == set(NUMBER_COLUMNS)
    assert res["p_value"].between(0, 1).all()


def test_position_uniformity_tests_detects_planted_bias():
    df = _make_fake_draws(300)
    df["n1"] = 7  # position 1 toujours = 7 : biais de position massif et artificiel
    res = position_uniformity_tests(df)
    row = res.loc[res["position"] == "n1"].iloc[0]
    assert row["p_value"] < 0.001
