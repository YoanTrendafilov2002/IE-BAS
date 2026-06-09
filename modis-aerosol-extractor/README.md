# MODIS Aerosol Extractor

A small browser tool that extracts monthly MODIS Collection 6.1 Deep Blue:

- aerosol optical depth (AOD) at 550 nm
- Angstrom exponent over land

The default point is central Sofia, Bulgaria (`42.6977 N, 23.3219 E`). The tool can
also sample any other latitude and longitude.

## Data

The app uses NASA's 1-degree monthly Level-3 products in Google Earth Engine:

- Terra: `MODIS/061/MOD08_M3`
- Aqua: `MODIS/061/MYD08_M3`

Both variables come from the Deep Blue algorithm, so the AOD and Angstrom exponent
are scientifically consistent. Values are monthly grid-cell averages, not direct
ground measurements or neighborhood-scale estimates.

## Setup

1. Install Python 3.10 or newer.
2. Create and activate a virtual environment.
3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Register for Google Earth Engine and authenticate:

   ```powershell
   earthengine authenticate
   ```

5. Run the app:

   ```powershell
   streamlit run app.py
   ```

If Earth Engine asks for a Cloud project, enter its project ID in the app sidebar
or set `EARTHENGINE_PROJECT`.

## Output

The app displays a time-series chart and table and downloads a CSV containing:

`date`, `platform`, `aod_550_nm`, `angstrom_exponent`, `latitude`, `longitude`.

Missing values are retained because cloud, snow, or failed retrievals are meaningful
parts of the satellite record.

## Scientific references

- NASA MODIS Aerosol product: https://atmosphere-imager.gsfc.nasa.gov/products/aerosol
- NASA Deep Blue data fields: https://earth.gsfc.nasa.gov/climate/data/deep-blue/data
- Earth Engine MODIS catalog: https://developers.google.com/earth-engine/datasets/catalog/modis

