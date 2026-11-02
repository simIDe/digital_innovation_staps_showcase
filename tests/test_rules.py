import math

import pytest

from training_review import rules


@pytest.mark.parametrize(("text", "expected"), [("4.24", 4.24), ("4,24", 4.24), (" 12 ", 12.0), ("0", 0.0)])
def test_to_number_reads_both_decimal_marks(text, expected):
    assert rules.to_number(text) == expected


@pytest.mark.parametrize("text", [None, "", "  ", math.nan])
def test_an_empty_cell_is_missing_not_zero(text):
    assert rules.to_number(text) is None


def test_text_that_is_not_a_number_is_an_error():
    with pytest.raises(ValueError, match="not a number"):
        rules.to_number("n/a")


def test_distances_end_up_in_metres():
    assert rules.distance_m(6.45, "km") == 6450
    assert rules.distance_m(6450, "m") == 6450
    assert rules.distance_m(None, "km") is None


@pytest.mark.parametrize(("value", "unit"), [(-6.47, "km"), (6.47, "miles")])
def test_an_impossible_distance_is_an_error(value, unit):
    with pytest.raises(ValueError):
        rules.distance_m(value, unit)


def test_heart_rate_is_checked_but_never_invented():
    assert rules.heart_rate(150) == 150
    assert rules.heart_rate(None) is None
    with pytest.raises(ValueError, match="implausible"):
        rules.heart_rate(0)


def test_attendance_is_yes_or_no():
    assert rules.present("yes") is True
    assert rules.present(" No ") is False
    with pytest.raises(ValueError):
        rules.present("maybe")
