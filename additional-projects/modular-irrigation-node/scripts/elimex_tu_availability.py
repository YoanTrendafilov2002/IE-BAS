from __future__ import annotations

import html
import json
import re
import sys
import urllib.request


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


TU_STORE = "София - ТУ бул. Св. Кл.Охридски 8"


PARTS = [
    {
        "function": "Light sensor",
        "qty": 1,
        "kit": "K2156",
        "slug": "75631-kit-k2156-senzor-za-osvetenost-gy-302-bh1750",
    },
    {
        "function": "Soil moisture sensor",
        "qty": 1,
        "kit": "K2112",
        "slug": "74854-kit-k2112-senzor-za-vlazhnost-na-pochvata",
    },
    {
        "function": "LiPo charger",
        "qty": 1,
        "kit": "K548",
        "slug": "82658-kit-k548-zarqdno-za-li-ion-li-po-baterii-usb-c",
    },
    {
        "function": "Boost converter",
        "qty": 1,
        "kit": "K585",
        "slug": "86296-kit-k585-konvertor-povishavasht-dc-dc-uvh-2v-24v-uizh-5v-28v",
    },
    {
        "function": "Pump",
        "qty": 1,
        "kit": "catalog part",
        "slug": "88738-vodna-pompa-dc-3-5v-200ma",
    },
    {
        "function": "Tank level switch",
        "qty": 1,
        "kit": "XSL-4510-P",
        "slug": "91654-datchik-za-nivo-xsl-4510-p",
    },
    {
        "function": "MOSFET",
        "qty": 1,
        "kit": "IRLZ44N",
        "slug": "36316-irlz44n-to-220",
    },
    {
        "function": "Flyback diode",
        "qty": 1,
        "kit": "1N5819",
        "slug": "28885-1n5819-do-41",
    },
    {
        "function": "Pump bulk capacitor",
        "qty": 1,
        "kit": "C470uF/16V",
        "slug": "46773-c470uf16v-vn-8x12-low",
    },
    {
        "function": "2-pin JST cable for pump/level",
        "qty": 2,
        "kit": "JST XH-2.54-F 2pin cable",
        "slug": "91533-saedinitel-jst-xh-2.54-f-2pin-s-kabel-0.2m",
    },
    {
        "function": "Battery/JST connector kit",
        "qty": 1,
        "kit": "JST 2-PIN kit",
        "slug": "82695-saedinitel-jst-2-pin-komplekt",
    },
]


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", "replace")


def parse_product(slug: str) -> dict:
    url = f"https://elimex.bg/product/{slug}"
    page = fetch(url)
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page)
    if not match:
        raise RuntimeError(f"No __NEXT_DATA__ found for {slug}")
    data = json.loads(html.unescape(match.group(1)))
    return data["props"]["pageProps"]["product"]


def availability_for_store(product: dict, store_name: str) -> int:
    total = 0
    for item in product.get("items") or []:
        for location in item.get("availabilityByLocations") or []:
            if location.get("name") == store_name:
                total += int(location.get("availability") or 0)
    return total


def total_availability(product: dict) -> int:
    total = 0
    for item in product.get("items") or []:
        total += int(item.get("availability") or 0)
    return total


def item_codes(product: dict) -> str:
    codes = []
    for item in product.get("items") or []:
        code = item.get("code")
        sin = item.get("sin")
        if code and sin and str(code) != str(sin):
            codes.append(f"{code} / sin {sin}")
        elif code:
            codes.append(str(code))
        elif sin:
            codes.append(f"sin {sin}")
    return ", ".join(codes)


def main() -> int:
    rows = []
    for part in PARTS:
        product = parse_product(part["slug"])
        rows.append(
            {
                **part,
                "name": product.get("name") or "",
                "url": f"https://elimex.bg/product/{part['slug']}",
                "code": item_codes(product),
                "price_bgn": product.get("minPrice"),
                "tu_available": availability_for_store(product, TU_STORE),
                "total_available": total_availability(product),
            }
        )

    print("| Function | Qty | Kit / part number | Elimex code | TU store stock | Total stock | Price BGN | Product |")
    print("|---|---:|---|---|---:|---:|---:|---|")
    for row in rows:
        print(
            f"| {row['function']} | {row['qty']} | {row['kit']} | {row['code']} | "
            f"{row['tu_available']} | {row['total_available']} | {row['price_bgn']} | "
            f"[{row['name']}]({row['url']}) |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
