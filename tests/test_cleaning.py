from datetime import date

import pandas as pd

from loto_research.cleaning.build_analytic import (
    build_analytic, compute_flags, make_draw_id, split_duplicate_dates, split_valid_invalid,
)


def rec(source_row, draw_number, mains, bonus, d):
    return {"source_row": source_row, "draw_number": draw_number, "mains": mains, "bonus": bonus, "date": d}


def test_split_valid_invalid_keeps_everything_somewhere():
    records = [
        rec(2, 1, [1, 2, 3, 4, 5, 6], 7, "2020-01-01"),          # valide
        rec(3, 2, [0, 0, 0, 0, 0, 0], 0, "2020-01-02"),          # invalide (Cahier §8)
        rec(4, 3, [1, 2, 3, 4, 5, 6], 7, "1900-01-01"),          # invalide (V001)
    ]
    valid_df, invalid_df = split_valid_invalid(records)
    assert len(valid_df) == 1
    assert len(invalid_df) == 2
    assert set(invalid_df["row_number"]) == {3, 4}
    # rien n'est perdu : 1 valide + 2 invalides = 3 enregistrements de départ
    assert len(valid_df) + len(invalid_df) == len(records)


def test_split_duplicate_dates_keeps_first_in_file_order():
    valid_df = pd.DataFrame([
        {"source_row": 2, "date": "2020-01-01", "draw_number_source": 10,
         "n1": 1, "n2": 2, "n3": 3, "n4": 4, "n5": 5, "n6": 6, "bonus": 7},
        {"source_row": 3, "date": "2020-01-01", "draw_number_source": 11,  # même date, arrive après
         "n1": 8, "n2": 9, "n3": 10, "n4": 11, "n5": 12, "n6": 13, "bonus": 14},
        {"source_row": 4, "date": "2020-01-02", "draw_number_source": 12,
         "n1": 1, "n2": 2, "n3": 3, "n4": 4, "n5": 5, "n6": 6, "bonus": 7},
    ])
    valid_df["date"] = pd.to_datetime(valid_df["date"])
    kept, all_dup, removed = split_duplicate_dates(valid_df)
    assert len(kept) == 2
    assert kept.iloc[0]["source_row"] == 2       # la première occurrence est gardée
    assert len(removed) == 1
    assert removed.iloc[0]["source_row"] == 3    # la seconde est retirée de l'ANALYTIC
    assert len(all_dup) == 2                     # mais les deux apparaissent dans le journal complet


def test_make_draw_id_is_deterministic_and_sensitive_to_every_field():
    a = make_draw_id(date(2020, 1, 1), 10, [1, 2, 3, 4, 5, 6], 7)
    b = make_draw_id(date(2020, 1, 1), 10, [1, 2, 3, 4, 5, 6], 7)
    c = make_draw_id(date(2020, 1, 1), 10, [1, 2, 3, 4, 5, 6], 8)  # bonus différent
    assert a == b
    assert a != c
    assert len(a) == 64  # SHA256 hexdigest


def test_compute_flags_detects_reset_gap_and_bonus_in_main():
    df = pd.DataFrame([
        {"date": pd.Timestamp("2020-01-01"), "draw_number_source": 1,
         "n1": 1, "n2": 2, "n3": 3, "n4": 4, "n5": 5, "n6": 6, "bonus": 7},
        {"date": pd.Timestamp("2020-01-04"), "draw_number_source": 3,   # saute le n°2
         "n1": 10, "n2": 11, "n3": 12, "n4": 13, "n5": 14, "n6": 15, "bonus": 16},
        {"date": pd.Timestamp("2020-01-20"), "draw_number_source": 4,   # écart > 7 jours
         "n1": 1, "n2": 20, "n3": 21, "n4": 22, "n5": 23, "n6": 24, "bonus": 1},  # bonus == n1
    ])
    flags = compute_flags(df)
    assert flags[0] == ""                       # premier tirage : rien à comparer
    assert "N_GAP:1" in flags[1]                 # un numéro de tirage sauté
    assert "DATE_GAP:16d" in flags[2]
    assert "BONUS_IN_MAIN" in flags[2]


def test_compute_flags_detects_reset_to_one():
    df = pd.DataFrame([
        {"date": pd.Timestamp("2020-12-30"), "draw_number_source": 157,
         "n1": 1, "n2": 2, "n3": 3, "n4": 4, "n5": 5, "n6": 6, "bonus": 7},
        {"date": pd.Timestamp("2021-01-02"), "draw_number_source": 1,   # remise à zéro
         "n1": 8, "n2": 9, "n3": 10, "n4": 11, "n5": 12, "n6": 13, "bonus": 14},
    ])
    flags = compute_flags(df)
    assert "N_RESET" in flags[1]
    assert "N_GAP" not in flags[1]  # un reset ne doit pas aussi compter comme un gap


def test_build_analytic_assigns_chronological_id_in_date_order_not_file_order():
    kept = pd.DataFrame([
        {"source_row": 5, "date": pd.Timestamp("2020-01-05"), "draw_number_source": 2,
         "n1": 1, "n2": 2, "n3": 3, "n4": 4, "n5": 5, "n6": 6, "bonus": 7},
        {"source_row": 2, "date": pd.Timestamp("2020-01-01"), "draw_number_source": 1,
         "n1": 8, "n2": 9, "n3": 10, "n4": 11, "n5": 12, "n6": 13, "bonus": 14},
    ])
    out = build_analytic(kept)
    assert list(out["chronological_id"]) == [1, 2]
    assert out.iloc[0]["date"] == pd.Timestamp("2020-01-01")  # la plus ancienne est chronological_id=1
    assert out.iloc[0]["draw_number_source"] == 1
    assert set(out.columns) >= {"draw_id", "date", "draw_number_source", "bonus",
                                 "year", "month", "day", "weekday", "chronological_id", "flags"}
