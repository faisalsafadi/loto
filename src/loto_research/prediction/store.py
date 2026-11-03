"""Gel, stockage et évaluation des prédictions exploratoires (Phase 11 exploratoire, EXECUTION_PLAN §11).

Règles (pré-enregistrées, voir docs/PREDICTIONS_PROTOCOL.md) :
 - une prédiction ne concerne que le PROCHAIN tirage, et se fige AVANT le jour du tirage (déclencheur SQL) ;
 - une seule prédiction figée par tirage (contrainte d'unicité), jamais modifiée ni supprimée (ajout seul) ;
 - empreinte SHA256 du fichier JSON, recopiée dans la base ;
 - l'évaluation est DÉRIVÉE du fichier figé et du tirage réel : rien n'est stocké après coup.
"""
import hashlib
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from loto_research.db.core import ValidationError
from loto_research.db.loader import load_draws_dataframe
from loto_research.db.runs import dataset_hash
from loto_research.models.baselines import FREQUENCY_BASELINE_ALPHA
from loto_research.models.logistic import FEATURE_COLUMNS
from loto_research.prediction import engine

MIN_TRAIN_DRAWS = 500
EXPECTED_HITS = 36 / 49           # espérance du nombre de bons numéros d'une combinaison de 6 parmi 49
H010_N_STAR = 500
STATUS = "EXPLORATORY_NOT_VALIDATED"
NOTE = ("NON VALIDÉ : aucun modèle ne bat le hasard hors échantillon (H008, 2 655 tirages). "
        "Toute combinaison a 1 chance sur 13 983 816. Ne pas utiliser comme conseil de jeu.")


def ensure_tables(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS frozen_predictions (
            id INTEGER PRIMARY KEY,
            game_id INTEGER NOT NULL REFERENCES games(id),
            target_date TEXT NOT NULL,
            frozen_at TEXT NOT NULL,
            dataset_hash TEXT NOT NULL,
            n_draws INTEGER NOT NULL,
            code_commit TEXT,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            UNIQUE (game_id, target_date));
        CREATE TRIGGER IF NOT EXISTS frozen_predictions_before_target BEFORE INSERT ON frozen_predictions
            WHEN NEW.frozen_at >= NEW.target_date
            BEGIN SELECT RAISE(ABORT, 'a prediction must be frozen before its target date'); END;
        CREATE TRIGGER IF NOT EXISTS frozen_predictions_no_update BEFORE UPDATE ON frozen_predictions
            BEGIN SELECT RAISE(ABORT, 'frozen_predictions is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS frozen_predictions_no_delete BEFORE DELETE ON frozen_predictions
            BEGIN SELECT RAISE(ABORT, 'frozen_predictions is append-only'); END;
        """
    )


def _table_exists(conn, name):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone() is not None


def prepare_prediction(conn, game_id, target_date=None, today=None, code_commit=None, allow_stale=False):
    """Calcule la prédiction du PROCHAIN tirage SANS rien écrire. Refuse tout ce qui ressemble à de la triche
    involontaire : tirage déjà connu, tirage trop lointain, jour du tirage atteint, tirage manquant en base."""
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if game is None:
        raise ValidationError(f"Jeu inconnu : {game_id}")
    if game["k"] != 6 or game["n_max"] != 49:
        raise ValidationError("Les modèles pré-enregistrés ne sont définis que pour un jeu 6/49.")
    df = load_draws_dataframe(conn, game_id)
    if len(df) <= MIN_TRAIN_DRAWS:
        raise ValidationError(f"Au moins {MIN_TRAIN_DRAWS + 1} tirages sont nécessaires ({len(df)} en base).")
    last = df["date"].max().date()
    try:
        target = engine.next_draw_date(last) if target_date is None else date.fromisoformat(str(target_date))
    except ValueError:
        raise ValidationError(f"Date invalide : {target_date!r} (format AAAA-MM-JJ)")
    if target <= last:
        raise ValidationError(f"Le tirage du {target} est déjà en base (dernier tirage : {last}).")
    if target > last + timedelta(days=7):
        raise ValidationError("Seul le PROCHAIN tirage peut être prédit (au plus 7 jours après le dernier tirage en base).")
    today = today or datetime.now(timezone.utc).date()
    if today >= target:
        raise ValidationError(f"Une prédiction se fige AVANT le jour du tirage (aujourd'hui, UTC : {today}, tirage : "
                              f"{target}).")
    notes = []
    prev = engine.previous_scheduled_date(target)
    if last < prev:
        msg = f"Il manque peut-être un tirage (attendu le {prev}, dernier tirage en base : {last})."
        if not allow_stale:
            raise ValidationError(msg + " Ajoute-le d'abord, ou force en connaissance de cause.")
        notes.append(msg)
    if _table_exists(conn, "frozen_predictions"):
        if conn.execute("SELECT 1 FROM frozen_predictions WHERE game_id = ? AND target_date = ?",
                        (game_id, target.isoformat())).fetchone():
            raise ValidationError(f"Une prédiction est déjà figée pour le tirage du {target} : une seule par tirage.")
    models = engine.predict_next(df, target.isoformat())
    payload = {
        "schema": 1,
        "game": game["name"],
        "target_date": target.isoformat(),
        "status": STATUS,
        "note": NOTE,
        "dataset_hash": dataset_hash(conn, game_id),
        "n_draws": int(len(df)),
        "last_draw_date": last.isoformat(),
        "code_commit": code_commit,
        "protocol": {
            "models": list(engine.MODELS),
            "frequency_alpha": FREQUENCY_BASELINE_ALPHA,
            "logistic": {"C": 1.0, "features": FEATURE_COLUMNS,
                         "training": "historique complet jusqu'au dernier tirage en base"},
            "variant": "frequence et logistique : les 6 numéros de plus forte probabilité ; "
                       "uniform_random : combinaison de contrôle tirée avec une graine dérivée de la date cible",
        },
        "models": models,
        "notes": notes,
    }
    return payload


def freeze_prediction(conn, game_id, payload, out_dir="data/predictions", now=None):
    """Fige une prédiction préparée : base (ajout seul) + fichier JSON dont l'empreinte SHA256 est enregistrée.
    Impossible après le début du jour du tirage (déclencheur SQL) ou si une prédiction existe déjà."""
    ensure_tables(conn)
    now = now or datetime.now(timezone.utc)
    full = dict(payload, frozen_at=now.isoformat(timespec="seconds"))
    text = json.dumps(full, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    path = Path(out_dir) / f"prediction_{payload['target_date'].replace('-', '')}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        cur = conn.execute(
            "INSERT INTO frozen_predictions (game_id, target_date, frozen_at, dataset_hash, n_draws, code_commit, "
            "payload_json, payload_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (game_id, payload["target_date"], full["frozen_at"], payload["dataset_hash"], payload["n_draws"],
             payload.get("code_commit"), text, sha))
        with open(path, "x", encoding="utf-8") as f:
            created = True
            f.write(text)
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if created:
            path.unlink(missing_ok=True)
        raise ValidationError(f"Prédiction refusée : {e}")
    except FileExistsError:
        conn.rollback()
        raise ValidationError(f"Le fichier {path} existe déjà : rien n'est écrasé.")
    except Exception:
        conn.rollback()
        if created:
            path.unlink(missing_ok=True)
        raise
    return {"id": cur.lastrowid, "sha256": sha, "path": str(path)}


def list_frozen(conn, game_id):
    if not _table_exists(conn, "frozen_predictions"):
        return []
    return conn.execute("SELECT * FROM frozen_predictions WHERE game_id = ? ORDER BY target_date",
                        (game_id,)).fetchall()


def verify_frozen(conn, game_id, out_dir=None):
    """Liste des anomalies d'intégrité : empreinte de la base ou fichier JSON qui ne correspond plus."""
    problems = []
    for row in list_frozen(conn, game_id):
        if hashlib.sha256(row["payload_json"].encode("utf-8")).hexdigest() != row["payload_sha256"]:
            problems.append(f"{row['target_date']} : le contenu enregistré ne correspond plus à son empreinte")
        if out_dir is not None:
            p = Path(out_dir) / f"prediction_{row['target_date'].replace('-', '')}.json"
            if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != row["payload_sha256"]:
                problems.append(f"{row['target_date']} : le fichier {p} a été modifié")
    return problems


def _log_loss(p, y):
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    return float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1 - p))))


def evaluate_payload(payload, drawn):
    """Évalue une prédiction figée contre le tirage réel : log loss (moyenne sur les 49 numéros), écart au hasard
    uniforme (négatif = mieux que le hasard), Brier, bons numéros de la combinaison associée."""
    y = np.zeros(49)
    y[np.array(sorted(drawn)) - 1] = 1.0
    base = _log_loss(np.full(49, 6 / 49), y)
    out = {}
    for name in engine.MODELS:
        m = payload["models"][name]
        p = np.asarray(m["probabilities"], dtype=float)
        ll = _log_loss(p, y)
        out[name] = {"log_loss": ll, "delta_vs_uniform": ll - base,
                     "brier": float(np.mean((p - y) ** 2)),
                     "hits": len(set(m["variant_numbers"]) & set(drawn))}
    return out


def evaluations(conn, game_id):
    """(DataFrame des évaluations par tirage et modèle, liste des prédictions encore en attente du tirage)."""
    rows = list_frozen(conn, game_id)
    if not rows:
        return pd.DataFrame(), []
    df = load_draws_dataframe(conn, game_id)
    by_date = {}
    for _, r in df.iterrows():
        by_date.setdefault(r["date"].strftime("%Y-%m-%d"), [int(r[f"n{j}"]) for j in range(1, 7)])
    ev, pending = [], []
    for row in rows:
        drawn = by_date.get(row["target_date"])
        if drawn is None:
            pending.append(row["target_date"])
            continue
        payload = json.loads(row["payload_json"])
        for name, m in evaluate_payload(payload, drawn).items():
            ev.append({"target_date": row["target_date"], "model": name, "drawn": drawn, **m})
    return pd.DataFrame(ev), pending


def cumulative_summary(ev):
    """Résumé cumulé par modèle (DESCRIPTIF : le test confirmatoire H010 n'est pas lu avant n_star)."""
    cols = ["model", "n", "mean_delta_logloss", "ci_low", "ci_high", "mean_hits", "expected_hits"]
    if ev is None or ev.empty:
        return pd.DataFrame(columns=cols)
    out = []
    for name in engine.MODELS:
        g = ev[ev["model"] == name]
        if g.empty:
            continue
        n = len(g)
        d = g["delta_vs_uniform"].to_numpy()
        mean = float(d.mean())
        se = float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
        out.append({"model": name, "n": n, "mean_delta_logloss": mean, "ci_low": mean - 1.96 * se,
                    "ci_high": mean + 1.96 * se, "mean_hits": float(g["hits"].mean()),
                    "expected_hits": EXPECTED_HITS})
    return pd.DataFrame(out, columns=cols)
