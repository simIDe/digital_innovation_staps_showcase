# Decisions

Short records of the choices that shape the project: the context, the decision, what it costs. When a
choice changes, add a new entry rather than rewriting an old one, so the reasoning stays readable.

## 1. A weekly static report, not a live app

**Context.** The staff look at the data once a week, before a meeting. An interactive app needs a server,
accounts and someone to keep it running.
**Decision.** One self-contained HTML file per batch, plus CSV files.
**Cost.** No in-app interaction: issues are resolved at the source (the device sheet), then the batch is
sent again. Revisit if that loop proves too slow ([roadmap](product.md#roadmap)).

## 2. Recognise files by their columns, never by their name

**Context.** File names are typed by people (`fieldsense_jeudi_FINAL.csv`, `HR_export (1).csv`).
**Decision.** Each format is declared once in `formats.FORMATS` with its exact set of columns. Unknown
columns stop the batch.
**Cost.** A vendor that adds a column breaks the import until its format is declared. That is intended:
a loud stop is better than a silent misreading.

## 3. Missing stays missing

**Context.** An empty cell turned into 0 makes a player who forgot their vest look like they did not run.
**Decision.** No imputation, anywhere. Missing values are empty in the CSV, written *missing* in the report,
and raised as issues.
**Cost.** Averages must be read with their count; the report always shows completeness next to the data.

## 4. Report doubts, never fix them by guessing

**Context.** When a device is recorded on an absent player, a likely wearer often exists. Likely is not sure.
**Decision.** The pipeline fixes only what is certain (an identical file, an identical line) and reports
everything else with who acts.
**Cost.** More issues to read. Each one says what to do, and the verdict counts only those that need a person.

## 5. The raw files are never edited

**Context.** A correction made inside a raw export is invisible afterwards.
**Decision.** The tool only reads the batch folder. Corrections go to the source files the staff own (the
device sheet, the squad) and the batch is processed again.
**Cost.** Correcting needs a new run, which takes seconds.

## 6. A data contract on the clean table

**Context.** The clean table is used by the report, and by whoever analyses the CSV later.
**Decision.** `schema.Records` (pandera) declares its columns, types, ranges and uniqueness; the pipeline
validates its own output.
**Cost.** One more dependency; a schema to update when a column is added.

## 7. No ranking, one measure per chart, describe rather than diagnose

**Context.** A ranking puts goalkeepers last by design and turns a review into a league table; a readiness
score would claim more than the data can support.
**Decision.** The overview is a player × session grid, players ordered by id, one measure per grid.
**Cost.** No "headline" number about players. That is deliberate.

## 8. Standard, well-known tools

**Context.** The tool must be maintainable by the next person, not only its author.
**Decision.** Python, pandas, pandera, Jinja2, Typer; uv for environments; ruff and pytest in CI.
**Cost.** None worth noting; each is widely documented.
