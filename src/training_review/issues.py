"""Issues and checks: every doubt found in a batch, and the quality check it belongs to.

The pipeline never fixes a doubt by guessing. Either the fix is certain and safe (a file sent twice is
read once), and the issue is only reported; or a person must look, and the issue says who and what to do.
Once they have decided, a correction (corrections.py) closes it, and the issue stays listed as resolved.
"""

from dataclasses import asdict, dataclass, fields
from enum import StrEnum

import pandas as pd

STAFF, OPERATOR = "staff", "operator"  # the people who run training; whoever sends the files


class Kind(StrEnum):
    FILE_SENT_TWICE = "file sent twice"
    REPEATED_LINE = "repeated line"
    INVALID_VALUE = "invalid value"
    UNKNOWN_DEVICE = "unknown device"
    UNKNOWN_PLAYER = "unknown player"
    DEVICE_ON_ABSENT_PLAYER = "device on absent player"
    TWO_GPS_RECORDS = "two GPS records"
    NO_GPS = "no GPS"
    NO_HEART_RATE = "no heart rate"
    UNUSED_CORRECTION = "unused correction"


@dataclass(frozen=True)
class Check:
    """One quality check of the weekly report. It fails when the batch has an issue of its kind."""

    title: str
    action: str  # what to do when it fails
    who_acts: str
    to_check: bool  # True: the data may be wrong or incomplete. False: handled automatically, for information.


# In the order the report shows them: files first, then identities, then measurements.
CHECKS = {
    Kind.FILE_SENT_TWICE: Check("Each file sent once", "Nothing to do: the copy was ignored.", OPERATOR, False),
    Kind.REPEATED_LINE: Check("No repeated line", "Nothing to do: kept once.", OPERATOR, False),
    Kind.INVALID_VALUE: Check(
        "Values are plausible", "Check the device or the export, then explain; the value is left out.", OPERATOR, True
    ),
    Kind.UNKNOWN_DEVICE: Check("Every device is on the device sheet", "Add it to the device sheet.", STAFF, True),
    Kind.UNKNOWN_PLAYER: Check("Every player is in the squad", "Add them to the squad, or explain.", STAFF, True),
    Kind.DEVICE_ON_ABSENT_PLAYER: Check(
        "Devices were worn by players who trained",
        "Find who wore it, and add a reassign correction.",
        STAFF,
        True,
    ),
    Kind.TWO_GPS_RECORDS: Check(
        "One GPS record per player and session", "Check the device sheet: two devices for one player?", STAFF, True
    ),
    Kind.NO_GPS: Check("Every player who trained has a GPS distance", "Explain the gap at the meeting.", STAFF, True),
    Kind.NO_HEART_RATE: Check(
        "Every player who trained has a heart rate", "Explain the gap at the meeting.", STAFF, True
    ),
    Kind.UNUSED_CORRECTION: Check(
        "Every correction was applied", "Fix the correction: it matches nothing in this batch.", STAFF, True
    ),
}


@dataclass(frozen=True)
class Issue:
    kind: Kind
    problem: str
    file: str | None = None
    player_id: str | None = None
    session_id: str | None = None
    device_id: str | None = None
    date: str | None = None


COLUMNS = [*(f.name for f in fields(Issue)), "who_acts", "status", "resolution"]
OPEN, CORRECTED, EXPLAINED, HANDLED = "open", "corrected", "explained", "handled"


def to_frame(issues: list[Issue], resolved: dict[int, tuple[str, str]]) -> pd.DataFrame:
    """`resolved` maps an issue's position in `issues` to (CORRECTED or EXPLAINED, the staff's note).

    open: a person must look. corrected / explained: a person decided, see corrections.py.
    handled: the fix was certain, done automatically.
    """
    rows = []
    for n, issue in enumerate(issues):
        status, note = resolved.get(n, (OPEN if CHECKS[issue.kind].to_check else HANDLED, None))
        rows.append({**asdict(issue), "kind": str(issue.kind), "who_acts": CHECKS[issue.kind].who_acts,
                     "status": status, "resolution": note})  # fmt: skip
    return pd.DataFrame(rows, columns=COLUMNS)
