# Pitch: a weekly training review you can trust

*One page for a decision-maker.*

## The problem

Each week, training data arrives as a folder of files from four different tools. Merging them by hand takes
hours, and the errors that matter are invisible: units mixed up, a vest worn by the wrong player, a file
counted twice, a gap read as zero. A wrong number that looks right leads to wrong decisions about players,
and to a staff that stops trusting the data.

## The proposal

A small tool that turns the weekly folder into **a report, then a dataset you can trust**:

1. **A verdict first**: *ready for the meeting*, or *N points to check*, each with who acts and what to do.
2. **Data-quality checks** on every batch, from "each file sent once" to "every player who trained has a GPS
   distance".
3. **Corrections that leave a trace**: each decision of the staff ("J21 wore D04 that day", "forgot the vest")
   is one line with a note saying who confirmed it. The report shows what each one changed; the raw files are
   never touched.
4. **One dataset to explore**: every week, cleaned and corrected, in a simple page (by position, one player
   over time) and as a CSV for any further analysis.

## What it costs

- **Software**: open source, built on standard tools (Python, pandas). No licence, no subscription.
- **Hardware**: runs on any laptop in seconds. No server.
- **People**: someone who sends the files each week (as today), and someone who maintains the tool a few
  hours per season: a new vendor format is one line of configuration.

## Risks, and how they are handled

| Risk | Mitigation |
| --- | --- |
| A vendor changes its export format | an unknown format stops the batch with a clear message; adding it is one entry |
| Health data leaks | the report stays a file on the club's storage; nothing is sent to a third party |
| The tool hides a problem | every doubt is reported, never fixed by guessing; automated tests run on every change |
| Only one person knows the tool | the code is short, tested, and documented for a newcomer ([architecture](architecture.md)) |
| Nobody uses it | a 4-week pilot with the staff, measured, before any further investment |

## The ask

A **4-week pilot** with the staff:

- week 0: time one review done the old way (the baseline);
- weeks 1–4: the staff use the report in the weekly meeting; two questions after each meeting;
- end of pilot: keep, change or stop, on the measures in [product](product.md#how-we-know-it-works):
  time to a ready review, errors found late, completeness, actual use.
