"""Value rules: one small job each, no I/O, each one tested.

A rule never guesses. A missing value stays missing (None); an impossible value raises ValueError,
and the pipeline turns that error into an issue someone can act on.
"""

import math

HEART_RATE_BPM = (30, 230)  # outside this range, a mean heart rate is a sensor error


def to_number(text: object) -> float | None:
    """A CSV cell as a number. Accepts a decimal comma ("4,24"). Empty means missing."""
    if text is None or (isinstance(text, float) and math.isnan(text)) or str(text).strip() == "":
        return None
    try:
        return float(str(text).strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"not a number: {text!r}") from None


def distance_m(value: float | None, unit: str) -> float | None:
    """A distance in metres, from a value in "km" or "m"."""
    if value is None:
        return None
    if value < 0:
        raise ValueError(f"negative distance: {value}")
    if unit not in ("km", "m"):
        raise ValueError(f"unknown distance unit: {unit!r}")
    return value * 1000 if unit == "km" else value


def heart_rate(value_bpm: float | None) -> float | None:
    """A mean heart rate in bpm. Missing stays missing, never 0."""
    if value_bpm is None:
        return None
    low, high = HEART_RATE_BPM
    if not low <= value_bpm <= high:
        raise ValueError(f"implausible heart rate: {value_bpm} bpm")
    return value_bpm


def present(text: object) -> bool:
    """The attendance sheet's yes/no."""
    answer = str(text).strip().lower()
    if answer not in ("yes", "no"):
        raise ValueError(f"attendance must be yes or no, not {text!r}")
    return answer == "yes"
