#!/usr/bin/env python3

"""Replay new ALU traces against an already-built mutation population."""

import argparse
import csv
import re
import subprocess
from pathlib import Path


MISMATCH_RE = re.compile(r"(?:RESULT|BRANCH)_MISMATCH")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--builds", required=True, type=Path)
    parser.add_argument("--traces", required=True, type=Path)
    parser.add_argument("--baseline-results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    metadata = {}
    with args.baseline_results.open(newline="") as baseline_file:
        for row in csv.DictReader(baseline_file):
            metadata.setdefault(row["fault_id"], (row["mode"], row["mutation"]))

    traces = sorted(args.traces.glob("*.csv"))
    output_path = args.output / "fault-results.csv"
    fields = ["fault_id", "mode", "mutation", "trace", "program", "alu_id",
              "classification", "detected", "return_code"]

    with output_path.open("w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields)
        writer.writeheader()

        for fault_id in sorted(metadata):
            executable = (args.builds / f"fault_{fault_id}"
                          / f"alu_replay_fault_{fault_id}")
            mode, mutation = metadata[fault_id]
            for trace in traces:
                completed = subprocess.run(
                    [str(executable), "+fault_campaign", f"+trace_file={trace}"],
                    text=True, capture_output=True, timeout=args.timeout,
                )
                log = completed.stdout + completed.stderr
                if MISMATCH_RE.search(log) and "*** FAULT DETECTED ***" in log:
                    classification, detected = "DETECTED", 1
                elif completed.returncode == 0 and "*** FAULT NOT DETECTED ***" in log:
                    classification, detected = "NOT_DETECTED", 0
                else:
                    classification, detected = "INFRASTRUCTURE_ERROR", ""

                trace_name = trace.stem
                program, alu_name = trace_name.rsplit(".", 1)
                writer.writerow({
                    "fault_id": fault_id, "mode": mode, "mutation": mutation,
                    "trace": trace_name, "program": program,
                    "alu_id": alu_name.removeprefix("alu"),
                    "classification": classification, "detected": detected,
                    "return_code": completed.returncode,
                })
                output_file.flush()

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
