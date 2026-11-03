#!/usr/bin/env python3
"""Phase 8 — Construction des features.

Un échec du test de non-fuite est un NO-GO BLOQUANT ABSOLU (IMPLEMENTATION_SPEC §36) : aucun
dataset de features n'est sauvegardé si le test échoue, sans exception.

Usage :
    python scripts/phase8_features.py
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

from loto_research.features.build import DEFAULT_WINDOWS, build_feature_dataset
from loto_research.features.leakage import test_no_future_features

ROOT = Path(__file__).resolve().parents[1]
SEED = 42
N_CHECKS = 10


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def guard_amendments():
    checks = [(ROOT / "docs/Cahier_des_charges", "AMENDEMENT A1")]
    for path, needle in checks:
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            sys.exit(f"ARRET : amendement manquant dans {path.relative_to(ROOT)} ('{needle}').")


def main():
    guard_amendments()

    parquet_path = ROOT / "data/analytic/draws.parquet"
    if not parquet_path.exists():
        sys.exit("ARRET : data/analytic/draws.parquet introuvable.")
    df = pd.read_parquet(parquet_path)
    n_draws = len(df)

    print("=== PHASE 8 — CONSTRUCTION DES FEATURES ===")
    print(f"Dataset : {n_draws} tirages (DATASET_v001)")
    print(f"Fenêtres de fréquence glissante : {DEFAULT_WINDOWS}\n")

    print(f"[Test de non-fuite] {N_CHECKS} points de contrôle aléatoires, seed={SEED}...")
    leakage_result = test_no_future_features(df, build_feature_dataset, n_checks=N_CHECKS, seed=SEED)
    print(f"[Test de non-fuite] points testés : {leakage_result['checkpoints_tested']}")
    print(f"[Test de non-fuite] échecs : {leakage_result['failures']}")
    print(f"[Test de non-fuite] PASSÉ : {leakage_result['passed']}")

    if not leakage_result["passed"]:
        print("\n*** NO-GO BLOQUANT ABSOLU (IMPLEMENTATION_SPEC §36) ***")
        print("Une fuite temporelle a été détectée. AUCUN dataset de features n'est sauvegardé.")
        print("Ne pas contourner ce résultat : corriger le code de src/loto_research/features/build.py")
        sys.exit(1)

    print("\nTest de non-fuite réussi. Construction du dataset complet...")
    feats = build_feature_dataset(df, windows=DEFAULT_WINDOWS)

    # Vérification de la dépendance structurelle documentée (IMPLEMENTATION_SPEC §29)
    sums_per_draw = feats.groupby("chronological_id")["target"].sum()
    structural_check_ok = bool((sums_per_draw == 6).all())
    print(f"Vérification structurelle (somme des cibles = 6 par tirage) : {structural_check_ok}")
    if not structural_check_ok:
        sys.exit("ARRET : la dépendance structurelle attendue (6 cibles=1 par tirage) n'est PAS respectée "
                 "— incohérence dans le dataset, à corriger avant de continuer.")

    features_dir = ROOT / "data/features"
    features_dir.mkdir(parents=True, exist_ok=True)
    out_path = features_dir / "FEATURES_v001.parquet"
    if out_path.exists():
        sys.exit("ARRET : FEATURES_v001.parquet existe déjà. Versionner vers v002 si les features changent.")
    feats.to_parquet(out_path, index=False)

    now = datetime.now(timezone.utc)
    manifest = {
        "features_version": "FEATURES_v001",
        "dataset_version": "DATASET_v001",
        "n_draws": n_draws,
        "n_rows": len(feats),
        "windows": list(DEFAULT_WINDOWS),
        "feature_columns": [c for c in feats.columns if c not in ("chronological_id", "number", "target")],
        "leakage_test": leakage_result,
        "structural_check_target_sum_equals_6": structural_check_ok,
        "created_at": now.isoformat(),
    }
    (features_dir / "features_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    deps = {}
    for name in ("pandas", "numpy"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": now.isoformat(), "timestamp": now.isoformat(), "phase": 8,
           "dataset_version": "DATASET_v001", "features_version": "FEATURES_v001",
           "git_commit": git_head(), "python_version": platform.python_version(),
           "dependencies": deps, "seed": SEED, "n_checks": N_CHECKS}
    (ROOT / "logs" / f"run_phase8_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print(f"\nDataset de features : {out_path.relative_to(ROOT)} ({len(feats)} lignes, "
          f"{len(manifest['feature_columns'])} colonnes de features)")
    print(f"Manifest : data/features/features_manifest.json")
    print(f"Git HEAD : {git_head()}")


if __name__ == "__main__":
    main()
