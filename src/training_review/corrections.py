"""Corrections: what the staff decided about the issues of a batch, kept in one versioned file.

The raw files are never edited. Each decision is written in data/corrections.yml, with a note saying who
confirmed it, and applied every time the batch is processed. The report shows each one and its effect.

Two kinds of decision, and only two:
- reassign: a device was worn by another player that day. The data changes: the distance moves to them.
- explain:  an issue has a known cause ("forgot the vest"). The data does not change: a gap stays a gap,
            but it no longer needs checking, and its reason travels with the data.

    batch1:
      - reassign: {device: D04, date: 2026-10-29, to: J21}
        note: J21's own vest was broken, so J21 wore D04. Confirmed by the physical trainer.
      - explain: {issue: no GPS, player: J15, session: S102}
        note: Forgot the vest.
"""

import datetime as dt
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from training_review.issues import Issue, Kind


class Reassign(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device: str
    date: dt.date
    to: str  # the player who wore it


class Explain(BaseModel):
    """Which issue: its kind, and any of player, session, device, date that pin it down."""

    model_config = ConfigDict(extra="forbid")
    issue: Kind
    player: str | None = None
    session: str | None = None
    device: str | None = None
    date: dt.date | None = None

    def matches(self, issue: Issue) -> bool:
        wanted = {"player_id": self.player, "session_id": self.session, "device_id": self.device,
                  "date": self.date.isoformat() if self.date else None}  # fmt: skip
        return issue.kind == self.issue and all(
            getattr(issue, field) == value for field, value in wanted.items() if value is not None
        )


class Correction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reassign: Reassign | None = None
    explain: Explain | None = None
    note: str = Field(min_length=3)  # who decided, on what basis: a decision without a note cannot be checked

    @model_validator(mode="after")
    def one_action(self) -> "Correction":
        if (self.reassign is None) == (self.explain is None):
            raise ValueError("each correction is either a reassign or an explain")
        return self

    def describe(self) -> str:
        if self.reassign:
            r = self.reassign
            return f"reassign {r.device} on {r.date} to {r.to}"
        e = self.explain
        where = ", ".join(str(v) for v in (e.player, e.session, e.device, e.date) if v)
        return f"explain {e.issue}{f' ({where})' if where else ''}"


CorrectionsFile = TypeAdapter(dict[str, list[Correction]])


def load(path: Path | None) -> dict[str, list[Correction]]:
    """Every batch's corrections. A missing file means no correction yet."""
    if path is None or not path.exists():
        return {}
    return CorrectionsFile.validate_python(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
