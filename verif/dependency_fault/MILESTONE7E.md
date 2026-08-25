# Milestone 7E: controlled RAW-checker fault campaign

## Question

Do microarchitectural scoreboard contexts distinguish tests that have similar
software-visible dependency descriptions, and do those contexts detect faults
inside the RAW dependency detector that an independent stream misses?

## Full-core capture

The four Milestone 7C programs were rerun on `cv32a65x` with simulator seed 1.
All passed. A simulation-only tracer in `issue_read_operands.sv` records the
exact inputs and outputs of both RAW-checker evaluations for every valid issue
attempt:

```text
cycle, issue port, operand, PC, source register and type,
eight destination registers and types, still-issued mask, issue pointer,
expected producer index, expected dependency-valid, operand-used
```

The complete traces contain 13,400 vectors and no X/Z fields. Only PCs inside
the marked 256-instruction payloads are used for fault coverage:

```text
independent           512 vectors
same_cycle_bypass     512 vectors
scoreboard_forward    768 vectors
load_use              928 vectors
```

## Golden replay and cross-tool check

The official live-core outputs and the flat replay RTL agree on every vector.
The synthesized JSON is formally equivalent and Yosys evaluates disputed
vectors correctly. Pinned Verilator 5.008 mis-evaluated the emitted deep
combinational Verilog, whereas OSS CAD Suite Verilator 5.051 replayed all four
complete traces with zero errors. Full-core CVA6 simulation remains pinned to
5.008; isolated synthesized-netlist replay uses 5.051 and records that version.

This validation also exposed packed-array ordering ambiguity in the first 7D
wrapper. The corrected synthesis boundary implements the same fixed
cv32a65x RAW-checker equations directly on a flat 40-bit destination vector.
The netlist, equivalence proof, and deterministic fault list were regenerated
before the campaign.

## Campaign

The corrected population contains 90 internal cell-output mutations:

```text
30 const0
30 const1
30 inversion
```

Direct mutations of `producer_idx_o` and `dependency_valid_o` remain excluded.
Each mutation was replayed against all four payload traces: 360 classified
trace--fault pairs, with zero infrastructure errors.

Milestone 8A later found that the first replay checker compared the producer
index even when dependency-valid was zero. That index is a don't-care unless a
RAW dependency exists. The campaign was therefore rerun with producer-index
comparison gated by the golden valid flag. The corrected results below replace
the original exploratory counts; the original CSV remains archived so the
methodological correction is auditable.

## Results

```text
treatment           detected / 90    coverage    exclusive in corpus
independent              12           13.33%       0
same_cycle_bypass        12           13.33%       0
load_use                 43           47.78%      20
scoreboard_forward       49           54.44%      25
combined corpus          69           76.67%       -
```

Independent and same-cycle-bypass detect exactly the same 12 faults. This is
expected for this boundary: same-cycle ALU bypass is resolved outside
`raw_checker`. Scoreboard forwarding adds 37 faults over independent. Load-use
adds 32, while losing one baseline fault. Load-use and scoreboard-forwarding
also detect different sets: 20 faults only in load-use, 26 only in
scoreboard-forwarding, and 23 in both.

## Meaning

The result is not merely that longer traces detect more faults. The 928-vector
load-use trace detects fewer faults than the 768-vector scoreboard-forwarding
trace, and the two equal-size 512-vector treatments are identical at this
fault boundary. Fault coverage follows internal scoreboard state and producer
context, not transaction count alone.

This supports using compact internal descriptors such as producer class,
scoreboard occupancy/age, valid RAW resolution, and unresolved-wait context as
feedback candidates. It does not yet prove that a hardware monitor improves
MicroGP; that requires an intervention comparing software-only feedback with
the compact descriptor under equal generation and time budgets.
