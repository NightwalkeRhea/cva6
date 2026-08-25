#!/usr/bin/env python3

"""Compare each Milestone 8C intervention only with its matched control."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


PAIRS = (
    ("producer_age", "newest_producer_control", "older_producer"),
    ("producer_multiplicity", "single_producer_control", "multiple_producers"),
    ("scoreboard_wrap", "wrap_pair_early", "wrap_pair_wrapped"),
)


def write_csv(path, fields, rows):
    """Write small deterministic tables that can be copied into LaTeX."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with args.campaign.open(newline="") as source:
        campaign = list(csv.DictReader(source))

    # Build one detected-fault set for every treatment.
    detected = defaultdict(set)
    first_context = {}
    for row in campaign:
        if row["classification"] == "DETECTED":
            detected[row["trace"]].add(row["fault_id"])
            first_context[(row["trace"], row["fault_id"])] = row["first_error_vector"]

    pair_rows = []
    changed_rows = []
    for descriptor, control, treatment in PAIRS:
        added = detected[treatment] - detected[control]
        lost = detected[control] - detected[treatment]
        shared = detected[control] & detected[treatment]
        pair_rows.append({
            "descriptor_intervention": descriptor,
            "control": control,
            "treatment": treatment,
            "control_detected": len(detected[control]),
            "treatment_detected": len(detected[treatment]),
            "added_by_treatment": len(added),
            "lost_by_treatment": len(lost),
            "detected_by_both": len(shared),
            "pair_union": len(detected[control] | detected[treatment]),
        })

        # Preserve exact fault IDs; totals alone can hide complementary sets.
        for direction, faults, owner in (
            ("added", added, treatment),
            ("lost", lost, control),
        ):
            for fault_id in sorted(faults):
                changed_rows.append({
                    "descriptor_intervention": descriptor,
                    "direction": direction,
                    "fault_id": fault_id,
                    "detecting_treatment": owner,
                    "first_error_vector": first_context[(owner, fault_id)],
                })

    write_csv(args.output / "controlled-pair-summary.csv", pair_rows[0].keys(), pair_rows)
    write_csv(args.output / "controlled-pair-changed-faults.csv",
              changed_rows[0].keys(), changed_rows)


if __name__ == "__main__":
    main()
