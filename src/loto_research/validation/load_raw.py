"""Lecture du fichier RAW : valeurs brutes, aucune correction, aucune suppression."""
from pathlib import Path

import openpyxl

from loto_research.validation.rules import missing_required_columns
from loto_research.validation.schema import RAW_HEADER


def load_raw(path):
    """Retourne (header, records, n_empty).

    records : liste de dicts {source_row, draw_number, mains, bonus, date}
    (source_row = numéro de ligne Excel, en-tête = ligne 1).
    Lève ValueError si l'en-tête ne correspond pas au schéma attendu (V006).
    """
    wb = openpyxl.load_workbook(Path(path))
    ws = wb.worksheets[0]
    rows = ws.iter_rows(min_row=1, values_only=True)
    header = list(next(rows))

    missing = missing_required_columns(header)
    if missing:
        raise ValueError(f"V006 : colonnes manquantes : {missing}")
    if [None if h is None else str(h) for h in header[:9]] != RAW_HEADER:
        raise ValueError(f"En-tête inattendu (ordre des colonnes) : {header[:9]}")

    records, n_empty = [], 0
    for excel_row, r in enumerate(rows, start=2):
        if all(v is None for v in r):
            n_empty += 1
            continue
        records.append({
            "source_row": excel_row,
            "draw_number": r[0],
            "mains": list(r[1:7]),
            "bonus": r[7],
            "date": r[8],
        })
    return header, records, n_empty
