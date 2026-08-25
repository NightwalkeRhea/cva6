#!/usr/bin/env python3
"""Compare a full-core monitor file with the independent trace oracle."""

import argparse
import csv
import subprocess
from pathlib import Path


def read_integrated_value(path: Path) -> int:
    # The bitmap is sticky, so the final emitted row is the final program value.
    with path.open(newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError(f"No feedback rows in {path}")
    return int(rows[-1]["dependency_feedback"], 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feedback", required=True, type=Path)
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--pc-start", required=True)
    parser.add_argument("--pc-end", required=True)
    args = parser.parse_args()

    integrated = read_integrated_value(args.feedback)

    # Reuse the frozen Python specification rather than duplicating bit rules.
    oracle = Path(__file__).with_name("expected_monitor_bitmap.py")
    expected_text = subprocess.check_output(
        [
            "python3", str(oracle), "--variant", "5",
            "--pc-start", args.pc_start, "--pc-end", args.pc_end,
            str(args.trace),
        ],
        text=True,
    ).strip()
    expected = int(expected_text, 16)

    verdict = "MATCH" if integrated == expected else "MISMATCH"
    print(f"integrated=0x{integrated:02x},offline=0x{expected:02x},status={verdict}")
    return 0 if integrated == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
