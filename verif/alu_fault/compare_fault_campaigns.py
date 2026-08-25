#!/usr/bin/env python3

import argparse
import csv
import json
import math
import shlex
from collections import defaultdict
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Compare mixed and stratified CVA6 ALU mutation campaigns."
    )
    parser.add_argument("--netlist", required=True, type=Path)
    parser.add_argument("--mixed-fault-list", required=True, type=Path)
    parser.add_argument("--mixed-results", required=True, type=Path)
    parser.add_argument("--stratified-results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--top", default="alu_cv32a65x_wrapper")
    return parser.parse_args()


def option_value(tokens, option):
    position = tokens.index(option)
    return tokens[position + 1]


def read_results(path):
    with path.open() as input_file:
        rows = list(csv.DictReader(input_file))

    errors = [
        row for row in rows if row["classification"] == "INFRASTRUCTURE_ERROR"
    ]

    if errors:
        raise SystemExit(f"{path} contains {len(errors)} infrastructure errors")

    return rows


def detected_faults(rows, allowed_faults=None):
    result = {
        row["fault_id"]
        for row in rows
        if row["detected"] == "1"
    }

    if allowed_faults is not None:
        result &= allowed_faults

    return result


def program_sets(rows, allowed_faults):
    result = defaultdict(set)

    for row in rows:
        if row["detected"] == "1" and row["fault_id"] in allowed_faults:
            result[row["program"]].add(row["fault_id"])

    return result


def mode_map(rows):
    result = {}

    for row in rows:
        fault = row["fault_id"]
        mode = row["mode"]

        if fault in result and result[fault] != mode:
            raise SystemExit(f"Fault {fault} has inconsistent modes")

        result[fault] = mode

    return result


def wilson_interval(detected, total, z=1.959963984540054):
    if total == 0:
        return 0.0, 0.0

    proportion = detected / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )

    return 100.0 * (center - margin), 100.0 * (center + margin)


def metric_row(name, faults, detected):
    count = len(faults)
    detected_count = len(detected & faults)
    low, high = wilson_interval(detected_count, count)

    return {
        "population": name,
        "total_mutations": count,
        "detected_mutations": detected_count,
        "undetected_mutations": count - detected_count,
        "coverage_percent": f"{100.0 * detected_count / count:.2f}",
        "wilson_95_low_percent": f"{low:.2f}",
        "wilson_95_high_percent": f"{high:.2f}",
    }


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_arguments()
    args.output.mkdir(parents=True, exist_ok=True)

    design = json.loads(args.netlist.read_text())
    module = design["modules"][args.top]

    output_bits = set()

    for port_name in ("result_o", "branch_result_o"):
        output_bits.update(module["ports"][port_name]["bits"])

    mixed_lines = [
        line.strip()
        for line in args.mixed_fault_list.read_text().splitlines()
        if line.strip()
    ]

    mixed_all = {f"{index:03d}" for index in range(len(mixed_lines))}
    mixed_internal = set()

    for index, mutation in enumerate(mixed_lines):
        tokens = shlex.split(mutation)
        cell_name = option_value(tokens, "-cell")
        port_name = option_value(tokens, "-port")
        port_bit = int(option_value(tokens, "-portbit"))
        bit = module["cells"][cell_name]["connections"][port_name][port_bit]

        if isinstance(bit, int) and bit not in output_bits:
            mixed_internal.add(f"{index:03d}")

    mixed_rows = read_results(args.mixed_results)
    stratified_rows = read_results(args.stratified_results)

    stratified_all = {row["fault_id"] for row in stratified_rows}
    mixed_detected = detected_faults(mixed_rows)
    stratified_detected = detected_faults(stratified_rows)

    comparison_rows = [
        metric_row("mixed_all", mixed_all, mixed_detected),
        metric_row("mixed_internal_subset", mixed_internal, mixed_detected),
        metric_row(
            "stratified_internal_cell_outputs",
            stratified_all,
            stratified_detected,
        ),
    ]

    write_csv(
        args.output / "campaign-comparison.csv",
        list(comparison_rows[0]),
        comparison_rows,
    )

    program_rows = []

    for population, rows, faults in (
        ("mixed_internal_subset", mixed_rows, mixed_internal),
        (
            "stratified_internal_cell_outputs",
            stratified_rows,
            stratified_all,
        ),
    ):
        sets = program_sets(rows, faults)

        for program in sorted({row["program"] for row in rows}):
            detected = sets[program]
            low, high = wilson_interval(len(detected), len(faults))
            program_rows.append(
                {
                    "population": population,
                    "program": program,
                    "detected_mutations": len(detected),
                    "total_mutations": len(faults),
                    "coverage_percent": f"{100.0 * len(detected) / len(faults):.2f}",
                    "wilson_95_low_percent": f"{low:.2f}",
                    "wilson_95_high_percent": f"{high:.2f}",
                }
            )

    write_csv(
        args.output / "program-comparison.csv",
        list(program_rows[0]),
        program_rows,
    )

    mode_rows = []

    for population, rows, faults in (
        ("mixed_internal_subset", mixed_rows, mixed_internal),
        (
            "stratified_internal_cell_outputs",
            stratified_rows,
            stratified_all,
        ),
    ):
        modes = mode_map(rows)
        detected = detected_faults(rows, faults)

        for mode in sorted(set(modes.values())):
            mode_faults = {
                fault
                for fault in faults
                if modes[fault] == mode
            }
            mode_detected = detected & mode_faults
            low, high = wilson_interval(len(mode_detected), len(mode_faults))
            mode_rows.append(
                {
                    "population": population,
                    "mode": mode,
                    "detected_mutations": len(mode_detected),
                    "total_mutations": len(mode_faults),
                    "coverage_percent": (
                        f"{100.0 * len(mode_detected) / len(mode_faults):.2f}"
                    ),
                    "wilson_95_low_percent": f"{low:.2f}",
                    "wilson_95_high_percent": f"{high:.2f}",
                }
            )

    write_csv(
        args.output / "mode-comparison.csv",
        list(mode_rows[0]),
        mode_rows,
    )

    report_lines = [
        "# CVA6 ALU mutation-campaign comparison",
        "",
        "| Population | Detected | Total | Coverage | Wilson 95% CI |",
        "|---|---:|---:|---:|---:|",
    ]

    for row in comparison_rows:
        report_lines.append(
            f"| {row['population']} | {row['detected_mutations']} | "
            f"{row['total_mutations']} | {row['coverage_percent']}% | "
            f"{row['wilson_95_low_percent']}--"
            f"{row['wilson_95_high_percent']}% |"
        )

    report_lines.extend(
        [
            "",
            "The mixed and stratified internal populations contain different "
            "random targets. Their point estimates must not be treated as a "
            "paired comparison. Overlapping confidence intervals mean that the "
            "observed difference alone is not evidence of improved stimulus.",
            "",
        ]
    )

    (args.output / "comparison-report.md").write_text(
        "\n".join(report_lines)
    )

    print(f"Mixed internal targets: {len(mixed_internal)}")
    print(f"Stratified internal targets: {len(stratified_all)}")
    print(f"Wrote comparison to: {args.output}")


if __name__ == "__main__":
    main()
