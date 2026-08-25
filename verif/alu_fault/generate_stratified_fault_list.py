#!/usr/bin/env python3

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


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a balanced Yosys mutation list targeting internal "
            "cell-output bits only."
        )
    )
    parser.add_argument("--netlist", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--top", default="alu_cv32a65x_wrapper")
    parser.add_argument("--per-mode", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260825)
    parser.add_argument("--yosys", default=shutil.which("yosys"))
    return parser.parse_args()


def option_value(tokens, option):
    try:
        position = tokens.index(option)
    except ValueError as error:
        raise ValueError(f"Mutation lacks {option}: {' '.join(tokens)}") from error

    try:
        return tokens[position + 1]
    except IndexError as error:
        raise ValueError(f"Mutation has no value after {option}") from error


def target_bit(module, mutation):
    tokens = shlex.split(mutation)
    cell_name = option_value(tokens, "-cell")
    port_name = option_value(tokens, "-port")
    port_bit = int(option_value(tokens, "-portbit"))

    try:
        cell = module["cells"][cell_name]
    except KeyError as error:
        raise ValueError(f"Unknown mutation cell: {cell_name}") from error

    if cell["port_directions"].get(port_name) != "output":
        raise ValueError(
            f"Mutation target {cell_name}.{port_name} is not a cell output"
        )

    try:
        bit = cell["connections"][port_name][port_bit]
    except (KeyError, IndexError) as error:
        raise ValueError(
            f"Invalid target bit: {cell_name}.{port_name}[{port_bit}]"
        ) from error

    return cell_name, port_name, port_bit, bit


def run_yosys_candidate_query(
    yosys,
    netlist,
    top,
    mode,
    seed,
    output,
):
    command = (
        f'read_json "{netlist}"; '
        f'hierarchy -check -top {top}; '
        f'mutate -list 100000 -seed {seed} '
        f'-mode {mode} -port Y -o {output}'
    )

    result = subprocess.run(
        [yosys, "-Q", "-p", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Yosys candidate query failed for {mode}:\n{result.stdout}"
        )

    if not output.is_file():
        raise RuntimeError(f"Yosys did not create candidate list: {output}")


def main():
    args = parse_arguments()

    if not args.yosys:
        raise SystemExit("yosys was not found in PATH; activate cva6-research-env")

    if args.per_mode <= 0:
        raise SystemExit("--per-mode must be positive")

    netlist = args.netlist.resolve()
    output = args.output.resolve()
    metadata_path = args.metadata.resolve()

    design = json.loads(netlist.read_text())

    try:
        module = design["modules"][args.top]
    except KeyError as error:
        raise SystemExit(f"Top module not found in JSON: {args.top}") from error

    excluded_port_names = ("result_o", "branch_result_o")
    excluded_bits = set()

    for port_name in excluded_port_names:
        try:
            port = module["ports"][port_name]
        except KeyError as error:
            raise SystemExit(f"Expected output port is absent: {port_name}") from error

        if port["direction"] != "output":
            raise SystemExit(f"Expected an output port: {port_name}")

        excluded_bits.update(port["bits"])

    output.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    selected_mutations = []
    mode_metadata = {}

    with tempfile.TemporaryDirectory(prefix="cva6-stratified-faults-") as temp:
        temp_directory = Path(temp)

        for mode_index, mode in enumerate(MODES):
            pool_path = temp_directory / f"{mode}.txt"
            mode_seed = args.seed + mode_index

            run_yosys_candidate_query(
                args.yosys,
                netlist,
                args.top,
                mode,
                mode_seed,
                pool_path,
            )

            raw_candidates = [
                line.strip()
                for line in pool_path.read_text().splitlines()
                if line.strip()
            ]

            internal_candidates = []
            seen_targets = set()

            for mutation in raw_candidates:
                cell_name, port_name, port_bit, bit = target_bit(module, mutation)

                if bit in excluded_bits:
                    continue

                if not isinstance(bit, int):
                    continue

                target = (cell_name, port_name, port_bit)

                if target in seen_targets:
                    continue

                seen_targets.add(target)
                internal_candidates.append(mutation)

            if len(internal_candidates) < args.per_mode:
                raise SystemExit(
                    f"Only {len(internal_candidates)} internal candidates "
                    f"exist for {mode}; requested {args.per_mode}"
                )

            internal_candidates.sort()
            generator = random.Random(mode_seed)
            selected = generator.sample(internal_candidates, args.per_mode)
            selected.sort()
            selected_mutations.extend(selected)

            mode_metadata[mode] = {
                "candidate_seed": mode_seed,
                "raw_cell_output_candidates": len(raw_candidates),
                "internal_cell_output_candidates": len(internal_candidates),
                "selected": len(selected),
            }

    output.write_text("".join(f"{line}\n" for line in selected_mutations))

    yosys_version = subprocess.check_output(
        [args.yosys, "-V"],
        text=True,
    ).strip()

    metadata = {
        "generator": str(Path(__file__).resolve()),
        "netlist": str(netlist),
        "netlist_sha256": hashlib.sha256(netlist.read_bytes()).hexdigest(),
        "top": args.top,
        "yosys_version": yosys_version,
        "seed": args.seed,
        "per_mode": args.per_mode,
        "total_selected": len(selected_mutations),
        "selection_scope": "internal cell-output bits",
        "excluded_primary_outputs": list(excluded_port_names),
        "modes": mode_metadata,
    }

    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    print(f"Wrote {len(selected_mutations)} mutations to {output}")
    print(f"Wrote selection metadata to {metadata_path}")


if __name__ == "__main__":
    main()
