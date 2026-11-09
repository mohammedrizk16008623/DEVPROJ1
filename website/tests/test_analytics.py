import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analytics import load_data, filtered, metrics, chart, SPECS, YEARS


def test_baseline():
    data=load_data()
    assert data['integrated'].shape==(236,70)
    assert len(data['activity'])==474
    assert len(data['hourly'])==5664
    m=metrics(data)
    assert m['housing']==48026
    assert m['crashes']==9458
    assert m['districts']==59


def test_each_chart_on_full_data():
    data=load_data()
    for key,*_ in SPECS:
        fig=chart(key,data)
        assert len(fig.data)>0,(key,"empty or failed")


def test_filters_and_charts():
    data=load_data()
    sets=[filtered(data,['Brooklyn'],[2024]),filtered(data,['Queens'],[2023],401),filtered(data,years=[2022]),filtered(data,boroughs=['Manhattan'],years=[2022,2025]),filtered(data,boroughs=['Staten Island'],years=YEARS)]
    for subset in sets:
        for key,*_ in SPECS:
            fig=chart(key,subset)
            assert fig is not None, key
        assert metrics(subset)['district_years']<=236


def test_no_double_counting():
    data=load_data()
    m=data['integrated']
    assert not m.duplicated(['cd','year']).any()
    assert int(m.crash_events.sum())==len(data['crashes'])
    assert set(m.year.unique())==set(YEARS)
