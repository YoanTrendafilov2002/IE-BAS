# BarcelonaData_old_working.py
# Fetch MONARCH dust data from AEMET THREDDS (OPeNDAP ASCII) and write daily JSON outputs.
# - Period: configured at top (daily model run at 00 UTC)
# - Point: configured at top (lat/lon)
# - Subset: ±0.5° (11x11 grid at 0.1° resolution), then bilinear interpolation to the point
# - Auth: HTTP Basic (from user_config.json)
# - SSL: default verify=False to avoid CERTIFICATE_VERIFY_FAILED on Windows

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Tuple

import requests
import urllib3
from requests.auth import HTTPBasicAuth


# =========================
# USER SETTINGS (EDIT HERE)
# =========================

POINT_LAT = 42.653733
POINT_LON = 23.387372

START_DATE = "2025-06-01"   # inclusive
END_DATE   = "2025-06-30"   # inclusive
RUN_HOUR_UTC = 0            # daily run at 00 UTC

SUBSET_HALF_DEG = 0.5       # ±0.5° window
VERIFY_SSL = False          # set True if you have proper CA chain

OUTPUT_DIR = "output_json"  # relative to this script
USER_CONFIG_PATH = "user_config.json"

# Variables to fetch:
VARS_2D = [
    "dust_ext_sfc",
    "dust_load",
    "dust_depd",
    "dust_depw",
    "od550_dust",
]
VAR_4D = "sconc_dust"  # [time][lev][lat][lon]

# Dataset filename pattern (the one that worked for you in 2025-12):
DATASET_NAME = "{yyyymmdd}00_3H_SDSWAS_MONARCH-fct.nc"


# =========================
# GRID (from your ASCII dump)
# =========================
GRID_LAT0 = -10.95
GRID_LON0 = -62.95
GRID_DLAT = 0.10
GRID_DLON = 0.10
GRID_NLAT = 825
GRID_NLON = 1650


# =========================
# Helpers
# =========================

def parse_yyyy_mm_dd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def daterange(d0: date, d1: date):
    cur = d0
    while cur <= d1:
        yield cur
        cur += timedelta(days=1)

def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))

def ensure_user_config(path: Path) -> Dict[str, str]:
    """
    Reads user_config.json with:
      {
        "BDSR_USER": "your_user",
        "BDSR_PASS": "your_pass"
      }
    If missing, creates a template and exits.
    """
    if not path.exists():
        template = {
            "BDSR_USER": "PUT_USER_HERE",
            "BDSR_PASS": "PUT_PASS_HERE"
        }
        path.write_text(json.dumps(template, indent=2), encoding="utf-8")
        raise SystemExit(f"Created {path}. Fill credentials and re-run.")

    cfg = json.loads(path.read_text(encoding="utf-8"))
    user = (cfg.get("BDSR_USER") or "").strip()
    pw   = (cfg.get("BDSR_PASS") or "").strip()
    if not user or not pw or "PUT_" in user or "PUT_" in pw:
        raise SystemExit(f"{path} missing real credentials. Fill BDSR_USER/BDSR_PASS.")
    return {"user": user, "pass": pw}

def make_session(user: str, pw: str) -> requests.Session:
    s = requests.Session()
    s.auth = HTTPBasicAuth(user, pw)
    s.headers.update({"User-Agent": "BarcelonaDustClient/1.0"})
    if not VERIFY_SSL:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return s

def http_get_text(s: requests.Session, url: str) -> str:
    r = s.get(url, timeout=120, allow_redirects=True, verify=VERIFY_SSL)
    r.raise_for_status()
    return r.text

def grid_index(lat: float, lon: float) -> Tuple[int, int]:
    """
    Returns nearest grid index (ilat, ilon) for the regular 0.1° grid.
    """
    ilat = int(round((lat - GRID_LAT0) / GRID_DLAT))
    ilon = int(round((lon - GRID_LON0) / GRID_DLON))
    ilat = clamp(ilat, 0, GRID_NLAT - 1)
    ilon = clamp(ilon, 0, GRID_NLON - 1)
    return ilat, ilon

def subset_indices_center(ilat: int, ilon: int, half_deg: float) -> Tuple[int, int, int, int]:
    """
    Compute subset window indices around center index for ±half_deg.
    For 0.1° step, half_deg=0.5 => radius=5 => 11 points.
    """
    radius = int(round(half_deg / GRID_DLAT))
    i0 = clamp(ilat - radius, 0, GRID_NLAT - 1)
    i1 = clamp(ilat + radius, 0, GRID_NLAT - 1)
    j0 = clamp(ilon - radius, 0, GRID_NLON - 1)
    j1 = clamp(ilon + radius, 0, GRID_NLON - 1)
    return i0, i1, j0, j1

def build_ascii_url(run_day: date, i0: int, i1: int, j0: int, j1: int) -> str:
    """
    Build a valid ".ascii" OPeNDAP URL with properly percent-encoded brackets.
    """
    y = run_day.strftime("%Y")
    m = run_day.strftime("%m")
    yyyymmdd = run_day.strftime("%Y%m%d")
    ds = DATASET_NAME.format(yyyymmdd=yyyymmdd)

    base = f"https://dust.aemet.es/thredds/dodsC/dataRoot/MONARCH/{y}/{m}/{ds}.ascii"

    parts: List[str] = []
    for v in VARS_2D:
        parts.append(f"{v}[0:1:24][{i0}:1:{i1}][{j0}:1:{j1}]")
    parts.append(f"{VAR_4D}[0:1:24][0:1:13][{i0}:1:{i1}][{j0}:1:{j1}]")

    parts.append("time[0:1:24]")
    parts.append("lev[0:1:13]")
    parts.append(f"lat[{i0}:1:{i1}]")
    parts.append(f"lon[{j0}:1:{j1}]")

    from urllib.parse import quote
    encoded = [quote(p, safe=",:-_~abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for p in parts]
    return base + "?" + ",".join(encoded)


# =========================
# DAP ASCII parsing
# =========================

_float_re = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")

def _parse_values_from_line(line: str) -> List[float]:
    return [float(x) for x in _float_re.findall(line)]

@dataclass
class ParsedDAP:
    vars2d: Dict[str, List[List[List[float]]]]  # v => [T][I][J]
    sconc: List[List[List[List[float]]]]        # [T][L][I][J]
    time: List[float]
    lev: List[float]
    lat: List[float]
    lon: List[float]

def parse_dap_ascii(text: str, ni: int, nj: int) -> ParsedDAP:
    lines = text.splitlines()

    def find_block_start(prefix: str) -> int:
        for idx, line in enumerate(lines):
            if line.strip().startswith(prefix):
                return idx
        raise ValueError(f"Could not find block start: {prefix}")

    def parse_vector(name: str, expected_len: int) -> List[float]:
        start = find_block_start(f"{name}[")
        vals: List[float] = []
        for i in range(start + 1, len(lines)):
            ln = lines[i].strip()
            if not ln:
                break
            vals.extend(_parse_values_from_line(ln))
        if len(vals) < expected_len:
            raise ValueError(f"{name} parsed length {len(vals)} < expected {expected_len}")
        return vals[:expected_len]

    def parse_grid3(name: str, T: int, I: int, J: int) -> List[List[List[float]]]:
        start = find_block_start(f"{name}.{name}[")
        out = [[[0.0 for _ in range(J)] for _ in range(I)] for _ in range(T)]
        for i in range(start + 1, len(lines)):
            ln = lines[i].strip()
            if not ln:
                break
            if not ln.startswith("["):
                continue
            idxs = [int(x) for x in re.findall(r"\[(\d+)\]", ln)]
            if len(idxs) < 2:
                continue
            t = idxs[0]
            ii = idxs[1]
            if "," in ln:
                data_str = ln.split(",", 1)[1]
                data_vals = [float(x) for x in _float_re.findall(data_str)]
            else:
                data_vals = [float(x) for x in _float_re.findall(ln)]
            if len(data_vals) < J:
                continue
            for jj in range(J):
                out[t][ii][jj] = data_vals[jj]
        return out

    def parse_grid4(name: str, T: int, L: int, I: int, J: int) -> List[List[List[List[float]]]]:
        start = find_block_start(f"{name}.{name}[")
        out = [[[[0.0 for _ in range(J)] for _ in range(I)] for _ in range(L)] for _ in range(T)]
        for i in range(start + 1, len(lines)):
            ln = lines[i].strip()
            if not ln:
                break
            if not ln.startswith("["):
                continue
            idxs = [int(x) for x in re.findall(r"\[(\d+)\]", ln)]
            if len(idxs) < 3:
                continue
            t, lev, ii = idxs[0], idxs[1], idxs[2]
            if "," in ln:
                data_str = ln.split(",", 1)[1]
                data_vals = [float(x) for x in _float_re.findall(data_str)]
            else:
                data_vals = [float(x) for x in _float_re.findall(ln)]
            if len(data_vals) < J:
                continue
            for jj in range(J):
                out[t][lev][ii][jj] = data_vals[jj]
        return out

    time = parse_vector("time", 25)
    lev = parse_vector("lev", 14)
    lat = parse_vector("lat", ni)
    lon = parse_vector("lon", nj)

    vars2d: Dict[str, List[List[List[float]]]] = {}
    for v in VARS_2D:
        vars2d[v] = parse_grid3(v, 25, ni, nj)

    sconc = parse_grid4(VAR_4D, 25, 14, ni, nj)

    return ParsedDAP(vars2d=vars2d, sconc=sconc, time=time, lev=lev, lat=lat, lon=lon)


# =========================
# Bilinear interpolation
# =========================

def bilinear_at(grid2d: List[List[float]], lat_vec: List[float], lon_vec: List[float], lat: float, lon: float) -> float:
    if lat <= lat_vec[0]:
        i0 = 0
    elif lat >= lat_vec[-1]:
        i0 = len(lat_vec) - 2
    else:
        i0 = int(math.floor((lat - lat_vec[0]) / (lat_vec[1] - lat_vec[0])))
        i0 = clamp(i0, 0, len(lat_vec) - 2)

    if lon <= lon_vec[0]:
        j0 = 0
    elif lon >= lon_vec[-1]:
        j0 = len(lon_vec) - 2
    else:
        j0 = int(math.floor((lon - lon_vec[0]) / (lon_vec[1] - lon_vec[0])))
        j0 = clamp(j0, 0, len(lon_vec) - 2)

    i1 = i0 + 1
    j1 = j0 + 1

    y0, y1 = lat_vec[i0], lat_vec[i1]
    x0, x1 = lon_vec[j0], lon_vec[j1]

    ty = 0.0 if y1 == y0 else (lat - y0) / (y1 - y0)
    tx = 0.0 if x1 == x0 else (lon - x0) / (x1 - x0)

    v00 = grid2d[i0][j0]
    v10 = grid2d[i1][j0]
    v01 = grid2d[i0][j1]
    v11 = grid2d[i1][j1]

    v0 = v00 * (1 - ty) + v10 * ty
    v1 = v01 * (1 - ty) + v11 * ty
    return v0 * (1 - tx) + v1 * tx


# =========================
# Main
# =========================

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    cfg_path = script_dir / USER_CONFIG_PATH
    out_dir = script_dir / OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = ensure_user_config(cfg_path)
    s = make_session(cfg["user"], cfg["pass"])

    d0 = parse_yyyy_mm_dd(START_DATE)
    d1 = parse_yyyy_mm_dd(END_DATE)

    ilat_c, ilon_c = grid_index(POINT_LAT, POINT_LON)
    i0, i1, j0, j1 = subset_indices_center(ilat_c, ilon_c, SUBSET_HALF_DEG)
    ni = i1 - i0 + 1
    nj = j1 - j0 + 1

    print(f"Point: {POINT_LAT}, {POINT_LON}")
    print(f"Center idx: lat={ilat_c}, lon={ilon_c}")
    print(f"Subset idx: lat[{i0}:{i1}] ({ni}), lon[{j0}:{j1}] ({nj})")
    print(f"Period: {d0} -> {d1} (daily run {RUN_HOUR_UTC:02d} UTC)")
    print(f"VERIFY_SSL={VERIFY_SSL}")

    for run_day in daterange(d0, d1):
        run_dt = datetime(run_day.year, run_day.month, run_day.day, RUN_HOUR_UTC, 0, 0)

        url = build_ascii_url(run_day, i0, i1, j0, j1)
        print(f"\n=== {run_day} ===")

        try:
            text = http_get_text(s, url)
        except requests.HTTPError as e:
            print(f"ERROR {run_day}: HTTPError: {e}")
            continue
        except Exception as e:
            print(f"ERROR {run_day}: {type(e).__name__}: {e}")
            continue

        try:
            parsed = parse_dap_ascii(text, ni=ni, nj=nj)
        except Exception as e:
            print(f"ERROR {run_day}: parse failed: {type(e).__name__}: {e}")
            continue

        records: List[Dict] = []
        for t_idx, t_hours in enumerate(parsed.time):
            ts = run_dt + timedelta(hours=float(t_hours))

            rec = {
                "timestamp_utc": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "forecast_hour": float(t_hours),
                "vars": {}
            }

            for v in VARS_2D:
                grid = parsed.vars2d[v][t_idx]
                rec["vars"][v] = bilinear_at(grid, parsed.lat, parsed.lon, POINT_LAT, POINT_LON)

            lev_vals: Dict[str, float] = {}
            for lev_i, lev_m in enumerate(parsed.lev):
                grid = parsed.sconc[t_idx][lev_i]
                lev_vals[str(float(lev_m))] = bilinear_at(grid, parsed.lat, parsed.lon, POINT_LAT, POINT_LON)

            rec["vars"][VAR_4D] = {
                "units": None,
                "by_level_m": lev_vals
            }

            records.append(rec)

        payload = {
            "meta": {
                "run_date_utc": run_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "point": {"lat": POINT_LAT, "lon": POINT_LON},
                "subset_half_deg": SUBSET_HALF_DEG,
                "subset_index": {"lat_i0": i0, "lat_i1": i1, "lon_j0": j0, "lon_j1": j1},
                "subset_lat": parsed.lat,
                "subset_lon": parsed.lon,
                "time_hours": parsed.time,
                "lev_m": parsed.lev,
                "source": "AEMET THREDDS OPeNDAP ASCII",
            },
            "data": records
        }

        out_file = out_dir / f"{run_day.strftime('%Y_%m_%d')}_00UTC.json"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote: {out_file}")

    print("\nDone.")

if __name__ == "__main__":
    main()
