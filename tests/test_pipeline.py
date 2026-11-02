"""The pipeline on the sample batches: each one hides problems, and each problem must be reported, never guessed."""

import pandas as pd
import pytest

from training_review.formats import UnknownFormat
from training_review.pipeline import clean_batch

from .conftest import SAMPLES


def kinds(batch) -> list[str]:
    return sorted(batch.issues.kind)


def value(batch, player_id, session_id, column):
    row = batch.records[(batch.records.player_id == player_id) & (batch.records.session_id == session_id)]
    return row[column].item()


def test_one_row_per_player_and_session_on_the_attendance_sheet():
    batch = clean_batch(SAMPLES / "batch1")
    assert len(batch.records) == 22 * 3
    assert not batch.records.duplicated(["player_id", "session_id"]).any()


def test_both_gps_vendors_end_up_in_metres():
    batch = clean_batch(SAMPLES / "batch1")
    trackpro = value(batch, "J07", "S101", "distance_m")  # exported as 6.45 km
    fieldsense = value(batch, "J01", "S103", "distance_m")  # exported as 3110 m
    assert (trackpro, fieldsense) == (6450, 3110)


def test_batch1_problems_are_all_reported():
    batch = clean_batch(SAMPLES / "batch1")
    assert kinds(batch) == sorted(
        ["repeated line", "device on absent player", "unknown player", "no GPS", "no GPS", "no heart rate"]
    )


def test_a_gap_stays_a_gap():
    batch = clean_batch(SAMPLES / "batch1")
    assert pd.isna(value(batch, "J15", "S102", "distance_m"))  # trained without GPS
    assert pd.isna(value(batch, "J12", "S101", "mean_hr_bpm"))  # strap stopped
    assert pd.isna(value(batch, "J09", "S101", "distance_m"))  # absent


def test_a_new_vendor_format_and_a_file_sent_twice_are_handled():
    batch = clean_batch(SAMPLES / "batch2")  # TrackPro v2: ';', new headers, decimal commas
    assert kinds(batch) == ["file sent twice"]
    assert batch.records[batch.records.present].distance_m.notna().all()


def test_a_negative_distance_is_rejected_and_reported():
    batch = clean_batch(SAMPLES / "batch4")
    assert "invalid value" in kinds(batch)
    assert pd.isna(value(batch, "J11", "S110", "distance_m"))


def test_an_unknown_file_stops_everything(batch_folder):
    folder = batch_folder()
    (folder / "export_new_tool.csv").write_text("athlete;km\nJ01;5\n", encoding="utf-8")
    with pytest.raises(UnknownFormat, match=r"export_new_tool\.csv"):
        clean_batch(folder)


def test_files_are_listed_with_their_format():
    batch = clean_batch(SAMPLES / "batch2")
    formats = dict(zip(batch.files.file, batch.files.format, strict=True))
    assert formats["TrackPro_2026-11-02.csv"] == "TrackPro v2"
    assert formats["HR_export.csv"] == "copy"


def test_a_batch_without_its_attendance_sheet_is_refused(batch_folder):
    folder = batch_folder()
    (folder / "presence.csv").unlink()
    with pytest.raises(UnknownFormat, match="attendance"):
        clean_batch(folder)
