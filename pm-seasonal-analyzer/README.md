# PM Seasonal Analyzer

A small desktop and command-line program for FIDAS particulate-matter export files.
It detects the metadata/header boundary automatically and analyzes every available
fraction among PM1, PM2.5, PM4, and PM10.

Dates are read from the measurement rows, never inferred from filenames. Calendar
grouping uses each interval's `date end` and `time end`; therefore an initial
December 31 interval ending at midnight on January 1 is counted in January.
The importer supports both `MM/DD/YYYY` exports with decimal points and localized
`DD.MM.YYYY` exports with trailing year markers, 24-hour times, and decimal commas.

## Install

Python 3.10 or newer is recommended.

```powershell
python -m pip install -r requirements.txt
```

## Run the desktop app

Double-click `run_pm_analyzer.bat`, or run:

```powershell
python pm_seasonal_analyzer.py --gui
```

Select one or more measurement files, choose an output folder, and click
**Analyze files**.

## Run from the command line

```powershell
python pm_seasonal_analyzer.py file1.txt file2.txt -o results
```

## Results

The output folder contains:

- `report.html`: browsable summary with all charts
- `combined_clean_data.csv`: standardized combined measurements
- `overall_statistics.csv`
- statistics grouped by season, month, hour, weekday, and year
- daily time-series, monthly, seasonal, hourly, weekday, heatmap, and boxplot PNGs

Meteorological seasons are defined as:

- Winter: December-February
- Spring: March-May
- Summer: June-August
- Autumn: September-November

Seasonal comparisons need data from the seasons being compared. A file covering
only January, for example, can show daily and hourly tendencies but cannot support
a winter-versus-summer conclusion. Full-year or multi-year input is preferable.
The seasonal chart always shows all four seasons and marks seasons with no loaded
measurements as `NO DATA`.
