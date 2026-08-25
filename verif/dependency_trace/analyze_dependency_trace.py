#!/usr/bin/env python3

"""Validate and summarize a CVA6 dependency-resolution trace."""

import argparse
import csv
from collections import Counter
from pathlib import Path


SOURCE_NAMES = {
    0: "REGFILE",
    1: "SCOREBOARD",
    2: "FLU_WB",
    3: "STORE_WB",
    4: "LOAD_WB",
    5: "FPU_OR_ALU2_WB",
    6: "X_WB",
    7: "SAME_CYCLE_ALU",
    8: "UNAVAILABLE",
    9: "PC",
    10: "ZIMM",
    11: "IMMEDIATE",
}


def integer(row, field):
    return int(row[field])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)

    with args.trace.open(newline="") as trace_file:
        rows = list(csv.DictReader(trace_file))
    if not rows:
        raise SystemExit(f"Trace contains no issue attempts: {args.trace}")

    expected_columns = 29
    if len(rows[0]) != expected_columns:
        raise SystemExit(
            f"Expected {expected_columns} columns, found {len(rows[0])}"
        )

    # Separate completed issue handshakes from repeated stalled attempts.
    accepted = [row for row in rows if integer(row, "issue_accepted")]
    unavailable_accepted = [
        row for row in accepted
        if integer(row, "rs1_source") == 8 or integer(row, "rs2_source") == 8
    ]
    if unavailable_accepted:
        raise SystemExit(
            f"Invariant failure: {len(unavailable_accepted)} accepted issues "
            "used an unavailable operand"
        )

    # Same-cycle ALU bypass is counted separately from ordinary forwarding.
    ordinary_forward_sources = {1, 2, 3, 4, 5, 6}
    for operand in ("rs1", "rs2"):
        forwarded = sum(integer(row, f"{operand}_forwarded") for row in accepted)
        classified = sum(
            integer(row, f"{operand}_source") in ordinary_forward_sources
            for row in accepted
        )
        if forwarded != classified:
            raise SystemExit(
                f"Invariant failure: {operand} has {forwarded} consumed "
                f"forwarding flags but {classified} ordinary forwarding sources"
            )

    # Preserve raw counts; percentages can be derived later without rerunning RTL.
    metrics = {
        "issue_attempt_rows": len(rows),
        "accepted_issues": len(accepted),
        "rejected_or_stalled_attempt_rows": len(rows) - len(accepted),
        "rs1_raw_attempt_rows": sum(integer(row, "rs1_has_raw") for row in rows),
        "rs2_raw_attempt_rows": sum(integer(row, "rs2_has_raw") for row in rows),
        "rs1_forwarded_accepted": sum(
            integer(row, "rs1_forwarded") for row in accepted
        ),
        "rs2_forwarded_accepted": sum(
            integer(row, "rs2_forwarded") for row in accepted
        ),
        "raw_stall_attempt_rows": sum(
            integer(row, "raw_stall_rs1") or integer(row, "raw_stall_rs2")
            for row in rows
        ),
        "structural_stall_attempt_rows": sum(
            integer(row, "structural_stall") for row in rows
        ),
        "same_cycle_bypass_accepted": sum(
            integer(row, "same_cycle_bypass_rs1")
            or integer(row, "same_cycle_bypass_rs2")
            for row in accepted
        ),
        "flush_attempt_rows": sum(integer(row, "flush") for row in rows),
        "accepted_unavailable_operands": len(unavailable_accepted),
    }

    summary_path = args.output_directory / "dependency-summary.csv"
    with summary_path.open("w", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["metric", "value"])
        writer.writerows(metrics.items())

    source_counts = Counter()
    for row in accepted:
        source_counts[("rs1", integer(row, "rs1_source"))] += 1
        source_counts[("rs2", integer(row, "rs2_source"))] += 1

    sources_path = args.output_directory / "dependency-source-counts.csv"
    with sources_path.open("w", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["operand", "source_code", "source", "accepted_count"])
        for (operand, source), count in sorted(source_counts.items()):
            writer.writerow([operand, source, SOURCE_NAMES[source], count])

    print(f"Wrote {summary_path}")
    print(f"Wrote {sources_path}")


if __name__ == "__main__":
    main()
