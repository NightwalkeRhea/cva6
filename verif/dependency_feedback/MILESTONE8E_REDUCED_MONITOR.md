# Milestone 8E: reduced dependency-feedback monitor

## Question

Can the eight-bit prototype be reduced without losing a descriptor distinction
that the controlled ten-program corpus already demonstrated?

The original eight-bit RTL and all `fi-results/milestone8d-*` artifacts are
preserved.  This milestone adds separately named four-bit and five-bit
candidates; it does not overwrite the prototype.

## Candidate bit maps

| Bit | Four-bit candidate | Five-bit candidate |
|---:|---|---|
| 0 | valid RAW dependency | valid RAW dependency |
| 1 | multiple matching producers | multiple matching producers |
| 2 | wrapped producer selected | wrapped producer selected |
| 3 | non-wrapped producer selected | non-wrapped producer selected |
| 4 | -- | medium scoreboard occupancy (3--4 live entries) |

Every bit is sticky until reset.  An event therefore records whether that
context occurred at least once during one program execution.

## Verification

Both candidates were driven simultaneously from the same ten captured RAW
dependency traces.  The expected summaries were calculated independently by
`expected_monitor_bitmap.py`.  All ten RTL replays and all ten synthesized
netlist replays finished with:

```text
*** REDUCED MONITOR REPLAY SUCCESS ***
```

The final summaries were:

| Program | Four bits | Five bits |
|---|---:|---:|
| independent | `0x00` | `0x00` |
| load_use | `0x09` | `0x19` |
| same_cycle_bypass | `0x00` | `0x00` |
| scoreboard_forward | `0x0f` | `0x0f` |
| newest_producer_control | `0x09` | `0x19` |
| older_producer | `0x0d` | `0x1d` |
| single_producer_control | `0x0d` | `0x1d` |
| multiple_producers | `0x0f` | `0x1f` |
| wrap_pair_early | `0x0b` | `0x0b` |
| wrap_pair_wrapped | `0x05` | `0x05` |

The four-bit candidate produced six distinct program summaries.  It collapsed
`scoreboard_forward` and `multiple_producers` to the same value.  The five-bit
candidate produced seven summaries and preserved every distinction made by the
eight-bit prototype on this corpus.  The remaining equal pairs were already
equal with eight bits, so they were not caused by this reduction.

## Synthesis cost

Yosys 0.67 mapped each standalone monitor to the same generic-cell library.
Both netlists passed `check` with zero reported problems.

| Monitor | State bits | Generic cells | Wire bits | Distinct summaries |
|---|---:|---:|---:|---:|
| Four-bit | 4 | 41 | 59 | 6 |
| Five-bit | 5 | 69 | 95 | 7 |
| Original eight-bit | 8 | 87 | 113 | 7 |

## Decision

The five-bit monitor is selected.  Compared with the eight-bit prototype it
removes three state bits and 18 generic cells while retaining the same observed
information partition.  The four-bit version is cheaper, but its saving is not
accepted because it removes an already demonstrated program distinction.

This is a corpus-scoped result, not a proof that five bits are universally
minimal.  New workloads may reveal another useful context or show that one of
the retained bits is redundant.  Integration must therefore keep the monitor
small and replaceable, and must define how its five-bit summary is reset and
read by the future MicroGP feedback loop.

## Reproducibility artifacts

- Four- and five-bit RTL: `verif/dependency_feedback/rtl/`
- Common replay testbench: `verif/dependency_feedback/tb/dependency_feedback_reduced_tb.sv`
- Synthesis scripts: `verif/dependency_feedback/scripts/`
- RTL and netlist replay logs: `fi-results/milestone8e-replay/`
- Netlists and synthesis logs: `fi-results/milestone8e-synthesis/`
- Original eight-bit results: `fi-results/milestone8d-replay/` and
  `fi-results/milestone8d-synthesis/`
