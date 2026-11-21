#!/usr/bin/env python3
"""Phase 4 — Recherche d'anomalies.

Usage :
    python scripts/phase4_anomalies.py
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

from loto_research.anomalies.frequency_anomalies import classify_anomaly_level, per_number_binomial_test
from loto_research.anomalies.position_bias import position_uniformity_tests
from loto_research.statistics.multiple_testing import bonferroni, fdr_bh, holm
from loto_research.validation.schema import NUMBER_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def guard_amendments():
    checks = [
        (ROOT / "docs/Cahier_des_charges", "AMENDEMENT A1"),
        (ROOT / "HYPOTHESES.md", "A7"),
    ]
    for path, needle in checks:
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            sys.exit(f"ARRET : amendement manquant dans {path.relative_to(ROOT)} ('{needle}').")


def format_frequency_flags(res_df):
    """res_df : colonnes number, count, expected, raw_p_value, adjusted_p_value, level."""
    flagged = res_df[res_df["level"] == "B"]
    if len(flagged) == 0:
        return "  Aucun numéro de niveau B."
    return "\n".join(
        f"  - numéro {int(r.number):2d} : count={r.count} (attendu {r.expected:.1f}), "
        f"p_brut={r.raw_p_value:.5g}, p_ajusté={r.adjusted_p_value:.5g}"
        for r in flagged.itertuples()
    )


def format_position_flags(res_df):
    """res_df : colonnes position, chi2, df, p_value, n, ..., adjusted_p_value, level."""
    flagged = res_df[res_df["level"] == "B"]
    if len(flagged) == 0:
        return "  Aucune position de niveau B."
    return "\n".join(
        f"  - {r.position} : chi2={r.chi2:.2f} (df={r.df}), "
        f"p_brut={r.p_value:.5g}, p_ajusté={r.adjusted_p_value:.5g}"
        for r in flagged.itertuples()
    )


def main():
    guard_amendments()

    parquet_path = ROOT / "data/analytic/draws.parquet"
    if not parquet_path.exists():
        sys.exit("ARRET : data/analytic/draws.parquet introuvable. Lancer la Phase 2 d'abord.")
    df = pd.read_parquet(parquet_path)
    n_draws = len(df)

    print("=== PHASE 4 — RECHERCHE D'ANOMALIES ===")
    print(f"Dataset : {n_draws} tirages (DATASET_v001)\n")

    # --- A. Fréquence par numéro principal (49 tests, correction Holm — pré-enregistrée H001) ---
    main_res = per_number_binomial_test(df, NUMBER_COLUMNS, p=6 / 49)
    main_corr = holm(main_res["raw_p_value"].tolist(), alpha=0.05)
    main_res["adjusted_p_value"] = main_corr["adjusted_p_value"]
    main_res["level"] = main_res["adjusted_p_value"].apply(classify_anomaly_level)
    print("[A] Fréquence par numéro PRINCIPAL (49 tests, Holm) :")
    print(format_frequency_flags(main_res))

    # --- B. Fréquence par numéro du COMPLÉMENTAIRE (49 tests, FDR-BH — EXPLORATOIRE, Phase 4) ---
    bonus_res = per_number_binomial_test(df, ["bonus"], p=1 / 49)
    bonus_corr = fdr_bh(bonus_res["raw_p_value"].tolist(), alpha=0.05)
    bonus_res["adjusted_p_value"] = bonus_corr["adjusted_p_value"]
    bonus_res["level"] = bonus_res["adjusted_p_value"].apply(classify_anomaly_level)
    print("\n[B] Fréquence par numéro du COMPLÉMENTAIRE (49 tests, FDR-BH, EXPLORATOIRE) :")
    print(format_frequency_flags(bonus_res))

    # --- C. Biais de position (6 tests, Bonferroni — EXPLORATOIRE, ordre de tirage non confirmé) ---
    pos_res = position_uniformity_tests(df)
    pos_corr = bonferroni(pos_res["p_value"].tolist(), alpha=0.05)
    pos_res["adjusted_p_value"] = pos_corr["adjusted_p_value"]
    pos_res["level"] = pos_res["adjusted_p_value"].apply(classify_anomaly_level)
    print("\n[C] Biais de POSITION (6 tests, Bonferroni, EXPLORATOIRE) :")
    print(format_position_flags(pos_res))

    n_level_b = int((main_res["level"] == "B").sum() + (bonus_res["level"] == "B").sum()
                     + (pos_res["level"] == "B").sum())
    total_tests = main_corr["number_of_tests"] + bonus_corr["number_of_tests"] + pos_corr["number_of_tests"]
    print(f"\nTotal numéros/positions de niveau B (avant Phase 5/7) : {n_level_b} / {total_tests} tests")

    # --- Rapport ---
    now = datetime.now(timezone.utc)
    lines = [
        "# ANOMALY_REPORT.md", "",
        "## LOTO MAROC Research Engine — Recherche d'anomalies (Phase 4)", "",
        f"Généré le {now.isoformat()}. Dataset : DATASET_v001, {n_draws} tirages.", "",
        "Aucune anomalie de ce rapport n'est présentée sans sa p-value corrigée. Aucune anomalie, "
        "quel que soit son niveau, n'est interprétée comme une preuve de fraude ou de trucage "
        "(Cahier des charges §37) — au plus, une anomalie statistique nécessitant investigation.", "",
        "**Absence d'information physique** : aucune donnée sur l'état, l'usure ou la calibration des "
        "boules et de la machine n'est disponible (RESEARCH_REVIEW.md §1.2) ; toute anomalie de "
        "fréquence ou de position reste une observation statistique, jamais une preuve mécanique.", "",

        "## OBSERVATION", "",
        f"- [A] Fréquence par numéro principal : {main_corr['number_of_tests']} tests "
        f"(méthode {main_corr['method']}, pré-enregistrée H001).",
        f"- [B] Fréquence par numéro du complémentaire : {bonus_corr['number_of_tests']} tests "
        f"(méthode {bonus_corr['method']}, EXPLORATOIRE — approfondit le signal Niveau B de la Phase 3).",
        f"- [C] Biais de position (n1..n6) : {pos_corr['number_of_tests']} tests "
        f"(méthode {pos_corr['method']}, EXPLORATOIRE — hypothèse NON confirmée que ces colonnes "
        "représentent l'ordre réel de tirage).",
        f"- Total : {total_tests} tests.",
        "",

        "## CALCUL", "",
        "### [A] Numéros principaux — niveau B après correction Holm",
        format_frequency_flags(main_res), "",
        "### [B] Complémentaire — niveau B après correction FDR-BH",
        format_frequency_flags(bonus_res), "",
        "### [C] Positions — niveau B après correction Bonferroni",
        format_position_flags(pos_res), "",

        "## INTERPRÉTATION", "",
        f"- {n_level_b} numéro(s)/position(s) de niveau B détecté(s) au total sur {total_tests} tests, "
        "après correction pour comparaisons multiples propre à chaque famille.",
        "- Le Niveau B signifie « anomalie statistique brute » (Cahier §2) : cela NE constitue PAS un "
        "Niveau C (anomalie robuste), qui exige la survie à une investigation multi-période/indépendante "
        "(Phases 5 et 7), ni a fortiori un Niveau D (pouvoir prédictif, Phase 10).",
        "- [B] et [C] sont des recherches EXPLORATOIRES au sens de HYPOTHESES.md : toute anomalie qui y "
        "serait détectée doit être ajoutée à HYPOTHESES.md comme POST_HOC avant d'être creusée plus loin.",
        "",

        "## LIMITATION", "",
        "- [C] repose sur une hypothèse NON vérifiée (colonnes = ordre réel de tirage). Un résultat "
        "significatif ici pourrait aussi bien refléter un artefact de saisie qu'un biais mécanique réel : "
        "aucune conclusion mécanique ne peut être tirée sans confirmation de la source des données.",
        "- La correction multiple est appliquée PAR FAMILLE (A, B, C séparément), pas globalement sur "
        "l'ensemble du projet — une correction globale de bout en bout est prévue en synthèse finale (Phase 14).",
        "- Les tests exacts (binomiaux, position) ne souffrent pas de la corrélation intra-tirage qui "
        "affecte le test joint des 6 numéros (Phase 3, amendement A1) : ils testent chaque numéro/position "
        "indépendamment, ce qui est statistiquement valide mais ne teste pas les dépendances conjointes "
        "(paires/triplets, prévues Phase 7).",
    ]
    (ROOT / "reports/ANOMALY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # --- research_audit.json : journalisation systématique (IMPLEMENTATION_SPEC §16, §56) ---
    audit_path = ROOT / "research_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    audit.setdefault("test_batches", [])
    for label, corr in (("phase4_main_numbers", main_corr), ("phase4_bonus_numbers", bonus_corr),
                         ("phase4_positions", pos_corr)):
        audit["test_batches"].append({
            "phase": 4, "label": label, "timestamp": now.isoformat(),
            "number_of_tests": corr["number_of_tests"], "method": corr["method"], "alpha": corr["alpha"],
        })
    audit["total_tests_registered"] = audit.get("total_tests_registered", 0) + total_tests
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    deps = {}
    for name in ("pandas", "numpy", "scipy", "statsmodels"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": now.isoformat(), "timestamp": now.isoformat(), "phase": 4,
           "dataset_version": "DATASET_v001", "git_commit": git_head(),
           "python_version": platform.python_version(), "dependencies": deps}
    (ROOT / "logs" / f"run_phase4_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print("\nRapport ecrit : reports/ANOMALY_REPORT.md")
    print("research_audit.json mis a jour")
    print(f"Git HEAD : {git_head()}")


if __name__ == "__main__":
    main()
