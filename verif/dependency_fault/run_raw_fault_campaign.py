#!/usr/bin/env python3

"""Build RAW-checker mutants and replay controlled payload-vector traces."""

import argparse
import csv
import re
import shutil
import subprocess
from pathlib import Path


DETECTED = "*** RAW FAULT DETECTED ***"
NOT_DETECTED = "*** RAW FAULT NOT DETECTED ***"


def run(command, *, log=None):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--netlist", required=True, type=Path)
    parser.add_argument("--fault-list", required=True, type=Path)
    parser.add_argument("--traces", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verilator", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    yosys = shutil.which("yosys")
    if not yosys:
        raise SystemExit("yosys is not in PATH")
    top = "raw_checker_cv32a65x_wrapper"
    tb = Path("verif/dependency_fault/tb/raw_checker_replay_tb.sv")
    mutations = [line for line in args.fault_list.read_text().splitlines() if line.strip()]
    traces = sorted(args.traces.glob("*.raw.csv"))
    if not traces:
        raise SystemExit(f"No *.raw.csv traces in {args.traces}")

    rows = []
    for fault_id, mutation in enumerate(mutations):
        tag = f"fault_{fault_id:03d}"
        fault_dir = args.output / "mutants" / tag
        build_dir = fault_dir / "build"
        netlist_v = fault_dir / f"{tag}.v"
        executable = build_dir / tag
        fault_dir.mkdir(parents=True, exist_ok=True)
        build_dir.mkdir(parents=True, exist_ok=True)
        mode = re.search(r"-mode\s+(\S+)", mutation).group(1)

        # Materialize exactly one mutation into a standalone Verilog netlist.
        yosys_script = (
            f'read_json "{args.netlist}"; hierarchy -check -top {top}; '
            f'{mutation}; write_verilog -noattr "{netlist_v}"'
        )
        run([yosys, "-Q", "-p", yosys_script], log=fault_dir / "yosys.log")
        run([
            # Build an independent replay executable for this mutant.
            str(args.verilator), "--binary", "--timing", "-Wno-fatal",
            "--top-module", "raw_checker_replay_tb", "--Mdir", str(build_dir),
            "-o", tag, str(netlist_v), str(tb),
        ], log=fault_dir / "build.log")

        detected_count = 0
        for trace in traces:
            # Every mutant sees every frozen payload trace under the same timeout.
            name = trace.name.removesuffix(".raw.csv")
            completed = subprocess.run(
                ["timeout", f"{args.timeout}s", str(executable), "+fault_campaign",
                 f"+trace_file={trace}"], text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            log = args.output / "logs" / tag / f"{name}.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(completed.stdout)
            if completed.returncode != 0:
                classification = "INFRASTRUCTURE_ERROR"
            elif DETECTED in completed.stdout:
                classification = "DETECTED"
                detected_count += 1
            elif NOT_DETECTED in completed.stdout:
                classification = "NOT_DETECTED"
            else:
                classification = "INFRASTRUCTURE_ERROR"
            vectors = re.search(r"Vectors: (\d+)", completed.stdout)
            errors = re.search(r"Errors: (\d+)", completed.stdout)
            first = re.search(r"First error vector: (\d+)", completed.stdout)
            rows.append({
                "fault_id": f"{fault_id:03d}", "mode": mode, "trace": name,
                "classification": classification,
                "vectors": vectors.group(1) if vectors else "",
                "errors": errors.group(1) if errors else "",
                "first_error_vector": first.group(1) if first else "",
                "mutation": mutation,
            })
        print(f"{tag}: detected by {detected_count}/{len(traces)} traces", flush=True)

    result_file = args.output / "campaign-results.csv"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    with result_file.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {result_file}")


if __name__ == "__main__":
    main()
