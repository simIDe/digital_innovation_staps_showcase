"""The explorer's charts, kept apart from the page.

Choices that hold for every chart:
- no ranking: we show who did what and what is missing, never a league table;
- one measure per chart, never two y-axes;
- a missing value is never drawn as 0: the line breaks, the label says "missing" or "absent";
- positions are compared side by side (small multiples), not by four colours on one chart.
"""

import altair as alt
import pandas as pd

from training_review.schema import POSITIONS

BLUE, INK, MUTED, BAND = "#2a78d6", "#0b0b0b", "#52514e", "#dcdbd7"
MEASURES = {"Distance (km)": "distance_m", "Mean heart rate (bpm)": "mean_hr_bpm"}


def with_value(records: pd.DataFrame, measure: str) -> pd.DataFrame:
    """Add `value` (km for distances) and `label`: the formatted value, "missing" or "absent"."""
    column = MEASURES[measure]
    df = records.copy()
    df["value"] = df[column] / 1000 if column == "distance_m" else df[column]
    df["label"] = df.value.map(lambda v: f"{v:.1f}" if column == "distance_m" else f"{v:.0f}")
    df.loc[df.value.isna(), "label"] = "missing"
    df.loc[~df.present, "label"] = "absent"
    return df


def by_position(records: pd.DataFrame, measure: str) -> alt.FacetChart:
    """One dot per player and session, one panel per position; the dark tick is the session's median."""
    df = with_value(records[records.present], measure).dropna(subset=["value"])
    y = alt.Y("session_id:N", title=None, sort=sorted(df.session_id.unique()))
    dots = (
        alt.Chart()
        .mark_circle(size=60, color=BLUE, opacity=0.6, stroke="white", strokeWidth=1)
        .encode(
            x=alt.X("value:Q", title=measure, scale=alt.Scale(zero=False)),
            y=y,
            tooltip=["player_id", "name", "session_id", "date", alt.Tooltip("label", title=measure)],
        )
    )
    median = (
        alt.Chart()
        .mark_tick(color=INK, thickness=2, size=16)
        .encode(x="median(value):Q", y=y, tooltip=[alt.Tooltip("median(value):Q", title="median", format=".1f")])
    )
    return (
        alt.layer(dots, median, data=df)
        .properties(width=170, height=26 * df.session_id.nunique())
        .facet(
            column=alt.Column(
                "position:N", title=None, sort=POSITIONS, header=alt.Header(labelFontWeight="bold", labelFontSize=13)
            )
        )
    )


def player_trend(records: pd.DataFrame, player_id: str, measure: str) -> alt.LayerChart:
    """One player across every session, against the middle half of the players in the same position."""
    df = with_value(records, measure)
    player = df[df.player_id == player_id]
    peers = df[(df.position == player.position.iloc[0]) & df.present].dropna(subset=["value"])
    band = (
        peers.groupby(["session_id", "date"])
        .value.agg(low=lambda v: v.quantile(0.25), median="median", high=lambda v: v.quantile(0.75))
        .reset_index()
    )
    data = band.merge(player[["session_id", "label", "value"]], on="session_id", how="right").sort_values(
        "date", ignore_index=True
    )
    data["segment"] = data.value.isna().cumsum()  # the line breaks at a gap instead of bridging it
    measured = data.dropna(subset=["value"])

    x = alt.X("date:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0, grid=False))
    area = (
        alt.Chart(data)
        .mark_area(color=BAND, opacity=0.6)
        .encode(x=x, y=alt.Y("low:Q", title=measure, scale=alt.Scale(zero=False)), y2="high:Q")
    )
    median = alt.Chart(data).mark_line(color=MUTED, strokeDash=[4, 3], strokeWidth=1.5).encode(x=x, y="median:Q")
    line = alt.Chart(measured).mark_line(color=BLUE, strokeWidth=2).encode(x=x, y="value:Q", detail="segment:N")
    points = (
        alt.Chart(measured)
        .mark_circle(color=BLUE, size=60, stroke="white", strokeWidth=2)
        .encode(x=x, y="value:Q", tooltip=["session_id", alt.Tooltip("label", title=measure)])
    )
    gaps = (
        alt.Chart(data[data.value.isna()])
        .mark_text(color=MUTED, fontStyle="italic", dy=-10)
        .encode(x=x, y="median:Q", text="label:N")
    )
    return alt.layer(area, median, line, points, gaps).properties(height=260)
