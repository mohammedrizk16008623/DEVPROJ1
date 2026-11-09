"""NYC Housing & Street Safety: interactive website for Milestone 1.

Research question: do neighbourhoods experiencing a surge in new affordable-housing construction
also experience more severe street-safety problems?

Run locally:   python app.py            (http://127.0.0.1:8050)
Production:    the WSGI app is `server` (Vercel imports it in api/index.py)
"""
import os

from dash import ALL, Dash, Input, Output, State, callback, ctx, dcc, html, no_update

from analysis import (BOROUGHS, CRASH_MEASURES, DEFAULTS, DISTRICTS, HOUSING_MEASURES, LABELS, TIME_BANDS,
                      YEARS, district_totals, district_year_table, hourly_profile, normalise_filters,
                      parse_search, spearman, strength)
from figures import (CRASH_SHORT, HOUSING_SHORT, heatmap_figure, map_figure, ranked_bar_figure,
                     scatter_figure, trend_figure)

app = Dash(__name__, title="NYC Housing & Street Safety", suppress_callback_exceptions=True)
server = app.server   # WSGI entry point used in production

GRAPH_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                "toImageButtonOptions": {"format": "png", "scale": 2}}
MAP_CONFIG = {**GRAPH_CONFIG, "scrollZoom": False}   # let the page scroll past the map
SEARCH_EXAMPLES = ["Brooklyn 2022 new buildings", "Bronx family units injuries", "Queens evening crashes",
                   "BK 01 BX 01 2024-2025", "Manhattan rental repeat crashes night"]


def district_options(boroughs):
    rows = DISTRICTS[DISTRICTS["borough"].isin(boroughs or BOROUGHS)]
    return [{"label": f"{lab} ({b})", "value": int(cd)} for cd, lab, b in zip(rows["cd"], rows["label"], rows["borough"])]


def control(label, component, width="md"):
    return html.Div([html.Label(label, htmlFor=component.id, className="control-label"), component],
                    className=f"control control-{width}")


# ---------------------------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------------------------
controls = html.Section(className="panel controls", children=[
    html.Div(className="search-row", children=[
        html.Label("Search the data", htmlFor="search", className="visually-hidden"),
        dcc.Input(id="search", type="text", debounce=False, className="search-input",
                  placeholder="Search, e.g. “Brooklyn 2022 new buildings” or “BX 01 family units injuries”"),
        html.Button("Search", id="search-button", className="btn btn-secondary", n_clicks=0),
    ]),
    html.Div(className="examples", children=[html.Span("Try: ", className="muted")] + [
        html.Button(e, id={"type": "example", "index": i}, className="chip", n_clicks=0)
        for i, e in enumerate(SEARCH_EXAMPLES)]),
    html.Div(id="search-feedback", className="search-feedback", role="status"),
    html.Div(className="control-row", children=[
        control("Borough", dcc.Dropdown(id="boroughs", options=BOROUGHS, value=BOROUGHS, multi=True,
                                        placeholder="All boroughs"), "lg"),
        control("Year", dcc.Dropdown(id="years", options=YEARS, value=YEARS, multi=True,
                                     placeholder="All years"), "md"),
        control("Community district", dcc.Dropdown(id="districts", options=district_options(BOROUGHS), value=[],
                                                   multi=True, placeholder="All districts"), "lg"),
    ]),
    html.Div(className="control-row", children=[
        control("Housing measure", dcc.Dropdown(id="housing", clearable=False, value=DEFAULTS["housing"],
                options=[{"label": v[0], "value": k} for k, v in HOUSING_MEASURES.items()]), "lg"),
        control("Crash measure", dcc.Dropdown(id="crash", clearable=False, value=DEFAULTS["crash"],
                options=[{"label": v[0], "value": k} for k, v in CRASH_MEASURES.items()]), "lg"),
        control("Time of day (crashes)", dcc.Dropdown(id="time", clearable=False, value=DEFAULTS["time"],
                options=[{"label": v[0], "value": k} for k, v in TIME_BANDS.items()]), "md"),
    ]),
    html.Div(className="generate-row", children=[
        html.Button("Generate Report", id="generate", className="btn btn-primary", n_clicks=0),
        html.Button("Reset filters", id="reset", className="btn btn-link", n_clicks=0),
        html.Span(id="pending", className="pending", role="status"),
    ]),
])

explore_tab = html.Div(children=[
    controls,
    dcc.Loading(type="dot", color="#15191c", children=html.Div(id="report", className="report", children=[
        html.Div(id="kpis", className="kpis"),
        html.Div(id="summary", className="panel summary"),
        html.Div(className="grid-map", children=[
            html.Div(className="panel chart", children=dcc.Graph(id="map", config=MAP_CONFIG)),
            html.Div(className="panel chart", children=dcc.Graph(id="ranked", config=GRAPH_CONFIG)),
        ]),
        html.Div(className="grid-2", children=[
            html.Div(className="panel chart", children=dcc.Graph(id="scatter", config=GRAPH_CONFIG)),
            html.Div(className="panel chart", children=dcc.Graph(id="trend", config=GRAPH_CONFIG)),
        ]),
        html.Div(className="panel chart", children=dcc.Graph(id="heatmap", config=GRAPH_CONFIG)),
        html.Details(className="panel table-view", children=[
            html.Summary("Table view of the selected districts"),
            html.Div(id="table")]),
    ])),
])


def story_block(title, *paragraphs):
    return html.Section(className="panel story-block", children=[html.H2(title)] + list(paragraphs))


story_tab = html.Div(className="story", children=[
    story_block("Does new affordable housing arrive where streets are most dangerous?",
                html.P("New York completed 48,026 affordable units in New Construction projects between 2022 and "
                       "2025 (buildings whose completion was recorded by HPD). In the same four years, the city "
                       "recorded 9,458 serious crashes that could be placed in a community district. We asked whether "
                       "the districts receiving the most new affordable housing are also the ones with the most "
                       "serious crashes, because new residents, many of them without a car, walk, cycle and take "
                       "the bus on those streets.")),
    story_block("Two city datasets, joined by place and year",
                html.Ul([
                    html.Li(["HPD ", html.Em("Affordable Housing Production by Building"),
                             ": one row per building, with units by income band, bedroom count and tenure."]),
                    html.Li(["DOT ", html.Em("Serious Injury Response Tracking (SIRTA)"),
                             ": one row per crash with a serious injury or fatality, with time and location."]),
                    html.Li("Both are aggregated to the 59 community districts and the years 2022-2025, giving 236 "
                            "district-years. Crashes are placed in a district from their coordinates using the "
                            "official district boundaries."),
                ])),
    story_block("Housing and crashes overlap only weakly",
                html.Ul([
                    html.Li("Across the 59 districts, the rank correlation between new affordable units and serious "
                            "crashes is 0.25: districts with more housing tend to have slightly more crashes, but the "
                            "evidence is weak (permutation p ≈ 0.06) and both largely reflect district size."),
                    html.Li("The boroughs do not line up. The Bronx received 35.8% of the affordable units but 19.6% "
                            "of serious crashes; Manhattan received 10.8% of the units but 20.2% of the crashes; "
                            "Staten Island 0.5% of the units and 4.7% of the crashes."),
                    html.Li("The two districts with the most serious injuries, QN 07 (324) and BK 18 (317), received "
                            "almost no new affordable housing: 53 and 61 units in four years."),
                    html.Li("Where housing grew fastest, the district's share of serious injuries did not rise: the "
                            "correlation between housing growth and the change in injury share is -0.26."),
                    html.Li("17 districts combine above-median new housing with above-median serious injuries, led by "
                            "BK 01, BX 01, BK 05, QN 12, BX 04 and MN 04. These are a shortlist for joint review."),
                    html.Li("Timing does not match either: completions peak in December, crashes in July. The "
                            "school-travel crash peak is citywide and unrelated to the share of family-sized units "
                            "(rho = 0.03)."),
                ])),
    story_block("What the data cannot tell us",
                html.Ul([
                    html.Li("This is association, not cause. Larger and denser districts have more of everything."),
                    html.Li("Crash counts are not adjusted for population, traffic or road length."),
                    html.Li("Fatal crashes after 2022 have no coordinates in the source, so fatalities cannot be "
                            "mapped by district and are left out of the site."),
                    html.Li("The share of crashes the source could place in a district differs by year (70-93% of "
                            "serious injuries), so year-on-year changes should be read with care."),
                    html.Li("Completion is not move-in: residents may arrive months later."),
                ])),
    story_block("Use the crash map, not the housing pipeline",
                html.P("Because new affordable housing does not follow the crash map, street-safety investment should "
                       "be targeted from crash history directly. Where the two do coincide (the 17 high/high "
                       "districts), coordinating HPD completions with DOT Vision Zero street redesigns is an easy win: "
                       "new residents move into streets that were made safer first.")),
])

TEAM_QUESTIONS = [
    ("7.4", "Yassin Amr Hegazy", "Do housing completions and serious crashes peak in the same month?",
     "No. Completions peak in December (13.1% of units), crashes in July (10.1%)."),
    ("7.4", "Yassin Amr Hegazy", "Does the difference in peak months vary by borough?",
     "Yes, mainly because housing timing differs; crash timing is similar everywhere."),
    ("7.5", "Mohammed Fady Rizk", "How does the borough distribution of affordable housing compare with serious crashes?",
     "Mismatched: the Bronx has 35.8% of units but 19.6% of crashes; Manhattan 10.8% vs 20.2%."),
    ("7.5", "Mohammed Fady Rizk", "Do districts with larger buildings (units per building) record more serious crashes?",
     "Weak positive link (r = 0.22) on only 60 complete district-years."),
    ("7.6", "Sam Shady Samih Soliman Bostawros", "Is the affordable share of units related to serious crash frequency?",
     "No (r = -0.06 across 218 district-years)."),
    ("7.6", "Sam Shady Samih Soliman Bostawros", "Do New Construction and Preservation areas differ in serious crashes?",
     "No. Medians 38 vs 40 crash events per district-year."),
    ("7.7", "Marawan Mohamed Elgendy", "Do districts with the largest housing growth see the largest change in serious injuries?",
     "No. Weak negative association (rho = -0.26, p = 0.051)."),
    ("7.7", "Marawan Mohamed Elgendy", "Which districts combine high housing volume with high serious injuries?",
     "17 of 59 districts, led by BK 01, BX 01, BK 05, QN 12, BX 04 and MN 04."),
    ("7.8", "Amro Taha Salih", "Are the deepest-affordability units placed in the most crash-burdened districts?",
     "No. All income tiers are spread alike; the two worst districts received almost none."),
    ("7.8", "Amro Taha Salih", "Do districts adding family-sized units have more crashes at school-travel times?",
     "No. The school-travel peak is citywide (rho = 0.03)."),
    ("7.9", "Fares Mustafa El-Sonbaty", "Is rental housing distributed differently from homeownership, and do rental-heavy districts have more repeat-location crashes?",
     "Yes, somewhat (rho = 0.28, p = 0.03). BK 03 holds 19.36% of ownership units; BX 01 holds 5.91% of rental units."),
    ("7.9", "Fares Mustafa El-Sonbaty", "Do districts with a wider income mix have crashes spread more evenly across the day?",
     "No clear link (rho = 0.21, p = 0.12, not significant); crashes are spread evenly almost everywhere."),
]

team_tab = html.Div(className="panel", children=[
    html.H2("Team research questions"),
    html.P("Each team member answered two questions in the notebook (sections 7.4 to 7.9). The website lets you "
           "explore the data behind all of them.", className="muted"),
    html.Div(className="table-scroll", children=html.Table(className="data-table", children=[
        html.Thead(html.Tr([html.Th("Section"), html.Th("Member"), html.Th("Question"), html.Th("Answer in short")])),
        html.Tbody([html.Tr([html.Td(s), html.Td(m), html.Td(q), html.Td(a)]) for s, m, q, a in TEAM_QUESTIONS]),
    ])),
])

about_tab = html.Div(className="panel", children=[
    html.H2("About the data"),
    html.Ul([
        html.Li([html.A("Affordable Housing Production by Building (HPD)", target="_blank", rel="noopener",
                        href="https://data.cityofnewyork.us/Housing-Development/Affordable-Housing-Production-by-Building/hg8x-zxpr"),
                 ": New Construction projects with a recorded building completion date in 2022-2025."]),
        html.Li([html.A("Serious Injury Response Tracking Application, SIRTA (DOT)", target="_blank", rel="noopener",
                        href="https://data.cityofnewyork.us/Transportation/Serious-Injury-Response-Tracking-Application-SIRTA-/xeqp-qz8h"),
                 ": crashes with a serious injury or fatality, 2022-2025."]),
        html.Li([html.A("Community District boundaries (DCP)", target="_blank", rel="noopener",
                        href="https://data.cityofnewyork.us/City-Government/Community-Districts/5crt-au7u"),
                 ": used to place each crash in one of the 59 community districts."]),
    ]),
    html.H3("How the numbers are made"),
    html.Ul([
        html.Li("All cleaning and integration happen in the project notebook. The website reads the notebook's exported "
                "district-by-year table and a district-by-year-by-hour crash table, so every number matches the notebook."),
        html.Li("“Serious crashes” counts SIRTA events; “serious injuries” counts injured people. "
                "“Repeat-location crashes” are events where the source found similar serious harm at the "
                "same place in the previous three years."),
        html.Li("Housing measures count units (or buildings) in projects completed in the selected years. Income bands "
                "follow HPD's Area Median Income (AMI) categories."),
        html.Li("The correlation shown is Spearman's rank correlation across districts, with a permutation p-value. It "
                "measures co-occurrence, not cause."),
        html.Li("Fatalities are not offered: fatal records after 2022 have no coordinates, so they cannot be placed in "
                "a district (203 in 2022, then 9, 4 and 5)."),
    ]),
])

app.layout = html.Div(className="page", children=[
    dcc.Store(id="report-store"),
    html.Header(className="masthead", children=[
        html.P("NYC Open Data, 2022-2025, 59 community districts", className="source-line"),
        html.H1("Affordable housing and street safety in New York City"),
        html.P("Do neighbourhoods with a surge in new affordable housing also have more serious traffic crashes? "
               "Pick a place, a period and a measure, then press Generate Report.", className="lede"),
        html.P(className="key", children=[
            html.Span([html.Span(className="swatch swatch-crash"), "Serious crashes"]),
            html.Span([html.Span(className="swatch swatch-housing"), "New affordable housing"]),
        ]),
    ]),
    dcc.Tabs(id="tabs", value="explore", className="tabs", children=[
        dcc.Tab(label="Explore the data", value="explore", children=explore_tab),
        dcc.Tab(label="Data story", value="story", children=story_tab),
        dcc.Tab(label="Team questions", value="team", children=team_tab),
        dcc.Tab(label="About the data", value="about", children=about_tab),
    ]),
    html.Footer("Milestone 1 project: data engineering and visualisation with NYC Open Data. "
                "Figures show association, not causation.", className="footer"),
])


# ---------------------------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------------------------
FILTER_IDS = ["boroughs", "years", "districts", "housing", "crash", "time"]
FILTER_KEYS = ["boroughs", "years", "districts", "housing", "crash", "time"]


@callback(Output("districts", "options"), Output("districts", "value", allow_duplicate=True),
          Input("boroughs", "value"), State("districts", "value"), prevent_initial_call=True)
def prune_districts(boroughs, selected):
    """District choices follow the borough filter; districts outside it are dropped."""
    allowed = {o["value"] for o in district_options(boroughs)}
    kept = [d for d in (selected or []) if d in allowed]
    return district_options(boroughs), (kept if kept != (selected or []) else no_update)


@callback(
    [Output(i, "value", allow_duplicate=True) for i in FILTER_IDS]
    + [Output("search", "value"), Output("search-feedback", "children"), Output("report-store", "data")],
    Input("generate", "n_clicks"), Input("search", "n_submit"), Input("search-button", "n_clicks"),
    Input({"type": "example", "index": ALL}, "n_clicks"), Input("reset", "n_clicks"),
    State("search", "value"), [State(i, "value") for i in FILTER_IDS],
    prevent_initial_call="initial_duplicate",
)
def apply_controls(_gen, _submit, _search_btn, _examples, _reset, text, *values):
    """One entry point for every way of asking for a report: Generate, the search box, an example
    chip, or Reset. The search sets the dropdowns so the user can see and adjust what it understood."""
    trigger = ctx.triggered_id
    feedback = no_update
    if isinstance(trigger, dict) and trigger.get("type") == "example":
        text = SEARCH_EXAMPLES[trigger["index"]]
        trigger = "search"
    if trigger in ("search", "search-button"):
        if not (text or "").strip():
            return [no_update] * 6 + [no_update, html.Span("Type something to search for.", className="warn"), no_update]
        filters, applied, ignored = parse_search(text)
        if applied:
            parts = [html.Span("Showing: ", className="muted")] + [
                html.Span([html.B(k + ": "), v], className="tag") for k, v in applied.items()]
        else:
            parts = [html.Span("Nothing in that search matched a borough, year, district or measure, so the "
                               "default report is shown.", className="warn")]
        if ignored:
            parts.append(html.Span(f" Not recognised: {', '.join(ignored)}", className="muted"))
        feedback = html.Span(parts)
        cleared = ""
    elif trigger == "reset":
        filters, cleared, feedback = dict(DEFAULTS), no_update, ""
    else:   # Generate Report (or the first page load)
        filters, cleared = dict(zip(FILTER_KEYS, values)), no_update
    filters = normalise_filters(filters)
    outputs = [filters[k] for k in FILTER_KEYS]
    return outputs + [cleared, feedback, filters]


@callback(Output("pending", "children"), [Input(i, "value") for i in FILTER_IDS], Input("report-store", "data"))
def show_pending(*args):
    """Tell the user when the dropdowns no longer match the report on screen."""
    *values, report = args
    if not report:
        return ""
    current = normalise_filters(dict(zip(FILTER_KEYS, values)))
    return "Filters changed. Press Generate Report to update the charts." if current != report else ""


def kpi(label, value, note="", swatch=None):
    label = [html.Span(className=f"swatch swatch-{swatch}"), label] if swatch else label
    return html.Div(className="kpi", children=[html.P(label, className="kpi-label"),
                                              html.P(value, className="kpi-value"),
                                              html.P(note, className="kpi-note")])


def scope_text(f):
    if f["districts"]:
        place = ", ".join(LABELS[d] for d in f["districts"])
    elif len(f["boroughs"]) == len(BOROUGHS):
        place = "all five boroughs"
    else:
        place = ", ".join(f["boroughs"])
    years = f"{f['years'][0]}" if len(f["years"]) == 1 else (
        f"{f['years'][0]}-{f['years'][-1]}" if f["years"] == list(range(f["years"][0], f["years"][-1] + 1))
        else ", ".join(map(str, f["years"])))
    time = "" if f["time"] == "all" else f", {TIME_BANDS[f['time']][0].lower()}"
    return place, years, time


@callback(Output("kpis", "children"), Output("summary", "children"), Output("map", "figure"),
          Output("scatter", "figure"), Output("ranked", "figure"), Output("trend", "figure"),
          Output("heatmap", "figure"), Output("table", "children"), Input("report-store", "data"))
def build_report(filters):
    f = normalise_filters(filters)
    table = district_year_table(f)
    totals = district_totals(table)
    stats = spearman(totals["housing"], totals["crash"]) if len(totals) else (None, None, 0)
    h, c = HOUSING_SHORT[f["housing"]], CRASH_SHORT[f["crash"]]
    place, years, time = scope_text(f)

    with_housing = int((totals["housing"] > 0).sum())
    rho, p, n = stats
    kpis = [
        kpi(f"New {h}", f"{int(totals['housing'].sum()):,}", f"{place}, {years}", swatch="housing"),
        kpi(c.capitalize(), f"{int(totals['crash'].sum()):,}", f"{years}{time}", swatch="crash"),
        kpi("Districts with new housing", f"{with_housing} of {len(totals)}", "had at least one in the period"),
        kpi("Housing vs crashes (rank correlation)", "n/a" if rho is None else f"{rho:+.2f}",
            "needs 5+ districts with variation" if rho is None else f"p = {p:.2f}, {n} districts"),
    ]

    if totals.empty:
        summary = html.P("No districts match these filters. Widen the borough or year selection.")
    else:
        top_crash = totals.sort_values(["crash", "cd"], ascending=[False, True]).iloc[0]
        top_house = totals.sort_values(["housing", "cd"], ascending=[False, True]).iloc[0]
        sentences = [
            f"In {place} ({years}{time}), {int(totals['crash'].sum()):,} {c} were recorded and "
            f"{int(totals['housing'].sum()):,} new {h} were completed.",
            f"The most {c}: {top_crash['label']} ({int(top_crash['crash']):,}). "
            f"The most new {h}: {top_house['label']} ({int(top_house['housing']):,})."
            if len(totals) > 1 else "",
        ]
        if rho is not None:
            sentences.append(f"Across these {n} districts there is {strength(rho)} rank relationship between the two "
                             f"(rho = {rho:.2f}, p = {p:.2f}). That is co-occurrence, not cause: bigger districts tend "
                             f"to have more of both.")
        summary = [html.H2("Report summary"), html.P(" ".join(s for s in sentences if s))]

    shown = totals.sort_values(["crash", "cd"], ascending=[False, True])
    data_table = html.Div(className="table-scroll", children=html.Table(className="data-table", children=[
        html.Thead(html.Tr([html.Th("District"), html.Th("Borough"), html.Th(f"New {h}", className="num"),
                            html.Th(c.capitalize(), className="num")])),
        html.Tbody([html.Tr([html.Td(r.label), html.Td(r.borough), html.Td(f"{r.housing:,}", className="num"),
                             html.Td(f"{r.crash:,}", className="num")]) for r in shown.itertuples()]),
    ]))
    return (kpis, summary, map_figure(totals, f), scatter_figure(totals, f, stats), ranked_bar_figure(totals, f),
            trend_figure(table, f), heatmap_figure(hourly_profile(f), f), data_table)


if __name__ == "__main__":
    app.run(debug=os.environ.get("DASH_DEBUG") == "1", host="127.0.0.1", port=int(os.environ.get("PORT", 8050)))
