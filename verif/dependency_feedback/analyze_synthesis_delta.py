#!/usr/bin/env python3
"""Calculate a reproducible hardware-cost delta from two Yosys JSON files."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def load_counts(path: Path) -> dict[str, int]:
    design = json.loads(path.read_text())
    if len(design["modules"]) != 1:
        raise ValueError(f"Expected one synthesized top module in {path}")
    module = next(iter(design["modules"].values()))
    types = Counter(cell["type"] for cell in module["cells"].values())

    # $scopeinfo preserves hierarchy metadata and is not physical hardware.
    hardware_cells = sum(count for kind, count in types.items() if kind != "$scopeinfo")
    state_cells = sum(count for kind, count in types.items() if "DFF" in kind)
    return {
        "wires": len(module["netnames"]),
        "wire_bits": sum(len(net["bits"]) for net in module["netnames"].values()),
        "hardware_cells": hardware_cells,
        "combinational_cells": hardware_cells - state_cells,
        "state_cells": state_cells,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--monitored", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    baseline = load_counts(args.baseline)
    monitored = load_counts(args.monitored)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", newline="") as destination:
        writer = csv.writer(destination)
        writer.writerow(["metric", "baseline", "monitored", "delta", "delta_percent"])
        for metric in baseline:
            old = baseline[metric]
            new = monitored[metric]
            delta = new - old
            percent = "NA" if old == 0 else f"{100.0 * delta / old:.2f}"
            writer.writerow([metric, old, new, delta, percent])


if __name__ == "__main__":
    main()
