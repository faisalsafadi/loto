#!/usr/bin/env python3
"""Phase 5 — Addendum : détection de rupture (CUSUM + ruptures) et autocorrélation par numéro.

Complète des actions prévues au Cahier §19 / EXECUTION_PLAN Phase 5, omises au premier passage.

Usage :
    python scripts/phase5b_addendum.py --n-permutations 2000 --quick-test
    python scripts/phase5b_addendum.py
"""
import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loto_research.statistics.multiple_testing import fdr_bh
from loto_research.temporal.autocorrelation import per_number_autocorrelation
from loto_research.temporal.changepoint import cusum_permutation_test, ruptures_pelt_breakpoints
from loto_research.validation.schema import NUMBER_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_N_PERMUTATIONS = 20000
SEED = 42
CALENDAR_CHANGE_WINDOW = (pd.Timestamp("2015-01-01"), pd.Timestamp("2016-12-31"))


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def guard_amendments():
    checks = [
        (ROOT / "docs/Cahier_des_charges", "AMENDEMENT A1"),
        (ROOT / "HYPOTHESES.md", "A6 — Changement de calendrier"),
    ]
    for path, needle in checks:
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            sys.exit(f"ARRET : amendement manquant dans {path.relative_to(ROOT)} ('{needle}').")


def calendar_note(cp_date):
    in_window = CALENDAR_CHANGE_WINDOW[0] <= cp_date <= CALENDAR_CHANGE_WINDOW[1]
    if in_window:
        return ("tombe **dans la fenêtre du changement de calendrier connu (2015-2016, amendement A6)** "
                ": à attribuer à ce changement de fréquence en premier lieu, pas à une anomalie.")
    return "ne tombe PAS dans la fenêtre du changement de calendrier connu (2015-2016)."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-permutations", type=int, default=None)
    ap.add_argument("--quick-test", action="store_true")
    args = ap.parse_args()

    guard_amendments()

    n_permutations = args.n_permutations or DEFAULT_N_PERMUTATIONS
    is_official_run = (not args.quick_test) and args.n_permutations is None

    parquet_path = ROOT / "data/analytic/draws.parquet"
    if not parquet_path.exists():
        sys.exit("ARRET : data/analytic/draws.parquet introuvable.")
    df = pd.read_parquet(parquet_path).sort_values("chronological_id").reset_index(drop=True)
    n_draws = len(df)

    print("=== PHASE 5 ADDENDUM — RUPTURE ET AUTOCORRÉLATION ===")
    print(f"Dataset : {n_draws} tirages")
    print(f"{'RUN OFFICIEL' if is_official_run else 'ESSAI / TEST (pas confirmatoire)'} "
          f"— n_permutations={n_permutations}\n")

    # --- CUSUM : somme des 6 principaux ---
    sums = df[NUMBER_COLUMNS].sum(axis=1).to_numpy()
    t0 = time.time()
    cusum_sum = cusum_permutation_test(sums, n_permutations, SEED, progress=True)
    elapsed_sum = time.time() - t0
    cp_date_sum = df["date"].iloc[cusum_sum["changepoint_index"]]
    print(f"[CUSUM somme] rupture la plus probable après le {cp_date_sum.date()} "
          f"(moyenne avant={cusum_sum['mean_before']:.2f}, après={cusum_sum['mean_after']:.2f}), "
          f"p_permutation={cusum_sum['p_value_permutation']:.5f}  ({elapsed_sum:.1f}s)")

    # --- CUSUM : valeur du complémentaire ---
    bonus = df["bonus"].to_numpy()
    t0 = time.time()
    cusum_bonus = cusum_permutation_test(bonus, n_permutations, SEED, progress=True)
    elapsed_bonus = time.time() - t0
    cp_date_bonus = df["date"].iloc[cusum_bonus["changepoint_index"]]
    print(f"[CUSUM complémentaire] rupture la plus probable après le {cp_date_bonus.date()} "
          f"(moyenne avant={cusum_bonus['mean_before']:.2f}, après={cusum_bonus['mean_after']:.2f}), "
          f"p_permutation={cusum_bonus['p_value_permutation']:.5f}  ({elapsed_bonus:.1f}s)")

    # --- ruptures (Pelt) : recoupement descriptif, sans p-value ---
    rpt_sum = ruptures_pelt_breakpoints(sums)
    rpt_bonus = ruptures_pelt_breakpoints(bonus)
    print(f"\n[ruptures.Pelt, descriptif] somme : {rpt_sum}")
    print(f"[ruptures.Pelt, descriptif] complémentaire : {rpt_bonus}")

    if not is_official_run:
        print("\n(Section non écrite : ceci est un essai. Relancer sans option pour le run officiel.)")
        return

    # --- Autocorrélation lag-1 par numéro (EXPLORATOIRE) ---
    ac_main = per_number_autocorrelation(df, NUMBER_COLUMNS)
    ac_main_corr = fdr_bh(ac_main["p_value"].tolist(), alpha=0.05)
    ac_main["adjusted_p_value"] = ac_main_corr["adjusted_p_value"]
    n_flagged_main = int((np.array(ac_main_corr["adjusted_p_value"]) < 0.05).sum())

    ac_bonus = per_number_autocorrelation(df, ["bonus"])
    ac_bonus_corr = fdr_bh(ac_bonus["p_value"].tolist(), alpha=0.05)
    ac_bonus["adjusted_p_value"] = ac_bonus_corr["adjusted_p_value"]
    n_flagged_bonus = int((np.array(ac_bonus_corr["adjusted_p_value"]) < 0.05).sum())

    print(f"\n[Autocorrélation lag-1, EXPLORATOIRE] principaux : {n_flagged_main}/49 après FDR-BH")
    print(f"[Autocorrélation lag-1, EXPLORATOIRE] complémentaire : {n_flagged_bonus}/49 après FDR-BH")

    # --- Rapport : AJOUT à TEMPORAL_REPORT.md existant (ne pas écraser) ---
    now = datetime.now(timezone.utc)
    report_path = ROOT / "reports/TEMPORAL_REPORT.md"
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else "# TEMPORAL_REPORT.md\n"

    addendum = [
        "", "---", "",
        "## ADDENDUM — Détection de rupture et autocorrélation par numéro", "",
        f"Ajouté le {now.isoformat()}. Complète des actions de Phase 5 prévues au Cahier §19 et à "
        "l'EXECUTION_PLAN (CUSUM/ruptures, mémoire temporelle), omises au premier passage — identifiées "
        "en relisant `a_lire` (module « PHYSICS-BIAS » proposé, points 3, 4, 6).", "",

        "### OBSERVATION", "",
        f"- CUSUM (test PRIMAIRE de cet addendum, permutation, {n_permutations} perm., seed {SEED}) sur "
        f"la somme des 6 principaux : rupture la plus probable après le **{cp_date_sum.date()}** "
        f"(moyenne avant={cusum_sum['mean_before']:.2f}, après={cusum_sum['mean_after']:.2f}), "
        f"p={cusum_sum['p_value_permutation']:.5f}.",
        f"- CUSUM sur le complémentaire : rupture la plus probable après le **{cp_date_bonus.date()}** "
        f"(moyenne avant={cusum_bonus['mean_before']:.2f}, après={cusum_bonus['mean_after']:.2f}), "
        f"p={cusum_bonus['p_value_permutation']:.5f}.",
        f"- `ruptures.Pelt` (descriptif, sans p-value, pénalité BIC pré-spécifiée) — somme : "
        f"{rpt_sum} ; complémentaire : {rpt_bonus}.",
        f"- Autocorrélation lag-1 (EXPLORATOIRE, FDR-BH) : {n_flagged_main}/49 numéros principaux et "
        f"{n_flagged_bonus}/49 valeurs du complémentaire significatifs après correction.",
        "",

        "### INTERPRÉTATION", "",
        f"- La rupture CUSUM de la somme {calendar_note(cp_date_sum)}",
        f"- La rupture CUSUM du complémentaire {calendar_note(cp_date_bonus)}",
        f"- Sous H0 (aucune structure), on attend ~{0.05 * 49:.1f} faux positifs par famille de 49 tests "
        "avant correction : le nombre flagué après FDR-BH doit être interprété à cette aune.",
        "- `ruptures.Pelt` est purement descriptif ici (pas de loi nulle calibrée pour sa pénalité) : "
        "il sert de recoupement visuel avec le CUSUM, pas de preuve indépendante.",
        "",

        "### LIMITATION", "",
        "- Le CUSUM ne détecte qu'UNE seule rupture dans la MOYENNE du signal ; un changement de variance "
        "ou de forme sans changement de moyenne, ou plusieurs ruptures successives, ne serait pas détecté "
        "par cette méthode seule (voir `ruptures.Pelt` en recoupement, lui aussi limité).",
        "- Les tirages numérotés absents (~33, amendement A5) ne sont pas comblés dans la séquence "
        "utilisée : ils sont simplement absents, ce qui peut légèrement décaler la position exacte "
        "d'une rupture détectée.",
        "- L'autocorrélation est EXPLORATOIRE (non pré-enregistrée avant la Phase 1) : tout numéro "
        "flagué ici doit être ajouté à HYPOTHESES.md comme POST_HOC avant toute investigation "
        "ultérieure, jamais présenté comme confirmatoire.",
    ]
    report_path.write_text(existing.rstrip("\n") + "\n" + "\n".join(addendum) + "\n", encoding="utf-8")

    audit_path = ROOT / "research_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    audit.setdefault("test_batches", [])
    for label, n_tests, method in (
        ("phase5b_cusum_sum", 1, "cusum_permutation"),
        ("phase5b_cusum_bonus", 1, "cusum_permutation"),
        ("phase5b_autocorrelation_main", 49, "fdr_bh"),
        ("phase5b_autocorrelation_bonus", 49, "fdr_bh"),
    ):
        audit["test_batches"].append({
            "phase": "5b", "label": label, "timestamp": now.isoformat(),
            "number_of_tests": n_tests, "method": method,
        })
    audit["total_tests_registered"] = audit.get("total_tests_registered", 0) + 1 + 1 + 49 + 49
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    deps = {}
    for name in ("pandas", "numpy", "scipy", "ruptures"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": now.isoformat(), "timestamp": now.isoformat(), "phase": "5b",
           "dataset_version": "DATASET_v001", "git_commit": git_head(),
           "python_version": platform.python_version(), "dependencies": deps,
           "seed": SEED, "n_permutations": n_permutations}
    (ROOT / "logs" / f"run_phase5b_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print("\nAddendum ajouté à reports/TEMPORAL_REPORT.md")
    print(f"Git HEAD : {git_head()}")


if __name__ == "__main__":
    main()
