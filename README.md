# Training review

Every week, a football staff receives a folder of files: the squad list, the attendance sheet, the device
sheet, GPS exports from two vendors, and heart-rate data. Merged by hand, they take hours, and the errors
stay hidden: kilometres added to metres, a device worn by the wrong player, a file counted twice, a gap
read as zero.

**Training review** turns that folder into **one weekly report** that checks the data first and then
shows it. The report opens with a verdict: *ready for the meeting*, or *5 points to check, and who acts*.

![The weekly report of a sample batch](docs/report.png)

All data in this repository is synthetic.

## Try it

You need [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run review report data/samples/batch1      # writes reports/batch1/report.html, records.csv, issues.csv
uv run review check data/samples/batch2       # the checks only, in the terminal; nothing is written
```

Open `reports/batch1/report.html` in a browser. Then try `batch2` to `batch4`: each one hides different
problems (a vendor that changed its export format, a file sent twice, a negative distance).

The exit code tells a scheduled job what to do: `0` ready, `1` points to check, `2` batch unreadable.

## What the report checks

| Check | When it fails, who acts |
|---|---|
| Every file is in a known format | the batch is refused and nothing is written (operator) |
| Each file sent once, no repeated line | handled automatically and reported (operator) |
| Values are plausible (no negative distance, heart rate 30–230 bpm) | the value is left out; check the device (operator) |
| Every device is on the device sheet, every player in the squad | update the sheet (staff) |
| Devices were worn by players who trained | find who wore it, fix the device sheet, send again (staff) |
| Every player who trained has a GPS distance and a heart rate | explain the gap at the meeting (staff) |

Then, per session, it shows how complete the GPS and heart-rate data are, and a player × session overview.
A missing value is written *missing*, never drawn as 0, and players are never ranked.

## Find your way

```
data/samples/         four synthetic weekly batches, as the staff would send them
src/training_review/
  rules.py            value rules: decimal commas, km → m, plausible ranges. No I/O.
  formats.py          the files we can read, recognised by their columns. Add a vendor here.
  issues.py           the kinds of issue, and the quality check each one belongs to
  schema.py           the data contract of the clean table (pandera)
  pipeline.py         a batch folder in, a clean table and its issues out
  quality.py          checks, completeness, verdict
  report.py           the HTML report and the CSV files; layout in templates/report.html
  cli.py              the `review` command
tests/                one test file per module, on the sample batches
scripts/              rebuilds the sample batches
docs/                 why and how, below
```

Start with `pipeline.py`: it reads top to bottom like the process it implements.

## Documentation

| Read this | To understand |
|---|---|
| [Product](docs/product.md) | who it is for, what they need, what we chose not to build, and how we measure success |
| [Pitch](docs/pitch.md) | the one page for a decision-maker: problem, proposal, cost, risks, the ask |
| [Architecture](docs/architecture.md) | the modules and the data flow, in diagrams |
| [Data](docs/data.md) | the source files, the clean table, every check |
| [Decisions](docs/decisions.md) | the choices made, and why |
| [Extending](docs/extending.md) | add a vendor, a check or a measure; run it every week |

## Develop

```bash
uv run pytest                          # tests
uv run ruff check . && uv run ruff format --check .   # lint and format
```

CI runs the same commands on every push, and publishes the sample reports as an artifact.
