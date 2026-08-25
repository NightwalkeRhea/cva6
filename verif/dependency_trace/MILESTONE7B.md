# Milestone 7B: dependency-resolution trace

The simulation-only tracer is implemented inside
`core/issue_read_operands.sv`. It is enabled only when the simulator receives:

```text
+dependency_trace_file=<output.csv>
```

It is wrapped in ``ifndef SYNTHESIS`` and therefore does not become hardware.

The trace records every valid issue attempt. A stalled instruction is recorded
again on every cycle until it is accepted, allowing dependency-stall duration
to be measured. Forwarding statistics must use rows with `issue_accepted=1`.

## Source codes

| Code | Meaning |
| --- | --- |
| 0 | Register file |
| 1 | Result already stored in the scoreboard |
| 2 | Live fixed-latency-unit writeback |
| 3 | Live store writeback |
| 4 | Live load writeback |
| 5 | Shared FPU/ALU2 writeback; this is ALU2 for `cv32a65x` |
| 6 | Live CV-X-IF writeback |
| 7 | Same-cycle ALU0-to-ALU1 bypass |
| 8 | Producer exists but its value is unavailable |
| 9 | PC overrides operand A |
| 10 | CSR Z-immediate overrides operand A |
| 11 | Immediate overrides operand B |

## Fixed-seed smoke-test command

Run from `verif/sim` after loading `cva6-research-env`:

```bash
REPO=/home/nightwalkerhea/testingResearch/ricerca/cva6
GCC_OPTS="-static -mcmodel=medany -fvisibility=hidden \
-nostdlib -nostartfiles -g \
../tests/custom/common/syscalls.c \
../tests/custom/common/crt.S \
-I../tests/custom/env -I../tests/custom/common -lgcc"

python3 cva6.py \
  --target cv32a65x \
  --iss=veri-testharness \
  --iss_yaml cva6.yaml \
  --c_tests ../tests/custom/coverage/memory_branch.c \
  --linker=../../config/gen_from_riscv_config/cv32a65x/linker/link.ld \
  --gcc_opts="$GCC_OPTS" \
  --sv_seed=1 \
  --issrun_opts="+debug_disable=1 \
+dependency_trace_file=$REPO/fi-results/milestone7b-traces/memory_branch.dependency.csv" \
  -o ../../fi-results/milestone7b-runs/memory_branch
```

Analyze it from the repository root:

```bash
python3 verif/dependency_trace/analyze_dependency_trace.py \
  fi-results/milestone7b-traces/memory_branch.dependency.csv \
  fi-results/milestone7b-analysis/memory_branch
```

The analyzer rejects a trace if an accepted issue uses source code 8. This is
the first basic consistency check for the instrumentation.

## Current boundary

This first trace records issue attempts, forwarding, stalls, the local flush
input, and same-cycle bypasses. It does not yet attach a later scoreboard
cancellation to the exact earlier issue row. Per-instruction squash tracking
can be added after the basic dependency trace has been validated on controlled
programs.

## Smoke-test result

`memory_branch.c` passed with `tohost = 0` after 4074 cycles. Its trace gave:

```text
issue attempt rows:                7073
accepted issues:                   2990
rejected or stalled attempt rows:  4083
RS1 forwarding events accepted:    1062
RS2 forwarding events accepted:    696
unresolved RAW stall rows:          2080
structural stall rows:              1096
same-cycle ALU bypasses accepted:   336
flush-qualified attempt rows:       90
accepted unavailable operands:      0
```

The consumed-forwarding flags exactly matched the classified ordinary
scoreboard/writeback sources for both operands. PC and immediate overrides
were classified separately, so prepared but overridden forwarding values were
not counted as consumed forwarding.
