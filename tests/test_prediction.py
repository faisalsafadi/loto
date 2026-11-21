import hashlib
import json
import sqlite3
from datetime import date, datetime, time, timedelta, timezone

import numpy as np
import pytest

from loto_research.db.core import ValidationError, add_draw, connect, get_or_create_game, init_db
from loto_research.db.loader import load_draws_dataframe
from loto_research.prediction import engine, store, trusted_time


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


def _last_noon(last):
    return datetime.combine(last, time(12, 0), tzinfo=timezone.utc)


def _before_cutoff(target):
    return engine.freeze_cutoff(target) - timedelta(hours=3)      # le jour du tirage, 3 h avant l'heure limite


def _after_cutoff(target):
    return engine.freeze_cutoff(target) + timedelta(minutes=1)


def test_calendar_helpers():
    assert engine.next_draw_date(date(2026, 10, 31)) == date(2026, 11, 2)      # samedi -> lundi
    assert engine.next_draw_date(date(2026, 11, 2)) == date(2026, 11, 4)       # lundi -> mercredi
    assert engine.next_draw_date(date(2026, 11, 4)) == date(2026, 11, 7)       # mercredi -> samedi
    assert engine.previous_scheduled_date(date(2026, 11, 2)) == date(2026, 10, 31)


def test_freeze_cutoff_is_a_fixed_utc_time_whatever_the_season():
    for d in (date(2026, 11, 2), date(2026, 4, 1), date(2026, 3, 2)):          # automne, printemps, ramadan 2026
        assert engine.freeze_cutoff(d) == datetime(d.year, d.month, d.day, 15, 0, tzinfo=timezone.utc)
    assert "15h00 UTC" in engine.cutoff_label("2026-11-02")


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
    noon = _last_noon(last)
    with pytest.raises(ValidationError):                                            # heure limite dépassée
        store.prepare_prediction(conn, gid, now=_after_cutoff(target))
    with pytest.raises(ValidationError):                                            # tirage déjà connu
        store.prepare_prediction(conn, gid, target_date=last.isoformat(), now=noon)
    with pytest.raises(ValidationError):                                            # tirage trop lointain
        store.prepare_prediction(conn, gid, target_date=(last + timedelta(days=9)).isoformat(), now=noon)
    with pytest.raises(ValidationError):                                            # un tirage manquerait entre-deux
        store.prepare_prediction(conn, gid, target_date=engine.next_draw_date(target).isoformat(), now=noon)
    with pytest.raises(ValidationError):
        store.prepare_prediction(conn, gid, target_date="pas une date", now=noon)


def test_too_few_draws_are_refused():
    conn = connect(":memory:")
    init_db(conn)
    gid = get_or_create_game(conn, "Loto Maroc 6/49", 6, 49, bonus_range=49, bonus_exclusive=True)
    for i, d in enumerate(_schedule(date(2019, 1, 2), 30)):
        add_draw(conn, gid, d.isoformat(), [i + 1, i + 2, i + 3, i + 4, i + 5, i + 6], i + 7, "src")
    with pytest.raises(ValidationError):
        store.prepare_prediction(conn, gid, now=datetime(2019, 6, 1, tzinfo=timezone.utc))


def test_freeze_on_the_draw_day_before_the_cutoff_writes_file_hash_and_refuses_duplicates(db, tmp_path):
    conn, gid, last = db
    target = engine.next_draw_date(last)
    now = _before_cutoff(target)
    clock = {"source": "test", "skew_seconds": 0.0, "warning": None}
    payload = store.prepare_prediction(conn, gid, now=now, clock=clock, code_commit="abc123")
    res = store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=now, clock={"source": "test-gel"})
    text = (tmp_path / f"prediction_{target.strftime('%Y%m%d')}.json").read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == res["sha256"]
    row = store.list_frozen(conn, gid)[0]
    assert row["payload_sha256"] == res["sha256"] and row["target_date"] == target.isoformat()
    assert row["cutoff_at"] == payload["cutoff_at"]
    data = json.loads(text)
    assert data["status"] == store.STATUS and data["clock"]["source"] == "test"
    assert data["freeze_clock"]["source"] == "test-gel"
    assert store.verify_frozen(conn, gid, out_dir=tmp_path) == []
    with pytest.raises(ValidationError):                                            # une seule par tirage
        store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=now)
    with pytest.raises(ValidationError):                                            # refus dès la préparation
        store.prepare_prediction(conn, gid, now=now)


def test_freeze_after_the_cutoff_or_with_a_forged_cutoff_is_refused_by_the_database(db, tmp_path):
    conn, gid, last = db
    target = engine.next_draw_date(last)
    payload = store.prepare_prediction(conn, gid, now=_last_noon(last))
    with pytest.raises(ValidationError):                                            # après l'heure limite
        store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=_after_cutoff(target))
    no_cutoff = {k: v for k, v in payload.items() if k != "cutoff_at"}
    with pytest.raises(ValidationError):                                            # heure limite absente
        store.freeze_prediction(conn, gid, no_cutoff, out_dir=tmp_path, now=_last_noon(last))
    late_cutoff = dict(payload, cutoff_at=f"{target.isoformat()}T23:00:00+00:00")
    with pytest.raises(ValidationError):                                            # heure limite après la publication
        store.freeze_prediction(conn, gid, late_cutoff, out_dir=tmp_path, now=_last_noon(last))
    assert store.list_frozen(conn, gid) == []
    assert list(tmp_path.glob("*.json")) == []


def test_migration_adds_the_cutoff_column_to_a_legacy_table(db, tmp_path):
    conn, gid, last = db
    conn.executescript("""
        CREATE TABLE frozen_predictions (
            id INTEGER PRIMARY KEY, game_id INTEGER NOT NULL REFERENCES games(id), target_date TEXT NOT NULL,
            frozen_at TEXT NOT NULL, dataset_hash TEXT NOT NULL, n_draws INTEGER NOT NULL, code_commit TEXT,
            payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL, UNIQUE (game_id, target_date));
        CREATE TRIGGER frozen_predictions_before_target BEFORE INSERT ON frozen_predictions
            WHEN NEW.frozen_at >= NEW.target_date BEGIN SELECT RAISE(ABORT, 'old rule'); END;
    """)
    conn.execute("INSERT INTO frozen_predictions (game_id, target_date, frozen_at, dataset_hash, n_draws, "
                 "payload_json, payload_sha256) VALUES (?, '2018-01-01', '2017-12-31T12:00:00+00:00', 'h', 1, '{}', 'x')",
                 (gid,))
    conn.commit()
    store.ensure_tables(conn)
    assert "cutoff_at" in {r[1] for r in conn.execute("PRAGMA table_info(frozen_predictions)")}
    assert conn.execute("SELECT cutoff_at FROM frozen_predictions").fetchone()[0] is None      # ancienne ligne intacte
    triggers = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    assert "frozen_predictions_before_target" not in triggers and "frozen_predictions_before_cutoff" in triggers
    target = engine.next_draw_date(last)
    now = _before_cutoff(target)
    payload = store.prepare_prediction(conn, gid, now=now)
    store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=now)
    assert len(store.list_frozen(conn, gid)) == 2


def test_frozen_predictions_are_append_only_and_tampering_is_detected(db, tmp_path):
    conn, gid, last = db
    target = engine.next_draw_date(last)
    now = _before_cutoff(target)
    payload = store.prepare_prediction(conn, gid, now=now)
    store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=now)
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
    now = _before_cutoff(target)
    payload = store.prepare_prediction(conn, gid, now=now)
    store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=now)
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


def test_reference_time_keeps_the_latest_clock_and_records_the_source():
    sys_now = datetime(2026, 11, 7, 10, 0, 0, tzinfo=timezone.utc)
    online = datetime(2026, 11, 7, 10, 5, 0, tzinfo=timezone.utc)
    info = trusted_time.reference_now(fetch=lambda: (online, "example.org"), system_now=sys_now)
    assert info["now"] == online and info["source"] == "online:example.org"
    assert info["skew_seconds"] == -300.0 and info["warning"]                      # l'ordinateur retarde de 5 minutes
    ahead = trusted_time.reference_now(fetch=lambda: (sys_now - timedelta(seconds=30), "example.org"),
                                       system_now=sys_now)
    assert ahead["now"] == sys_now and ahead["warning"] is None
    offline = trusted_time.reference_now(fetch=lambda: None, system_now=sys_now)
    assert offline["now"] == sys_now and offline["source"] == "system" and offline["warning"]
    rec = trusted_time.clock_record(info)
    assert rec["source"] == "online:example.org" and rec["reference_utc"].endswith("+00:00")


def test_complementary_helpers():
    p = engine.complementary_frequency([1, 1, 2, 49], alpha=10.0)
    assert len(p) == 49 and p.sum() == pytest.approx(1.0) and p[0] > p[1] > p[2]
    assert engine.best_complementary(list(p), exclude=[1]) == 2               # 1 exclu : le suivant, à égalité le plus petit
    assert engine.best_complementary([1 / 49] * 49, exclude=[1, 2]) == 3
    banned = [1, 2, 3, 4, 5, 6]
    r = engine.random_complementary("2026-11-07", exclude=banned)
    assert r == engine.random_complementary("2026-11-07", exclude=banned) and 7 <= r <= 49


def test_prediction_includes_a_complementary_outside_the_six_numbers(db):
    conn, gid, _ = db
    df = load_draws_dataframe(conn, gid)
    models = engine.predict_next(df, "2030-01-01")
    for m in models.values():
        c = m["complementary"]
        assert len(c["probabilities"]) == 49 and sum(c["probabilities"]) == pytest.approx(1.0)
        assert 1 <= c["variant"] <= 49 and c["variant"] not in m["variant_numbers"]
    assert np.allclose(models["uniform_random"]["complementary"]["probabilities"], 1 / 49)


def test_evaluate_payload_scores_the_complementary_and_tolerates_old_files():
    drawn = [1, 2, 3, 4, 5, 6]
    flat = [6 / 49] * 49
    sharp = [0.01] * 49
    sharp[31] = 1 - 0.01 * 48                                                  # la valeur 32 porte 0,52
    payload = {"models": {
        "uniform_random": {"probabilities": flat, "variant_numbers": [7, 8, 9, 10, 11, 12],
                           "complementary": {"probabilities": [1 / 49] * 49, "variant": 40}},
        "frequency": {"probabilities": flat, "variant_numbers": [13, 14, 15, 16, 17, 18],
                      "complementary": {"probabilities": sharp, "variant": 32}},
        "logistic": {"probabilities": flat, "variant_numbers": [19, 20, 21, 22, 23, 24],
                     "complementary": {"probabilities": sharp, "variant": 33}}}}
    ev = store.evaluate_payload(payload, drawn, drawn_bonus=32)
    assert ev["uniform_random"]["comp_delta_vs_uniform"] == pytest.approx(0.0, abs=1e-9)
    assert ev["frequency"]["comp_delta_vs_uniform"] < -2
    assert ev["frequency"]["comp_hit"] == 1 and ev["logistic"]["comp_hit"] == 0 and ev["uniform_random"]["comp_hit"] == 0
    old = {"models": {n: {"probabilities": flat, "variant_numbers": [7, 8, 9, 10, 11, 12]} for n in engine.MODELS}}
    assert "comp_hit" not in store.evaluate_payload(old, drawn, drawn_bonus=32)["frequency"]
    assert "comp_hit" not in store.evaluate_payload(payload, drawn)["frequency"]        # complémentaire réel inconnu


def test_complementary_full_cycle_and_summary(db, tmp_path):
    conn, gid, last = db
    target = engine.next_draw_date(last)
    now = _before_cutoff(target)
    payload = store.prepare_prediction(conn, gid, now=now)
    assert payload["schema"] == 2 and payload["protocol"]["h011_registered"] == store.H011_REGISTERED
    store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=now)
    add_draw(conn, gid, target.isoformat(), [3, 9, 14, 22, 31, 40], 5, "src")
    ev, _ = store.evaluations(conn, gid)
    assert {"comp_log_loss", "comp_delta_vs_uniform", "comp_hit"} <= set(ev.columns)
    summ = store.complementary_summary(ev)
    assert summ["n"].tolist() == [1, 1, 1] and summ["expected_hit_rate"].iloc[0] == pytest.approx(1 / 49)
    assert store.complementary_summary(None).empty
