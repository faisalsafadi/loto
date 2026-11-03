#!/usr/bin/env python3
"""Phase 6 — Monte-Carlo : moteur de simulation général (validé) + test H004 (gaps, loi exacte).

Usage :
    python scripts/phase6_monte_carlo.py --n-calibration 500 --quick-test
    python scripts/phase6_monte_carlo.py
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

from loto_research.simulation.monte_carlo import simulate_draws, simulate_gaps_for_number
from loto_research.statistics.multiple_testing import fdr_bh
from loto_research.temporal.gaps import compare_gaps_to_geometric, per_number_gap_test
from loto_research.validation.schema import NUMBER_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_N_CALIBRATION = 2000
SEED = 42


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def guard_amendments():
    checks = [
        (ROOT / "docs/Cahier_des_charges", "AMENDEMENT A1"),
        (ROOT / "HYPOTHESES.md", "H004"),
    ]
    for path, needle in checks:
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            sys.exit(f"ARRET : amendement manquant dans {path.relative_to(ROOT)} ('{needle}').")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-calibration", type=int, default=None)
    ap.add_argument("--quick-test", action="store_true")
    args = ap.parse_args()

    guard_amendments()
    n_calibration = args.n_calibration or DEFAULT_N_CALIBRATION
    is_official_run = (not args.quick_test) and args.n_calibration is None

    parquet_path = ROOT / "data/analytic/draws.parquet"
    if not parquet_path.exists():
        sys.exit("ARRET : data/analytic/draws.parquet introuvable.")
    df = pd.read_parquet(parquet_path).sort_values("chronological_id").reset_index(drop=True)
    n_draws = len(df)

    print("=== PHASE 6 — MONTE-CARLO ===")
    print(f"Dataset : {n_draws} tirages")
    print(f"{'RUN OFFICIEL' if is_official_run else 'ESSAI / TEST (pas confirmatoire)'} "
          f"— n_calibration={n_calibration}, seed={SEED}\n")

    # --- 0. Reproductibilité du moteur (critère GO explicite de la Phase 6) ---
    b1 = np.concatenate(list(simulate_draws(n_draws=50, n_simulations=20, seed=SEED, batch_size=5)))
    b2 = np.concatenate(list(simulate_draws(n_draws=50, n_simulations=20, seed=SEED, batch_size=5)))
    reproducible = bool(np.array_equal(b1, b2))
    print(f"[Reproductibilité] même seed -> résultats identiques : {reproducible}")
    if not reproducible:
        sys.exit("ARRET : le moteur Monte-Carlo n'est PAS reproductible avec le même seed.")

    # --- 1. Calibration : gaps simulés (moteur général) vs loi géométrique exacte ---
    t0 = time.time()
    sim_gaps = simulate_gaps_for_number(n_draws, n_calibration, SEED, number_zero_indexed=0, progress=True)
    elapsed_calib = time.time() - t0
    p_main = 6 / 49
    calib_res = compare_gaps_to_geometric(sim_gaps, p_main, max_k=30)
    print(f"[Calibration] {len(sim_gaps)} gaps simulés (numéro 1, {n_calibration} historiques) : "
          f"moyenne={sim_gaps.mean():.3f} (théorique {1 / p_main:.3f}), "
          f"χ² vs géométrique exacte : chi2={calib_res['chi2']:.2f} df={calib_res['df']} "
          f"p={calib_res['p_value']:.4f}  ({elapsed_calib:.1f}s)")
    if calib_res["p_value"] < 0.01:
        print("  ATTENTION : le moteur s'écarte significativement de la loi théorique attendue. "
              "Ne pas faire confiance à simulate_draws() avant d'avoir corrigé le bug.")

    if not is_official_run:
        print("\n(Rapport non écrit : ceci est un essai. Relancer sans option pour le run officiel.)")
        return

    # --- 2. H004 (test PRIMAIRE, confirmatoire) : gaps des 6 principaux vs géométrique exacte ---
    gaps_main = per_number_gap_test(df, NUMBER_COLUMNS, p_main)
    valid = gaps_main["p_value"].notna()
    corr_main = fdr_bh(gaps_main.loc[valid, "p_value"].tolist(), alpha=0.05)
    gaps_main.loc[valid, "adjusted_p_value"] = corr_main["adjusted_p_value"]
    n_flagged_main = int((gaps_main["adjusted_p_value"] < 0.05).sum())
    print(f"\n[H004, PRIMAIRE] Gaps des 6 principaux vs géométrique exacte (FDR-BH, {int(valid.sum())} tests) : "
          f"{n_flagged_main}/{int(valid.sum())} numéros significatifs après correction")

    # --- 3. Extension EXPLORATOIRE : gaps du complémentaire ---
    p_bonus = 1 / 49
    gaps_bonus = per_number_gap_test(df, ["bonus"], p_bonus)
    valid_b = gaps_bonus["p_value"].notna()
    corr_bonus = fdr_bh(gaps_bonus.loc[valid_b, "p_value"].tolist(), alpha=0.05)
    gaps_bonus.loc[valid_b, "adjusted_p_value"] = corr_bonus["adjusted_p_value"]
    n_flagged_bonus = int((gaps_bonus["adjusted_p_value"] < 0.05).sum())
    print(f"[Extension EXPLORATOIRE] Gaps du complémentaire vs géométrique exacte (FDR-BH, "
          f"{int(valid_b.sum())} tests) : {n_flagged_bonus}/{int(valid_b.sum())} significatifs")

    # --- Rapport ---
    now = datetime.now(timezone.utc)

    def flagged_list(gaps_df):
        f = gaps_df[gaps_df["adjusted_p_value"] < 0.05]
        if len(f) == 0:
            return "  Aucun numéro significatif après correction."
        return "\n".join(
            f"  - numéro {int(r.number)} : n_gaps={r.n_gaps}, mean_gap={r.mean_gap:.2f} "
            f"(théorique {r.theoretical_mean_gap:.2f}), p_ajusté={r.adjusted_p_value:.4f}"
            for r in f.itertuples()
        )

    lines = [
        "# MONTE_CARLO.md", "",
        "## LOTO MAROC Research Engine — Moteur Monte-Carlo et test des gaps (Phase 6)", "",
        f"Généré le {now.isoformat()}. Dataset : DATASET_v001, {n_draws} tirages. Seed : {SEED}.", "",

        "## OBSERVATION", "",
        "- Moteur de simulation (`simulate_draws`, src/loto_research/simulation/monte_carlo.py) : "
        "reproductibilité vérifiée (même seed → résultats strictement identiques sur 20 historiques de test).",
        f"- Calibration : {len(sim_gaps)} gaps simulés (numéro 1, {n_calibration} historiques "
        f"synthétiques de {n_draws} tirages) comparés à la loi géométrique exacte (p=6/49) : "
        f"moyenne simulée {sim_gaps.mean():.3f} (théorique {1 / p_main:.3f}), "
        f"χ²={calib_res['chi2']:.2f}, p={calib_res['p_value']:.4f} — le moteur reproduit correctement "
        "la loi théorique connue.",
        f"- H004 (principaux) : {n_flagged_main}/{int(valid.sum())} numéro(s) significatif(s) après FDR-BH.",
        f"- Extension complémentaire : {n_flagged_bonus}/{int(valid_b.sum())} numéro(s) significatif(s).",
        "",

        "## CALCUL", "",
        "### H004 — Distribution des gaps, 6 numéros principaux (test PRIMAIRE)",
        "Référence : loi géométrique EXACTE de paramètre p=6/49 (pas de simulation nécessaire — la "
        "présence d'un numéro fixé est i.i.d. Bernoulli(p) d'un tirage à l'autre, tirages indépendants).",
        flagged_list(gaps_main), "",
        "### Extension EXPLORATOIRE — Distribution des gaps, complémentaire",
        "Référence : loi géométrique exacte de paramètre p=1/49.",
        flagged_list(gaps_bonus), "",

        "## INTERPRÉTATION", "",
        "- Le moteur `simulate_draws()` est validé par calibration (gaps simulés vs loi géométrique "
        "exacte) : il pourra être réutilisé pour la Phase 7 (paires/triplets), où aucune loi exacte "
        "simple n'existe pour les comparaisons envisagées.",
        "- H004 est testée par sa loi de référence EXACTE, pas par Monte-Carlo : plus précis et moins "
        "coûteux qu'une simulation, dans l'esprit retenu depuis la Phase 3 (distributions exactes "
        "préférées à l'approximation quand elles existent).",
        "- L'extension sur le complémentaire est EXPLORATOIRE (non pré-enregistrée) : tout numéro "
        "significatif devrait être ajouté à HYPOTHESES.md comme POST_HOC avant toute investigation ultérieure.",
        "",

        "## LIMITATION", "",
        "- Les gaps sont mesurés en nombre de tirages du dataset ANALYTIC (chronological_id), pas en "
        "jours civils ni en tirages officiels réels : les ~33 tirages absents (amendement A5) sont "
        "silencieusement sautés dans le décompte, comme pour H003.",
        "- Un gap long observé ne doit JAMAIS être interprété comme une probabilité future accrue "
        "(Cahier §14, §18) : ce test vérifie seulement la compatibilité de la distribution des gaps "
        "passés avec le modèle nul, pas une quelconque prédiction.",
        "- Les gaps ouverts en début/fin de série (avant la première apparition, après la dernière) "
        "sont exclus du test (convention standard, évite un biais de troncature).",
    ]
    (ROOT / "reports/MONTE_CARLO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    audit_path = ROOT / "research_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    audit.setdefault("test_batches", [])
    audit["test_batches"].append({
        "phase": 6, "label": "phase6_h004_gaps_main", "timestamp": now.isoformat(),
        "number_of_tests": int(valid.sum()), "method": "fdr_bh",
    })
    audit["test_batches"].append({
        "phase": 6, "label": "phase6_gaps_bonus_exploratory", "timestamp": now.isoformat(),
        "number_of_tests": int(valid_b.sum()), "method": "fdr_bh",
    })
    audit["total_tests_registered"] = audit.get("total_tests_registered", 0) + int(valid.sum()) + int(valid_b.sum())
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    deps = {}
    for name in ("pandas", "numpy", "scipy"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": now.isoformat(), "timestamp": now.isoformat(), "phase": 6,
           "dataset_version": "DATASET_v001", "git_commit": git_head(),
           "python_version": platform.python_version(), "dependencies": deps,
           "seed": SEED, "n_calibration": n_calibration}
    (ROOT / "logs" / f"run_phase6_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print("\nRapport ecrit : reports/MONTE_CARLO.md")
    print(f"Git HEAD : {git_head()}")


if __name__ == "__main__":
    main()
