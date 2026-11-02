"""The pipeline: a batch folder of raw files and the staff's corrections in, one clean table and its issues out.

Pure logic: it reads the folder and returns data. It writes nothing, so it is easy to test and to reuse.

    attendance + squad  ──> one row per player and session
    GPS exports         ──> + distance in metres, given to a player through the device sheet
                            (or through a `reassign` correction, for that device and day)
    heart-rate straps   ──> + mean heart rate
    every doubt along the way ──> issues, closed by an `explain` correction when the staff know the cause
"""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from training_review import rules
from training_review.corrections import Correction
from training_review.formats import SourceFile, read_batch
from training_review.issues import CORRECTED, EXPLAINED, Issue, Kind, to_frame
from training_review.schema import COLUMNS, Records

CORRECTION_COLUMNS = ["correction", "effect", "note"]


@dataclass
class Batch:
    name: str
    files: pd.DataFrame  # every file received: file, format, rows (a copy sent twice has format "copy")
    records: pd.DataFrame  # validated against schema.Records
    issues: pd.DataFrame  # issues.COLUMNS
    corrections: pd.DataFrame  # CORRECTION_COLUMNS: each correction and what it changed


@dataclass
class Log:
    """What happened while cleaning: the issues found, and what each correction did."""

    issues: list[Issue] = field(default_factory=list)
    applied: list[tuple[str, str, str]] = field(default_factory=list)  # (correction, effect, note)
    notes: dict[tuple[str, str], str] = field(default_factory=dict)  # (player_id, date) -> note for the record
    resolved: dict[int, tuple[str, str]] = field(default_factory=dict)  # issue position -> (status, note)

    def issue(self, *args, **kwargs) -> int:
        self.issues.append(Issue(*args, **kwargs))
        return len(self.issues) - 1


def clean_batch(folder: Path, corrections: list[Correction] = ()) -> Batch:
    """Clean one batch folder. Raises formats.UnknownFormat if a file cannot be read without guessing."""
    sources, copies = read_batch(folder)
    log = Log()
    for copy, original in copies:
        log.issue(Kind.FILE_SENT_TWICE, f"same content as {original}, ignored", file=copy)

    squad, devices, attendance = (sources[kind][0].table for kind in ("squad", "devices", "attendance"))
    attendance = attendance.assign(
        present=attendance.present.map(rules.present),
        minutes=attendance.minutes.map(rules.to_number),
    )
    for player_id in sorted(set(attendance.player_id) - set(squad.player_id)):
        log.issue(Kind.UNKNOWN_PLAYER, "on the attendance sheet but not in the squad", player_id=player_id)

    reassignments = [c for c in corrections if c.reassign]
    gps = gps_distances(sources["gps"], devices, attendance, reassignments, log)
    heart = heart_rates(sources["heart_rate"], squad, log)
    table = (
        attendance.merge(squad, on="player_id", how="left")
        .merge(gps, on=["player_id", "date"], how="left")
        .merge(heart, on=["player_id", "date"], how="left")
    )

    # A missing value stays missing, and is reported so that someone can explain it.
    trained = table[table.present]
    for r in trained[trained.distance_m.isna()].itertuples():
        log.issue(Kind.NO_GPS, "trained, but no GPS distance", player_id=r.player_id, session_id=r.session_id,
                  date=r.date)  # fmt: skip
    for r in trained[trained.mean_hr_bpm.isna()].itertuples():
        log.issue(Kind.NO_HEART_RATE, "trained, but no heart rate", player_id=r.player_id, session_id=r.session_id,
                  date=r.date)  # fmt: skip

    explain([c for c in corrections if c.explain], attendance, log)
    table["note"] = [log.notes.get((p, d)) for p, d in zip(table.player_id, table.date, strict=True)]
    records = Records.validate(table)[COLUMNS].sort_values(["session_id", "player_id"], ignore_index=True)
    files = pd.DataFrame(
        [(s.name, s.format.name, len(s.table)) for kind in sources.values() for s in kind]
        + [(c, "copy", 0) for c, _ in copies],
        columns=["file", "format", "rows"],
    ).sort_values("file", ignore_index=True)
    return Batch(folder.name, files, records, to_frame(log.issues, log.resolved),
                 pd.DataFrame(log.applied, columns=CORRECTION_COLUMNS))  # fmt: skip


def gps_distances(
    sources: list[SourceFile],
    devices: pd.DataFrame,
    attendance: pd.DataFrame,
    reassignments: list[Correction],
    log: Log,
) -> pd.DataFrame:
    """Every GPS export in metres, given to the player who wore the device. Columns: player_id, date, distance_m."""
    rows = []
    for source in sources:
        unique = source.table.drop_duplicates()
        if len(unique) < len(source.table):
            repeated = len(source.table) - len(unique)
            log.issue(Kind.REPEATED_LINE, f"{repeated} repeated line(s), kept once", file=source.name)
        for r in unique.itertuples():
            try:
                distance = rules.distance_m(rules.to_number(r.distance), source.format.unit)
            except ValueError as error:
                log.issue(Kind.INVALID_VALUE, f"{r.device_id} on {r.date}: {error}", file=source.name,
                          device_id=r.device_id, date=r.date)  # fmt: skip
                continue
            rows.append((source.name, r.device_id, r.date, distance))
    gps = pd.DataFrame(rows, columns=["file", "device_id", "date", "distance_m"]).merge(
        devices, on="device_id", how="left"
    )

    # Who wore the device: the device sheet, unless the staff reassigned it for that day.
    for c in reassignments:
        r = c.reassign
        day = (gps.device_id == r.device) & (gps.date == r.date.isoformat())
        if not day.any():
            log.issue(Kind.UNUSED_CORRECTION, f"{c.describe()}: no GPS record of {r.device} that day",
                      device_id=r.device, date=r.date.isoformat())  # fmt: skip
            continue
        before = gps.loc[day, "player_id"].iloc[0]
        km = gps.loc[day, "distance_m"].iloc[0] / 1000
        gps.loc[day, "player_id"] = r.to
        trained = attendance[(attendance.player_id == before) & (attendance.date == r.date.isoformat())].present
        if not trained.any():  # the issue this correction resolves stays listed, as corrected
            n = log.issue(Kind.DEVICE_ON_ABSENT_PLAYER,
                          f"device {r.device} recorded on {r.date}, but it is given to {before}, who did not train",
                          player_id=before, device_id=r.device, date=r.date.isoformat())  # fmt: skip
            log.resolved[n] = (CORRECTED, c.note)
        log.applied.append((c.describe(), f"{km:.2f} km moved from {before} (device sheet) to {r.to}", c.note))
        log.notes[(r.to, r.date.isoformat())] = f"wore {r.device}: {c.note}"

    for r in gps[gps.player_id.isna()].itertuples():
        log.issue(Kind.UNKNOWN_DEVICE, f"device {r.device_id} is not on the device sheet", file=r.file,
                  device_id=r.device_id, date=r.date)  # fmt: skip

    gps = gps.merge(attendance[["session_id", "date", "player_id", "present"]], on=["date", "player_id"], how="left")
    worn_by_absent = gps[gps.player_id.notna() & (gps.present != True)]  # noqa: E712 (NaN: not on the sheet)
    for r in worn_by_absent.itertuples():
        log.issue(Kind.DEVICE_ON_ABSENT_PLAYER,
                  f"device {r.device_id} recorded on {r.date}, but it is given to {r.player_id}, who did not train. "
                  "Who wore it?",
                  file=r.file, player_id=r.player_id, session_id=r.session_id, device_id=r.device_id,
                  date=r.date)  # fmt: skip
    gps = gps[gps.present == True]  # noqa: E712

    for r in gps[gps.duplicated(["player_id", "date"])].itertuples():
        log.issue(Kind.TWO_GPS_RECORDS, "two GPS records for one session, the first one is kept", file=r.file,
                  player_id=r.player_id, session_id=r.session_id, date=r.date)  # fmt: skip
    return gps.drop_duplicates(["player_id", "date"])[["player_id", "date", "distance_m"]]


def heart_rates(sources: list[SourceFile], squad: pd.DataFrame, log: Log) -> pd.DataFrame:
    """Mean heart rate per player and day. Columns: player_id, date, mean_hr_bpm."""
    rows = []
    for source in sources:
        known = source.table.player_id.isin(squad.player_id)
        for r in source.table[~known].drop_duplicates("player_id").itertuples():
            log.issue(Kind.UNKNOWN_PLAYER, "not in the squad (a trialist?), ignored", file=source.name,
                      player_id=r.player_id, date=r.date)  # fmt: skip
        for r in source.table[known].itertuples():
            try:
                rows.append((r.player_id, r.date, rules.heart_rate(rules.to_number(r.mean_hr_bpm))))
            except ValueError as error:
                log.issue(Kind.INVALID_VALUE, f"{r.player_id} on {r.date}: {error}", file=source.name,
                          player_id=r.player_id, date=r.date)  # fmt: skip
    return pd.DataFrame(rows, columns=["player_id", "date", "mean_hr_bpm"]).drop_duplicates(["player_id", "date"])


def explain(explanations: list[Correction], attendance: pd.DataFrame, log: Log) -> None:
    """Attach each explanation to the issues it matches. The data is unchanged."""
    found = list(log.issues)  # an unused explanation must not try to explain the issue it raises
    dates = dict(zip(attendance.session_id, attendance.date, strict=False))
    for c in explanations:
        matched = [n for n, issue in enumerate(found) if c.explain.matches(issue)]
        if not matched:
            log.issue(Kind.UNUSED_CORRECTION, f"{c.describe()}: no such issue in this batch")
            continue
        for n in matched:
            log.resolved[n] = (EXPLAINED, c.note)
            issue = found[n]
            date = issue.date or dates.get(issue.session_id)
            if issue.player_id and date:
                log.notes[(issue.player_id, date)] = c.note
        log.applied.append((c.describe(), f"explains {len(matched)} issue(s); data unchanged", c.note))
