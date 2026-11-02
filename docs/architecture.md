# Architecture

One idea shapes the code: **a pure core, a thin shell**. The core reads a folder and returns data; it
writes nothing and asks nothing. The shell (the command line and the report) does the input and output.
The core is where the rules live, so that is where the tests are.

## In context

```mermaid
flowchart LR
    tools["Training-ground tools<br/>GPS vests · heart-rate straps<br/>attendance · squad · device sheet"]
    operator(["Operator"])
    folder[("Weekly batch folder<br/>raw CSV files")]
    review["review report"]
    out[("reports/batchN/<br/>report.html<br/>records.csv · issues.csv")]
    staff(["Staff"])

    tools --> operator -->|collects the week's files| folder --> review --> out
    out -->|verdict, checks, overview| staff
    out -->|file problems| operator
```

The raw files are never modified. Everything the tool produces can be rebuilt from them at any time.

## Modules

```mermaid
flowchart TB
    subgraph shell["Shell: input and output"]
        cli["cli.py<br/>the review command"]
        report["report.py<br/>+ templates/report.html"]
    end
    subgraph core["Core: pure functions, no I/O apart from reading the batch"]
        quality["quality.py<br/>checks · completeness · verdict"]
        pipeline["pipeline.py<br/>batch folder → clean table + issues"]
        formats["formats.py<br/>known files, by their columns"]
        rules["rules.py<br/>value rules"]
        issues["issues.py<br/>kinds of issue · checks catalogue"]
        schema["schema.py<br/>data contract (pandera)"]
    end

    cli --> report
    cli --> quality
    report --> quality
    quality --> pipeline
    quality --> issues
    pipeline --> formats
    pipeline --> rules
    pipeline --> issues
    pipeline --> schema
```

Dependencies only point down. Each module has one reason to change:

| When this changes… | …edit only |
|---|---|
| a vendor changes its export, or a new tool appears | `formats.py` |
| a plausibility rule (e.g. the heart-rate range) | `rules.py` |
| what a check is called, who acts, what to do | `issues.py` |
| how files are merged | `pipeline.py` |
| what the clean table guarantees to its users | `schema.py` |
| how the report looks | `templates/report.html` |

## What happens in `review report`

```mermaid
sequenceDiagram
    actor U as Operator
    participant C as cli
    participant P as pipeline
    participant F as formats
    participant S as schema
    participant Q as quality
    participant R as report

    U->>C: review report batch5/
    C->>P: clean_batch(folder)
    P->>F: read_batch(folder)
    F-->>P: files grouped by kind, copies skipped
    Note over F: unknown columns → UnknownFormat:<br/>stop, nothing written, exit code 2
    P->>P: attendance + squad → one row per player and session
    P->>P: + GPS in metres, via the device sheet
    P->>P: + heart rate
    P->>P: every doubt → an Issue
    P->>S: validate the clean table
    P-->>C: Batch(files, records, issues)
    C->>Q: assess(batch)
    Q-->>C: checks, completeness, verdict
    C->>R: write(batch)
    R-->>U: report.html · records.csv · issues.csv
    C-->>U: exit code 0 ready / 1 points to check
```

## How the clean table is built

```mermaid
flowchart LR
    att["attendance<br/>session · date · player · present"]
    squad["squad<br/>player · name · position"]
    gps["GPS exports<br/>device · date · distance<br/>km or m"]
    dev["device sheet<br/>device → player"]
    hr["heart rate<br/>player · date · bpm"]

    att --> base["one row per<br/>player × session"]
    squad --> base
    gps -->|to metres| g2["distance per<br/>device and day"]
    dev --> g3["distance per<br/>player and day"]
    g2 --> g3
    g3 -->|left join| table["clean table<br/>(schema.Records)"]
    base --> table
    hr -->|left join| table

    g3 -. "device on a player who did not train" .-> iss["issues"]
    gps -. "negative value, repeated line" .-> iss
    table -. "trained but no value" .-> iss
```

Left joins keep every player on the attendance sheet: a missing measurement stays an empty cell and becomes
an issue, it never removes the row and never becomes 0.

## Quality: from issues to a verdict

```mermaid
flowchart LR
    issues["issues<br/>(kind, where, problem)"] --> checks{"one check<br/>per kind"}
    checks -->|no issue| pass["passed"]
    checks -->|handled automatically<br/>copy, repeated line| info["handled"]
    checks -->|a person must look| check["to check"]
    check --> verdict{"any?"}
    verdict -->|no| ready["Ready for the meeting · exit 0"]
    verdict -->|yes| todo["N points to check · exit 1"]
```

## Engineering choices

- **Data contract.** `schema.Records` (pandera) states what the clean table guarantees: one row per player
  and session, distances ≥ 0, heart rates in range, known positions. The pipeline validates its own output;
  a broken rule fails at once instead of showing a wrong number.
- **Configuration as data.** File formats and checks are declared in lists (`formats.FORMATS`,
  `issues.CHECKS`), not buried in `if` statements.
- **Static output.** The report is one HTML file with inline CSS, no JavaScript, no server. It can be opened,
  printed, archived or e-mailed as is.
- **Tests on realistic data.** The sample batches carry the real problems; each test names the behaviour it
  protects (`test_a_gap_stays_a_gap`).
- **Reproducible.** `uv.lock` pins every dependency; the sample data is generated by a seeded script; CI runs
  lint, tests and the sample reports on every push.

The reasons behind these choices are in [decisions](decisions.md).
