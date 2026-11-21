#!/usr/bin/env python3
"""Phase 2 — Validation / nettoyage.

Usage (depuis la racine du dépôt, venv activé) :
    python scripts/phase2_validate.py --expected-rows 3159
"""
import argparse
import json
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loto_research.validation.load_raw import load_raw
from loto_research.cleaning.build_analytic import build_analytic, split_duplicate_dates, split_valid_invalid
from loto_research.reporting.quality_report import build_report

ROOT = Path(__file__).resolve().parents[1]


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def guard_amendments():
    checks = [
        (ROOT / "docs/Cahier_des_charges", "AMENDEMENT A1"),
        (ROOT / "docs/IMPLEMENTATION_SPEC.md", "AMENDEMENT A1"),
        (ROOT / "HYPOTHESES.md", "A5 — Tirages consécutifs"),
    ]
    for path, needle in checks:
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            sys.exit(f"ARRET : amendement manquant dans {path.relative_to(ROOT)} ('{needle}').")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected-rows", type=int, default=3159)
    args = ap.parse_args()

    guard_amendments()

    raw_files = sorted((ROOT / "data/raw").glob("loteriema_*_original.xlsx"))
    if len(raw_files) != 1:
        sys.exit(f"ARRET : attendu 1 fichier RAW, trouvé {len(raw_files)} : {raw_files}")
    raw_path = raw_files[0]

    manifest = json.loads((ROOT / "data/raw/MANIFEST.json").read_text(encoding="utf-8"))

    header, records, n_empty = load_raw(raw_path)
    valid_df, invalid_df = split_valid_invalid(records)
    kept, all_dup_df, removed_df = split_duplicate_dates(valid_df)
    analytic_df = build_analytic(kept)

    validated_dir = ROOT / "data/validated"
    validated_dir.mkdir(parents=True, exist_ok=True)
    invalid_df.to_csv(validated_dir / "invalid_records.csv", index=False)
    all_dup_df.to_csv(validated_dir / "duplicate_dates.csv", index=False)
    removed_df.to_csv(validated_dir / "removed_duplicate_dates.csv", index=False)

    analytic_dir = ROOT / "data/analytic"
    analytic_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = analytic_dir / "draws.parquet"
    if parquet_path.exists():
        sys.exit("ARRET : draws.parquet existe deja. ANALYTIC est immuable pour une version donnee "
                 "(IMPLEMENTATION_SPEC §11) : supprimer manuellement pour reconstruire une NOUVELLE version, "
                 "en renommant vers DATASET_v002 si une donnee/regle a change.")
    analytic_df.to_parquet(parquet_path, index=False)

    now = datetime.now(timezone.utc)
    dataset_manifest = {
        "dataset_version": "DATASET_v001",
        "source_hash": manifest["sha256"],
        "row_count": len(analytic_df),
        "date_min": str(analytic_df["date"].min().date()),
        "date_max": str(analytic_df["date"].max().date()),
        "created_at": now.isoformat(),
    }
    (analytic_dir / "dataset_manifest.json").write_text(
        json.dumps(dataset_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    report = build_report(header, n_empty, records, invalid_df, all_dup_df, removed_df, analytic_df, args.expected_rows)
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "DATA_QUALITY_REPORT.md").write_text(report, encoding="utf-8")

    deps = {}
    for name in ("pandas", "numpy", "pyarrow", "openpyxl"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    run = {"run_id": str(uuid.uuid4()), "timestamp": now.isoformat(), "phase": 2,
           "dataset_version": "DATASET_v001", "git_commit": git_head(),
           "python_version": platform.python_version(), "dependencies": deps, "seed": None}
    (logs_dir / f"run_phase2_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    print("=== PHASE 2 — VALIDATION / NETTOYAGE ===")
    print(f"RAW                        : {raw_path.relative_to(ROOT)}")
    print(f"Lignes RAW (non vides)     : {len(records)}  (vides ignorees : {n_empty})")
    print(f"Lignes invalides (V001-V005): {len(invalid_df)}  -> data/validated/invalid_records.csv")
    print(f"Dates dupliquees           : {len(all_dup_df)}  (supprimees ANALYTIC: {len(removed_df)}) -> data/validated/duplicate_dates.csv")
    print(f"ANALYTIC (DATASET_v001)    : {len(analytic_df)} lignes -> data/analytic/draws.parquet")
    print(f"Plage de dates             : {dataset_manifest['date_min']} -> {dataset_manifest['date_max']}")
    print("--- flags (non bloquants) ---")
    flat = [f for row in analytic_df["flags"] for f in (row.split(";") if row else []) if f]
    from collections import Counter
    for kind, n in sorted(Counter(f.split(":")[0] for f in flat).items(), key=lambda x: -x[1]):
        print(f"  {kind:20} {n}")
    bonus_in_main = sum(1 for f in flat if f == "BONUS_IN_MAIN")
    print(f"--- H002 : BONUS_IN_MAIN = {bonus_in_main} / {len(analytic_df)} ({bonus_in_main/len(analytic_df):.2%}) ---")
    print(f"Rapport ecrit              : reports/DATA_QUALITY_REPORT.md")
    print(f"Git HEAD                   : {git_head()}")
    if len(invalid_df) or len(all_dup_df):
        print("\nCRITERE GO : verifier reports/DATA_QUALITY_REPORT.md avant de valider la phase.")
    else:
        print("\nCRITERE GO : 0 ligne invalide, 0 date dupliquee -> conforme au diagnostic Phase 1.")


if __name__ == "__main__":
    main()
