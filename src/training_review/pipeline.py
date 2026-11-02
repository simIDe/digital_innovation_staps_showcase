"""The pipeline: a batch folder of raw files in, one clean table and a list of issues out.

Pure logic: it reads the folder and returns data. It writes nothing, so it is easy to test and to reuse.

    attendance + squad  ──> one row per player and session
    GPS exports         ──> + distance in metres, given to a player through the device sheet
    heart-rate straps   ──> + mean heart rate
    every doubt along the way ──> issues
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from training_review import rules
from training_review.formats import SourceFile, read_batch
from training_review.issues import Issue, Kind, to_frame
from training_review.schema import COLUMNS, Records


@dataclass
class Batch:
    name: str
    files: pd.DataFrame  # every file received: file, format, rows (a copy sent twice has format "copy")
    records: pd.DataFrame  # validated against schema.Records
    issues: pd.DataFrame  # issues.COLUMNS


def clean_batch(folder: Path) -> Batch:
    """Clean one batch folder. Raises formats.UnknownFormat if a file cannot be read without guessing."""
    sources, copies = read_batch(folder)
    issues = [Issue(Kind.FILE_SENT_TWICE, f"same content as {original}, ignored", file=c) for c, original in copies]

    squad, devices, attendance = (sources[kind][0].table for kind in ("squad", "devices", "attendance"))
    attendance = attendance.assign(
        present=attendance.present.map(rules.present),
        minutes=attendance.minutes.map(rules.to_number),
    )
    for player_id in sorted(set(attendance.player_id) - set(squad.player_id)):
        issues.append(Issue(Kind.UNKNOWN_PLAYER, "on the attendance sheet but not in the squad", player_id=player_id))

    gps = gps_distances(sources["gps"], devices, attendance, issues)
    heart = heart_rates(sources["heart_rate"], squad, issues)
    table = (
        attendance.merge(squad, on="player_id", how="left")
        .merge(gps, on=["player_id", "date"], how="left")
        .merge(heart, on=["player_id", "date"], how="left")
    )

    # A missing value stays missing, and is reported so that someone can explain it.
    trained = table[table.present]
    for r in trained[trained.distance_m.isna()].itertuples():
        issues.append(Issue(Kind.NO_GPS, "trained, but no GPS distance", player_id=r.player_id,
                            session_id=r.session_id, date=r.date))  # fmt: skip
    for r in trained[trained.mean_hr_bpm.isna()].itertuples():
        issues.append(Issue(Kind.NO_HEART_RATE, "trained, but no heart rate", player_id=r.player_id,
                            session_id=r.session_id, date=r.date))  # fmt: skip

    records = Records.validate(table)[COLUMNS].sort_values(["session_id", "player_id"], ignore_index=True)
    files = pd.DataFrame(
        [(s.name, s.format.name, len(s.table)) for kind in sources.values() for s in kind]
        + [(c, "copy", 0) for c, _ in copies],
        columns=["file", "format", "rows"],
    ).sort_values("file", ignore_index=True)
    return Batch(folder.name, files, records, to_frame(issues))


def gps_distances(
    sources: list[SourceFile], devices: pd.DataFrame, attendance: pd.DataFrame, issues: list[Issue]
) -> pd.DataFrame:
    """Every GPS export in metres, given to the player who wore the device. Columns: player_id, date, distance_m."""
    rows = []
    for source in sources:
        unique = source.table.drop_duplicates()
        if len(unique) < len(source.table):
            repeated = len(source.table) - len(unique)
            issues.append(Issue(Kind.REPEATED_LINE, f"{repeated} repeated line(s), kept once", file=source.name))
        for r in unique.itertuples():
            try:
                distance = rules.distance_m(rules.to_number(r.distance), source.format.unit)
            except ValueError as error:
                issues.append(Issue(Kind.INVALID_VALUE, f"{r.device_id} on {r.date}: {error}", file=source.name,
                                    device_id=r.device_id, date=r.date))  # fmt: skip
                continue
            rows.append((source.name, r.device_id, r.date, distance))
    gps = pd.DataFrame(rows, columns=["file", "device_id", "date", "distance_m"]).merge(
        devices, on="device_id", how="left"
    )

    for r in gps[gps.player_id.isna()].itertuples():
        issues.append(Issue(Kind.UNKNOWN_DEVICE, f"device {r.device_id} is not on the device sheet", file=r.file,
                            device_id=r.device_id, date=r.date))  # fmt: skip

    gps = gps.merge(attendance[["session_id", "date", "player_id", "present"]], on=["date", "player_id"], how="left")
    worn_by_absent = gps[gps.player_id.notna() & (gps.present != True)]  # noqa: E712 (NaN: not on the sheet)
    for r in worn_by_absent.itertuples():
        issues.append(Issue(Kind.DEVICE_ON_ABSENT_PLAYER,
                            f"device {r.device_id} recorded on {r.date}, but the device sheet gives it to "
                            f"{r.player_id}, who did not train. Who wore it?",
                            file=r.file, player_id=r.player_id, session_id=r.session_id, device_id=r.device_id,
                            date=r.date))  # fmt: skip
    gps = gps[gps.present == True]  # noqa: E712

    for r in gps[gps.duplicated(["player_id", "date"])].itertuples():
        issues.append(Issue(Kind.TWO_GPS_RECORDS, "two GPS records for one session, the first one is kept",
                            file=r.file, player_id=r.player_id, session_id=r.session_id, date=r.date))  # fmt: skip
    return gps.drop_duplicates(["player_id", "date"])[["player_id", "date", "distance_m"]]


def heart_rates(sources: list[SourceFile], squad: pd.DataFrame, issues: list[Issue]) -> pd.DataFrame:
    """Mean heart rate per player and day. Columns: player_id, date, mean_hr_bpm."""
    rows = []
    for source in sources:
        known = source.table.player_id.isin(squad.player_id)
        for r in source.table[~known].drop_duplicates("player_id").itertuples():
            issues.append(Issue(Kind.UNKNOWN_PLAYER, "not in the squad (a trialist?), ignored", file=source.name,
                                player_id=r.player_id, date=r.date))  # fmt: skip
        for r in source.table[known].itertuples():
            try:
                rows.append((r.player_id, r.date, rules.heart_rate(rules.to_number(r.mean_hr_bpm))))
            except ValueError as error:
                issues.append(Issue(Kind.INVALID_VALUE, f"{r.player_id} on {r.date}: {error}", file=source.name,
                                    player_id=r.player_id, date=r.date))  # fmt: skip
    return pd.DataFrame(rows, columns=["player_id", "date", "mean_hr_bpm"]).drop_duplicates(["player_id", "date"])
