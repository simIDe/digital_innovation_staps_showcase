"""The `review` command. Run `uv run review --help`.

Exit codes, so that a scheduled job can react: 0 ready, 1 points to check, 2 batch or corrections unreadable.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from training_review import corrections, report
from training_review.formats import UnknownFormat
from training_review.pipeline import Batch, clean_batch
from training_review.quality import Quality, assess

app = typer.Typer(
    help="Weekly training review: check a batch of training files, apply the staff's corrections, report, explore.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
READY, TO_CHECK, UNREADABLE = 0, 1, 2
COLOURS = {"passed": "green", "open": "dark_orange", "corrected": "blue", "explained": "blue", "handled": "blue"}

Corrections = Annotated[Path, typer.Option("--corrections", help="The staff's corrections (YAML).")]
Out = Annotated[Path, typer.Option(help="Where the reports and the data are written.")]


def load(folder: Path, corrections_file: Path) -> Batch:
    try:
        decided = corrections.load(corrections_file)
        return clean_batch(folder, decided.get(folder.name, []))
    except UnknownFormat as error:
        console.print(f"[red]{folder.name}: cannot be read, nothing written.[/] {error}")
    except ValidationError as error:
        console.print(f"[red]{corrections_file.as_posix()} is not valid, nothing written.[/]\n{error}")
    raise typer.Exit(UNREADABLE)


def show(batch: Batch, quality: Quality) -> None:
    verdict = "[green]ready[/]" if quality.ready else f"[dark_orange]{quality.to_check} point(s) to check[/]"
    console.print(f"[bold]{batch.name}[/]: {batch.records.session_id.nunique()} sessions, {verdict}")
    table = Table("check", "status", "found", box=None)
    for c in quality.checks:
        table.add_row(c.title, f"[{COLOURS[c.status]}]{c.status}[/]", str(c.found or ""))
    console.print(table)
    for c in batch.corrections.itertuples():
        console.print(f"  applied: {c.correction} -> {c.effect}")


@app.command()
def check(folder: Path, corrections_file: Corrections = Path("data/corrections.yml")) -> None:
    """Run the quality checks on a batch folder, with its corrections. Nothing is written."""
    batch = load(folder, corrections_file)
    quality = assess(batch)
    show(batch, quality)
    raise typer.Exit(READY if quality.ready else TO_CHECK)


@app.command("report")
def write_report(
    folders: list[Path],
    corrections_file: Corrections = Path("data/corrections.yml"),
    out: Out = Path("reports"),
) -> None:
    """Write each batch's report and data in out/<batch>/, then the data of every batch together in out/."""
    worst = READY
    for folder in folders:
        batch = load(folder, corrections_file)
        quality = assess(batch)
        show(batch, quality)
        console.print(f"-> {report.write(batch, out).as_posix()}\n")
        worst = max(worst, READY if quality.ready else TO_CHECK)
    for name in report.TABLES:
        parts = [pd.read_csv(p).assign(batch=p.parent.name) for p in sorted(out.glob(f"*/{name}.csv"))]
        pd.concat(parts, ignore_index=True).to_csv(out / f"{name}.csv", index=False)
    console.print(f"All batches together: {', '.join(f'{out.as_posix()}/{n}.csv' for n in report.TABLES)}")
    raise typer.Exit(worst)


@app.command()
def explore(out: Out = Path("reports")) -> None:
    """Open the explorer on every batch reported so far, in the browser."""
    page = Path(__file__).parent / "explore.py"
    env = {**os.environ, "REVIEW_REPORTS": str(out)}
    raise typer.Exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(page)], env=env))


if __name__ == "__main__":
    app()
