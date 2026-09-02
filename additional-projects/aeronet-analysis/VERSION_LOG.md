# AERONET Output Version Log

Current version: `v2026-08-31_statistics-retrieval`

Default rule for all future regenerated outputs:
`2022-10-21` is excluded unless the raw/original version is explicitly requested.

## v2026-08-31_statistics-retrieval

Status: current working version

Main file to open:
`outputs/OPEN_THIS_FIRST.html`

Changes included:
- Adds a dedicated `Statistics` block to `OPEN_THIS_FIRST.html` with direct, selector-aware links to every statistics section.
- Expands individual-measurement descriptive statistics from two metrics to all 13 available AOD and AE channels.
- Adds sample standard deviation beside `n`, mean, median, minimum, maximum, and adjusted Fisher-Pearson skewness.
- Adds `AERONET_SSA_FMF_SDA_statistics_2020-2026.html` for separate SSA 440/675/870/1020, FMF 500, AODf500, and AODc500 analysis.
- The retrieval page supports individual or daily-mean bases and monthly, seasonal, annual, and season-of-year grouping with hover values and standard-deviation whiskers.
- Retrieval inputs exclude LUNAR files, files marked `NO DATA`, and `2022-10-21`.
- Adds CSV exports for retrieval observations, descriptive statistics, and monthly/seasonal summaries.
- Mean particle number size distributions remain deferred because the available AERONET `.siz` product is a volume size distribution, not a direct number-size product.

Frozen snapshot:
`outputs/versions/v2026-08-31_statistics-retrieval/`

## v2026-07-21_annual-daily-individual-basis

Status: current working version

Main file to open:
`outputs/OPEN_THIS_FIRST.html`

Changes included:
- Adds a Daily means / Individual measurements control to the annual AOD500 and AE380/500 bar graphs.
- Recalculates annual means, standard-deviation whiskers, table values, counts, captions, and hover details from the chosen basis.
- Exports both bases in `annual_AOD500_AE380-500_summary.csv`.
- Confirms that the underlying raw arrays match the previous version; April differences are caused by daily versus individual weighting.
- Keeps separate selector-aware individual descriptive statistics for AOD500 and AE380/500.
- Keeps the July 2020-only later-worksheet/partial-channel exception.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-21_annual-daily-individual-basis/`

## v2026-07-21_individual-descriptive-statistics

Status: previous working version

Main file to open:
`outputs/OPEN_THIS_FIRST.html`

Changes included:
- Adds separate individual-measurement descriptive statistics for AOD 500 nm and AE 380/500.
- Shows selector-aware `n`, mean, median, minimum, maximum, and adjusted Fisher-Pearson sample skewness.
- Adds `individual_AOD500_AE380-500_descriptive_statistics.csv` for all-period individual values.
- Keeps the July 2020-only later-worksheet/partial-channel exception.
- Keeps exact `YYYY-MM` selectors, four-decimal relative/cumulative percentages, and full standard-deviation whiskers.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-21_individual-descriptive-statistics/`

## v2026-07-21_july-2020-partial-only

Status: previous working version

Main file to open:
`outputs/OPEN_THIS_FIRST.html`

Changes included:
- Limits all-worksheet and missing-channel recovery to July 2020 only.
- Every other month returns to the previously accepted worksheet 1 import behavior.
- Retains 416 unique July 2020 measurements across six days, including available channels when AOD1020 or AOD340 is missing.
- Includes 117,497 measurements and 1,472 daily dates after excluding `2022-10-21`.
- Restores the established 13 AOD/AE channels and 26 individual/daily frequency groups.
- Keeps exact `YYYY-MM` selectors, four-decimal relative/cumulative percentages, and full standard-deviation whiskers.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-21_july-2020-partial-only/`

## v2026-07-21_all-channels-calendar-frequency

Status: previous working version

Main file to open:
`outputs/OPEN_THIS_FIRST.html`

Changes included:
- Scans every worksheet in each AOD/AE workbook instead of reading only the first worksheet.
- Retains every observation with at least one available AOD or AE channel; missing channels remain unavailable and use channel-specific `n` values.
- Merges duplicate site/date/time observations across worksheet variants and duplicate workbooks, filling missing channels without double-counting.
- Adds the exact supplied `2020 July AOD, AE 1.5_1 (1).xlsx` workbook and includes its 416 unique July 2020 measurements across six days.
- Uses one canonical individual-observation export for the dashboard, scatter, frequency distributions, and full package.
- Includes 120,596 measurements after excluding `2022-10-21`, 1,502 daily dates, and 29 AOD/AE channels with available values.
- Uses individual `YYYY-MM` controls in the frequency page and launcher.
- Formats both relative frequency and cumulative percentage to four decimal places.
- Uses full mean plus/minus standard deviation whiskers on repeated annual bar graphs.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-21_all-channels-calendar-frequency/`

## v2026-07-21_individual-calendar-month-selector

Status: previous working version

Main file to open:
`outputs/OPEN_THIS_FIRST.html`

Changes included:
- Replaced separate month-name and year selectors with one calendar matrix containing every available `YYYY-MM` period.
- Each calendar month can be kept or removed independently, so July 2020 can be selected without selecting July in any other year.
- Year labels toggle all available months in that year; quick actions keep all, remove all, keep all summers, or keep all winters.
- Launcher links pass an exact `periods=YYYY-MM,...` selection to the scatter, frequency, and no-date dashboard pages.
- All graphs, annual summaries, percentages, frequency distributions, overall means, and the daily aerosol table use the exact selected periods.
- Added `verify_calendar_period_selection.js`; its uneven July 2020 plus August 2021 test reconciles to 31 daily rows in all three dashboard datasets.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-21_individual-calendar-month-selector/`

## v2026-07-21_year-selector-retrieval-table

Status: previous working version

Main file to open:
`outputs/OPEN_THIS_FIRST.html`

Changes included:
- Launcher selector now supports both months and years.
- Launcher graph links pass `months=` and `years=` to the scatter, frequency, and no-date dashboard pages.
- The similar daily mean table now parses SDA fine/coarse AOD500 and inversion SF, DR440, and real refractive index at 440 nm where available.
- Frequency distributions include visible year buttons; scatter and no-date dashboard initialize from launcher-selected years.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-21_year-selector-retrieval-table/`

## v2026-07-21_open-first-data-selector

Status: previous working version

Main file to open:
`outputs/OPEN_THIS_FIRST.html`

Changes included:
- Added a month data selector on `OPEN_THIS_FIRST.html`.
- Added a Table 4-style daily mean aerosol table derived from this AERONET dataset to `OPEN_THIS_FIRST.html`.
- Dashboard links opened from the launcher carry the selected months in the URL.
- Frequency distributions initialize from the launcher month selection and still support local month changes.
- The seasonal scatter dashboard filters points, aerosol composition table, annual bars, and overall mean cards by the launcher month selection.
- The broad AOD/AE dashboard reads the launcher month selection for daily/monthly views and seeds its own month filter when one month is selected.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-21_open-first-data-selector/`

## v2026-07-21_frequency-month-cumulative

Status: previous working version

Main file to open:
`outputs/AOD_AE_frequency_distributions_2020-2026.html`

Changes included:
- Added month buttons so selected months are applied before frequency and annual calculations.
- Added cumulative percentage view and a `Cumulative %` column to the frequency table.
- Added yearly and all-years daily mean summaries for AOD 500 nm and AE 380/500.
- Frequency exports now include cumulative frequency count and cumulative percent.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-21_frequency-month-cumulative/`

## v2026-07-20_visible-annual-grain

Status: previous working version

Main file to open:
`outputs/AOD440_AE440-870_interactive_seasonal_scatter_2020-2026.html`

Changes included:
- Annual AOD440 and AE440/870 bar charts now use the same vertical scale for daily means and individual measurements.
- Annual mean values are printed above each yearly bar.
- Annual chart title includes the current basis: daily means or individual measurements.
- This makes the annual values visibly change when switching data grain.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-20_visible-annual-grain/`

## v2026-07-20_overall-mean

Status: current working version

Main file to open:
`outputs/AOD440_AE440-870_interactive_seasonal_scatter_2020-2026.html`

Changes included:
- Added all-data mean cards for AOD440 and AE440/870 in the annual bar graph section.
- Overall mean cards switch between daily means and individual measurements.
- Overall cards show standard deviation and `n days` or `n measurements`.
- Added `overall_AOD440_AE440-870_basis_summary.csv` with daily and individual all-data means.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-20_overall-mean/`

## v2026-07-20_annual-basis-toggle

Status: current working version

Main file to open:
`outputs/AOD440_AE440-870_interactive_seasonal_scatter_2020-2026.html`

Changes included:
- Annual AOD440 and AE440/870 bar graphs now switch between daily means and individual measurements.
- The annual section has its own Daily means / Individual buttons.
- Switching the main scatter between Daily means and Individual also updates the annual bar basis.
- Annual table and hover tooltips show `n days` for daily means and `n measurements` for individual measurements.
- Added `annual_AOD440_AE440-870_basis_summary.csv` with yearly daily and individual annual summaries.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-20_annual-basis-toggle/`

## v2026-07-20_annual-bars

Status: current working version

Main file to open:
`outputs/AOD440_AE440-870_interactive_seasonal_scatter_2020-2026.html`

Changes included:
- Seasonal AOD440 vs AE440/870 interactive scatter.
- Aerosol type table with the latest categories: Dust, BB, Urban, Continental, Mixed.
- No Unclassified category.
- Composition margin guide lines on the scatter plot.
- Embedded annual mean bar graphs for AOD440 and AE440/870.
- Annual bar whiskers show standard deviation from daily means.
- Hover tooltips on scatter points and annual bars.
- `2022-10-21` excluded.

Frozen snapshot:
`outputs/versions/v2026-07-20_annual-bars/`

## Related Current Files

- `outputs/AOD440_AE440-870_interactive_seasonal_scatter_2020-2026.html`
- `outputs/AOD_AE_frequency_distributions_2020-2026.html`
- `outputs/aeronet_aod_ae_dashboard_no_2022-10-21.html`
- `outputs/aeronet_summary_data/annual_AOD440_AE440-870_scatter_summary.csv`
- `outputs/aeronet_summary_data/annual_AOD440_AE440-870_basis_summary.csv`
- `outputs/aeronet_summary_data/overall_AOD440_AE440-870_basis_summary.csv`
- `outputs/aeronet_summary_data/frequency_distributions.csv`
- `outputs/aeronet_summary_data/annual_AOD500_AE380-500_summary.csv`

## Versioning Workflow

Use the root `outputs/` files as latest/editable working files.

When a version is accepted, copy the latest files into:
`outputs/versions/vYYYY-MM-DD_short-description/`

Every accepted version should include:
- main HTML outputs
- relevant CSV exports
- generator scripts
- a manifest
- a short entry in this log
