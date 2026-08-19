#!/usr/bin/env python3

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def percentage(numerator, denominator):
    if denominator == 0:
        return 0.0

    return round(100.0 * numerator / denominator, 2)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze CVA6 ALU fault-campaign results."
    )

    parser.add_argument(
        "results",
        type=Path,
        help="fault-results.csv produced by run_fault_campaign.py",
    )

    parser.add_argument(
        "output",
        type=Path,
        help="Directory for analysis files",
    )

    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    with args.results.open() as input_file:
        rows = list(csv.DictReader(input_file))

    if not rows:
        raise SystemExit("The input CSV contains no result rows")

    infrastructure_errors = [
        row
        for row in rows
        if row["classification"] == "INFRASTRUCTURE_ERROR"
    ]

    if infrastructure_errors:
        raise SystemExit(
            f"Found {len(infrastructure_errors)} infrastructure errors"
        )

    all_faults = {row["fault_id"] for row in rows}
    all_traces = sorted({row["trace"] for row in rows})
    all_programs = sorted({row["program"] for row in rows})

    rows_per_fault = Counter(row["fault_id"] for row in rows)

    invalid_fault_counts = {
        fault: count
        for fault, count in rows_per_fault.items()
        if count != len(all_traces)
    }

    if invalid_fault_counts:
        raise SystemExit(
            f"Faults with an incorrect number of rows: "
            f"{invalid_fault_counts}"
        )

    fault_modes = {}

    for row in rows:
        fault = row["fault_id"]
        mode = row["mode"]

        if fault in fault_modes and fault_modes[fault] != mode:
            raise SystemExit(
                f"Fault {fault} has multiple mutation modes"
            )

        fault_modes[fault] = mode

    detected_by_trace = defaultdict(set)
    detected_by_program = defaultdict(set)

    for row in rows:
        if row["detected"] == "1":
            detected_by_trace[row["trace"]].add(row["fault_id"])
            detected_by_program[row["program"]].add(row["fault_id"])

    corpus_detected = set()

    for detected_faults in detected_by_program.values():
        corpus_detected |= detected_faults

    corpus_undetected = all_faults - corpus_detected
    total_faults = len(all_faults)

    trace_summary = []

    for trace in all_traces:
        selected_rows = [
            row
            for row in rows
            if row["trace"] == trace
        ]

        detected_faults = detected_by_trace[trace]

        first_transactions = [
            int(row["first_failing_transaction"])
            for row in selected_rows
            if row["detected"] == "1"
            and row["first_failing_transaction"]
        ]

        trace_summary.append(
            {
                "trace": trace,
                "detected_faults": len(detected_faults),
                "undetected_faults": total_faults - len(detected_faults),
                "coverage_percent": percentage(
                    len(detected_faults),
                    total_faults,
                ),
                "minimum_first_detection": (
                    min(first_transactions)
                    if first_transactions
                    else ""
                ),
                "median_first_detection": (
                    statistics.median(first_transactions)
                    if first_transactions
                    else ""
                ),
                "maximum_first_detection": (
                    max(first_transactions)
                    if first_transactions
                    else ""
                ),
            }
        )

    baseline = detected_by_program.get("return0", set())
    program_summary = []

    for program in all_programs:
        detected_faults = detected_by_program[program]

        other_program_faults = set()

        for other_program in all_programs:
            if other_program != program:
                other_program_faults |= detected_by_program[other_program]

        program_summary.append(
            {
                "program": program,
                "detected_faults": len(detected_faults),
                "undetected_faults": total_faults - len(detected_faults),
                "coverage_percent": percentage(
                    len(detected_faults),
                    total_faults,
                ),
                "new_faults_vs_return0": len(
                    detected_faults - baseline
                ),
                "return0_faults_missed": len(
                    baseline - detected_faults
                ),
                "exclusive_faults": len(
                    detected_faults - other_program_faults
                ),
            }
        )

    mode_summary = []

    for mode in sorted(set(fault_modes.values())):
        mode_faults = {
            fault
            for fault, fault_mode in fault_modes.items()
            if fault_mode == mode
        }

        detected_mode_faults = mode_faults & corpus_detected

        mode_summary.append(
            {
                "mode": mode,
                "total_faults": len(mode_faults),
                "detected_faults": len(detected_mode_faults),
                "undetected_faults": (
                    len(mode_faults) - len(detected_mode_faults)
                ),
                "coverage_percent": percentage(
                    len(detected_mode_faults),
                    len(mode_faults),
                ),
            }
        )

    pairwise_summary = []

    for program_a in all_programs:
        for program_b in all_programs:
            if program_a == program_b:
                continue

            faults_a = detected_by_program[program_a]
            faults_b = detected_by_program[program_b]

            pairwise_summary.append(
                {
                    "program_a": program_a,
                    "program_b": program_b,
                    "faults_in_a_not_b": len(faults_a - faults_b),
                    "faults_in_b_not_a": len(faults_b - faults_a),
                    "faults_detected_by_both": len(faults_a & faults_b),
                }
            )

    write_csv(
        args.output / "trace-summary.csv",
        [
            "trace",
            "detected_faults",
            "undetected_faults",
            "coverage_percent",
            "minimum_first_detection",
            "median_first_detection",
            "maximum_first_detection",
        ],
        trace_summary,
    )

    write_csv(
        args.output / "program-summary.csv",
        [
            "program",
            "detected_faults",
            "undetected_faults",
            "coverage_percent",
            "new_faults_vs_return0",
            "return0_faults_missed",
            "exclusive_faults",
        ],
        program_summary,
    )

    write_csv(
        args.output / "mutation-mode-summary.csv",
        [
            "mode",
            "total_faults",
            "detected_faults",
            "undetected_faults",
            "coverage_percent",
        ],
        mode_summary,
    )

    write_csv(
        args.output / "pairwise-program-summary.csv",
        [
            "program_a",
            "program_b",
            "faults_in_a_not_b",
            "faults_in_b_not_a",
            "faults_detected_by_both",
        ],
        pairwise_summary,
    )

    undetected_path = args.output / "undetected-faults.txt"
    undetected_path.write_text(
        "".join(
            f"{fault}\n"
            for fault in sorted(corpus_undetected)
        )
    )

    corpus_path = args.output / "corpus-summary.csv"

    write_csv(
        corpus_path,
        [
            "total_faults",
            "detected_faults",
            "undetected_faults",
            "coverage_percent",
            "trace_fault_pairs",
            "detected_trace_fault_pairs",
        ],
        [
            {
                "total_faults": total_faults,
                "detected_faults": len(corpus_detected),
                "undetected_faults": len(corpus_undetected),
                "coverage_percent": percentage(
                    len(corpus_detected),
                    total_faults,
                ),
                "trace_fault_pairs": len(rows),
                "detected_trace_fault_pairs": sum(
                    row["detected"] == "1"
                    for row in rows
                ),
            }
        ],
    )

    print(f"Faults: {total_faults}")
    print(f"Detected by corpus: {len(corpus_detected)}")
    print(f"Undetected by corpus: {len(corpus_undetected)}")
    print(
        "Corpus coverage: "
        f"{percentage(len(corpus_detected), total_faults):.2f}%"
    )
    print(f"Wrote analysis to: {args.output}")


if __name__ == "__main__":
    main()
