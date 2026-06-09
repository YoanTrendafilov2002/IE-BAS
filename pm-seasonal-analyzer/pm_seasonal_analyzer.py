from __future__ import annotations

import argparse
import html
import os
import re
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Callable, Iterable

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "pm_seasonal_analyzer_matplotlib"))

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
except ImportError as exc:
    print(
        "Missing Python packages. Run: python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


SEASON_ORDER = ["Winter", "Spring", "Summer", "Autumn"]
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_ORDER = list(range(1, 13))
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
COLORS = ["#2463A6", "#E07A1F", "#398B5A", "#A5447C", "#6A5ACD", "#6B7280"]
ENCODINGS = ("utf-8-sig", "utf-16", "cp1252", "latin-1")


def _clean_header(value: str) -> str:
    return value.strip().lstrip("\ufeff")


def _find_header_line(path: Path) -> tuple[int, list[str], str]:
    failures: list[str] = []
    for encoding in ENCODINGS:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                for line_number, line in enumerate(handle):
                    fields = [_clean_header(item) for item in line.rstrip("\r\n").split("\t")]
                    lower = [item.lower() for item in fields]
                    if "date beginning" in lower and "time beginning" in lower:
                        return line_number, fields, encoding
        except UnicodeError as exc:
            failures.append(f"{encoding}: {exc}")
    detail = "; ".join(failures)
    raise ValueError(
        "Could not decode the file or find the tab-delimited FIDAS header."
        + (f" Tried: {detail}" if detail else "")
    )


def _pm_label(column: str) -> str | None:
    text = column.lower().replace(" ", "")
    patterns = [
        (r"pm(?:_enviro_\d+-)?pm?10(?:[_.-]|ambient|$)", "PM10"),
        (r"pm(?:_enviro_\d+-)?pm?4(?:[_.-]|ambient|$)", "PM4"),
        (r"pm(?:_enviro_\d+-)?pm?2[._]?5(?:[_.-]|ambient|$)", "PM2.5"),
        (r"pm(?:_enviro_\d+-)?pm?1(?:[_.-]|ambient|$)", "PM1"),
    ]
    # FIDAS names normally contain " - PM1_ambient - ". These direct checks
    # also support shortened headers from manually exported CSV files.
    direct = [
        (r"(^|[-_])pm10([_ -]|$)", "PM10"),
        (r"(^|[-_])pm4([_ -]|$)", "PM4"),
        (r"(^|[-_])pm2[._]?5([_ -]|$)", "PM2.5"),
        (r"(^|[-_])pm1([_ -]|$)", "PM1"),
    ]
    normalized = column.lower().strip()
    for pattern, label in direct:
        if re.search(pattern, normalized):
            return label
    for pattern, label in patterns:
        if re.search(pattern, text):
            return label
    return None


def _detect_date_format(values: pd.Series) -> str:
    # Dot-separated FIDAS exports use DD.MM.YYYY. Slash-separated exports are
    # commonly MM/DD/YYYY, unless an unambiguous day greater than 12 proves DMY.
    for value in values.dropna().astype(str):
        match = re.search(r"(\d{1,2})([./-])(\d{1,2})\2(\d{4})", value)
        if not match:
            continue
        first, separator, second = int(match.group(1)), match.group(2), int(match.group(3))
        if separator == ".":
            return "%d/%m/%Y"
        if first > 12 and second <= 12:
            return "%d/%m/%Y"
        if second > 12 and first <= 12:
            return "%m/%d/%Y"
    return "%m/%d/%Y"


def _parse_timestamp(date_values: pd.Series, time_values: pd.Series, date_format: str) -> pd.Series:
    dates = date_values.astype(str).str.extract(
        r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", expand=True
    )
    normalized_date = dates[0] + "/" + dates[1] + "/" + dates[2]
    times = time_values.astype(str).str.extract(
        r"(\d{1,2}:\d{2}:\d{2})(?:\s*([APap][Mm]))?", expand=True
    )
    normalized_time = times[0]
    has_ampm = times[1].notna()
    normalized_time = normalized_time.where(
        ~has_ampm, normalized_time + " " + times[1].str.upper()
    )
    normalized_raw = normalized_date + " " + normalized_time
    time_format = "%I:%M:%S %p" if has_ampm.any() else "%H:%M:%S"
    return pd.to_datetime(
        normalized_raw,
        format=f"{date_format} {time_format}",
        errors="coerce",
    )


def _parse_numeric(values: pd.Series) -> pd.Series:
    normalized = values.astype(str).str.strip().str.replace("\u00a0", "", regex=False)
    comma_decimal = normalized.str.contains(",", regex=False)
    normalized = normalized.where(
        ~comma_decimal,
        normalized.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    return pd.to_numeric(normalized, errors="coerce")


def read_measurement_file(path: Path) -> pd.DataFrame:
    header_line, _, encoding = _find_header_line(path)
    frame = pd.read_csv(
        path,
        sep="\t",
        skiprows=header_line,
        engine="python",
        encoding=encoding,
        on_bad_lines="skip",
    )
    frame.columns = [_clean_header(str(column)) for column in frame.columns]
    frame = frame.loc[:, [column for column in frame.columns if column and not column.startswith("Unnamed:")]]

    lower_to_original: dict[str, str] = {}
    for column in frame.columns:
        lower_to_original.setdefault(column.lower(), column)
    start_date_column = lower_to_original.get("date beginning")
    start_time_column = lower_to_original.get("time beginning")
    end_date_column = lower_to_original.get("date end")
    end_time_column = lower_to_original.get("time end")
    if not start_date_column or not start_time_column:
        raise ValueError("Missing 'date beginning' or 'time beginning' columns.")

    pm_columns: dict[str, str] = {}
    for column in frame.columns:
        label = _pm_label(column)
        if label and label not in pm_columns:
            pm_columns[label] = column
    if not pm_columns:
        raise ValueError("No PM1, PM2.5, PM4, or PM10 columns were found.")

    result = pd.DataFrame()
    date_samples = frame[start_date_column]
    if end_date_column:
        date_samples = pd.concat([date_samples, frame[end_date_column]], ignore_index=True)
    date_format = _detect_date_format(date_samples)
    result["interval_start"] = _parse_timestamp(
        frame[start_date_column], frame[start_time_column], date_format
    )
    if end_date_column and end_time_column:
        result["interval_end"] = _parse_timestamp(
            frame[end_date_column], frame[end_time_column], date_format
        )
    else:
        result["interval_end"] = pd.NaT

    # Calendar statistics use the interval end. This assigns the initial
    # Dec 31 -> Jan 1 boundary record to January, where the measurement ends.
    result["timestamp"] = result["interval_end"].fillna(result["interval_start"])
    for label, column in pm_columns.items():
        result[label] = _parse_numeric(frame[column])
    result["source_file"] = path.name
    result = result.dropna(subset=["timestamp"])
    result = result.sort_values("timestamp")
    return result


def _season_for_month(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Autumn"


def _save_figure(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _plot_time_series(data: pd.DataFrame, pm_columns: list[str], output: Path) -> None:
    daily = data.set_index("timestamp")[pm_columns].resample("D").mean()
    fig, ax = plt.subplots(figsize=(13, 6))
    for index, column in enumerate(pm_columns):
        ax.plot(daily.index, daily[column], label=column, color=COLORS[index], linewidth=1.5)
    ax.set(title="Daily mean particulate matter", xlabel="Date", ylabel="Concentration")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.grid(alpha=0.25)
    ax.legend(ncol=min(4, len(pm_columns)))
    _save_figure(fig, output / "01_daily_time_series.png")


def _plot_monthly(data: pd.DataFrame, pm_columns: list[str], output: Path) -> None:
    monthly = data.groupby("month")[pm_columns].mean().reindex(MONTH_ORDER)
    fig, ax = plt.subplots(figsize=(12, 6))
    for index, column in enumerate(pm_columns):
        ax.plot(MONTH_ORDER, monthly[column], marker="o", label=column, color=COLORS[index])
    ax.set(title="Monthly mean profile", xlabel="Month", ylabel="Mean concentration", xticks=MONTH_ORDER)
    ax.set_xticklabels(MONTH_LABELS)
    ax.grid(alpha=0.25)
    ax.legend()
    _save_figure(fig, output / "02_monthly_profile.png")


def _plot_seasons(data: pd.DataFrame, pm_columns: list[str], output: Path) -> None:
    seasonal = data.groupby("season", observed=False)[pm_columns].mean().reindex(SEASON_ORDER)
    counts = data.groupby("season", observed=False).size().reindex(SEASON_ORDER, fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(SEASON_ORDER))
    width = 0.78 / len(pm_columns)
    for index, column in enumerate(pm_columns):
        positions = x - 0.39 + width / 2 + index * width
        ax.bar(
            positions,
            seasonal[column].fillna(0),
            width=width,
            label=column,
            color=COLORS[index],
        )
    for index, season in enumerate(SEASON_ORDER):
        if counts.loc[season] == 0:
            ax.text(
                index,
                0.03,
                "NO DATA",
                rotation=90,
                ha="center",
                va="bottom",
                color="#9A3412",
                fontweight="bold",
                transform=ax.get_xaxis_transform(),
            )
    ax.set(title="Mean concentration by meteorological season", xlabel="", ylabel="Mean concentration")
    ax.set_xticks(x, SEASON_ORDER)
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    _save_figure(fig, output / "03_seasonal_means.png")


def _plot_hourly(data: pd.DataFrame, pm_columns: list[str], output: Path) -> None:
    hourly = data.groupby("hour")[pm_columns].mean().reindex(range(24))
    fig, ax = plt.subplots(figsize=(12, 6))
    for index, column in enumerate(pm_columns):
        ax.plot(hourly.index, hourly[column], marker=".", label=column, color=COLORS[index])
    ax.set(title="Average daily cycle", xlabel="Hour of day", ylabel="Mean concentration", xticks=range(0, 24, 2))
    ax.grid(alpha=0.25)
    ax.legend()
    _save_figure(fig, output / "04_hourly_profile.png")


def _plot_weekday(data: pd.DataFrame, pm_columns: list[str], output: Path) -> None:
    weekday = data.groupby("weekday", observed=False)[pm_columns].mean().reindex(WEEKDAY_ORDER)
    fig, ax = plt.subplots(figsize=(11, 6))
    weekday.plot(kind="bar", ax=ax, color=COLORS[: len(pm_columns)], width=0.8)
    ax.set(title="Mean concentration by weekday", xlabel="", ylabel="Mean concentration")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.25)
    _save_figure(fig, output / "05_weekday_profile.png")


def _plot_heatmaps(data: pd.DataFrame, pm_columns: list[str], output: Path) -> None:
    fig, axes = plt.subplots(
        len(pm_columns),
        1,
        figsize=(13, max(4, 3.4 * len(pm_columns))),
        squeeze=False,
    )
    for index, column in enumerate(pm_columns):
        matrix = data.pivot_table(index="month", columns="hour", values=column, aggfunc="mean")
        matrix = matrix.reindex(index=MONTH_ORDER, columns=range(24))
        image = axes[index, 0].imshow(matrix, aspect="auto", cmap="viridis", interpolation="nearest")
        axes[index, 0].set_title(f"{column}: mean concentration by month and hour")
        axes[index, 0].set_ylabel("Month")
        axes[index, 0].set_yticks(range(12), MONTH_LABELS)
        axes[index, 0].set_xlabel("Hour of day")
        axes[index, 0].set_xticks(range(0, 24, 2))
        fig.colorbar(image, ax=axes[index, 0], label="Mean concentration")
    _save_figure(fig, output / "06_month_hour_heatmaps.png")


def _plot_seasonal_boxplots(data: pd.DataFrame, pm_columns: list[str], output: Path) -> None:
    fig, axes = plt.subplots(1, len(pm_columns), figsize=(max(8, 4 * len(pm_columns)), 6), squeeze=False)
    for index, column in enumerate(pm_columns):
        values = [
            data.loc[data["season"] == season, column].dropna().to_numpy()
            for season in SEASON_ORDER
        ]
        axes[0, index].boxplot(values, tick_labels=SEASON_ORDER, showfliers=False)
        axes[0, index].set_title(column)
        axes[0, index].set_ylabel("Concentration")
        axes[0, index].tick_params(axis="x", rotation=25)
        axes[0, index].grid(axis="y", alpha=0.25)
    fig.suptitle("Seasonal distributions (outliers hidden for readability)")
    _save_figure(fig, output / "07_seasonal_boxplots.png")


def _write_group_statistics(
    data: pd.DataFrame,
    pm_columns: list[str],
    group_column: str,
    output_path: Path,
    order: Iterable | None = None,
) -> None:
    grouped = data.groupby(group_column, observed=False)[pm_columns].agg(
        ["count", "mean", "median", "std", "min", "max"]
    )
    grouped.columns = [f"{pm}_{stat}" for pm, stat in grouped.columns]
    if order is not None:
        grouped = grouped.reindex(list(order))
    grouped.to_csv(output_path, float_format="%.4f")


def _build_report(
    data: pd.DataFrame,
    pm_columns: list[str],
    output: Path,
    file_results: list[tuple[str, int, str]],
) -> None:
    start = data["timestamp"].min()
    end = data["timestamp"].max()
    covered_months = sorted(data["month"].unique())
    covered_seasons = [season for season in SEASON_ORDER if season in set(data["season"].astype(str))]
    season_counts = data.groupby("season", observed=False).size().reindex(SEASON_ORDER, fill_value=0)
    season_coverage_rows = "".join(
        f"<tr><td>{season}</td><td>{'Dec-Feb' if season == 'Winter' else 'Mar-May' if season == 'Spring' else 'Jun-Aug' if season == 'Summer' else 'Sep-Nov'}</td>"
        f"<td>{int(season_counts.loc[season]):,}</td><td>{'Available' if season_counts.loc[season] else 'No data loaded'}</td></tr>"
        for season in SEASON_ORDER
    )
    rows = []
    for column in pm_columns:
        values = data[column].dropna()
        rows.append(
            f"<tr><td>{html.escape(column)}</td><td>{len(values):,}</td>"
            f"<td>{values.mean():.3f}</td><td>{values.median():.3f}</td>"
            f"<td>{values.std():.3f}</td><td>{values.min():.3f}</td><td>{values.max():.3f}</td></tr>"
        )
    file_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{count:,}</td><td>{html.escape(status)}</td></tr>"
        for name, count, status in file_results
    )
    image_names = [
        "01_daily_time_series.png",
        "02_monthly_profile.png",
        "03_seasonal_means.png",
        "04_hourly_profile.png",
        "05_weekday_profile.png",
        "06_month_hour_heatmaps.png",
        "07_seasonal_boxplots.png",
    ]
    images = "".join(
        f'<section><img src="{name}" alt="{html.escape(name)}"></section>' for name in image_names
    )
    warning = ""
    if len(covered_months) < 12:
        warning = (
            '<div class="warning"><strong>Coverage note:</strong> This dataset covers '
            f"{len(covered_months)} of 12 months and {len(covered_seasons)} season(s). "
            "Seasonal conclusions become reliable only when the relevant seasons are represented, "
            "preferably across multiple years.</div>"
        )
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PM Seasonal Analysis</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 32px auto; padding: 0 20px; color: #18212b; }}
h1, h2 {{ color: #173f68; }}
.summary {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; }}
.card {{ background: #eef4f9; border-radius: 8px; padding: 12px 16px; }}
.warning {{ background: #fff4d6; border-left: 5px solid #d59b13; padding: 14px; margin: 18px 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0 28px; }}
th, td {{ border: 1px solid #ccd6df; padding: 8px; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
img {{ width: 100%; height: auto; border: 1px solid #d8e0e7; margin: 12px 0 28px; }}
.small {{ color: #52606d; }}
</style>
</head>
<body>
<h1>Particulate Matter Seasonal Analysis</h1>
<div class="summary">
  <div class="card"><strong>Period</strong><br>{start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M}</div>
  <div class="card"><strong>Valid rows</strong><br>{len(data):,}</div>
  <div class="card"><strong>PM fractions</strong><br>{", ".join(pm_columns)}</div>
  <div class="card"><strong>Months represented</strong><br>{", ".join(MONTH_LABELS[m - 1] for m in covered_months)}</div>
</div>
{warning}
<h2>Season coverage</h2>
<table><thead><tr><th>Season</th><th>Months</th><th>Rows</th><th>Status</th></tr></thead>
<tbody>{season_coverage_rows}</tbody></table>
<h2>Overall statistics</h2>
<table><thead><tr><th>Fraction</th><th>Count</th><th>Mean</th><th>Median</th><th>Std. dev.</th><th>Min</th><th>Max</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
<h2>Input files</h2>
<table><thead><tr><th>File</th><th>Rows loaded</th><th>Status</th></tr></thead><tbody>{file_rows}</tbody></table>
<h2>Charts</h2>
{images}
<p class="small">Meteorological seasons: Winter = Dec-Feb, Spring = Mar-May, Summer = Jun-Aug, Autumn = Sep-Nov.</p>
</body></html>"""
    (output / "report.html").write_text(document, encoding="utf-8")


def analyze_files(
    input_paths: Iterable[Path],
    output: Path,
    progress: Callable[[str], None] = print,
) -> dict[str, object]:
    paths = [Path(path) for path in input_paths]
    if not paths:
        raise ValueError("No input files selected.")
    output.mkdir(parents=True, exist_ok=True)

    loaded: list[pd.DataFrame] = []
    file_results: list[tuple[str, int, str]] = []
    errors: list[str] = []
    for path in paths:
        progress(f"Reading {path.name}...")
        try:
            frame = read_measurement_file(path)
            loaded.append(frame)
            file_results.append((path.name, len(frame), "Loaded"))
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            file_results.append((path.name, 0, f"Skipped: {exc}"))
    if not loaded:
        raise ValueError("None of the selected files could be read.\n" + "\n".join(errors))

    data = pd.concat(loaded, ignore_index=True, sort=False)
    pm_columns = [column for column in ["PM1", "PM2.5", "PM4", "PM10"] if column in data.columns]
    for column in pm_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        data.loc[data[column] < 0, column] = np.nan
    data = data.drop_duplicates(subset=["timestamp", *pm_columns]).sort_values("timestamp")
    data["year"] = data["timestamp"].dt.year
    data["month"] = data["timestamp"].dt.month
    data["month_name"] = data["timestamp"].dt.month_name()
    data["season"] = pd.Categorical(
        data["month"].map(_season_for_month), categories=SEASON_ORDER, ordered=True
    )
    data["hour"] = data["timestamp"].dt.hour
    data["weekday"] = pd.Categorical(
        data["timestamp"].dt.day_name(), categories=WEEKDAY_ORDER, ordered=True
    )

    progress("Writing cleaned data and statistics...")
    export_columns = ["timestamp", "interval_start", "interval_end", "source_file", *pm_columns]
    data[export_columns].to_csv(output / "combined_clean_data.csv", index=False, float_format="%.6f")
    data[pm_columns].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T.to_csv(
        output / "overall_statistics.csv", float_format="%.4f"
    )
    _write_group_statistics(data, pm_columns, "season", output / "statistics_by_season.csv", SEASON_ORDER)
    _write_group_statistics(data, pm_columns, "month", output / "statistics_by_month.csv", MONTH_ORDER)
    _write_group_statistics(data, pm_columns, "hour", output / "statistics_by_hour.csv", range(24))
    _write_group_statistics(data, pm_columns, "weekday", output / "statistics_by_weekday.csv", WEEKDAY_ORDER)
    _write_group_statistics(data, pm_columns, "year", output / "statistics_by_year.csv")

    progress("Creating charts...")
    _plot_time_series(data, pm_columns, output)
    _plot_monthly(data, pm_columns, output)
    _plot_seasons(data, pm_columns, output)
    _plot_hourly(data, pm_columns, output)
    _plot_weekday(data, pm_columns, output)
    _plot_heatmaps(data, pm_columns, output)
    _plot_seasonal_boxplots(data, pm_columns, output)
    _build_report(data, pm_columns, output, file_results)

    progress("Analysis complete.")
    return {
        "rows": len(data),
        "start": data["timestamp"].min(),
        "end": data["timestamp"].max(),
        "pm_columns": pm_columns,
        "errors": errors,
        "covered_months": sorted(data["month"].unique().tolist()),
        "covered_seasons": [
            season
            for season in SEASON_ORDER
            if int((data["season"] == season).sum()) > 0
        ],
        "output": output,
    }


def launch_gui() -> None:
    import threading
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("PM Seasonal Analyzer")
    root.geometry("780x560")
    root.minsize(680, 480)

    selected_files: list[Path] = []
    output_var = tk.StringVar(value=str(Path.cwd() / "pm_analysis_output"))
    status_var = tk.StringVar(value="Select one or more FIDAS export files.")

    container = ttk.Frame(root, padding=18)
    container.pack(fill="both", expand=True)
    ttk.Label(container, text="PM Seasonal Analyzer", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(
        container,
        text="Load FIDAS text exports and generate seasonal, monthly, hourly, and weekday statistics.",
        wraplength=720,
    ).pack(anchor="w", pady=(4, 14))

    list_frame = ttk.LabelFrame(container, text="Input files", padding=10)
    list_frame.pack(fill="both", expand=True)
    file_list = tk.Listbox(list_frame, height=10)
    file_list.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=file_list.yview)
    scrollbar.pack(side="right", fill="y")
    file_list.configure(yscrollcommand=scrollbar.set)

    def choose_files() -> None:
        chosen = filedialog.askopenfilenames(
            title="Select measurement files",
            filetypes=[("Measurement files", "*.txt *.csv *.tsv"), ("All files", "*.*")],
        )
        for name in chosen:
            path = Path(name)
            if path not in selected_files:
                selected_files.append(path)
                file_list.insert("end", str(path))
        status_var.set(f"{len(selected_files)} file(s) selected.")

    def clear_files() -> None:
        selected_files.clear()
        file_list.delete(0, "end")
        status_var.set("Select one or more FIDAS export files.")

    button_row = ttk.Frame(container)
    button_row.pack(fill="x", pady=(10, 12))
    ttk.Button(button_row, text="Add files...", command=choose_files).pack(side="left")
    ttk.Button(button_row, text="Clear", command=clear_files).pack(side="left", padx=8)

    output_row = ttk.LabelFrame(container, text="Output folder", padding=10)
    output_row.pack(fill="x")
    ttk.Entry(output_row, textvariable=output_var).pack(side="left", fill="x", expand=True)

    def choose_output() -> None:
        chosen = filedialog.askdirectory(title="Choose output folder")
        if chosen:
            output_var.set(chosen)

    ttk.Button(output_row, text="Browse...", command=choose_output).pack(side="left", padx=(8, 0))
    progress_bar = ttk.Progressbar(container, mode="indeterminate")
    progress_bar.pack(fill="x", pady=(14, 5))
    ttk.Label(container, textvariable=status_var, wraplength=720).pack(anchor="w")

    def set_status(message: str) -> None:
        root.after(0, status_var.set, message)

    def finish_success(result: dict[str, object]) -> None:
        progress_bar.stop()
        analyze_button.configure(state="normal")
        error_note = ""
        if result["errors"]:
            error_note = f"\n\n{len(result['errors'])} file(s) were skipped. See the report for details."
        missing_seasons = [
            season for season in SEASON_ORDER if season not in result["covered_seasons"]
        ]
        coverage_note = ""
        if missing_seasons:
            coverage_note = (
                "\n\nNo measurements were loaded for: "
                + ", ".join(missing_seasons)
                + ". Add files containing the corresponding months to calculate them."
            )
        messagebox.showinfo(
            "Analysis complete",
            f"Processed {result['rows']:,} rows from {result['start']:%Y-%m-%d} "
            f"to {result['end']:%Y-%m-%d}.\n\nResults:\n{result['output']}"
            f"{coverage_note}{error_note}",
        )

    def finish_error(exc: Exception) -> None:
        progress_bar.stop()
        analyze_button.configure(state="normal")
        status_var.set("Analysis failed.")
        messagebox.showerror("Analysis failed", f"{exc}\n\n{traceback.format_exc()}")

    def run_analysis() -> None:
        if not selected_files:
            messagebox.showwarning("No files", "Please select at least one measurement file.")
            return
        output = Path(output_var.get().strip())
        if not str(output):
            messagebox.showwarning("No output folder", "Please choose an output folder.")
            return
        analyze_button.configure(state="disabled")
        progress_bar.start(12)

        def worker() -> None:
            try:
                result = analyze_files(selected_files, output, set_status)
                root.after(0, finish_success, result)
            except Exception as exc:
                root.after(0, finish_error, exc)

        threading.Thread(target=worker, daemon=True).start()

    analyze_button = ttk.Button(container, text="Analyze files", command=run_analysis)
    analyze_button.pack(anchor="e", pady=(12, 0))
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze seasonal tendencies in FIDAS PM exports.")
    parser.add_argument("files", nargs="*", type=Path, help="Input .txt/.csv/.tsv files")
    parser.add_argument("-o", "--output", type=Path, default=Path("pm_analysis_output"))
    parser.add_argument("--gui", action="store_true", help="Open the desktop interface")
    args = parser.parse_args()
    if args.gui or not args.files:
        launch_gui()
    else:
        result = analyze_files(args.files, args.output)
        print(f"Processed {result['rows']:,} rows. Results: {result['output'].resolve()}")


if __name__ == "__main__":
    main()
