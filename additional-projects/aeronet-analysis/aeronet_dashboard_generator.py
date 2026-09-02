import csv
import json
import math
import os
import re
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET


OUTPUT_DIR = Path(__file__).resolve().parent
PACKAGED_SOURCE_DIR = OUTPUT_DIR.parent / "data" / "raw_AeronetDATA"
SOURCE_DIR = Path(
    os.environ.get(
        "AERONET_SOURCE_DIR",
        str(PACKAGED_SOURCE_DIR if PACKAGED_SOURCE_DIR.exists() else Path(r"C:\Users\user\Documents\AeronetDATA")),
    )
)
SUPPLEMENTAL_SOURCE_DIRS = [
    OUTPUT_DIR.parent / "inputs" / "supplemental_AERONET",
    OUTPUT_DIR.parent / "data" / "supplied_files",
]
APP_PATH = OUTPUT_DIR / "aeronet_aod_ae_dashboard.html"
DATA_DIR = OUTPUT_DIR / "aeronet_summary_data"

MONTH_ALIASES = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "mart": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

SEASONS = {
    12: "Winter",
    1: "Winter",
    2: "Winter",
    3: "Spring",
    4: "Spring",
    5: "Spring",
    6: "Summer",
    7: "Summer",
    8: "Summer",
    9: "Autumn",
    10: "Autumn",
    11: "Autumn",
}

SEASON_ORDER = {"Winter": 1, "Spring": 2, "Summer": 3, "Autumn": 4}

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def excel_serial_to_datetime(value):
    try:
        serial = float(value)
    except (TypeError, ValueError):
        return None
    return datetime(1899, 12, 30) + timedelta(days=serial)


def column_index(cell_ref):
    letters = re.sub(r"[^A-Z]", "", cell_ref.upper())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def read_shared_strings(zip_file):
    if "xl/sharedStrings.xml" not in zip_file.namelist():
        return []
    root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("a:si", NS):
        strings.append("".join(text.text or "" for text in item.findall(".//a:t", NS)))
    return strings


def cell_value(cell, shared_strings):
    value_node = cell.find("a:v", NS)
    inline_node = cell.find("a:is", NS)
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr" and inline_node is not None:
        return "".join(text.text or "" for text in inline_node.findall(".//a:t", NS))
    if value_node is None:
        return ""

    raw = value_node.text or ""
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return raw
    return raw


def worksheet_sort_key(name):
    match = re.search(r"sheet(\d+)\.xml$", name)
    return int(match.group(1)) if match else name


def read_xlsx_sheets(path):
    with zipfile.ZipFile(path) as workbook:
        shared_strings = read_shared_strings(workbook)
        sheet_names = [name for name in workbook.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")]
        sheets = []
        for sheet_name in sorted(sheet_names, key=worksheet_sort_key):
            root = ET.fromstring(workbook.read(sheet_name))
            rows = []
            for row in root.findall(".//a:sheetData/a:row", NS):
                values = []
                for cell in row.findall("a:c", NS):
                    idx = column_index(cell.attrib.get("r", "A1"))
                    while len(values) <= idx:
                        values.append("")
                    values[idx] = cell_value(cell, shared_strings)
                rows.append(values)
            sheets.append((Path(sheet_name).stem, rows))
        return sheets


def parse_year_month(path):
    haystack = " ".join([path.name] + [part for part in path.parts])
    year_match = re.search(r"\b(20\d{2})\b", haystack)
    month_number = None
    for token in re.findall(r"[A-Za-z]+", haystack):
        key = token.lower()
        if key in MONTH_ALIASES:
            month_number = MONTH_ALIASES[key]
            break
    if not year_match or not month_number:
        return None, None
    return int(year_match.group(1)), month_number


def is_source_file(path):
    name = path.name.lower()
    if path.suffix.lower() != ".xlsx":
        return False
    if "no data" in name or "lunar" in name:
        return False
    return re.search(r"aod\s*,\s*ae", name) is not None and "1.5" in name


def to_float(value):
    if value in ("", None):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= -900 or math.isnan(number):
        return None
    return number


def find_header(rows):
    for idx, row in enumerate(rows):
        normalized = [str(value).strip() for value in row]
        if "Date(dd:mm:yyyy)" in normalized and any("AOD_" in value for value in normalized):
            return idx, normalized
    return None, None


def parse_date(value, fallback_year=None, fallback_month=None):
    text = str(value).strip()
    for fmt in ("%d:%m:%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    parsed = excel_serial_to_datetime(text)
    if parsed:
        return parsed.date()
    if fallback_year and fallback_month:
        day = to_float(text)
        if day and 1 <= int(day) <= 31:
            return datetime(fallback_year, fallback_month, int(day)).date()
    return None


def parse_time(value):
    text = str(value).strip()
    if not text:
        return ""
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M:%S")
        except ValueError:
            pass
    try:
        seconds = int(round((float(text) % 1) * 24 * 60 * 60)) % (24 * 60 * 60)
    except (TypeError, ValueError):
        return text
    hour, remainder = divmod(seconds, 60 * 60)
    minute, second = divmod(remainder, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def observation_key(record, metric_fields):
    if record["time"]:
        return ("timestamp", record["date"], record["time"], record["site"])
    signature = tuple(
        (metric, record.get(metric))
        for metric in sorted(metric_fields)
        if record.get(metric) is not None
    )
    return ("values", record["date"], record["site"], signature)


def merge_observation(existing, incoming, metric_fields):
    sources = set(existing.get("source_files", [existing["source_file"]]))
    sources.update(incoming.get("source_files", [incoming["source_file"]]))
    existing["source_files"] = sorted(sources)
    existing["source_file"] = " | ".join(existing["source_files"])
    for metric in metric_fields:
        if existing.get(metric) is None and incoming.get(metric) is not None:
            existing[metric] = incoming[metric]


def summarize(values):
    clean = [value for value in values if value is not None]
    if not clean:
        return {"mean": None, "std": None, "n": 0}
    return {
        "mean": sum(clean) / len(clean),
        "std": statistics.stdev(clean) if len(clean) > 1 else 0,
        "n": len(clean),
    }


def make_summary_records(records, group_fields, metric_fields):
    grouped = defaultdict(lambda: defaultdict(list))
    labels = {}
    for record in records:
        key = tuple(record[field] for field in group_fields)
        labels[key] = {field: record[field] for field in group_fields}
        for metric in metric_fields:
            grouped[key][metric].append(record.get(metric))

    output = []
    for key in sorted(grouped.keys()):
        row = dict(labels[key])
        for metric in metric_fields:
            stats = summarize(grouped[key][metric])
            row[f"{metric}_mean"] = stats["mean"]
            row[f"{metric}_std"] = stats["std"]
            row[f"{metric}_n"] = stats["n"]
        output.append(row)
    return output


def write_csv(path, records):
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fields = list(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def round_data(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: round_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [round_data(item) for item in value]
    return value


def scan_records():
    source_files = sorted(path for path in SOURCE_DIR.rglob("*.xlsx") if is_source_file(path))
    for supplemental_dir in SUPPLEMENTAL_SOURCE_DIRS:
        if supplemental_dir.exists():
            source_files.extend(
                sorted(path for path in supplemental_dir.rglob("*.xlsx") if is_source_file(path))
            )
    source_files = list(dict.fromkeys(source_files))
    observations_by_key = {}
    skipped = []
    metric_fields = set()

    for path in source_files:
        year, month = parse_year_month(path)
        try:
            sheets = read_xlsx_sheets(path)
        except Exception as exc:
            skipped.append({"file": str(path), "reason": f"read error: {exc}"})
            continue

        # July 2020 is the only approved exception: its valid measurements
        # are stored on later worksheets and may have missing channels.
        sheets_to_scan = sheets if (year, month) == (2020, 7) else sheets[:1]
        parsed_in_file = 0
        for sheet_name, rows in sheets_to_scan:
            flat_preview = " ".join(str(cell) for row in rows[:10] for cell in row[:5]).lower()
            if "no data" in flat_preview:
                skipped.append({"file": f"{path} [{sheet_name}]", "reason": "NO DATA marker"})
                continue

            header_idx, headers = find_header(rows)
            if header_idx is None:
                continue

            date_idx = headers.index("Date(dd:mm:yyyy)")
            time_idx = next((idx for idx, header in enumerate(headers) if header.startswith("Time(")), None)
            site_idx = next((idx for idx, header in enumerate(headers) if header == "AERONET_Site_Name"), None)
            metric_indexes = {
                idx: header
                for idx, header in enumerate(headers)
                if header.startswith("AOD_") or "Angstrom_Exponent" in header
            }
            sheet_metrics = set(metric_indexes.values())
            metric_fields.update(sheet_metrics)

            for row in rows[header_idx + 1 :]:
                if date_idx >= len(row):
                    continue
                date_value = parse_date(row[date_idx], year, month)
                if not date_value:
                    continue
                time_value = parse_time(row[time_idx]) if time_idx is not None and time_idx < len(row) else ""
                site_value = str(row[site_idx]).strip() if site_idx is not None and site_idx < len(row) else ""
                record = {
                    "date": date_value.isoformat(),
                    "time": time_value,
                    "site": site_value,
                    "year": date_value.year,
                    "month": date_value.month,
                    "month_name": MONTH_NAMES[date_value.month],
                    "month_key": f"{date_value.year}-{date_value.month:02d}",
                    "season": SEASONS[date_value.month],
                    "season_year": date_value.year + 1 if date_value.month == 12 else date_value.year,
                    "source_file": str(path),
                    "source_files": [str(path)],
                }
                for idx, metric in metric_indexes.items():
                    record[metric] = to_float(row[idx] if idx < len(row) else None)
                if not any(record.get(metric) is not None for metric in sheet_metrics):
                    continue

                key = observation_key(record, sheet_metrics)
                existing = observations_by_key.get(key)
                if existing is None:
                    observations_by_key[key] = record
                else:
                    merge_observation(existing, record, sheet_metrics)
                parsed_in_file += 1

        if not parsed_in_file:
            skipped.append({"file": str(path), "reason": "No usable AOD/AE observations in any worksheet"})

    observations = sorted(
        observations_by_key.values(),
        key=lambda record: (record["date"], record["time"], record["site"]),
    )
    available_metrics = sorted(
        metric for metric in metric_fields if any(record.get(metric) is not None for record in observations)
    )
    return observations, available_metrics, source_files, skipped


def build_dashboard_html(payload):
    data_json = json.dumps(round_data(payload), ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AERONET AOD / AE Dashboard</title>
<style>
:root {{
  color-scheme: light;
  --ink: #1d2733;
  --muted: #647184;
  --line: #d8dee8;
  --paper: #f7f9fc;
  --panel: #ffffff;
  --aod: #1f78b4;
  --ae: #d95f02;
  --accent: #0f766e;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: var(--paper); }}
header {{ padding: 24px clamp(16px, 4vw, 44px) 14px; background: #ffffff; border-bottom: 1px solid var(--line); }}
h1 {{ margin: 0 0 8px; font-size: clamp(24px, 3vw, 38px); letter-spacing: 0; }}
p {{ margin: 0; color: var(--muted); line-height: 1.5; }}
main {{ padding: 18px clamp(12px, 3vw, 36px) 34px; }}
.toolbar {{ display: grid; grid-template-columns: repeat(3, minmax(150px, 1fr)); gap: 10px; margin-bottom: 16px; align-items: end; }}
label {{ display: grid; gap: 5px; font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase; }}
select, button {{ width: 100%; min-height: 38px; border: 1px solid var(--line); background: #fff; border-radius: 6px; color: var(--ink); padding: 8px 10px; font: inherit; }}
button {{ cursor: pointer; font-weight: 700; background: #eff6ff; color: #17426b; }}
.tabs {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 16px; }}
.tab {{ width: auto; min-height: 34px; padding: 7px 12px; background: #fff; color: var(--ink); }}
.tab.active {{ background: var(--ink); color: #fff; border-color: var(--ink); }}
.kpis {{ display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr)); gap: 10px; margin-bottom: 16px; }}
.card, .chart, .table-wrap {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }}
.card {{ padding: 14px; }}
.metric {{ font-size: 26px; font-weight: 800; margin-top: 4px; }}
.card span {{ color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }}
.grid {{ display: grid; grid-template-columns: 1fr; gap: 14px; }}
.chart {{ min-height: 360px; padding: 12px; overflow: hidden; }}
.chart h2 {{ margin: 0 0 2px; font-size: 18px; }}
.section-title {{ margin: 22px 0 10px; font-size: 20px; }}
.table-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }}
.metric-table h3 {{ margin: 0; padding: 12px 12px 0; font-size: 15px; }}
svg {{ width: 100%; height: 300px; display: block; }}
.axis {{ stroke: #9aa6b5; stroke-width: 1; }}
.line-aod {{ fill: none; stroke: var(--aod); stroke-width: 2.2; }}
.line-ae {{ fill: none; stroke: var(--ae); stroke-width: 2.2; }}
.marker-aod {{ fill: #ffffff; stroke: var(--aod); stroke-width: 2; }}
.marker-ae {{ fill: #ffffff; stroke: var(--ae); stroke-width: 2; }}
.err {{ stroke: #273341; stroke-width: 1.4; }}
.tick text, .legend, .note, .subtitle {{ fill: var(--muted); color: var(--muted); font-size: 11px; }}
.panel-letter {{ fill: var(--ink); font-size: 16px; font-weight: 800; }}
.table-wrap {{ overflow: auto; max-height: 420px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: right; white-space: nowrap; }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ position: sticky; top: 0; background: #fff; z-index: 1; color: var(--muted); }}
footer {{ padding: 16px clamp(16px, 4vw, 44px) 26px; color: var(--muted); font-size: 12px; }}
.hidden {{ display: none; }}
@media (max-width: 950px) {{ .toolbar, .kpis, .table-grid {{ grid-template-columns: 1fr 1fr; }} }}
@media (max-width: 640px) {{ .toolbar, .kpis, .grid, .table-grid {{ grid-template-columns: 1fr; }} .chart {{ min-height: 320px; }} }}
</style>
</head>
<body>
<header>
  <h1>AERONET AOD / AE Dashboard</h1>
  <p>Monthly, daily, month-of-year, and seasonal summaries from Level 1.5 daytime AOD/AE Excel files. Every AOD wavelength and every Angstrom exponent is shown as a separate graph and table; line markers show means and whiskers show standard deviation.</p>
</header>
<main>
  <section class="toolbar">
    <label>Year<select id="yearFilter"></select></label>
    <label>Month<select id="monthFilter"></select></label>
    <label>Season<select id="seasonFilter"></select></label>
  </section>
  <nav class="tabs">
    <button class="tab active" data-view="overview">Overview</button>
    <button class="tab" data-view="daily">Daily</button>
    <button class="tab" data-view="monthName">Each Month</button>
    <button class="tab" data-view="seasons">Seasons</button>
  </nav>
  <section class="kpis" id="kpis"></section>
  <h2 class="section-title" id="chartSectionTitle"></h2>
  <section class="grid" id="chartGrid"></section>
  <h2 class="section-title">Separate Metric Tables</h2>
  <section class="table-grid" id="tableGrid"></section>
</main>
<footer id="methodology"></footer>
<script id="dashboard-data" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('dashboard-data').textContent);
const state = {{
  view: 'overview',
  selectedMonths: parseRequestedMonths(),
  selectedYears: parseRequestedYears(),
  selectedPeriods: parseRequestedPeriods(),
}};
const fmt = value => value === null || value === undefined || Number.isNaN(value) ? '' : Number(value).toFixed(3);
const shortFmt = value => value === null || value === undefined || Number.isNaN(value) ? 'n/a' : Number(value).toFixed(3);

function parseRequestedMonths() {{
  const params = new URLSearchParams(window.location.search);
  const raw = params.get('months') || params.get('month');
  if (!raw || raw.toLowerCase() === 'all') return new Set(DATA.months.map(item => Number(item.month)));
  const allowed = new Set(DATA.months.map(item => Number(item.month)));
  const values = raw.split(',')
    .map(part => Number(part.trim()))
    .filter(value => Number.isInteger(value) && allowed.has(value));
  return new Set(values.length ? values : DATA.months.map(item => Number(item.month)));
}}

function parseRequestedYears() {{
  const params = new URLSearchParams(window.location.search);
  const raw = params.get('years') || params.get('year');
  if (!raw || raw.toLowerCase() === 'all') return new Set(DATA.years.map(Number));
  const allowed = new Set(DATA.years.map(Number));
  const values = raw.split(',')
    .map(part => Number(part.trim()))
    .filter(value => Number.isInteger(value) && allowed.has(value));
  return new Set(values.length ? values : DATA.years.map(Number));
}}

function availablePeriods() {{
  return Array.from(new Set(DATA.daily.map(row => String(row.date).slice(0, 7)))).sort();
}}

function parseRequestedPeriods() {{
  const params = new URLSearchParams(window.location.search);
  if (!params.has('periods')) return null;
  const allowed = new Set(availablePeriods());
  const values = (params.get('periods') || '').split(',')
    .map(part => part.trim())
    .filter(value => allowed.has(value));
  return new Set(values);
}}

function periodAllowed(year, month) {{
  if (!state.selectedPeriods) return true;
  return state.selectedPeriods.has(`${{year}}-${{String(month).padStart(2, '0')}}`);
}}

function monthAllowed(month) {{
  const value = Number(month);
  if (!state.selectedMonths.has(value)) return false;
  if (!state.selectedPeriods) return true;
  return Array.from(state.selectedPeriods).some(period => Number(period.slice(5, 7)) === value);
}}

function yearAllowed(year) {{
  const value = Number(year);
  if (!state.selectedYears.has(value)) return false;
  if (!state.selectedPeriods) return true;
  return Array.from(state.selectedPeriods).some(period => Number(period.slice(0, 4)) === value);
}}

function monthsForSelection(monthValue) {{
  if (monthValue === 'all') return DATA.months.map(item => Number(item.month)).filter(monthAllowed);
  const value = Number(monthValue);
  return monthAllowed(value) ? [value] : [];
}}

function yearsForSelection(yearValue) {{
  if (yearValue === 'all') return DATA.years.map(Number).filter(yearAllowed);
  const value = Number(yearValue);
  return yearAllowed(value) ? [value] : [];
}}

function selectedMonthNames() {{
  if (state.selectedMonths.size === DATA.months.length) return 'all months';
  return DATA.months
    .filter(item => state.selectedMonths.has(Number(item.month)))
    .map(item => item.name.slice(0, 3))
    .join(', ');
}}

function selectedYearNames() {{
  if (state.selectedYears.size === DATA.years.length) return 'all years';
  return DATA.years
    .filter(value => state.selectedYears.has(Number(value)))
    .join(', ');
}}

function selectionNames() {{
  if (state.selectedPeriods) {{
    const selected = Array.from(state.selectedPeriods).sort();
    if (!selected.length) return 'no calendar months';
    if (selected.length <= 6) return selected.join(', ');
    return `${{selected.length}} selected calendar months`;
  }}
  return `${{selectedMonthNames()}}, ${{selectedYearNames()}}`;
}}

function option(select, value, label) {{
  const opt = document.createElement('option');
  opt.value = value;
  opt.textContent = label;
  select.appendChild(opt);
}}

function initControls() {{
  const year = document.getElementById('yearFilter');
  option(year, 'all', 'All years');
  DATA.years.forEach(value => option(year, value, value));
  if (state.selectedYears.size === 1) {{
    year.value = String(Array.from(state.selectedYears)[0]);
  }}
  Array.from(year.options).forEach(opt => {{
    if (opt.value !== 'all' && !yearAllowed(opt.value)) opt.disabled = true;
  }});

  const month = document.getElementById('monthFilter');
  option(month, 'all', 'All months');
  DATA.months.forEach(item => option(month, item.month, item.name));
  if (state.selectedMonths.size === 1) {{
    month.value = String(Array.from(state.selectedMonths)[0]);
  }}
  Array.from(month.options).forEach(opt => {{
    if (opt.value !== 'all' && !monthAllowed(opt.value)) opt.disabled = true;
  }});

  const season = document.getElementById('seasonFilter');
  option(season, 'all', 'All seasons');
  DATA.seasons.forEach(value => option(season, value, value));

  document.querySelectorAll('select').forEach(select => select.addEventListener('change', render));
  document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    state.view = tab.dataset.view;
    render();
  }}));
}}

function metricValue(row, metric, suffix) {{
  return row[`${{metric}}_${{suffix}}`];
}}

function meanOf(rows, metric) {{
  const vals = rows.map(row => metricValue(row, metric, 'mean')).filter(value => value !== null && value !== undefined);
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
}}

function sampleCountOf(rows, metric) {{
  return rows.reduce((sum, row) => sum + (metricValue(row, metric, 'n') || 0), 0);
}}

function filtered(records) {{
  const year = document.getElementById('yearFilter').value;
  const month = document.getElementById('monthFilter').value;
  const season = document.getElementById('seasonFilter').value;
  return records.filter(row => {{
    const rowYear = row.year || row.season_year;
    if (rowYear !== undefined && !yearAllowed(rowYear)) return false;
    if (row.year !== undefined && row.month !== undefined && !periodAllowed(row.year, row.month)) return false;
    if (year !== 'all' && (row.year !== undefined || row.season_year !== undefined) && String(row.year || row.season_year) !== year) return false;
    if (row.month !== undefined && !monthAllowed(row.month)) return false;
    if (month !== 'all' && row.month !== undefined && String(row.month) !== month) return false;
    if (season !== 'all' && row.season !== undefined && row.season !== season) return false;
    return true;
  }});
}}

const monthlyByKey = new Map(DATA.monthly.map(row => [row.month_key, row]));
const dailyByDate = new Map(DATA.daily.map(row => [row.date, row]));

function monthName(month) {{
  const match = DATA.months.find(item => Number(item.month) === Number(month));
  return match ? match.name : '';
}}

function monthKey(year, month) {{
  return `${{year}}-${{String(month).padStart(2, '0')}}`;
}}

function dateKey(year, month, day) {{
  return `${{monthKey(year, month)}}-${{String(day).padStart(2, '0')}}`;
}}

function seasonForMonth(month) {{
  const m = Number(month);
  if (m === 12 || m === 1 || m === 2) return 'Winter';
  if (m >= 3 && m <= 5) return 'Spring';
  if (m >= 6 && m <= 8) return 'Summer';
  return 'Autumn';
}}

function seasonYearForMonth(year, month) {{
  return Number(month) === 12 ? Number(year) + 1 : Number(year);
}}

function daysInMonth(year, month) {{
  return new Date(Number(year), Number(month), 0).getDate();
}}

function calendarMonthlyRows() {{
  const yearValue = document.getElementById('yearFilter').value;
  const monthValue = document.getElementById('monthFilter').value;
  const seasonValue = document.getElementById('seasonFilter').value;
  const years = yearsForSelection(yearValue);
  const months = monthsForSelection(monthValue);
  const rows = [];
  years.forEach(year => {{
    months.forEach(month => {{
      if (!periodAllowed(year, month)) return;
      const season = seasonForMonth(month);
      if (seasonValue !== 'all' && season !== seasonValue) return;
      const key = monthKey(year, month);
      const source = monthlyByKey.get(key);
      const row = source ? {{ ...source }} : {{
        year,
        month,
        month_name: monthName(month),
        month_key: key,
        season,
        season_year: seasonYearForMonth(year, month),
      }};
      row.label = key;
      rows.push(row);
    }});
  }});
  return rows;
}}

function calendarDailyRows() {{
  const yearValue = document.getElementById('yearFilter').value;
  const monthValue = document.getElementById('monthFilter').value;
  const seasonValue = document.getElementById('seasonFilter').value;
  if (yearValue === 'all' && monthValue === 'all') return labelled(filtered(DATA.daily), 'daily');

  const years = yearsForSelection(yearValue);
  const months = monthsForSelection(monthValue);
  const rows = [];
  years.forEach(year => {{
    months.forEach(month => {{
      if (!periodAllowed(year, month)) return;
      const season = seasonForMonth(month);
      if (seasonValue !== 'all' && season !== seasonValue) return;
      for (let day = 1; day <= daysInMonth(year, month); day += 1) {{
        const key = dateKey(year, month, day);
        const source = dailyByDate.get(key);
        const row = source ? {{ ...source }} : {{
          date: key,
          year,
          month,
          month_name: monthName(month),
          season,
          season_year: seasonYearForMonth(year, month),
          day,
        }};
        row.label = yearValue === 'all' ? `${{year}}-${{String(day).padStart(2, '0')}}` : String(day).padStart(2, '0');
        rows.push(row);
      }}
    }});
  }});
  return rows;
}}

function allMetrics() {{
  return [
    ...DATA.aod_metrics.map(metric => ({{ metric, kind: 'aod' }})),
    ...DATA.ae_metrics.map(metric => ({{ metric, kind: 'ae' }})),
  ];
}}

function makeKpis(rows) {{
  const files = DATA.source_files;
  const html = [
    ['Source files', files, 'daytime AOD/AE workbooks'],
    ['Observations', DATA.observation_count, 'valid measurement rows'],
    ['Displayed groups', rows.length, 'rows in the current view'],
    ['Separate metrics', allMetrics().length, `${{DATA.aod_metrics.length}} AOD + ${{DATA.ae_metrics.length}} AE`],
  ].map(item => `<article class="card"><span>${{item[0]}}</span><div class="metric">${{item[1]}}</div><p>${{item[2]}}</p></article>`).join('');
  document.getElementById('kpis').innerHTML = html;
}}

function metricLabel(metric) {{
  return metric.replace('AOD_', 'AOD ').replace(/_/g, ' ').replace('Angstrom Exponent', 'Ang. Exp.');
}}

function niceTicks(maxValue) {{
  const max = Math.max(0.01, maxValue);
  const rawStep = max / 5;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const residual = rawStep / magnitude;
  const niceResidual = residual <= 1 ? 1 : residual <= 2 ? 2 : residual <= 5 ? 5 : 10;
  const step = niceResidual * magnitude;
  const axisMax = Math.ceil(max / step) * step;
  const ticks = [];
  for (let value = 0; value <= axisMax + step / 2; value += step) ticks.push(value);
  return {{ ticks, axisMax }};
}}

function lineChart(containerRef, rows, labelField, metric, metricKind, panelLetter, maxPoints = 72) {{
  const container = typeof containerRef === 'string' ? document.getElementById(containerRef) : containerRef;
  const subset = rows.slice(Math.max(0, rows.length - maxPoints));
  const observed = subset.filter(row => metricValue(row, metric, 'mean') !== null && metricValue(row, metric, 'mean') !== undefined);
  const w = 980, h = 300, margin = {{ top: 22, right: 30, bottom: 72, left: 64 }};
  const innerW = w - margin.left - margin.right;
  const innerH = h - margin.top - margin.bottom;
  if (!subset.length || !observed.length) {{
    container.innerHTML = '<p class="note">No matching records.</p>';
    return;
  }}

  const maxObserved = Math.max(...observed.map(row => (metricValue(row, metric, 'mean') || 0) + (metricValue(row, metric, 'std') || 0)));
  const scale = niceTicks(maxObserved * 1.08);
  const y = value => margin.top + innerH - (Math.max(0, value) / scale.axisMax) * innerH;
  const x = index => subset.length === 1 ? margin.left + innerW / 2 : margin.left + (index / (subset.length - 1)) * innerW;
  const clsLine = metricKind === 'aod' ? 'line-aod' : 'line-ae';
  const clsMarker = metricKind === 'aod' ? 'marker-aod' : 'marker-ae';
  const yTitle = metricKind === 'aod' ? metricLabel(metric) : 'Ang. Exp.';
  const stepLabel = Math.max(1, Math.ceil(subset.length / 14));
  const segments = [];
  let currentSegment = [];
  subset.forEach((row, index) => {{
    const mean = metricValue(row, metric, 'mean');
    if (mean === null || mean === undefined) {{
      if (currentSegment.length) segments.push(currentSegment);
      currentSegment = [];
      return;
    }}
    currentSegment.push([x(index), y(mean)]);
  }});
  if (currentSegment.length) segments.push(currentSegment);

  let svg = `<svg viewBox="0 0 ${{w}} ${{h}}" role="img" aria-label="${{metricLabel(metric)}} line chart with standard deviation error bars">`;
  svg += `<text x="${{margin.left - 44}}" y="${{margin.top - 3}}" class="panel-letter">${{panelLetter}}</text>`;
  svg += `<text x="${{margin.left}}" y="${{margin.top - 6}}" class="subtitle">${{metricLabel(metric)}} means with standard deviation</text>`;
  scale.ticks.forEach(t => {{
    const ty = y(t);
    svg += `<line x1="${{margin.left}}" x2="${{w - margin.right}}" y1="${{ty}}" y2="${{ty}}" stroke="#edf1f6"/>`;
    svg += `<text x="${{margin.left - 8}}" y="${{ty + 4}}" text-anchor="end" class="tick">${{t.toFixed(t < 1 ? 2 : 1)}}</text>`;
  }});
  svg += `<line x1="${{margin.left}}" x2="${{margin.left}}" y1="${{margin.top}}" y2="${{h - margin.bottom}}" class="axis"/>`;
  svg += `<line x1="${{margin.left}}" x2="${{w - margin.right}}" y1="${{h - margin.bottom}}" y2="${{h - margin.bottom}}" class="axis"/>`;
  svg += `<text x="18" y="${{margin.top + innerH / 2}}" transform="rotate(-90 18 ${{margin.top + innerH / 2}})" class="legend">${{yTitle}}</text>`;
  segments.forEach(segment => {{
    const path = segment.map((point, index) => `${{index === 0 ? 'M' : 'L'}} ${{point[0].toFixed(1)}} ${{point[1].toFixed(1)}}`).join(' ');
    svg += `<path d="${{path}}" class="${{clsLine}}"/>`;
  }});
  subset.forEach((row, index) => {{
    const label = row[labelField] || row.label || '';
    const cx = x(index);
    if (index % stepLabel === 0 || subset.length <= 14) {{
      svg += `<text x="${{cx}}" y="${{h - margin.bottom + 18}}" text-anchor="end" transform="rotate(-45 ${{cx}} ${{h - margin.bottom + 18}})" class="tick">${{label}}</text>`;
    }}
    const mean = metricValue(row, metric, 'mean');
    if (mean === null || mean === undefined) return;
    const std = metricValue(row, metric, 'std') || 0;
    const cy = y(mean);
    const yHigh = y(mean + std);
    const yLow = y(Math.max(0, mean - std));
    svg += `<line x1="${{cx}}" x2="${{cx}}" y1="${{yHigh}}" y2="${{yLow}}" class="err"/>`;
    svg += `<line x1="${{cx - 5}}" x2="${{cx + 5}}" y1="${{yHigh}}" y2="${{yHigh}}" class="err"/>`;
    svg += `<line x1="${{cx - 5}}" x2="${{cx + 5}}" y1="${{yLow}}" y2="${{yLow}}" class="err"/>`;
    svg += `<circle cx="${{cx}}" cy="${{cy}}" r="4.2" class="${{clsMarker}}"><title>${{label}}\\n${{metric}} mean ${{fmt(mean)}} sd ${{fmt(std)}}</title></circle>`;
  }});
  svg += `</svg>`;
  container.innerHTML = svg;
}}

function metricTableHtml(rows, metric, labelField) {{
  const head = ['Group', 'Mean', 'Std. dev.', 'Sample count'];
  const body = rows.map(row => `<tr><td>${{row[labelField] || row.label || ''}}</td><td>${{fmt(metricValue(row, metric, 'mean'))}}</td><td>${{fmt(metricValue(row, metric, 'std'))}}</td><td>${{metricValue(row, metric, 'n') || 0}}</td></tr>`).join('');
  return `<article class="table-wrap metric-table"><h3>${{metricLabel(metric)}}</h3><table><thead><tr>${{head.map(h => `<th>${{h}}</th>`).join('')}}</tr></thead><tbody>${{body}}</tbody></table></article>`;
}}

function renderTables(rows, labelField) {{
  document.getElementById('tableGrid').innerHTML = allMetrics()
    .map(item => metricTableHtml(rows, item.metric, labelField))
    .join('');
}}

function renderCharts(rows, labelField, maxPoints, viewTitle) {{
  const grid = document.getElementById('chartGrid');
  const metrics = allMetrics();
  grid.innerHTML = metrics
    .map((item, index) => `<article class="chart"><h2>${{index + 1}}. ${{metricLabel(item.metric)}} - ${{viewTitle}}</h2><div id="chart-${{index}}"></div></article>`)
    .join('');
  metrics.forEach((item, index) => {{
    const letter = item.kind === 'aod' ? `a${{DATA.aod_metrics.indexOf(item.metric) + 1}}` : `b${{DATA.ae_metrics.indexOf(item.metric) + 1}}`;
    lineChart(`chart-${{index}}`, rows, labelField, item.metric, item.kind, letter, maxPoints);
  }});
}}

function labelled(rows, kind) {{
  return rows.map(row => {{
    const clone = {{ ...row }};
    if (kind === 'month') clone.label = `${{row.year}}-${{String(row.month).padStart(2, '0')}}`;
    if (kind === 'daily') clone.label = row.date;
    if (kind === 'monthName') clone.label = row.month_name;
    if (kind === 'season') clone.label = row.season;
    if (kind === 'seasonYear') clone.label = `${{row.season_year}} ${{row.season}}`;
    return clone;
  }});
}}

function summarizeGroupRows(rows, keys, kind) {{
  const groups = new Map();
  rows.forEach(row => {{
    const key = keys.map(field => row[field]).join('|');
    if (!groups.has(key)) {{
      const base = Object.fromEntries(keys.map(field => [field, row[field]]));
      groups.set(key, {{ ...base, _rows: [] }});
    }}
    groups.get(key)._rows.push(row);
  }});
  return labelled(Array.from(groups.values()).map(group => {{
    const sourceRows = group._rows;
    const output = {{ ...group }};
    delete output._rows;
    allMetrics().forEach(item => {{
      const means = sourceRows
        .map(row => metricValue(row, item.metric, 'mean'))
        .filter(value => value !== null && value !== undefined && !Number.isNaN(value));
      const mean = means.length ? means.reduce((sum, value) => sum + value, 0) / means.length : null;
      const variance = means.length > 1
        ? means.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / (means.length - 1)
        : 0;
      output[`${{item.metric}}_mean`] = mean;
      output[`${{item.metric}}_std`] = means.length ? Math.sqrt(variance) : null;
      output[`${{item.metric}}_n`] = sourceRows.reduce((sum, row) => sum + (metricValue(row, item.metric, 'n') || 0), 0);
    }});
    return output;
  }}), kind);
}}

function render() {{
  const monthValue = document.getElementById('monthFilter').value;
  const seasonValue = document.getElementById('seasonFilter').value;
  const yearValue = document.getElementById('yearFilter').value;
  let rows, labelField, maxPoints, viewTitle;
  if (state.view === 'daily') {{
    rows = calendarDailyRows();
    labelField = 'label';
    maxPoints = rows.length || 1;
    if (yearValue !== 'all' && monthValue !== 'all') {{
      viewTitle = `${{monthName(monthValue)}} ${{yearValue}} daily means`;
    }} else if (yearValue !== 'all') {{
      viewTitle = `${{yearValue}} daily means`;
    }} else if (monthValue !== 'all') {{
      viewTitle = `${{monthName(monthValue)}} daily means by year`;
    }} else {{
      viewTitle = 'Daily means';
    }}
  }} else if (state.view === 'monthName') {{
    if (monthValue === 'all') {{
      rows = summarizeGroupRows(filtered(DATA.daily), ['month', 'month_name'], 'monthName');
      viewTitle = `Multi-year monthly means - ${{selectionNames()}}`;
      maxPoints = 12;
    }} else {{
      rows = calendarMonthlyRows();
      viewTitle = `${{monthName(monthValue)}} in each year`;
      maxPoints = rows.length || 1;
    }}
    labelField = 'label';
  }} else if (state.view === 'seasons') {{
    if (seasonValue === 'all' && yearValue === 'all') {{
      rows = summarizeGroupRows(filtered(DATA.daily), ['season'], 'season');
      viewTitle = `Multi-year seasonal means - ${{selectionNames()}}`;
      maxPoints = 4;
    }} else {{
      rows = summarizeGroupRows(filtered(DATA.daily), ['season_year', 'season'], 'seasonYear');
      viewTitle = seasonValue === 'all' ? 'Seasons in each year' : `${{seasonValue}} in each year`;
      maxPoints = 32;
    }}
    labelField = 'label';
  }} else {{
    rows = calendarMonthlyRows();
    labelField = 'label';
    maxPoints = rows.length || 1;
    viewTitle = 'Monthly means';
  }}
  document.getElementById('chartSectionTitle').textContent = `Separate AOD and AE Graphs - ${{viewTitle}}`;
  makeKpis(rows);
  renderCharts(rows, labelField, maxPoints, viewTitle);
  renderTables(rows, labelField);
}}

document.getElementById('methodology').textContent = `Source: ${{DATA.source_dir}}. Excludes LUNAR files and files marked NO DATA. Generated ${{DATA.generated_at}}. Launcher selector: ${{selectionNames()}}. CSV exports are saved beside this dashboard in aeronet_summary_data.`;
initControls();
render();
</script>
</body>
</html>
"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    observations, metric_fields, source_files, skipped = scan_records()

    aod_metrics = [metric for metric in metric_fields if metric.startswith("AOD_")]
    ae_metrics = [metric for metric in metric_fields if "Angstrom_Exponent" in metric]
    default_aod = "AOD_500nm" if "AOD_500nm" in aod_metrics else (aod_metrics[0] if aod_metrics else "")
    default_ae = "440-870_Angstrom_Exponent" if "440-870_Angstrom_Exponent" in ae_metrics else (ae_metrics[0] if ae_metrics else "")

    daily = make_summary_records(observations, ["date", "year", "month", "month_name", "season", "season_year"], metric_fields)
    monthly = make_summary_records(observations, ["year", "month", "month_name", "month_key", "season", "season_year"], metric_fields)
    month_name = make_summary_records(observations, ["month", "month_name"], metric_fields)
    season = make_summary_records(observations, ["season"], metric_fields)
    season_year = make_summary_records(observations, ["season_year", "season"], metric_fields)

    month_name.sort(key=lambda row: row["month"])
    season.sort(key=lambda row: SEASON_ORDER.get(row["season"], 99))
    season_year.sort(key=lambda row: (row["season_year"], SEASON_ORDER.get(row["season"], 99)))

    for row in monthly:
        row["label"] = row["month_key"]
    for row in daily:
        row["label"] = row["date"]
    for row in month_name:
        row["label"] = row["month_name"]
    for row in season:
        row["label"] = row["season"]
    for row in season_year:
        row["label"] = f"{row['season_year']} {row['season']}"

    payload = {
        "source_dir": str(SOURCE_DIR),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_files": len(source_files),
        "observation_count": len(observations),
        "default_aod": default_aod,
        "default_ae": default_ae,
        "aod_metrics": aod_metrics,
        "ae_metrics": ae_metrics,
        "years": sorted({record["year"] for record in observations}),
        "months": [{"month": idx, "name": MONTH_NAMES[idx]} for idx in range(1, 13)],
        "seasons": ["Winter", "Spring", "Summer", "Autumn"],
        "daily": daily,
        "monthly": monthly,
        "month_name": month_name,
        "season": season,
        "season_year": season_year,
        "skipped": skipped,
    }

    (DATA_DIR / "aeronet_dashboard_data.json").write_text(json.dumps(round_data(payload), indent=2), encoding="utf-8")
    write_csv(DATA_DIR / "daily_summary.csv", round_data(daily))
    write_csv(DATA_DIR / "monthly_summary.csv", round_data(monthly))
    write_csv(DATA_DIR / "month_name_summary.csv", round_data(month_name))
    write_csv(DATA_DIR / "season_summary.csv", round_data(season))
    write_csv(DATA_DIR / "season_year_summary.csv", round_data(season_year))
    write_csv(DATA_DIR / "skipped_files.csv", skipped)
    APP_PATH.write_text(build_dashboard_html(payload), encoding="utf-8")

    print(f"Parsed observations: {len(observations)}")
    print(f"Source files matched: {len(source_files)}")
    print(f"Skipped files: {len(skipped)}")
    print(f"Dashboard: {APP_PATH}")
    print(f"Data exports: {DATA_DIR}")


if __name__ == "__main__":
    main()
