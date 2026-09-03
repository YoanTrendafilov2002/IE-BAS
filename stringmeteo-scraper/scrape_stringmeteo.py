import os
import re
import json
import time
import calendar
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException


# Настройки
START_DATE = "2024-02-03"
END_DATE   = "2024-07-22"

EXPORT_DIR = os.environ.get("STRINGMETEO_OUTPUT", "output")
EDGE_DRIVER_PATH = os.environ.get("EDGE_DRIVER_PATH")

CITY_ID = 15614
BASE_URL = "https://www.stringmeteo.com/synop/bg_stday.php"

REQUEST_DELAY_S = 0.35


@dataclass
class Record:
    temp_c: float
    rh_percent: float
    pressure_hpa: float        # ВЗИМАМЕ ВТОРОТО ЧИСЛО
    wind_speed_ms: float
    wind_dir_deg: float
    unix_time: int
    timestamp: str

    def to_json(self) -> Dict[str, Any]:
        return {
            "temp_c": round(self.temp_c, 3),
            "rh_percent": round(self.rh_percent, 3),
            "pressure_hpa": round(self.pressure_hpa, 3),
            "wind_speed_ms": round(self.wind_speed_ms, 3),
            "wind_dir_deg": round(self.wind_dir_deg, 3),
            "unix_time": int(self.unix_time),
            "timestamp": self.timestamp,
        }


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def daterange_desc(newer: date, older: date):
    d = newer
    while d >= older:
        yield d
        d -= timedelta(days=1)


def build_url(d: date) -> str:
    return (
        f"{BASE_URL}?year={d.year}&month={d.month}&day={d.day}"
        f"&city={CITY_ID}&int=1&submit=%D0%9F%D0%9E%D0%9A%D0%90%D0%96%D0%98#sel"
    )


def setup_driver() -> webdriver.Edge:
    opts = Options()
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")

    if EDGE_DRIVER_PATH:
        driver = webdriver.Edge(service=Service(EDGE_DRIVER_PATH), options=opts)
    else:
        driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(25)
    return driver


def safe_get(driver, url: str):
    try:
        driver.get(url)
    except TimeoutException:
        try:
            driver.execute_script("window.stop();")
        except Exception:
            pass


# Consent handling (IAB TCF)
def accept_tcf_consent(driver) -> None:
    consent_btn_xpath = "//*[self::button or self::a][normalize-space(.)='Consent']"

    def try_here() -> bool:
        try:
            el = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, consent_btn_xpath))
            )
            el.click()
            time.sleep(0.4)
            return True
        except Exception:
            return False

    if try_here():
        return

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for fr in frames:
        try:
            driver.switch_to.frame(fr)
            if try_here():
                driver.switch_to.default_content()
                return
        except Exception:
            pass
        finally:
            driver.switch_to.default_content()

    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except Exception:
        pass


def to_float(x: str) -> float:
    return float(x.replace(",", "."))


def extract_records_from_body_text(d: date, body_text: str) -> List[Record]:
    """
    Парсваме директно от body.text.
    ВАЖНО: налягане = ВТОРОТО число след "/"
    """

    t = body_text.replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)

    pattern = re.compile(
        r"(?P<dd>\d{2})\.(?P<mm>\d{2})\.\s*\n"
        r"(?P<hhmm>\d{4})\s+"
        r"(?P<temp>-?\d+(?:[.,]\d+)?)\s*[º°]C"
        r".*?\|(?P<rh>\d{1,3})%\|"
        r".*?(?:\((?P<deg>\d{1,3})\s*º\)|--)"
        r"\s*(?P<speed>-?\d+(?:[.,]\d+)?)\s*м/с"
        r".*?\d{3,4}(?:[.,]\d+)?\s*/\s*(?P<press>\d{3,4}(?:[.,]\d+)?)",
        re.DOTALL
    )

    out: List[Record] = []

    for m in pattern.finditer(t):
        dd = int(m.group("dd"))
        mm = int(m.group("mm"))

        if dd != d.day or mm != d.month:
            continue

        hour = int(m.group("hhmm")[:2])

        temp = to_float(m.group("temp"))
        rh = float(m.group("rh"))
        speed = to_float(m.group("speed"))
        pressure = to_float(m.group("press"))   # ← ТУК Е ВТОРОТО ЧИСЛО

        deg_str = m.group("deg")
        wind_deg = float(deg_str) if deg_str else 0.0

        dt = datetime(d.year, d.month, d.day, hour, 0, 0, tzinfo=timezone.utc)

        out.append(
            Record(
                temp_c=temp,
                rh_percent=rh,
                pressure_hpa=pressure,
                wind_speed_ms=speed,
                wind_dir_deg=wind_deg,
                unix_time=calendar.timegm(dt.utctimetuple()),
                timestamp=dt.strftime("%Y-%m-%d.%H:%M:%S"),
            )
        )

    dedup: Dict[int, Record] = {}
    for r in out:
        h = int(r.timestamp[11:13])
        dedup[h] = r

    return [dedup[h] for h in sorted(dedup.keys())]


def main():
    print("[START]", os.path.abspath(__file__))
    os.makedirs(EXPORT_DIR, exist_ok=True)

    d1 = parse_date(START_DATE)
    d2 = parse_date(END_DATE)
    newer, older = (d2, d1) if d2 >= d1 else (d1, d2)

    driver = setup_driver()
    try:
        for d in daterange_desc(newer, older):
            url = build_url(d)
            print(f"[NAV] {d}")

            safe_get(driver, url)

            for _ in range(3):
                accept_tcf_consent(driver)
                time.sleep(0.4)

            time.sleep(1.0)

            body_text = driver.find_element(By.TAG_NAME, "body").text
            records = extract_records_from_body_text(d, body_text)

            if not records:
                print(f"[EMPTY] {d}")
                time.sleep(REQUEST_DELAY_S)
                continue

            out_path = os.path.join(EXPORT_DIR, f"{d.isoformat()}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump([r.to_json() for r in records], f, ensure_ascii=False, indent=2)

            print(f"[OK] {d} -> {len(records)} записа")
            time.sleep(REQUEST_DELAY_S)

    finally:
        driver.quit()
        print("[DONE]")


if __name__ == "__main__":
    main()
