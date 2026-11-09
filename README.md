# Affordable Housing and Street Safety in New York City

**Data Engineering & Visualization: Milestone 1 (Winter 2026, GIU)**

**Live site:** [deployment link]  ·  **Repository:** https://github.com/mohammedrizk16008623/DEVPROJ1  ·  **Notebook:** [`notebook/Final_Submission_Notebook.ipynb`](notebook/Final_Submission_Notebook.ipynb)

> **Research question.** Do neighbourhoods experiencing a surge in new affordable-housing construction also experience more severe street-safety problems?

The project combines two NYC Open Data sources at community-district level for 2022-2025:

- completed affordable-housing buildings (HPD);
- serious-injury and fatal traffic crashes (DOT SIRTA).

The notebook cleans and integrates the data, and each team member answers two research questions in it. This repository holds that notebook and the interactive website built on its outputs.

## Team

| Member | ID | Contribution |
|---|---|---|
| Yassin Amr Hegazy | 16001061 | Research questions 7.4 (peak month of housing completions vs serious crashes; how the gap between the peaks varies by borough) |
| Mohammed Fady Rizk | 16008623 | Research questions 7.5 (borough distribution of affordable housing vs serious crashes; affordable units per building vs crash frequency) |
| Sam Shady Samih Soliman Bostawros | 16004357 | Research questions 7.6 (affordable share of units vs crash frequency; New Construction vs Preservation areas and crash frequency) |
| Amro Taha Salih | 16007093 | Research questions 7.8 (deepest-affordability units vs district crash burden; family-sized units vs school-travel-time crashes) |
| Marawan Mohamed Elgendy | 16001322 | Research questions 7.7 (housing growth vs change in serious injuries; high-housing/high-injury districts) |
| Fares Mustafa El-Sonbaty | 16006173 | Research questions 7.9 (rental vs homeownership in recurring-crash districts; income mix vs spread of crashes across the day) |

**Shared work (all six members):** dataset selection and EDA, pre-integration cleaning, integration and post-integration cleaning, validation of the integrated table, the data story, the website (data preparation, search, filters, charts and layout), this README, the repository and the deployment.

Section 8 of the notebook lists the research questions (8.1), the shared work (8.2) and the prompts used (8.3).

## Datasets

| Dataset | Domain | Link |
|---|---|---|
| Affordable Housing Production by Building (HPD) | Housing & Development | https://data.cityofnewyork.us/Housing-Development/Affordable-Housing-Production-by-Building/hg8x-zxpr |
| Serious Injury Response Tracking Application, SIRTA (DOT) | Transportation | https://data.cityofnewyork.us/Transportation/Serious-Injury-Response-Tracking-Application-SIRTA-/xeqp-qz8h |
| Community Districts (DCP), boundary lookup only | Reference | https://data.cityofnewyork.us/City-Government/Community-Districts/5crt-au7u |

## Main findings

- **Weak overlap.** Across the 59 districts, the rank correlation between new affordable units and serious crashes is 0.25 (permutation p ≈ 0.06). Larger districts tend to have more of both.
- **The boroughs do not line up:**
  - the Bronx received 35.8% of affordable units but had 19.6% of serious crashes;
  - Manhattan received 10.8% of units but had 20.2% of crashes.
- **The worst crash districts get little new housing.** QN 07 (324 serious injuries) and BK 18 (317) received only 53 and 61 affordable units.
- **No rise in crash share where housing grew fastest.** Housing growth vs the change in a district's share of serious injuries gives rho = -0.26.
- **17 districts are high on both.** They have above-median new housing and above-median serious injuries, led by BK 01, BX 01, BK 05, QN 12, BX 04 and MN 04. These are candidates for joint housing and street-safety review.
- **No shared timing.** Completions peak in December and crashes in July.

All results describe association, not causation. See the notebook and the site's *Data story* tab for the limits.

## The website

Built with **Dash + Plotly**. The site reads the notebook's exported tables and does no cleaning of its own, so its numbers match the notebook exactly.

- **Search bar.** Free text such as `Brooklyn 2022 new buildings`, `BX 01 family units injuries`, `Queens evening crashes` or `Manhattan rental repeat crashes night`. The search sets the filters and reports any words it did not recognise.
- **Filters (one row):**
  - borough and year;
  - community district (the list narrows to the chosen boroughs);
  - housing measure (9 options);
  - crash measure (4 options);
  - time of day.
- **Generate Report.** Charts update only when it is pressed. A notice shows when the filters have changed since the last report.
- **Report:**
  - headline numbers with the rank correlation;
  - a written summary;
  - a map (crash shading + housing circles);
  - a district scatter;
  - the top-15 districts;
  - year-by-year trends per borough;
  - an hour-by-borough heatmap;
  - a table view.
- **Other tabs:**
  - *Data story*: the narrative.
  - *Team questions*: all 12 research questions with short answers.
  - *About the data*: definitions and dataset links.

### Repository layout

```
app.py                  Dash layout and callbacks (server = app.server is the WSGI app)
analysis.py             data loading, filtering, search parser, Spearman test
figures.py              Plotly figure builders
assets/style.css        styles (Dash loads assets/ automatically)
data/                   tables exported by the notebook + simplified district boundaries
scripts/prepare_data.py copies the notebook outputs into data/ and simplifies the map
notebook/               the final submission notebook
tests/test_site.py      checks totals against the notebook, search parsing and every chart
api/index.py            Vercel entry point (imports `server` from app.py)
vercel.json             Vercel config: every path goes to api/index.py
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
python app.py                   # http://127.0.0.1:8050
python -m pytest -q             # 19 tests
```

To rebuild `data/` after re-running the notebook, pass the folder the notebook writes its outputs to (it contains `data/` and `reference/`):

```bash
python scripts/prepare_data.py path/to/notebook_output_folder
```

## Deploy (Vercel)

The site runs as one Vercel Python function. `api/index.py` exposes the Flask server that Dash runs on, and `vercel.json` sends every path to it. `data/` and `assets/` are bundled with the function. Tests, the notebook and the scripts are left out.

1. Push this repository to GitHub.
2. On https://vercel.com choose **Add New → Project** and import the repository. Leave **Framework Preset** on *Other*, with no build or output settings. Vercel installs `requirements.txt` and uses Python 3.12 (from `.python-version`).
3. Deploy, then copy the `https://….vercel.app` URL into this README and into Section 9 of the notebook.

With the Vercel CLI, run `vercel` for a preview deployment or `vercel --prod` for production, from this folder.

The first request after the site has been idle starts a new instance. It loads the data and can take a few seconds.

## Prompts used

The prompts used at each step of the project (data preparation, each research question, combining the notebooks, the website and this README) are listed in Section 8.3 of the notebook.

Every number in the notebook and on the site comes from executed code on the full datasets.

## Limitations

- Association only. Counts are not adjusted for population, traffic volume or road length.
- Fatal crashes after 2022 have no coordinates in SIRTA, so fatalities cannot be mapped by district and are left out of the site.
- The share of serious injuries that can be placed in a district varies by year (70-93%).
- A completion date is not a move-in date.
