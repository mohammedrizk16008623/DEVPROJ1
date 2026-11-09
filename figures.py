"""Plotly figure builders. Each takes already-filtered data and returns a figure, so the
Generate Report callback in app.py only has to filter once and call these."""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analysis import BOROUGHS, CRASH_MEASURES, DISTRICTS, GEOJSON, HOUSING_MEASURES, TIME_BANDS

# Colours: blue is always crashes and orange always housing (the key in the page header). The five
# borough colours are separate hues used only where boroughs are compared, in a fixed order that
# never changes when a filter removes a borough. Emphasis follows the course rule: the districts a
# chart is about keep full colour and the rest are faded, so they stand out pre-attentively.
BORO_COLORS = dict(zip(BOROUGHS, ["#1baf7a", "#7b5cd6", "#eda100", "#00a3c4", "#e0457b"]))
CRASH_COLOR, CRASH_FADED = "#1c5cab", "#b9cfea"
BLUES = [[0, "#cde2fb"], [0.25, "#86b6ef"], [0.5, "#3987e5"], [0.75, "#1c5cab"], [1, "#0d366b"]]
HOUSING_COLOR = "#eb6834"
INK, INK_2, MUTED, GRID, SURFACE = "#15191c", "#4a5157", "#6b7177", "#e6e6e1", "#ffffff"

HOUSING_SHORT = {"affordable": "affordable units", "total": "units (all)", "buildings": "new buildings",
                 "deep": "0-50% AMI units", "low": "51-80% AMI units", "moderate": "81-165% AMI units",
                 "family": "2+ bedroom units", "rental": "rental units", "ownership": "homeownership units"}
CRASH_SHORT = {"crash_events": "serious crashes", "severe_injuries": "serious injuries",
               "non_severe_injuries": "other injuries", "positive_lookback_events": "repeat-location crashes"}


def _style(fig, title, subtitle="", height=460, legend=True):
    fig.update_layout(
        title=dict(text=title, subtitle=dict(text=subtitle, font=dict(size=13, color=INK_2)),
                   x=0, xanchor="left", y=0.97, yanchor="top", yref="container", font=dict(size=17, color=INK)),
        height=height, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif", size=13, color=INK_2),
        margin=dict(l=10, r=10, t=95, b=10), showlegend=legend,
        legend=dict(orientation="h", x=0, y=-0.12, xanchor="left", yanchor="top", title_text=""),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRID, font=dict(color=INK, size=13)))
    fig.update_xaxes(gridcolor=GRID, linecolor="#b9bab3", zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor="#b9bab3", zeroline=False, tickfont=dict(color=MUTED))
    return fig


def empty_figure(message, height=360):
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=15, color=INK_2), x=0.5, y=0.5,
                       xref="paper", yref="paper")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig, "", height=height, legend=False)


def map_figure(totals, filters):
    """Choropleth of the crash measure with housing bubbles on top: both domains on one map."""
    if totals.empty:
        return empty_figure("No community districts match these filters.", 560)
    h, c = HOUSING_SHORT[filters["housing"]], CRASH_SHORT[filters["crash"]]
    ids = totals["cd"].astype(str)
    custom = np.c_[totals["label"], totals["borough"], totals["housing"], totals["crash"]]
    hover = (f"<b>%{{customdata[0]}}</b>, %{{customdata[1]}}<br>{c.capitalize()}: %{{customdata[3]:,}}"
             f"<br>{h.capitalize()}: %{{customdata[2]:,}}<extra></extra>")
    fig = go.Figure()
    # Grey context layer: every district of the selected boroughs, so a district filter keeps its
    # surroundings visible (and the map zooms to the selected boroughs).
    context = DISTRICTS[DISTRICTS["borough"].isin(filters["boroughs"])]
    fig.add_trace(go.Choropleth(geojson=GEOJSON, featureidkey="properties.boro_cd",
                                locations=context["cd"].astype(str), z=[0] * len(context),
                                colorscale=[[0, "#ecece7"], [1, "#ecece7"]], showscale=False,
                                marker_line_color="#ffffff", marker_line_width=0.6, hoverinfo="skip"))
    fig.add_trace(go.Choropleth(
        geojson=GEOJSON, featureidkey="properties.boro_cd", locations=ids, z=totals["crash"], zmin=0,
        colorscale=BLUES, marker_line_color="#ffffff", marker_line_width=0.8, customdata=custom,
        hovertemplate=hover, name=c.capitalize(),
        colorbar=dict(title=dict(text=c.capitalize(), side="right"), thickness=12, len=0.7, outlinewidth=0)))
    with_housing = totals.merge(DISTRICTS[["cd", "lon", "lat"]], on="cd")
    with_housing = with_housing[with_housing["housing"] > 0]
    if not with_housing.empty:
        size = 6 + 34 * np.sqrt(with_housing["housing"] / with_housing["housing"].max())  # area ~ value
        fig.add_trace(go.Scattergeo(
            lon=with_housing["lon"], lat=with_housing["lat"], mode="markers",
            marker=dict(size=size, color=HOUSING_COLOR, opacity=0.8, line=dict(color="#ffffff", width=1.5)),
            customdata=np.c_[with_housing["label"], with_housing["borough"], with_housing["housing"],
                             with_housing["crash"]],
            hovertemplate=hover, name=f"Circle size = {h}"))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor=SURFACE)
    _style(fig, f"{c.capitalize()} and new {h} by district",
           "Shade = crashes; orange circle = housing.<br>Hover a district for both numbers.", height=620)
    fig.update_layout(margin=dict(l=0, r=0, t=95, b=0), legend=dict(y=0.02, yanchor="bottom", x=0.01,
                      bgcolor="rgba(255,255,255,0.85)"))
    return fig


def scatter_figure(totals, filters, stats):
    """Housing measure (x) against crash measure (y), one point per district."""
    if len(totals) < 2:
        return empty_figure("Select at least two districts to compare them.")
    h, c = HOUSING_SHORT[filters["housing"]], CRASH_SHORT[filters["crash"]]
    fig = go.Figure()
    x_med, y_med = totals["housing"].median(), totals["crash"].median()
    for borough in BOROUGHS:
        part = totals[totals["borough"] == borough]
        if part.empty:
            continue
        both_high = (part["housing"] > x_med) & (part["crash"] > y_med)
        fig.add_trace(go.Scatter(
            x=part["housing"], y=part["crash"], mode="markers", name=borough,
            marker=dict(color=BORO_COLORS[borough], size=11, line=dict(color=SURFACE, width=2),
                        opacity=np.where(both_high, 1.0, 0.35)),
            customdata=part["label"],
            hovertemplate=f"<b>%{{customdata}}</b><br>{h.capitalize()}: %{{x:,}}<br>{c.capitalize()}: %{{y:,}}<extra>{borough}</extra>"))
    fig.add_vline(x=x_med, line_dash="dot", line_color=MUTED, line_width=1)
    fig.add_hline(y=y_med, line_dash="dot", line_color=MUTED, line_width=1)
    rho, p, n = stats
    sub = ("Dotted lines = medians; solid points are above both.<br>" + (f"Rank correlation rho = {rho:.2f} (permutation p = {p:.2f}, n = {n}): "
           f"co-occurrence, not cause." if rho is not None else "Too few districts for a correlation."))
    _style(fig, f"New {h} vs {c}, by district", sub)
    fig.update_xaxes(title_text=f"New {h} (selected years)", rangemode="tozero")
    fig.update_yaxes(title_text=f"{c.capitalize()} (selected years)", rangemode="tozero")
    return fig


def ranked_bar_figure(totals, filters, top=15):
    """Districts with the highest crash measure, labelled with the housing they received."""
    if totals.empty:
        return empty_figure("No community districts match these filters.")
    h, c = HOUSING_SHORT[filters["housing"]], CRASH_SHORT[filters["crash"]]
    ranked = totals.sort_values(["crash", "cd"], ascending=[False, True]).head(top).iloc[::-1]
    high_housing = ranked["housing"] > totals["housing"].median()
    fig = go.Figure(go.Bar(
        x=ranked["crash"], y=[f"{lab}  ({v:,} {h})" for lab, v in zip(ranked["label"], ranked["housing"])],
        orientation="h", marker=dict(color=np.where(high_housing, CRASH_COLOR, CRASH_FADED), cornerradius=4),
        customdata=np.c_[ranked["label"], ranked["borough"], ranked["housing"]],
        hovertemplate=(f"<b>%{{customdata[0]}}</b>, %{{customdata[1]}}<br>{c.capitalize()}: %{{x:,}}"
                       f"<br>{h.capitalize()}: %{{customdata[2]:,}}<extra></extra>")))
    _style(fig, f"Districts with the most {c}", f"Dark bar = also above-median new {h}.<br>In brackets: new {h} in the same years.",
           height=620, legend=False)
    fig.update_layout(bargap=0.25)
    fig.update_xaxes(title_text=c.capitalize())
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=INK_2))
    return fig


def trend_figure(table, filters):
    """Year-by-year totals per borough: housing on the left, crashes on the right (two panels,
    never two y-axes on one plot)."""
    if table.empty:
        return empty_figure("No community districts match these filters.")
    h, c = HOUSING_SHORT[filters["housing"]], CRASH_SHORT[filters["crash"]]
    yearly = table.groupby(["borough", "year"], as_index=False)[["housing", "crash"]].sum()
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1,
                        subplot_titles=(f"New {h}", c.capitalize()))
    for borough in BOROUGHS:
        part = yearly[yearly["borough"] == borough]
        if part.empty:
            continue
        for col, measure in [(1, "housing"), (2, "crash")]:
            fig.add_trace(go.Scatter(
                x=part["year"], y=part[measure], mode="lines+markers", name=borough, legendgroup=borough,
                showlegend=col == 1, line=dict(color=BORO_COLORS[borough], width=2), marker=dict(size=8),
                hovertemplate=f"{borough}, %{{x}}: %{{y:,}}<extra></extra>"), row=1, col=col)
    _style(fig, "Year by year, by borough",
           "Crashes counted only where the source placed them in a district;<br>that share differs by year.")
    fig.update_xaxes(tickmode="array", tickvals=filters["years"], showgrid=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_annotations(font=dict(size=13, color=INK_2))
    return fig


def heatmap_figure(profile, filters):
    """Share of each borough's crash measure in each hour of the day."""
    if profile.empty or profile.to_numpy().sum() == 0:
        return empty_figure("No crashes recorded for these filters.")
    c = CRASH_SHORT[filters["crash"]]
    profile = profile.reindex([b for b in BOROUGHS if b in profile.index])
    totals = profile.sum(axis=1).replace(0, np.nan)
    share = profile.div(totals, axis=0) * 100
    fig = go.Figure(go.Heatmap(
        z=share.to_numpy(), x=list(range(24)), y=list(share.index), colorscale=BLUES, xgap=2, ygap=2,
        customdata=profile.to_numpy(), colorbar=dict(title=dict(text="% of borough", side="right"),
                                                      thickness=12, outlinewidth=0, ticksuffix="%"),
        hovertemplate="%{y}, %{x}:00-%{x}:59<br>%{z:.1f}% of the borough's " + c + " (%{customdata:,})<extra></extra>"))
    hours = TIME_BANDS[filters["time"]][1]
    if filters["time"] != "all":   # outline the selected time band (night wraps past midnight)
        runs, start = [], hours[0]
        for a, b in zip(hours, hours[1:] + [None]):
            if b != a + 1:
                runs.append((start, a))
                start = b
        for lo, hi in runs:
            fig.add_shape(type="rect", x0=lo - 0.5, x1=hi + 0.5, y0=-0.5, y1=len(share) - 0.5,
                          line=dict(color=INK, width=2), fillcolor="rgba(0,0,0,0)")
    _style(fig, f"When in the day {c} happen",
           "Each row sums to 100%. Shows all hours; the selected time band is outlined. "
           "Hour 0 includes records stored as exactly 00:00, which may be placeholder times.",
           height=max(300, 150 + 46 * len(share)), legend=False)
    fig.update_xaxes(title_text="Hour of day", tickvals=list(range(0, 24, 3)), showgrid=False)
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig
