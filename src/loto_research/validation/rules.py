"""Règles de validation V001–V007 (IMPLEMENTATION_SPEC §8).

Aucune règle ne corrige une valeur : elle signale seulement l'échec.
"""
from datetime import date, datetime

from loto_research.validation.schema import MAIN_MAX, MAIN_MIN, RAW_HEADER

EARLIEST_DATE = date(1978, 1, 1)  # lancement du jeu (RESEARCH_REVIEW §5)

RULE_DESCRIPTIONS = {
    "V001": "date invalide, absente ou hors de la plage 1978-aujourd'hui",
    "V002": "un numéro principal hors de [1,49]",
    "V003": "doublon parmi les 6 numéros principaux",
    "V004": "complémentaire hors de [1,49]",
    "V005": "valeur non numérique (numéros, complémentaire ou numéro de tirage)",
    "V006": "colonne obligatoire manquante",
    "V007": "dates non triables chronologiquement",
}


def parse_int(v):
    """Retourne un int si v est un entier (int, float entier, str numérique), sinon None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else None
    if isinstance(v, str):
        try:
            return int(v.strip())
        except ValueError:
            return None
    return None


def parse_date(v):
    """Retourne un objet date, ou None. Formats acceptés : datetime, date, 'YYYY-MM-DD'."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return datetime.strptime(v.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def validate_row(draw_number, mains, bonus, raw_date):
    """Retourne la liste des règles échouées (V001–V005) pour une ligne.

    Si une valeur n'est pas numérique (V005), les règles de plage (V002–V004)
    ne sont pas évaluables et sont sautées.
    """
    failed = []
    d = parse_date(raw_date)
    if d is None or not (EARLIEST_DATE <= d <= date.today()):
        failed.append("V001")

    ints = [parse_int(v) for v in list(mains) + [bonus, draw_number]]
    if any(v is None for v in ints):
        failed.append("V005")
        return failed

    n, b = ints[:6], ints[6]
    if any(not (MAIN_MIN <= v <= MAIN_MAX) for v in n):
        failed.append("V002")
    if len(set(n)) != len(n):
        failed.append("V003")
    if not (MAIN_MIN <= b <= MAIN_MAX):
        failed.append("V004")
    return failed


def missing_required_columns(header):
    """V006 : colonnes obligatoires absentes de l'en-tête."""
    present = {str(h) for h in header if h is not None}
    return [c for c in RAW_HEADER if c not in present]


def dates_sortable(dates):
    """V007 : toutes les dates fournies sont de vraies dates, donc triables."""
    return all(isinstance(d, date) for d in dates)
