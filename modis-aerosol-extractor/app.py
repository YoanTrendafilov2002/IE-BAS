"""Streamlit interface for the MODIS aerosol point extractor."""

from __future__ import annotations

import os
from datetime import date

import streamlit as st

from modis_aerosol import extract_monthly, initialize_earth_engine


SOFIA_LATITUDE = 42.6977
SOFIA_LONGITUDE = 23.3219

st.set_page_config(page_title="MODIS Aerosol Extractor")
st.title("MODIS AOD and Angstrom Exponent")
st.caption(
    "Monthly MODIS Collection 6.1 Deep Blue aerosol values for a selected location."
)

with st.sidebar:
    st.header("Location and dates")
    latitude = st.number_input(
        "Latitude", min_value=-90.0, max_value=90.0, value=SOFIA_LATITUDE, format="%.5f"
    )
    longitude = st.number_input(
        "Longitude",
        min_value=-180.0,
        max_value=180.0,
        value=SOFIA_LONGITUDE,
        format="%.5f",
    )
    start_date = st.date_input("Start date", value=date(2020, 1, 1))
    end_date = st.date_input("End date", value=date.today())
    platforms = st.multiselect(
        "Satellites", ["Terra", "Aqua"], default=["Terra", "Aqua"]
    )
    project = st.text_input(
        "Earth Engine project",
        value=os.getenv("EARTHENGINE_PROJECT", ""),
        help="Optional when your authenticated account has a default project.",
    )
    extract = st.button("Extract data", type="primary", use_container_width=True)

st.info(
    "This tool samples the 1° monthly grid cell containing the point. Missing values "
    "normally mean that no valid cloud-free retrieval was available for that month."
)

if extract:
    if not platforms:
        st.error("Select at least one satellite.")
        st.stop()

    try:
        with st.spinner("Connecting to Earth Engine and extracting MODIS data..."):
            initialize_earth_engine(project.strip() or None)
            data = extract_monthly(
                latitude, longitude, start_date, end_date, platforms
            )
    except Exception as exc:
        st.error("The extraction could not be completed.")
        st.code(str(exc))
        st.markdown(
            "Authenticate once in a terminal with `earthengine authenticate`, then "
            "restart the app. Also check that the Earth Engine project is enabled."
        )
    else:
        if data.empty:
            st.warning("No MODIS images were found for that date range.")
        else:
            valid = data.dropna(subset=["aod_550_nm", "angstrom_exponent"])
            st.subheader("Time series")
            aod_tab, ae_tab = st.tabs(["AOD 550 nm", "Angstrom exponent"])
            with aod_tab:
                st.line_chart(
                    valid,
                    x="date",
                    y="aod_550_nm",
                    color="platform",
                )
            with ae_tab:
                st.line_chart(
                    valid,
                    x="date",
                    y="angstrom_exponent",
                    color="platform",
                )

            st.subheader("Extracted values")
            display = data.copy()
            display["date"] = display["date"].dt.date
            st.dataframe(display, use_container_width=True, hide_index=True)

            csv = data.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV",
                csv,
                file_name="modis_aerosol_sofia.csv",
                mime="text/csv",
            )

            missing = int(
                data[["aod_550_nm", "angstrom_exponent"]].isna().any(axis=1).sum()
            )
            st.caption(
                f"{len(data)} satellite-month rows returned; "
                f"{len(valid)} contain both variables; {missing} contain a missing value."
            )

st.markdown(
    """
### Variables

- **AOD 550 nm:** `Deep_Blue_Aerosol_Optical_Depth_550_Land_Mean_Mean`
- **Angstrom exponent:** `Deep_Blue_Angstrom_Exponent_Land_Mean_Mean`

The Angstrom exponent describes aerosol spectral dependence. Larger values generally
indicate a greater contribution from fine particles, while smaller values generally
indicate coarser particles.
"""
)
