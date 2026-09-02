from __future__ import annotations

import html
import json
import re
import sys
import urllib.parse
import urllib.request


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TU_STORE = "София - ТУ бул. Св. Кл.Охридски 8"
API = "https://api8.composity.cloud/elimex/web/content/fVVVVf"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://elimex.bg",
            "Referer": "https://elimex.bg/",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", "replace")


def parse_product_page(slug: str) -> dict:
    page = fetch_text(f"https://elimex.bg/product/{slug}")
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page)
    if not match:
        raise RuntimeError(f"No product data for {slug}")
    data = json.loads(html.unescape(match.group(1)))
    return data["props"]["pageProps"]["product"]


def clean(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    out = []
    in_tag = False
    for char in text:
        if char == "<":
            in_tag = True
        elif char == ">":
            in_tag = False
            out.append(" ")
        elif not in_tag:
            out.append(char)
    return " ".join("".join(out).split())


def product_stock(product: dict) -> tuple[int, int]:
    tu = 0
    total = 0
    for item in product.get("items") or []:
        total += int(item.get("availability") or 0)
        for location in item.get("availabilityByLocations") or []:
            if location.get("name") == TU_STORE:
                tu += int(location.get("availability") or 0)
    return tu, total


def codes(product: dict) -> str:
    values = []
    for item in product.get("items") or []:
        code = item.get("code")
        sin = item.get("sin")
        if code:
            values.append(str(code))
        elif sin:
            values.append(f"sin {sin}")
    return ", ".join(values)


def search(term: str, limit: int = 25) -> list[dict]:
    url = (
        f"{API}?search={urllib.parse.quote(term)}&isPublished=1"
        f"&query=product-search&limit={limit}&offset=0"
    )
    data = fetch_json(url)
    rows = []
    for product in data.get("data") or []:
        slug = product.get("slug")
        if slug:
            try:
                product = parse_product_page(slug)
            except Exception:
                pass
        tu, total = product_stock(product)
        rows.append(
            {
                "name": product.get("name") or "",
                "url": f"https://elimex.bg/product/{product.get('slug') or slug}",
                "code": codes(product),
                "price": product.get("minPrice"),
                "tu": tu,
                "total": total,
                "description": clean((product.get("shortDescription") or "") + " " + (product.get("description") or "")),
            }
        )
    return rows


def main() -> int:
    terms = sys.argv[1:] or ["влажност почва", "водна помпа", "mosfet logic", "jst 2 pin"]
    for term in terms:
        print(f"=== {term} ===")
        for row in search(term):
            print(
                f"{row['name']} | code={row['code']} | TU={row['tu']} | total={row['total']} | "
                f"price={row['price']} | {row['url']}"
            )
            print(row["description"][:600])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
