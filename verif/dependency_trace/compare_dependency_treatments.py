#!/usr/bin/env python3

"""Compare dependency descriptors inside marked assembly payload regions."""

import argparse
import csv
import os
import shutil
import subprocess
from collections import Counter
from pathlib import Path


SOURCE_NAMES = {
    0: "REGFILE", 1: "SCOREBOARD", 2: "FLU_WB", 3: "STORE_WB",
    4: "LOAD_WB", 5: "FPU_OR_ALU2_WB", 6: "X_WB",
    7: "SAME_CYCLE_ALU", 8: "UNAVAILABLE", 9: "PC", 10: "ZIMM",
    11: "IMMEDIATE",
}


def find_nm():
    candidate = shutil.which("riscv-none-elf-nm")
    if candidate:
        return candidate
    riscv_cc = os.environ.get("RISCV_CC")
    if riscv_cc:
        sibling = Path(riscv_cc).with_name("riscv-none-elf-nm")
        if sibling.is_file():
            return str(sibling)
    raise SystemExit("Cannot find riscv-none-elf-nm; load cva6-research-env")


def symbol_addresses(nm, elf):
    symbols = {}
    output = subprocess.check_output([nm, str(elf)], text=True)
    for line in output.splitlines():
        fields = line.split()
        if len(fields) == 3:
            address, _, name = fields
            if name in {"dependency_payload_start", "dependency_payload_end"}:
                symbols[name] = int(address, 16)
    if len(symbols) != 2:
        raise SystemExit(f"Payload boundary symbols are missing from {elf}")
    return symbols["dependency_payload_start"], symbols["dependency_payload_end"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_directory", type=Path)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    nm = find_nm()

    programs = sorted(
        path.name.removesuffix(".dependency.csv")
        for path in args.trace_directory.glob("*.dependency.csv")
    )
    summary_rows = []
    source_rows = []

    for program in programs:
        trace = args.trace_directory / f"{program}.dependency.csv"
        elf = args.run_directory / program / "directed_tests" / f"{program}.o"
        start, end = symbol_addresses(nm, elf)
        with trace.open(newline="") as trace_file:
            all_rows = list(csv.DictReader(trace_file))
        rows = [row for row in all_rows if start <= int(row["pc"], 16) < end]
        accepted = [row for row in rows if row["issue_accepted"] == "1"]
        if len(accepted) != 256:
            raise SystemExit(
                f"{program}: expected 256 accepted payload instructions, "
                f"found {len(accepted)}"
            )
        if any(row["rs1_source"] == "8" or row["rs2_source"] == "8"
               for row in accepted):
            raise SystemExit(f"{program}: accepted an unavailable payload operand")

        sources = Counter()
        for row in accepted:
            sources[("rs1", int(row["rs1_source"]))] += 1
            sources[("rs2", int(row["rs2_source"]))] += 1
        for (operand, source), count in sorted(sources.items()):
            source_rows.append([program, operand, source, SOURCE_NAMES[source], count])

        summary_rows.append([
            program, f"0x{start:08x}", f"0x{end:08x}", len(rows), len(accepted),
            sum(int(row["rs1_forwarded"]) + int(row["rs2_forwarded"])
                for row in accepted),
            sum(int(row["same_cycle_bypass_rs1"]) or
                int(row["same_cycle_bypass_rs2"]) for row in accepted),
            sum(int(row["raw_stall_rs1"]) or int(row["raw_stall_rs2"])
                for row in rows),
            sum(int(row["structural_stall"]) for row in rows),
            sum(int(row["rs1_has_raw"]) + int(row["rs2_has_raw"])
                for row in rows),
        ])

    summary_path = args.output_directory / "dependency-treatment-summary.csv"
    with summary_path.open("w", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow([
            "program", "payload_start", "payload_end", "issue_attempt_rows",
            "accepted_payload_instructions", "ordinary_forwarded_operands",
            "same_cycle_bypass_instructions", "raw_stall_rows",
            "structural_stall_rows", "raw_operand_attempts",
        ])
        writer.writerows(summary_rows)

    sources_path = args.output_directory / "dependency-treatment-sources.csv"
    with sources_path.open("w", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["program", "operand", "source_code", "source", "count"])
        writer.writerows(source_rows)

    print(f"Wrote {summary_path}")
    print(f"Wrote {sources_path}")


if __name__ == "__main__":
    main()
