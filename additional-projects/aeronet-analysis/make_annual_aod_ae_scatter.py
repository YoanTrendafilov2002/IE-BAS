import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "work" / "outputs_rar_check_2026-07-13"
OUT_PATH = ROOT / "outputs" / "AOD440_AE440-870_annual_mean_scatter_2020-2026.html"
CSV_PATH = ROOT / "outputs" / "aeronet_summary_data" / "annual_AOD440_AE440-870_scatter_summary.csv"
DAILY_CSV = SOURCE_DIR / "AOD440_AE440-870_seasonal_daily_2020-2026.csv"
EXCLUDED_DATES = {"2022-10-21"}


def stats(values):
    clean = [float(value) for value in values]
    return {
        "mean": sum(clean) / len(clean),
        "std": statistics.stdev(clean) if len(clean) > 1 else 0,
        "n": len(clean),
    }


def read_annual_rows():
    by_year = defaultdict(lambda: {"aod": [], "ae": []})
    with DAILY_CSV.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["date"] in EXCLUDED_DATES:
                continue
            year = int(row["date"][:4])
            by_year[year]["aod"].append(float(row["AOD_440nm_daily_mean"]))
            by_year[year]["ae"].append(float(row["AE_440_870_daily_mean"]))

    rows = []
    for year in sorted(by_year):
        aod_stats = stats(by_year[year]["aod"])
        ae_stats = stats(by_year[year]["ae"])
        rows.append(
            {
                "year": year,
                "aod_mean": aod_stats["mean"],
                "aod_std": aod_stats["std"],
                "ae_mean": ae_stats["mean"],
                "ae_std": ae_stats["std"],
                "n_days": min(aod_stats["n"], ae_stats["n"]),
            }
        )
    return rows


def write_csv(rows):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["year", "aod_mean", "aod_std", "ae_mean", "ae_std", "n_days"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "year": row["year"],
                    "aod_mean": round(row["aod_mean"], 6),
                    "aod_std": round(row["aod_std"], 6),
                    "ae_mean": round(row["ae_mean"], 6),
                    "ae_std": round(row["ae_std"], 6),
                    "n_days": row["n_days"],
                }
            )


def build_html(rows):
    payload = {
        "rows": rows,
        "excluded_dates": sorted(EXCLUDED_DATES),
        "source": str(DAILY_CSV),
    }
    data_json = json.dumps(payload, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Annual AOD440 AE440/870 Scatter With Standard Deviation</title>
<style>
:root {{
  --ink: #172234;
  --muted: #506078;
  --line: #d9e0ea;
  --paper: #f6f8fb;
  --panel: #ffffff;
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
  margin: 0 0 6px;
  font-size: clamp(24px, 3vw, 34px);
  line-height: 1.15;
  letter-spacing: 0;
}}
p {{
  margin: 0;
  color: var(--muted);
  line-height: 1.45;
}}
main {{
  padding: 16px 24px 28px;
}}
.plot-panel, .table-panel {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}}
.plot-panel {{
  position: relative;
  padding: 14px;
}}
.plot-head {{
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}}
h2 {{
  margin: 0;
  font-size: 20px;
}}
.meta {{
  color: var(--muted);
  font-size: 13px;
}}
.canvas-wrap {{
  position: relative;
  width: 100%;
  height: min(68vh, 680px);
  min-height: 520px;
}}
canvas {{
  display: block;
  width: 100%;
  height: 100%;
  background: #fff;
}}
.tooltip {{
  position: absolute;
  z-index: 5;
  display: none;
  max-width: 280px;
  padding: 9px 10px;
  border: 1px solid #b9c5d5;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 10px 28px rgba(17, 24, 39, 0.16);
  color: var(--ink);
  font-size: 12px;
  line-height: 1.4;
  pointer-events: none;
}}
.tooltip strong {{
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
}}
.table-panel {{
  margin-top: 14px;
}}
.table-head {{
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  gap: 12px;
}}
.table-wrap {{
  overflow: auto;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}
th, td {{
  padding: 8px 10px;
  border-bottom: 1px solid #edf1f6;
  text-align: right;
  white-space: nowrap;
}}
th:first-child, td:first-child {{ text-align: left; }}
th {{
  background: #f9fbfd;
  color: var(--muted);
  font-size: 12px;
}}
.note {{
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}}
@media (max-width: 720px) {{
  main {{ padding: 12px; }}
  .plot-head, .table-head {{ flex-direction: column; }}
  .canvas-wrap {{ min-height: 420px; height: 58vh; }}
}}
</style>
</head>
<body>
<header>
  <h1>Annual AOD440 - AE440/870 scatter with standard deviation</h1>
  <p>Each point is one year. Horizontal error bars show AOD440 standard deviation; vertical error bars show AE440/870 standard deviation, computed from daily means.</p>
</header>
<main>
  <section class="plot-panel">
    <div class="plot-head">
      <div>
        <h2>Annual means, 2020-2026</h2>
        <p class="meta">Daily-mean basis; excludes 2022-10-21. Dashed lines show the current composition margins.</p>
      </div>
      <p class="meta" id="rangeText"></p>
    </div>
    <div class="canvas-wrap" id="canvasWrap">
      <canvas id="plotCanvas" aria-label="Annual AOD AE scatter"></canvas>
      <div class="tooltip" id="tooltip"></div>
    </div>
  </section>
  <section class="table-panel">
    <div class="table-head">
      <strong>Annual data table</strong>
      <span class="meta">Mean and standard deviation from daily means</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Year</th>
            <th>AOD440 mean</th>
            <th>AOD440 std</th>
            <th>AE440/870 mean</th>
            <th>AE440/870 std</th>
            <th>n days</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </section>
</main>
<script id="payload" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
const canvas = document.getElementById('plotCanvas');
const ctx = canvas.getContext('2d');
const wrap = document.getElementById('canvasWrap');
const tooltip = document.getElementById('tooltip');
const colors = ['#2f80bd', '#ee9344', '#7f944a', '#cf6f93', '#9467bd', '#8c6d31', '#1f9d8a'];
let layout = null;

function fmt(value, digits = 4) {{
  return Number(value).toLocaleString(undefined, {{ maximumFractionDigits: digits, minimumFractionDigits: digits }});
}}

function domain() {{
  const rows = DATA.rows;
  const xMin = Math.max(0, Math.min(0.2, ...rows.map(row => row.aod_mean - row.aod_std)) - 0.025);
  const xMax = Math.max(0.35, ...rows.map(row => row.aod_mean + row.aod_std)) + 0.035;
  const yMin = Math.max(0, Math.min(0.8, ...rows.map(row => row.ae_mean - row.ae_std)) - 0.08);
  const yMax = Math.max(1.0, ...rows.map(row => row.ae_mean + row.ae_std)) + 0.12;
  return {{ xMin, xMax, yMin, yMax }};
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

function drawMargins(d, xScale, yScale, dom) {{
  ctx.save();
  ctx.setLineDash([7, 5]);
  ctx.lineWidth = 1.2;
  ctx.strokeStyle = '#6f7480';
  ctx.fillStyle = '#3f4756';
  ctx.font = '12px Segoe UI, Arial';
  [[0.8, 'AE 0.8'], [1.0, 'AE 1.0']].forEach(([value, label]) => {{
    if (value < dom.yMin || value > dom.yMax) return;
    const y = yScale(value);
    ctx.beginPath();
    ctx.moveTo(d.left, y);
    ctx.lineTo(d.w - d.right, y);
    ctx.stroke();
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    ctx.fillText(label, d.w - d.right - 8, y - 4);
  }});
  [[0.2, 'AOD 0.20'], [0.35, 'AOD 0.35']].forEach(([value, label]) => {{
    if (value < dom.xMin || value > dom.xMax) return;
    const x = xScale(value);
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

function draw() {{
  const rect = wrap.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(320, Math.round(rect.width * ratio));
  canvas.height = Math.max(320, Math.round(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const d = {{ w: rect.width, h: rect.height, left: 74, right: 30, top: 26, bottom: 70 }};
  const dom = domain();
  const xScale = value => d.left + (value - dom.xMin) / (dom.xMax - dom.xMin) * (d.w - d.left - d.right);
  const yScale = value => d.top + (dom.yMax - value) / (dom.yMax - dom.yMin) * (d.h - d.top - d.bottom);
  ctx.clearRect(0, 0, d.w, d.h);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, d.w, d.h);

  ctx.strokeStyle = '#d9e0ea';
  ctx.lineWidth = 1;
  ctx.font = '12px Segoe UI, Arial';
  ctx.fillStyle = '#506078';
  niceTicks(dom.yMin, dom.yMax, 7).forEach(tick => {{
    const y = yScale(tick);
    ctx.beginPath();
    ctx.moveTo(d.left, y);
    ctx.lineTo(d.w - d.right, y);
    ctx.stroke();
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(tick.toFixed(1), d.left - 9, y);
  }});
  niceTicks(dom.xMin, dom.xMax, 8).forEach(tick => {{
    const x = xScale(tick);
    ctx.beginPath();
    ctx.moveTo(x, d.h - d.bottom);
    ctx.lineTo(x, d.h - d.bottom + 5);
    ctx.stroke();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(tick.toFixed(2), x, d.h - d.bottom + 10);
  }});

  drawMargins(d, xScale, yScale, dom);

  const points = [];
  DATA.rows.forEach((row, index) => {{
    const x = xScale(row.aod_mean);
    const y = yScale(row.ae_mean);
    const x0 = xScale(row.aod_mean - row.aod_std);
    const x1 = xScale(row.aod_mean + row.aod_std);
    const y0 = yScale(row.ae_mean - row.ae_std);
    const y1 = yScale(row.ae_mean + row.ae_std);
    const color = colors[index % colors.length];
    ctx.strokeStyle = '#263241';
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    ctx.moveTo(x0, y);
    ctx.lineTo(x1, y);
    ctx.moveTo(x0, y - 5);
    ctx.lineTo(x0, y + 5);
    ctx.moveTo(x1, y - 5);
    ctx.lineTo(x1, y + 5);
    ctx.moveTo(x, y0);
    ctx.lineTo(x, y1);
    ctx.moveTo(x - 5, y0);
    ctx.lineTo(x + 5, y0);
    ctx.moveTo(x - 5, y1);
    ctx.lineTo(x + 5, y1);
    ctx.stroke();

    ctx.fillStyle = color;
    ctx.strokeStyle = '#172234';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(x, y, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#172234';
    ctx.font = '700 12px Segoe UI, Arial';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(row.year), x + 12, y);
    points.push({{ x, y, row }});
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
  ctx.fillText('AOD440 annual mean', d.left + (d.w - d.left - d.right) / 2, d.h - 18);
  ctx.save();
  ctx.translate(22, d.top + (d.h - d.top - d.bottom) / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('AE440/870 annual mean', 0, 0);
  ctx.restore();

  document.getElementById('rangeText').textContent = `x ${{dom.xMin.toFixed(2)}}-${{dom.xMax.toFixed(2)}} | y ${{dom.yMin.toFixed(2)}}-${{dom.yMax.toFixed(2)}}`;
  layout = {{ points }};
}}

function renderTable() {{
  document.getElementById('rows').innerHTML = DATA.rows.map(row => `
    <tr>
      <td>${{row.year}}</td>
      <td>${{fmt(row.aod_mean)}}</td>
      <td>${{fmt(row.aod_std)}}</td>
      <td>${{fmt(row.ae_mean)}}</td>
      <td>${{fmt(row.ae_std)}}</td>
      <td>${{row.n_days.toLocaleString()}}</td>
    </tr>
  `).join('');
}}

function setTooltip(point, event) {{
  if (!point) {{
    tooltip.style.display = 'none';
    return;
  }}
  const row = point.row;
  tooltip.innerHTML = `<strong>${{row.year}}</strong><div>AOD440 mean: ${{fmt(row.aod_mean)}}</div><div>AOD440 std: ${{fmt(row.aod_std)}}</div><div>AE440/870 mean: ${{fmt(row.ae_mean)}}</div><div>AE440/870 std: ${{fmt(row.ae_std)}}</div><div>n days: ${{row.n_days.toLocaleString()}}</div>`;
  const box = wrap.getBoundingClientRect();
  const left = Math.min(Math.max(8, event.clientX - box.left + 14), box.width - 260);
  const top = Math.max(8, event.clientY - box.top - 86);
  tooltip.style.left = `${{left}}px`;
  tooltip.style.top = `${{top}}px`;
  tooltip.style.display = 'block';
}}

canvas.addEventListener('mousemove', event => {{
  if (!layout) return;
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  let best = null;
  let bestDist = Infinity;
  layout.points.forEach(point => {{
    const dist = Math.hypot(point.x - x, point.y - y);
    if (dist < bestDist) {{
      bestDist = dist;
      best = point;
    }}
  }});
  setTooltip(bestDist <= 18 ? best : null, event);
}});
canvas.addEventListener('mouseleave', () => setTooltip(null));
window.addEventListener('resize', draw);
renderTable();
draw();
</script>
</body>
</html>
"""


def main():
    rows = read_annual_rows()
    write_csv(rows)
    OUT_PATH.write_text(build_html(rows), encoding="utf-8")
    print(f"Annual rows: {len(rows)}")
    print(f"HTML: {OUT_PATH}")
    print(f"CSV: {CSV_PATH}")


if __name__ == "__main__":
    main()
