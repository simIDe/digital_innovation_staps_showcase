"""The files we know how to read, recognised by their columns, never by their name.

A vendor that changes its export, or a new tool, is one more entry in FORMATS: map its columns
to the standard ones and say which unit it uses. Nothing else in the code has to change.
An unknown file stops the import: we never guess what a column means.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# What each kind of file must hold once its columns are renamed.
STANDARD = {
    "squad": ["player_id", "name", "position"],
    "devices": ["device_id", "player_id"],
    "attendance": ["session_id", "date", "player_id", "present", "minutes"],
    "gps": ["device_id", "date", "distance"],
    "heart_rate": ["player_id", "date", "mean_hr_bpm"],
}
# Exactly one of each per batch: without them, nothing can be checked.
REQUIRED = ("squad", "devices", "attendance")


@dataclass(frozen=True)
class Format:
    name: str
    kind: str  # one of STANDARD
    columns: dict[str, str | None]  # source column -> standard column, or None for a column we ignore
    unit: str | None = None  # distance unit, for GPS exports

    def matches(self, columns: list[str]) -> bool:
        return set(columns) == set(self.columns)


def identity(*columns: str) -> dict[str, str | None]:
    return {c: c for c in columns}


FORMATS = [
    Format("squad", "squad", identity("player_id", "name", "position")),
    Format("device sheet", "devices", identity("device_id", "player_id")),
    Format("attendance", "attendance", identity("session_id", "date", "player_id", "present", "minutes")),
    Format("heart-rate straps", "heart_rate", {**identity("player_id", "date", "mean_hr_bpm"), "coverage_pct": None}),
    Format(
        "TrackPro",
        "gps",
        {"device_id": "device_id", "date": "date", "distance_km": "distance", "duration_min": None},
        "km",
    ),
    Format(
        "TrackPro v2",
        "gps",
        {"Device": "device_id", "Date": "date", "Distance (km)": "distance", "Duration (min)": None},
        "km",
    ),
    Format(
        "FieldSense",
        "gps",
        {"device": "device_id", "session_date": "date", "distance_m": "distance", "minutes": None},
        "m",
    ),
]


class UnknownFormat(Exception):
    """A file or a batch we cannot read without guessing. Nothing is stored."""


@dataclass
class SourceFile:
    name: str
    format: Format
    table: pd.DataFrame  # standard columns only, every cell as text


def detect(path: Path, columns: list[str]) -> Format:
    for fmt in FORMATS:
        if fmt.matches(columns):
            return fmt
    raise UnknownFormat(
        f"{path.name}: unknown columns {columns}. "
        "Add its format to formats.FORMATS once you know what each column means."
    )


def read_file(path: Path) -> SourceFile:
    raw = pd.read_csv(path, sep=None, engine="python", dtype=str, encoding="utf-8-sig")  # , or ; alike
    fmt = detect(path, list(raw.columns))
    kept = {source: standard for source, standard in fmt.columns.items() if standard}
    return SourceFile(path.name, fmt, raw[list(kept)].rename(columns=kept))


def read_batch(folder: Path) -> tuple[dict[str, list[SourceFile]], list[tuple[str, str]]]:
    """Every CSV of a batch folder, grouped by kind, and the files skipped as copies: (copy, original)."""
    if not folder.is_dir():
        raise UnknownFormat(f"{folder}: not a folder")
    by_kind: dict[str, list[SourceFile]] = {kind: [] for kind in STANDARD}
    seen: dict[str, str] = {}
    duplicates = []
    for path in sorted(folder.glob("*.csv")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:  # the same file sent twice would silently count everything twice
            duplicates.append((path.name, seen[digest]))
            continue
        seen[digest] = path.name
        source = read_file(path)
        by_kind[source.format.kind].append(source)
    for kind in REQUIRED:
        if len(by_kind[kind]) != 1:
            raise UnknownFormat(f"{folder.name}: expected exactly one {kind} file, found {len(by_kind[kind])}")
    return by_kind, duplicates
