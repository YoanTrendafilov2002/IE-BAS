import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "outputs" / "AOD440_AE440-870_interactive_seasonal_scatter_2020-2026.html"
ANNUAL_BASIS_CSV = ROOT / "outputs" / "aeronet_summary_data" / "annual_AOD440_AE440-870_basis_summary.csv"
OVERALL_BASIS_CSV = ROOT / "outputs" / "aeronet_summary_data" / "overall_AOD440_AE440-870_basis_summary.csv"

DATA_DIR = ROOT / "outputs" / "aeronet_summary_data_no_2022-10-21"
DAILY_CSV = DATA_DIR / "daily_summary.csv"
INDIVIDUAL_CSV = DATA_DIR / "individual_observations.csv"
EXCLUDED_DATES = {"2022-10-21"}


def excel_fraction_to_time(value):
    try:
        fraction = float(value) % 1
    except (TypeError, ValueError):
        return str(value)
    seconds = int(round(fraction * 24 * 60 * 60))
    seconds %= 24 * 60 * 60
    hour, rem = divmod(seconds, 3600)
    minute, second = divmod(rem, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def read_daily():
    rows = []
    with DAILY_CSV.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["date"] in EXCLUDED_DATES:
                continue
            aod = row.get("AOD_440nm_mean")
            ae = row.get("440-870_Angstrom_Exponent_mean")
            if not aod or not ae:
                continue
            rows.append(
                [
                    round(float(aod), 6),
                    round(float(ae), 6),
                    row["season"],
                    row["date"],
                    int(row["AOD_440nm_n"]),
                    int(row["440-870_Angstrom_Exponent_n"]),
                ]
            )
    return rows


def read_individual():
    rows = []
    with INDIVIDUAL_CSV.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["date"] in EXCLUDED_DATES:
                continue
            aod = row.get("AOD_440nm")
            ae = row.get("440-870_Angstrom_Exponent")
            if not aod or not ae:
                continue
            rows.append(
                [
                    round(float(aod), 6),
                    round(float(ae), 6),
                    row["season"],
                    row["date"],
                    excel_fraction_to_time(row["time"]),
                ]
            )
    return rows


def season_counts(rows):
    counts = {}
    for row in rows:
        counts[row[2]] = counts.get(row[2], 0) + 1
    return counts


def summarize(values):
    if not values:
        return {"mean": None, "std": None, "n": 0}
    return {
        "mean": sum(values) / len(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0,
        "n": len(values),
    }


def annual_summary(rows):
    by_year = defaultdict(lambda: {"aod": [], "ae": []})
    for row in rows:
        year = int(row[3][:4])
        by_year[year]["aod"].append(row[0])
        by_year[year]["ae"].append(row[1])

    rows = []
    for year in sorted(by_year):
        aod = summarize(by_year[year]["aod"])
        ae = summarize(by_year[year]["ae"])
        rows.append(
            {
                "year": year,
                "aod_mean": aod["mean"],
                "aod_std": aod["std"],
                "ae_mean": ae["mean"],
                "ae_std": ae["std"],
                "n": min(aod["n"], ae["n"]),
            }
        )
    return rows


def overall_summary(rows):
    aod = summarize([row[0] for row in rows])
    ae = summarize([row[1] for row in rows])
    return {
        "aod_mean": aod["mean"],
        "aod_std": aod["std"],
        "ae_mean": ae["mean"],
        "ae_std": ae["std"],
        "n": min(aod["n"], ae["n"]),
    }


def write_annual_basis_summary(summary_by_basis):
    ANNUAL_BASIS_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["basis", "year", "aod_mean", "aod_std", "ae_mean", "ae_std", "n"]
    with ANNUAL_BASIS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for basis, rows in summary_by_basis.items():
            for row in rows:
                writer.writerow({"basis": basis, **row})


def write_overall_basis_summary(summary_by_basis):
    OVERALL_BASIS_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["basis", "aod_mean", "aod_std", "ae_mean", "ae_std", "n"]
    with OVERALL_BASIS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for basis, row in summary_by_basis.items():
            writer.writerow({"basis": basis, **row})


def build_html(payload):
    data_json = json.dumps(payload, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Interactive Seasonal AOD440 AE440/870 Scatter</title>
<style>
:root {{
  --ink: #172234;
  --muted: #506078;
  --line: #d9e0ea;
  --panel: #ffffff;
  --paper: #f6f8fb;
  --blue: #2f80bd;
  --orange: #ee9344;
  --olive: #7f944a;
  --pink: #cf6f93;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: "Segoe UI", Arial, sans-serif;
}}
header {{
  padding: 20px 24px 12px;
  background: var(--panel);
  border-bottom: 1px solid var(--line);
}}
h1 {{
  margin: 0;
  font-size: 28px;
  line-height: 1.16;
  letter-spacing: 0;
}}
main {{
  padding: 16px 24px 24px;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
}}
.toolbar, .plot-shell {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}}
.toolbar {{
  padding: 14px;
  align-self: start;
}}
.group {{
  padding: 10px 0 14px;
  border-bottom: 1px solid var(--line);
}}
.group:last-child {{ border-bottom: 0; padding-bottom: 0; }}
.label {{
  display: block;
  font-size: 12px;
  color: var(--muted);
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 8px;
}}
.segmented {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}}
button, .season-toggle {{
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  border-radius: 6px;
  padding: 8px 10px;
  font: inherit;
  cursor: pointer;
  min-height: 36px;
}}
button.active {{
  border-color: #26364e;
  background: #26364e;
  color: #fff;
}}
.season-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}}
.season-toggle {{
  display: flex;
  align-items: center;
  gap: 8px;
  user-select: none;
}}
.season-toggle input {{ margin: 0; }}
.swatch {{
  width: 10px;
  height: 10px;
  display: inline-block;
  border-radius: 50%;
}}
.metric {{
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px 10px;
  font-size: 13px;
  margin-top: 8px;
}}
.metric span:nth-child(odd) {{ color: var(--muted); }}
input[type="range"] {{ width: 100%; }}
.plot-shell {{
  min-width: 0;
  padding: 14px;
  position: relative;
}}
.canvas-wrap {{
  position: relative;
  width: 100%;
  aspect-ratio: 1.4;
  min-height: 520px;
}}
canvas {{
  width: 100%;
  height: 100%;
  display: block;
  border-radius: 4px;
  background: #fff;
}}
.tooltip {{
  position: absolute;
  min-width: 180px;
  pointer-events: none;
  background: rgba(23, 34, 52, 0.95);
  color: #fff;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.45;
  transform: translate(12px, 12px);
  display: none;
  z-index: 4;
}}
.status {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}}
.status strong {{ font-size: 15px; }}
.status span {{ color: var(--muted); font-size: 13px; }}
.classification {{
  border-top: 1px solid var(--line);
  margin-top: 14px;
  padding-top: 14px;
}}
.annual-section {{
  position: relative;
  border-top: 1px solid var(--line);
  margin-top: 14px;
  padding-top: 14px;
}}
.table-controls {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}}
.table-controls .segmented {{
  grid-template-columns: repeat(3, minmax(88px, 1fr));
}}
.table-controls h2 {{
  font-size: 16px;
  margin: 0;
}}
.table-wrap {{
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  min-width: 820px;
  font-size: 13px;
}}
th, td {{
  border-bottom: 1px solid var(--line);
  padding: 8px 9px;
  text-align: right;
  vertical-align: top;
}}
th:first-child, td:first-child {{
  text-align: left;
  font-weight: 700;
  color: var(--ink);
  position: sticky;
  left: 0;
  background: #fff;
}}
thead th {{
  background: #f8fafc;
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
}}
thead th:first-child {{ background: #f8fafc; }}
tbody tr:last-child td {{ border-bottom: 0; }}
tfoot td {{
  background: #f8fafc;
  font-weight: 700;
}}
td span {{
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 400;
  margin-top: 2px;
}}
.annual-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 10px;
}}
.overall-grid {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}}
.overall-card {{
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  background: #f8fafc;
}}
.overall-card span {{
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 5px;
}}
.overall-card strong {{
  display: block;
  font-size: 24px;
  line-height: 1.05;
}}
.overall-card em {{
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
  font-style: normal;
}}
.annual-card {{
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  background: #fff;
}}
.annual-card h3 {{
  margin: 0 0 4px;
  font-size: 15px;
}}
.annual-card p {{
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.35;
}}
.annual-canvas-wrap {{
  width: 100%;
  height: 310px;
  margin-top: 8px;
}}
.annual-canvas-wrap canvas {{
  width: 100%;
  height: 100%;
  display: block;
  background: #fff;
}}
.note {{
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.4;
}}
@media (max-width: 900px) {{
  main {{ grid-template-columns: 1fr; padding: 12px; }}
  header {{ padding: 16px 12px 10px; }}
  .canvas-wrap {{ min-height: 420px; }}
  .annual-grid {{ grid-template-columns: 1fr; }}
  .overall-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<header>
  <h1>Interactive Seasonal AOD440 - AE440/870 Scatter</h1>
</header>
<main>
  <aside class="toolbar">
    <section class="group">
      <span class="label">Dataset</span>
      <div class="segmented">
        <button id="dailyBtn" class="active" type="button">Daily means</button>
        <button id="individualBtn" type="button">Individual</button>
      </div>
    </section>
    <section class="group">
      <span class="label">Seasons</span>
      <div class="season-grid" id="seasonControls"></div>
    </section>
    <section class="group">
      <span class="label">View</span>
      <div class="segmented">
        <button id="fitBtn" type="button">Fit</button>
        <button id="paperBtn" type="button">Paper scale</button>
      </div>
      <div class="metric">
        <span>Shown</span><strong id="shownCount">0</strong>
        <span>Hovered</span><strong id="hoveredValue">-</strong>
      </div>
    </section>
    <section class="group">
      <span class="label">Marks</span>
      <div class="metric">
        <span>Size</span><strong id="sizeValue">4</strong>
      </div>
      <input id="sizeSlider" type="range" min="1" max="9" step="1" value="4">
      <div class="metric">
        <span>Opacity</span><strong id="opacityValue">70%</strong>
      </div>
      <input id="opacitySlider" type="range" min="10" max="100" step="5" value="70">
    </section>
  </aside>
  <section class="plot-shell">
    <div class="status">
      <strong id="plotTitle">Daily means by season</strong>
      <span id="viewStatus"></span>
    </div>
    <div class="canvas-wrap" id="canvasWrap">
      <canvas id="plotCanvas"></canvas>
      <div class="tooltip" id="tooltip"></div>
    </div>
    <section class="classification">
      <div class="table-controls">
        <h2>Aerosol type distribution</h2>
        <div class="segmented">
          <button id="tableMonthBtn" type="button">Month</button>
          <button id="tableSeasonBtn" class="active" type="button">Season</button>
          <button id="tableYearBtn" type="button">Year</button>
        </div>
      </div>
      <div class="table-wrap">
        <table id="classificationTable"></table>
      </div>
      <p class="note">Classification follows the updated thresholds: Dust AE &lt; 0.8 for all AOD; BB AOD &gt;= 0.35 and AE &gt; 1; Urban 0.2 &lt; AOD &lt; 0.35 and AE &gt; 1; Continental AOD &lt;= 0.2 and AE &gt;= 0.8; Mixed AOD &gt;= 0.2 and 0.8 &lt;= AE &lt;= 1. Percentages are within each row. Excludes 2022-10-21.</p>
    </section>
    <section class="annual-section" id="annual-statistics">
      <div class="table-controls">
        <h2>Annual mean bar graphs with standard deviation</h2>
        <div class="segmented">
          <button id="annualDailyBtn" class="active" type="button">Daily means</button>
          <button id="annualIndividualBtn" type="button">Individual</button>
        </div>
      </div>
      <p class="note" id="annualNote">Each bar is one year, computed from daily means; whiskers show standard deviation. Daily and individual views use the same vertical scale. Excludes 2022-10-21.</p>
      <div class="overall-grid" aria-label="Overall means for selected annual basis">
        <div class="overall-card">
          <span>AOD440 all-data mean</span>
          <strong id="overallAodMean">-</strong>
          <em id="overallAodStd">-</em>
        </div>
        <div class="overall-card">
          <span>AE440/870 all-data mean</span>
          <strong id="overallAeMean">-</strong>
          <em id="overallAeStd">-</em>
        </div>
        <div class="overall-card">
          <span id="overallCountLabel">n days</span>
          <strong id="overallCount">-</strong>
          <em id="overallBasis">daily means</em>
        </div>
      </div>
      <div class="annual-grid">
        <div class="annual-card">
          <h3>AOD440 annual mean</h3>
          <p id="annualAodCaption">Mean AOD440 by year, with standard deviation from daily means.</p>
          <div class="annual-canvas-wrap"><canvas id="annualAodCanvas"></canvas></div>
        </div>
        <div class="annual-card">
          <h3>AE440/870 annual mean</h3>
          <p id="annualAeCaption">Mean Angstrom exponent by year, with standard deviation from daily means.</p>
          <div class="annual-canvas-wrap"><canvas id="annualAeCanvas"></canvas></div>
        </div>
      </div>
      <div class="table-wrap" style="margin-top: 10px;">
        <table id="annualTable"></table>
      </div>
      <div class="tooltip" id="annualTooltip"></div>
    </section>
  </section>
</main>
<script id="payload" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
const seasons = ['MAM', 'JJA', 'SON', 'DJF'];
const seasonNames = {{ MAM: 'Spring', JJA: 'Summer', SON: 'Autumn', DJF: 'Winter' }};
const displaySeason = {{ Spring: 'MAM', Summer: 'JJA', Autumn: 'SON', Winter: 'DJF' }};
const colors = {{ MAM: '#2f80bd', JJA: '#ee9344', SON: '#7f944a', DJF: '#cf6f93' }};
const state = {{
  dataset: 'daily',
  enabled: new Set(seasons),
  bounds: {{ xMin: 0, xMax: 0.9, yMin: 0, yMax: 2.1 }},
  size: 4,
  opacity: 0.7,
  hover: null,
  hoverGrid: new Map(),
  drawFrame: null,
  tableGroup: 'season',
  annualDataset: 'daily',
  selectedMonths: parseRequestedMonths(),
  selectedYears: parseRequestedYears(),
  selectedPeriods: parseRequestedPeriods(),
  dragging: false,
  dragStart: null,
  dragBounds: null,
}};

const canvas = document.getElementById('plotCanvas');
const ctx = canvas.getContext('2d');
const wrap = document.getElementById('canvasWrap');
const tooltip = document.getElementById('tooltip');

function parseRequestedMonths() {{
  const params = new URLSearchParams(window.location.search);
  const raw = params.get('months') || params.get('month');
  if (!raw || raw.toLowerCase() === 'all') return new Set(Array.from({{ length: 12 }}, (_, index) => index + 1));
  const values = raw.split(',')
    .map(part => Number(part.trim()))
    .filter(value => Number.isInteger(value) && value >= 1 && value <= 12);
  return new Set(values.length ? values : Array.from({{ length: 12 }}, (_, index) => index + 1));
}}

function allYears() {{
  return Array.from(new Set(DATA.daily.concat(DATA.individual).map(row => rowYear(row)))).sort((a, b) => a - b);
}}

function parseRequestedYears() {{
  const years = allYears();
  const params = new URLSearchParams(window.location.search);
  const raw = params.get('years') || params.get('year');
  if (!raw || raw.toLowerCase() === 'all') return new Set(years);
  const allowed = new Set(years);
  const values = raw.split(',')
    .map(part => Number(part.trim()))
    .filter(value => Number.isInteger(value) && allowed.has(value));
  return new Set(values.length ? values : years);
}}

function allPeriods() {{
  return Array.from(new Set(DATA.daily.concat(DATA.individual).map(row => String(row[3]).slice(0, 7)))).sort();
}}

function parseRequestedPeriods() {{
  const params = new URLSearchParams(window.location.search);
  if (!params.has('periods')) return null;
  const allowed = new Set(allPeriods());
  const values = (params.get('periods') || '').split(',')
    .map(part => part.trim())
    .filter(value => allowed.has(value));
  return new Set(values);
}}

function rowMonth(row) {{
  return Number(String(row[3]).slice(5, 7));
}}

function rowYear(row) {{
  return Number(String(row[3]).slice(0, 4));
}}

function rowPeriod(row) {{
  return String(row[3]).slice(0, 7);
}}

function filteredRows(datasetName) {{
  const rows = datasetName === 'daily' ? DATA.daily : DATA.individual;
  return rows.filter(row =>
    state.selectedMonths.has(rowMonth(row)) &&
    state.selectedYears.has(rowYear(row)) &&
    (!state.selectedPeriods || state.selectedPeriods.has(rowPeriod(row)))
  );
}}

function selectedMonthNames() {{
  if (state.selectedMonths.size === 12) return 'all months';
  const names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return Array.from(state.selectedMonths).sort((a, b) => a - b).map(month => names[month - 1]).join(', ');
}}

function selectedYearNames() {{
  const years = allYears();
  if (state.selectedYears.size === years.length) return 'all years';
  if (!state.selectedYears.size) return 'no years';
  return Array.from(state.selectedYears).sort((a, b) => a - b).join(', ');
}}

function selectionLabel() {{
  if (state.selectedPeriods) {{
    const selected = Array.from(state.selectedPeriods).sort();
    if (!selected.length) return 'no calendar months';
    if (selected.length <= 6) return selected.join(', ');
    return `${{selected.length}} selected calendar months`;
  }}
  return `${{selectedMonthNames()}}, ${{selectedYearNames()}}`;
}}

function summarize(values) {{
  const clean = values.filter(value => Number.isFinite(value));
  if (!clean.length) return {{ mean: null, std: null, n: 0 }};
  const mean = clean.reduce((sum, value) => sum + value, 0) / clean.length;
  const variance = clean.length > 1
    ? clean.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / (clean.length - 1)
    : 0;
  return {{ mean, std: Math.sqrt(variance), n: clean.length }};
}}

function annualRowsFor(datasetName) {{
  const byYear = new Map();
  filteredRows(datasetName).forEach(row => {{
    const year = Number(String(row[3]).slice(0, 4));
    if (!byYear.has(year)) byYear.set(year, []);
    byYear.get(year).push(row);
  }});
  return Array.from(byYear.entries()).sort((a, b) => a[0] - b[0]).map(([year, rows]) => {{
    const aod = summarize(rows.map(row => row[0]));
    const ae = summarize(rows.map(row => row[1]));
    return {{ year, aod_mean: aod.mean, aod_std: aod.std, ae_mean: ae.mean, ae_std: ae.std, n: rows.length }};
  }});
}}

function overallRowFor(datasetName) {{
  const rows = filteredRows(datasetName);
  const aod = summarize(rows.map(row => row[0]));
  const ae = summarize(rows.map(row => row[1]));
  return {{ aod_mean: aod.mean, aod_std: aod.std, ae_mean: ae.mean, ae_std: ae.std, n: rows.length }};
}}

function currentRows() {{
  return filteredRows(state.dataset)
    .filter(row => state.enabled.has(displaySeason[row[2]]));
}}

function baseRows() {{
  return filteredRows(state.dataset);
}}

function currentAnnualRows() {{
  return annualRowsFor(state.annualDataset);
}}

function currentOverallRow() {{
  return overallRowFor(state.annualDataset);
}}

function annualCountLabel() {{
  return state.annualDataset === 'daily' ? 'n days' : 'n measurements';
}}

function annualBasisLabel() {{
  return state.annualDataset === 'daily' ? 'daily means' : 'individual measurements';
}}

function fitBounds(rows) {{
  if (!rows.length) return {{ xMin: 0, xMax: 1, yMin: 0, yMax: 2.2 }};
  const xs = rows.map(row => row[0]);
  const ys = rows.map(row => row[1]);
  const xMin = Math.max(0, Math.min(...xs) - 0.03);
  const xMax = Math.max(...xs) + 0.03;
  const yMin = Math.max(0, Math.min(...ys) - 0.08);
  const yMax = Math.max(...ys) + 0.08;
  return {{ xMin, xMax, yMin, yMax }};
}}

function paperBounds() {{
  return state.dataset === 'daily'
    ? {{ xMin: 0, xMax: 0.9, yMin: 0, yMax: 2.1 }}
    : {{ xMin: 0, xMax: 1.3, yMin: 0, yMax: 2.3 }};
}}

function resizeCanvas() {{
  const rect = wrap.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(320, Math.round(rect.width * ratio));
  canvas.height = Math.max(320, Math.round(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  draw();
}}

function dims() {{
  const rect = canvas.getBoundingClientRect();
  return {{ w: rect.width, h: rect.height, left: 72, right: 26, top: 22, bottom: 68 }};
}}

function xScale(value, d = dims()) {{
  return d.left + (value - state.bounds.xMin) / (state.bounds.xMax - state.bounds.xMin) * (d.w - d.left - d.right);
}}

function yScale(value, d = dims()) {{
  return d.top + (state.bounds.yMax - value) / (state.bounds.yMax - state.bounds.yMin) * (d.h - d.top - d.bottom);
}}

function invX(px, d = dims()) {{
  return state.bounds.xMin + (px - d.left) / (d.w - d.left - d.right) * (state.bounds.xMax - state.bounds.xMin);
}}

function invY(py, d = dims()) {{
  return state.bounds.yMax - (py - d.top) / (d.h - d.top - d.bottom) * (state.bounds.yMax - state.bounds.yMin);
}}

function niceTicks(min, max, count = 6) {{
  const span = Math.max(0.001, max - min);
  const step0 = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const err = step0 / mag;
  const step = (err >= 5 ? 10 : err >= 2 ? 5 : err >= 1 ? 2 : 1) * mag;
  const ticks = [];
  const start = Math.ceil(min / step) * step;
  for (let value = start; value <= max + step * 0.5; value += step) ticks.push(value);
  return ticks;
}}

function drawMarker(x, y, season, size, alpha) {{
  ctx.globalAlpha = alpha;
  ctx.fillStyle = colors[season];
  ctx.beginPath();
  if (season === 'MAM') {{
    ctx.arc(x, y, size, 0, Math.PI * 2);
  }} else if (season === 'JJA') {{
    ctx.moveTo(x, y - size * 1.15);
    ctx.lineTo(x + size * 1.1, y + size);
    ctx.lineTo(x - size * 1.1, y + size);
    ctx.closePath();
  }} else if (season === 'SON') {{
    ctx.rect(x - size, y - size, size * 2, size * 2);
  }} else {{
    ctx.moveTo(x, y - size * 1.15);
    ctx.lineTo(x + size * 1.15, y);
    ctx.lineTo(x, y + size * 1.15);
    ctx.lineTo(x - size * 1.15, y);
    ctx.closePath();
  }}
  ctx.fill();
  ctx.globalAlpha = 1;
}}

function requestDraw() {{
  if (state.drawFrame) return;
  state.drawFrame = requestAnimationFrame(() => {{
    state.drawFrame = null;
    draw();
  }});
}}

function drawAxes(d) {{
  ctx.clearRect(0, 0, d.w, d.h);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, d.w, d.h);
  ctx.strokeStyle = '#d9e0ea';
  ctx.lineWidth = 1;
  ctx.font = '12px Segoe UI, Arial';
  ctx.fillStyle = '#506078';
  const xTicks = niceTicks(state.bounds.xMin, state.bounds.xMax, 8);
  const yTicks = niceTicks(state.bounds.yMin, state.bounds.yMax, 7);
  yTicks.forEach(tick => {{
    const y = yScale(tick, d);
    ctx.beginPath();
    ctx.moveTo(d.left, y);
    ctx.lineTo(d.w - d.right, y);
    ctx.stroke();
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(tick.toFixed(1), d.left - 9, y);
  }});
  xTicks.forEach(tick => {{
    const x = xScale(tick, d);
    ctx.beginPath();
    ctx.moveTo(x, d.h - d.bottom);
    ctx.lineTo(x, d.h - d.bottom + 5);
    ctx.stroke();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(tick.toFixed(1), x, d.h - d.bottom + 10);
  }});
  ctx.strokeStyle = '#172234';
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(d.left, d.top);
  ctx.lineTo(d.left, d.h - d.bottom);
  ctx.lineTo(d.w - d.right, d.h - d.bottom);
  ctx.stroke();
  ctx.fillStyle = '#172234';
  ctx.font = '700 16px Segoe UI, Arial';
  ctx.textAlign = 'center';
  ctx.fillText(state.dataset === 'daily' ? 'AOD440 daily mean' : 'AOD440', d.left + (d.w - d.left - d.right) / 2, d.h - 18);
  ctx.save();
  ctx.translate(20, d.top + (d.h - d.top - d.bottom) / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(state.dataset === 'daily' ? 'AE440/870 daily mean' : 'AE440/870', 0, 0);
  ctx.restore();
}}

function drawClassificationMargins(d) {{
  ctx.save();
  ctx.setLineDash([7, 5]);
  ctx.lineWidth = 1.2;
  ctx.strokeStyle = '#6f7480';
  ctx.fillStyle = '#3f4756';
  ctx.font = '12px Segoe UI, Arial';

  [
    [0.8, 'AE 0.8'],
    [1.0, 'AE 1.0'],
  ].forEach(([value, label]) => {{
    if (value < state.bounds.yMin || value > state.bounds.yMax) return;
    const y = yScale(value, d);
    ctx.beginPath();
    ctx.moveTo(d.left, y);
    ctx.lineTo(d.w - d.right, y);
    ctx.stroke();
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    ctx.fillText(label, d.w - d.right - 8, y - 4);
  }});

  [
    [0.2, 'AOD 0.20'],
    [0.35, 'AOD 0.35'],
  ].forEach(([value, label]) => {{
    if (value < state.bounds.xMin || value > state.bounds.xMax) return;
    const x = xScale(value, d);
    ctx.beginPath();
    ctx.moveTo(x, d.top);
    ctx.lineTo(x, d.h - d.bottom);
    ctx.stroke();
    ctx.save();
    ctx.translate(x + 5, d.top + 6);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'right';
    ctx.textBaseline = 'top';
    ctx.fillText(label, 0, 0);
    ctx.restore();
  }});
  ctx.restore();
}}

function drawLegend(rows, d) {{
  ctx.font = '13px Segoe UI, Arial';
  let x = d.left;
  const y = 16;
  seasons.forEach(season => {{
    if (!state.enabled.has(season)) return;
    const count = rows.filter(row => displaySeason[row[2]] === season).length;
    drawMarker(x + 7, y - 4, season, 4, 1);
    ctx.fillStyle = '#172234';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${{season}} (${{count.toLocaleString()}})`, x + 18, y - 4);
    x += 112;
  }});
}}

function drawHover(d) {{
  if (!state.hover) return;
  const x = xScale(state.hover[0], d);
  const y = yScale(state.hover[1], d);
  if (x < d.left || x > d.w - d.right || y < d.top || y > d.h - d.bottom) return;
  ctx.strokeStyle = '#172234';
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.arc(x, y, state.size + 4, 0, Math.PI * 2);
  ctx.stroke();
}}

function gridKey(x, y, cell = 28) {{
  return `${{Math.floor(x / cell)}}:${{Math.floor(y / cell)}}`;
}}

function draw() {{
  const d = dims();
  const rows = currentRows();
  drawAxes(d);
  drawClassificationMargins(d);
  const size = state.dataset === 'daily' ? state.size : Math.max(1, state.size - 1);
  const alpha = state.dataset === 'daily' ? state.opacity : Math.min(0.28, state.opacity * 0.35);
  const hoverGrid = new Map();
  ctx.save();
  ctx.beginPath();
  ctx.rect(d.left, d.top, d.w - d.left - d.right, d.h - d.top - d.bottom);
  ctx.clip();
  rows.forEach(row => {{
    const x = xScale(row[0], d);
    const y = yScale(row[1], d);
    if (x < d.left || x > d.w - d.right || y < d.top || y > d.h - d.bottom) return;
    drawMarker(x, y, displaySeason[row[2]], size, alpha);
    const key = gridKey(x, y);
    if (!hoverGrid.has(key)) hoverGrid.set(key, []);
    hoverGrid.get(key).push([x, y, row]);
  }});
  ctx.restore();
  state.hoverGrid = hoverGrid;
  drawLegend(rows, d);
  drawHover(d);
  document.getElementById('shownCount').textContent = rows.length.toLocaleString();
  document.getElementById('viewStatus').textContent = `${{selectionLabel()}} | x ${{state.bounds.xMin.toFixed(2)}}-${{state.bounds.xMax.toFixed(2)}} | y ${{state.bounds.yMin.toFixed(2)}}-${{state.bounds.yMax.toFixed(2)}}`;
  document.getElementById('plotTitle').textContent = state.dataset === 'daily'
    ? `Daily means by season - ${{selectionLabel()}}`
    : `Individual measurements by season - ${{selectionLabel()}}`;
}}

const aerosolTypes = ['Dust', 'BB', 'Urban', 'Continental', 'Mixed'];
const groupOrders = {{
  month: Array.from({{ length: 12 }}, (_, index) => String(index + 1)),
  season: ['DJF', 'JJA', 'MAM', 'SON'],
}};

function classifyAerosol(row) {{
  const aod = row[0];
  const ae = row[1];
  if (ae < 0.8) return 'Dust';
  if (aod >= 0.35 && ae > 1) return 'BB';
  if (aod > 0.2 && aod < 0.35 && ae > 1) return 'Urban';
  if (aod <= 0.2 && ae >= 0.8) return 'Continental';
  return 'Mixed';
}}

function groupLabel(row) {{
  if (state.tableGroup === 'month') return String(Number(row[3].slice(5, 7)));
  if (state.tableGroup === 'year') return row[3].slice(0, 4);
  return displaySeason[row[2]];
}}

function sortedGroups(groups) {{
  const labels = Array.from(groups.keys());
  if (state.tableGroup === 'month') return groupOrders.month.filter(label => groups.has(label));
  if (state.tableGroup === 'season') return groupOrders.season.filter(label => groups.has(label));
  return labels.sort((a, b) => Number(a) - Number(b));
}}

function cellHtml(count, total) {{
  const pct = total ? (count / total * 100) : 0;
  return `${{count.toLocaleString()}}<span>${{pct.toFixed(1)}}%</span>`;
}}

function renderClassificationTable(rows) {{
  const table = document.getElementById('classificationTable');
  const groups = new Map();
  rows.forEach(row => {{
    const label = groupLabel(row);
    const type = classifyAerosol(row);
    if (!groups.has(label)) {{
      groups.set(label, {{ total: 0, counts: Object.fromEntries(aerosolTypes.map(name => [name, 0])) }});
    }}
    const group = groups.get(label);
    group.total += 1;
    group.counts[type] += 1;
  }});

  const columns = aerosolTypes;
  const totals = {{ total: 0, counts: Object.fromEntries(columns.map(name => [name, 0])) }};
  const body = sortedGroups(groups).map(label => {{
    const group = groups.get(label);
    totals.total += group.total;
    columns.forEach(name => totals.counts[name] += group.counts[name] || 0);
    return `<tr><td>${{label}}</td>${{columns.map(name => `<td>${{cellHtml(group.counts[name] || 0, group.total)}}</td>`).join('')}}<td>${{group.total.toLocaleString()}}</td></tr>`;
  }}).join('');
  const foot = `<tr><td>Total</td>${{columns.map(name => `<td>${{cellHtml(totals.counts[name] || 0, totals.total)}}</td>`).join('')}}<td>${{totals.total.toLocaleString()}}</td></tr>`;
  table.innerHTML = `
    <thead><tr><th>${{state.tableGroup}}</th>${{columns.map(name => `<th>${{name}}</th>`).join('')}}<th>Total</th></tr></thead>
    <tbody>${{body}}</tbody>
    <tfoot>${{foot}}</tfoot>
  `;
}}

let annualLayouts = {{}};

function fmtAnnual(value) {{
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return 'n/a';
  return Number(value).toFixed(4);
}}

function annualScaleMax(metric, stdMetric) {{
  const allRows = [...annualRowsFor('daily'), ...annualRowsFor('individual')];
  return Math.max(...allRows.map(row => (row[metric] || 0) + (row[stdMetric] || 0)), 0.001) * 1.22;
}}

function drawAnnualChart(canvasId, metric, stdMetric, title, color, darkColor) {{
  const canvasEl = document.getElementById(canvasId);
  const annualCtx = canvasEl.getContext('2d');
  const rect = canvasEl.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvasEl.width = Math.max(320, Math.round(rect.width * ratio));
  canvasEl.height = Math.max(260, Math.round(rect.height * ratio));
  annualCtx.setTransform(ratio, 0, 0, ratio, 0, 0);
  annualCtx.clearRect(0, 0, rect.width, rect.height);
  annualCtx.fillStyle = '#fff';
  annualCtx.fillRect(0, 0, rect.width, rect.height);

  const rows = currentAnnualRows();
  if (!rows.length) {{
    annualCtx.fillStyle = '#506078';
    annualCtx.font = '13px Segoe UI, Arial';
    annualCtx.fillText(`No annual data for ${{selectionLabel()}}`, 18, 28);
    annualLayouts[canvasId] = {{ bars: [] }};
    return;
  }}
  const margin = {{ left: 58, right: 18, top: 42, bottom: 64 }};
  const plotW = Math.max(1, rect.width - margin.left - margin.right);
  const plotH = Math.max(1, rect.height - margin.top - margin.bottom);
  const maxY = annualScaleMax(metric, stdMetric);
  const yScale = value => margin.top + plotH - (value / maxY * plotH);
  const band = plotW / rows.length;
  const barW = Math.min(46, band * 0.58);
  const bars = [];

  annualCtx.strokeStyle = '#d9e0ea';
  annualCtx.lineWidth = 1;
  annualCtx.font = '12px Segoe UI, Arial';
  annualCtx.fillStyle = '#506078';
  annualCtx.beginPath();
  for (let i = 0; i <= 4; i += 1) {{
    const y = margin.top + plotH - (plotH * i / 4);
    annualCtx.moveTo(margin.left, y);
    annualCtx.lineTo(margin.left + plotW, y);
  }}
  annualCtx.stroke();

  annualCtx.textAlign = 'right';
  annualCtx.textBaseline = 'middle';
  for (let i = 0; i <= 4; i += 1) {{
    const value = maxY * i / 4;
    const y = margin.top + plotH - (plotH * i / 4);
    annualCtx.fillText(value.toFixed(metric === 'aod_mean' ? 2 : 1), margin.left - 8, y);
  }}

  rows.forEach((row, index) => {{
    const mean = row[metric];
    const std = row[stdMetric];
    const x = margin.left + band * index + (band - barW) / 2;
    const y = yScale(mean);
    const h = margin.top + plotH - y;
    const center = x + barW / 2;
    const errTop = yScale(mean + std);
    const errBottom = yScale(Math.max(0, mean - std));
    annualCtx.fillStyle = color;
    annualCtx.strokeStyle = darkColor;
    annualCtx.lineWidth = 1;
    annualCtx.fillRect(x, y, barW, h);
    annualCtx.strokeRect(x, y, barW, h);

    annualCtx.strokeStyle = '#263241';
    annualCtx.lineWidth = 1.3;
    annualCtx.beginPath();
    annualCtx.moveTo(center, errTop);
    annualCtx.lineTo(center, errBottom);
    annualCtx.moveTo(center - 6, errTop);
    annualCtx.lineTo(center + 6, errTop);
    annualCtx.moveTo(center - 6, errBottom);
    annualCtx.lineTo(center + 6, errBottom);
    annualCtx.stroke();

    annualCtx.fillStyle = '#172234';
    annualCtx.font = '700 11px Segoe UI, Arial';
    annualCtx.textAlign = 'center';
    annualCtx.textBaseline = 'bottom';
    annualCtx.fillText(fmtAnnual(mean), center, Math.max(13, errTop - 8));

    annualCtx.fillStyle = '#506078';
    annualCtx.textAlign = 'center';
    annualCtx.textBaseline = 'top';
    annualCtx.fillText(String(row.year), center, margin.top + plotH + 10);
    bars.push({{ x, y: errTop, w: barW, h: margin.top + plotH - errTop, row, metric, stdMetric, title }});
  }});

  annualCtx.strokeStyle = '#172234';
  annualCtx.lineWidth = 1.5;
  annualCtx.beginPath();
  annualCtx.moveTo(margin.left, margin.top);
  annualCtx.lineTo(margin.left, margin.top + plotH);
  annualCtx.lineTo(margin.left + plotW, margin.top + plotH);
  annualCtx.stroke();
  annualCtx.fillStyle = '#172234';
  annualCtx.font = '700 13px Segoe UI, Arial';
  annualCtx.textAlign = 'center';
  annualCtx.fillText(`${{title}} (${{annualBasisLabel()}})`, margin.left + plotW / 2, rect.height - 12);
  annualLayouts[canvasId] = {{ bars }};
}}

function drawAnnualCharts() {{
  drawAnnualChart('annualAodCanvas', 'aod_mean', 'aod_std', 'AOD440 annual mean', '#2f80bd', '#1c5f91');
  drawAnnualChart('annualAeCanvas', 'ae_mean', 'ae_std', 'AE440/870 annual mean', '#ee9344', '#b4641f');
}}

function renderAnnualTable() {{
  const rows = currentAnnualRows();
  const countLabel = annualCountLabel();
  document.getElementById('annualTable').innerHTML = `
    <thead>
      <tr>
        <th>Year</th>
        <th>AOD440 mean</th>
        <th>AOD440 std</th>
        <th>AE440/870 mean</th>
        <th>AE440/870 std</th>
        <th>${{countLabel}}</th>
      </tr>
    </thead>
    <tbody>
      ${{rows.map(row => `
        <tr>
          <td>${{row.year}}</td>
          <td>${{fmtAnnual(row.aod_mean)}}</td>
          <td>${{fmtAnnual(row.aod_std)}}</td>
          <td>${{fmtAnnual(row.ae_mean)}}</td>
          <td>${{fmtAnnual(row.ae_std)}}</td>
          <td>${{row.n.toLocaleString()}}</td>
        </tr>
      `).join('')}}
    </tbody>
  `;
}}

function renderOverallSummary() {{
  const row = currentOverallRow();
  document.getElementById('overallAodMean').textContent = fmtAnnual(row.aod_mean);
  document.getElementById('overallAodStd').textContent = `std ${{fmtAnnual(row.aod_std)}}`;
  document.getElementById('overallAeMean').textContent = fmtAnnual(row.ae_mean);
  document.getElementById('overallAeStd').textContent = `std ${{fmtAnnual(row.ae_std)}}`;
  document.getElementById('overallCountLabel').textContent = annualCountLabel();
  document.getElementById('overallCount').textContent = row.n.toLocaleString();
  document.getElementById('overallBasis').textContent = annualBasisLabel();
}}

function setAnnualDataset(name) {{
  state.annualDataset = name;
  document.getElementById('annualDailyBtn').classList.toggle('active', name === 'daily');
  document.getElementById('annualIndividualBtn').classList.toggle('active', name === 'individual');
  const basis = annualBasisLabel();
  document.getElementById('annualNote').textContent = `Each bar is one year, computed from ${{basis}} for ${{selectionLabel()}}; whiskers show standard deviation. Daily and individual views use the same vertical scale. Excludes 2022-10-21.`;
  document.getElementById('annualAodCaption').textContent = `Mean AOD440 by year, with standard deviation from ${{basis}} for ${{selectionLabel()}}.`;
  document.getElementById('annualAeCaption').textContent = `Mean Angstrom exponent by year, with standard deviation from ${{basis}} for ${{selectionLabel()}}.`;
  hideAnnualTooltip();
  renderOverallSummary();
  renderAnnualTable();
  drawAnnualCharts();
}}

function hideAnnualTooltip() {{
  document.getElementById('annualTooltip').style.display = 'none';
}}

function updateAnnualTooltip(event, canvasId) {{
  const layout = annualLayouts[canvasId];
  if (!layout) return hideAnnualTooltip();
  const canvasEl = document.getElementById(canvasId);
  const rect = canvasEl.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const bar = layout.bars.find(item => x >= item.x - 4 && x <= item.x + item.w + 4 && y >= item.y - 8 && y <= item.y + item.h + 8);
  if (!bar) return hideAnnualTooltip();
  const row = bar.row;
  const valueLabel = bar.metric === 'aod_mean' ? 'AOD440' : 'AE440/870';
  const tooltipEl = document.getElementById('annualTooltip');
  tooltipEl.innerHTML = `<strong>${{valueLabel}} - ${{row.year}}</strong><div>Mean: ${{fmtAnnual(row[bar.metric])}}</div><div>Standard deviation: ${{fmtAnnual(row[bar.stdMetric])}}</div><div>${{annualCountLabel()}}: ${{row.n.toLocaleString()}}</div><div>Basis: ${{annualBasisLabel()}}</div>`;
  const panel = document.querySelector('.annual-section').getBoundingClientRect();
  const tipWidth = 240;
  const left = Math.min(Math.max(8, event.clientX - panel.left + 14), panel.width - tipWidth - 8);
  const top = Math.max(8, event.clientY - panel.top - 76);
  tooltipEl.style.left = `${{left}}px`;
  tooltipEl.style.top = `${{top}}px`;
  tooltipEl.style.display = 'block';
}}

function nearestPoint(mouseX, mouseY) {{
  const d = dims();
  if (mouseX < d.left || mouseX > d.w - d.right || mouseY < d.top || mouseY > d.h - d.bottom) return null;
  let best = null;
  let bestDist = Infinity;
  const threshold = state.dataset === 'daily' ? 12 : 8;
  const cell = 28;
  const gx = Math.floor(mouseX / cell);
  const gy = Math.floor(mouseY / cell);
  for (let dx = -1; dx <= 1; dx += 1) {{
    for (let dy = -1; dy <= 1; dy += 1) {{
      const bucket = state.hoverGrid.get(`${{gx + dx}}:${{gy + dy}}`);
      if (!bucket) continue;
      for (const point of bucket) {{
        const dist = Math.hypot(point[0] - mouseX, point[1] - mouseY);
        if (dist < bestDist) {{
          bestDist = dist;
          best = point[2];
        }}
      }}
    }}
  }}
  return bestDist <= threshold ? best : null;
}}

function setTooltip(row, x, y) {{
  if (!row) {{
    tooltip.style.display = 'none';
    document.getElementById('hoveredValue').textContent = '-';
    state.hover = null;
    return;
  }}
  const season = displaySeason[row[2]];
  const extra = state.dataset === 'daily'
    ? `<div>AOD samples: ${{row[4]}}</div><div>AE samples: ${{row[5]}}</div>`
    : `<div>Time: ${{row[4]}}</div>`;
  tooltip.innerHTML = `<strong>${{season}} - ${{row[3]}}</strong><div>AOD440: ${{row[0].toFixed(3)}}</div><div>AE440/870: ${{row[1].toFixed(3)}}</div>${{extra}}`;
  tooltip.style.left = `${{x}}px`;
  tooltip.style.top = `${{y}}px`;
  tooltip.style.display = 'block';
  document.getElementById('hoveredValue').textContent = `${{row[0].toFixed(3)}}, ${{row[1].toFixed(3)}}`;
  state.hover = row;
}}

function setDataset(name) {{
  state.dataset = name;
  document.getElementById('dailyBtn').classList.toggle('active', name === 'daily');
  document.getElementById('individualBtn').classList.toggle('active', name === 'individual');
  state.hover = null;
  state.bounds = paperBounds();
  tooltip.style.display = 'none';
  draw();
  renderClassificationTable(currentRows());
  setAnnualDataset(name);
}}

function makeSeasonControls() {{
  const holder = document.getElementById('seasonControls');
  holder.innerHTML = seasons.map(season => `
    <label class="season-toggle">
      <input type="checkbox" data-season="${{season}}" checked>
      <span class="swatch" style="background:${{colors[season]}}"></span>
      <span>${{season}}</span>
    </label>
  `).join('');
  holder.querySelectorAll('input').forEach(input => {{
    input.addEventListener('change', () => {{
      if (input.checked) state.enabled.add(input.dataset.season);
      else state.enabled.delete(input.dataset.season);
      state.hover = null;
      tooltip.style.display = 'none';
      draw();
      renderClassificationTable(currentRows());
    }});
  }});
}}

function zoomAt(mouseX, mouseY, factor) {{
  const d = dims();
  const cx = invX(mouseX, d);
  const cy = invY(mouseY, d);
  const xSpan = (state.bounds.xMax - state.bounds.xMin) * factor;
  const ySpan = (state.bounds.yMax - state.bounds.yMin) * factor;
  const xRatio = (cx - state.bounds.xMin) / (state.bounds.xMax - state.bounds.xMin);
  const yRatio = (cy - state.bounds.yMin) / (state.bounds.yMax - state.bounds.yMin);
  state.bounds = {{
    xMin: cx - xSpan * xRatio,
    xMax: cx + xSpan * (1 - xRatio),
    yMin: Math.max(0, cy - ySpan * yRatio),
    yMax: cy + ySpan * (1 - yRatio),
  }};
  requestDraw();
}}

canvas.addEventListener('wheel', event => {{
  event.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const factor = event.deltaY < 0 ? 0.82 : 1.22;
  zoomAt(event.clientX - rect.left, event.clientY - rect.top, factor);
}}, {{ passive: false }});

canvas.addEventListener('mousedown', event => {{
  state.dragging = true;
  state.dragStart = {{ x: event.clientX, y: event.clientY }};
  state.dragBounds = {{ ...state.bounds }};
}});

window.addEventListener('mouseup', () => {{
  state.dragging = false;
}});

canvas.addEventListener('mousemove', event => {{
  const rect = canvas.getBoundingClientRect();
  const mx = event.clientX - rect.left;
  const my = event.clientY - rect.top;
  if (state.dragging && state.dragStart) {{
    const d = dims();
    const dx = (event.clientX - state.dragStart.x) / (d.w - d.left - d.right) * (state.dragBounds.xMax - state.dragBounds.xMin);
    const dy = (event.clientY - state.dragStart.y) / (d.h - d.top - d.bottom) * (state.dragBounds.yMax - state.dragBounds.yMin);
    state.bounds = {{
      xMin: state.dragBounds.xMin - dx,
      xMax: state.dragBounds.xMax - dx,
      yMin: Math.max(0, state.dragBounds.yMin + dy),
      yMax: state.dragBounds.yMax + dy,
    }};
    tooltip.style.display = 'none';
    requestDraw();
    return;
  }}
  const nearest = nearestPoint(mx, my);
  setTooltip(nearest, mx, my);
}});

canvas.addEventListener('mouseleave', () => setTooltip(null, 0, 0));
document.getElementById('dailyBtn').addEventListener('click', () => setDataset('daily'));
document.getElementById('individualBtn').addEventListener('click', () => setDataset('individual'));
document.getElementById('annualDailyBtn').addEventListener('click', () => setAnnualDataset('daily'));
document.getElementById('annualIndividualBtn').addEventListener('click', () => setAnnualDataset('individual'));
function setTableGroup(group) {{
  state.tableGroup = group;
  document.getElementById('tableMonthBtn').classList.toggle('active', group === 'month');
  document.getElementById('tableSeasonBtn').classList.toggle('active', group === 'season');
  document.getElementById('tableYearBtn').classList.toggle('active', group === 'year');
  renderClassificationTable(currentRows());
}}
document.getElementById('tableMonthBtn').addEventListener('click', () => setTableGroup('month'));
document.getElementById('tableSeasonBtn').addEventListener('click', () => setTableGroup('season'));
document.getElementById('tableYearBtn').addEventListener('click', () => setTableGroup('year'));
document.getElementById('fitBtn').addEventListener('click', () => {{
  state.bounds = fitBounds(currentRows());
  draw();
}});
document.getElementById('paperBtn').addEventListener('click', () => {{
  state.bounds = paperBounds();
  draw();
}});
document.getElementById('sizeSlider').addEventListener('input', event => {{
  state.size = Number(event.target.value);
  document.getElementById('sizeValue').textContent = state.size;
  requestDraw();
}});
document.getElementById('opacitySlider').addEventListener('input', event => {{
  state.opacity = Number(event.target.value) / 100;
  document.getElementById('opacityValue').textContent = `${{event.target.value}}%`;
  requestDraw();
}});

makeSeasonControls();
state.bounds = paperBounds();
window.addEventListener('resize', () => {{
  resizeCanvas();
  drawAnnualCharts();
}});
document.getElementById('annualAodCanvas').addEventListener('mousemove', event => updateAnnualTooltip(event, 'annualAodCanvas'));
document.getElementById('annualAeCanvas').addEventListener('mousemove', event => updateAnnualTooltip(event, 'annualAeCanvas'));
document.getElementById('annualAodCanvas').addEventListener('mouseleave', hideAnnualTooltip);
document.getElementById('annualAeCanvas').addEventListener('mouseleave', hideAnnualTooltip);
resizeCanvas();
renderClassificationTable(currentRows());
setAnnualDataset('daily');
</script>
</body>
</html>
"""


def main():
    if not DAILY_CSV.exists() or not INDIVIDUAL_CSV.exists():
        raise SystemExit(f"Missing source CSVs in {DATA_DIR}")
    daily = read_daily()
    individual = read_individual()
    annual = {
        "daily": annual_summary(daily),
        "individual": annual_summary(individual),
    }
    overall = {
        "daily": overall_summary(daily),
        "individual": overall_summary(individual),
    }
    write_annual_basis_summary(annual)
    write_overall_basis_summary(overall)
    payload = {
        "daily": daily,
        "individual": individual,
        "counts": {
            "daily": season_counts(daily),
            "individual": season_counts(individual),
        },
        "annual": annual,
        "overall": overall,
    }
    OUT_PATH.write_text(build_html(payload), encoding="utf-8")
    print(f"Daily rows: {len(daily)}")
    print(f"Individual rows: {len(individual)}")
    print(f"Annual basis CSV: {ANNUAL_BASIS_CSV}")
    print(f"Overall basis CSV: {OVERALL_BASIS_CSV}")
    print(f"Output: {OUT_PATH}")


if __name__ == "__main__":
    main()
