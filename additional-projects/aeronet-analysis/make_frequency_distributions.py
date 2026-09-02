import csv
import json
import math
import re
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import aeronet_dashboard_generator as aeronet


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "aeronet_summary_data"
OUT_PATH = ROOT / "AOD_AE_frequency_distributions_2020-2026.html"
CACHE_PATH = DATA_DIR / "frequency_distribution_data.json"
CSV_PATH = DATA_DIR / "frequency_distributions.csv"
ANNUAL_CSV_PATH = DATA_DIR / "annual_AOD500_AE380-500_summary.csv"
INDIVIDUAL_STATS_CSV_PATH = DATA_DIR / "individual_AOD_AE_descriptive_statistics.csv"

BIN_WIDTH = 0.01
PERCENT_DIGITS = 4
EXCLUDED_DATES = {"2022-10-21"}
ANNUAL_METRICS = ["AOD_500nm", "380-500_Angstrom_Exponent"]
MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def is_number(value):
    return isinstance(value, (int, float)) and not math.isnan(value)


def metric_family(metric):
    return "AOD" if metric.startswith("AOD_") else "AE"


def metric_label(metric):
    if metric.startswith("AOD_"):
        match = re.search(r"AOD_(\d+)nm", metric)
        return f"AOD {match.group(1)} nm" if match else metric
    match = re.search(r"(\d+)-(\d+)_Angstrom_Exponent", metric)
    return f"AE {match.group(1)}-{match.group(2)} nm" if match else metric


def metric_order(metric):
    if metric.startswith("AOD_"):
        match = re.search(r"AOD_(\d+)nm", metric)
        return int(match.group(1)) if match else 9999
    match = re.search(r"(\d+)-(\d+)_Angstrom_Exponent", metric)
    return (int(match.group(1)), int(match.group(2))) if match else (9999, 9999)


def build_histogram(values):
    clean = [float(value) for value in values if is_number(value)]
    bins = defaultdict(int)
    for value in clean:
        idx = math.floor((value / BIN_WIDTH) + 1e-12)
        bins[idx] += 1
    ordered = sorted([[idx, count] for idx, count in bins.items()])
    return {
        "n": len(clean),
        "min": min(clean) if clean else None,
        "max": max(clean) if clean else None,
        "bins": ordered,
    }


def summarize_values(values):
    clean = [float(value) for value in values if is_number(value)]
    if not clean:
        return {"mean": None, "std": None, "n": 0}
    return {
        "mean": sum(clean) / len(clean),
        "std": statistics.stdev(clean) if len(clean) > 1 else 0,
        "n": len(clean),
    }


def descriptive_statistics(values):
    clean = sorted(float(value) for value in values if is_number(value))
    if not clean:
        return {
            "n": 0,
            "mean": None,
            "std": None,
            "median": None,
            "min": None,
            "max": None,
            "skewness": None,
        }
    mean = statistics.fmean(clean)
    std = statistics.stdev(clean) if len(clean) > 1 else 0
    skewness = None
    if len(clean) >= 3:
        skewness = 0 if std == 0 else (
            len(clean) / ((len(clean) - 1) * (len(clean) - 2))
            * sum(((value - mean) / std) ** 3 for value in clean)
        )
    return {
        "n": len(clean),
        "mean": mean,
        "std": std,
        "median": statistics.median(clean),
        "min": clean[0],
        "max": clean[-1],
        "skewness": skewness,
    }


def collect_values(observations, metric_fields):
    all_values = {metric: [] for metric in metric_fields}
    daily_lists = defaultdict(lambda: defaultdict(list))

    filtered = []
    for record in observations:
        if record["date"] in EXCLUDED_DATES:
            continue
        filtered.append(record)
        for metric in metric_fields:
            value = record.get(metric)
            if is_number(value):
                all_values[metric].append(value)
                daily_lists[record["date"]][metric].append(value)

    daily_values = {metric: [] for metric in metric_fields}
    daily_records = []
    for date in sorted(daily_lists):
        metric_map = daily_lists[date]
        daily_record = {"date": date, "year": int(date[:4]), "month": int(date[5:7])}
        for metric, values in metric_map.items():
            if values:
                mean_value = sum(values) / len(values)
                daily_values[metric].append(mean_value)
                daily_record[metric] = mean_value
        daily_records.append(daily_record)

    return filtered, all_values, daily_values, daily_records


def compact_rows(records, metric_fields):
    rows = []
    for record in records:
        date = record["date"]
        compact = [int(date[:4]), int(date[5:7])]
        for metric in metric_fields:
            value = record.get(metric)
            compact.append(round(float(value), 6) if is_number(value) else None)
        rows.append(compact)
    return rows


def build_annual_summary(records):
    annual = {}
    for metric in ANNUAL_METRICS:
        by_year = defaultdict(list)
        all_values = []
        for record in records:
            value = record.get(metric)
            if is_number(value):
                by_year[record["year"]].append(value)
                all_values.append(value)

        rows = []
        for year in sorted(by_year):
            stats = summarize_values(by_year[year])
            rows.append(
                {
                    "period": str(year),
                    "year": year,
                    "mean": stats["mean"],
                    "std": stats["std"],
                    "n": stats["n"],
                }
            )
        stats = summarize_values(all_values)
        rows.append(
            {
                "period": "All years",
                "year": None,
                "mean": stats["mean"],
                "std": stats["std"],
                "n": stats["n"],
            }
        )
        annual[metric] = {"label": metric_label(metric), "rows": rows}

    return annual


def build_payload():
    observations, metric_fields, source_files, skipped = aeronet.scan_records()
    aod_metrics = sorted(
        [metric for metric in metric_fields if metric.startswith("AOD_")],
        key=metric_order,
    )
    ae_metrics = sorted(
        [metric for metric in metric_fields if "Angstrom_Exponent" in metric],
        key=metric_order,
    )
    metric_fields = aod_metrics + ae_metrics
    filtered, all_values, daily_values, daily_records = collect_values(observations, metric_fields)

    metrics = {}
    for metric in metric_fields:
        metrics[metric] = {
            "family": metric_family(metric),
            "label": metric_label(metric),
            "order": metric_order(metric),
            "all": build_histogram(all_values[metric]),
            "daily": build_histogram(daily_values[metric]),
        }

    years = sorted({record["year"] for record in filtered})
    dates = sorted({record["date"] for record in filtered})
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_dir": str(aeronet.SOURCE_DIR),
        "source_files": len(source_files),
        "skipped_files": len(skipped),
        "excluded_dates": sorted(EXCLUDED_DATES),
        "bin_width": BIN_WIDTH,
        "observation_count": len(filtered),
        "daily_count": len(dates),
        "years": years,
        "months": [{"number": index + 1, "name": name} for index, name in enumerate(MONTH_NAMES)],
        "date_range": [dates[0], dates[-1]] if dates else ["", ""],
        "aod_metrics": aod_metrics,
        "ae_metrics": ae_metrics,
        "raw_metric_fields": metric_fields,
        "raw": {
            "all": compact_rows(filtered, metric_fields),
            "daily": compact_rows(daily_records, metric_fields),
        },
        "metrics": metrics,
        "annual": {
            "daily": build_annual_summary(daily_records),
            "individual": build_annual_summary(filtered),
        },
        "individual_descriptive": {
            metric: descriptive_statistics(all_values[metric]) for metric in metric_fields
        },
    }
    return payload


def write_csv_export(payload):
    rows = []
    width = payload["bin_width"]
    for metric, info in payload["metrics"].items():
        for grain in ("all", "daily"):
            hist = info[grain]
            total = hist["n"] or 0
            cumulative = 0
            for idx, count in hist["bins"]:
                cumulative += count
                rows.append(
                    {
                        "family": info["family"],
                        "metric": metric,
                        "label": info["label"],
                        "grain": "all_measurements" if grain == "all" else "daily_means",
                        "bin_start": round(idx * width, 6),
                        "bin_end": round((idx + 1) * width, 6),
                        "frequency_count": count,
                        "relative_frequency_percent": f"{((count / total * 100) if total else 0):.{PERCENT_DIGITS}f}",
                        "cumulative_frequency_count": cumulative,
                        "cumulative_percent": f"{((cumulative / total * 100) if total else 0):.{PERCENT_DIGITS}f}",
                        "n": total,
                    }
                )

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    annual_rows = []
    for basis, basis_data in payload["annual"].items():
        for metric, info in basis_data.items():
            for row in info["rows"]:
                annual_rows.append(
                    {
                        "basis": basis,
                        "metric": metric,
                        "label": info["label"],
                        "period": row["period"],
                        "mean": round(row["mean"], 6) if row["mean"] is not None else "",
                        "standard_deviation": round(row["std"], 6) if row["std"] is not None else "",
                        "n": row["n"],
                    }
                )
    with ANNUAL_CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(annual_rows[0].keys()) if annual_rows else [])
        if annual_rows:
            writer.writeheader()
            writer.writerows(annual_rows)

    individual_rows = []
    for metric in payload["raw_metric_fields"]:
        stats = payload["individual_descriptive"][metric]
        individual_rows.append(
            {
                "metric": metric,
                "label": payload["metrics"][metric]["label"],
                "n_individual_measurements": stats["n"],
                "mean": round(stats["mean"], 10) if stats["mean"] is not None else "",
                "standard_deviation": round(stats["std"], 10) if stats["std"] is not None else "",
                "median": round(stats["median"], 10) if stats["median"] is not None else "",
                "minimum": round(stats["min"], 10) if stats["min"] is not None else "",
                "maximum": round(stats["max"], 10) if stats["max"] is not None else "",
                "adjusted_fisher_pearson_skewness": round(stats["skewness"], 10)
                if stats["skewness"] is not None
                else "",
            }
        )
    with INDIVIDUAL_STATS_CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(individual_rows[0].keys()))
        writer.writeheader()
        writer.writerows(individual_rows)


def build_html(payload):
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    template = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AOD and AE Frequency Distributions</title>
<style>
:root {
  --ink: #182230;
  --muted: #5b6678;
  --line: #d8e0ea;
  --paper: #f6f8fb;
  --panel: #ffffff;
  --aod: #2f80bd;
  --aod-dark: #1c5f91;
  --ae: #d68432;
  --ae-dark: #a95f18;
  --focus: #0f766e;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: "Segoe UI", Arial, sans-serif;
}
header {
  padding: 20px clamp(16px, 3vw, 32px) 14px;
  background: var(--panel);
  border-bottom: 1px solid var(--line);
}
h1 {
  margin: 0 0 6px;
  font-size: clamp(24px, 3vw, 34px);
  line-height: 1.15;
  letter-spacing: 0;
}
p {
  margin: 0;
  color: var(--muted);
  line-height: 1.45;
}
main {
  padding: 16px clamp(12px, 3vw, 28px) 28px;
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 16px;
}
.toolbar, .plot-panel, .table-panel, .individual-panel, .annual-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.toolbar {
  align-self: start;
  padding: 14px;
}
.group {
  padding: 10px 0 14px;
  border-bottom: 1px solid var(--line);
}
.group:last-child { border-bottom: 0; padding-bottom: 0; }
.label {
  display: block;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.segmented {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.segmented.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
button {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  cursor: pointer;
}
button.active {
  border-color: var(--focus);
  background: #e9f5f2;
  color: #0a5b52;
  font-weight: 700;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.metric-grid button {
  text-align: left;
  padding: 7px 9px;
  font-size: 13px;
}
.period-groups {
  display: grid;
  gap: 8px;
}
.period-year {
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr);
  gap: 6px;
  align-items: stretch;
}
.period-year-toggle {
  background: #f3f6fa;
  font-weight: 700;
}
.period-months {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 5px;
}
.period-months button {
  min-height: 30px;
  padding: 4px 2px;
  font-size: 11px;
}
.period-months button:disabled {
  border-color: #e5e9ef;
  background: #f5f6f8;
  color: #a4adba;
  cursor: default;
}
.quick-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  margin-top: 6px;
}
.quick-row button {
  font-size: 12px;
}
.content {
  min-width: 0;
  display: grid;
  gap: 14px;
}
.plot-panel {
  min-width: 0;
  padding: 14px;
}
.plot-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
h2 {
  margin: 0;
  font-size: 20px;
  letter-spacing: 0;
}
.meta {
  color: var(--muted);
  font-size: 13px;
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 10px 0 12px;
}
.stat {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px 10px;
  min-width: 0;
}
.stat b {
  display: block;
  font-size: 18px;
  line-height: 1.2;
}
.stat span {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
.canvas-wrap {
  position: relative;
  width: 100%;
  height: min(56vh, 560px);
  min-height: 410px;
}
canvas {
  display: block;
  width: 100%;
  height: 100%;
}
.tooltip {
  position: absolute;
  z-index: 5;
  display: none;
  max-width: min(280px, calc(100% - 24px));
  padding: 9px 10px;
  border: 1px solid #b9c5d5;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 28px rgba(17, 24, 39, 0.16);
  color: var(--ink);
  font-size: 12px;
  line-height: 1.35;
  pointer-events: none;
}
.tooltip strong {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
}
.table-panel {
  min-width: 0;
  overflow: hidden;
}
.individual-panel {
  min-width: 0;
  overflow: hidden;
}
.individual-table-wrap {
  max-height: 460px;
  overflow: auto;
}
.annual-panel {
  position: relative;
  min-width: 0;
  overflow: hidden;
}
.annual-basis-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(130px, 1fr));
  gap: 6px;
  padding: 12px 14px 0;
}
.table-head {
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.table-wrap {
  max-height: 340px;
  overflow: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th, td {
  padding: 8px 10px;
  border-bottom: 1px solid #edf1f6;
  text-align: right;
  white-space: nowrap;
}
th:first-child, td:first-child { text-align: left; }
th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f9fbfd;
  color: var(--muted);
  font-size: 12px;
}
.annual-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 14px;
}
.annual-card {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
}
.annual-card h3 {
  margin: 0 0 3px;
  font-size: 16px;
  letter-spacing: 0;
}
.annual-card p {
  font-size: 12px;
}
.annual-canvas-wrap {
  width: 100%;
  height: 300px;
  margin-top: 8px;
}
.annual-canvas-wrap canvas {
  width: 100%;
  height: 100%;
}
.note {
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}
@media (max-width: 860px) {
  main { grid-template-columns: 1fr; }
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .individual-grid { grid-template-columns: 1fr; }
  .individual-metric + .individual-metric { border-left: 0; border-top: 1px solid var(--line); }
  .annual-grid { grid-template-columns: 1fr; }
  .canvas-wrap { min-height: 360px; height: 52vh; }
}
</style>
</head>
<body>
<header>
  <h1>AOD and AE frequency distributions by wavelength</h1>
  <p>Rectangular histograms with bin width 0.01. Switch between all individual measurements and daily means, choose exact calendar months before calculations, and view frequency count, relative frequency percent, or cumulative percent.</p>
</header>
<main>
  <aside class="toolbar">
    <section class="group">
      <span class="label">Metric family</span>
      <div class="segmented" id="familyControls"></div>
    </section>
    <section class="group">
      <span class="label">Data grain</span>
      <div class="segmented" id="grainControls"></div>
    </section>
    <section class="group">
      <span class="label">Y value</span>
      <div class="segmented three" id="modeControls"></div>
    </section>
    <section class="group">
      <span class="label">Individual calendar months</span>
      <div class="period-groups" id="periodControls"></div>
      <div class="quick-row">
        <button id="allPeriodsBtn" type="button">Keep all</button>
        <button id="clearPeriodsBtn" type="button">Remove all</button>
      </div>
    </section>
    <section class="group">
      <span class="label">Wavelength / pair</span>
      <div class="metric-grid" id="metricControls"></div>
    </section>
    <p class="note" id="sourceNote"></p>
  </aside>
  <section class="content">
    <section class="plot-panel">
      <div class="plot-head">
        <div>
          <h2 id="chartTitle"></h2>
          <p class="meta" id="chartSubtitle"></p>
        </div>
      </div>
      <div class="stats" id="stats"></div>
      <div class="canvas-wrap" id="canvasWrap">
        <canvas id="histogram" aria-label="Histogram"></canvas>
        <div class="tooltip" id="histTooltip"></div>
      </div>
    </section>
    <section class="table-panel">
      <div class="table-head">
        <strong>Frequency table</strong>
        <span class="meta" id="tableMeta"></span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Bin</th>
              <th>Start</th>
              <th>End</th>
              <th>Frequency count</th>
              <th>Relative frequency %</th>
              <th>Cumulative %</th>
            </tr>
          </thead>
          <tbody id="freqRows"></tbody>
        </table>
      </div>
    </section>
    <section class="individual-panel" id="individual-statistics">
      <div class="table-head">
        <strong>Individual-measurement descriptive statistics for every AOD and AE channel</strong>
        <span class="meta" id="individualStatsMeta"></span>
      </div>
      <div class="individual-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              <th>n measurements</th>
              <th>Mean</th>
              <th>Standard deviation</th>
              <th>Median</th>
              <th>Minimum</th>
              <th>Maximum</th>
              <th>Skewness</th>
            </tr>
          </thead>
          <tbody id="individualStatsRows"></tbody>
        </table>
      </div>
      <p class="note" style="padding: 0 14px 14px; margin-top: 0;">Skewness is the adjusted Fisher-Pearson sample skewness. Values use individual observations from the selected calendar months.</p>
    </section>
    <section class="annual-panel" id="annual-statistics">
      <div class="table-head">
        <strong>AOD 500 and AE 380/500 annual mean values</strong>
        <span class="meta" id="annualMeta">Daily-mean basis, selected calendar months, excluding listed dates</span>
      </div>
      <div class="annual-basis-controls">
        <button id="annualDailyBtn" class="active" type="button">Daily means</button>
        <button id="annualIndividualBtn" type="button">Individual measurements</button>
      </div>
      <div class="annual-grid">
        <div class="annual-card">
          <h3>AOD 500 nm</h3>
          <p id="annualAodCaption">Mean annual AOD 500 from daily means for the selected calendar months. Whiskers show mean &plusmn; standard deviation.</p>
          <div class="annual-canvas-wrap"><canvas id="annualAodCanvas" aria-label="Annual AOD 500 means"></canvas></div>
        </div>
        <div class="annual-card">
          <h3>AE 380/500</h3>
          <p id="annualAeCaption">Mean annual Angstrom exponent 380/500 from daily means for the selected calendar months. Whiskers show mean &plusmn; standard deviation.</p>
          <div class="annual-canvas-wrap"><canvas id="annualAeCanvas" aria-label="Annual AE 380/500 means"></canvas></div>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              <th>Period</th>
              <th>Mean</th>
              <th>Standard deviation</th>
              <th id="annualCountHeader">n days</th>
            </tr>
          </thead>
          <tbody id="annualRows"></tbody>
        </table>
      </div>
      <div class="tooltip" id="annualTooltip"></div>
    </section>
  </section>
</main>
<script>
const DATA = __DATA__;
const PERCENT_DIGITS = 4;
const state = {
  family: "AOD",
  grain: "all",
  mode: "count",
  metric: DATA.aod_metrics[0],
  annualGrain: "daily",
  selectedPeriods: new Set(availablePeriods()),
  hoverBin: null
};
let chartLayout = null;
let annualLayouts = {};
const controls = {
  family: document.getElementById("familyControls"),
  grain: document.getElementById("grainControls"),
  mode: document.getElementById("modeControls"),
  metric: document.getElementById("metricControls"),
  periods: document.getElementById("periodControls")
};
const labels = {
  all: "All measurements",
  daily: "Daily means",
  count: "Frequency count",
  relative: "Relative frequency %",
  cumulative: "Cumulative %"
};
const requestedPeriods = parseRequestedPeriods();
if (requestedPeriods !== null) state.selectedPeriods = requestedPeriods;

function fmt(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function fmtBin(value) {
  return Number(value).toFixed(3);
}

function fmtPercent(value) {
  return Number(value).toFixed(PERCENT_DIGITS);
}

function metricList() {
  return state.family === "AOD" ? DATA.aod_metrics : DATA.ae_metrics;
}

function parseRequestedMonths() {
  const params = new URLSearchParams(window.location.search);
  const raw = params.get("months") || params.get("month");
  if (!raw || raw.toLowerCase() === "all") return null;
  const allowed = new Set(DATA.months.map(month => month.number));
  const values = raw.split(",")
    .map(part => Number(part.trim()))
    .filter(value => Number.isInteger(value) && allowed.has(value));
  return values.length ? new Set(values) : null;
}

function parseRequestedYears() {
  const params = new URLSearchParams(window.location.search);
  const raw = params.get("years") || params.get("year");
  if (!raw || raw.toLowerCase() === "all") return null;
  const allowed = new Set(DATA.years);
  const values = raw.split(",")
    .map(part => Number(part.trim()))
    .filter(value => Number.isInteger(value) && allowed.has(value));
  return values.length ? new Set(values) : null;
}

function availablePeriods() {
  return Array.from(new Set(DATA.raw.daily.map(row => `${row[0]}-${String(row[1]).padStart(2, "0")}`))).sort();
}

function parseRequestedPeriods() {
  const params = new URLSearchParams(window.location.search);
  const allowed = new Set(availablePeriods());
  if (params.has("periods")) {
    const values = (params.get("periods") || "").split(",")
      .map(part => part.trim())
      .filter(value => allowed.has(value));
    return new Set(values);
  }
  const requestedMonths = parseRequestedMonths();
  const requestedYears = parseRequestedYears();
  if (!requestedMonths && !requestedYears) return null;
  return new Set(availablePeriods().filter(period => {
    const year = Number(period.slice(0, 4));
    const month = Number(period.slice(5, 7));
    return (!requestedMonths || requestedMonths.has(month)) &&
      (!requestedYears || requestedYears.has(year));
  }));
}

function selectionLabel() {
  const selected = Array.from(state.selectedPeriods).sort();
  if (selected.length === availablePeriods().length) return `all ${selected.length} available calendar months`;
  if (!selected.length) return "no calendar months";
  if (selected.length <= 6) return selected.join(", ");
  return `${selected.length} selected calendar months`;
}

function metricIndex(metric) {
  return DATA.raw_metric_fields.indexOf(metric) + 2;
}

function filteredRows(grain = state.grain) {
  return DATA.raw[grain].filter(row => {
    const period = `${row[0]}-${String(row[1]).padStart(2, "0")}`;
    return state.selectedPeriods.has(period);
  });
}

function buildHistogramFromRows(metric, grain = state.grain) {
  const idx = metricIndex(metric);
  let n = 0;
  let min = null;
  let max = null;
  const bins = new Map();
  filteredRows(grain).forEach(row => {
    const value = row[idx];
    if (typeof value !== "number" || !Number.isFinite(value)) return;
    n += 1;
    min = min === null ? value : Math.min(min, value);
    max = max === null ? value : Math.max(max, value);
    const bin = Math.floor((value / DATA.bin_width) + 1e-12);
    bins.set(bin, (bins.get(bin) || 0) + 1);
  });
  return {
    n,
    min,
    max,
    bins: [...bins.entries()].sort((a, b) => a[0] - b[0])
  };
}

function makeButton(text, active, onClick, title) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = text;
  button.title = title || text;
  if (active) button.classList.add("active");
  button.addEventListener("click", onClick);
  return button;
}

function renderControls() {
  controls.family.replaceChildren(
    makeButton("AOD", state.family === "AOD", () => {
      state.family = "AOD";
      state.metric = DATA.aod_metrics.includes(state.metric) ? state.metric : DATA.aod_metrics[0];
      render();
    }),
    makeButton("AE", state.family === "AE", () => {
      state.family = "AE";
      state.metric = DATA.ae_metrics.includes(state.metric) ? state.metric : DATA.ae_metrics[0];
      render();
    })
  );
  controls.grain.replaceChildren(
    makeButton("All", state.grain === "all", () => { state.grain = "all"; render(); }, labels.all),
    makeButton("Daily", state.grain === "daily", () => { state.grain = "daily"; render(); }, labels.daily)
  );
  controls.mode.replaceChildren(
    makeButton("Count", state.mode === "count", () => { state.mode = "count"; render(); }, labels.count),
    makeButton("%", state.mode === "relative", () => { state.mode = "relative"; render(); }, labels.relative),
    makeButton("Cum %", state.mode === "cumulative", () => { state.mode = "cumulative"; render(); }, labels.cumulative)
  );
  const available = new Set(availablePeriods());
  controls.periods.replaceChildren(...DATA.years.map(year => {
    const wrapper = document.createElement("div");
    wrapper.className = "period-year";
    const yearPeriods = availablePeriods().filter(period => period.startsWith(`${year}-`));
    const allYearSelected = yearPeriods.every(period => state.selectedPeriods.has(period));
    const yearButton = makeButton(String(year), allYearSelected, () => {
      yearPeriods.forEach(period => allYearSelected ? state.selectedPeriods.delete(period) : state.selectedPeriods.add(period));
      state.hoverBin = null;
      render();
    }, `${allYearSelected ? "Remove" : "Keep"} all available months in ${year}`);
    yearButton.classList.add("period-year-toggle");
    const monthGrid = document.createElement("div");
    monthGrid.className = "period-months";
    monthGrid.replaceChildren(...DATA.months.map(month => {
      const period = `${year}-${String(month.number).padStart(2, "0")}`;
      const button = makeButton(month.name.slice(0, 3), state.selectedPeriods.has(period), () => {
        if (state.selectedPeriods.has(period)) state.selectedPeriods.delete(period);
        else state.selectedPeriods.add(period);
        state.hoverBin = null;
        render();
      }, available.has(period) ? `${period}: ${state.selectedPeriods.has(period) ? "kept" : "removed"}` : `${period}: no daily data`);
      button.disabled = !available.has(period);
      return button;
    }));
    wrapper.append(yearButton, monthGrid);
    return wrapper;
  }));
  controls.metric.replaceChildren(...metricList().map(metric => {
    const info = DATA.metrics[metric];
    return makeButton(info.label.replace(" nm", ""), metric === state.metric, () => {
      state.metric = metric;
      render();
    }, info.label);
  }));
}

function getHistogram() {
  return buildHistogramFromRows(state.metric, state.grain);
}

function binMap(hist) {
  const map = new Map();
  hist.bins.forEach(([idx, count]) => map.set(idx, count));
  return map;
}

function yValue(count, total) {
  return state.mode === "relative" ? (total ? count / total * 100 : 0) : count;
}

function drawHistogram() {
  const canvas = document.getElementById("histogram");
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);

  const hist = getHistogram();
  const bins = hist.bins;
  const margin = { left: 66, right: 18, top: 22, bottom: 56 };
  const plotW = Math.max(1, rect.width - margin.left - margin.right);
  const plotH = Math.max(1, rect.height - margin.top - margin.bottom);
  ctx.font = "12px Segoe UI, Arial, sans-serif";
  ctx.fillStyle = "#182230";
  ctx.strokeStyle = "#cfd8e4";
  ctx.lineWidth = 1;

  if (!bins.length) {
    ctx.fillText("No data for this selection", margin.left, margin.top + 24);
    chartLayout = null;
    return;
  }

  const total = hist.n;
  const minIdx = Math.min(...bins.map(item => item[0]));
  const maxIdx = Math.max(...bins.map(item => item[0]));
  const counts = binMap(hist);
  const cumulative = new Map();
  let maxY = 0;
  let running = 0;
  for (let idx = minIdx; idx <= maxIdx; idx += 1) {
    const count = counts.get(idx) || 0;
    running += count;
    const cumulativePercent = total ? running / total * 100 : 0;
    cumulative.set(idx, cumulativePercent);
    const value = state.mode === "cumulative" ? cumulativePercent : yValue(count, total);
    maxY = Math.max(maxY, value);
  }
  maxY = maxY || 1;
  const yMax = state.mode === "cumulative" ? 100 : maxY * 1.08;
  const barW = plotW / (maxIdx - minIdx + 1);
  const color = state.family === "AOD" ? "#2f80bd" : "#d68432";
  const stroke = state.family === "AOD" ? "#1c5f91" : "#a95f18";
  chartLayout = { margin, plotW, plotH, minIdx, maxIdx, barW, yMax, counts, cumulative, total };

  ctx.strokeStyle = "#d8e0ea";
  ctx.beginPath();
  for (let i = 0; i <= 4; i += 1) {
    const y = margin.top + plotH - (plotH * i / 4);
    ctx.moveTo(margin.left, y);
    ctx.lineTo(margin.left + plotW, y);
  }
  ctx.stroke();

  ctx.fillStyle = color;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = Math.max(0.5, Math.min(1, barW));
  for (let idx = minIdx; idx <= maxIdx; idx += 1) {
    const count = counts.get(idx) || 0;
    const value = state.mode === "cumulative" ? (cumulative.get(idx) || 0) : yValue(count, total);
    const x = margin.left + (idx - minIdx) * barW;
    const h = value / yMax * plotH;
    const y = margin.top + plotH - h;
    if (h > 0) {
      ctx.fillRect(x, y, Math.max(1, barW - 0.4), h);
      if (barW > 2) ctx.strokeRect(x, y, Math.max(1, barW - 0.4), h);
    }
  }
  if (state.hoverBin !== null && state.hoverBin >= minIdx && state.hoverBin <= maxIdx) {
    const count = counts.get(state.hoverBin) || 0;
    if (count > 0) {
      const value = state.mode === "cumulative" ? (cumulative.get(state.hoverBin) || 0) : yValue(count, total);
      const x = margin.left + (state.hoverBin - minIdx) * barW;
      const h = value / yMax * plotH;
      const y = margin.top + plotH - h;
      ctx.save();
      ctx.strokeStyle = "#111827";
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, Math.max(2, barW), h);
      ctx.restore();
    }
  }

  ctx.strokeStyle = "#6d7788";
  ctx.beginPath();
  ctx.moveTo(margin.left, margin.top);
  ctx.lineTo(margin.left, margin.top + plotH);
  ctx.lineTo(margin.left + plotW, margin.top + plotH);
  ctx.stroke();

  ctx.fillStyle = "#4f5b6d";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= 4; i += 1) {
    const value = yMax * i / 4;
    const y = margin.top + plotH - (plotH * i / 4);
    const label = state.mode === "count" ? Math.round(value).toLocaleString() : fmtPercent(value);
    ctx.fillText(label, margin.left - 8, y);
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  const tickCount = 6;
  for (let i = 0; i < tickCount; i += 1) {
    const t = tickCount === 1 ? 0 : i / (tickCount - 1);
    const idx = minIdx + Math.round((maxIdx - minIdx) * t);
    const x = margin.left + (idx - minIdx + 0.5) * barW;
    ctx.fillText(fmtBin(idx * DATA.bin_width), x, margin.top + plotH + 10);
  }

  ctx.save();
  ctx.translate(18, margin.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(state.mode === "count" ? "Frequency count" : labels[state.mode], 0, 0);
  ctx.restore();

  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText(state.family === "AOD" ? "AOD bin start" : "AE bin start", margin.left + plotW / 2, rect.height - 8);
}

function hideTooltip() {
  const tooltip = document.getElementById("histTooltip");
  tooltip.style.display = "none";
  if (state.hoverBin !== null) {
    state.hoverBin = null;
    drawHistogram();
  }
}

function updateTooltip(event) {
  if (!chartLayout) return hideTooltip();
  const canvas = document.getElementById("histogram");
  const tooltip = document.getElementById("histTooltip");
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const { margin, plotW, plotH, minIdx, maxIdx, barW, counts, cumulative, total } = chartLayout;

  if (x < margin.left || x > margin.left + plotW || y < margin.top || y > margin.top + plotH) {
    return hideTooltip();
  }

  const idx = Math.min(maxIdx, Math.max(minIdx, minIdx + Math.floor((x - margin.left) / barW)));
  const count = counts.get(idx) || 0;
  if (!count) return hideTooltip();

  if (state.hoverBin !== idx) {
    state.hoverBin = idx;
    drawHistogram();
  }

  const start = idx * DATA.bin_width;
  const end = (idx + 1) * DATA.bin_width;
  const percent = total ? count / total * 100 : 0;
  const cumulativePercent = cumulative.get(idx) || 0;
  const info = DATA.metrics[state.metric];
  tooltip.innerHTML = `<strong>${info.label} - ${labels[state.grain]}</strong><div>Bin: ${fmtBin(start)} to ${fmtBin(end)}</div><div>Frequency count: ${count.toLocaleString()}</div><div>Relative frequency: ${fmtPercent(percent)}%</div><div>Cumulative: ${fmtPercent(cumulativePercent)}%</div><div>n: ${total.toLocaleString()}</div>`;

  const wrap = document.getElementById("canvasWrap").getBoundingClientRect();
  const tipWidth = 240;
  const left = Math.min(Math.max(8, event.clientX - wrap.left + 14), wrap.width - tipWidth - 8);
  const top = Math.max(8, event.clientY - wrap.top - 78);
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
  tooltip.style.display = "block";
}

function renderStats() {
  const hist = getHistogram();
  const nonzero = hist.bins.length;
  const maxBin = hist.bins.reduce((best, item) => item[1] > best[1] ? item : best, [0, 0]);
  const stats = [
    ["n", hist.n.toLocaleString()],
    ["min", fmt(hist.min, 4)],
    ["max", fmt(hist.max, 4)],
    ["largest bin", `${fmtBin(maxBin[0] * DATA.bin_width)} (${maxBin[1].toLocaleString()})`]
  ];
  document.getElementById("stats").replaceChildren(...stats.map(([label, value]) => {
    const div = document.createElement("div");
    div.className = "stat";
    div.innerHTML = `<b>${value}</b><span>${label}</span>`;
    return div;
  }));
}

function renderTable() {
  const hist = getHistogram();
  const total = hist.n || 0;
  let cumulative = 0;
  const rows = hist.bins.map(([idx, count]) => {
    cumulative += count;
    const start = idx * DATA.bin_width;
    const end = (idx + 1) * DATA.bin_width;
    const percent = total ? count / total * 100 : 0;
    const cumulativePercent = total ? cumulative / total * 100 : 0;
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${fmtBin(start)}-${fmtBin(end)}</td><td>${fmtBin(start)}</td><td>${fmtBin(end)}</td><td>${count.toLocaleString()}</td><td>${fmtPercent(percent)}</td><td>${fmtPercent(cumulativePercent)}</td>`;
    return tr;
  });
  document.getElementById("freqRows").replaceChildren(...rows);
  document.getElementById("tableMeta").textContent = `${rows.length.toLocaleString()} non-empty bins`;
}

function annualValue(value) {
  return value === null || value === undefined ? "n/a" : Number(value).toFixed(4);
}

function individualDescriptive(metric) {
  const idx = metricIndex(metric);
  const values = filteredRows("all")
    .map(row => row[idx])
    .filter(value => typeof value === "number" && Number.isFinite(value))
    .sort((a, b) => a - b);
  if (!values.length) return { n: 0, mean: null, std: null, median: null, min: null, max: null, skewness: null };
  const n = values.length;
  const mean = values.reduce((sum, value) => sum + value, 0) / n;
  const middle = Math.floor(n / 2);
  const median = n % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
  let skewness = null;
  const variance = n > 1
    ? values.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / (n - 1)
    : 0;
  const std = Math.sqrt(variance);
  if (n >= 3) {
    skewness = std === 0
      ? 0
      : n / ((n - 1) * (n - 2)) * values.reduce((sum, value) => sum + Math.pow((value - mean) / std, 3), 0);
  }
  return { n, mean, std, median, min: values[0], max: values[n - 1], skewness };
}

function individualStatValue(value) {
  return value === null || value === undefined ? "n/a" : Number(value).toFixed(6);
}

function renderIndividualStats() {
  const rows = DATA.raw_metric_fields.map(metric => {
    const stats = individualDescriptive(metric);
    const row = document.createElement("tr");
    row.innerHTML = `<td>${DATA.metrics[metric].label}</td><td>${stats.n.toLocaleString()}</td><td>${individualStatValue(stats.mean)}</td><td>${individualStatValue(stats.std)}</td><td>${individualStatValue(stats.median)}</td><td>${individualStatValue(stats.min)}</td><td>${individualStatValue(stats.max)}</td><td>${individualStatValue(stats.skewness)}</td>`;
    return row;
  });
  document.getElementById("individualStatsRows").replaceChildren(...rows);
  document.getElementById("individualStatsMeta").textContent = `Individual basis, ${selectionLabel()}`;
}

function summarizeNumbers(values) {
  const clean = values.filter(value => typeof value === "number" && Number.isFinite(value));
  if (!clean.length) return { mean: null, std: null, n: 0 };
  const mean = clean.reduce((sum, value) => sum + value, 0) / clean.length;
  const variance = clean.length > 1
    ? clean.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / (clean.length - 1)
    : 0;
  return { mean, std: Math.sqrt(variance), n: clean.length };
}

function annualRows(metric) {
  const idx = metricIndex(metric);
  const byYear = new Map();
  const allValues = [];
  filteredRows(state.annualGrain).forEach(row => {
    const value = row[idx];
    if (typeof value !== "number" || !Number.isFinite(value)) return;
    const year = row[0];
    if (!byYear.has(year)) byYear.set(year, []);
    byYear.get(year).push(value);
    allValues.push(value);
  });
  const rows = [...byYear.entries()].sort((a, b) => a[0] - b[0]).map(([year, values]) => ({
    period: String(year),
    year,
    ...summarizeNumbers(values)
  }));
  rows.push({ period: "All years", year: null, ...summarizeNumbers(allValues) });
  return rows;
}

function drawAnnualChart(canvasId, metric, color, darkColor) {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);

  const rows = annualRows(metric);
  const margin = { left: 56, right: 14, top: 18, bottom: 54 };
  const plotW = Math.max(1, rect.width - margin.left - margin.right);
  const plotH = Math.max(1, rect.height - margin.top - margin.bottom);
  const maxY = Math.max(...rows.map(row => (row.mean || 0) + (row.std || 0)), 1e-6) * 1.12;
  const yScale = value => margin.top + plotH - (value / maxY * plotH);
  const band = plotW / rows.length;
  const barW = Math.min(46, band * 0.58);
  const bars = [];

  ctx.font = "12px Segoe UI, Arial, sans-serif";
  if (rows.every(row => row.n === 0)) {
    ctx.fillStyle = "#4f5b6d";
    ctx.fillText("No annual data for this calendar-month selection", margin.left, margin.top + 24);
    annualLayouts[canvasId] = { bars: [] };
    return;
  }
  ctx.strokeStyle = "#d8e0ea";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 4; i += 1) {
    const y = margin.top + plotH - plotH * i / 4;
    ctx.moveTo(margin.left, y);
    ctx.lineTo(margin.left + plotW, y);
  }
  ctx.stroke();

  ctx.fillStyle = "#4f5b6d";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= 4; i += 1) {
    const value = maxY * i / 4;
    const y = margin.top + plotH - plotH * i / 4;
    ctx.fillText(value.toFixed(metric.startsWith("AOD") ? 2 : 1), margin.left - 8, y);
  }

  rows.forEach((row, i) => {
    const mean = row.mean || 0;
    const std = row.std || 0;
    const x = margin.left + band * i + (band - barW) / 2;
    const y = yScale(mean);
    const h = margin.top + plotH - y;
    const isAll = row.period === "All years";
    ctx.fillStyle = isAll ? darkColor : color;
    ctx.strokeStyle = isAll ? darkColor : color;
    ctx.fillRect(x, y, barW, h);
    ctx.strokeRect(x, y, barW, h);

    const errTop = yScale(mean + std);
    const errBottom = yScale(Math.max(0, mean - std));
    const center = x + barW / 2;
    ctx.strokeStyle = "#263241";
    ctx.beginPath();
    ctx.moveTo(center, errTop);
    ctx.lineTo(center, errBottom);
    ctx.moveTo(center - 6, errTop);
    ctx.lineTo(center + 6, errTop);
    ctx.moveTo(center - 6, errBottom);
    ctx.lineTo(center + 6, errBottom);
    ctx.stroke();

    ctx.fillStyle = "#4f5b6d";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const label = row.period === "All years" ? "All" : row.period;
    ctx.fillText(label, center, margin.top + plotH + 10);
    bars.push({ x, y: errTop, w: barW, h: margin.top + plotH - errTop, row, metric });
  });

  ctx.strokeStyle = "#6d7788";
  ctx.beginPath();
  ctx.moveTo(margin.left, margin.top);
  ctx.lineTo(margin.left, margin.top + plotH);
  ctx.lineTo(margin.left + plotW, margin.top + plotH);
  ctx.stroke();
  annualLayouts[canvasId] = { bars };
}

function drawAnnualCharts() {
  drawAnnualChart("annualAodCanvas", "AOD_500nm", "#2f80bd", "#1c5f91");
  drawAnnualChart("annualAeCanvas", "380-500_Angstrom_Exponent", "#d68432", "#a95f18");
}

function renderAnnualTable() {
  const metricOrder = ["AOD_500nm", "380-500_Angstrom_Exponent"];
  const rows = [];
  metricOrder.forEach(metric => {
    const info = DATA.metrics[metric];
    annualRows(metric).forEach(row => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${info.label}</td><td>${row.period}</td><td>${annualValue(row.mean)}</td><td>${annualValue(row.std)}</td><td>${row.n.toLocaleString()}</td>`;
      rows.push(tr);
    });
  });
  document.getElementById("annualRows").replaceChildren(...rows);
  const individual = state.annualGrain === "all";
  const basis = individual ? "Individual-measurement basis" : "Daily-mean basis";
  const phrase = individual ? "individual measurements" : "daily means";
  document.getElementById("annualMeta").textContent = `${basis}, ${selectionLabel()}, excluding listed dates`;
  document.getElementById("annualCountHeader").textContent = individual ? "n measurements" : "n days";
  document.getElementById("annualAodCaption").textContent = `Mean annual AOD 500 from ${phrase} for the selected calendar months. Whiskers show mean plus/minus standard deviation.`;
  document.getElementById("annualAeCaption").textContent = `Mean annual Angstrom exponent 380/500 from ${phrase} for the selected calendar months. Whiskers show mean plus/minus standard deviation.`;
  document.getElementById("annualDailyBtn").classList.toggle("active", !individual);
  document.getElementById("annualIndividualBtn").classList.toggle("active", individual);
}

function hideAnnualTooltip() {
  document.getElementById("annualTooltip").style.display = "none";
}

function updateAnnualTooltip(event, canvasId) {
  const layout = annualLayouts[canvasId];
  if (!layout) return hideAnnualTooltip();
  const canvas = document.getElementById(canvasId);
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const bar = layout.bars.find(item => x >= item.x - 4 && x <= item.x + item.w + 4 && y >= item.y - 8 && y <= item.y + item.h + 8);
  if (!bar) return hideAnnualTooltip();

  const tooltip = document.getElementById("annualTooltip");
  const info = DATA.metrics[bar.metric];
  const countLabel = state.annualGrain === "all" ? "n measurements" : "n days";
  tooltip.innerHTML = `<strong>${info.label} - ${bar.row.period}</strong><div>Mean: ${annualValue(bar.row.mean)}</div><div>Standard deviation: ${annualValue(bar.row.std)}</div><div>${countLabel}: ${bar.row.n.toLocaleString()}</div>`;
  const panel = document.querySelector(".annual-panel").getBoundingClientRect();
  const tipWidth = 240;
  const left = Math.min(Math.max(8, event.clientX - panel.left + 14), panel.width - tipWidth - 8);
  const top = Math.max(8, event.clientY - panel.top - 76);
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
  tooltip.style.display = "block";
}

function renderText() {
  const info = DATA.metrics[state.metric];
  const hist = getHistogram();
  const dateText = DATA.date_range[0] && DATA.date_range[1] ? `${DATA.date_range[0]} to ${DATA.date_range[1]}` : "available dates";
  document.getElementById("chartTitle").textContent = `${info.label} - ${labels[state.grain]}`;
  document.getElementById("chartSubtitle").textContent = `${labels[state.mode]}, bin width ${DATA.bin_width.toFixed(3)}, ${hist.n.toLocaleString()} values, ${selectionLabel()}, ${dateText}`;
  document.getElementById("sourceNote").textContent = `Source files: ${DATA.source_files}. Measurements after excluding ${DATA.excluded_dates.join(", ")}: ${DATA.observation_count.toLocaleString()}. Daily dates: ${DATA.daily_count.toLocaleString()}. Filter: ${selectionLabel()}.`;
}

function render() {
  renderControls();
  renderText();
  renderStats();
  drawHistogram();
  renderTable();
  renderIndividualStats();
  renderAnnualTable();
  drawAnnualCharts();
}

window.addEventListener("resize", () => {
  drawHistogram();
  drawAnnualCharts();
});
document.getElementById("histogram").addEventListener("mousemove", updateTooltip);
document.getElementById("histogram").addEventListener("mouseleave", hideTooltip);
document.getElementById("annualAodCanvas").addEventListener("mousemove", event => updateAnnualTooltip(event, "annualAodCanvas"));
document.getElementById("annualAeCanvas").addEventListener("mousemove", event => updateAnnualTooltip(event, "annualAeCanvas"));
document.getElementById("annualAodCanvas").addEventListener("mouseleave", hideAnnualTooltip);
document.getElementById("annualAeCanvas").addEventListener("mouseleave", hideAnnualTooltip);
document.getElementById("annualDailyBtn").addEventListener("click", () => {
  state.annualGrain = "daily";
  hideAnnualTooltip();
  renderAnnualTable();
  drawAnnualCharts();
});
document.getElementById("annualIndividualBtn").addEventListener("click", () => {
  state.annualGrain = "all";
  hideAnnualTooltip();
  renderAnnualTable();
  drawAnnualCharts();
});
document.getElementById("allPeriodsBtn").addEventListener("click", () => {
  state.selectedPeriods = new Set(availablePeriods());
  state.hoverBin = null;
  render();
});
document.getElementById("clearPeriodsBtn").addEventListener("click", () => {
  state.selectedPeriods = new Set();
  state.hoverBin = null;
  render();
});
render();
</script>
</body>
</html>
"""
    return template.replace("__DATA__", data_json)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv_export(payload)
    OUT_PATH.write_text(build_html(payload), encoding="utf-8")
    print(f"Measurements after exclusions: {payload['observation_count']}")
    print(f"Daily dates after exclusions: {payload['daily_count']}")
    print(f"Histogram data: {CACHE_PATH}")
    print(f"CSV export: {CSV_PATH}")
    print(f"Annual CSV export: {ANNUAL_CSV_PATH}")
    print(f"Individual statistics CSV: {INDIVIDUAL_STATS_CSV_PATH}")
    print(f"Interactive page: {OUT_PATH}")


if __name__ == "__main__":
    main()
