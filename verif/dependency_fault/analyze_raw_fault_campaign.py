#!/usr/bin/env python3

"""Summarize per-treatment and pairwise RAW-checker fault detection."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = list(csv.DictReader(args.results.open()))
    faults = sorted({row["fault_id"] for row in rows})
    traces = sorted({row["trace"] for row in rows})
    detected = defaultdict(set)
    for row in rows:
        if row["classification"] == "DETECTED":
            detected[row["trace"]].add(row["fault_id"])
    corpus = set().union(*(detected[name] for name in traces))

    summary = []
    for name in traces:
        others = set().union(*(detected[item] for item in traces if item != name))
        summary.append({
            "treatment": name,
            "detected_faults": len(detected[name]),
            "undetected_faults": len(faults) - len(detected[name]),
            "coverage_percent": f"{100 * len(detected[name]) / len(faults):.2f}",
            "exclusive_faults": len(detected[name] - others),
        })
    write_csv(args.output / "treatment-summary.csv", summary[0].keys(), summary)

    pairs = []
    for left in traces:
        for right in traces:
            if left >= right:
                continue
            pairs.append({
                "treatment_a": left, "treatment_b": right,
                "faults_in_a_not_b": len(detected[left] - detected[right]),
                "faults_in_b_not_a": len(detected[right] - detected[left]),
                "faults_detected_by_both": len(detected[left] & detected[right]),
            })
    write_csv(args.output / "pairwise-summary.csv", pairs[0].keys(), pairs)

    corpus_row = [{
        "total_faults": len(faults), "detected_faults": len(corpus),
        "undetected_faults": len(faults) - len(corpus),
        "coverage_percent": f"{100 * len(corpus) / len(faults):.2f}",
        "trace_fault_pairs": len(rows),
        "infrastructure_errors": sum(
            row["classification"] == "INFRASTRUCTURE_ERROR" for row in rows
        ),
    }]
    write_csv(args.output / "corpus-summary.csv", corpus_row[0].keys(), corpus_row)


if __name__ == "__main__":
    main()
