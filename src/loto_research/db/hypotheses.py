"""Registre d'hypothèses et règle anti-peeking (SPEC_V2 §3, M3).

Règles appliquées :
- l'hypothèse est enregistrée AVANT les données qui la testeront ; la date est posée par l'outil ;
- le test n'utilise que les tirages de date STRICTEMENT postérieure à la date d'enregistrement
  (la date de tirage compte, pas la date d'import) et exactement les n_star premiers ;
- un seul test confirmatoire par hypothèse, et seulement quand n_star est atteint ;
- une hypothèse EXPLORATORY / POST_HOC n'est jamais testée de façon confirmatoire."""
import json
import sqlite3
from datetime import datetime, timezone

from loto_research.analysis.catalog import CATALOG
from loto_research.analysis.core import ensure_supported_game
from loto_research.db.core import ValidationError
from loto_research.db.loader import load_draws_dataframe
from loto_research.db.runs import log_result, start_run

KINDS = ("PRE_REGISTERED", "EXPLORATORY", "POST_HOC")
CORRECTIONS = ("none", "bonferroni")


def register_hypothesis(conn, game_id, code, h0, h1, test_name, test_params, correction="none",
                        family_size=1, kind="PRE_REGISTERED", n_star=None, now=None):
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if game is None:
        raise ValidationError(f"Jeu inconnu : {game_id}")
    ensure_supported_game(game)
    if test_name not in CATALOG:
        raise ValidationError(f"Test inconnu : {test_name!r}. Catalogue : {sorted(CATALOG)}")
    CATALOG[test_name]["validate"](game, test_params)
    if kind not in KINDS:
        raise ValidationError(f"kind doit être l'un de {KINDS}")
    if correction not in CORRECTIONS:
        raise ValidationError(f"correction doit être l'une de {CORRECTIONS}")
    if correction == "none" and family_size != 1:
        raise ValidationError("family_size > 1 exige une correction (bonferroni)")
    if kind == "PRE_REGISTERED" and (not isinstance(n_star, int) or n_star <= 0):
        raise ValidationError("Une hypothèse PRE_REGISTERED exige n_star (effectif cible, entier > 0)")
    if not (code and h0 and h1):
        raise ValidationError("code, h0 et h1 sont obligatoires")
    now = now or datetime.now(timezone.utc)
    try:
        cur = conn.execute(
            "INSERT INTO hypotheses (game_id, code, h0, h1, test_name, test_params_json, correction, "
            "family_size, kind, registered_at, registered_date, n_star) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (game_id, code, h0, h1, test_name, json.dumps(test_params, sort_keys=True), correction, family_size,
             kind, now.isoformat(), now.date().isoformat(), n_star),
        )
    except sqlite3.IntegrityError:
        raise ValidationError(f"Une hypothèse de code {code!r} existe déjà pour ce jeu")
    conn.commit()
    return cur.lastrowid


def _get(conn, hypothesis_id):
    row = conn.execute("SELECT * FROM hypotheses WHERE id = ?", (hypothesis_id,)).fetchone()
    if row is None:
        raise ValidationError(f"Hypothèse inconnue : {hypothesis_id}")
    return row


def available_draws(conn, hypothesis):
    """Nombre de tirages utilisables : date strictement postérieure à l'enregistrement."""
    return conn.execute(
        "SELECT COUNT(*) FROM draws WHERE game_id = ? AND draw_date > ?",
        (hypothesis["game_id"], hypothesis["registered_date"]),
    ).fetchone()[0]


def decide(p_value, alpha, correction, family_size):
    alpha_eff = alpha / family_size if correction == "bonferroni" else alpha
    return ("CONFIRMED" if p_value <= alpha_eff else "NOT_CONFIRMED"), alpha_eff


def run_confirmatory_test(conn, hypothesis_id, alpha=0.05, seed=42, git_commit=None):
    hyp = _get(conn, hypothesis_id)
    if hyp["kind"] != "PRE_REGISTERED":
        raise ValidationError(
            f"L'hypothèse {hyp['code']} est {hyp['kind']} : une hypothèse formée après observation des "
            f"données n'est jamais testée de façon confirmatoire sur les données qui l'ont suggérée.")
    if conn.execute("SELECT 1 FROM hypothesis_outcomes WHERE hypothesis_id = ?", (hypothesis_id,)).fetchone():
        raise ValidationError(f"L'hypothèse {hyp['code']} a déjà eu son test confirmatoire : un seul est permis.")
    n_avail = available_draws(conn, hyp)
    if n_avail < hyp["n_star"]:
        raise ValidationError(
            f"Test refusé : {n_avail} tirages postérieurs au {hyp['registered_date']}, {hyp['n_star']} requis "
            f"(n_star). Avant cela, les résultats ne peuvent être que descriptifs.")

    df = load_draws_dataframe(conn, hyp["game_id"], after_date=hyp["registered_date"], limit=hyp["n_star"])
    params = json.loads(hyp["test_params_json"])
    res = CATALOG[hyp["test_name"]]["run"](df, params, seed)
    decision, alpha_eff = decide(res["p_value"], alpha, hyp["correction"], hyp["family_size"])
    detail = {**res["detail"], "alpha": alpha, "correction": hyp["correction"], "family_size": hyp["family_size"]}

    # L'issue est enregistrée d'abord : l'unique tentative est consommée même si la suite échoue.
    conn.execute(
        "INSERT INTO hypothesis_outcomes (hypothesis_id, tested_at, n_draws_used, statistic, p_value, "
        "alpha_effective, decision, detail_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (hypothesis_id, datetime.now(timezone.utc).isoformat(), len(df), res["statistic"], res["p_value"],
         alpha_eff, decision, json.dumps(detail, sort_keys=True)),
    )
    conn.commit()
    run_id = start_run(conn, hyp["game_id"], "confirmatory",
                       {"hypothesis_id": hypothesis_id, "seed": seed, "n_draws_used": len(df)}, git_commit)
    log_result(conn, run_id, hyp["code"], statistic=res["statistic"], p_raw=res["p_value"],
               method=hyp["test_name"], family_size=hyp["family_size"], tag="CONFIRMATORY",
               detail=detail, hypothesis_id=hypothesis_id)
    return {"code": hyp["code"], "decision": decision, "p_value": res["p_value"], "statistic": res["statistic"],
            "alpha_effective": alpha_eff, "n_draws_used": len(df)}
