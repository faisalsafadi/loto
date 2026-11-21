import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from loto_research.dashboard import data as D
from loto_research.dashboard import entry as E
from loto_research.dashboard import views as V
from loto_research.db.core import ValidationError, add_draw, connect, count_draws, get_or_create_game, init_db
from loto_research.db.hypotheses import register_hypothesis
from loto_research.db.loader import load_draws_dataframe
from loto_research.prediction import engine, store

GAME = "Loto Maroc 6/49"
FOLDER = Path(D.__file__).parent
WRITE_TOKENS = ["INSERT ", "UPDATE ", "DELETE ", "CREATE ", "DROP ", ".commit(", "executescript"]
FORBIDDEN_WORDS = ["chaud", "froid", "en retard", "favori", "gagnant", "à jouer"]
PASTE = ("N. du tirage\tRésultats 1\tR2\n"
         "130\t42\t3\t28\t12\t31\t17\t15\t2025-01-04\n"
         "129 4 39 2 48 35 20 16 2025-01-01\n")


@pytest.fixture
def dbfile(tmp_path):
    path = tmp_path / "t.sqlite"
    conn = connect(path)
    init_db(conn)
    get_or_create_game(conn, GAME, 6, 49, bonus_range=49, bonus_exclusive=True)
    conn.close()
    return path


def _count(path):
    conn = connect(path)
    gid = conn.execute("SELECT id FROM games").fetchone()[0]
    n = count_draws(conn, gid)
    conn.close()
    return n


def test_parse_pasted_ignores_headers_and_reports_unreadable_lines():
    rows, errors, headers = E.parse_pasted(PASTE)
    assert len(rows) == 2 and errors == [] and headers == 1
    assert rows[0] == {"no": 130, "nums": [42, 3, 28, 12, 31, 17], "bonus": 15, "date": "2025-01-04"}
    _, errors, _ = E.parse_pasted("130 1 2 3\n")
    assert len(errors) == 1


def test_preview_then_commit_then_nothing_left_to_add(dbfile):
    res = E.preview_pasted(dbfile, GAME, PASTE, "site")
    assert [r["date"] for r in res["new"]] == ["2025-01-01", "2025-01-04"] and res["errors"] == []
    assert _count(dbfile) == 0                                    # la vérification n'écrit rien
    assert E.commit_pasted(dbfile, GAME, PASTE, "site", "http://x") == 2
    assert _count(dbfile) == 2
    again = E.preview_pasted(dbfile, GAME, PASTE, "site")
    assert again["new"] == [] and len(again["skipped"]) == 2
    with pytest.raises(ValidationError):
        E.commit_pasted(dbfile, GAME, PASTE, "site")


@pytest.mark.parametrize("text, source", [
    ("130 42 42 28 12 31 17 15 2025-01-04\n", "site"),                       # numéros en double
    ("130 42 3 28 12 31 17 15 2025-01-04\n131 4 5 6 7 8 9 10 2025-01-04\n", "site"),   # même date deux fois
    ("130 42 3 28 12 31 17 15 2025-01-04\n", ""),                            # source obligatoire
    ("130 42 3 28 12 31 17 15 2099-01-04\n", "site"),                        # date dans le futur
])
def test_errors_block_the_commit_and_nothing_is_written(dbfile, text, source):
    assert E.preview_pasted(dbfile, GAME, text, source)["errors"]
    with pytest.raises(ValidationError):
        E.commit_pasted(dbfile, GAME, text, source)
    assert _count(dbfile) == 0


def test_commit_is_all_or_nothing(dbfile):
    text = "130 42 3 28 12 31 17 15 2025-01-04\n129 4 4 2 48 35 20 16 2025-01-01\n"
    with pytest.raises(ValidationError):
        E.commit_pasted(dbfile, GAME, text, "site")
    assert _count(dbfile) == 0


def test_correction_flow_from_the_page(dbfile):
    E.commit_pasted(dbfile, GAME, PASTE, "site")
    plan = E.preview_correction(dbfile, GAME, "2025-01-04", "n1=43")
    assert plan["before"][0][0] == 42 and plan["after"][0][0] == 43
    E.apply_correction(dbfile, GAME, "2025-01-04", "n1=43", "faute de frappe", "faisal")
    ro = D.open_readonly(dbfile)
    gid = D.get_game(ro, GAME)["id"]
    assert len(D.corrections_table(ro, gid)) == 1
    df = load_draws_dataframe(ro, gid)
    assert int(df[df["date"] == "2025-01-04"].iloc[0]["n1"]) == 43


def test_correction_refusals_and_swap(dbfile):
    E.commit_pasted(dbfile, GAME, PASTE, "site")
    with pytest.raises(ValidationError):
        E.preview_correction(dbfile, GAME, "2025-01-04", "n1=3")             # doublon
    with pytest.raises(ValidationError):
        E.preview_correction(dbfile, GAME, "2030-01-01", "n1=3")             # aucun tirage ce jour-là
    with pytest.raises(ValidationError):
        E.apply_correction(dbfile, GAME, "2025-01-04", "n1=43", "", "faisal")  # raison obligatoire
    E.apply_correction(dbfile, GAME, "2025-01-01", "n1=39, n2=4", "numéros permutés", "faisal")
    ro = D.open_readonly(dbfile)
    df = load_draws_dataframe(ro, D.get_game(ro, GAME)["id"])
    row = df[df["date"] == "2025-01-01"].iloc[0]
    assert (int(row["n1"]), int(row["n2"])) == (39, 4)


def test_views_listing_variants_and_weekday(dbfile):
    E.commit_pasted(dbfile, GAME, PASTE, "site")
    ro = D.open_readonly(dbfile)
    df = load_draws_dataframe(ro, D.get_game(ro, GAME)["id"])
    listing = V.draws_listing(df)
    assert listing.iloc[0]["Date"] == "2025-01-04" and len(listing) == 2
    assert len(V.draws_listing(df, 2024)) == 0
    payload = {"models": {"frequency": {"variant_numbers": [1, 2, 3, 4, 5, 6]},
                          "logistic": {"variant_numbers": [7, 8, 9, 10, 11, 12]},
                          "uniform_random": {"variant_numbers": [13, 14, 15, 16, 17, 18]}}}
    vt = V.variants_table(payload)
    assert list(vt.index) == ["Variante A (fréquence)", "Variante B (logistique)", "Variante C (contrôle aléatoire)"]
    assert vt.iloc[0]["Numéros"] == "1 · 2 · 3 · 4 · 5 · 6"
    assert V.weekday_fr("2026-11-02") == "lundi"
    assert V.summary_view(store.cumulative_summary(None)).empty


def test_prediction_history_goes_from_pending_to_evaluated(tmp_path):
    conn = connect(":memory:")
    init_db(conn)
    gid = get_or_create_game(conn, GAME, 6, 49, bonus_range=49, bonus_exclusive=True)
    rng = np.random.default_rng(3)
    d, n = date(2019, 1, 2), 0
    while n < 520:
        if d.weekday() in engine.DRAW_WEEKDAYS:
            pick = rng.choice(49, size=7, replace=False) + 1
            add_draw(conn, gid, d.isoformat(), [int(x) for x in pick[:6]], int(pick[6]), "src")
            n += 1
            last = d
        d += timedelta(days=1)
    assert V.prediction_history(conn, gid).empty
    target = engine.next_draw_date(last)
    now = engine.freeze_cutoff(target) - timedelta(hours=3)
    payload = store.prepare_prediction(conn, gid, now=now)
    store.freeze_prediction(conn, gid, payload, out_dir=tmp_path, now=now)
    hist = V.prediction_history(conn, gid)
    assert len(hist) == 1 and hist.iloc[0]["Statut"] == "en attente du tirage"
    add_draw(conn, gid, target.isoformat(), [3, 9, 14, 22, 31, 40], 5, "src")
    hist = V.prediction_history(conn, gid)
    assert hist.iloc[0]["Statut"] == "évaluée" and "bons" in hist.iloc[0]["Variante A (fréquence)"]


def test_read_only_modules_never_write_and_use_no_forbidden_wording():
    for name in ("app.py", "data.py", "views.py"):
        text = (FOLDER / name).read_text(encoding="utf-8")
        for token in WRITE_TOKENS:
            assert token not in text, f"{name} contient {token!r}"
        for word in FORBIDDEN_WORDS:
            assert word not in text.lower(), f"{name} contient {word!r}"


def test_entry_module_is_imported_only_in_writable_mode_and_default_is_read_only():
    lines = (FOLDER / "app.py").read_text(encoding="utf-8").splitlines()
    idx = next(i for i, line in enumerate(lines) if "import entry as E" in line)
    assert lines[idx - 1].strip() == "if WRITABLE:"
    assert any('LOTO_WRITABLE") == "1"' in line for line in lines)
    main_text = (FOLDER / "__main__.py").read_text(encoding="utf-8")
    assert 'LOTO_WRITABLE="1" if args.writable else "0"' in main_text
    assert 'action="store_true"' in main_text


def test_missing_expected_draws_follows_the_monday_wednesday_saturday_rhythm(dbfile):
    E.commit_pasted(dbfile, GAME, PASTE, "site")                       # dernier tirage : samedi 2025-01-04
    ro = D.open_readonly(dbfile)
    df = load_draws_dataframe(ro, D.get_game(ro, GAME)["id"])
    assert V.missing_expected_draws(df, today=date(2025, 1, 9)) == ["2025-01-06", "2025-01-08"]
    assert V.missing_expected_draws(df, today=date(2025, 1, 6)) == []      # le jour même n'est pas encore « manquant »
    assert V.missing_expected_draws(df, today=date(2025, 1, 4)) == []


def test_backup_rotation_listing_and_automatic_backup(dbfile, tmp_path):
    E.commit_pasted(dbfile, GAME, PASTE, "site")
    folder = tmp_path / "b"
    first = E.backup_database(dbfile, folder=folder, tag="t1")
    chk = sqlite3.connect(first)
    assert chk.execute("SELECT COUNT(*) FROM draws").fetchone()[0] == 2
    chk.close()
    for tag in ("t2", "t3", "t4"):
        E.backup_database(dbfile, folder=folder, keep=2, tag=tag)
    listing = E.list_backups(folder)
    assert len(listing) == 2 and {"name", "path", "size_kb", "modified"} <= set(listing[0])
    assert E.auto_backup_if_needed(dbfile, folder=folder) is None                  # une sauvegarde récente existe
    assert E.auto_backup_if_needed(dbfile, folder=tmp_path / "vide") is not None   # aucune : en crée une


def test_restore_returns_to_the_backup_and_keeps_a_safety_copy(dbfile, tmp_path):
    E.commit_pasted(dbfile, GAME, PASTE, "site")
    folder = tmp_path / "b"
    backup = E.backup_database(dbfile, folder=folder, tag="base")
    E.commit_pasted(dbfile, GAME, "131 1 2 3 4 5 6 7 2025-01-06\n", "site")
    assert _count(dbfile) == 3
    res = E.restore_backup(dbfile, backup, folder=folder)
    assert res["draws"] == 2 and _count(dbfile) == 2
    assert any("avant-restauration" in b["name"] for b in E.list_backups(folder))


def test_restore_refuses_files_outside_the_folder_and_invalid_files(dbfile, tmp_path):
    folder = tmp_path / "b"
    folder.mkdir()
    outside = tmp_path / "loto_autre.sqlite"
    outside.write_bytes(b"x")
    with pytest.raises(ValidationError):
        E.restore_backup(dbfile, outside, folder=folder)
    bad = folder / "loto_bad.sqlite"
    bad.write_text("pas une base")
    with pytest.raises(ValidationError):
        E.restore_backup(dbfile, bad, folder=folder)
    with pytest.raises(ValidationError):
        E.restore_backup(dbfile, folder / "absente.sqlite", folder=folder)


def test_confirmatory_test_from_the_page_is_refused_before_n_star(dbfile):
    conn = connect(dbfile)
    gid = conn.execute("SELECT id FROM games").fetchone()[0]
    register_hypothesis(conn, gid, "HX", "h0", "h1", "bonus_lag1", {"value": 2, "direction": "positive"},
                        correction="none", family_size=1, kind="PRE_REGISTERED", n_star=10)
    conn.close()
    with pytest.raises(ValidationError):
        E.run_hypothesis_test(dbfile, GAME, 1)


def test_prediction_reminder_only_when_it_is_still_time_and_nothing_is_frozen(dbfile):
    E.commit_pasted(dbfile, GAME, PASTE, "site")                       # dernier tirage : samedi 2025-01-04
    ro = D.open_readonly(dbfile)
    df = load_draws_dataframe(ro, D.get_game(ro, GAME)["id"])
    cutoff = engine.freeze_cutoff(date(2025, 1, 6))
    assert V.prediction_reminder(df, [], now=cutoff - timedelta(hours=3)) == "2025-01-06"   # même jour, avant la limite
    assert V.prediction_reminder(df, ["2025-01-06"], now=cutoff - timedelta(hours=3)) is None
    assert V.prediction_reminder(df, [], now=cutoff + timedelta(minutes=1)) is None


def test_variants_table_shows_the_complementary_when_present():
    payload = {"models": {n: {"variant_numbers": [1, 2, 3, 4, 5, 6], "complementary": {"variant": 9}}
                          for n in ("frequency", "logistic", "uniform_random")}}
    assert "complémentaire 9" in V.variants_table(payload).iloc[0]["Numéros"]
