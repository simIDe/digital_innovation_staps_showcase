# Product

## The problem

After each training week, the staff collect the files the training ground produced:

- the **squad** list and the **attendance** sheet, kept by hand;
- the **device sheet**: which GPS vest belongs to which player;
- **GPS exports** from two vendors, one file per session, each in its own format;
- **heart-rate** data from the straps.

Before the weekly meeting, someone merges them in a spreadsheet. It takes time, and the worst errors are
silent: a vendor exports kilometres and the other metres, a vest is worn by the wrong player that day, a file
is sent twice and every value counts double, an empty cell becomes 0 and a player who forgot the vest seems
to have run nothing.

The cost is not only the hours. **A number that is wrong but looks right is worse than no number**:
it leads to a wrong decision about a player, and the staff stop trusting the data.

## Who it is for

| Who | What they need, in their words | What the report gives them |
|---|---|---|
| **The staff** (the people who plan and run training) | "Can I use these numbers in the meeting?" "What happened this week?" | a verdict at the top, the points to check with what to do, an overview of every player and session |
| **The operator** (whoever collects and sends the files) | "Did the files arrive, and were they readable?" | the list of files and what each was recognised as, file problems separated from pitch problems |
| **A decision-maker** (head of performance, club management) | "Is this worth the effort, and is the data safe?" | [the pitch](pitch.md), the success measures below |

Every issue says **who acts**: the staff for what happened on the pitch, the operator for the files.
Nobody has to read an issue that is not theirs to solve.

## What we learnt, and the principles it gave

These come from looking at the real files, and asking the staff about each oddity rather than guessing.

1. **Missing is never zero.** A player without GPS did not run 0 m. The report writes *missing*, and asks
   for an explanation.
2. **Never guess, always report.** When a device was recorded on an absent player, the code does not decide
   who wore it. It asks, and the staff fix the device sheet.
3. **Quality first, then the numbers.** The report opens on the verdict and the checks. The overview comes
   after, once you know how far to trust it.
4. **No ranking.** A "who ran the most" chart puts goalkeepers last by design and turns a review into a league
   table. The report shows who did what, and what is missing.
5. **No player data where it does not belong.** Heart rate is health data under the GDPR. The report is a
   file kept by the club, not a message in a chat.
6. **Describe, do not diagnose.** The report says what was recorded. It does not say who is fit, tired or at
   risk: that is the staff's job, with information the files do not hold.

## What it does not do, on purpose

- No fatigue, readiness or injury-risk score: the data cannot support it, and a wrong score is dangerous.
- No dashboard server, no accounts, no database: a weekly decision needs a weekly report, not a live app.
  A static file opens anywhere, can be printed, and reads the same in a year.
- No automatic correction of identities: a person confirms, the device sheet carries the correction.

Each of these can change if the staff ask for it. See the [roadmap](#roadmap).

## How we know it works

The tool is worth keeping only if it changes the week of the staff. We measure, during a pilot:

| Measure | Today (to measure before the pilot) | Target |
|---|---|---|
| Time from the last file received to a review ready for the meeting | hours, by hand | under 10 minutes |
| Errors found in the meeting, after the review was shared | unknown: silent | 0 |
| Records complete at meeting time (GPS and heart rate for every player who trained) | unknown | measured every week, explained when below 100% |
| Weeks the staff used the report in the meeting | — | every week of the pilot |

The baseline is measured first, by timing one week done the old way. The targets are hypotheses: the pilot
tells us if they were the right ones.

## Roadmap

Driven by what the staff ask for after using the report, not by what is technically interesting.

| When | What | Why |
|---|---|---|
| **Now** | the weekly report, the checks, the clean CSV | the smallest thing that saves time and prevents silent errors |
| **Next** | run it automatically when a batch lands in a shared folder, and send the link to who acts ([how](extending.md#run-it-every-week)) | nobody has to remember to run it |
| **Next** | trends across weeks for one player, against their position | asked as soon as several weeks exist; needs the weekly CSVs kept together |
| **Later** | resolve issues inside a small app, with a note kept for each decision | only if fixing the device sheet by hand proves too slow |
| **Later** | a third GPS vendor, or a new sensor | one entry in `formats.py`, see [extending](extending.md) |

## How we collect feedback

- After each meeting during the pilot, two questions to the staff: *what did you look at first?* and
  *what did you still have to check by hand?*
- Every "I had to check by hand" is a candidate for a new check. Every section nobody looked at is a candidate
  for removal.
