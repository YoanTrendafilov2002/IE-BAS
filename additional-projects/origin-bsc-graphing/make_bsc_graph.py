import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "originpro_pkg"))

import matplotlib.pyplot as plt
import numpy as np
import originpro as op


PROJECT = Path(r"C:\Users\user\Downloads\BSC-all.opju")
OUT_DIR = Path(
    r"C:\Users\user\Documents\Codex\2026-06-05"
    r"\can-you-make-a-single-graph\outputs"
)
SHEET_NAME = "BSC-03.06.2026"


def numeric(values, length):
    converted = []
    for value in list(values)[:length]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = math.nan
        converted.append(number)
    converted.extend([math.nan] * (length - len(converted)))
    return np.asarray(converted, dtype=float)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        op.set_show(False)
        if not op.open(str(PROJECT), readonly=True):
            raise RuntimeError(f"Origin could not open {PROJECT}")

        sheet = None
        for book in op.pages("w"):
            for candidate in book:
                if candidate.name == SHEET_NAME:
                    sheet = candidate
                    break
            if sheet is not None:
                break
        if sheet is None:
            raise RuntimeError(f"Worksheet {SHEET_NAME!r} was not found")

        labels = sheet.get_labels("L")
        row_count = sheet.shape[0]
        altitude = numeric(sheet.to_list(1), row_count)
        y_columns = [2, 4, 6, 9, 11, 13, 16, 18, 20, 22, 24, 26]
        series = [
            (labels[col], numeric(sheet.to_list(col), row_count)) for col in y_columns
        ]
    finally:
        op.exit()

    csv_path = OUT_DIR / "BSC-03.06.2026-linear-data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Altitude", *(label for label, _ in series)])
        for row in range(len(altitude)):
            writer.writerow(
                [altitude[row], *(values[row] if row < len(values) else "" for _, values in series)]
            )

    time_colors = {
        "20:10": "#2563eb",
        "21:11": "#dc2626",
        "22:11": "#16a34a",
        "23:12": "#9333ea",
    }
    wavelength_colors = {
        "355": "#2563eb",
        "532": "#16a34a",
        "1064": "#dc2626",
    }
    line_styles = {
        "20:10": "-",
        "21:11": "--",
        "22:11": "-.",
        "23:12": ":",
    }

    output_files = []
    for target_wavelength in ("355", "532", "1064"):
        fig, ax = plt.subplots(figsize=(7.8, 9.2), constrained_layout=True)
        for label, values in series:
            time, wavelength = label.split("-", 1)
            if wavelength != target_wavelength:
                continue
            mask = np.isfinite(altitude) & np.isfinite(values)
            x = values[mask] * 1e6
            y = altitude[mask]
            order = np.argsort(y)
            ax.plot(
                x[order],
                y[order],
                color=time_colors[time],
                linestyle=line_styles[time],
                linewidth=1.7,
                alpha=0.95,
                label=time,
            )

        ax.set_title(
            f"BSC - 03.06.2026 - {target_wavelength} nm", fontsize=15, pad=12
        )
        ax.set_xlabel(r"BSC ($10^{-6}$ m$^{-1}$ sr$^{-1}$)", fontsize=12)
        ax.set_ylabel("Altitude (km)", fontsize=12)
        ax.set_ylim(0, 15.5)
        ax.grid(True, which="major", color="#d9d9d9", linewidth=0.7, alpha=0.75)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(
            title="Time",
            loc="upper right",
            frameon=True,
            fontsize=10,
            title_fontsize=10,
        )

        png_path = OUT_DIR / f"BSC-03.06.2026-{target_wavelength}nm.png"
        pdf_path = OUT_DIR / f"BSC-03.06.2026-{target_wavelength}nm.pdf"
        fig.savefig(png_path, dpi=220, facecolor="white")
        fig.savefig(pdf_path, facecolor="white")
        plt.close(fig)
        output_files.extend((png_path, pdf_path))

    for path in output_files:
        print(f"OUTPUT: {path}")

    hourly_output_files = []
    for target_time in ("20:10", "21:11", "22:11", "23:12"):
        fig, ax = plt.subplots(figsize=(7.8, 9.2), constrained_layout=True)
        for label, values in series:
            time, wavelength = label.split("-", 1)
            if time != target_time:
                continue
            mask = np.isfinite(altitude) & np.isfinite(values)
            x = values[mask] * 1e6
            y = altitude[mask]
            order = np.argsort(y)
            ax.plot(
                x[order],
                y[order],
                color=wavelength_colors[wavelength],
                linewidth=1.7,
                alpha=0.95,
                label=f"{wavelength} nm",
            )

        ax.set_title(f"BSC - 03.06.2026 - {target_time}", fontsize=15, pad=12)
        ax.set_xlabel(r"BSC ($10^{-6}$ m$^{-1}$ sr$^{-1}$)", fontsize=12)
        ax.set_ylabel("Altitude (km)", fontsize=12)
        ax.set_ylim(0, 15.5)
        ax.grid(True, which="major", color="#d9d9d9", linewidth=0.7, alpha=0.75)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(
            title="Wavelength",
            loc="upper right",
            frameon=True,
            fontsize=10,
            title_fontsize=10,
        )

        file_time = target_time.replace(":", "-")
        png_path = OUT_DIR / f"BSC-03.06.2026-{file_time}.png"
        pdf_path = OUT_DIR / f"BSC-03.06.2026-{file_time}.pdf"
        fig.savefig(png_path, dpi=220, facecolor="white")
        fig.savefig(pdf_path, facecolor="white")
        plt.close(fig)
        hourly_output_files.extend((png_path, pdf_path))

    for path in hourly_output_files:
        print(f"HOURLY OUTPUT: {path}")
    print(f"CSV: {csv_path}")
    for label, values in series:
        mask = np.isfinite(altitude) & np.isfinite(values)
        print(
            f"{label}: points={mask.sum()} "
            f"x=[{np.nanmin(altitude[mask]):.6g}, {np.nanmax(altitude[mask]):.6g}] "
            f"y=[{np.nanmin(values[mask]):.6g}, {np.nanmax(values[mask]):.6g}]"
        )


if __name__ == "__main__":
    main()
