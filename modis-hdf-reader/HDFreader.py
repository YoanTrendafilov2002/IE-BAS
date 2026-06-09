import os
import sys
import numpy as np

try:
    import h5py
except ImportError:
    h5py = None

try:
    from pyhdf.SD import SD, SDC
except ImportError:
    SD = None
    SDC = None

try:
    from netCDF4 import Dataset
except ImportError:
    Dataset = None


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_TXT = os.path.join(SCRIPT_DIR, "input.txt")
OUTPUT_DIR = os.environ.get("HDF_OUTPUT", os.path.join(SCRIPT_DIR, "output"))


def write_stats_header(out, file_path, fmt_name):
    out.write(f"FILE: {file_path}\n")
    out.write("=" * 60 + "\n\n")
    out.write(f"FORMAT: {fmt_name}\n\n")


def safe_stats(arr):
    try:
        a = np.array(arr)
        if np.ma.isMaskedArray(a):
            if a.count() == 0:
                return None, None, None
            vals = a.compressed().astype(float)
        else:
            vals = np.array(a, dtype=float).ravel()

        vals = vals[np.isfinite(vals)]
        if vals.size == 0:
            return None, None, None

        return float(np.min(vals)), float(np.max(vals)), float(np.mean(vals))
    except Exception:
        return None, None, None


def read_input_path(input_txt):
    if not os.path.exists(input_txt):
        raise FileNotFoundError(f"Input file not found: {input_txt}")

    with open(input_txt, "r", encoding="utf-8") as f:
        hdf_path = f.readline().strip()

    if not hdf_path:
        raise ValueError("input.txt is empty")

    if not os.path.exists(hdf_path):
        raise FileNotFoundError(f"Target file not found: {hdf_path}")

    return hdf_path


def infer_unit(var_name):
    name = var_name.lower()

    if "latitude" in name or "longitude" in name:
        return "degrees"

    if "zenith" in name or "azimuth" in name or "angle" in name:
        return "degrees"

    if "scan_start_time" in name or name.endswith("time"):
        return "seconds"

    if "mass_concentration" in name:
        return "ug/m3"

    if "effective_radius" in name:
        return "um"

    if "topographic_altitude" in name:
        return "km"

    if "wind_speed" in name:
        return "m/s"

    if "distance" in name:
        return "km"

    if "optical_depth" in name or "aod" in name:
        return "unitless"

    if "angstrom" in name:
        return "unitless"

    if "reflectance" in name:
        return "unitless"

    if "fraction" in name:
        return "unitless"

    if "ratio" in name:
        return "unitless"

    if "asymmetry" in name:
        return "unitless"

    if "quality" in name or "flag" in name or "mask" in name or "type" in name or "index" in name:
        return "unitless"

    if "number_pixels_used" in name:
        return "count"

    return "unknown"


def write_raw_table(raw_out, var_name, arr):
    unit = infer_unit(var_name)

    try:
        a = np.array(arr)

        if np.ma.isMaskedArray(a):
            a = a.filled(np.nan)

        # 0D
        if a.ndim == 0:
            raw_out.write("NAME\tMEAS_NO\tUNIT\tVALUE\n")
            raw_out.write(f"{var_name}\t1\t{unit}\t{a.item()}\n\n")
            return

        # 1D
        if a.ndim == 1:
            raw_out.write("NAME\tMEAS_NO\tUNIT\tINDEX\tVALUE\n")
            meas_no = 1
            for i, v in enumerate(a):
                raw_out.write(f"{var_name}\t{meas_no}\t{unit}\t{i}\t{v}\n")
                meas_no += 1
            raw_out.write("\n")
            return

        # 2D
        if a.ndim == 2:
            raw_out.write("NAME\tMEAS_NO\tUNIT\tROW\tCOL\tVALUE\n")
            meas_no = 1
            rows, cols = a.shape
            for i in range(rows):
                for j in range(cols):
                    raw_out.write(f"{var_name}\t{meas_no}\t{unit}\t{i}\t{j}\t{a[i, j]}\n")
                    meas_no += 1
            raw_out.write("\n")
            return

        # 3D
        if a.ndim == 3:
            raw_out.write("NAME\tMEAS_NO\tUNIT\tXY\tROW\tCOL\tVALUE\n")
            meas_no = 1
            d0, d1, d2 = a.shape
            for x in range(d0):
                for y in range(d1):
                    xy = f"{x}/{y}"
                    for j in range(d2):
                        raw_out.write(f"{var_name}\t{meas_no}\t{unit}\t{xy}\t{y}\t{j}\t{a[x, y, j]}\n")
                        meas_no += 1
            raw_out.write("\n")
            return

        # 4D or more fallback
        raw_out.write("NAME\tMEAS_NO\tUNIT\tFLAT_INDEX\tVALUE\n")
        meas_no = 1
        flat = a.ravel()
        for i, v in enumerate(flat):
            raw_out.write(f"{var_name}\t{meas_no}\t{unit}\t{i}\t{v}\n")
            meas_no += 1
        raw_out.write("\n")

    except Exception as e:
        raw_out.write("NAME\tMEAS_NO\tUNIT\tERROR\n")
        raw_out.write(f"{var_name}\t1\t{unit}\tFAILED TO WRITE DATA: {e}\n\n")


def try_h5py(file_path, stats_path, raw_path):
    if h5py is None:
        return False

    try:
        with h5py.File(file_path, "r") as f, \
             open(stats_path, "w", encoding="utf-8") as out, \
             open(raw_path, "w", encoding="utf-8") as raw_out:

            write_stats_header(out, file_path, "HDF5 / NETCDF (via h5py)")

            def visit(name, obj):
                if isinstance(obj, h5py.Dataset):
                    try:
                        data = obj[()]
                    except Exception as e:
                        out.write(f"DATASET: {name}\n")
                        out.write("  shape: unknown\n")
                        out.write(f"  stats: FAILED TO READ ({e})\n\n")
                        return

                    out.write(f"DATASET: {name}\n")
                    out.write(f"  shape: {np.shape(data)}\n")
                    out.write(f"  unit: {infer_unit(name)}\n")

                    mn, mx, mean = safe_stats(data)
                    if mn is None:
                        out.write("  min: --\n")
                        out.write("  max: --\n")
                        out.write("  stats: N/A\n\n")
                    else:
                        out.write(f"  min: {mn}\n")
                        out.write(f"  max: {mx}\n")
                        out.write(f"  mean: {mean}\n\n")

                    write_raw_table(raw_out, name, data)

            f.visititems(visit)

        return True
    except Exception:
        return False


def try_hdf4(file_path, stats_path, raw_path):
    if SD is None or SDC is None:
        return False

    try:
        hdf = SD(file_path, SDC.READ)

        with open(stats_path, "w", encoding="utf-8") as out, \
             open(raw_path, "w", encoding="utf-8") as raw_out:

            write_stats_header(out, file_path, "HDF4 (pyhdf)")

            datasets = hdf.datasets()

            for name in datasets:
                out.write(f"DATASET: {name}\n")

                try:
                    ds = hdf.select(name)
                    data = ds[:]

                    out.write(f"  shape: {np.shape(data)}\n")
                    out.write(f"  unit: {infer_unit(name)}\n")

                    mn, mx, mean = safe_stats(data)
                    if mn is None:
                        out.write("  min: --\n")
                        out.write("  max: --\n")
                        out.write("  stats: N/A\n\n")
                    else:
                        out.write(f"  min: {mn}\n")
                        out.write(f"  max: {mx}\n")
                        out.write(f"  mean: {mean}\n\n")

                    write_raw_table(raw_out, name, data)

                except Exception as e:
                    out.write("  shape: unknown\n")
                    out.write(f"  stats: FAILED TO READ ({e})\n\n")

        try:
            hdf.end()
        except Exception:
            pass

        return True
    except Exception:
        return False


def try_netcdf4(file_path, stats_path, raw_path):
    if Dataset is None:
        return False

    try:
        nc = Dataset(file_path, "r")

        with open(stats_path, "w", encoding="utf-8") as out, \
             open(raw_path, "w", encoding="utf-8") as raw_out:

            write_stats_header(out, file_path, "NETCDF (netCDF4)")

            for var_name in nc.variables:
                out.write(f"VARIABLE: {var_name}\n")

                try:
                    data = nc.variables[var_name][:]

                    out.write(f"  shape: {np.shape(data)}\n")
                    out.write(f"  unit: {infer_unit(var_name)}\n")

                    mn, mx, mean = safe_stats(data)
                    if mn is None:
                        out.write("  min: --\n")
                        out.write("  max: --\n")
                        out.write("  stats: N/A\n\n")
                    else:
                        out.write(f"  min: {mn}\n")
                        out.write(f"  max: {mx}\n")
                        out.write(f"  mean: {mean}\n\n")

                    write_raw_table(raw_out, var_name, data)

                except Exception as e:
                    out.write("  shape: unknown\n")
                    out.write(f"  stats: FAILED TO READ ({e})\n\n")

        try:
            nc.close()
        except Exception:
            pass

        return True
    except Exception:
        return False


def main():
    try:
        hdf_path = read_input_path(INPUT_TXT)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(hdf_path))[0]
        stats_path = os.path.join(OUTPUT_DIR, base_name + ".txt")
        raw_path = os.path.join(OUTPUT_DIR, base_name + "_raw.txt")

        if try_h5py(hdf_path, stats_path, raw_path):
            print("Read as HDF5 / NETCDF using h5py")
            print(f"Stats file: {stats_path}")
            print(f"Raw file:   {raw_path}")
            return

        if try_hdf4(hdf_path, stats_path, raw_path):
            print("Read as HDF4 using pyhdf")
            print(f"Stats file: {stats_path}")
            print(f"Raw file:   {raw_path}")
            return

        if try_netcdf4(hdf_path, stats_path, raw_path):
            print("Read as NETCDF using netCDF4")
            print(f"Stats file: {stats_path}")
            print(f"Raw file:   {raw_path}")
            return

        with open(stats_path, "w", encoding="utf-8") as out:
            out.write(f"FILE: {hdf_path}\n")
            out.write("=" * 60 + "\n\n")
            out.write("FAILED TO READ FILE FORMAT\n")

        with open(raw_path, "w", encoding="utf-8") as raw_out:
            raw_out.write("NAME\tMEAS_NO\tUNIT\tERROR\n")
            raw_out.write("FILE\t1\tunknown\tFAILED TO READ FILE FORMAT\n")

        print("Failed to read file format.")
        print(f"Stats file: {stats_path}")
        print(f"Raw file:   {raw_path}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
