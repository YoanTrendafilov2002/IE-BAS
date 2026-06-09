from datetime import datetime, timedelta, timezone
import math
import requests
from skyfield.api import load, wgs84, EarthSatellite

NORAD_ID = 59908
THRESHOLD_KM = 75.0
SOFIA_LAT = 42.6977
SOFIA_LON = 23.3219
SEARCH_DAYS = 7
STEP_SECONDS = 5

def fetch_tle(norad_id: int) -> tuple[str, str]:
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=TLE"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    lines = [line.strip() for line in r.text.splitlines() if line.strip()]
    if lines[0].startswith("1 ") and lines[1].startswith("2 "):
        return lines[0], lines[1]
    if len(lines) >= 3 and lines[1].startswith("1 ") and lines[2].startswith("2 "):
        return lines[1], lines[2]
    raise RuntimeError("Unexpected TLE format")

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"

def main():
    line1, line2 = fetch_tle(NORAD_ID)
    ts = load.timescale()
    sat = EarthSatellite(line1, line2, "EarthCARE", ts)

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=SEARCH_DAYS)
    step = timedelta(seconds=STEP_SECONDS)

    inside = False
    start_time = None
    best_dist = None
    best_time = None
    first_window = None

    t = now
    while t <= end:
        ti = ts.from_datetime(t)
        subpoint = wgs84.subpoint_of(sat.at(ti))
        d_km = haversine_km(
            SOFIA_LAT, SOFIA_LON,
            subpoint.latitude.degrees, subpoint.longitude.degrees
        )

        if d_km < THRESHOLD_KM:
            if not inside:
                inside = True
                start_time = t
                best_dist = d_km
                best_time = t
            elif d_km < best_dist:
                best_dist = d_km
                best_time = t
        else:
            if inside:
                finish_time = t
                duration_s = (finish_time - start_time).total_seconds()
                first_window = (start_time, finish_time, duration_s, best_time, best_dist)
                break
            inside = False
            start_time = None
            best_dist = None
            best_time = None

        t += step

    if inside and first_window is None:
        finish_time = end
        duration_s = (finish_time - start_time).total_seconds()
        first_window = (start_time, finish_time, duration_s, best_time, best_dist)

    if first_window is None:
        print(f"No interval found in the next {SEARCH_DAYS} days where ground track is within {THRESHOLD_KM:.1f} km of Sofia.")
        return

    start_time, finish_time, duration_s, best_time, best_dist = first_window
    print("Next ground-track interval found:")
    print("  Start UTC:    ", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    print("  End UTC:      ", finish_time.strftime("%Y-%m-%d %H:%M:%S"))
    print("  Duration:     ", format_duration(duration_s))
    print("  Closest UTC:  ", best_time.strftime("%Y-%m-%d %H:%M:%S"))
    print(f"  Min distance:  {best_dist:.3f} km")

if __name__ == "__main__":
    main()