#!/usr/bin/env python3

"""Compare equal-budget control and targeted tests with a baseline corpus."""

import argparse
import csv
from pathlib import Path


def detected_by_program(path):
    """Build one detected-fault set per program from a campaign CSV."""
    sets = {}
    fault_ids = set()
    infrastructure_errors = 0
    with path.open(newline="") as input_file:
        for row in csv.DictReader(input_file):
            fault_ids.add(row["fault_id"])
            if row["classification"] == "INFRASTRUCTURE_ERROR":
                infrastructure_errors += 1
            if row["detected"] == "1":
                sets.setdefault(row["program"], set()).add(row["fault_id"])
    return sets, fault_ids, infrastructure_errors


def main():
    """Compare the ALU descriptor treatment only with its matched control."""
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline_results", type=Path)
    parser.add_argument("intervention_results", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)

    baseline, baseline_faults, baseline_errors = detected_by_program(
        args.baseline_results
    )
    intervention, intervention_faults, intervention_errors = detected_by_program(
        args.intervention_results
    )
    if baseline_faults != intervention_faults:
        raise SystemExit("Baseline and intervention fault populations differ")
    baseline_union = set().union(*baseline.values())
    control = intervention.get("alu_control", set())
    target = intervention.get("alu_sra_target", set())

    rows = [
        ("baseline_corpus", baseline_union),
        ("alu_control", control),
        ("alu_sra_target", target),
    ]
    output_path = args.output_directory / "descriptor-intervention-summary.csv"
    with output_path.open("w", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["treatment", "detected_faults", "new_vs_baseline",
                         "new_vs_control", "coverage_percent"])
        for name, faults in rows:
            writer.writerow([
                name, len(faults), len(faults - baseline_union),
                len(faults - control) if name == "alu_sra_target" else "",
                f"{100.0 * len(faults) / len(baseline_faults):.2f}",
            ])

    detail_path = args.output_directory / "incremental-faults.txt"
    detail_path.write_text(
        "target_new_vs_baseline=" + ",".join(sorted(target - baseline_union)) + "\n"
        "target_new_vs_control=" + ",".join(sorted(target - control)) + "\n"
        "control_new_vs_baseline=" + ",".join(sorted(control - baseline_union)) + "\n"
        f"baseline_infrastructure_errors={baseline_errors}\n"
        f"intervention_infrastructure_errors={intervention_errors}\n"
    )
    print(f"Wrote {output_path}")
    print(f"Wrote {detail_path}")


if __name__ == "__main__":
    main()
