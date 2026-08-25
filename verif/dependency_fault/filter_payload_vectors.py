#!/usr/bin/env python3

"""Keep RAW-checker vectors whose instruction PC is inside a marked payload."""

import argparse
import csv
from pathlib import Path


def number(text):
    return int(text, 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start", required=True, type=number)
    parser.add_argument("--end", required=True, type=number)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with args.input.open(newline="") as source, args.output.open("w", newline="") as target:
        reader = csv.DictReader(source)
        writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            pc = int(row["pc"], 16)
            # Use [start, end), exactly like the two assembly linker symbols.
            if args.start <= pc < args.end:
                writer.writerow(row)
                kept += 1
    print(f"{args.output}: {kept} payload vectors")


if __name__ == "__main__":
    main()
