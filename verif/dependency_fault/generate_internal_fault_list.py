#!/usr/bin/env python3

"""Generate balanced internal cell-output mutations for a Yosys netlist."""

import argparse
import hashlib
import json
import random
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path


MODES = ("const0", "const1", "inv")


def option(tokens, name):
    position = tokens.index(name)
    return tokens[position + 1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--netlist", required=True, type=Path)
    parser.add_argument("--top", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--exclude-output", action="append", default=[])
    parser.add_argument("--per-mode", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260825)
    args = parser.parse_args()

    yosys = shutil.which("yosys")
    if not yosys:
        raise SystemExit("yosys is not in PATH; load cva6-research-env")
    design = json.loads(args.netlist.read_text())
    module = design["modules"][args.top]

    excluded_bits = set()
    for name in args.exclude_output:
        port = module["ports"].get(name)
        if not port or port["direction"] != "output":
            raise SystemExit(f"Missing output selected for exclusion: {name}")
        excluded_bits.update(port["bits"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    selected_all = []
    mode_metadata = {}

    with tempfile.TemporaryDirectory(prefix="cva6-dependency-faults-") as temp:
        temp_path = Path(temp)
        for mode_index, mode in enumerate(MODES):
            # Give each mutation mode a fixed, independent random stream.
            mode_seed = args.seed + mode_index
            pool = temp_path / f"{mode}.txt"
            command = (
                f'read_json "{args.netlist}"; hierarchy -check -top {args.top}; '
                f'mutate -list 100000 -seed {mode_seed} -mode {mode} '
                f'-port Y -o {pool}'
            )
            result = subprocess.run(
                [yosys, "-Q", "-p", command], text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            if result.returncode:
                raise SystemExit(result.stdout)

            candidates = []
            seen = set()
            raw_count = 0
            for mutation in pool.read_text().splitlines():
                if not mutation.strip():
                    continue
                raw_count += 1
                tokens = shlex.split(mutation)
                cell_name = option(tokens, "-cell")
                port_name = option(tokens, "-port")
                port_bit = int(option(tokens, "-portbit"))
                cell = module["cells"][cell_name]
                # Keep only internal cell-output bits, never direct primary outputs.
                if cell["port_directions"].get(port_name) != "output":
                    continue
                bit = cell["connections"][port_name][port_bit]
                target = (cell_name, port_name, port_bit)
                if not isinstance(bit, int) or bit in excluded_bits or target in seen:
                    continue
                seen.add(target)
                candidates.append(mutation)

            if len(candidates) < args.per_mode:
                raise SystemExit(
                    f"{mode}: only {len(candidates)} internal targets; "
                    f"requested {args.per_mode}"
                )
            candidates.sort()
            # Sorting before sampling makes selection independent of tool output order.
            chosen = random.Random(mode_seed).sample(candidates, args.per_mode)
            selected_all.extend(sorted(chosen))
            mode_metadata[mode] = {
                "candidate_seed": mode_seed,
                "raw_candidates": raw_count,
                "internal_candidates": len(candidates),
                "selected": len(chosen),
            }

    args.output.write_text("".join(f"{item}\n" for item in selected_all))
    metadata = {
        "netlist": str(args.netlist.resolve()),
        "netlist_sha256": hashlib.sha256(args.netlist.read_bytes()).hexdigest(),
        "top": args.top,
        "yosys_version": subprocess.check_output([yosys, "-V"], text=True).strip(),
        "seed": args.seed,
        "per_mode": args.per_mode,
        "total_selected": len(selected_all),
        "scope": "internal cell-output bits",
        "excluded_outputs": args.exclude_output,
        "modes": mode_metadata,
    }
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {len(selected_all)} mutations to {args.output}")
    print(f"Wrote {args.metadata}")


if __name__ == "__main__":
    main()
