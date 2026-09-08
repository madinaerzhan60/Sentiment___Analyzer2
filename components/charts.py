from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from services.analytics_service import issue_stats, platform_stats, trend

COLORS = {"positive": "#43C59E", "neutral": "#8EA4BF", "negative": "#EF6A6A"}


def _style(fig, height=350):
    fig.update_layout(
        height=height, margin=dict(l=12, r=12, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font_color="#DCE6F2", legend_title_text="",
        hoverlabel=dict(bgcolor="#102844"),
    )
    fig.update_xaxes(gridcolor="rgba(142,164,191,.12)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(142,164,191,.12)", zeroline=False)
    return fig


def trend_chart(df: pd.DataFrame):
    data = trend(df)
    fig = px.line(data, x="date", y="reviews", color="sentiment", markers=True,
                  color_discrete_map=COLORS, category_orders={"sentiment": ["positive", "neutral", "negative"]})
    fig.update_traces(line_width=3)
    return _style(fig)


def platform_chart(df: pd.DataFrame):
    data = platform_stats(df)
    fig = go.Figure(go.Bar(x=data["source"], y=data["reviews"], marker_color="#4F7CAC",
                           customdata=data[["negative_pct"]],
                           hovertemplate="%{x}<br>%{y} reviews<br>%{customdata[0]:.1f}% negative<extra></extra>"))
    fig.update_layout(yaxis_title="Reviews", xaxis_title=None)
    return _style(fig)


def issues_chart(df: pd.DataFrame):
    data = issue_stats(df)
    fig = px.bar(data, x="reviews", y="issue", orientation="h", text="reviews",
                 custom_data=["percentage"], color_discrete_sequence=["#C8A96B"])
    fig.update_traces(hovertemplate="%{y}<br>%{x} reviews (%{customdata[0]:.1f}%)<extra></extra>")
    fig.update_layout(xaxis_title="Negative reviews", yaxis_title=None)
    return _style(fig)


def sentiment_chart(df: pd.DataFrame):
    counts = df[df["analysis_status"].eq("done")]["sentiment"].value_counts().reindex(
        ["positive", "neutral", "negative"], fill_value=0).rename_axis("sentiment").reset_index(name="reviews")
    fig = px.pie(counts, names="sentiment", values="reviews", hole=.7, color="sentiment", color_discrete_map=COLORS)
    fig.update_traces(textinfo="percent+label", sort=False)
    return _style(fig)

