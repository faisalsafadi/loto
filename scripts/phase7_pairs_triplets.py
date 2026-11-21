#!/usr/bin/env python3
"""Phase 7 — Recherche de structures : paires et triplets.

Pipeline :
1. EXPLORATOIRE   : test binomial exact de chaque paire/triplet sur la moitié "exploration" du
                     dataset (split chronologique pré-spécifié, décidé avant tout calcul).
2. FILTRAGE       : correction FDR-BH sur l'ENSEMBLE des tests (1176 paires, 18424 triplets) ;
                     seuls les candidats survivants passent à l'étape suivante.
3-4. CONFIRMATION HORS-ÉCHANTILLON : les candidats, et EUX SEULS, sont retestés sur la moitié
                     "confirmation" (jamais vue au niveau exploratoire), test unilatéral dans le
                     sens observé, correction Holm (petit nombre de candidats).

Usage :
    python scripts/phase7_pairs_triplets.py
"""
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loto_research.anomalies.pairs_triplets import (
    confirm_candidates, count_pairs, count_triplets, draws_to_bitmasks, pair_probability,
    pairs_dataframe, split_exploration_confirmation, triplet_probability, triplets_dataframe,
)
from loto_research.statistics.multiple_testing import fdr_bh, holm

ROOT = Path(__file__).resolve().parents[1]


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def guard_amendments():
    checks = [
        (ROOT / "docs/Cahier_des_charges", "AMENDEMENT A1"),
        (ROOT / "HYPOTHESES.md", "H005"),
        (ROOT / "HYPOTHESES.md", "H006"),
    ]
    for path, needle in checks:
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            sys.exit(f"ARRET : amendement manquant dans {path.relative_to(ROOT)} ('{needle}').")


def run_pipeline(df_explore, df_confirm, combo_cols, p, count_fn, build_df_fn, label, alpha=0.05):
    masks_explore = draws_to_bitmasks(df_explore)
    explore_df = build_df_fn(masks_explore, p)
    corr = fdr_bh(explore_df["raw_p_value"].tolist(), alpha=alpha)
    explore_df["adjusted_p_value"] = corr["adjusted_p_value"]
    candidates = explore_df[explore_df["adjusted_p_value"] < alpha].copy()

    print(f"[{label}] Exploration : {len(explore_df)} tests, {len(candidates)} candidat(s) après FDR-BH")

    if len(candidates) == 0:
        confirm_df = pd.DataFrame(columns=list(combo_cols) + [
            "count_confirmation", "expected_confirmation", "direction",
            "raw_p_value_confirmation", "adjusted_p_value_confirmation"])
        confirmed = confirm_df
    else:
        confirm_df = confirm_candidates(df_confirm, candidates, combo_cols, p, count_fn)
        corr2 = holm(confirm_df["raw_p_value_confirmation"].tolist(), alpha=alpha)
        confirm_df["adjusted_p_value_confirmation"] = corr2["adjusted_p_value"]
        confirmed = confirm_df[confirm_df["adjusted_p_value_confirmation"] < alpha]
        print(f"[{label}] Confirmation : {len(candidates)} candidat(s) retestés, "
              f"{len(confirmed)} confirmé(s) hors-échantillon (Niveau C)")

    return explore_df, candidates, confirm_df, confirmed


def write_report(label, p, explore_df, candidates, confirmed, combo_cols, expected_count, now):
    top = explore_df.nsmallest(10, "raw_p_value")
    lines = [
        f"# {label.upper()}.md", "",
        f"## LOTO MAROC Research Engine — {label.capitalize()} (Phase 7)", "",
        f"Généré le {now.isoformat()}. Pipeline (Cahier §17) : exploratoire -> filtrage (FDR-BH) -> "
        "confirmation hors-échantillon (split chronologique pré-spécifié, décidé avant tout calcul).", "",

        "## OBSERVATION", "",
        f"- {len(explore_df)} {label} possibles testés (probabilité théorique par tirage p={p:.6f}, "
        "test binomial EXACT — aucune simulation nécessaire, même argument que pour les numéros "
        "individuels en Phase 4 : probabilité constante par tirage, tirages indépendants).",
        f"- Effectif attendu par {label[:-1]} sur l'échantillon d'exploration : ~{expected_count:.2f}.",
        "- Split pré-spécifié (avant tout calcul) : exploration = première moitié chronologique, "
        "confirmation = seconde moitié, jamais consultée au niveau exploratoire.",
        f"- Candidats après FDR-BH (exploration) : {len(candidates)} / {len(explore_df)}.",
        f"- Confirmés hors-échantillon (Niveau C potentiel) : {len(confirmed)}.",
        "",

        "## CALCUL", "",
        "### Top 10 (exploration, p brut le plus faible — à titre descriptif uniquement, PAS une liste de signaux)",
    ]
    for r in top.itertuples():
        combo = "-".join(str(int(getattr(r, c))) for c in combo_cols)
        lines.append(f"  - {combo} : count={r.count} (attendu {r.expected:.2f}), "
                     f"ratio={r.effect_ratio:.2f}, p_brut={r.raw_p_value:.5g}, "
                     f"p_ajusté={r.adjusted_p_value:.5g}")
    lines += ["", "### Candidats confirmés hors-échantillon (Niveau C, Cahier §2)"]
    if len(confirmed) == 0:
        lines.append("  Aucun.")
    else:
        for r in confirmed.itertuples():
            combo = "-".join(str(int(getattr(r, c))) for c in combo_cols)
            lines.append(f"  - {combo} : confirmé, "
                         f"p_ajusté_confirmation={r.adjusted_p_value_confirmation:.5g}")
    lines += [
        "", "## INTERPRÉTATION", "",
        "- Un candidat qui survit à l'exploration (FDR-BH) MAIS PAS à la confirmation hors-échantillon "
        "est un faux positif probable : il n'est jamais présenté comme signal (Cahier §17).",
        "- Un candidat confirmé dans les deux étapes atteint le Niveau C (anomalie robuste), jamais le "
        "Niveau D (pouvoir prédictif), qui exigerait une validation walk-forward complète (Phase 10).",
        "",

        "## LIMITATION", "",
        "- Les niveaux « filtrage » et « validation » du pipeline à 4 niveaux du Cahier sont fusionnés "
        "ici en une seule confirmation hors-échantillon.",
        "- Le split 50/50 chronologique est un choix pré-enregistré parmi d'autres raisonnables (ex. "
        "70/30) ; non reconsidéré après avoir vu les résultats.",
        "- Tout candidat confirmé ici doit être ajouté à HYPOTHESES.md comme POST_HOC (Cahier §17, "
        "§21) : ce pipeline ne le fait pas automatiquement.",
    ]
    return "\n".join(lines) + "\n"


def main():
    guard_amendments()

    parquet_path = ROOT / "data/analytic/draws.parquet"
    if not parquet_path.exists():
        sys.exit("ARRET : data/analytic/draws.parquet introuvable.")
    df = pd.read_parquet(parquet_path)
    df_explore, df_confirm = split_exploration_confirmation(df)

    print("=== PHASE 7 — PAIRES ET TRIPLETS (pipeline exploration/confirmation) ===")
    print(f"Dataset total : {len(df)} tirages")
    print(f"Exploration   : {len(df_explore)} tirages (première moitié chronologique, pré-spécifié)")
    print(f"Confirmation  : {len(df_confirm)} tirages (seconde moitié, jamais vue en exploration)\n")

    p_pair = pair_probability()
    p_triplet = triplet_probability()

    pairs_explore, pairs_candidates, pairs_confirm, pairs_confirmed = run_pipeline(
        df_explore, df_confirm, ["i", "j"], p_pair, count_pairs, pairs_dataframe, "paires")
    print()
    triplets_explore, triplets_candidates, triplets_confirm, triplets_confirmed = run_pipeline(
        df_explore, df_confirm, ["i", "j", "k"], p_triplet, count_triplets, triplets_dataframe, "triplets")

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    pairs_explore.to_csv(reports_dir / "pairs_exploration.csv", index=False)
    pairs_confirm.to_csv(reports_dir / "pairs_confirmation.csv", index=False)
    triplets_explore.to_csv(reports_dir / "triplets_exploration.csv", index=False)
    triplets_confirm.to_csv(reports_dir / "triplets_confirmation.csv", index=False)

    now = datetime.now(timezone.utc)
    (reports_dir / "PAIRS.md").write_text(
        write_report("paires", p_pair, pairs_explore, pairs_candidates, pairs_confirmed,
                     ["i", "j"], len(df_explore) * p_pair, now), encoding="utf-8")
    (reports_dir / "TRIPLETS.md").write_text(
        write_report("triplets", p_triplet, triplets_explore, triplets_candidates, triplets_confirmed,
                     ["i", "j", "k"], len(df_explore) * p_triplet, now), encoding="utf-8")

    audit_path = ROOT / "research_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    audit.setdefault("test_batches", [])
    for label, n_tests, method in (
        ("phase7_pairs_exploration", len(pairs_explore), "fdr_bh"),
        ("phase7_pairs_confirmation", len(pairs_candidates), "holm"),
        ("phase7_triplets_exploration", len(triplets_explore), "fdr_bh"),
        ("phase7_triplets_confirmation", len(triplets_candidates), "holm"),
    ):
        audit["test_batches"].append({
            "phase": 7, "label": label, "timestamp": now.isoformat(),
            "number_of_tests": n_tests, "method": method,
        })
    audit["total_tests_registered"] = audit.get("total_tests_registered", 0) + \
        len(pairs_explore) + len(pairs_candidates) + len(triplets_explore) + len(triplets_candidates)
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    deps = {}
    for name in ("pandas", "numpy", "scipy", "statsmodels"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": now.isoformat(), "timestamp": now.isoformat(), "phase": 7,
           "dataset_version": "DATASET_v001", "git_commit": git_head(),
           "python_version": platform.python_version(), "dependencies": deps}
    (ROOT / "logs" / f"run_phase7_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print("\nRapports écrits : reports/PAIRS.md, reports/TRIPLETS.md")
    print("CSV complets : reports/pairs_exploration.csv, reports/triplets_exploration.csv, etc.")
    print(f"Git HEAD : {git_head()}")


if __name__ == "__main__":
    main()
