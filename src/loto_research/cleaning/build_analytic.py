"""Construction du dataset ANALYTIC à partir des enregistrements RAW (Phase 2).

Principe : aucune valeur n'est corrigée. Les anomalies sont SIGNALÉES (colonne `flags`),
jamais supprimées. Seuls sont retirés du dataset ANALYTIC : les lignes invalides
(V001–V005) et les dates dupliquées (keep first, ordre du fichier). Tout est exporté.
"""
import hashlib

import pandas as pd

from loto_research.validation.rules import (
    RULE_DESCRIPTIONS, parse_date, parse_int, validate_row,
)
from loto_research.validation.schema import (
    CANONICAL_COLUMNS, DTYPES, EXTRA_COLUMNS, NUMBER_COLUMNS,
)

WEEKDAYS_FR = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]

# Seuil approximatif déduit du diagnostic structurel de la Phase 1 (3 lundis en 2015,
# puis un lundi par semaine dès 2016). Sert UNIQUEMENT à signaler pour revue.
MONDAY_DRAWS_FROM = pd.Timestamp("2016-01-01")

VALID_COLUMNS = ["source_row", "date", "draw_number_source", *NUMBER_COLUMNS, "bonus"]
INVALID_COLUMNS = ["row_number", "reason", "original_values", "validation_rule"]


def make_draw_id(d, draw_number, mains, bonus):
    """SHA256 complet de date + N source + n1..n6 (ordre du fichier) + complémentaire."""
    payload = "|".join(
        [d.strftime("%Y-%m-%d"), str(draw_number), *[str(x) for x in mains], str(bonus)]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def split_valid_invalid(records):
    """Sépare les enregistrements RAW en (valid_df, invalid_df). Rien n'est perdu."""
    valid, invalid = [], []
    for rec in records:
        failed = validate_row(rec["draw_number"], rec["mains"], rec["bonus"], rec["date"])
        if failed:
            invalid.append({
                "row_number": rec["source_row"],
                "reason": " | ".join(RULE_DESCRIPTIONS[r] for r in failed),
                "original_values": repr([rec["draw_number"], *rec["mains"], rec["bonus"], rec["date"]]),
                "validation_rule": ";".join(failed),
            })
        else:
            mains = [parse_int(v) for v in rec["mains"]]
            row = {
                "source_row": rec["source_row"],
                "date": parse_date(rec["date"]),
                "draw_number_source": parse_int(rec["draw_number"]),
                "bonus": parse_int(rec["bonus"]),
            }
            row.update({f"n{i + 1}": m for i, m in enumerate(mains)})
            valid.append(row)

    valid_df = pd.DataFrame(valid, columns=VALID_COLUMNS)
    valid_df["date"] = pd.to_datetime(valid_df["date"])
    invalid_df = pd.DataFrame(invalid, columns=INVALID_COLUMNS)
    return valid_df, invalid_df


def split_duplicate_dates(valid_df):
    """Règle du Cahier §7 : garder la première occurrence (ordre du fichier RAW).

    Retourne (kept, all_duplicates, removed). Le RAW n'est jamais touché.
    """
    df = valid_df.sort_values("source_row", kind="stable").reset_index(drop=True)
    all_dup = df[df.duplicated("date", keep=False)]
    removed = df[df.duplicated("date", keep="first")]
    kept = df[~df.duplicated("date", keep="first")]
    return kept, all_dup, removed


def compute_flags(df):
    """Signalements non bloquants, calculés en ordre chronologique. Retourne list[str].

    N_RESET            : numéro de tirage = 1 (remise à zéro de la numérotation)
    N_NOT_INCREASING   : numéro <= dernier numéro cohérent (doublon ou retour en arrière)
    N_GAP:k            : k numéros de tirage sautés (tirages potentiellement absents)
    DATE_GAP:kd        : plus de 7 jours depuis le tirage précédent
    WEEKDAY:xxx        : jour de semaine atypique (voir MONDAY_DRAWS_FROM)
    BONUS_IN_MAIN      : le complémentaire coïncide avec l'un des 6 principaux
    """
    flags = []
    ref_n = None
    prev_date = None
    for row in df.itertuples(index=False):
        f = []
        n = row.draw_number_source

        if ref_n is None:
            ref_n = n
        elif n == 1:
            f.append("N_RESET")
            ref_n = 1
        elif n <= ref_n:
            f.append("N_NOT_INCREASING")
        else:
            gap = n - ref_n - 1
            if gap > 0:
                f.append(f"N_GAP:{gap}")
            ref_n = n

        if prev_date is not None:
            delta = (row.date - prev_date).days
            if delta > 7:
                f.append(f"DATE_GAP:{delta}d")
        prev_date = row.date

        wd = row.date.weekday()
        allowed = {2, 5} if row.date < MONDAY_DRAWS_FROM else {0, 2, 5}
        if wd not in allowed:
            f.append(f"WEEKDAY:{WEEKDAYS_FR[wd]}")

        if row.bonus in tuple(getattr(row, c) for c in NUMBER_COLUMNS):
            f.append("BONUS_IN_MAIN")

        flags.append(";".join(f))
    return flags


def build_analytic(kept):
    """Dataset ANALYTIC : trié par date, chronological_id 1..N, schéma canonique typé."""
    df = kept.sort_values("date", kind="stable").reset_index(drop=True)
    df.insert(0, "chronological_id", range(1, len(df) + 1))
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["weekday"] = df["date"].dt.weekday.map(lambda k: WEEKDAYS_FR[k])
    df["draw_id"] = [
        make_draw_id(r.date, r.draw_number_source, [getattr(r, c) for c in NUMBER_COLUMNS], r.bonus)
        for r in df.itertuples(index=False)
    ]
    df["flags"] = compute_flags(df)
    df = df[CANONICAL_COLUMNS + EXTRA_COLUMNS]
    return df.astype(DTYPES)
