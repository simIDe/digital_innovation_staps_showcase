"""The explorer: every batch reported so far, cleaned and corrected, in one page. Run: uv run review explore

It only reads what `review report` wrote (reports/records.csv, issues.csv, corrections.csv): nothing is
computed again and nothing is written, so what you explore is exactly what the reports say.
"""

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from training_review import charts
from training_review.schema import POSITIONS

OUT = Path(os.environ.get("REVIEW_REPORTS", "reports"))  # set by `review explore --out`

st.set_page_config(page_title="Training explorer", page_icon="⚽", layout="wide")
st.title("Training explorer")

if not (OUT / "records.csv").exists():
    st.info("Nothing to explore yet. Run `uv run review report data/samples/*` first.")
    st.stop()

records = pd.read_csv(OUT / "records.csv", dtype={"note": "str"})
issues = pd.read_csv(OUT / "issues.csv")
corrections = pd.read_csv(OUT / "corrections.csv")

with st.sidebar:
    batches = st.multiselect("Batches", sorted(records.batch.unique()), default=sorted(records.batch.unique()))
    positions = st.multiselect("Positions", POSITIONS, default=POSITIONS)
    measure = st.radio("Measure", list(charts.MEASURES))
    st.caption(f"Source: `{OUT.as_posix()}/records.csv`, written by `review report`. Synthetic data.")

shown = records[records.batch.isin(batches) & records.position.isin(positions)]
trained = shown[shown.present]
open_issues = issues[issues.batch.isin(batches) & (issues.status == "open")]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Sessions", shown.session_id.nunique())
c2.metric("Player attendances", len(trained))
c3.metric("Complete records", f"{trained[['distance_m', 'mean_hr_bpm']].notna().all(axis=1).mean():.0%}")
c4.metric("Open issues", len(open_issues))

table_tab, sessions_tab, player_tab, quality_tab = st.tabs(
    ["Data", "Sessions by position", "One player over time", "Quality and corrections"]
)

with table_tab:
    st.caption(
        "One row per player and session. Empty means no valid measurement, never 0. "
        "`note` holds the staff's correction or explanation."
    )
    st.dataframe(
        shown.assign(distance_km=shown.distance_m / 1000).drop(columns="distance_m"),
        hide_index=True,
        column_order=[
            "batch",
            "session_id",
            "date",
            "player_id",
            "name",
            "position",
            "present",
            "minutes",
            "distance_km",
            "mean_hr_bpm",
            "note",
        ],
        column_config={"distance_km": st.column_config.NumberColumn("distance (km)", format="%.2f")},
    )
    st.download_button("Download these rows (CSV)", shown.to_csv(index=False), "training_records.csv", "text/csv")

with sessions_tab:
    st.caption("One dot per player. The dark tick is the median. Compare a position with itself, session to session.")
    st.altair_chart(charts.by_position(shown, measure))

with player_tab:
    names = records.drop_duplicates("player_id").set_index("player_id").name
    player = st.selectbox("Player", sorted(names.index), format_func=lambda p: f"{p} · {names[p]}")
    st.caption("Grey band: the middle half of the players in the same position; dashed line: their median.")
    st.altair_chart(charts.player_trend(records[records.batch.isin(batches)], player, measure), width="stretch")
    notes = records[(records.player_id == player) & records.note.notna()]
    if not notes.empty:
        st.dataframe(notes[["batch", "session_id", "date", "note"]], hide_index=True)

with quality_tab:
    st.subheader("Corrections applied")
    st.dataframe(corrections[corrections.batch.isin(batches)], hide_index=True)
    st.subheader("Issues")
    statuses = ["open", "corrected", "explained", "handled"]
    status = st.segmented_control("Status", statuses, selection_mode="multi", default=statuses)
    st.dataframe(
        issues[issues.batch.isin(batches) & issues.status.isin(status or [])],
        hide_index=True,
        column_order=["batch", "status", "kind", "player_id", "session_id", "problem", "resolution", "who_acts"],
    )

st.caption("This explorer describes what was recorded; it does not say who is fit or tired. Players are never ranked.")
