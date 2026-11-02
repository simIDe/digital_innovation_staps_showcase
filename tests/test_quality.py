"""The quality overview: checks, completeness and the verdict, before and after the staff's corrections."""

from training_review import corrections
from training_review.pipeline import clean_batch
from training_review.quality import assess

from .conftest import SAMPLES

DECIDED = corrections.load(SAMPLES.parent / "corrections.yml")


def statuses(quality) -> dict[str, str]:
    return {c.title: c.status for c in quality.checks}


def test_a_batch_whose_only_issue_was_handled_is_ready():
    quality = assess(clean_batch(SAMPLES / "batch2"))  # a file sent twice: ignored, nothing to check
    assert quality.ready
    assert statuses(quality)["Each file sent once"] == "handled"


def test_before_corrections_the_verdict_counts_every_open_point():
    quality = assess(clean_batch(SAMPLES / "batch1"))
    assert quality.to_check == 5  # 1 device on an absent player, 2 no GPS, 1 no heart rate, 1 unknown player
    assert statuses(quality)["No repeated line"] == "handled"
    assert statuses(quality)["Values are plausible"] == "passed"


def test_after_corrections_the_checks_say_how_each_point_was_resolved():
    quality = assess(clean_batch(SAMPLES / "batch1", DECIDED["batch1"]))
    assert quality.ready
    assert statuses(quality)["Devices were worn by players who trained"] == "corrected"
    assert statuses(quality)["Every player who trained has a GPS distance"] == "explained"


def test_an_unexplained_point_keeps_the_batch_not_ready():
    quality = assess(clean_batch(SAMPLES / "batch4", DECIDED["batch4"]))
    assert quality.to_check == 1  # J17's missing GPS: no answer from the staff yet


def test_completeness_is_the_share_of_players_who_trained_with_a_value():
    completeness = assess(clean_batch(SAMPLES / "batch1")).completeness.set_index("session_id")
    s102 = completeness.loc["S102"]
    assert (s102.trained, s102.absent) == (22, 0)
    assert s102.gps == 21 / 22  # J15 trained without GPS
    assert s102.heart_rate == 1.0
