"""Journal des lancements d'analyse (SPEC_V2 §2 principe 4, §5). Chaque lancement enregistre la
version exacte des données analysées ; rien n'est jamais modifié ni supprimé après coup."""
import hashlib
import json
from datetime import datetime, timezone

from loto_research.db.core import ValidationError


def dataset_hash(conn, game_id):
    """Empreinte SHA256 de l'état des données d'un jeu : tous les tirages (dans l'ordre d'insertion)
    et toutes les corrections. Deux lancements avec la même empreinte ont analysé exactement les
    mêmes données ; un tirage ou une correction ajouté(e) change l'empreinte."""
    h = hashlib.sha256()
    for (sha,) in conn.execute("SELECT row_sha256 FROM draws WHERE game_id = ? ORDER BY id", (game_id,)):
        h.update(sha.encode("utf-8"))
    for row in conn.execute(
        "SELECT c.id, c.draw_id, c.field, c.new_value FROM draw_corrections c "
        "JOIN draws d ON d.id = c.draw_id WHERE d.game_id = ? ORDER BY c.id", (game_id,)
    ):
        h.update(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}".encode("utf-8"))
    return h.hexdigest()


def start_run(conn, game_id, mode, config, git_commit=None):
    n_draws = conn.execute("SELECT COUNT(*) FROM draws WHERE game_id = ?", (game_id,)).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO analysis_runs (game_id, started_at, mode, git_commit, dataset_hash, n_draws, config_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (game_id, datetime.now(timezone.utc).isoformat(), mode, git_commit,
         dataset_hash(conn, game_id), n_draws, json.dumps(config, sort_keys=True)),
    )
    conn.commit()
    return cur.lastrowid


def log_result(conn, run_id, label, statistic=None, p_raw=None, p_adjusted=None, method=None,
               family_size=None, tag="DESCRIPTIVE", detail=None, hypothesis_id=None):
    """Un résultat CONFIRMATORY exige une hypothèse pré-enregistrée (vérifié ici ET par un
    déclencheur SQL, pour qu'aucun chemin de code ne puisse le contourner)."""
    if tag == "CONFIRMATORY" and hypothesis_id is None:
        raise ValidationError("Un résultat CONFIRMATORY exige une hypothèse pré-enregistrée (hypothesis_id)")
    cur = conn.execute(
        "INSERT INTO test_results (run_id, label, statistic, p_raw, p_adjusted, method, family_size, tag, "
        "detail_json, hypothesis_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id, label, statistic, p_raw, p_adjusted, method, family_size, tag,
         None if detail is None else json.dumps(detail, sort_keys=True), hypothesis_id),
    )
    conn.commit()
    return cur.lastrowid


def cumulative_test_count(conn, game_id):
    """Nombre de tests distincts déjà enregistrés pour un jeu : chaque (label, version des données)
    ne compte qu'une fois. Relancer sur des données identiques n'apporte aucune information et ne
    gonfle pas le total ; relancer après l'ajout de tirages compte à nouveau (SPEC_V2 §3)."""
    return conn.execute(
        "SELECT COALESCE(SUM(fs), 0) FROM ("
        "  SELECT MAX(COALESCE(t.family_size, 1)) AS fs FROM test_results t "
        "  JOIN analysis_runs r ON r.id = t.run_id WHERE r.game_id = ? "
        "  GROUP BY t.label, r.dataset_hash)", (game_id,)
    ).fetchone()[0]
