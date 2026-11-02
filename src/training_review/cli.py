"""The `review` command. Run `uv run review --help`.

Exit codes, so that a scheduled job can react: 0 ready, 1 points to check, 2 batch unreadable.
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from training_review import report
from training_review.formats import UnknownFormat
from training_review.pipeline import Batch, clean_batch
from training_review.quality import Quality, assess

app = typer.Typer(
    help="Weekly training review: check a batch of training files and write its report.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
READY, TO_CHECK, UNREADABLE = 0, 1, 2
STATUS = {"pass": "[green]passed[/]", "check": "[dark_orange]to check[/]", "info": "[blue]handled[/]"}


def load(folder: Path) -> Batch:
    try:
        return clean_batch(folder)
    except UnknownFormat as error:
        console.print(f"[red]{folder.name}: cannot be read, nothing written.[/] {error}")
        raise typer.Exit(UNREADABLE) from None


def show(batch: Batch, quality: Quality) -> None:
    verdict = "[green]ready[/]" if quality.ready else f"[dark_orange]{quality.to_check} point(s) to check[/]"
    console.print(f"[bold]{batch.name}[/]: {batch.records.session_id.nunique()} sessions, {verdict}")
    table = Table("check", "status", "issues", "who acts", box=None)
    for c in quality.checks:
        table.add_row(c.title, STATUS[c.status], str(c.issues or ""), c.who_acts if c.issues else "")
    console.print(table)


@app.command()
def check(folder: Path) -> None:
    """Run the quality checks on a batch folder. Nothing is written."""
    batch = load(folder)
    quality = assess(batch)
    show(batch, quality)
    raise typer.Exit(READY if quality.ready else TO_CHECK)


@app.command("report")
def write_report(
    folders: list[Path],
    out: Annotated[Path, typer.Option(help="Where to write one folder per batch.")] = Path("reports"),
) -> None:
    """Write the weekly report of each batch folder: report.html, records.csv and issues.csv."""
    worst = READY
    for folder in folders:
        batch = load(folder)
        quality = assess(batch)
        show(batch, quality)
        console.print(f"-> {report.write(batch, out).as_posix()}\n")
        worst = max(worst, READY if quality.ready else TO_CHECK)
    raise typer.Exit(worst)


if __name__ == "__main__":
    app()
