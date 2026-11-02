# Data

## A batch

A batch is one folder per training week, holding the CSV files as they were sent. File names do not matter
(`fieldsense_jeudi_FINAL.csv` is fine): each file is recognised **by its columns**, the separator (`,` or
`;`) is detected, and a decimal comma (`4,24`) is read as a number.

| Kind | Required | Known formats (`formats.FORMATS`) | Columns used |
| --- | --- | --- | --- |
| squad | exactly one | squad | `player_id`, `name`, `position` (GK, DEF, MID, FWD) |
| device sheet | exactly one | device sheet | `device_id`, `player_id` |
| attendance | exactly one | attendance | `session_id`, `date`, `player_id`, `present` (yes/no), `minutes` |
| GPS | any number | TrackPro (km), TrackPro v2 (km, `;`, decimal comma), FieldSense (m) | device, date, distance |
| heart rate | any number | heart-rate straps | `player_id`, `date`, `mean_hr_bpm` |

A file with columns that match no known format stops the whole batch: we never guess what a column means.
Columns a format does not use (`duration_min`, `coverage_pct`) are read and ignored.

## The clean table: `records.csv`

One row per player and session on the attendance sheet. Its contract is `schema.Records`, checked every time.

| Column | Type | Meaning | Guarantee |
| --- | --- | --- | --- |
| `session_id` | text | the session, e.g. `S101` | with `player_id`, unique |
| `date` | text | `YYYY-MM-DD` | format checked |
| `player_id` | text | e.g. `J07` | |
| `name` | text | from the squad | empty if the player is not in the squad (reported) |
| `position` | text | GK, DEF, MID or FWD | one of these, or empty |
| `present` | bool | from the attendance sheet | |
| `minutes` | number | minutes trained | ≥ 0 or empty |
| `distance_m` | number | GPS distance, **in metres** whatever the vendor | ≥ 0, or empty: **empty means no valid measurement, never 0** |
| `mean_hr_bpm` | number | mean heart rate | 30–230, or empty |
| `note` | text | the staff's correction or explanation for this record | empty if none |

A player who was absent keeps their row (`present = false`, measurements empty): an absence is information.

## The issues: `issues.csv`

Every doubt found, one row each: `kind`, `problem` (in plain words), where it is (`file`, `player_id`,
`session_id`, `device_id`, `date`), `who_acts`, `status` and `resolution` (the staff's note).

| Status | Meaning | Counts in the verdict |
| --- | --- | --- |
| `open` | a person must look | yes |
| `corrected` | resolved by a `reassign`: the data changed | no |
| `explained` | resolved by an `explain`: the data did not change | no |
| `handled` | the fix was certain and done automatically (a copy, a repeated line) | no |

## The checks

Each kind of issue belongs to one check (`issues.CHECKS`). A check passes when the batch has no issue of
its kind; otherwise it takes the most serious status of its issues.

| Check | Issue kind | Example in the samples | Effect on the data | Resolved by | Who acts |
| --- | --- | --- | --- | --- | --- |
| Each file sent once | file sent twice | batch2: `HR_export (1).csv` | the copy is ignored | automatic | operator |
| No repeated line | repeated line | batch1: J07 twice on 27 Oct | kept once | automatic | operator |
| Values are plausible | invalid value | batch4: D11 at −6.47 km | the value is left out | explain | operator |
| Every device is on the device sheet | unknown device | none | the distance is left out | explain, or fix the sheet | staff |
| Every player is in the squad | unknown player | batch1: J99, a trialist | heart rate ignored | explain | staff |
| Devices were worn by players who trained | device on absent player | batch1: D04 on absent J04 (J21 wore it); batch3: D09 | the distance is left out | reassign | staff |
| One GPS record per player and session | two GPS records | none | the first one is kept | explain | staff |
| Every player who trained has a GPS distance | no GPS | batch1: J15; batch4: J11, J17 | stays empty | explain | staff |
| Every player who trained has a heart rate | no heart rate | batch1: J12's strap stopped | stays empty | explain | staff |
| Every correction was applied | unused correction | none | none: the correction is ignored | fix the correction | staff |

One real event often raises two issues: when J21 wears D04, the report shows *D04 on absent J04* **and**
*J21 has no GPS*. One `reassign` resolves both: the distance moves to J21.

## The corrections: `data/corrections.yml`

One list per batch, one entry per decision. Every entry needs a `note`: who confirmed it, and how.

```yaml
batch1:
  - reassign: {device: D04, date: 2026-10-29, to: J21}
    note: J21's own vest was broken, so J21 wore D04 (J04 was absent). Confirmed by the physical trainer.
  - explain: {issue: no GPS, player: J15, session: S102}
    note: Vest forgotten in the locker room. Confirmed by the player.
```

| Action | Fields | Effect |
| --- | --- | --- |
| `reassign` | `device`, `date`, `to` | for that device and that day only, the distance goes to `to` instead of the player on the device sheet |
| `explain` | `issue` (a kind from the table above) and any of `player`, `session`, `device`, `date` | every issue of that kind matching all the given fields becomes `explained`; the data does not change |

The file is validated before anything runs: an unknown field, an unknown issue kind, a missing note or an
entry with both actions stops the run (exit code 2). The report lists each correction applied with its
effect, and `reports/corrections.csv` keeps them all.

## The unified dataset

`review report` writes each batch in `reports/batchN/`, then rebuilds `reports/records.csv`, `issues.csv`
and `corrections.csv` with every batch reported so far, plus a `batch` column. They are what
`review explore` reads, and what any further analysis should start from.

## The samples

`data/samples/batch1` to `batch4` are four synthetic training weeks (3 sessions each, 22 then 23 players),
generated by `scripts/generate_samples.py` with a fixed seed. Names and numbers are invented. What each
batch hides is listed at the top of the script; `data/corrections.yml` resolves all of it except J17's
missing GPS in batch4, left open on purpose.
