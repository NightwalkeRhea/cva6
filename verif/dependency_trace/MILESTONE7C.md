# Milestone 7C: controlled dependency treatments

Configuration: `cv32a65x`, Verilator seed 1.

Four self-checking assembly programs contain exactly 256 marked payload
instructions. Global `dependency_payload_start` and `dependency_payload_end`
symbols let the analyzer exclude common startup, exit, and self-check code.

## Treatments

| Program | Intended internal behavior |
| --- | --- |
| `independent.S` | Independent register operands; negative control |
| `same_cycle_bypass.S` | Adjacent ALU producer and ALU consumer |
| `scoreboard_forward.S` | ALU producer followed by a store consumer that cannot use ALU bypass |
| `load_use.S` | Load immediately followed by its ALU consumer |

Each payload contains 64 repetitions of four instructions. The instruction
mix is intentionally appropriate to each mechanism, so equal payload size does
not mean identical opcodes.

## Analysis command

After loading `cva6-research-env`, run from the repository root:

```bash
python3 verif/dependency_trace/compare_dependency_treatments.py \
  fi-results/milestone7c-refined-traces \
  fi-results/milestone7c-refined-runs \
  fi-results/milestone7c-refined-analysis
```

The analyzer reads the payload symbols from each ELF, requires exactly 256
accepted payload instructions, and rejects any accepted unavailable operand.

## Full-core results

All four programs passed:

```text
independent:          SUCCESS after 1452 cycles
same_cycle_bypass:    SUCCESS after 1446 cycles
scoreboard_forward:   SUCCESS after 1528 cycles
load_use:             SUCCESS after 1417 cycles
```

Payload-only descriptor results:

| Program | Attempts | Accepted | Ordinary forwarded operands | Same-cycle bypasses | RAW stall rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| independent | 256 | 256 | 0 | 0 | 0 |
| same_cycle_bypass | 256 | 256 | 0 | 128 | 0 |
| scoreboard_forward | 384 | 256 | 128 | 0 | 0 |
| load_use | 464 | 256 | 128 | 0 | 135 |

The 128 ordinary forwarding events in `scoreboard_forward` came from the
shared ALU2/FPU writeback port, used as ALU2 in this configuration. The 128
ordinary forwarding events in `load_use` came from `LOAD_WB`.

Issue-attempt rows can exceed accepted instructions because a waiting
instruction is recorded on each cycle. In a dual-issue core, port-one
suppression caused by port zero also contributes rejected attempts and must
not automatically be interpreted as a RAW or structural stall.

## What this proves

The hardware-derived descriptors selectively distinguish four dependency
resolution mechanisms under the same accepted payload-instruction budget:

- no dependency activity;
- direct same-cycle ALU bypass;
- live non-bypass writeback forwarding;
- unresolved load-use waiting followed by load-result forwarding.

This validates the trace as a measurement instrument and shows that it reports
more than static RAW presence. It does not yet prove that these descriptors
improve fault coverage or MicroGP guidance. That requires a fault population
inside the dependency-resolution, forwarding-mux, and hazard-control logic.
