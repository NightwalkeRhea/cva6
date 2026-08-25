#!/usr/bin/env python3

"""Compute interpretable ALU activity descriptors from CVA6 trace CSVs."""

import argparse
import csv
from collections import Counter
from pathlib import Path


SHIFT_OPERATIONS = {0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C}


def read_program(trace_directory, program):
    transactions = []
    for alu_id in (0, 1):
        path = trace_directory / f"{program}.alu{alu_id}.csv"
        if not path.is_file():
            raise SystemExit(f"Missing paired trace: {path}")
        with path.open(newline="") as trace_file:
            for row in csv.DictReader(trace_file):
                transactions.append(
                    {
                        "operation": int(row["operation"], 16),
                        "operand_a": int(row["operand_a"], 16),
                        "operand_b": int(row["operand_b"], 16),
                        "result": int(row["result"], 16),
                    }
                )
    return transactions


def shift_bin(amount):
    if amount == 0:
        return "shift_0"
    if amount <= 7:
        return "shift_1_7"
    if amount <= 15:
        return "shift_8_15"
    if amount <= 23:
        return "shift_16_23"
    return "shift_24_31"


def descriptors(transactions):
    counts = Counter()
    counts["total_transactions"] = len(transactions)

    for transaction in transactions:
        operation = transaction["operation"]
        operand_a = transaction["operand_a"] & 0xFFFFFFFF
        operand_b = transaction["operand_b"] & 0xFFFFFFFF
        result = transaction["result"] & 0xFFFFFFFF

        counts[f"op_0x{operation:02x}"] += 1
        counts["operand_a_zero"] += operand_a == 0
        counts["operand_b_zero"] += operand_b == 0
        counts["operand_a_negative"] += bool(operand_a & 0x80000000)
        counts["operand_b_negative"] += bool(operand_b & 0x80000000)
        counts["operands_equal"] += operand_a == operand_b
        counts["result_zero"] += result == 0
        counts["result_negative"] += bool(result & 0x80000000)
        counts["result_all_ones"] += result == 0xFFFFFFFF

        if operation in SHIFT_OPERATIONS:
            counts["shift_total"] += 1
            counts[shift_bin(operand_b & 0x1F)] += 1

        if operation == 0x07:
            counts["sra"] += 1
            counts["sra_negative_operand"] += bool(operand_a & 0x80000000)

    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_directory", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)

    programs = sorted(
        path.name.removesuffix(".alu0.csv")
        for path in args.trace_directory.glob("*.alu0.csv")
    )
    if not programs:
        raise SystemExit(f"No paired ALU traces in {args.trace_directory}")

    rows = {program: descriptors(read_program(args.trace_directory, program))
            for program in programs}
    operation_columns = [f"op_0x{operation:02x}" for operation in range(0x17)]
    columns = [
        "total_transactions", "sra", "sra_negative_operand", "shift_total",
        "shift_0", "shift_1_7", "shift_8_15", "shift_16_23",
        "shift_24_31", "operand_a_zero", "operand_b_zero",
        "operand_a_negative", "operand_b_negative", "operands_equal",
        "result_zero", "result_negative", "result_all_ones",
    ] + operation_columns

    output_path = args.output_directory / "alu-descriptor-summary.csv"
    with output_path.open("w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=["program"] + columns)
        writer.writeheader()
        for program in programs:
            writer.writerow({"program": program, **{
                column: rows[program][column] for column in columns
            }})

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
