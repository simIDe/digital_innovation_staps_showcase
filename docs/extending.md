# Extending

Recipes for the changes most likely to come. Each one starts with a failing test, on a sample batch or a
small folder written in the test (see `tests/test_pipeline.py`).

## Add a vendor, or a new version of an export

A batch stops with `unknown columns [...]`. Find out what each column means (ask the vendor or the staff),
then add one entry to `FORMATS` in `src/training_review/formats.py`:

```python
Format("Catapult", "gps",
       {"Device ID": "device_id", "Session Date": "date", "Total Distance (m)": "distance", "Duration": None},
       "m"),
```

The keys are the file's columns, the values the standard ones (`None` for a column we ignore), and the last
argument is the distance unit. Nothing else changes: the pipeline, the checks and the report already handle
any GPS format.

## Add a quality check

1. Add the kind to `Kind` in `issues.py`, and its `Check` to `CHECKS` (title, action, who acts, whether a
   person must look).
2. Raise the issue in `pipeline.py` where the doubt appears: `issues.append(Issue(Kind.NEW_KIND, "...", ...))`.
3. The report shows the new check automatically.

Example: flag a heart rate whose strap coverage is below 60%. `coverage_pct` is already in the heart-rate
files; map it in the format instead of ignoring it, and raise an issue when it is too low.

## Add a measure

E.g. high-speed running distance from the GPS exports:

1. map the column in the GPS formats (`formats.py`) and add it to `STANDARD["gps"]`;
2. carry it through `gps_distances` in `pipeline.py`;
3. add it to `schema.Records`, with its range;
4. add it to `MEASURES` in `report.py`: the report gets a new grid.

## Change a plausibility rule

Edit `rules.py` (e.g. `HEART_RATE_BPM`) and its test in `tests/test_rules.py`. The schema reuses the same
constant, so the contract follows.

## Run it every week

The command is made to be scheduled. Its exit code says what happened: `0` ready, `1` points to check,
`2` batch unreadable.

- **On a computer**: a scheduled task (Windows Task Scheduler, cron) runs
  `uv run review report <shared folder>/<this week>` on the morning of the meeting.
- **With a workflow tool** (n8n, Make, Power Automate): when a folder appears in the shared drive, run the
  command, then send a message by exit code: to the staff with the report's location (0 or 1), to the
  operator with the error (2). Send the location of the report, never player data, in the message.

## Keep weeks together

`records.csv` of each batch has the same columns. To follow trends, concatenate them:

```python
import pandas as pd
from pathlib import Path

season = pd.concat(pd.read_csv(p).assign(batch=p.parent.name) for p in Path("reports").glob("*/records.csv"))
```

When this becomes a weekly need, the next step is a small database (SQLite, then PostgreSQL if several people
need it), filled by the same pipeline.
