import json
from pathlib import Path

import originpro as op


OUT_DIR = Path(
    r"C:\Users\user\Documents\Codex\2026-06-05"
    r"\can-you-make-a-single-graph\work"
)
TARGET = "BSC - 03.06.2026"


def norm(value):
    return " ".join(str(value).split()).casefold()


def sheet_record(book, sheet, include_data=False):
    record = {
        "book_name": book.name,
        "book_long_name": book.lname,
        "sheet_name": sheet.name,
        "sheet_long_name": sheet.lname,
        "shape": list(sheet.shape),
        "labels": {},
    }
    for label_type in ("L", "U", "C", "F", "S"):
        try:
            record["labels"][label_type] = sheet.get_labels(label_type)
        except Exception as exc:
            record["labels"][label_type] = {"error": str(exc)}
    if include_data:
        record["columns"] = [sheet.to_list(col) for col in range(sheet.cols)]
    return record


def main():
    inventory = []
    matches = []
    wanted = norm(TARGET)

    for book in op.pages("w"):
        for sheet in book:
            names = (book.name, book.lname, sheet.name, sheet.lname)
            is_match = any(wanted == norm(name) for name in names)
            record = sheet_record(book, sheet, include_data=is_match)
            inventory.append(record)
            if is_match:
                matches.append(record)

    (OUT_DIR / "origin_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "target_sheet.json").write_text(
        json.dumps(matches, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "origin_extract.done").write_text(
        f"inventory={len(inventory)} matches={len(matches)}", encoding="ascii"
    )


main()
