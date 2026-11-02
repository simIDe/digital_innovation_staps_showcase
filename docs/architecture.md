# Architecture

One idea shapes the code: **a pure core, a thin shell**. The core reads a batch folder and the corrections
file and returns data. It writes nothing and asks nothing. The shell (the command line, the report and the
explorer) handles input and output. The rules live in the core, so that is where the tests are.

## In context

```mermaid
flowchart LR
    tools["Training-ground tools<br/>GPS vests · heart-rate straps<br/>attendance · squad · device sheet"]
    operator(["Operator"])
    folder[("Weekly batch folder<br/>raw CSV, never edited")]
    fixes[("data/corrections.yml<br/>the staff's decisions")]
    review["review report"]
    out[("reports/<br/>one report per batch<br/>+ unified CSV files")]
    explore["review explore"]
    staff(["Staff"])

    tools --> operator -->|collects the week's files| folder --> review
    fixes --> review --> out
    out -->|verdict, points to check| staff
    staff -->|decide, then record| fixes
    out --> explore -->|all batches, corrected| staff
```

Everything in `reports/` can be rebuilt at any time from the raw folders and the corrections file. Those two
are the only sources of truth, and both can be versioned.

## Modules

```mermaid
flowchart TB
    subgraph shell["Shell: input and output"]
        cli["cli.py<br/>the review command"]
        report["report.py<br/>+ templates/report.html"]
        explore["explore.py + charts.py<br/>Streamlit, reads reports/*.csv"]
    end
    subgraph core["Core: pure functions, no I/O apart from reading its inputs"]
        quality["quality.py<br/>checks · completeness · verdict"]
        pipeline["pipeline.py<br/>batch + corrections → clean table + issues"]
        corrections["corrections.py<br/>reassign · explain (validated)"]
        formats["formats.py<br/>known files, by their columns"]
        rules["rules.py<br/>value rules"]
        issues["issues.py<br/>kinds of issue · checks catalogue"]
        schema["schema.py<br/>data contract (pandera)"]
    end

    cli --> report
    cli --> quality
    cli --> corrections
    report --> quality
    quality --> pipeline
    pipeline --> corrections
    pipeline --> formats
    pipeline --> rules
    pipeline --> issues
    pipeline --> schema
    explore -. "reads the CSV files<br/>report.py wrote" .-> report
```

Dependencies only point down. The explorer does not call the pipeline: it reads what the reports wrote, so
what you explore is exactly what the reports say. Each module has one reason to change:

| When this changes… | …edit only |
| --- | --- |
| a vendor changes its export, or a new tool appears | `formats.py` |
| a plausibility rule (e.g. the heart-rate range) | `rules.py` |
| what a check is called, who acts, what to do | `issues.py` |
| a new kind of correction | `corrections.py`, and where it applies in `pipeline.py` |
| how files are merged | `pipeline.py` |
| what the clean table guarantees to its users | `schema.py` |
| how the report looks | `templates/report.html` |
| what the explorer shows | `explore.py`, `charts.py` |

## What happens in `review report`

```mermaid
sequenceDiagram
    actor U as Operator
    participant C as cli
    participant K as corrections
    participant P as pipeline
    participant F as formats
    participant Q as quality
    participant R as report

    U->>C: review report batch5/
    C->>K: load(data/corrections.yml)
    Note over K: invalid entry (no note, unknown issue…)<br/>→ stop, exit code 2
    C->>P: clean_batch(folder, corrections for batch5)
    P->>F: read_batch(folder)
    Note over F: unknown columns → stop, exit code 2
    F-->>P: files grouped by kind, copies skipped
    P->>P: attendance + squad → one row per player and session
    P->>P: + GPS in metres, via the device sheet or a reassign
    P->>P: + heart rate
    P->>P: every doubt → an issue, closed by a matching explain
    P->>P: validate the clean table (schema)
    P-->>C: Batch(files, records, issues, corrections applied)
    C->>Q: assess(batch)
    Q-->>C: checks, completeness, verdict
    C->>R: write(batch)
    R-->>U: reports/batch5/ and the unified reports/*.csv
    C-->>U: exit code 0 ready / 1 points to check
```

## How the clean table is built

```mermaid
flowchart LR
    att["attendance<br/>session · date · player · present"]
    squad["squad<br/>player · name · position"]
    gps["GPS exports<br/>device · date · distance<br/>km or m"]
    dev["device sheet<br/>device → player"]
    re["reassign corrections<br/>device + day → player"]
    hr["heart rate<br/>player · date · bpm"]

    att --> base["one row per<br/>player × session"]
    squad --> base
    gps -->|to metres| g2["distance per<br/>device and day"]
    dev --> g3["distance per<br/>player and day"]
    re -->|overrides the sheet<br/>for that day only| g3
    g2 --> g3
    g3 -->|left join| table["clean table<br/>(schema.Records)"]
    base --> table
    hr -->|left join| table

    g3 -. "device on a player who did not train" .-> iss["issues"]
    gps -. "negative value, repeated line" .-> iss
    table -. "trained but no value" .-> iss
```

Left joins keep every player on the attendance sheet. A missing measurement stays an empty cell and becomes
an issue. It never removes the row and never becomes 0.

## The life of an issue

```mermaid
stateDiagram-v2
    [*] --> handled: certain fix (copy, repeated line)
    [*] --> open: a person must look
    open --> corrected: reassign, the data changes
    open --> explained: explain, the data does not change
    handled --> [*]
    corrected --> [*]
    explained --> [*]
```

The verdict counts only **open** issues: *ready* when there are none. Resolved issues stay in the report and
in `issues.csv` with their status and the staff's note, so nothing disappears without a trace. A correction
that matches nothing raises its own open issue (*unused correction*).

## Engineering choices

- **Corrections as data, not code.** Decisions live in one YAML file, validated by pydantic (unknown fields,
  missing notes and unknown issue kinds are refused). It is easy to review in a diff and easy to version, and
  it is applied the same way every time.
- **Data contract.** `schema.Records` (pandera) states what the clean table guarantees: one row per player
  and session, distances ≥ 0, heart rates in range, known positions. The pipeline validates its own output,
  so a broken rule fails at once instead of showing a wrong number.
- **Configuration as data.** File formats and checks are declared in lists (`formats.FORMATS`,
  `issues.CHECKS`), not buried in `if` statements.
- **Static report, read-only explorer.** The report is one HTML file with no JavaScript, to open, print or
  archive. The explorer only reads CSV files, so it can never change the data.
- **Tests on realistic data.** The sample batches carry the real problems, and each test names the behaviour
  it protects (`test_an_explain_closes_the_issue_but_keeps_the_gap`).
- **Reproducible.** `uv.lock` pins every dependency, a seeded script generates the sample data, and CI runs
  lint, tests and the sample reports on every push.

The reasons behind these choices are in [decisions](decisions.md).
