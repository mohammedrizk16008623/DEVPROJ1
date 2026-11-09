"""Interactive NYC housing and crash dashboard. Launch: python app.py"""
import re
import os
from dash import Dash, dcc, html, Input, Output, State, no_update
import plotly.express as px
from analytics import BOROUGHS, YEARS, SPECS, chart, filtered, load_data, metrics

DATA = load_data()
app = Dash(__name__, title="NYC Urban Insights", suppress_callback_exceptions=False)
server = app.server

CATEGORY_LABELS = {"All": "All housing activity", "New Construction": "New Construction", "Preservation": "Preservation"}
CRASH_METRICS = {"crash_events":"Reported serious crashes", "severe_injuries":"Severe injuries", "fatalities":"Fatalities"}

def parse_search(query):
    """Simple rule-based search: borough/year/district/category; no invented NLP."""
    query = (query or "").strip().lower()
    if not query: return {}, None
    found = {}
    bs = [b for b in BOROUGHS if b.lower() in query]
    if bs: found["boroughs"] = bs
    year_matches = [int(v) for v in re.findall(r"\b20(?:22|23|24|25)\b",query)]
    if year_matches: found["years"] = sorted(set(year_matches))
    district = re.search(r"\b(?:district|cd)\s*#?\s*(\d{3})\b",query)
    if district: found["district"] = int(district.group(1))
    if "preservation" in query: found["housing_type"] = "Preservation"
    elif "new construction" in query or "new buildings" in query: found["housing_type"] = "New Construction"
    if "fatalit" in query or "fatal" in query:found["crash_metric"]="fatalities"
    elif "severe injuries" in query or "severe injury" in query:found["crash_metric"]="severe_injuries"
    if not found:return {}, "Search not recognized. Try 'Brooklyn 2024', 'Queens 2023 preservation' or 'district 301'."
    if district and found["district"] not in set(DATA["integrated"].cd):
        return {}, "That community district ID is not in the dataset."
    return found, None


def metric_tile(label,value):
    return html.Div([html.Div(label,className="metric-label"),html.Div(f"{value:,}",className="metric-value")],className="metric-card")

def chart_card(spec):
    key,title,question,note=spec
    return html.Article([
        html.Div([html.Span("RESEARCH CHART",className="eyebrow"),html.Span(note,className="tag")],className="chart-meta"),
        html.H3(title),html.P(question,className="question"),
        dcc.Graph(id=f"graph-{key}",config={"displaylogo":False,"responsive":True},style={"height":"350px"})
    ],className="chart-card")

app.layout = html.Div([
    dcc.Store(id="report-state",data={"boroughs":BOROUGHS,"years":YEARS,"district":None,"housing_type":"All","crash_metric":"crash_events"}),
    html.Header([html.Div([html.Div("NYC / URBAN INSIGHTS",className="brand"),html.Div("Housing development × road safety",className="brand-sub")],className="topbar-inner")],className="topbar"),
    html.Main([
        html.Section([html.Div("DATA ENGINEERING & VISUALIZATION · 2022—2025",className="eyebrow"),
            html.H1("Where housing and street safety intersect."),
            html.P("Explore completed affordable housing and investigated serious crashes across New York City's community districts. All figures use the team's validated data exports—not live NYC counts.",className="intro")],className="hero"),
        html.Section([
            html.Div([html.H2("Explore the data"),html.P("Set filters or enter a supported search, then generate your report.")],className="filters-heading"),
            html.Div([
                html.Div([html.Label("Borough"),dcc.Dropdown(id="borough-filter",options=[{"label":b,"value":b} for b in BOROUGHS],value=BOROUGHS,multi=True,clearable=False)],className="input-group"),
                html.Div([html.Label("Year"),dcc.Dropdown(id="year-filter",options=[{"label":str(y),"value":y} for y in YEARS],value=YEARS,multi=True,clearable=False)],className="input-group"),
                html.Div([html.Label("Community district"),dcc.Dropdown(id="district-filter",options=[{"label":f"{int(r.cd)} · {r.borough}","value":int(r.cd)} for r in DATA["integrated"][["cd","borough"]].drop_duplicates().itertuples()],placeholder="All districts",clearable=True)],className="input-group"),
                html.Div([html.Label("Housing activity category"),dcc.Dropdown(id="housing-type-filter",options=[{"label":v,"value":k} for k,v in CATEGORY_LABELS.items()],value="All",clearable=False)],className="input-group"),
                html.Div([html.Label("Road safety outcome"),dcc.Dropdown(id="crash-metric-filter",options=[{"label":v,"value":k} for k,v in CRASH_METRICS.items()],value="crash_events",clearable=False)],className="input-group"),
            ],className="filter-grid"),
            html.Div([dcc.Input(id="search-input",placeholder="Try: Brooklyn 2024 · Queens preservation · district 301",debounce=True,type="text",className="search-input"),html.Button("Generate Report",id="generate-button",n_clicks=0,className="report-button")],className="search-row"),
            html.Div(id="filter-feedback",className="filter-feedback",role="status"),
            html.P("Housing activity category applies to the activity breakdown below; primary research charts retain their stated housing definitions. Road safety outcome controls the outcome overview, while fixed research questions retain their specified measures.",className="filter-footnote")
        ],className="filters-panel"),
        html.Section([html.Div(id="report-subtitle",className="report-subtitle"),html.Div(id="metric-row",className="metrics"),
            html.Div([html.Article([html.H3("Housing program activity"),html.P("Administrative project starts (New Construction / Preservation), distinct from completed-building analyses.",className="question"),dcc.Graph(id="activity-overview",config={"displaylogo":False},style={"height":"300px"})],className="overview-card"),
            html.Article([html.H3("Road safety outcomes"),html.P("Selected outcome, grouped by year for the active area.",className="question"),dcc.Graph(id="outcome-overview",config={"displaylogo":False},style={"height":"300px"})],className="overview-card")],className="overview-grid")],className="summary"),
        html.Section([html.Div("RESEARCH EXPLORER",className="eyebrow"),html.H2("Questions answered with data"),html.P("Interactive charts reflect borough, district and year filters. Individual chart definitions and inclusion rules are stated above each plot.",className="intro"),html.Div([chart_card(spec) for spec in SPECS],className="charts-grid")],className="research"),
        html.Section([html.H2("The story behind the numbers"),html.Div([
            html.Div([html.H3("The question"),html.P("How do patterns of affordable housing development and investigated serious road crashes compare across place and time?")]),
            html.Div([html.H3("The data & method"),html.P("HPD Affordable Housing Production by Building and NYC DOT SIRTA are cleaned independently and aggregated to NYC Community District × Year (2022–2025). The primary housing measure is completed New Construction. Project-start activity is retained separately.")]),
            html.Div([html.H3("What we can conclude"),html.P("These figures describe geographic and temporal patterns in eligible, assigned records. Explore the charts to form defensible observations; similar trends or associations do not establish cause and effect.")]),
            html.Div([html.H3("Limitations & impact"),html.P("Some eligible crash and housing records cannot be geographically assigned. Crash counts are not exposure-adjusted and SIRTA does not represent every collision. The results may help planners identify areas deserving closer investigation—not rank crash risk without population or travel-exposure data.")])
        ],className="story-grid")],className="story"),
        html.Footer([html.Span("GIU · Data Engineering & Visualization · Winter 2026"),html.Span("Source: NYC Open Data · HPD / NYC DOT · Methodology: accompanying Colab notebook")],className="footer")
    ],className="page")
])


OUTPUTS = [Output("metric-row","children"),Output("report-subtitle","children"),Output("filter-feedback","children"),Output("activity-overview","figure"),Output("outcome-overview","figure")]
OUTPUTS += [Output(f"graph-{s[0]}","figure") for s in SPECS]

@app.callback(OUTPUTS,Input("generate-button","n_clicks"),State("borough-filter","value"),State("year-filter","value"),State("district-filter","value"),State("housing-type-filter","value"),State("crash-metric-filter","value"),State("search-input","value"))
def generate_report(n_clicks,boroughs,years,district,housing_type,crash_metric,query):
    boroughs=boroughs or BOROUGHS
    years=years or YEARS
    overrides,error=parse_search(query)
    if error:
        message=error+" Existing dropdown settings are used."
    else:message="Report updated. All applicable charts use the active geographic and year filters."
    boroughs=overrides.get("boroughs",boroughs)
    years=overrides.get("years",years)
    district=overrides.get("district",district)
    housing_type=overrides.get("housing_type",housing_type)
    crash_metric=overrides.get("crash_metric",crash_metric)
    # If borough/district selections contradict, surface empty results rather than pretending a match.
    d=filtered(DATA,boroughs,years,district)
    m=metrics(d)
    cards=[metric_tile("Districts in selection",m["districts"]),metric_tile("Completed affordable units",m["housing"]),metric_tile("Eligible crash events",m["crashes"]),metric_tile(CRASH_METRICS[crash_metric],int(d["integrated"][crash_metric].sum()))]
    desc=f"{', '.join(boroughs)} · {', '.join(map(str,sorted(years)))} · {m['district_years']} district-year observations"
    # Supplementary category-specific overview; main completed-buildings charts do not change semantics.
    a=d["activity"]
    if housing_type != "All":a=a[a.construction_type==housing_type]
    g=a.groupby(["project_start_year","construction_type"],as_index=False).housing_source_records.sum()
    if g.empty:
        from analytics import empty_fig
        activity_fig=empty_fig()
    else:
        activity_fig=px.bar(g,x="project_start_year",y="housing_source_records",color="construction_type",barmode="group",color_discrete_sequence=["#2473aa","#e18a46"],labels={"project_start_year":"Project start year","housing_source_records":"Housing activity records","construction_type":"Construction type"})
    t=d["integrated"].groupby("year",as_index=False)[crash_metric].sum()
    outcome_fig=px.bar(t,x="year",y=crash_metric,labels={"year":"Year",crash_metric:CRASH_METRICS[crash_metric]},color_discrete_sequence=["#2473aa"])
    from analytics import style
    return (cards,desc,message,style(activity_fig),style(outcome_fig),*[chart(s[0],d) for s in SPECS])


if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",8050)),debug=False)
