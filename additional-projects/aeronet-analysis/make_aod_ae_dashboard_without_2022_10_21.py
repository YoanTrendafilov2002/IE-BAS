import json
from datetime import datetime
from pathlib import Path

import aeronet_dashboard_generator as dashboard


OUTPUT_DIR = Path(__file__).resolve().parent
DATA_DIR = OUTPUT_DIR / "aeronet_summary_data_no_2022-10-21"
APP_PATH = OUTPUT_DIR / "aeronet_aod_ae_dashboard_no_2022-10-21.html"
INDIVIDUAL_CSV_PATH = DATA_DIR / "individual_observations.csv"
EXCLUDED_DATES = {"2022-10-21"}


def build_individual_records(records, metric_fields):
    identity_fields = [
        "date",
        "time",
        "site",
        "year",
        "month",
        "month_name",
        "month_key",
        "season",
        "season_year",
        "source_file",
    ]
    return [
        {
            **{field: record.get(field, "") for field in identity_fields},
            **{metric: record.get(metric) for metric in metric_fields},
        }
        for record in records
    ]


def build_payload():
    observations, metric_fields, source_files, skipped = dashboard.scan_records()
    filtered = [record for record in observations if record["date"] not in EXCLUDED_DATES]

    aod_metrics = [metric for metric in metric_fields if metric.startswith("AOD_")]
    ae_metrics = [metric for metric in metric_fields if "Angstrom_Exponent" in metric]
    default_aod = "AOD_500nm" if "AOD_500nm" in aod_metrics else (aod_metrics[0] if aod_metrics else "")
    default_ae = (
        "440-870_Angstrom_Exponent"
        if "440-870_Angstrom_Exponent" in ae_metrics
        else (ae_metrics[0] if ae_metrics else "")
    )

    daily = dashboard.make_summary_records(
        filtered,
        ["date", "year", "month", "month_name", "season", "season_year"],
        metric_fields,
    )
    monthly = dashboard.make_summary_records(
        filtered,
        ["year", "month", "month_name", "month_key", "season", "season_year"],
        metric_fields,
    )
    month_name = dashboard.make_summary_records(filtered, ["month", "month_name"], metric_fields)
    season = dashboard.make_summary_records(filtered, ["season"], metric_fields)
    season_year = dashboard.make_summary_records(filtered, ["season_year", "season"], metric_fields)

    month_name.sort(key=lambda row: row["month"])
    season.sort(key=lambda row: dashboard.SEASON_ORDER.get(row["season"], 99))
    season_year.sort(key=lambda row: (row["season_year"], dashboard.SEASON_ORDER.get(row["season"], 99)))

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
        "source_dir": str(dashboard.SOURCE_DIR),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_files": len(source_files),
        "observation_count": len(filtered),
        "excluded_dates": sorted(EXCLUDED_DATES),
        "default_aod": default_aod,
        "default_ae": default_ae,
        "aod_metrics": aod_metrics,
        "ae_metrics": ae_metrics,
        "years": sorted({record["year"] for record in filtered}),
        "months": [{"month": idx, "name": dashboard.MONTH_NAMES[idx]} for idx in range(1, 13)],
        "seasons": ["Winter", "Spring", "Summer", "Autumn"],
        "daily": daily,
        "monthly": monthly,
        "month_name": month_name,
        "season": season,
        "season_year": season_year,
        "skipped": skipped,
    }
    return payload, build_individual_records(filtered, metric_fields)


def build_html(payload):
    html = dashboard.build_dashboard_html(payload)
    html = html.replace(
        "<title>AERONET AOD / AE Dashboard</title>",
        "<title>AERONET AOD / AE Dashboard - without 2022-10-21</title>",
    )
    html = html.replace(
        "<h1>AERONET AOD / AE Dashboard</h1>",
        "<h1>AERONET AOD / AE Dashboard - without 2022-10-21</h1>",
    )
    html = html.replace(
        "Excludes LUNAR files and files marked NO DATA.",
        "Excludes LUNAR files, files marked NO DATA, and 2022-10-21.",
    )
    html = html.replace(
        "CSV exports are saved beside this dashboard in aeronet_summary_data.",
        "CSV exports are saved beside this dashboard in aeronet_summary_data_no_2022-10-21.",
    )
    return html


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload, individual = build_payload()
    rounded = dashboard.round_data(payload)

    (DATA_DIR / "aeronet_dashboard_data.json").write_text(json.dumps(rounded, indent=2), encoding="utf-8")
    dashboard.write_csv(DATA_DIR / "daily_summary.csv", rounded["daily"])
    dashboard.write_csv(DATA_DIR / "monthly_summary.csv", rounded["monthly"])
    dashboard.write_csv(DATA_DIR / "month_name_summary.csv", rounded["month_name"])
    dashboard.write_csv(DATA_DIR / "season_summary.csv", rounded["season"])
    dashboard.write_csv(DATA_DIR / "season_year_summary.csv", rounded["season_year"])
    dashboard.write_csv(DATA_DIR / "skipped_files.csv", rounded["skipped"])
    dashboard.write_csv(INDIVIDUAL_CSV_PATH, dashboard.round_data(individual))
    APP_PATH.write_text(build_html(payload), encoding="utf-8")

    print(f"Excluded dates: {', '.join(sorted(EXCLUDED_DATES))}")
    print(f"Parsed observations after exclusions: {payload['observation_count']}")
    print(f"Individual observations exported: {len(individual)}")
    print(f"Daily rows after exclusions: {len(payload['daily'])}")
    print(f"Dashboard: {APP_PATH}")
    print(f"Data exports: {DATA_DIR}")


if __name__ == "__main__":
    main()
