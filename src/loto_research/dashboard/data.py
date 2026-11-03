"""Fonctions de données du tableau de bord (M5, SPEC_V2 §6). Aucune dépendance à Streamlit ni à Plotly :
tout ce qui calcule est ici, donc testable. Le tableau de bord n'ÉCRIT JAMAIS dans la base : ouverture en
lecture seule, et aucune fonction de ce module ne modifie quoi que ce soit."""
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from loto_research.db.corrections import list_corrections
from loto_research.db.hypotheses import available_draws
from loto_research.db.runs import cumulative_test_count, dataset_hash

# Seules fenêtres proposées : l'historique complet et les 5 périodes pré-enregistrées (HYPOTHESES.md, A3).
# Aucune fenêtre libre : choisir une période après coup est un degré de liberté du chercheur.
PERIODS = {
    "Historique complet": None,
    "2001–2005": (2001, 2005),
    "2006–2010": (2006, 2010),
    "2011–2015": (2011, 2015),
    "2016–2020": (2016, 2020),
    "2021–2026": (2021, 2026),
}

ALPHA = 0.05


def open_readonly(path):
    """Connexion SQLite en lecture seule : toute tentative d'écriture échoue."""
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def get_game(conn, name):
    row = conn.execute("SELECT * FROM games WHERE name = ?", (name,)).fetchone()
    return None if row is None else dict(row)


def banner_text(n_max=49, k=6):
    return f"Toute combinaison a la même probabilité : 1 sur {math.comb(n_max, k):,}.".replace(",", " ")


def filter_period(df, label):
    bounds = PERIODS[label]
    if bounds is None:
        return df
    return df[(df["year"] >= bounds[0]) & (df["year"] <= bounds[1])]


def counts_from_df(df, k=6, n_max=49):
    vals = df[[f"n{j}" for j in range(1, k + 1)]].to_numpy(dtype=int)
    return np.bincount(vals.ravel(), minlength=n_max + 1)[1:]


def frequency_from_counts(counts, n_draws, k=6, n_max=49):
    """Fréquence de chaque numéro avec l'écart attendu par hasard : bande à 95 % (par numéro) et bande
    corrigée pour n_max comparaisons (Bonferroni). Loi marginale exacte : binomiale (approximation normale)."""
    p = k / n_max
    expected = n_draws * p
    sd = math.sqrt(n_draws * p * (1 - p))
    z95 = norm.ppf(1 - ALPHA / 2)
    zb = norm.ppf(1 - ALPHA / (2 * n_max))
    counts = np.asarray(counts)
    z = (counts - expected) / sd
    tab = pd.DataFrame({
        "numero": np.arange(1, n_max + 1),
        "count": counts,
        "expected": expected,
        "z": z,
        "lo95": expected - z95 * sd,
        "hi95": expected + z95 * sd,
        "loB": expected - zb * sd,
        "hiB": expected + zb * sd,
    })
    tab["freq_pct"] = 100 * tab["count"] / n_draws
    tab["exp_pct"] = 100 * p
    tab["lo95_pct"] = 100 * tab["lo95"] / n_draws
    tab["hi95_pct"] = 100 * tab["hi95"] / n_draws
    tab["outside95"] = tab["z"].abs() > z95
    tab["outsideB"] = tab["z"].abs() > zb
    return tab


def frequency_table(df, k=6, n_max=49):
    return frequency_from_counts(counts_from_df(df, k, n_max), len(df), k, n_max)


def simulate_counts(n_draws, seed, k=6, n_max=49):
    """Apparitions de chaque numéro dans n_draws tirages de hasard pur (graine explicite)."""
    rng = np.random.default_rng(seed)
    keys = rng.random((n_draws, n_max))
    idx = np.argpartition(keys, k - 1, axis=1)[:, :k]
    return np.bincount(idx.ravel(), minlength=n_max)


def outside_counts(tab):
    """(numéros hors de la bande à 95 %, numéros hors de la bande corrigée)."""
    return int(tab["outside95"].sum()), int(tab["outsideB"].sum())


def expected_outside(n_max=49):
    """Nombre attendu PAR HASARD de numéros hors de chaque bande (95 % ; corrigée pour n_max comparaisons)."""
    return n_max * ALPHA, ALPHA


def draws_per_year(df):
    return df.groupby("year").size().rename("tirages").reset_index()


def last_draws(df, n=10, k=6):
    cols = ["date"] + [f"n{j}" for j in range(1, k + 1)] + ["bonus"]
    out = df.sort_values("date", ascending=False).head(n)[cols].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out.reset_index(drop=True)


def dataset_state(conn, game_id):
    return {"hash": dataset_hash(conn, game_id), "tests": cumulative_test_count(conn, game_id)}


def runs_table(conn, game_id):
    return pd.read_sql_query(
        "SELECT id AS lancement, started_at AS date_utc, mode, n_draws AS tirages, "
        "substr(dataset_hash, 1, 12) AS empreinte_donnees, substr(COALESCE(git_commit, ''), 1, 8) AS commit_code "
        "FROM analysis_runs WHERE game_id = ? ORDER BY id DESC", conn, params=(game_id,))


def results_table(conn, game_id, run_id=None):
    sql = ("SELECT t.run_id AS lancement, t.label AS test, t.statistic AS statistique, t.p_raw AS p_brut, "
           "t.p_adjusted AS p_ajuste, t.method AS methode, t.family_size AS taille_famille, t.tag AS etiquette "
           "FROM test_results t JOIN analysis_runs r ON r.id = t.run_id WHERE r.game_id = ?")
    params = [game_id]
    if run_id is not None:
        sql += " AND t.run_id = ?"
        params.append(int(run_id))
    return pd.read_sql_query(sql + " ORDER BY t.run_id, t.id", conn, params=params)


def hypotheses_progress(conn, game_id):
    rows = conn.execute("SELECT * FROM hypotheses WHERE game_id = ? ORDER BY id", (game_id,)).fetchall()
    out = []
    for h in rows:
        o = conn.execute("SELECT decision, p_value FROM hypothesis_outcomes WHERE hypothesis_id = ?",
                         (h["id"],)).fetchone()
        out.append({"code": h["code"], "type": h["kind"], "test": h["test_name"],
                    "enregistree_le": h["registered_date"], "n_star": h["n_star"],
                    "tirages_posterieurs": available_draws(conn, h),
                    "decision": None if o is None else o["decision"],
                    "p": None if o is None else o["p_value"]})
    return pd.DataFrame(out)


def ingestion_by_source(conn, game_id):
    return pd.read_sql_query(
        "SELECT source, COUNT(*) AS tirages, MIN(draw_date) AS premier_tirage, MAX(draw_date) AS dernier_tirage, "
        "MIN(ingested_at) AS premier_ajout_utc FROM draws WHERE game_id = ? GROUP BY source "
        "ORDER BY MIN(draw_date)", conn, params=(game_id,))


def corrections_table(conn, game_id):
    rows = list_corrections(conn, game_id)
    cols = ["id", "draw_id", "draw_date", "field", "old_value", "new_value", "reason", "author", "at"]
    return pd.DataFrame([{c: r[c] for c in cols} for r in rows], columns=cols)


def bench_results(conn):
    """Résultats du banc d'essai (M4, M4b) ; vide si le banc n'a jamais tourné. Pour une même cellule,
    la valeur la plus récente est conservée."""
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if not {"bench_cells", "simulated_runs"} <= names:
        return pd.DataFrame()
    df = pd.read_sql_query(
        "SELECT b.run_id, s.model, s.created_at, b.n, b.scenario, b.level, b.test, b.reps, b.rejections, "
        "b.rate, b.ci_low, b.ci_high FROM bench_cells b JOIN simulated_runs s ON s.id = b.run_id "
        "ORDER BY b.run_id", conn)
    return df.drop_duplicates(subset=["n", "scenario", "level", "test"], keep="last").reset_index(drop=True)
