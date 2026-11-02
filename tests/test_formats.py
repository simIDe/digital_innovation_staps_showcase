"""The format registry: every declared format must give its kind's standard columns, and be unambiguous."""

import pytest

from training_review.formats import FORMATS, STANDARD


@pytest.mark.parametrize("fmt", FORMATS, ids=lambda f: f.name)
def test_each_format_maps_to_the_standard_columns_of_its_kind(fmt):
    mapped = {standard for standard in fmt.columns.values() if standard}
    assert mapped == set(STANDARD[fmt.kind])
    if fmt.kind == "gps":
        assert fmt.unit in ("km", "m")


def test_no_two_formats_have_the_same_columns():
    columns = [frozenset(f.columns) for f in FORMATS]
    assert len(columns) == len(set(columns))
