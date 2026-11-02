"""Data quality of a batch: which checks pass, how complete each session is, and one verdict.

The verdict answers the staff's first question: can we use these numbers in the meeting as they are?
"""

from dataclasses import dataclass

import pandas as pd

from training_review.issues import CHECKS, CORRECTED, EXPLAINED, HANDLED, OPEN
from training_review.pipeline import Batch

STATUSES = (OPEN, CORRECTED, EXPLAINED, HANDLED)  # most serious first


@dataclass
class CheckResult:
    title: str
    action: str
    who_acts: str
    open: int  # issues a person must still look at
    corrected: int  # issues a person resolved with a reassign: the data changed
    explained: int  # issues a person explained: the data did not change
    handled: int  # issues fixed automatically, for information

    @property
    def found(self) -> int:
        return self.open + self.corrected + self.explained + self.handled

    @property
    def status(self) -> str:
        """The most serious status among its issues, or "passed" when there is none."""
        counts = dict(zip(STATUSES, (self.open, self.corrected, self.explained, self.handled), strict=True))
        return next((status for status, n in counts.items() if n), "passed")


@dataclass
class Quality:
    checks: list[CheckResult]
    completeness: pd.DataFrame  # one row per session, see completeness()

    @property
    def to_check(self) -> int:
        """Issues a person must look at before the numbers are used."""
        return sum(c.open for c in self.checks)

    @property
    def ready(self) -> bool:
        return self.to_check == 0


def assess(batch: Batch) -> Quality:
    counts = batch.issues.groupby(["kind", "status"]).size()
    checks = [
        CheckResult(c.title, c.action, c.who_acts, *(int(counts.get((kind, s), 0)) for s in STATUSES))
        for kind, c in CHECKS.items()
    ]
    return Quality(checks, completeness(batch.records))


def completeness(records: pd.DataFrame) -> pd.DataFrame:
    """Per session: players who trained, and the share of them with a GPS distance and a heart rate."""
    trained = records[records.present]
    per_session = trained.groupby(["session_id", "date"]).agg(
        trained=("player_id", "size"),
        gps=("distance_m", lambda v: v.notna().mean()),
        heart_rate=("mean_hr_bpm", lambda v: v.notna().mean()),
    )
    absent = records[~records.present].groupby("session_id").size()
    return per_session.reset_index().assign(absent=lambda d: d.session_id.map(absent).fillna(0).astype(int))
