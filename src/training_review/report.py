"""The weekly report: one self-contained HTML page per batch, plus the clean data as CSV.

No server, no JavaScript: the page opens anywhere, can be e-mailed or printed, and reads the same in a year.
Layout lives in templates/report.html; this module only prepares what the page shows.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape

from training_review.issues import CORRECTED, EXPLAINED, HANDLED, OPEN
from training_review.pipeline import Batch
from training_review.quality import Quality, assess

LIGHT, DARK = (0xCD, 0xE2, 0xFB), (0x10, 0x42, 0x81)  # one hue, light to dark: more is darker
MEASURES = {"distance_m": ("Distance (km)", 1000, "{:.1f}"), "mean_hr_bpm": ("Mean heart rate (bpm)", 1, "{:.0f}")}

TABLES = ("records", "issues", "corrections")

env = Environment(loader=PackageLoader("training_review"), autoescape=select_autoescape())


def write(batch: Batch, out: Path) -> Path:
    """Write report.html and the batch's data (records, issues, corrections as CSV) in out/<batch>/."""
    folder = out / batch.name
    folder.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        getattr(batch, name).to_csv(folder / f"{name}.csv", index=False)
    page = folder / "report.html"
    page.write_text(render(batch, assess(batch)), encoding="utf-8")
    return page


def render(batch: Batch, quality: Quality, now: datetime | None = None) -> str:
    records, issues = batch.records, batch.issues
    trained = records[records.present]
    return env.get_template("report.html").render(
        batch=batch.name,
        first_day=records.date.min(),
        last_day=records.date.max(),
        generated=(now or datetime.now()).strftime("%d %B %Y, %H:%M"),
        quality=quality,
        summary={
            "sessions": records.session_id.nunique(),
            "players": records.player_id.nunique(),
            "attendances": len(trained),
            "complete": len(trained.dropna(subset=["distance_m", "mean_hr_bpm"])),
        },
        open_issues=rows(issues[issues.status == OPEN].sort_values(["who_acts", "kind"], ascending=[False, True])),
        resolved=rows(issues[issues.status.isin([CORRECTED, EXPLAINED])]),
        handled=rows(issues[issues.status == HANDLED]),
        corrections=rows(batch.corrections),
        files=rows(batch.files),
        grids=[grid(records, column) for column in MEASURES],
    )


def rows(df: pd.DataFrame) -> list[dict]:
    """Rows for the template, with an empty string where a cell is missing."""
    return df.astype(object).where(df.notna(), "").to_dict("records")


def grid(records: pd.DataFrame, column: str) -> dict:
    """Every player x every session for one measure. Each cell: its text and its colours."""
    title, divisor, fmt = MEASURES[column]
    values = records[column] / divisor
    low, high = values.min(), values.max()

    def cell(value: float, present: bool, note: object) -> dict:
        noted = {"title": note, "class": "noted"} if isinstance(note, str) else {}  # a correction or explanation
        if not present:
            return {"text": "absent", "class": "absent"}
        if pd.isna(value):
            return {"text": "missing", **noted, "class": f"missing {noted.get('class', '')}"}
        share = (value - low) / (high - low) if high > low else 0.5
        rgb = tuple(round(a + share * (b - a)) for a, b in zip(LIGHT, DARK, strict=True))
        ink = "#fff" if share > 0.6 else "#0b0b0b"
        return {"text": fmt.format(value), "style": f"background:rgb{rgb};color:{ink}", **noted}

    df = records.assign(value=values)
    sessions = sorted(df.session_id.unique())
    players = df.drop_duplicates("player_id").sort_values("player_id")
    by_key = {(r.player_id, r.session_id): cell(r.value, r.present, r.note) for r in df.itertuples()}
    return {
        "title": title,
        "sessions": sessions,
        "rows": [
            {
                "player": f"{p.player_id} · {p.name}",
                "position": p.position,
                "cells": [by_key.get((p.player_id, s), {"text": "", "class": "absent"}) for s in sessions],
            }
            for p in players.itertuples()
        ],
    }
