"""The weekly report and the command line: what gets written, and the exit code a scheduled job reads."""

import pandas as pd
from typer.testing import CliRunner

from training_review.cli import app

from .conftest import SAMPLES

runner = CliRunner()
CORRECTIONS = str(SAMPLES.parent / "corrections.yml")


def report(out, *batches, corrections=CORRECTIONS):
    folders = [str(SAMPLES / b) for b in batches]
    return runner.invoke(app, ["report", *folders, "--corrections", corrections, "--out", str(out)])


def test_report_writes_the_page_and_the_data(tmp_path):
    result = report(tmp_path, "batch1", corrections=str(tmp_path / "none.yml"))
    folder = tmp_path / "batch1"
    assert sorted(p.name for p in folder.iterdir()) == ["corrections.csv", "issues.csv", "records.csv", "report.html"]
    page = (folder / "report.html").read_text(encoding="utf-8")
    assert "5 points to check before the meeting" in page
    assert "missing" in page and "absent" in page  # gaps are written, never drawn as 0
    assert result.exit_code == 1  # points to check


def test_corrections_show_in_the_report_and_make_it_ready(tmp_path):
    result = report(tmp_path, "batch1")
    page = (tmp_path / "batch1" / "report.html").read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert "Ready for the meeting" in page
    assert "3.66 km moved from J04 (device sheet) to J21" in page


def test_every_batch_is_also_written_together(tmp_path):
    report(tmp_path, "batch1", "batch2", "batch3", "batch4")
    records = pd.read_csv(tmp_path / "records.csv")
    assert sorted(records.batch.unique()) == ["batch1", "batch2", "batch3", "batch4"]
    assert len(records) == 66 + 3 * 69
    assert (tmp_path / "issues.csv").exists() and (tmp_path / "corrections.csv").exists()


def test_check_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["check", str(SAMPLES / "batch4"), "--corrections", CORRECTIONS])
    assert result.exit_code == 1  # J17 still unexplained
    assert list(tmp_path.iterdir()) == []


def test_an_unreadable_batch_exits_with_2_and_writes_nothing(batch_folder, tmp_path):
    folder = batch_folder()
    (folder / "mystery.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    result = runner.invoke(app, ["report", str(folder), "--out", str(tmp_path / "out")])
    assert result.exit_code == 2
    assert "mystery.csv" in result.output
    assert not (tmp_path / "out").exists()


def test_an_invalid_corrections_file_exits_with_2(tmp_path):
    bad = tmp_path / "corrections.yml"
    bad.write_text("batch1:\n  - explain: {issue: no GPS, player: J15}\n", encoding="utf-8")  # no note
    result = report(tmp_path / "out", "batch1", corrections=str(bad))
    assert result.exit_code == 2
    assert "not valid" in result.output
