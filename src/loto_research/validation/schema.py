"""Schéma canonique (IMPLEMENTATION_SPEC §6) et en-tête attendu du fichier source."""

RAW_HEADER = [
    "N. du tirage", "Résultats 1", "Résultats 2", "Résultats 3",
    "Résultats 4", "Résultats 5", "Résultats 6", "C", "DATE TIRAGE",
]

MAIN_MIN, MAIN_MAX = 1, 49
NUMBER_COLUMNS = [f"n{i}" for i in range(1, 7)]

CANONICAL_COLUMNS = [
    "draw_id", "date", "draw_number_source", *NUMBER_COLUMNS,
    "bonus", "year", "month", "day", "weekday",
]

# Colonnes ajoutées pour la traçabilité (hors schéma canonique)
EXTRA_COLUMNS = ["chronological_id", "source_row", "flags"]

DTYPES = {
    "draw_id": "string",
    "draw_number_source": "Int64",
    **{c: "Int64" for c in NUMBER_COLUMNS},
    "bonus": "Int64",
    "year": "Int16",
    "month": "Int8",
    "day": "Int8",
    "weekday": "category",
    "chronological_id": "Int64",
    "source_row": "Int64",
    "flags": "string",
}
