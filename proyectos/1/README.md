# Aria a Madrid

**Author:** Chiara Geron · Free University of Bozen-Bolzano (unibz)  
**Event:** DATAMAD 2026  
**Working prototype:** https://aria-madrid-laboratorio.chiaragg87.chatgpt.site

## Purpose and added contribution

Aria a Madrid helps people understand public air-quality measurements. Users select a monitoring station, inspect hourly concentrations and air-quality categories, and compare the observations with similar historical days. Explanations linked to each pollutant support learning about sources, health effects and interpretation.

The added contribution is a guided station view combining historical comparisons and educational explanations. The official Madrid services already provide measurements, historical records, indices and forecasts. Improved usability and learning outcomes remain hypotheses to validate with users.

## Run locally

No build step or JavaScript package installation is required. From this project folder, run:

```sh
python3 -m http.server 8765 --directory dist
```

Open http://localhost:8765 in a browser. Do not open index.html directly: the app loads JSON files using fetch. The interface supports Spanish, English and Italian and remembers the selected language.

Internet access is needed for the Leaflet library, map tiles, web fonts and live-data requests. Prepared measurements and historical profiles are included. If the municipal live services cannot be reached, the app retains the last loaded data and displays its status and measurement date; freshness is not guaranteed.

## Included files

- `dist/`: complete static website and prepared JSON data.
- `prepare_data.py`: filtering and historical clustering pipeline.
- `build_annual_history.py`: historical annual summaries, using aggregation functions from the app.
- `integrate_recent.py`: integration of the 2026 archive and saved recent-data snapshot.
- `fetch_sources.py`: municipal archive and recent-data download helper.
- `audit_annual_history.py`: independent annual-summary checks against original archives.
- `verify*.cjs`: checks for observations, missing data, clustering, recent-data integration and annual aggregation.
- `inputs/stations.csv`: station metadata used by the preparation script; original column labels are preserved.

## Data sources and attribution

1. Ayuntamiento de Madrid, hourly air-quality archive: https://datos.madrid.es/dataset/201200-0-calidad-aire-horario
2. Ayuntamiento de Madrid, recent air-quality data: https://datos.madrid.es/dataset/212531-0-calidad-aire-tiempo-real
3. Municipal current-day endpoint: https://ciudadesabiertas.madrid.es/dynamicAPI/API/query/calair_tiemporeal.json?pageSize=4500
4. Municipal recent endpoint: https://ciudadesabiertas.madrid.es/dynamicAPI/API/query/calair_tiemporeal_ult.json?pageSize=4500
5. European Environment Agency index methodology: https://airindex.eea.europa.eu/AQI/
6. Spanish regulatory reference used in the annual section: https://www.boe.es/buscar/act.php?id=BOE-A-2011-1645#ani
7. WHO pollutant and health explanations: https://www.who.int/teams/environment-climate-change-and-health/air-quality-and-health/health-impacts/types-of-pollutants

The measurement source is **Madrid City Council (Ayuntamiento de Madrid)**, not the regional monitoring network. Regional-catalogue eligibility must be assessed against the event rules. Municipal data are attributed in the app as CC BY 4.0; source terms remain applicable. OpenStreetMap, Leaflet and Google Fonts retain their own attribution and licence terms. Including source code here does not assign a new licence to third-party material.

## Historical comparison method

The prototype includes 23 monitoring stations and focuses on NO₂, PM₂.₅, PM₁₀ and O₃. Not every station measures all pollutants. SO₂ is excluded from the displayed index and analytical views; original prepared records may retain its source code for provenance.

Historical reference: **2015–2025**. Exploratory k-means uses three groups of normalised daily shapes, separately by calendar month and pollutant. Days require at least 22 valid hours; up to two internal missing hours are interpolated only for profile construction. Constant profiles are excluded. The implementation uses a fixed random seed and multiple initialisations.

The selected day's observed hours (at least six) are compared with historical group shapes. The graph displays the matched group's median and 25th–75th percentiles in the original concentration units, µg/m³. Station-specific profiles are used where available; shared profiles can provide a fallback. Shared-profile construction requires at least five station profiles per day and median pairwise shape correlation of at least 0.60.

The monthly graph compares daily hourly maxima with historical group maxima. It does not cluster whole months. Measurements and index calculations use valid original observations; missing readings are not replaced by zero.

**The dashed line is a historical comparison, not a forecast.** The green band describes historical variability, not a confidence or prediction interval. Group selection and its usefulness have not yet undergone a comprehensive external validation. Historical dates can belong to the same reference period used to construct the profiles.

## Index and annual summaries

The hourly summary takes the worst available pollutant category, with pollutant-specific EEA thresholds and station-type coverage rules implemented in `app.js`. Concentrations are not added or weighted. This is a prototype adaptation covering four pollutants, not an official monitoring service or an assessment of personal exposure.

The annual view has independent year and pollutant selectors. NO₂ and PM₁₀ summaries count intervals above the corresponding hourly/daily references. O₃ uses daily maximum 8-hour moving means; a single year's count does not assess the three-year target. PM₂.₅ compares daily means with the annual 25 µg/m³ reference descriptively: these are **not daily legal exceedances**. Missing intervals and incomplete periods remain explicit. The app does not certify legal compliance.

## Reproduce the historical processing

Prepared outputs are included so the website can run without re-downloading 11 years of raw archives. For a full rebuild, download the original annual municipal CSV or ZIP resources for 2015–2025 from the archive dataset above into `inputs/historical/`, named `2015.csv` or `2015.zip`, and so on. Raw annual archives are not bundled.

```sh
python3 -m venv .venv
# Activate the environment for your operating system.
python3 -m pip install -r requirements.txt
python3 prepare_data.py
python3 build_annual_history.py
python3 audit_annual_history.py
```

Node.js must be available as `node` for the annual build. Alternatively set `NODE_BINARY` to its executable path. Run from the project folder. The preparation script preserves existing displayed records when `dist/data.json` is present while rebuilding historical profiles. To integrate newly downloaded recent data:

```sh
python3 fetch_sources.py
python3 integrate_recent.py
```

Inspect downloaded data and endpoint completeness before replacing a submission snapshot. The download helper is not an automatic guarantee of source availability or a permanently fixed archive resource.

## Checks

```sh
node verify.cjs
node verify-live.cjs
node verify-annual.cjs
node verify-debug.cjs
```

The recent-data checks use the bundled snapshot, without network requests. These cover known observations, missing values, SO₂ exclusion, historical quantiles, absence of future-hour leakage in profile matching, valid-zero handling, archive precedence, pagination rejection, annual threshold boundaries, daily coverage and leap years. They do not demonstrate predictive skill or improved user comprehension.

## Next steps

Test comprehension with users, assess cluster quality and stability, and evaluate meteorological integration. Planning uses such as sustainable-mobility prioritisation would require additional traffic, exposure and territorial data and specialist assessment.

## Submission

Place this folder's contents inside the project directory assigned by the organisers, such as `proyectos/<assigned-number>/`. Do not modify files outside that directory. A lightweight PowerPoint presentation is included as `Presentazione_Aria_Madrid_light.pptx`. Both embedded videos are retained with reduced resolution and bitrate; slide content and layout are unchanged. All bundled files are below 25 MB. Do not upload account credentials, hosting configuration or private working folders.
