"""The weekly report and the command line: what gets written, and the exit code a scheduled job reads."""

from typer.testing import CliRunner

from training_review.cli import app

from .conftest import SAMPLES

runner = CliRunner()


def test_report_writes_the_page_and_the_data(tmp_path):
    result = runner.invoke(app, ["report", str(SAMPLES / "batch1"), "--out", str(tmp_path)])
    folder = tmp_path / "batch1"
    assert sorted(p.name for p in folder.iterdir()) == ["issues.csv", "records.csv", "report.html"]
    page = (folder / "report.html").read_text(encoding="utf-8")
    assert "5 points to check before the meeting" in page
    assert "missing" in page and "absent" in page  # gaps are written, never drawn as 0
    assert result.exit_code == 1  # points to check


def test_a_ready_batch_exits_with_0(tmp_path):
    result = runner.invoke(app, ["report", str(SAMPLES / "batch2"), "--out", str(tmp_path)])
    assert result.exit_code == 0
    assert "Ready for the meeting" in (tmp_path / "batch2" / "report.html").read_text(encoding="utf-8")


def test_check_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["check", str(SAMPLES / "batch4")])
    assert result.exit_code == 1
    assert list(tmp_path.iterdir()) == []


def test_an_unreadable_batch_exits_with_2_and_writes_nothing(batch_folder, tmp_path):
    folder = batch_folder()
    (folder / "mystery.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    result = runner.invoke(app, ["report", str(folder), "--out", str(tmp_path / "out")])
    assert result.exit_code == 2
    assert "mystery.csv" in result.output
    assert not (tmp_path / "out").exists()
