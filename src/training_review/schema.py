"""The data contract of the review table: what every consumer (the report, anyone analysing the CSV) can rely on.

The pipeline validates its output against it, so a broken rule fails loudly at import time
instead of showing a wrong number in the meeting.
"""

import pandera.pandas as pa
from pandera.typing import Series

from training_review.rules import HEART_RATE_BPM

POSITIONS = ["GK", "DEF", "MID", "FWD"]


class Records(pa.DataFrameModel):
    """One row per player and session on the attendance sheet."""

    session_id: Series[str]
    date: Series[str] = pa.Field(str_matches=r"^\d{4}-\d{2}-\d{2}$")
    player_id: Series[str]
    name: Series[str] = pa.Field(nullable=True)
    position: Series[str] = pa.Field(isin=POSITIONS, nullable=True)
    present: Series[bool]
    minutes: Series[float] = pa.Field(ge=0, nullable=True)
    distance_m: Series[float] = pa.Field(ge=0, nullable=True)  # missing means no valid measurement, never 0
    mean_hr_bpm: Series[float] = pa.Field(
        in_range={"min_value": HEART_RATE_BPM[0], "max_value": HEART_RATE_BPM[1]}, nullable=True
    )

    note: Series[str] = pa.Field(nullable=True)  # the staff's correction or explanation for this record, if any

    class Config:
        strict = "filter"  # keep exactly these columns
        coerce = True
        ordered = False
        unique = ("player_id", "session_id")


COLUMNS = list(Records.to_schema().columns)
