# IE-BAS Atmospheric Data Tools

Portable, sanitized source packages for atmospheric observation, satellite,
aerosol, particulate-matter, and website workflows.

Each directory is an independent project with its own dependencies and run
instructions:

- `stringmeteo-scraper`: Selenium scraper for station 15614 observations.
- `wyoming-soundings`: University of Wyoming sounding downloader.
- `station-parsers`: C/C++ Lufft and Vaisala log parsers.
- `monarch-dust`: AEMET MONARCH forecast extraction and C++ graphing.
- `modis-hdf-reader`: HDF4/HDF5/netCDF inspection and text export.
- `earthcare-tracking`: EarthCARE ground-track proximity calculator.
- `pm-binary-decode`: Diagnostic decoder for binary PM instrument files.
- `pm-seasonal-analyzer`: Desktop/CLI seasonal analysis for FIDAS exports.
- `modis-aerosol-extractor`: Streamlit MODIS Deep Blue extractor.

## Privacy and reproducibility

Credentials, password hashes, local virtual environments, compiled debug
artifacts, caches, and generated result archives are intentionally excluded.
Copy each `*.example` configuration file to its local name and add private
values only on your own machine.

Python projects recommend Python 3.10 or newer. Install dependencies from the
`requirements.txt` in the project directory.

## Additional projects

The [`additional-projects`](additional-projects/) directory contains sanitized
source snapshots of the newer embedded, desktop, web, data-analysis, WordPress,
FPGA-reporting, and document-tooling projects collected from the local workspace.
