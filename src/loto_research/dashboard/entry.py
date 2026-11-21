"""Écriture depuis le tableau de bord. Ce module est le SEUL du tableau de bord qui écrit, et il n'est importé que si
le tableau de bord est lancé avec --writable (python -m loto_research.dashboard --writable).

Il n'ajoute aucune règle : il appelle les MÊMES fonctions que la ligne de commande (validation complète, source
obligatoire, un seul tirage par date, ajout seul, raison et auteur pour toute correction, gel avant le tirage)."""
import csv
import os
import re
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from loto_research.analysis.core import ensure_supported_game, run_quick_analysis
from loto_research.db.core import ValidationError, connect, init_db
from loto_research.db.corrections import correct_draw, parse_changes, plan_correction
from loto_research.db.hypotheses import run_confirmatory_test
from loto_research.db.ingest import add_csv, prepare_draw
from loto_research.db.loader import load_draws_dataframe
from loto_research.db.runs import log_result, start_run
from loto_research.prediction import store, trusted_time

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
CSV_HEADER = ["date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus", "source", "source_ref", "draw_no"]


def _open(db, game_name):
    conn = connect(db)
    init_db(conn)
    game = conn.execute("SELECT * FROM games WHERE name = ?", (game_name,)).fetchone()
    if game is None:
        conn.close()
        raise ValidationError(f"Jeu introuvable : {game_name!r}")
    return conn, game


def parse_pasted(text):
    """Lignes collées du site : N R1 R2 R3 R4 R5 R6 C AAAA-MM-JJ (espaces ou tabulations). En-têtes ignorés."""
    rows, errors, headers = [], [], 0
    for ln, line in enumerate(str(text).splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        parts = re.split(r"\s+", s)
        if not parts[0].isdigit():
            headers += 1
            continue
        if len(parts) != 9 or not DATE.fullmatch(parts[8]) or not all(p.isdigit() for p in parts[:8]):
            errors.append(f"ligne {ln} illisible : {s!r}")
            continue
        rows.append({"no": int(parts[0]), "nums": [int(p) for p in parts[1:7]], "bonus": int(parts[7]),
                     "date": parts[8]})
    return rows, errors, headers


def preview_pasted(db, game_name, text, source):
    """Vérifie les lignes collées SANS rien écrire. Les tirages déjà présents et identiques sont ignorés ;
    toute autre anomalie est une erreur et bloque l'enregistrement."""
    rows, errors, _ = parse_pasted(text)
    if not rows and not errors:
        errors.append("Aucune ligne de tirage reconnue.")
    conn, game = _open(db, game_name)
    new, skipped, notes, seen = [], [], set(), set()
    try:
        for r in rows:
            if r["date"] in seen:
                errors.append(f"Date en double dans la liste : {r['date']}")
                continue
            seen.add(r["date"])
            try:
                prep = prepare_draw(conn, game["id"], r["date"], r["nums"], r["bonus"], source)
            except ValidationError as e:
                if "déjà dans la base" in str(e):
                    skipped.append(r)
                else:
                    errors.append(f"{r['date']} : {e}")
                continue
            new.append(r)
            notes.update(prep["notes"])
    finally:
        conn.close()
    return {"new": sorted(new, key=lambda r: r["date"]), "skipped": skipped, "errors": errors,
            "notes": sorted(notes)}


def commit_pasted(db, game_name, text, source, source_ref=None):
    """Enregistre les nouveaux tirages collés, TOUT OU RIEN (même fonction que `loto add-csv`)."""
    res = preview_pasted(db, game_name, text, source)
    if res["errors"]:
        raise ValidationError("\n".join(res["errors"]))
    if not res["new"]:
        raise ValidationError("Aucun tirage à ajouter : tout est déjà dans la base.")
    conn, game = _open(db, game_name)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
    try:
        w = csv.writer(tmp)
        w.writerow(CSV_HEADER)
        for r in res["new"]:
            w.writerow([r["date"], *r["nums"], r["bonus"], str(source).strip(), source_ref or "", r["no"]])
        tmp.close()
        add_csv(conn, game["id"], tmp.name)
    finally:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        conn.close()
    return len(res["new"])


def _draw_id_by_date(conn, game_id, draw_date):
    rows = conn.execute("SELECT id FROM draws WHERE game_id = ? AND draw_date = ?",
                        (game_id, str(draw_date).strip())).fetchall()
    if not rows:
        raise ValidationError(f"Aucun tirage à la date {str(draw_date).strip()!r}.")
    if len(rows) > 1:
        raise ValidationError("Plusieurs tirages à cette date : utilise la ligne de commande "
                              "(loto correct --draw-id).")
    return rows[0]["id"]


def _changes(text):
    return parse_changes([p.strip() for p in str(text).split(",") if p.strip()])


def preview_correction(db, game_name, draw_date, changes_text):
    conn, game = _open(db, game_name)
    try:
        did = _draw_id_by_date(conn, game["id"], draw_date)
        return dict(plan_correction(conn, did, _changes(changes_text)), draw_id=did)
    finally:
        conn.close()


def apply_correction(db, game_name, draw_date, changes_text, reason, author):
    conn, game = _open(db, game_name)
    try:
        did = _draw_id_by_date(conn, game["id"], draw_date)
        return correct_draw(conn, did, _changes(changes_text), reason, author)
    finally:
        conn.close()


def freeze(db, game_name, payload):
    """Fige une prédiction préparée (mêmes règles que `scripts/predictions.py next`)."""
    conn, game = _open(db, game_name)
    try:
        info = trusted_time.reference_now()
        return dict(store.freeze_prediction(conn, game["id"], payload,
                                            out_dir=Path(db).resolve().parent / "predictions",
                                            now=info["now"], clock=trusted_time.clock_record(info)),
                    clock_source=info["source"], clock_warning=info["warning"])
    finally:
        conn.close()


# ---------------------------------------------------------------- sauvegardes (tout se fait depuis l'interface)

def backup_dir():
    """Dossier des sauvegardes : ~/Loto_sauvegardes (ou LOTO_BACKUP_DIR)."""
    return Path(os.environ.get("LOTO_BACKUP_DIR") or Path.home() / "Loto_sauvegardes")


def backup_database(db, folder=None, keep=60, tag="auto"):
    """Copie cohérente de la base (API de sauvegarde de SQLite, sûre même base ouverte). Conserve les `keep` plus
    récentes. Retourne le chemin de la sauvegarde."""
    folder = Path(folder) if folder else backup_dir()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = folder / f"loto_{stamp}_{tag}.sqlite"
    src = sqlite3.connect(str(db))
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    for old in sorted(folder.glob("loto_*.sqlite"))[:-keep]:
        old.unlink(missing_ok=True)
    return target


def list_backups(folder=None):
    folder = Path(folder) if folder else backup_dir()
    if not folder.exists():
        return []
    out = []
    for p in sorted(folder.glob("loto_*.sqlite"), reverse=True):
        st = p.stat()
        out.append({"name": p.name, "path": str(p), "size_kb": round(st.st_size / 1024),
                    "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M")})
    return out


def auto_backup_if_needed(db, folder=None, max_age_hours=20):
    """Sauvegarde automatique au lancement si la dernière a plus de `max_age_hours` heures. Retourne le chemin
    créé, ou None."""
    files = list_backups(folder)
    if files:
        newest = max(Path(f["path"]).stat().st_mtime for f in files)
        if (time.time() - newest) / 3600 < max_age_hours:
            return None
    return backup_database(db, folder=folder, tag="auto")


def restore_backup(db, backup_path, folder=None):
    """Restaure une sauvegarde du dossier des sauvegardes. La base actuelle est d'abord sauvegardée
    (« avant-restauration »). Refuse tout fichier hors du dossier ou qui n'est pas une base de tirages."""
    folder = Path(folder) if folder else backup_dir()
    backup_path = Path(backup_path)
    if not backup_path.exists() or backup_path.resolve().parent != folder.resolve():
        raise ValidationError("Sauvegarde introuvable dans le dossier des sauvegardes.")
    try:
        chk = sqlite3.connect(f"file:{backup_path.resolve()}?mode=ro", uri=True)
        try:
            n = chk.execute("SELECT COUNT(*) FROM draws").fetchone()[0]
        finally:
            chk.close()
    except sqlite3.Error as e:
        raise ValidationError(f"Ce fichier n'est pas une base de tirages valide : {e}")
    safety = backup_database(db, folder=folder, tag="avant-restauration")
    src = sqlite3.connect(str(backup_path))
    dst = sqlite3.connect(str(db))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return {"restored": backup_path.name, "safety": safety.name, "draws": n}


# ------------------------------------------------- analyse et test confirmatoire depuis la page Tests

def run_analysis(db, game_name, n_sim=100000, n_perm=20000, seed=42):
    """Analyse rapide (mêmes calculs et même journal que `loto analyze`) : résultats DESCRIPTIFS."""
    conn, game = _open(db, game_name)
    try:
        try:
            ensure_supported_game(game)
        except NotImplementedError as e:
            raise ValidationError(str(e))
        df = load_draws_dataframe(conn, game["id"])
        run_id = start_run(conn, game["id"], "quick", {"n_sim": n_sim, "n_perm": n_perm, "seed": seed})
        results = run_quick_analysis(df, n_sim, n_perm, seed, progress=False)
        for r in results:
            log_result(conn, run_id, tag="DESCRIPTIVE", **r)
        return {"run_id": run_id, "n_draws": len(df), "results": results}
    finally:
        conn.close()


def run_hypothesis_test(db, game_name, hypothesis_id):
    """Test confirmatoire UNIQUE d'une hypothèse pré-enregistrée (mêmes règles que `loto hypothesis test`) :
    refusé avant n_star tirages postérieurs, refusé s'il a déjà eu lieu."""
    conn, _ = _open(db, game_name)
    try:
        return run_confirmatory_test(conn, int(hypothesis_id))
    finally:
        conn.close()
