"""The explorer opens on the unified data, and says what to do when there is none yet."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from typer.testing import CliRunner

from training_review.cli import app as cli

from .conftest import SAMPLES

PAGE = str(Path(__file__).parents[1] / "src" / "training_review" / "explore.py")


@pytest.fixture
def explorer(tmp_path, monkeypatch):
    monkeypatch.setenv("REVIEW_REPORTS", str(tmp_path))
    return AppTest.from_file(PAGE, default_timeout=30)


def test_without_reports_it_says_what_to_run(explorer):
    explorer.run()
    assert not explorer.exception
    assert "review report" in explorer.info[0].value


def test_it_shows_every_batch_and_the_open_issues(explorer, tmp_path):
    folders = [str(SAMPLES / f"batch{n}") for n in range(1, 5)]
    CliRunner().invoke(cli, ["report", *folders, "--corrections", str(SAMPLES.parent / "corrections.yml"),
                             "--out", str(tmp_path)])  # fmt: skip
    explorer.run()
    assert not explorer.exception
    assert explorer.metric[0].value == "12"  # sessions
    assert explorer.metric[3].value == "1"  # open issues: J17, batch4
    explorer.sidebar.multiselect[0].set_value(["batch1"]).run()
    assert not explorer.exception
    assert explorer.metric[0].value == "3"
