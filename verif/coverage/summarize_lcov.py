#!/usr/bin/env python3
"""Convert Verilator LCOV line records into a sortable per-source CSV."""

import csv
import pathlib
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} INPUT.info OUTPUT.csv", file=sys.stderr)
        return 2

    input_path = pathlib.Path(sys.argv[1])
    output_path = pathlib.Path(sys.argv[2])
    records = []
    source = None
    found = hit = 0

    def save_record():
        if source is None or found == 0:
            return
        percent = 100.0 * hit / found
        records.append((percent, hit, found, source))

    for raw_line in input_path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("SF:"):
            save_record()
            source = raw_line[3:]
            found = hit = 0
        elif raw_line.startswith("DA:"):
            found += 1
            count = int(raw_line.split(",", 2)[1])
            hit += count > 0
        elif raw_line == "end_of_record":
            save_record()
            source = None
            found = hit = 0
    save_record()

    records.sort(key=lambda row: (row[0], -row[2], row[3]))
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(("line_coverage_percent", "lines_hit", "lines_found", "source"))
        for percent, lines_hit, lines_found, source_name in records:
            writer.writerow((f"{percent:.2f}", lines_hit, lines_found, source_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
