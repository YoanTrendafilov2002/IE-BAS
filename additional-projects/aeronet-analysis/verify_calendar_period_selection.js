const fs = require("fs");
const path = require("path");

const outputDir = fs.existsSync(path.join(__dirname, "OPEN_THIS_FIRST.html"))
  ? __dirname
  : path.dirname(__dirname);

function firstExisting(...candidates) {
  const match = candidates.find(candidate => fs.existsSync(candidate));
  if (!match) throw new Error(`Required data file was not found: ${candidates.join(", ")}`);
  return match;
}

function parseCsvLine(line) {
  const cells = [];
  let value = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (quoted && line[index + 1] === '"') {
        value += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      cells.push(value);
      value = "";
    } else {
      value += char;
    }
  }
  cells.push(value);
  return cells;
}
const htmlFiles = [
  "OPEN_THIS_FIRST.html",
  "AOD440_AE440-870_interactive_seasonal_scatter_2020-2026.html",
  "AOD_AE_frequency_distributions_2020-2026.html",
  "aeronet_aod_ae_dashboard_no_2022-10-21.html",
];

for (const filename of htmlFiles) {
  const html = fs.readFileSync(path.join(outputDir, filename), "utf8");
  const scripts = html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi);
  let compiled = 0;
  for (const match of scripts) {
    if (/application\/json/i.test(match[1]) || !match[2].trim()) continue;
    new Function(match[2]);
    compiled += 1;
  }
  console.log(`${filename}: ${compiled} JavaScript block(s) OK`);
}

const selected = new Set(["2020-07", "2021-08"]);
const excludedDate = "2022-10-21";

const frequencyDataPath = firstExisting(
  path.join(outputDir, "aeronet_summary_data", "frequency_distribution_data.json"),
  path.join(outputDir, "data", "frequency_distribution_data.json"),
  path.join(outputDir, "data", "generated_summary", "frequency_distribution_data.json"),
);
const frequencyData = JSON.parse(fs.readFileSync(frequencyDataPath, "utf8"));
const frequencyRows = frequencyData.raw.daily.filter(row =>
  selected.has(`${row[0]}-${String(row[1]).padStart(2, "0")}`),
);

const frequencyHtml = fs.readFileSync(
  path.join(outputDir, "AOD_AE_frequency_distributions_2020-2026.html"),
  "utf8",
);
if (!frequencyHtml.includes('id="periodControls"')) throw new Error("Frequency calendar-month selector is missing");
if (!frequencyHtml.includes("const PERCENT_DIGITS = 4")) throw new Error("Shared four-decimal percentage formatter is missing");
if (!frequencyHtml.includes("errBottom")) throw new Error("Frequency annual charts are missing lower SD whiskers");
if (!frequencyHtml.includes('id="individualAodStats"') || !frequencyHtml.includes('id="individualAeStats"')) {
  throw new Error("Separate individual AOD500 and AE380/500 statistics are missing");
}
if (!frequencyHtml.includes("adjusted Fisher-Pearson sample skewness")) {
  throw new Error("Individual skewness method is not identified");
}
if (!frequencyHtml.includes('id="annualDailyBtn"') || !frequencyHtml.includes('id="annualIndividualBtn"')) {
  throw new Error("Annual daily/individual basis controls are missing");
}
if (!frequencyHtml.includes('filteredRows(state.annualGrain)')) {
  throw new Error("Annual charts do not use the selected annual data basis");
}

function descriptiveStatistics(values) {
  const clean = values.filter(value => typeof value === "number" && Number.isFinite(value)).sort((a, b) => a - b);
  const n = clean.length;
  const mean = clean.reduce((sum, value) => sum + value, 0) / n;
  const middle = Math.floor(n / 2);
  const median = n % 2 ? clean[middle] : (clean[middle - 1] + clean[middle]) / 2;
  const variance = clean.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / (n - 1);
  const std = Math.sqrt(variance);
  const skewness = std === 0
    ? 0
    : n / ((n - 1) * (n - 2)) * clean.reduce((sum, value) => sum + Math.pow((value - mean) / std, 3), 0);
  return { n, mean, median, min: clean[0], max: clean[n - 1], skewness };
}

const individualStatsPath = firstExisting(
  path.join(outputDir, "aeronet_summary_data", "individual_AOD500_AE380-500_descriptive_statistics.csv"),
  path.join(outputDir, "data", "individual_AOD500_AE380-500_descriptive_statistics.csv"),
  path.join(outputDir, "data", "generated_summary", "individual_AOD500_AE380-500_descriptive_statistics.csv"),
);
const individualStatsLines = fs.readFileSync(individualStatsPath, "utf8").trim().split(/\r?\n/).map(parseCsvLine);
const individualStatsHeaders = individualStatsLines[0];
const individualStatsRows = individualStatsLines.slice(1).map(cells =>
  Object.fromEntries(individualStatsHeaders.map((header, index) => [header, cells[index]])),
);
for (const metric of ["AOD_500nm", "380-500_Angstrom_Exponent"]) {
  const metricIndex = frequencyData.raw_metric_fields.indexOf(metric) + 2;
  const expected = descriptiveStatistics(frequencyData.raw.all.map(row => row[metricIndex]));
  const stored = frequencyData.individual_descriptive[metric];
  const csvRow = individualStatsRows.find(row => row.metric === metric);
  if (!csvRow || expected.n !== stored.n || expected.n !== Number(csvRow.n_individual_measurements)) {
    throw new Error(`${metric}: individual statistic count mismatch`);
  }
  for (const [key, csvKey] of [["mean", "mean"], ["median", "median"], ["min", "minimum"], ["max", "maximum"], ["skewness", "adjusted_fisher_pearson_skewness"]]) {
    if (Math.abs(expected[key] - stored[key]) > 1e-9 || Math.abs(expected[key] - Number(csvRow[csvKey])) > 1e-8) {
      throw new Error(`${metric}: ${key} mismatch`);
    }
  }
}
console.log("Individual AOD500 and AE380/500 descriptive statistics reconcile with raw observations");

const annualSummaryPath = firstExisting(
  path.join(outputDir, "aeronet_summary_data", "annual_AOD500_AE380-500_summary.csv"),
  path.join(outputDir, "data", "annual_AOD500_AE380-500_summary.csv"),
  path.join(outputDir, "data", "generated_summary", "annual_AOD500_AE380-500_summary.csv"),
);
const annualSummaryLines = fs.readFileSync(annualSummaryPath, "utf8").trim().split(/\r?\n/).map(parseCsvLine);
const annualSummaryHeaders = annualSummaryLines[0];
const annualSummaryRows = annualSummaryLines.slice(1).map(cells =>
  Object.fromEntries(annualSummaryHeaders.map((header, index) => [header, cells[index]])),
);
function meanAndStd(values) {
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.length > 1
    ? values.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / (values.length - 1)
    : 0;
  return { n: values.length, mean, std: Math.sqrt(variance) };
}
for (const [basis, rawKey] of [["daily", "daily"], ["individual", "all"]]) {
  for (const metric of ["AOD_500nm", "380-500_Angstrom_Exponent"]) {
    const metricIndex = frequencyData.raw_metric_fields.indexOf(metric) + 2;
    const values = frequencyData.raw[rawKey]
      .map(row => row[metricIndex])
      .filter(value => typeof value === "number" && Number.isFinite(value));
    const expected = meanAndStd(values);
    const row = annualSummaryRows.find(item => item.basis === basis && item.metric === metric && item.period === "All years");
    if (!row || Number(row.n) !== expected.n || Math.abs(Number(row.mean) - expected.mean) > 1e-6 || Math.abs(Number(row.standard_deviation) - expected.std) > 1e-6) {
      throw new Error(`${basis} ${metric}: annual summary mismatch`);
    }
  }
}
console.log("Annual AOD500 and AE380/500 daily/individual bases reconcile with raw observations");

const frequencyCsvPath = firstExisting(
  path.join(outputDir, "aeronet_summary_data", "frequency_distributions.csv"),
  path.join(outputDir, "data", "frequency_distributions.csv"),
  path.join(outputDir, "data", "generated_summary", "frequency_distributions.csv"),
);
const csvLines = fs.readFileSync(frequencyCsvPath, "utf8").trim().split(/\r?\n/);
const headers = csvLines[0].split(",");
const relativeIndex = headers.indexOf("relative_frequency_percent");
const cumulativeIndex = headers.indexOf("cumulative_percent");
const metricIndex = headers.indexOf("metric");
const grainIndex = headers.indexOf("grain");
const precisionPattern = /^-?\d+\.\d{4}$/;
const percentageGroups = new Map();
for (const line of csvLines.slice(1)) {
  const cells = line.split(",");
  if (!precisionPattern.test(cells[relativeIndex]) || !precisionPattern.test(cells[cumulativeIndex])) {
    throw new Error(`Frequency CSV percentage precision mismatch: ${line}`);
  }
  const key = `${cells[metricIndex]}|${cells[grainIndex]}`;
  const group = percentageGroups.get(key) || { relativeSum: 0, finalCumulative: "" };
  group.relativeSum += Number(cells[relativeIndex]);
  group.finalCumulative = cells[cumulativeIndex];
  percentageGroups.set(key, group);
}
for (const [key, group] of percentageGroups) {
  if (Math.abs(group.relativeSum - 100) > 0.02 || group.finalCumulative !== "100.0000") {
    throw new Error(`${key}: invalid percentage reconciliation`);
  }
}
if (percentageGroups.size !== 26) {
  throw new Error(`Expected 26 frequency groups under the July-only exception; found ${percentageGroups.size}`);
}
console.log(`${csvLines.length - 1} frequency rows use four decimals; ${percentageGroups.size} groups reconcile to 100.0000%`);

const dashboardDataPath = firstExisting(
  path.join(outputDir, "aeronet_summary_data_no_2022-10-21", "aeronet_dashboard_data.json"),
  path.join(outputDir, "data", "aeronet_dashboard_data_no_2022-10-21.json"),
  path.join(outputDir, "data", "generated_summary", "aeronet_dashboard_data_no_2022-10-21.json"),
);
const dashboardData = JSON.parse(fs.readFileSync(dashboardDataPath, "utf8"));
if (dashboardData.observation_count !== 117497 || dashboardData.daily.length !== 1472) {
  throw new Error(
    `July-only import scope mismatch: expected 117497 measurements and 1472 daily dates; found ${dashboardData.observation_count} and ${dashboardData.daily.length}`,
  );
}
const dashboardRows = dashboardData.daily.filter(row =>
  selected.has(`${row.year}-${String(row.month).padStart(2, "0")}`),
);

const scatterHtml = fs.readFileSync(
  path.join(outputDir, "AOD440_AE440-870_interactive_seasonal_scatter_2020-2026.html"),
  "utf8",
);
if (!scatterHtml.includes("errBottom")) throw new Error("Scatter annual charts are missing lower SD whiskers");
const payloadMatch = scatterHtml.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/i);
if (!payloadMatch) throw new Error("Scatter payload was not found");
const scatterData = JSON.parse(payloadMatch[1]);
const scatterRows = scatterData.daily.filter(row => selected.has(String(row[3]).slice(0, 7)));

const individualDataPath = firstExisting(
  path.join(outputDir, "aeronet_summary_data_no_2022-10-21", "individual_observations.csv"),
  path.join(outputDir, "data", "individual_observations_no_2022-10-21.csv"),
  path.join(outputDir, "data", "generated_summary", "individual_observations_no_2022-10-21.csv"),
);
const individualLines = fs.readFileSync(individualDataPath, "utf8").trim().split(/\r?\n/);
const individualHeaders = parseCsvLine(individualLines[0]);
const individualIndexes = Object.fromEntries(individualHeaders.map((header, index) => [header, index]));
const julyRows = individualLines.slice(1).map(parseCsvLine).filter(row => row[individualIndexes.date].startsWith("2020-07"));
const metricHeaders = individualHeaders.filter(header => header.startsWith("AOD_") || header.includes("Angstrom_Exponent"));
if (metricHeaders.length !== 13) {
  throw new Error(`Expected the established 13 channels plus the July-only row exception; found ${metricHeaders.length}`);
}

if (individualLines.length - 1 !== dashboardData.observation_count) {
  throw new Error("Individual CSV row count does not match the dashboard observation count");
}
if (julyRows.length !== 416) throw new Error(`July 2020 expected 416 unique measurements; found ${julyRows.length}`);
if (julyRows.some(row => !metricHeaders.some(metric => row[individualIndexes[metric]] !== ""))) {
  throw new Error("A July row without any available AOD/AE channel was retained");
}
for (const [metric, expected] of Object.entries({
  AOD_1020nm: 415,
  AOD_340nm: 409,
  AOD_440nm: 416,
  AOD_500nm: 416,
  "380-500_Angstrom_Exponent": 416,
  "440-870_Angstrom_Exponent": 416,
})) {
  const count = julyRows.filter(row => row[individualIndexes[metric]] !== "").length;
  if (count !== expected) throw new Error(`July 2020 ${metric}: expected ${expected}, found ${count}`);
}
if (julyRows.some(row => !row[individualIndexes.source_file].includes("supplemental_AERONET"))) {
  throw new Error("The supplied July workbook was not merged into every July observation");
}
if (individualLines.slice(1).some(line => line.startsWith(excludedDate))) {
  throw new Error("Excluded date detected in individual observations");
}
console.log("July 2020: 416 unique measurements retained with channel-specific missing values");

for (const [name, rows, periodOf, dateOf] of [
  ["frequency", frequencyRows, row => `${row[0]}-${String(row[1]).padStart(2, "0")}`, row => String(row[2] || "")],
  ["dashboard", dashboardRows, row => `${row.year}-${String(row.month).padStart(2, "0")}`, row => String(row.date || "")],
  ["scatter", scatterRows, row => String(row[3]).slice(0, 7), row => String(row[3] || "")],
]) {
  if (!rows.length) throw new Error(`${name}: selected test periods returned no rows`);
  if (rows.some(row => !selected.has(periodOf(row)))) throw new Error(`${name}: calendar-month leakage detected`);
  if (rows.some(row => dateOf(row).startsWith(excludedDate))) throw new Error(`${name}: excluded date detected`);
  console.log(`${name}: ${rows.length} daily rows limited to 2020-07 and 2021-08`);
}

console.log("Calendar-period selection verification passed.");
