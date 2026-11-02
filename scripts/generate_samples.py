"""Generate the synthetic sample batches in data/samples/: four training weeks of a 23-player squad.

The output is committed; run `uv run python scripts/generate_samples.py` only to rebuild it.
Each batch hides realistic problems, so that every quality check has something to catch:

- batch1: GPS in km (TrackPro) and in m (FieldSense); device D04 worn by J21, but the device sheet says J04,
  who was absent; J12's heart-rate strap stopped; a repeated GPS line (J07); an unknown player (J99, a trialist);
- batch2: TrackPro changed its export (semicolons, new headers, decimal commas); the heart-rate file sent twice;
- batch3: J08 wore absent J09's device D09; J05's strap failed;
- batch4: J06 out all week; J17 trained without GPS; a device glitch gives J11 a negative distance.

All names and numbers are invented.
"""

import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / "data" / "samples"
RNG = random.Random(44)

NAMES = [
    "Hugo",
    "Théo",
    "Nathan",
    "Lucas",
    "Yanis",
    "Enzo",
    "Karim",
    "Louis",
    "Malik",
    "Bastien",
    "Samy",
    "Adam",
    "Noah",
    "Rayan",
    "Jules",
    "Mathis",
    "Ilyes",
    "Gabriel",
    "Tom",
    "Moussa",
    "Axel",
    "Ewan",
    "Sacha",
]
POSITIONS = ["GK"] * 2 + ["DEF"] * 7 + ["MID"] * 7 + ["FWD"] * 6 + ["MID"]
METRES_PER_MIN = {"GK": 55, "DEF": 82, "MID": 92, "FWD": 86}


def swapped(*sessions):
    """From batch 2 on, J21 wears D04 and J04 wears D21, as the device sheet says."""
    return {key: device for s in sessions for key, device in ((("J21", s), "D04"), (("J04", s), "D21"))}


BATCHES = {
    1: {
        "sessions": [
            ("S101", "2026-10-26", 75, "trackpro"),
            ("S102", "2026-10-27", 75, "trackpro"),
            ("S103", "2026-10-29", 60, "fieldsense"),
        ],
        "squad": 22,
        "absent": {("J09", "S101"), ("J04", "S103")},
        "no_gps": {("J15", "S102")},
        "fixed": {
            ("J07", "S101"): (75, 6450, 151),
            ("J12", "S101"): (75, 5820, None),
            ("J18", "S101"): (60, 4900, 146),
        },
        "worn": {("J21", "S103"): "D04"},  # J21's unit broke; the sheet was not updated
        "sheet_swaps": {},
    },
    2: {
        "sessions": [
            ("S104", "2026-11-02", 75, "trackpro_v2"),
            ("S105", "2026-11-03", 75, "trackpro_v2"),
            ("S106", "2026-11-05", 60, "fieldsense"),
        ],
        "squad": 23,
        "absent": {("J04", "S104"), ("J04", "S105"), ("J16", "S106")},
        "no_gps": set(),
        "fixed": {},
        # J21 kept D04; J04, back on Thursday, took J21's repaired D21. The sheet is up to date this time.
        "worn": swapped("S104", "S105", "S106"),
        "sheet_swaps": {"D04": "J21", "D21": "J04"},
    },
    3: {
        "sessions": [
            ("S107", "2026-11-09", 75, "trackpro_v2"),
            ("S108", "2026-11-10", 75, "trackpro_v2"),
            ("S109", "2026-11-12", 60, "fieldsense"),
        ],
        "squad": 23,
        "absent": {("J14", "S107"), ("J09", "S108")},
        "no_gps": set(),
        "fixed": {("J05", "S109"): (60, 4920, None)},
        "worn": {**swapped("S107", "S108", "S109"), ("J08", "S108"): "D09"},  # J08 grabbed absent J09's device
        "sheet_swaps": {"D04": "J21", "D21": "J04"},
    },
    4: {
        "sessions": [
            ("S110", "2026-11-16", 75, "trackpro_v2"),
            ("S111", "2026-11-17", 75, "trackpro_v2"),
            ("S112", "2026-11-19", 60, "fieldsense"),
        ],
        "squad": 23,
        "absent": {("J06", s) for s in ("S110", "S111", "S112")},
        "no_gps": {("J17", "S111")},
        "fixed": {},
        "negative": {("J11", "S110")},  # a device glitch
        "worn": swapped("S110", "S111", "S112"),
        "sheet_swaps": {"D04": "J21", "D21": "J04"},
    },
}


def players(n):
    return pd.DataFrame(
        {"player_id": [f"J{i:02d}" for i in range(1, n + 1)], "name": NAMES[:n], "position": POSITIONS[:n]}
    )


def batch(root, number, spec):
    folder = root / f"batch{number}"
    folder.mkdir(parents=True, exist_ok=True)
    roster = players(spec["squad"])
    roster.to_csv(folder / "effectif.csv", index=False, lineterminator="\n")

    devices = {f"D{p[1:]}": p for p in roster.player_id}
    for device, player in spec["sheet_swaps"].items():
        devices[device] = player
    sheet = pd.DataFrame([(d, p) for d, p in devices.items() if p], columns=["device_id", "player_id"])
    sheet.to_csv(folder / "attribution_boitiers.csv", index=False, lineterminator="\n")

    presence, gps, hr = [], [], []
    for session_id, date, planned, vendor in spec["sessions"]:
        for player_id, position in zip(roster.player_id, roster.position, strict=True):
            key = (player_id, session_id)
            if key in spec["absent"]:
                presence.append((session_id, date, player_id, "no", 0))
                continue
            if key in spec["fixed"]:
                minutes, dist, mean_hr = spec["fixed"][key]
            else:
                minutes = planned if RNG.random() > 0.1 else planned - 15
                dist = round(minutes * METRES_PER_MIN[position] * RNG.uniform(0.9, 1.1), -1)
                mean_hr = RNG.randint(138, 162) if position != "GK" else RNG.randint(118, 132)
            if key in spec.get("negative", ()):
                dist = -dist
            presence.append((session_id, date, player_id, "yes", minutes))
            if key not in spec["no_gps"]:
                device = spec["worn"].get(key, f"D{player_id[1:]}")
                gps.append((vendor, device, date, minutes, dist))
            hr.append((player_id, date, mean_hr, 38 if mean_hr is None else RNG.randint(92, 100)))

    pd.DataFrame(presence, columns=["session_id", "date", "player_id", "present", "minutes"]).to_csv(
        folder / "presence.csv", index=False, lineterminator="\n"
    )
    hr_df = pd.DataFrame(hr, columns=["player_id", "date", "mean_hr_bpm", "coverage_pct"])
    hr_df = hr_df.astype({"mean_hr_bpm": "Int64"})
    return folder, gps, hr_df


def write_gps(folder, gps, number):
    by_file = {}
    for vendor, device, date, minutes, dist in gps:
        by_file.setdefault((vendor, date), []).append((device, date, minutes, dist))
    for (vendor, date), rows in by_file.items():
        if vendor == "trackpro":
            df = pd.DataFrame(
                [(d, dt, m, round(x / 1000, 2)) for d, dt, m, x in rows],
                columns=["device_id", "date", "duration_min", "distance_km"],
            )
            name = f"TrackPro_export_{date}.csv"
            if date == "2026-10-27":
                df = pd.concat([df, df[df.device_id == "D07"]], ignore_index=True)
                name = f"TrackPro_export_{date} (1).csv"
            df.to_csv(folder / name, index=False, lineterminator="\n")
        elif vendor == "trackpro_v2":
            # The vendor's new export: French locale, new headers.
            lines = ["Device;Date;Duration (min);Distance (km)"]
            lines += [f"{d};{dt};{m};{x / 1000:.2f}".replace(".", ",") for d, dt, m, x in rows]
            (folder / f"TrackPro_{date}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        else:
            df = pd.DataFrame(
                [(d, dt, m, int(x)) for d, dt, m, x in rows],
                columns=["device", "session_date", "minutes", "distance_m"],
            )
            name = "fieldsense_jeudi_FINAL.csv" if number == 1 else f"fieldsense_{date}.csv"
            df.to_csv(folder / name, index=False, sep=";", lineterminator="\n")


def main(root: Path = ROOT):
    for number, spec in BATCHES.items():
        folder, gps, hr = batch(root, number, spec)
        write_gps(folder, gps, number)
        if number == 1:
            hr = pd.concat([hr, pd.DataFrame([("J99", "2026-10-27", 149, 97)], columns=hr.columns)])
        hr.to_csv(folder / "HR_export.csv", index=False, lineterminator="\n")
        if number == 2:
            hr.to_csv(folder / "HR_export (1).csv", index=False, lineterminator="\n")  # sent twice by mistake
    print("written to", root)


if __name__ == "__main__":
    main()
