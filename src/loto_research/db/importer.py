"""Import d'un dataset v1 (parquet) dans la base, en une seule transaction (SPEC_V2 §10, M1)."""
import pandas as pd

from loto_research.db.core import ValidationError, add_draw

NUMBER_COLUMNS = [f"n{i}" for i in range(1, 7)]
DATE_CANDIDATES = ("date", "draw_date")


def import_v1_parquet(conn, game_id, parquet_path, source, source_ref):
    """Insère les tirages de DATASET_v001 dans l'ordre chronologique. Si une ligne est refusée par
    la validation, la transaction entière est annulée : jamais d'import partiel, jamais de
    correction silencieuse. Retourne le nombre de tirages insérés."""
    df = pd.read_parquet(parquet_path)
    date_col = next((c for c in DATE_CANDIDATES if c in df.columns), None)
    if date_col is None:
        raise ValidationError(f"Aucune colonne de date trouvée parmi {DATE_CANDIDATES}. "
                              f"Colonnes disponibles : {list(df.columns)}")
    missing = [c for c in NUMBER_COLUMNS + ["bonus", "chronological_id"] if c not in df.columns]
    if missing:
        raise ValidationError(f"Colonnes manquantes : {missing}")

    df = df.sort_values("chronological_id").reset_index(drop=True)
    has_no = "draw_number_source" in df.columns
    inserted = 0
    try:
        for i, row in df.iterrows():
            sdn = None
            if has_no and pd.notna(row["draw_number_source"]):
                sdn = int(row["draw_number_source"])
            try:
                add_draw(
                    conn, game_id,
                    pd.Timestamp(row[date_col]).date().isoformat(),
                    [row[c] for c in NUMBER_COLUMNS],
                    row["bonus"],
                    source=source, source_ref=source_ref, source_draw_no=sdn, commit=False,
                )
            except ValidationError as e:
                raise ValidationError(f"Ligne {i} (chronological_id={row['chronological_id']}) : {e}")
            inserted += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return inserted
