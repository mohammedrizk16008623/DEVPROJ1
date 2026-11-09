# NYC Urban Insights — Housing × Road Safety

A lightweight, **read-only Dash/Plotly website** built on the team's exported, cleaned, and integrated NYC housing/serious-crash results. Data source: GIU Data Engineering & Visualization project, milestone 1.

## What is included

- 12 interactive research-chart definitions, plus housing activity and crash outcome overview charts.
- Borough (multi-select), year (multi-select), community district, housing activity category, and road-safety outcome dropdowns.
- Rule-based text search with supported examples: `Brooklyn 2024`, `Queens preservation`, `district 301`, `Manhattan 2025 fatal`.
- **Generate Report** updates all geographic/year-sensitive charts and overview metrics.
- Methodological notes, project story, limitations, responsive CSS, and pre-exported CSV inputs.
- Validated integration key: community district (`cd`) × year (2022–2025).

## Run on your computer

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:8050**.

## Deploy to Render

1. Commit this folder's contents to a **GitHub repository root** (so that `app.py`, `requirements.txt`, `data/` and `assets/` sit at the repository top level).
2. Create a Render **Web Service** connected to the repository (or use the supplied `render.yaml` Blueprint).
3. Choose Python 3.11, build command `pip install -r requirements.txt`, start command `gunicorn app:server --bind 0.0.0.0:$PORT`.
4. Once deployed, check the public URL using Brooklyn / 2024 and an unsupported search term, and confirm all graphs render and respond to Generate Report.
5. Verify the hosting plan's current free-tier availability independently. Deployment and GitHub upload require your authenticated accounts and are **not yet performed** by this project package.

## Source data / reproducibility

The `data/` directory contains outputs *copied unchanged* from `DEV_with_boundaries_Results.zip`:

| File | Rows | Meaning |
|---|---:|---|
| `integrated_district_year.csv` | 236 | Primary completed New Construction and assigned SIRTA district-year aggregates |
| `housing_program_activity_district_year.csv` | 474 | Housing project-start activity, New Construction/Preservation |
| `crashes_district_year_hour.csv` | 5664 | District-year-hour aggregated crash outcomes |
| `housing_new_construction_2022_2025.csv` | 1878 | Primary housing record detail, including inclusion flags |
| `crashes_2022_2025_assigned.csv` | 9458 | Geographically assigned crash records |

The notebook should accompany the website in the GitHub repository under `notebooks/` for full re-execution. The raw NYC CSVs are not required at website runtime, and the website does not rerun its cleaning pipeline.

**Two official primary sources**:

- NYC HPD Affordable Housing Production by Building: https://data.cityofnewyork.us/d/hg8x-zxpr
- NYC DOT Serious Injury Response, Tracking & Analysis Program: https://data.cityofnewyork.us/d/xeqp-qz8h

The community-district boundary file used for geographic assignment is an auxiliary reference in the source notebook, not a third research-domain dataset.

## Interpretations and filter behavior

- Main housing charts measure **eligible completed New Construction**; activity category select affects the **housing activity overview** based on project-start records. It does not silently convert completion analyses into preservation analyses.
- The crash outcome dropdown affects the **outcome overview and KPI**; research question charts retain each explicitly stated crash measure.
- Borough, year and district selections propagate to every chart. Search terms override named controls for the generated report; search does not silently attempt to interpret unsupported text.
- Growth comparison is only valid when all four study years are selected and shows an explanatory empty state otherwise.
- Some records are geographically unassigned. Data are counts of eligible/assigned observations, not true crash risk rates. SIRTA does not represent all NYC collisions, and these analyses do not justify causal claims.
- The 12 chart definitions are implemented from the user's named research-question inventory. The mapping of each chart to the team's final approved question/owner should be reconciled against their latest Colab notebook before submission. The app does not invent chart findings.

## Checks

```bash
pip install pytest
pytest -q
```

Local code/data-level tests verify the shape of exported tables, all 12 graph computations, common filter combinations, and join uniqueness. Verify the full Dash runtime after dependencies are installed.

## Submission checklist

- [x] The previously reviewed Colab notebook is included under notebooks/; confirm it is the latest version and reconcile all 12 chart assignments.
- [ ] Add team names/IDs and precise individual contributions to this README/notebook.
- [ ] Run all charts, inspect titles, units, filter semantics and notebook reconciliation.
- [ ] Confirm text search, dropdowns, Generate Report and mobile behavior on the live URL.
- [ ] Submit the six member IDs, GitHub link, live deployment link and both dataset links to the course address by the stated deadline.

## Team contributions

**To be filled using actual team work; no contribution claims are inferred.**
