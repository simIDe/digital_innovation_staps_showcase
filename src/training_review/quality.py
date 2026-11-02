"""Data quality of a batch: which checks pass, how complete each session is, and one verdict.

The verdict answers the staff's first question: can we use these numbers in the meeting as they are?
"""

from dataclasses import dataclass

import pandas as pd

from training_review.issues import CHECKS
from training_review.pipeline import Batch


@dataclass
class CheckResult:
    title: str
    issues: int  # how many issues of this kind; 0 means passed
    action: str
    who_acts: str
    to_check: bool

    @property
    def status(self) -> str:
        if not self.issues:
            return "pass"
        return "check" if self.to_check else "info"


@dataclass
class Quality:
    checks: list[CheckResult]
    completeness: pd.DataFrame  # one row per session, see completeness()

    @property
    def to_check(self) -> int:
        """Issues a person must look at before the numbers are used."""
        return sum(c.issues for c in self.checks if c.status == "check")

    @property
    def ready(self) -> bool:
        return self.to_check == 0


def assess(batch: Batch) -> Quality:
    counts = batch.issues.kind.value_counts()
    checks = [
        CheckResult(c.title, int(counts.get(kind, 0)), c.action, c.who_acts, c.to_check) for kind, c in CHECKS.items()
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
