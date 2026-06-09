import os
import requests
import re
from datetime import datetime, timedelta

# =========================
# USER-ADJUSTABLE PARAMETERS
# =========================
START_DATE = "2025-11-07"   # YYYY-MM-DD
END_DATE   = "2026-02-01"   # YYYY-MM-DD

HOUR  = "12"               # "00" or "12"
STNM  = "15614"

EXPORT_DIR = os.environ.get("WYOMING_OUTPUT", "output")

STOP_LINE = "Precipitable water [mm] for entire sounding"

# =========================
# HELPERS
# =========================
def build_url(date_obj):
    year  = date_obj.strftime("%Y")
    month = date_obj.strftime("%m")
    day   = date_obj.strftime("%d")
    ddhh  = f"{day}{HOUR}"

    return (
        "https://weather.uwyo.edu/cgi-bin/sounding?"
        f"region=europe&TYPE=TEXT%3ALIST"
        f"&YEAR={year}&MONTH={month}"
        f"&FROM={ddhh}&TO={ddhh}"
        f"&STNM={STNM}"
    ), day, month, year

def clean_and_cut(text):
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    lines = text.splitlines()
    kept = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        kept.append(line)
        if STOP_LINE in line:
            break

    return "\n".join(kept) + "\n" if kept else None

# =========================
# MAIN LOOP
# =========================
os.makedirs(EXPORT_DIR, exist_ok=True)

start = datetime.strptime(START_DATE, "%Y-%m-%d")
end   = datetime.strptime(END_DATE, "%Y-%m-%d")

current = start
while current <= end:
    url, day, month, year = build_url(current)

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        cleaned = clean_and_cut(r.text)

        if not cleaned or STOP_LINE not in cleaned:
            print(f"[SKIP] {current.date()} – no valid sounding")
        else:
            filename = f"wyoming-{day}-{month}-{year}.txt"
            out_path = os.path.join(EXPORT_DIR, filename)

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(cleaned)

            print(f"[OK]   {current.date()} → {filename}")

    except Exception as e:
        print(f"[ERR]  {current.date()} → {e}")

    current += timedelta(days=1)
