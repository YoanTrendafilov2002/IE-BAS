from pathlib import Path
from collections import Counter
import struct
import math
import re
import csv
import sys


def extract_ascii_strings(data: bytes, min_len: int = 4):
    pattern = rb"[\x20-\x7E]{" + str(min_len).encode() + rb",}"
    return [(m.start(), m.group().decode("latin-1", errors="replace")) for m in re.finditer(pattern, data)]


def find_distribution_blocks(data: bytes):
    term = b"distribution"
    offsets = []
    start = 0

    while True:
        pos = data.find(term, start)
        if pos == -1:
            break
        offsets.append(pos)
        start = pos + 1

    return offsets


def read_float64(data: bytes, offset: int, endian: str):
    if offset + 8 > len(data):
        return None

    try:
        x = struct.unpack(endian + "d", data[offset:offset + 8])[0]
    except struct.error:
        return None

    if not math.isfinite(x):
        return None

    return x


def read_float32(data: bytes, offset: int, endian: str):
    if offset + 4 > len(data):
        return None

    try:
        x = struct.unpack(endian + "f", data[offset:offset + 4])[0]
    except struct.error:
        return None

    if not math.isfinite(x):
        return None

    return x


def scan_plausible_numbers(block: bytes):
    """
    Scans one block for plausible numeric values.
    This is diagnostic. It exports candidate numbers with offsets.
    """
    rows = []

    for offset in range(0, len(block)):
        for typ, size, reader in [
            ("float64_be", 8, lambda b, o: read_float64(b, o, ">")),
            ("float64_le", 8, lambda b, o: read_float64(b, o, "<")),
            ("float32_be", 4, lambda b, o: read_float32(b, o, ">")),
            ("float32_le", 4, lambda b, o: read_float32(b, o, "<")),
        ]:
            if offset + size > len(block):
                continue

            value = reader(block, offset)

            if value is None:
                continue

            # Broad range for PM, Cn, flow, temp, pressure, PSD, status-like values.
            if -1000 <= value <= 1_000_000:
                rows.append((offset, typ, value))

    return rows


def export_header_strings(data: bytes, first_block_offset: int, out_path: Path):
    header = data[:first_block_offset]
    strings = extract_ascii_strings(header, min_len=4)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        for offset, text in strings:
            f.write(f"{offset}\t{text}\n")


def export_block_strings(data: bytes, offsets, out_path: Path, max_blocks: int = 20):
    with out_path.open("w", encoding="utf-8", newline="") as f:
        for idx, start in enumerate(offsets[:max_blocks]):
            end = offsets[idx + 1] if idx + 1 < len(offsets) else min(start + 5000, len(data))
            block = data[start:end]
            strings = extract_ascii_strings(block, min_len=3)

            f.write(f"\n===== BLOCK {idx} OFFSET {start} SIZE {len(block)} =====\n")
            for rel_offset, text in strings:
                f.write(f"{rel_offset}\t{text}\n")


def export_block_hex(data: bytes, offsets, out_path: Path, block_index: int = 0, size: int = 4096):
    if not offsets:
        return

    start = offsets[block_index]
    block = data[start:start + size]

    with out_path.open("w", encoding="utf-8") as f:
        for i in range(0, len(block), 16):
            chunk = block[i:i + 16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            f.write(f"{i:08X}  {hex_part:<48}  {ascii_part}\n")


def export_numeric_scan_for_first_block(data: bytes, offsets, out_path: Path):
    if not offsets:
        return

    start = offsets[0]
    end = offsets[1] if len(offsets) > 1 else min(start + 5000, len(data))
    block = data[start:end]

    rows = scan_plausible_numbers(block)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["relative_offset", "type", "value"])

        for offset, typ, value in rows:
            writer.writerow([offset, typ, repr(value)])


def export_fixed_offset_timeseries(data: bytes, offsets, out_path: Path, max_blocks: int | None = None):
    """
    Creates a wide diagnostic table.

    It reads big-endian float64 values at every 8-byte aligned offset in each block.
    This does NOT know which field is PM1/PM2.5/etc.
    The goal is to create candidate time series columns.

    If a column changes smoothly and has values in expected ranges, it may be a real field.
    """
    if not offsets:
        return

    block_lengths = []
    for i, start in enumerate(offsets[:-1]):
        block_lengths.append(offsets[i + 1] - start)

    normal_len = Counter(block_lengths).most_common(1)[0][0]
    print(f"Using normal block size for wide export: {normal_len} bytes")

    aligned_offsets = list(range(0, normal_len - 8, 8))

    if max_blocks is None:
        selected_offsets = offsets
    else:
        selected_offsets = offsets[:max_blocks]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")

        header = ["record_index", "file_offset", "block_size"]
        header += [f"be_f64_at_{o}" for o in aligned_offsets]
        writer.writerow(header)

        for idx, start in enumerate(selected_offsets):
            if idx + 1 < len(offsets):
                block_size = offsets[idx + 1] - start
            else:
                block_size = min(normal_len, len(data) - start)

            # Skip weird blocks for this simple fixed-offset export.
            if block_size < normal_len:
                continue

            block = data[start:start + normal_len]

            row = [idx, start, block_size]

            for rel in aligned_offsets:
                x = read_float64(block, rel, ">")
                if x is None or not (-1000 <= x <= 1_000_000):
                    row.append("")
                else:
                    row.append(f"{x:.10g}")

            writer.writerow(row)

            if idx % 5000 == 0 and idx > 0:
                print(f"Exported {idx} records...")


def export_candidate_pm_like_series(data: bytes, offsets, out_path: Path, max_blocks: int | None = None):
    """
    More compact diagnostic export.

    It scans each normal block for plausible big-endian float64 values.
    Then it keeps only values in ranges that could plausibly include PM, Cn, meteo, flow.

    Output is long format:
    record_index, file_offset, relative_offset, value

    This is large, but much smaller than exporting every possible float interpretation.
    """
    if not offsets:
        return

    block_lengths = []
    for i, start in enumerate(offsets[:-1]):
        block_lengths.append(offsets[i + 1] - start)

    normal_len = Counter(block_lengths).most_common(1)[0][0]
    selected_offsets = offsets if max_blocks is None else offsets[:max_blocks]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["record_index", "file_offset", "relative_offset", "be_float64_value"])

        for idx, start in enumerate(selected_offsets):
            if idx + 1 < len(offsets):
                block_size = offsets[idx + 1] - start
            else:
                block_size = min(normal_len, len(data) - start)

            if block_size < normal_len:
                continue

            block = data[start:start + normal_len]

            # Big-endian float64 is the most likely from previous inspection.
            for rel in range(0, normal_len - 8):
                x = read_float64(block, rel, ">")
                if x is None:
                    continue

                # Plausible range for PM/Cn/meteo/status/flow.
                if -100 <= x <= 100000:
                    writer.writerow([idx, start, rel, f"{x:.12g}"])

            if idx % 1000 == 0 and idx > 0:
                print(f"Scanned {idx} records...")


def main():
    if len(sys.argv) < 2:
        print('Usage: python promo_dump.py "file.promo"')
        sys.exit(1)

    in_file = Path(sys.argv[1])
    if not in_file.exists():
        print(f"File not found: {in_file}")
        sys.exit(1)

    out_dir = in_file.with_suffix("")
    out_dir = out_dir.parent / (out_dir.name + "_decoded_attempt")
    out_dir.mkdir(exist_ok=True)

    print(f"Reading: {in_file}")
    data = in_file.read_bytes()
    print(f"File size: {len(data):,} bytes")

    print("Finding distribution blocks...")
    offsets = find_distribution_blocks(data)
    print(f"Found distribution blocks: {len(offsets):,}")

    if not offsets:
        print("No 'distribution' blocks found. Exporting only global strings.")
        strings = extract_ascii_strings(data, min_len=4)
        with (out_dir / "all_strings.txt").open("w", encoding="utf-8") as f:
            for offset, text in strings:
                f.write(f"{offset}\t{text}\n")
        return

    diffs = [offsets[i + 1] - offsets[i] for i in range(len(offsets) - 1)]
    spacing_counts = Counter(diffs).most_common()

    with (out_dir / "file_summary.txt").open("w", encoding="utf-8") as f:
        f.write(f"Input file: {in_file}\n")
        f.write(f"File size bytes: {len(data)}\n")
        f.write(f"Distribution blocks: {len(offsets)}\n")
        f.write(f"First distribution offset: {offsets[0]}\n")
        f.write(f"Last distribution offset: {offsets[-1]}\n")
        f.write("\nBlock spacing counts:\n")
        for spacing, count in spacing_counts[:50]:
            f.write(f"{spacing}\t{count}\n")

    print("Exporting header strings...")
    export_header_strings(data, offsets[0], out_dir / "header_strings.txt")

    print("Exporting strings from first blocks...")
    export_block_strings(data, offsets, out_dir / "first_blocks_strings.txt", max_blocks=20)

    print("Exporting hex dump of first block...")
    export_block_hex(data, offsets, out_dir / "first_block_hex.txt", block_index=0, size=5000)

    print("Exporting numeric scan of first block...")
    export_numeric_scan_for_first_block(data, offsets, out_dir / "first_block_numeric_scan.txt")

    print("Exporting compact candidate PM-like series from first 2000 records...")
    export_candidate_pm_like_series(
        data,
        offsets,
        out_dir / "candidate_pm_like_series_first_2000.txt",
        max_blocks=2000
    )

    print("Exporting fixed-offset wide time series from first 2000 records...")
    export_fixed_offset_timeseries(
        data,
        offsets,
        out_dir / "fixed_offset_be_float64_wide_first_2000.txt",
        max_blocks=2000
    )

    print("\nDone.")
    print(f"Output folder: {out_dir}")
    print("\nImportant files:")
    print("  file_summary.txt")
    print("  header_strings.txt")
    print("  first_blocks_strings.txt")
    print("  first_block_hex.txt")
    print("  first_block_numeric_scan.txt")
    print("  candidate_pm_like_series_first_2000.txt")
    print("  fixed_offset_be_float64_wide_first_2000.txt")


if __name__ == "__main__":
    main()