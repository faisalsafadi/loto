"""Aides de lecture seule pour les pages Tirages et Prédictions (aucune écriture ici)."""
import json
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from loto_research.prediction import engine, store

WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
VARIANT_LABELS = {"frequency": "Variante A (fréquence)", "logistic": "Variante B (logistique)",
                  "uniform_random": "Variante C (contrôle aléatoire)"}
MODEL_LABELS = {"frequency": "Fréquence", "logistic": "Logistique", "uniform_random": "Hasard uniforme"}


def weekday_fr(iso_date):
    return WEEKDAYS_FR[date.fromisoformat(str(iso_date)).weekday()]


def missing_expected_draws(df, today=None):
    """Dates de tirage attendues (lundi, mercredi, samedi) après le dernier tirage en base et STRICTEMENT avant
    aujourd'hui (UTC). Rythme observé depuis 2016 : un jour férié peut le décaler, d'où « probablement »."""
    today = today or datetime.now(timezone.utc).date()
    out, d = [], df["date"].max().date() + timedelta(days=1)
    while d < today:
        if d.weekday() in engine.DRAW_WEEKDAYS:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def draws_listing(df, year=None, k=6):
    """Liste des tirages (corrections appliquées), du plus récent au plus ancien."""
    d = df if year is None else df[df["year"] == int(year)]
    cols = ["date"] + [f"n{j}" for j in range(1, k + 1)] + ["bonus", "draw_number_source"]
    out = d.sort_values("date", ascending=False)[cols].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.columns = ["Date"] + [f"N{j}" for j in range(1, k + 1)] + ["Compl.", "N° officiel"]
    return out.reset_index(drop=True)


def variants_table(payload):
    rows = [{"Variante": VARIANT_LABELS[name],
             "Numéros": " · ".join(str(v) for v in payload["models"][name]["variant_numbers"])}
            for name in ("frequency", "logistic", "uniform_random")]
    return pd.DataFrame(rows).set_index("Variante")


def prediction_history(conn, game_id):
    """Prédictions figées, avec le nombre de bons numéros de chaque variante une fois le tirage connu."""
    rows = store.list_frozen(conn, game_id)
    if not rows:
        return pd.DataFrame()
    ev, pending = store.evaluations(conn, game_id)
    hits = {}
    if not ev.empty:
        for r in ev.itertuples():
            hits[(r.target_date, r.model)] = int(r.hits)
    out = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        rec = {"Tirage visé": row["target_date"],
               "Figée le (UTC)": row["frozen_at"][:19].replace("T", " "),
               "Empreinte": row["payload_sha256"][:12],
               "Statut": "en attente du tirage" if row["target_date"] in pending else "évaluée"}
        for name in ("frequency", "logistic", "uniform_random"):
            txt = " · ".join(str(v) for v in payload["models"][name]["variant_numbers"])
            key = (row["target_date"], name)
            rec[VARIANT_LABELS[name]] = txt + (f"  ({hits[key]} bons)" if key in hits else "")
        out.append(rec)
    return pd.DataFrame(out)


def summary_view(summ):
    if summ.empty:
        return summ
    v = summ.copy()
    v["model"] = v["model"].map(MODEL_LABELS)
    v.columns = ["Modèle", "Tirages évalués", "Écart moyen de log loss vs hasard", "IC bas", "IC haut",
                 "Bons numéros (moyenne)", "Bons numéros attendus par hasard"]
    return v.round(6)
