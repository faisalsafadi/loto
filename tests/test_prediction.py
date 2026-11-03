import json
import sqlite3
from datetime import date, datetime, time, timedelta, timezone

import numpy as np
import pytest

from loto_research.db.core import ValidationError, add_draw, connect, get_or_create_game, init_db
from loto_research.db.loader import load_draws_dataframe
from loto_research.prediction import engine, store


def _schedule(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() in engine.DRAW_WEEKDAYS:
            out.append(d)
        d += timedelta(days=1)
    return out


@pytest.fixture
def db():
    conn = connect(":memory:")
    init_db(conn)
    gid = get_or_create_game(conn, "Loto Maroc 6/49", 6, 49, bonus_range=49, bonus_exclusive=True)
    rng = np.random.default_rng(7)
    dates = _schedule(date(2019, 1, 2), 520)
    for d in dates:
        pick = rng.choice(49, size=7, replace=False) + 1
        add_draw(conn, gid, d.isoformat(), [int(x) for x in pick[:6]], int(pick[6]), "src")
    return conn, gid, dates[-1]


def _frozen_at(target):
    return datetime.combine(target - timedelta(days=1), time(12, 0), tzinfo=timezone.utc)


def test_calendar_helpers():
    assert engine.next_draw_date(date(2026, 10, 31)) == date(2026, 11, 2)      # samedi -> lundi
    assert engine.next_draw_date(date(2026, 11, 2)) == date(2026, 11, 4)       # lundi -> mercredi
    assert engine.next_draw_date(date(2026, 11, 4)) == date(2026, 11, 7)       # mercredi -> samedi
    assert engine.previous_scheduled_date(date(2026, 11, 2)) == date(2026, 10, 31)


def test_variants_are_valid_and_reproducible():
    a = engine.random_variant("2026-11-02")
    assert a == engine.random_variant("2026-11-02")
    assert len(set(a)) == 6 and all(1 <= v <= 49 for v in a) and a == sorted(a)
    assert engine.top_k_variant([1 / 49] * 49) == [1, 2, 3, 4, 5, 6]
    p = [0.1] * 49
    p[48], p[0] = 0.9, 0.8
    assert 49 in engine.top_k_variant(p) and 1 in engine.top_k_variant(p)


def test_prediction_structure_and_normalisation(db):
    conn, gid, _ = db
    df = load_draws_dataframe(conn, gid)
    models = engine.predict_next(df, "2030-01-01")
    assert set(models) == set(engine.MODELS)
    for m in models.values():
        assert len(m["probabilities"]) == 49 and len(set(m["variant_numbers"])) == 6
    assert np.allclose(models["uniform_random"]["probabilities"], 6 / 49)
    assert sum(models["frequency"]["probabilities"]) == pytest.approx(6.0)
    assert all(0 < p < 1 for p in models["logistic"]["probabilities"])


def test_prediction_does_not_depend_on_the_placeholder_row(db):
    """Garde anti-fuite : le contenu de la ligne fictive du tirage à prédire ne doit rien changer."""
    conn, gid, _ = db
    df = load_draws_dataframe(conn, gid)
    a = engine.predict_next(df, "2030-01-01", _placeholder=(1, 2, 3, 4, 5, 6))
    b = engine.predict_next(df, "2030-01-01", _placeholder=(44, 45, 46, 47, 48, 49))
    for name in engine.MODELS:
        assert np.allclose(a[name]["probabilities"], b[name]["probabilities"])


def test_prepare_refusals(db):
    conn, gid, last = db
    target = engine.next_draw_date(last)
    with pytest.raises(ValidationError):
        store.prepare_prediction(conn, gid, today=target)                       # le jour du tirage est atteint
    with pytest.raises(ValidationError):
        store.prepare_prediction(conn, gid, target_date=last.isoformat(), today=last)   # tirage déjà connu
    with pytest.raises(ValidationError):
        store.prepare_prediction(conn, gid, target_date=(last + timedelta(days=9)).isoformat(), today=last)
    with pytest.raises(ValidationError):                                         # un tirage manquerait entre-deux
        store.prepare_prediction(conn, gid, target_date=engine.next_draw_date(target).isoformat(), today=last)
    with pytest.raises(ValidationError):
        store.prepare_prediction(conn, gid, target_date="pas une date", today=last)


def test_too_few_draws_are_refused():
    conn = connect(":memory:")
    init_db(conn)
    gid = get_or_create_game(conn, "Loto Maroc 6/49", 6, 49, bonus_range=49, bonus_exclusive=True)
    for i, d in enumerate(_schedule(date(2019, 1, 2), 30)):
        add_draw(conn, gid, d.isoformat(), [i + 1, i + 2, i + 3, i + 4, i + 5, i + 6], i + 7, "src")
    with pytest.raises(ValidationError):
        store.prepare_prediction(conn, gid, today=date(2019, 6, 1))


def test_freeze_writes_file_hash_and_refuses_duplicates(db, tmp_path):
    conn, gid, last = db
    target = engine.next_draw_date(last)
    payload = store.prepare_prediction(conn, gid, today=last, code_commit="abc123")
    res = store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=_frozen_at(target))
    text = (tmp_path / f"prediction_{target.strftime('%Y%m%d')}.json").read_text(encoding="utf-8")
    import hashlib
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == res["sha256"]
    row = store.list_frozen(conn, gid)[0]
    assert row["payload_sha256"] == res["sha256"] and row["target_date"] == target.isoformat()
    assert json.loads(text)["status"] == store.STATUS
    assert store.verify_frozen(conn, gid, out_dir=tmp_path) == []
    with pytest.raises(ValidationError):                                         # une seule par tirage
        store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=_frozen_at(target))
    with pytest.raises(ValidationError):                                         # déjà figée : refus dès la préparation
        store.prepare_prediction(conn, gid, today=last)


def test_freeze_on_the_draw_day_is_refused_by_the_database(db, tmp_path):
    conn, gid, last = db
    target = engine.next_draw_date(last)
    payload = store.prepare_prediction(conn, gid, today=last)
    same_day = datetime.combine(target, time(0, 0, 1), tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=same_day)
    assert store.list_frozen(conn, gid) == []
    assert list(tmp_path.glob("*.json")) == []


def test_frozen_predictions_are_append_only_and_tampering_is_detected(db, tmp_path):
    conn, gid, last = db
    target = engine.next_draw_date(last)
    payload = store.prepare_prediction(conn, gid, today=last)
    store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=_frozen_at(target))
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE frozen_predictions SET n_draws = 1")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM frozen_predictions")
    path = tmp_path / f"prediction_{target.strftime('%Y%m%d')}.json"
    path.write_text(path.read_text(encoding="utf-8").replace('"EXPLORATORY_NOT_VALIDATED"', '"VALIDATED"'),
                    encoding="utf-8")
    assert len(store.verify_frozen(conn, gid, out_dir=tmp_path)) == 1


def test_evaluate_payload_rewards_a_better_prediction():
    drawn = [1, 2, 3, 4, 5, 6]
    sharp = [0.99 if i + 1 in drawn else 0.01 for i in range(49)]
    flat = [6 / 49] * 49
    payload = {"models": {
        "uniform_random": {"probabilities": flat, "variant_numbers": [7, 8, 9, 10, 11, 12]},
        "frequency": {"probabilities": sharp, "variant_numbers": [1, 2, 3, 40, 41, 42]},
        "logistic": {"probabilities": flat, "variant_numbers": [1, 2, 3, 4, 5, 6]}}}
    ev = store.evaluate_payload(payload, drawn)
    assert ev["uniform_random"]["delta_vs_uniform"] == pytest.approx(0.0, abs=1e-12)
    assert ev["frequency"]["delta_vs_uniform"] < -0.1
    assert [ev[m]["hits"] for m in ("uniform_random", "frequency", "logistic")] == [0, 3, 6]
    assert ev["uniform_random"]["log_loss"] == pytest.approx(0.3718, abs=1e-3)


def test_evaluation_after_the_draw_and_pending_before(db, tmp_path):
    conn, gid, last = db
    target = engine.next_draw_date(last)
    payload = store.prepare_prediction(conn, gid, today=last)
    store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=_frozen_at(target))
    ev, pending = store.evaluations(conn, gid)
    assert ev.empty and pending == [target.isoformat()]
    add_draw(conn, gid, target.isoformat(), [3, 9, 14, 22, 31, 40], 5, "src")
    ev, pending = store.evaluations(conn, gid)
    assert pending == [] and len(ev) == 3 and set(ev["model"]) == set(engine.MODELS)
    assert ev[ev["model"] == "uniform_random"]["delta_vs_uniform"].iloc[0] == pytest.approx(0.0, abs=1e-12)
    summ = store.cumulative_summary(ev)
    assert summ["n"].tolist() == [1, 1, 1] and list(summ.columns)[0] == "model"


def test_tables_absent_on_a_fresh_database():
    conn = connect(":memory:")
    init_db(conn)
    gid = get_or_create_game(conn, "Loto Maroc 6/49", 6, 49, bonus_range=49, bonus_exclusive=True)
    assert store.list_frozen(conn, gid) == []
    ev, pending = store.evaluations(conn, gid)
    assert ev.empty and pending == []
    assert store.cumulative_summary(ev).empty
