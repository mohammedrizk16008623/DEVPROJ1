"""Chart calculations on frozen, audited, NYC community-district/year outputs.
All figures are descriptive; no causal or risk-rate interpretations are made.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
YEARS = [2022, 2023, 2024, 2025]
BOROUGHS = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"]
COLORS = ["#2473aa", "#e18a46", "#329782", "#9168b5"]

SPECS = [
    ("geography", "Geographical distribution", "How does the geographical distribution of completed affordable housing compare with reported serious crashes?", "Completion-based housing · crash events"),
    ("building_size", "Building scale and crashes", "Is the average number of affordable units per completed building associated with reported crash frequency?", "Eligible identified buildings only"),
    ("month_peaks", "Citywide monthly peaks", "Do housing completions and serious crashes peak in the same month?", "Monthly events · selected years"),
    ("borough_peaks", "Peak-month variation by borough", "Does the difference between housing-completion and crash peak months vary by borough?", "Two event series · selected years"),
    ("afford_share", "Affordable-unit share", "Does the affordable-unit proportion within completed housing relate to serious crash frequency?", "Valid affordable share observations"),
    ("construction_type", "Construction and preservation", "Do areas dominated by new construction and preservation activity differ in crash frequency?", "Project-start basis, not completions"),
    ("growth", "Changes between two periods", "Do districts with more growth in counted new units also show a greater change in severe injuries?", "Comparison of 2022–23 and 2024–25; full range only"),
    ("volume_severity", "Housing volume and serious injuries", "Which districts combine more completed housing units with higher severe-injury totals?", "Descriptive district totals"),
    ("tenure_recurrence", "Tenure and recurring crash reports", "Does rental- versus homeownership-oriented housing differ across districts with recorded recurring crash problems?", "Recurrence among records with known lookback"),
    ("income_hour", "Income composition and crash hours", "Is housing income-category diversity associated with the spread of recorded crashes across the day?", "Diversity and hourly dispersion indicators"),
    ("presence", "Housing-completion presence", "Do district-years with recorded housing completions have different crash-count distributions from those without?", "Presence means eligible completions in main table"),
    ("consistency", "Consistency across years", "How consistently are housing completions and serious crashes recorded across community districts?", "Counts of active years · selected interval"),
]


def load_data(directory=ROOT / "data"):
    directory = Path(directory)
    d = {k: pd.read_csv(directory / filename, low_memory=False) for k, filename in {
        "integrated": "integrated_district_year.csv",
        "activity": "housing_program_activity_district_year.csv",
        "hourly": "crashes_district_year_hour.csv",
        "housing": "housing_new_construction_2022_2025.csv",
        "crashes": "crashes_2022_2025_assigned.csv",
    }.items()}
    main = d["integrated"]
    assert len(main) == 236 and main["cd"].nunique() == 59
    assert not main.duplicated(["cd", "year"]).any()
    assert set(main.year.unique()) == set(YEARS)
    for name in ("housing", "crashes"):
        datecol = "Building Completion Date" if name == "housing" else "Crash Date"
        d[name]["event_date"] = pd.to_datetime(d[name][datecol], errors="coerce")
    return d


def filtered(data, boroughs=None, years=None, district=None):
    boroughs = list(boroughs or BOROUGHS)
    years = [int(y) for y in (years or YEARS)]
    result = {}
    for key, original in data.items():
        d = original.copy()
        if "borough" in d.columns:
            d = d[d["borough"].isin(boroughs)]
        if "year" in d.columns:
            d = d[d["year"].isin(years)]
        elif "project_start_year" in d.columns:
            d = d[d["project_start_year"].isin(years)]
        else:
            d = d[d["event_date"].dt.year.isin(years)]
        if district is not None and "cd" in d.columns:
            d = d[d["cd"] == int(district)]
        result[key] = d
    return result


def empty_fig(message="No eligible records for these filters"):
    f = go.Figure()
    f.add_annotation(text=message, x=.5, y=.5, showarrow=False, xref="paper", yref="paper", font_size=15)
    f.update_layout(xaxis_visible=False, yaxis_visible=False)
    return style(f)


def style(f):
    f.update_layout(template="plotly_white", margin=dict(l=35, r=20, t=36, b=40),
                    font=dict(family="Inter, Arial, sans-serif", size=12),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend_title_text="", hovermode="closest")
    return f


def chart(key, data):
    main, activity, hourly, housing, crashes = [data[k] for k in ["integrated", "activity", "hourly", "housing", "crashes"]]
    if main.empty:
        return empty_fig()
    try:
        if key == "geography":
            g = main.groupby("borough", as_index=False).agg(units=("housing_affordable_units", "sum"), crashes=("crash_events", "sum"))
            if g.units.sum() == 0 or g.crashes.sum() == 0: return empty_fig()
            g["Housing share (%)"] = 100*g.units/g.units.sum()
            g["Crash share (%)"] = 100*g.crashes/g.crashes.sum()
            m=g.melt("borough", value_vars=["Housing share (%)", "Crash share (%)"],var_name="Measure",value_name="Percent")
            return style(px.bar(m,x="borough",y="Percent",color="Measure",barmode="group",category_orders={"borough":BOROUGHS},color_discrete_sequence=COLORS,labels={"borough":"Borough","Percent":"Share of selected area total (%)"}))

        if key == "building_size":
            x=main[(main.housing_identified_buildings>0)&(main.housing_missing_building_id_records==0)&(main.housing_affordable_units_known_records==main.housing_source_records)].copy()
            if x.empty:return empty_fig("No complete building-ID observations")
            x["Affordable units per identified building"]=x.housing_affordable_units/x.housing_identified_buildings
            return style(px.scatter(x,x="Affordable units per identified building",y="crash_events",color="borough",hover_data=["cd","year"],labels={"crash_events":"Reported crash events","borough":"Borough"}))

        if key in ("month_peaks", "borough_peaks"):
            if housing.empty or crashes.empty:return empty_fig()
            h=housing.assign(month=housing.event_date.dt.month).dropna(subset=["month"])
            c=crashes.assign(month=crashes.event_date.dt.month).dropna(subset=["month"])
            if key == "month_peaks":
                hm=h.groupby("month").size().reindex(range(1,13),fill_value=0)
                cm=c.groupby("month").size().reindex(range(1,13),fill_value=0)
                if hm.sum()==0 or cm.sum()==0:return empty_fig()
                f=go.Figure()
                f.add_trace(go.Scatter(x=list(range(1,13)),y=hm/hm.sum()*100,mode="lines+markers",name="Completed building records"))
                f.add_trace(go.Scatter(x=list(range(1,13)),y=cm/cm.sum()*100,mode="lines+markers",name="Crash events"))
                f.update_layout(xaxis=dict(title="Calendar month",tickmode="array",tickvals=list(range(1,13)),ticktext=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]),yaxis_title="Share of selected records (%)")
                return style(f)
            bs=[]
            for b in sorted(set(h.borough)&set(c.borough)):
                a=h[h.borough==b].groupby("month").size(); z=c[c.borough==b].groupby("month").size()
                if not len(a) or not len(z):continue
                bs.append({"borough":b,"Housing peak month":int(a.idxmax()),"Crash peak month":int(z.idxmax())})
            if not bs:return empty_fig()
            t=pd.DataFrame(bs).melt("borough",var_name="Type",value_name="Peak month")
            return style(px.bar(t,x="borough",y="Peak month",color="Type",barmode="group",color_discrete_sequence=COLORS,category_orders={"borough":BOROUGHS}))

        if key == "afford_share":
            x=main[(main.housing_source_records>0)&main.housing_affordable_share_of_reported_total.notna()].copy()
            x["Affordable unit share (%)"]=x.housing_affordable_share_of_reported_total*100
            x=x[x["Affordable unit share (%)"].between(0,100)]
            if x.empty:return empty_fig()
            return style(px.scatter(x,x="Affordable unit share (%)",y="crash_events",color="borough",hover_data=["cd","year"],labels={"crash_events":"Reported crash events"}))

        if key == "construction_type":
            a=activity[activity.construction_type.isin(["New Construction","Preservation"])].groupby(["cd","project_start_year","construction_type"],as_index=False).housing_source_records.sum()
            if a.empty:return empty_fig()
            p=a.pivot_table(index=["cd","project_start_year"],columns="construction_type",values="housing_source_records",aggfunc="sum",fill_value=0).reset_index()
            for col in ["New Construction","Preservation"]:
                if col not in p:p[col]=0
            p["Dominant activity"]=np.where(p["New Construction"]>p["Preservation"],"New Construction",np.where(p["Preservation"]>p["New Construction"],"Preservation","Tie"))
            p=p[p["Dominant activity"]!="Tie"]
            joined=p.merge(main[["cd","year","crash_events"]],left_on=["cd","project_start_year"],right_on=["cd","year"],validate="one_to_one")
            if joined.empty:return empty_fig()
            return style(px.box(joined,x="Dominant activity",y="crash_events",points="all",color="Dominant activity",labels={"crash_events":"Reported crash events"},color_discrete_sequence=COLORS))

        if key == "growth":
            if set(main.year.unique()) != set(YEARS):return empty_fig("This comparison requires all four years (2022–2025).")
            x=main.assign(period=np.where(main.year<=2023,"2022–23","2024–25")).groupby(["cd","borough","period"],as_index=False).agg(units=("housing_affordable_units","sum"),injuries=("severe_injuries","sum"))
            p=x.pivot_table(index=["cd","borough"],columns="period",values=["units","injuries"],aggfunc="sum",fill_value=0)
            if ("units","2022–23") not in p or ("units","2024–25") not in p:return empty_fig()
            p=pd.DataFrame({"Change in completed units":p[("units","2024–25")]-p[("units","2022–23")],"Change in severe injuries":p[("injuries","2024–25")]-p[("injuries","2022–23")]}).reset_index()
            return style(px.scatter(p,x="Change in completed units",y="Change in severe injuries",color="borough",hover_data=["cd"]))

        if key == "volume_severity":
            x=main.groupby(["cd","borough"],as_index=False).agg(units=("housing_affordable_units","sum"),severe=("severe_injuries","sum"))
            return style(px.scatter(x,x="units",y="severe",color="borough",hover_data=["cd"],labels={"units":"Completed counted units","severe":"Severe injuries"}))

        if key == "tenure_recurrence":
            x=main.groupby(["cd","borough"],as_index=False).agg(rental=("housing_rental_units","sum"),owned=("housing_homeownership_units","sum"),known=("lookback_known_events","sum"),recurring=("positive_lookback_events","sum"))
            x=x[(x.rental+x.owned>0)&(x.known>0)].copy()
            if x.empty:return empty_fig()
            x["Rental share (%)"]=100*x.rental/(x.rental+x.owned)
            x["Recurring lookback share (%)"]=100*x.recurring/x.known
            return style(px.scatter(x,x="Rental share (%)",y="Recurring lookback share (%)",color="borough",hover_data=["cd"],labels={"borough":"Borough"}))

        if key == "income_hour":
            # District-year Simpson diversity for recorded income-category unit counts.
            income=["housing_extremely_low_income_units","housing_very_low_income_units","housing_low_income_units","housing_moderate_income_units","housing_middle_income_units","housing_other_income_units"]
            x=main[["cd","year","borough"]+income].copy()
            a=x[income].clip(lower=0).fillna(0).to_numpy(dtype=float)
            total=a.sum(axis=1)
            x["Income-category diversity"] = np.where(total>0,1-(a*a).sum(axis=1)/np.maximum(total,1)**2,np.nan)
            # Hourly entropy normalized 0-1 for records with known crash hour.
            pivot=hourly.pivot_table(index=["cd","year"],columns="hour",values="crash_events",aggfunc="sum",fill_value=0).reindex(columns=range(24),fill_value=0)
            counts=pivot.to_numpy(dtype=float)
            sums=counts.sum(axis=1)
            prob=np.divide(counts,sums[:,None],out=np.zeros_like(counts),where=sums[:,None]>0)
            entropy=-(np.where(prob>0,prob*np.log(np.maximum(prob,1e-12)),0)).sum(axis=1)/np.log(24)
            entropy[sums==0]=np.nan
            t=pivot.reset_index()[["cd","year"]];t["Crash-hour spread"] = entropy
            x=x.merge(t,on=["cd","year"],how="left",validate="one_to_one").dropna(subset=["Income-category diversity","Crash-hour spread"])
            if x.empty:return empty_fig()
            return style(px.scatter(x,x="Income-category diversity",y="Crash-hour spread",color="borough",hover_data=["cd","year"]))

        if key == "presence":
            x=main.copy();x["Housing completion status"]=np.where(x.housing_source_records>0,"With completions","Without completions")
            return style(px.box(x,x="Housing completion status",y="crash_events",points="all",color="Housing completion status",color_discrete_sequence=COLORS,labels={"crash_events":"Reported crash events"}))

        if key == "consistency":
            x=main.groupby("cd").agg(housing_years=("housing_source_records",lambda s:int((s>0).sum())),crash_years=("crash_events",lambda s:int((s>0).sum())))
            n=main.year.nunique()
            freqs=pd.DataFrame({"Years with activity":list(range(n+1)),"Housing completions":[(x.housing_years==i).sum() for i in range(n+1)],"Crash events":[(x.crash_years==i).sum() for i in range(n+1)]})
            m=freqs.melt("Years with activity",var_name="Domain",value_name="Community districts")
            return style(px.bar(m,x="Years with activity",y="Community districts",color="Domain",barmode="group",color_discrete_sequence=COLORS))
    except (KeyError, ValueError, ZeroDivisionError, TypeError) as exc:
        return empty_fig(f"This chart cannot be calculated for the selected filters: {type(exc).__name__}")
    return empty_fig("Chart not configured")


def metrics(data):
    m=data["integrated"]
    return dict(districts=int(m.cd.nunique()),district_years=int(len(m)),housing=int(m.housing_affordable_units.sum()),crashes=int(m.crash_events.sum()),severe=int(m.severe_injuries.sum()))
