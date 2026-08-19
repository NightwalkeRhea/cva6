#!/usr/bin/env python3

"""Summarize ALU transaction traces produced by CVA6."""

import argparse
import csv
from collections import Counter
from pathlib import Path


def read_trace(path):
    """Read one ALU CSV and convert hexadecimal fields to integers."""
    transactions = []

    with path.open(newline="") as trace_file:
        for row in csv.DictReader(trace_file):
            transactions.append(
                {
                    "cycle": int(row["cycle"]),
                    "alu_id": int(row["alu_id"]),
                    "is_branch": int(row["is_branch"]),
                    "operation": int(row["operation"], 16),
                    "operand_a": int(row["operand_a"], 16),
                    "operand_b": int(row["operand_b"], 16),
                    "result": int(row["result"], 16),
                }
            )

    return transactions


def transaction_vector(transaction):
    """Return the fields that define one ALU stimulus."""
    return (
        transaction["alu_id"],
        transaction["operation"],
        transaction["operand_a"],
        transaction["operand_b"],
    )


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

    all_transactions = {}
    all_vectors = {}

    for program in programs:
        alu0 = read_trace(args.trace_directory / f"{program}.alu0.csv")
        alu1 = read_trace(args.trace_directory / f"{program}.alu1.csv")

        transactions = alu0 + alu1
        all_transactions[program] = transactions
        all_vectors[program] = {
            transaction_vector(transaction)
            for transaction in transactions
        }

    baseline_vectors = all_vectors.get("return0", set())
    baseline_operations = {
        transaction["operation"]
        for transaction in all_transactions.get("return0", [])
    }

    summary_path = args.output_directory / "alu-program-summary.csv"

    with summary_path.open("w", newline="") as output_file:
        writer = csv.writer(output_file)

        writer.writerow(
            [
                "program",
                "alu0_transactions",
                "alu1_transactions",
                "total_transactions",
                "branch_transactions",
                "unique_operations",
                "unique_input_vectors",
                "unique_results",
                "new_operations_vs_return0",
                "new_vectors_vs_return0",
            ]
        )

        for program in programs:
            transactions = all_transactions[program]

            alu0_count = sum(
                transaction["alu_id"] == 0
                for transaction in transactions
            )
            alu1_count = sum(
                transaction["alu_id"] == 1
                for transaction in transactions
            )
            branch_count = sum(
                transaction["is_branch"] == 1
                for transaction in transactions
            )

            operations = {
                transaction["operation"]
                for transaction in transactions
            }
            results = {
                transaction["result"]
                for transaction in transactions
            }

            writer.writerow(
                [
                    program,
                    alu0_count,
                    alu1_count,
                    len(transactions),
                    branch_count,
                    len(operations),
                    len(all_vectors[program]),
                    len(results),
                    len(operations - baseline_operations),
                    len(all_vectors[program] - baseline_vectors),
                ]
            )

    operation_path = args.output_directory / "alu-operation-counts.csv"

    with operation_path.open("w", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["program", "operation", "count"])

        for program in programs:
            counts = Counter(
                transaction["operation"]
                for transaction in all_transactions[program]
            )

            for operation, count in sorted(counts.items()):
                writer.writerow(
                    [
                        program,
                        f"0x{operation:02x}",
                        count,
                    ]
                )

    print(f"Wrote {summary_path}")
    print(f"Wrote {operation_path}")


if __name__ == "__main__":
    main()
