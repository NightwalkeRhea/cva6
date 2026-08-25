#!/usr/bin/env python3

"""Relate compact RAW descriptors to the first observation of injected faults."""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


DESCRIPTORS = (
    "occupancy_bin",
    "raw_valid",
    "producer_age_bin",
    "matching_producers_bin",
    "wrap_selection",
    "context_bin",
)


def write_table(path, fields, rows):
    """Write one deterministic CSV table for later LaTeX or plotting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path}")


def read_descriptors(directory):
    """Keep descriptor rows in replay order; first-error indices are one-based."""
    traces = {}
    for path in sorted(directory.glob("*.descriptors.csv")):
        name = path.name.removesuffix(".descriptors.csv")
        with path.open(newline="") as source:
            traces[name] = list(csv.DictReader(source))
    if not traces:
        raise SystemExit(f"No descriptor CSV files in {directory}")
    return traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--descriptors", required=True, type=Path)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    traces = read_descriptors(args.descriptors)
    with args.campaign.open(newline="") as source:
        campaign = list(csv.DictReader(source))

    # Count how often a bin occurs and whether each treatment reaches it at all.
    occurrence = Counter()
    visited_by = defaultdict(set)
    for treatment, rows in traces.items():
        for row in rows:
            for descriptor in DESCRIPTORS:
                key = (descriptor, row[descriptor])
                occurrence[(treatment, *key)] += 1
                visited_by[key].add(treatment)

    # Join the first mismatch index to the exact vector that exposed the fault.
    first_detection = Counter()
    first_faults = defaultdict(set)
    detected_faults = defaultdict(set)
    for result in campaign:
        if result["classification"] != "DETECTED":
            continue
        treatment = result["trace"]
        vector_index = int(result["first_error_vector"])
        vector = traces[treatment][vector_index - 1]
        detected_faults[treatment].add(result["fault_id"])
        for descriptor in DESCRIPTORS:
            key = (descriptor, vector[descriptor])
            first_detection[(treatment, *key)] += 1
            first_faults[(treatment, *key)].add(result["fault_id"])

    relevance_rows = []
    for treatment in sorted(traces):
        keys = {
            (descriptor, row[descriptor])
            for row in traces[treatment]
            for descriptor in DESCRIPTORS
        }
        for descriptor, value in sorted(keys):
            relevance_rows.append({
                "treatment": treatment,
                "descriptor": descriptor,
                "bin": value,
                "vector_occurrences": occurrence[(treatment, descriptor, value)],
                "first_detections": first_detection[(treatment, descriptor, value)],
                "distinct_first_detected_faults": len(
                    first_faults[(treatment, descriptor, value)]
                ),
            })
    write_table(
        args.output / "descriptor-first-detection.csv",
        relevance_rows[0].keys(), relevance_rows,
    )

    # Focus selection on faults added beyond the software-like independent case.
    baseline = "independent"
    incremental_rows = []
    for result in campaign:
        treatment = result["trace"]
        is_new_fault = (
            result["classification"] == "DETECTED"
            and treatment != baseline
            and result["fault_id"] not in detected_faults[baseline]
        )
        if not is_new_fault:
            continue
        vector_index = int(result["first_error_vector"])
        vector = traces[treatment][vector_index - 1]
        incremental_rows.append({
            "treatment": treatment,
            "fault_id": result["fault_id"],
            "first_error_vector": vector_index,
            "occupancy_bin": vector["occupancy_bin"],
            "raw_valid": vector["raw_valid"],
            "producer_age_bin": vector["producer_age_bin"],
            "matching_producers_bin": vector["matching_producers_bin"],
            "wrap_selection": vector["wrap_selection"],
            "context_bin": vector["context_bin"],
        })
    write_table(
        args.output / "incremental-fault-first-context.csv",
        incremental_rows[0].keys(), incremental_rows,
    )

    # Compare visited context bins and detected fault sets without implying causality.
    pair_rows = []
    treatments = sorted(traces)
    for position, left in enumerate(treatments):
        for right in treatments[position + 1:]:
            left_contexts = {
                row["context_bin"] for row in traces[left]
            }
            right_contexts = {
                row["context_bin"] for row in traces[right]
            }
            pair_rows.append({
                "treatment_a": left,
                "treatment_b": right,
                "contexts_only_a": len(left_contexts - right_contexts),
                "contexts_only_b": len(right_contexts - left_contexts),
                "contexts_shared": len(left_contexts & right_contexts),
                "faults_only_a": len(detected_faults[left] - detected_faults[right]),
                "faults_only_b": len(detected_faults[right] - detected_faults[left]),
                "faults_shared": len(detected_faults[left] & detected_faults[right]),
            })
    write_table(
        args.output / "pairwise-context-faults.csv",
        pair_rows[0].keys(), pair_rows,
    )

    # A constant descriptor cannot guide search inside this experiment.
    variability_rows = []
    for descriptor in DESCRIPTORS:
        all_values = {
            row[descriptor] for rows in traces.values() for row in rows
        }
        variability_rows.append({
            "descriptor": descriptor,
            "global_populated_bins": len(all_values),
            "varies": int(len(all_values) > 1),
        })
    write_table(
        args.output / "descriptor-variability.csv",
        variability_rows[0].keys(), variability_rows,
    )


if __name__ == "__main__":
    main()
