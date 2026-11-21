from datetime import date, datetime

from loto_research.validation.rules import (
    dates_sortable, missing_required_columns, parse_date, parse_int, validate_row,
)


def test_parse_int_accepts_int_float_str():
    assert parse_int(7) == 7
    assert parse_int(7.0) == 7
    assert parse_int("7") == 7
    assert parse_int(" 7 ") == 7


def test_parse_int_rejects_non_integers():
    assert parse_int(7.5) is None
    assert parse_int("abc") is None
    assert parse_int(None) is None
    assert parse_int(True) is None  # bool n'est pas un numéro de loterie


def test_parse_date_accepts_datetime_date_and_iso_string():
    assert parse_date(datetime(2020, 1, 2)) == date(2020, 1, 2)
    assert parse_date(date(2020, 1, 2)) == date(2020, 1, 2)
    assert parse_date("2020-01-02") == date(2020, 1, 2)


def test_parse_date_rejects_garbage():
    assert parse_date("02/01/2020") is None
    assert parse_date(None) is None


def test_validate_row_valid_line_has_no_failure():
    failed = validate_row(1, [1, 2, 3, 4, 5, 6], 7, "2020-01-01")
    assert failed == []


def test_v001_invalid_date():
    assert "V001" in validate_row(1, [1, 2, 3, 4, 5, 6], 7, "1900-01-01")
    assert "V001" in validate_row(1, [1, 2, 3, 4, 5, 6], 7, None)
    assert "V001" in validate_row(1, [1, 2, 3, 4, 5, 6], 7, "2999-01-01")


def test_v002_out_of_range_main_number():
    assert "V002" in validate_row(1, [0, 2, 3, 4, 5, 6], 7, "2020-01-01")
    assert "V002" in validate_row(1, [1, 2, 3, 4, 5, 50], 7, "2020-01-01")


def test_v003_duplicate_main_numbers():
    assert "V003" in validate_row(1, [1, 1, 3, 4, 5, 6], 7, "2020-01-01")


def test_v004_bonus_out_of_range():
    assert "V004" in validate_row(1, [1, 2, 3, 4, 5, 6], 0, "2020-01-01")
    assert "V004" in validate_row(1, [1, 2, 3, 4, 5, 6], 50, "2020-01-01")


def test_v005_non_numeric_short_circuits_range_checks():
    failed = validate_row(1, [1, 2, 3, 4, 5, "x"], 7, "2020-01-01")
    assert failed == ["V005"]  # V002/V003/V004 non évaluables, pas de faux résultat


def test_zero_line_is_invalid_v002_and_v003():
    """La ligne '0 0 0 0 0 0 + 0' (Cahier §8) doit être détectée invalide."""
    failed = validate_row(0, [0, 0, 0, 0, 0, 0], 0, "2020-01-01")
    assert "V002" in failed
    assert "V003" in failed  # six zéros = six doublons
    assert "V004" in failed


def test_v006_missing_required_columns():
    header = ["N. du tirage", "Résultats 1"]  # incomplet
    missing = missing_required_columns(header)
    assert "Résultats 2" in missing
    assert "DATE TIRAGE" in missing


def test_v006_complete_header_has_no_missing_column():
    header = [
        "N. du tirage", "Résultats 1", "Résultats 2", "Résultats 3", "Résultats 4",
        "Résultats 5", "Résultats 6", "C", "DATE TIRAGE",
    ]
    assert missing_required_columns(header) == []


def test_v007_dates_sortable():
    assert dates_sortable([date(2020, 1, 1), date(2020, 1, 2)])
    assert not dates_sortable([date(2020, 1, 1), "pas une date"])
