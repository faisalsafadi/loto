#!/usr/bin/env python3
"""Phase 1 — Import et contrôle du fichier source.

AUCUNE correction, AUCUNE suppression, AUCUN calcul statistique.
Le fichier est copié tel quel dans data/raw/, hashé, puis décrit (structure, comptage).

Usage (depuis la racine du dépôt, venv activé) :
    python scripts/phase1_import.py CHEMIN/vers/loteriema.xlsx [--expected-rows 3159]
"""
import argparse
import hashlib
import json
import platform
import shutil
import stat
import subprocess
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def guard_amendments() -> None:
    """Refuse de lire des données si les amendements A1-A4 ne sont pas en place."""
    checks = [
        (ROOT / "docs/Cahier_des_charges", "AMENDEMENT A1"),
        (ROOT / "docs/IMPLEMENTATION_SPEC.md", "AMENDEMENT A1"),
        (ROOT / "HYPOTHESES.md", "Amendements pré-enregistrés"),
    ]
    for path, needle in checks:
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            sys.exit(f"ARRET : amendement manquant dans {path.relative_to(ROOT)} ('{needle}'). "
                     "Les amendements doivent etre en place AVANT toute lecture des donnees.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--expected-rows", type=int, default=3159)
    args = ap.parse_args()

    guard_amendments()

    src = Path(args.source).expanduser().resolve()
    if not src.is_file():
        sys.exit(f"ARRET : fichier introuvable : {src}")

    raw_dir = ROOT / "data/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    dst = raw_dir / f"loteriema_{now:%Y%m%d}_original.xlsx"
    manifest_path = raw_dir / "MANIFEST.json"
    if dst.exists() or manifest_path.exists():
        sys.exit("ARRET : RAW deja present. Le RAW est immuable : ne pas reimporter.")

    # 1. Copie sans transformation + vérification d'intégrité
    src_hash = sha256(src)
    shutil.copy2(src, dst)
    dst_hash = sha256(dst)
    if src_hash != dst_hash:
        dst.unlink()
        sys.exit("ARRET : hash source != hash copie. Copie supprimee, rien n'a ete importe.")
    dst.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # lecture seule

    # 2. Description structurelle (lecture seule de la copie RAW)
    wb = openpyxl.load_workbook(dst)
    sheets = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(min_row=1, values_only=True))
        header, data = rows[0], rows[1:]
        empty = sum(1 for r in data if all(v is None for v in r))
        types = {
            str(header[j]): dict(Counter(type(r[j]).__name__ for r in data if not all(v is None for v in r)))
            for j in range(len(header)) if header[j] is not None
        }
        sheets.append({
            "name": ws.title, "state": ws.sheet_state, "dimensions": ws.dimensions,
            "header": [None if h is None else str(h) for h in header],
            "data_rows_total": len(data), "data_rows_empty": empty,
            "data_rows_nonempty": len(data) - empty, "cell_types_by_column": types,
            "first_data_row_raw": [str(v) for v in data[0]] if data else None,
            "last_data_row_raw": [str(v) for v in data[-1]] if data else None,
        })
    observed = sheets[0]["data_rows_nonempty"]
    matches = observed == args.expected_rows

    manifest = {
        "filename": src.name, "sha256": dst_hash, "size_bytes": dst.stat().st_size,
        "import_timestamp": now.isoformat(), "source": "user_upload",
        "raw_copy": str(dst.relative_to(ROOT)),
        "rows_expected": args.expected_rows, "rows_observed": observed,
        "row_count_matches_expected": matches,
        "row_count_difference": observed - args.expected_rows,
        "sheets": sheets,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. Journal d'exécution (IMPLEMENTATION_SPEC 49)
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    deps = {}
    for name in ("pandas", "numpy", "openpyxl"):
        try:
            deps[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            deps[name] = "absent"
    run = {"run_id": str(uuid.uuid4()), "timestamp": now.isoformat(), "phase": 1,
           "dataset_version": None, "git_commit": git_head(),
           "python_version": platform.python_version(), "dependencies": deps, "seed": None}
    (logs / f"run_phase1_{now:%Y%m%d_%H%M%S}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    # 4. Rapport console (à coller tel quel)
    print("=== PHASE 1 — IMPORT / CONTROLE (aucune donnee modifiee) ===")
    print(f"Source            : {src}")
    print(f"RAW               : {dst.relative_to(ROOT)}  (lecture seule)")
    print(f"SHA256            : {dst_hash}")
    print(f"Taille            : {dst.stat().st_size} octets")
    for s in sheets:
        print(f"Feuille           : {s['name']!r}  etat={s['state']}  dims={s['dimensions']}")
        print(f"En-tete           : {s['header']}")
        print(f"Lignes de donnees : total={s['data_rows_total']}  vides={s['data_rows_empty']}  non vides={s['data_rows_nonempty']}")
        print(f"Types par colonne : {json.dumps(s['cell_types_by_column'], ensure_ascii=False)}")
        print(f"Premiere ligne    : {s['first_data_row_raw']}")
        print(f"Derniere ligne    : {s['last_data_row_raw']}")
    print(f"Attendu           : {args.expected_rows}")
    print(f"Observe           : {observed}")
    print(f"Ecart             : {observed - args.expected_rows:+d}")
    if matches:
        print("CRITERE COMPTAGE  : SATISFAIT")
    else:
        print("CRITERE COMPTAGE  : NON SATISFAIT -> verdict Phase 1 = BLOCKED (aucun ajustement silencieux)")
    print(f"Git HEAD          : {git_head()}")


if __name__ == "__main__":
    main()
