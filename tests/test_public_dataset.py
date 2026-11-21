import csv
from datetime import date, timedelta

from typer.testing import CliRunner

from loto_research.cli import app
from loto_research.db.core import add_draw, connect, count_draws, get_or_create_game, init_db
from loto_research.db.corrections import correct_draw
from loto_research.db.export import CSV_HEADER, export_draws_csv
from loto_research.db.ingest import add_csv
from loto_research.db.loader import load_draws_dataframe
from loto_research.db.runs import dataset_hash

GAME = "Loto Maroc 6/49"
COLS = ["date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"]


def _fresh():
    conn = connect(":memory:")
    init_db(conn)
    return conn, get_or_create_game(conn, GAME, 6, 49, bonus_range=49, bonus_exclusive=True)


def _fill(conn, gid):
    d, i = date(2024, 1, 1), 0
    while i < 10:
        if d.weekday() in (0, 2, 5):
            nums = [(5 * i + 7 * j) % 49 + 1 for j in range(6)]
            bonus = (5 * i + 3) % 49 + 1
            add_draw(conn, gid, d.isoformat(), nums, bonus, "source A" if i < 5 else "source B",
                     source_ref=None if i < 5 else "http://x", source_draw_no=None if i % 2 else i + 1)
            i += 1
        d += timedelta(days=1)


def test_export_then_rebuild_gives_the_same_data_and_the_same_fingerprint(tmp_path):
    conn1, gid1 = _fresh()
    _fill(conn1, gid1)
    path = tmp_path / "d.csv"
    assert export_draws_csv(conn1, gid1, path) == 10
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(CSV_HEADER)
    conn2, gid2 = _fresh()
    add_csv(conn2, gid2, path)
    assert count_draws(conn2, gid2) == 10
    assert dataset_hash(conn1, gid1) == dataset_hash(conn2, gid2)
    df1, df2 = load_draws_dataframe(conn1, gid1), load_draws_dataframe(conn2, gid2)
    assert df1[COLS].equals(df2[COLS])


def test_export_applies_corrections(tmp_path):
    conn, gid = _fresh()
    _fill(conn, gid)
    correct_draw(conn, 1, {"n1": 2}, "faute de frappe", "test")
    path = tmp_path / "d.csv"
    export_draws_csv(conn, gid, path)
    with open(path, newline="", encoding="utf-8") as f:
        first = next(csv.DictReader(f))
    assert first["n1"] == "2"


def test_init_db_builds_a_database_from_the_csv_and_refuses_an_existing_one(tmp_path):
    conn, gid = _fresh()
    _fill(conn, gid)
    csv_path = tmp_path / "d.csv"
    export_draws_csv(conn, gid, csv_path)
    db = tmp_path / "x.sqlite"
    runner = CliRunner()
    ok = runner.invoke(app, ["init-db", "--db", str(db), "--csv", str(csv_path)])
    assert ok.exit_code == 0 and "10 tirages importés" in ok.output
    again = runner.invoke(app, ["init-db", "--db", str(db), "--csv", str(csv_path)])
    assert again.exit_code == 1 and "contient déjà" in again.output
    other = runner.invoke(app, ["init-db", "--db", str(tmp_path / "y.sqlite"), "--game", "Autre jeu"])
    assert other.exit_code == 1


def test_init_db_is_all_or_nothing(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(",".join(CSV_HEADER) + "\n"
                   "2024-01-01,1,2,3,4,5,6,7,src,,\n"
                   "2024-01-03,1,1,3,4,5,6,7,src,,\n", encoding="utf-8")
    db = tmp_path / "z.sqlite"
    res = CliRunner().invoke(app, ["init-db", "--db", str(db), "--csv", str(bad)])
    assert res.exit_code == 1
    conn = connect(db)
    assert count_draws(conn, conn.execute("SELECT id FROM games").fetchone()[0]) == 0
