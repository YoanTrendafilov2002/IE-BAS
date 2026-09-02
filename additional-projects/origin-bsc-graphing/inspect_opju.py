import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "originpro_pkg"))

import originpro as op


PROJECT = Path(r"C:\Users\user\Downloads\BSC-all.opju")
OUTPUT = Path(__file__).parent / "opju_inventory.json"


def main():
    inventory = []
    try:
        op.set_show(False)
        if not op.open(str(PROJECT), readonly=True):
            raise RuntimeError(f"Origin could not open {PROJECT}")

        for book in op.pages("w"):
            book_info = {
                "name": book.name,
                "long_name": book.lname,
                "sheets": [],
            }
            for sheet in book:
                labels = {}
                for label_type in ("L", "U", "C", "F", "S"):
                    try:
                        labels[label_type] = sheet.get_labels(label_type)
                    except Exception as exc:
                        labels[label_type] = {"error": str(exc)}
                book_info["sheets"].append(
                    {
                        "name": sheet.name,
                        "long_name": sheet.lname,
                        "shape": sheet.shape,
                        "labels": labels,
                    }
                )
            inventory.append(book_info)

        OUTPUT.write_text(
            json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Wrote {OUTPUT}")
        for book in inventory:
            print(f"BOOK {book['name']!r} / {book['long_name']!r}")
            for sheet in book["sheets"]:
                print(
                    f"  SHEET {sheet['name']!r} / {sheet['long_name']!r}"
                    f" shape={sheet['shape']}"
                )
    finally:
        op.exit()


if __name__ == "__main__":
    main()
