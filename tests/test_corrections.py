"""Corrections: a reassign changes the data, an explain does not, and nothing is applied silently."""

import pandas as pd
import pytest
from pydantic import ValidationError

from training_review import corrections
from training_review.corrections import Correction
from training_review.pipeline import clean_batch

from .conftest import SAMPLES


def reassign(device, date, to, note="confirmed by the physical trainer"):
    return Correction(reassign={"device": device, "date": date, "to": to}, note=note)


def explain(note="forgot the vest", **which):
    return Correction(explain=which, note=note)


def value(batch, player_id, session_id, column="distance_m"):
    records = batch.records
    return records[(records.player_id == player_id) & (records.session_id == session_id)][column].item()


def statuses(batch, kind, player_id):
    issues = batch.issues
    return issues[(issues.kind == kind) & (issues.player_id == player_id)].status.tolist()


def test_a_reassign_gives_the_distance_to_the_player_who_wore_the_device():
    before = clean_batch(SAMPLES / "batch1")
    after = clean_batch(SAMPLES / "batch1", [reassign("D04", "2026-10-29", "J21")])
    assert pd.isna(value(before, "J21", "S103"))
    assert value(after, "J21", "S103") == 3660
    assert statuses(after, "no GPS", "J21") == []  # the gap it caused is gone
    assert statuses(after, "device on absent player", "J04") == ["corrected"]  # the issue stays visible
    assert after.corrections.effect.item() == "3.66 km moved from J04 (device sheet) to J21"
    assert value(after, "J21", "S103", "note").startswith("wore D04")


def test_an_explain_closes_the_issue_but_keeps_the_gap():
    batch = clean_batch(SAMPLES / "batch1", [explain(issue="no GPS", player="J15", session="S102")])
    assert pd.isna(value(batch, "J15", "S102"))
    assert statuses(batch, "no GPS", "J15") == ["explained"]
    assert value(batch, "J15", "S102", "note") == "forgot the vest"


def test_a_correction_that_matches_nothing_is_reported():
    unused = [reassign("D04", "2026-10-30", "J21"), explain(issue="no GPS", player="J01")]
    issues = clean_batch(SAMPLES / "batch1", unused).issues
    assert (issues[issues.kind == "unused correction"].status == "open").sum() == 2


LOAN = {"device": "D04", "date": "2026-10-29", "to": "J21"}


@pytest.mark.parametrize(
    "entry",
    [
        {"reassign": LOAN},
        {"reassign": LOAN, "note": ""},
        {"reassign": LOAN, "explain": {"issue": "no GPS"}, "note": "both at once"},
        {"explain": {"issue": "bad kind"}, "note": "not a kind of issue"},
        {"explain": {"issue": "no GPS", "playr": "J15"}, "note": "typo in a field name"},
    ],
    ids=["no note", "empty note", "two actions", "unknown issue", "unknown field"],
)
def test_an_invalid_correction_is_refused(entry):
    with pytest.raises(ValidationError):
        corrections.CorrectionsFile.validate_python({"batch1": [entry]})


def test_the_corrections_of_the_samples_are_valid():
    assert set(corrections.load(SAMPLES.parent / "corrections.yml")) == {"batch1", "batch3", "batch4"}


def test_no_corrections_file_means_no_correction(tmp_path):
    assert corrections.load(tmp_path / "missing.yml") == {}
