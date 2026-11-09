"""Data access, filtering, search parsing and statistics for the website.

Kept separate from app.py (layout + callbacks) so the logic can be tested without a browser.
All inputs are the notebook's exported tables in data/; nothing is re-cleaned here.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
BOROUGHS = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]
YEARS = [2022, 2023, 2024, 2025]

# Housing categories (HPD Affordable Housing Production by Building, New Construction completions).
HOUSING_MEASURES = {
    "affordable": ("Affordable units", ["housing_affordable_units"]),
    "total": ("All units, affordable + market-rate", ["housing_total_units"]),
    "buildings": ("New buildings completed", ["housing_source_records"]),
    "deep": ("Extremely + very low income units (0-50% AMI)",
             ["housing_extremely_low_income_units", "housing_very_low_income_units"]),
    "low": ("Low income units (51-80% AMI)", ["housing_low_income_units"]),
    "moderate": ("Moderate + middle income units (81-165% AMI)",
                 ["housing_moderate_income_units", "housing_middle_income_units"]),
    "family": ("Family-sized units (2+ bedrooms)",
               ["housing_two_br_units", "housing_three_br_units", "housing_four_br_units",
                "housing_five_br_units", "housing_six_plus_br_units"]),
    "rental": ("Rental units", ["housing_rental_units"]),
    "ownership": ("Homeownership units", ["housing_homeownership_units"]),
}
# Transportation categories (SIRTA serious crashes). Fatalities are deliberately not offered:
# fatal records after 2022 have no coordinates, so they cannot be placed in a district
# (notebook section 7.7), and a district-level fatality chart would be misleading.
CRASH_MEASURES = {
    "crash_events": ("Serious crashes", "crash_events"),
    "severe_injuries": ("Serious injuries", "severe_injuries"),
    "non_severe_injuries": ("Other injuries in serious crashes", "non_severe_injuries"),
    "positive_lookback_events": ("Repeat-location crashes (similar serious harm there in the prior 3 years)",
                                 "positive_lookback_events"),
}
TIME_BANDS = {
    "all": ("All hours", list(range(24))),
    "am": ("Morning peak, 06:00-09:59", list(range(6, 10))),
    "midday": ("Midday, 10:00-15:59", list(range(10, 16))),
    "pm": ("Evening peak, 16:00-19:59", list(range(16, 20))),
    "night": ("Night, 20:00-05:59", list(range(20, 24)) + list(range(0, 6))),
}
DEFAULTS = {"boroughs": BOROUGHS, "years": YEARS, "districts": [], "housing": "affordable",
            "crash": "crash_events", "time": "all"}


def load_data(folder=DATA):
    integrated = pd.read_csv(folder / "integrated_district_year.csv")
    hourly = pd.read_csv(folder / "crashes_district_year_hour.csv")
    districts = pd.read_csv(folder / "districts.csv")
    with open(folder / "community_districts.geojson", encoding="utf-8") as f:
        geojson = json.load(f)
    return integrated, hourly, districts, geojson


INTEGRATED, HOURLY, DISTRICTS, GEOJSON = load_data()
LABELS = dict(zip(DISTRICTS["cd"], DISTRICTS["label"]))


# ----------------------------------------------------------------------------------------------
# Filtering
# ----------------------------------------------------------------------------------------------
def normalise_filters(filters):
    """Fill missing keys with defaults and treat an empty borough/year choice as 'all'."""
    f = {**DEFAULTS, **(filters or {})}
    f["boroughs"] = [b for b in BOROUGHS if b in (f["boroughs"] or BOROUGHS)]
    f["years"] = sorted(int(y) for y in (f["years"] or YEARS))
    f["districts"] = sorted(int(d) for d in (f["districts"] or []))
    return f


def district_year_table(filters):
    """One row per selected district/year with the chosen housing and crash measures.

    The crash measure comes from the hourly table when a time band is chosen; that table
    reconciles exactly with the annual totals, so 'All hours' gives the same numbers either way.
    """
    f = normalise_filters(filters)
    keep = INTEGRATED["borough"].isin(f["boroughs"]) & INTEGRATED["year"].isin(f["years"])
    if f["districts"]:
        keep &= INTEGRATED["cd"].isin(f["districts"])
    table = INTEGRATED.loc[keep, ["cd", "borough", "year"]].copy()
    table["housing"] = INTEGRATED.loc[keep, HOUSING_MEASURES[f["housing"]][1]].sum(axis=1)

    crash_column = CRASH_MEASURES[f["crash"]][1]
    hours = TIME_BANDS[f["time"]][1]
    crashes = (HOURLY[HOURLY["hour"].isin(hours)].groupby(["cd", "year"])[crash_column].sum()
               .rename("crash").reset_index())
    table = table.merge(crashes, on=["cd", "year"], how="left")
    table["crash"] = table["crash"].fillna(0).astype(int)   # no hourly row = no recorded event
    table["label"] = table["cd"].map(LABELS)
    return table


def district_totals(table):
    """Sum the selected years for each district (district = one point on the map / scatter)."""
    return (table.groupby(["cd", "borough", "label"], as_index=False)[["housing", "crash"]].sum()
            .sort_values("cd").reset_index(drop=True))


def hourly_profile(filters):
    """Crash measure by hour and borough for the selected districts and years (all hours)."""
    f = normalise_filters(filters)
    keep = HOURLY["borough"].isin(f["boroughs"]) & HOURLY["year"].isin(f["years"])
    if f["districts"]:
        keep &= HOURLY["cd"].isin(f["districts"])
    column = CRASH_MEASURES[f["crash"]][1]
    return (HOURLY[keep].groupby(["borough", "hour"])[column].sum()
            .unstack("hour").reindex(columns=range(24), fill_value=0).fillna(0))


# ----------------------------------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------------------------------
def spearman(x, y, permutations=2000, seed=11):
    """Spearman rank correlation with a two-sided permutation p-value (no SciPy needed).
    Returns (rho, p, n); rho and p are None when the test is undefined."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    if n < 5 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None, None, n
    rx, ry = pd.Series(x).rank().to_numpy(), pd.Series(y).rank().to_numpy()
    rho = float(np.corrcoef(rx, ry)[0, 1])
    rng = np.random.default_rng(seed)
    perms = np.array([np.corrcoef(rx, rng.permutation(ry))[0, 1] for _ in range(permutations)])
    p = float((np.sum(np.abs(perms) >= abs(rho) - 1e-12) + 1) / (permutations + 1))
    return rho, p, n


def strength(rho):
    size = abs(rho)
    word = "no clear" if size < 0.1 else "a weak" if size < 0.3 else "a moderate" if size < 0.5 else "a strong"
    direction = "" if size < 0.1 else (" positive" if rho > 0 else " negative")
    return f"{word}{direction}"


# ----------------------------------------------------------------------------------------------
# Search: free text -> filters
# ----------------------------------------------------------------------------------------------
BOROUGH_WORDS = [("staten island", "Staten Island"), ("the bronx", "Bronx"), ("manhattan", "Manhattan"),
                 ("bronx", "Bronx"), ("brooklyn", "Brooklyn"), ("queens", "Queens"), ("staten", "Staten Island")]
DISTRICT_PREFIX = {"mn": 1, "bx": 2, "bk": 3, "qn": 4, "si": 5}
# Order matters: longer / more specific phrases are matched (and removed) first.
HOUSING_WORDS = [
    ("extremely low", "deep"), ("very low", "deep"), ("deep affordab", "deep"), ("0-50", "deep"),
    ("low income", "low"), ("low-income", "low"), ("moderate", "moderate"), ("middle income", "moderate"),
    ("family", "family"), ("bedroom", "family"), ("2br", "family"), ("homeownership", "ownership"),
    ("homeowner", "ownership"), ("ownership", "ownership"), ("rental", "rental"), ("rent", "rental"),
    ("market rate", "total"), ("market-rate", "total"), ("all units", "total"), ("total units", "total"),
    ("new buildings", "buildings"), ("buildings", "buildings"), ("building", "buildings"),
    ("affordable", "affordable"), ("units", "affordable"), ("housing", "affordable"),
]
CRASH_WORDS = [
    ("non-severe", "non_severe_injuries"), ("non severe", "non_severe_injuries"), ("minor", "non_severe_injuries"),
    ("other injuries", "non_severe_injuries"), ("repeat", "positive_lookback_events"),
    ("recurring", "positive_lookback_events"), ("hotspot", "positive_lookback_events"),
    ("serious injur", "severe_injuries"), ("injur", "severe_injuries"), ("crash", "crash_events"),
    ("collision", "crash_events"), ("accident", "crash_events"),
]
TIME_WORDS = [("morning", "am"), ("am peak", "am"), ("rush hour", "pm"), ("evening", "pm"), ("pm peak", "pm"),
              ("midday", "midday"), ("afternoon", "midday"), ("lunch", "midday"), ("night", "night"),
              ("late", "night"), ("all day", "all"), ("all hours", "all")]
STOPWORDS = {"show", "me", "in", "for", "and", "of", "the", "with", "to", "from", "by", "a", "an", "new",
             "completed", "completions", "nyc", "city", "district", "districts", "cd", "between", "on", "at",
             "data", "report", "vs", "versus", "compared", "per", "all", "year", "years", "during", "income"}


def parse_search(text):
    """Turn a query such as 'Brooklyn 2022 new buildings' into filters.

    Returns (filters, applied, ignored): every dimension the query mentions is set; the others
    go back to their defaults, so the result never depends on what was selected before.
    """
    query = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
    filters = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
    applied = {}

    def take(pattern):
        nonlocal query
        query = re.sub(pattern, " ", query)

    # Community districts: "BK 05", "bk5", "brooklyn cd 5", "QN07"
    districts = set()
    for prefix, boro in DISTRICT_PREFIX.items():
        for number in re.findall(rf"\b{prefix}\s?-?(\d{{1,2}})\b", query):
            districts.add(boro * 100 + int(number))
        take(rf"\b{prefix}\s?-?\d{{1,2}}\b")
    for word, borough in BOROUGH_WORDS:
        boro = BOROUGHS.index(borough) + 1
        for number in re.findall(rf"\b{word}\s+(?:cd|community district|district)\s*(\d{{1,2}})\b", query):
            districts.add(boro * 100 + int(number))
        take(rf"\b{word}\s+(?:cd|community district|district)\s*\d{{1,2}}\b")
    districts = sorted(d for d in districts if d in LABELS)
    if districts:
        filters["districts"] = districts
        applied["Districts"] = ", ".join(LABELS[d] for d in districts)

    boroughs = []
    for word, borough in BOROUGH_WORDS:
        if re.search(rf"\b{word}\b", query):
            if borough not in boroughs:
                boroughs.append(borough)
            take(rf"\b{word}\b")
    # A named district must stay visible, so its borough is always part of the borough filter.
    boroughs += [BOROUGHS[d // 100 - 1] for d in districts]
    if boroughs:
        filters["boroughs"] = [b for b in BOROUGHS if b in boroughs]
        applied["Borough"] = ", ".join(filters["boroughs"])

    years = set()
    for start, end in re.findall(r"\b(20\d\d)\s*(?:-|to|through|until)\s*(20\d\d)\b", query):
        years.update(range(int(start), int(end) + 1))
    take(r"\b20\d\d\s*(?:-|to|through|until)\s*20\d\d\b")
    years.update(int(y) for y in re.findall(r"\b(20\d\d)\b", query))
    take(r"\b20\d\d\b")
    years = sorted(y for y in years if y in YEARS)
    if years:
        filters["years"] = years
        applied["Year"] = ", ".join(map(str, years))

    for table, key, name, labels in [(HOUSING_WORDS, "housing", "Housing", HOUSING_MEASURES),
                                     (CRASH_WORDS, "crash", "Crashes", CRASH_MEASURES),
                                     (TIME_WORDS, "time", "Time of day", TIME_BANDS)]:
        for word, value in table:
            pattern = rf"\b{re.escape(word)}"      # match at a word start: 'rent' must not hit 'current'
            if re.search(pattern, query):
                if name not in applied:            # the list is ordered most-specific first
                    filters[key] = value
                    applied[name] = labels[value][0]
                take(pattern + r"[a-z]*")

    leftovers = re.findall(r"[a-z0-9][a-z0-9'-]*", query)
    ignored = [w for w in leftovers if w not in STOPWORDS and not re.fullmatch(r"(s|es|ed|ing|ies|y)", w)]
    return filters, applied, ignored
