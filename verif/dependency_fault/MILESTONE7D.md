# Milestone 7D: internal RAW-detector fault population

## Boundary decision

`issue_read_operands.sv` combines dependency logic with register files,
functional-unit dispatch, CV-X-IF handling, and unrelated control. Mutating the
whole module would not provide a clean dependency-resolution experiment.

The first fault boundary is therefore the official `core/raw_checker.sv`.
This combinational block searches the eight live scoreboard destinations,
excludes integer register x0, handles scoreboard-pointer wraparound, and
returns the newest matching producer ID and dependency-valid flag.

This population targets RAW dependency detection. It does not yet target the
forwarding data mux, producer-readiness logic, same-cycle ALU bypass, or stall
generation embedded in `issue_read_operands.sv`.

## Wrapper and configuration

`raw_checker_cv32a65x_wrapper.sv` instantiates the official unmodified
`raw_checker` with the configuration produced from `cv32a65x_config_pkg`.
Its flat ports represent:

```text
5-bit consumer source register
consumer register-file type
eight 5-bit scoreboard destinations
eight destination register-file types
eight still-issued flags
3-bit scoreboard issue pointer
3-bit newest producer index
dependency-valid result
```

## Synthesis

From the repository root after loading `cva6-research-env`:

```bash
mkdir -p fi-results/milestone7d-synthesis

yosys -Q \
  -l fi-results/milestone7d-synthesis/synthesis.log \
  verif/dependency_fault/scripts/synth_raw_checker.ys
```

The synthesized design contains:

```text
65 input bits
4 output bits
226 combinational cells
226 total cells
0 synthesis check problems
```

Cell distribution:

```text
ANDNOT   4
AND     88
NAND    34
NOR      5
NOT      1
ORNOT   71
OR       7
XNOR    16
```

## Equivalence check

The official RTL wrapper and synthesized gate netlist were compared using:

```bash
yosys -Q \
  -l fi-results/milestone7d-synthesis/equivalence.log \
  verif/dependency_fault/scripts/check_raw_checker_equivalence.ys
```

Result:

```text
116 equivalence cells proven
0 equivalence cells unproven
Equivalence successfully proven
```

## Balanced internal fault population

The deterministic fault list was generated with:

```bash
mkdir -p fi-results/milestone7d-faults

python3 verif/dependency_fault/generate_internal_fault_list.py \
  --netlist \
    fi-results/milestone7d-synthesis/raw_checker_cv32a65x_netlist.json \
  --top raw_checker_cv32a65x_wrapper \
  --output fi-results/milestone7d-faults/fault-list.txt \
  --metadata fi-results/milestone7d-faults/fault-list-metadata.json \
  --exclude-output producer_idx_o \
  --exclude-output dependency_valid_o \
  --per-mode 30 \
  --seed 20260825
```

Population:

```text
const0: 30
const1: 30
inversion: 30
total: 90
```

For every mutation mode, Yosys reported 226 cell-output candidates. Removing
the four primary-output bits left 222 eligible internal cell outputs. Thirty
targets were sampled independently for each mode using fixed seeds 20260825,
20260826, and 20260827.

Mutations directly driving `producer_idx_o` or `dependency_valid_o` are
excluded. This avoids the direct-output bias found in the first ALU campaign.

## What this milestone establishes

The official RAW dependency detector can be synthesized as a small,
configuration-correct, formally equivalent combinational target. A balanced,
deterministic, internal-only population of 90 faults is available for the next
campaign.

The existing Milestone 7C traces are not sufficient to replay this block:
they contain the selected producer ID and dependency decision but not the full
eight-entry destination and still-issued input vectors. The next step must
capture the complete `raw_checker` input vectors during the four controlled
programs, then replay those vectors against the frozen 90-fault population.
