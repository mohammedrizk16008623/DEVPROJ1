"""Run with:  python -m pytest -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

import analysis as A  # noqa: E402
import figures as F  # noqa: E402


def test_totals_match_notebook():
    totals = A.district_totals(A.district_year_table(A.DEFAULTS))
    assert len(totals) == 59
    assert totals["housing"].sum() == 48026          # affordable units, 2022-2025
    assert totals["crash"].sum() == 9458             # serious crashes placed in a district
    rho, p, n = A.spearman(totals["housing"], totals["crash"])
    assert n == 59 and round(rho, 3) == 0.248


def test_hourly_table_reconciles_with_annual_totals():
    for crash in A.CRASH_MEASURES:
        f = {**A.DEFAULTS, "crash": crash}
        annual = A.INTEGRATED[A.CRASH_MEASURES[crash][1]].sum()
        assert A.district_year_table(f)["crash"].sum() == annual


def test_time_bands_partition_the_day():
    total = sum(A.district_year_table({"time": t})["crash"].sum() for t in ["am", "midday", "pm", "night"])
    assert total == A.district_year_table({"time": "all"})["crash"].sum()


@pytest.mark.parametrize("text, expected", [
    ("Brooklyn 2022 new buildings", {"boroughs": ["Brooklyn"], "years": [2022], "housing": "buildings"}),
    ("bronx family units injuries", {"boroughs": ["Bronx"], "housing": "family", "crash": "severe_injuries"}),
    ("Queens evening crashes", {"boroughs": ["Queens"], "time": "pm", "crash": "crash_events"}),
    ("BK 01 bx1 2024-2025", {"districts": [201, 301], "boroughs": ["Bronx", "Brooklyn"], "years": [2024, 2025]}),
    ("brooklyn cd 5 rental", {"districts": [305], "housing": "rental"}),
    ("current trends", {"housing": "affordable"}),     # 'rent' inside 'current' must not match
    ("staten island repeat crashes night", {"boroughs": ["Staten Island"],
                                            "crash": "positive_lookback_events", "time": "night"}),
])
def test_search_parser(text, expected):
    filters, applied, ignored = A.parse_search(text)
    for key, value in expected.items():
        assert filters[key] == value, (key, filters[key])


def test_search_resets_unmentioned_dimensions():
    filters, applied, ignored = A.parse_search("2023")
    assert filters["boroughs"] == A.BOROUGHS and filters["housing"] == "affordable" and filters["years"] == [2023]


def test_search_reports_unknown_words():
    _, applied, ignored = A.parse_search("Brooklyn bananas")
    assert applied == {"Borough": "Brooklyn"} and ignored == ["bananas"]


@pytest.mark.parametrize("filters", [
    {}, {"boroughs": ["Staten Island"], "years": [2022]}, {"districts": [101]},
    {"districts": [101, 102], "time": "night"}, {"housing": "ownership", "crash": "non_severe_injuries"},
    {"boroughs": [], "years": []},
])
def test_every_figure_builds(filters):
    f = A.normalise_filters(filters)
    table = A.district_year_table(f)
    totals = A.district_totals(table)
    stats = A.spearman(totals["housing"], totals["crash"])
    for fig in [F.map_figure(totals, f), F.scatter_figure(totals, f, stats), F.ranked_bar_figure(totals, f),
                F.trend_figure(table, f), F.heatmap_figure(A.hourly_profile(f), f)]:
        fig.to_dict()


def test_app_callbacks():
    import app
    out = app.build_report(A.DEFAULTS)
    assert len(out) == 8
    out = app.build_report({**A.DEFAULTS, "districts": [101]})   # one district: no correlation
    assert "n/a" in str(out[0])
