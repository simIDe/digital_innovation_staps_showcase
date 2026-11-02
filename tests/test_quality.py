"""The quality overview: checks, completeness and the verdict."""

from training_review.pipeline import clean_batch
from training_review.quality import assess

from .conftest import SAMPLES


def statuses(quality) -> dict[str, str]:
    return {c.title: c.status for c in quality.checks}


def test_a_batch_whose_only_issue_was_handled_is_ready():
    quality = assess(clean_batch(SAMPLES / "batch2"))  # a file sent twice: ignored, nothing to check
    assert quality.ready
    assert statuses(quality)["Each file sent once"] == "info"


def test_a_batch_with_gaps_is_not_ready_and_says_how_many_points():
    quality = assess(clean_batch(SAMPLES / "batch1"))
    assert not quality.ready
    assert quality.to_check == 5  # 1 device on an absent player, 2 no GPS, 1 no heart rate, 1 unknown player
    assert statuses(quality)["No repeated line"] == "info"
    assert statuses(quality)["Values are plausible"] == "pass"


def test_completeness_is_the_share_of_players_who_trained_with_a_value():
    completeness = assess(clean_batch(SAMPLES / "batch1")).completeness.set_index("session_id")
    s102 = completeness.loc["S102"]
    assert (s102.trained, s102.absent) == (22, 0)
    assert s102.gps == 21 / 22  # J15 trained without GPS
    assert s102.heart_rate == 1.0
