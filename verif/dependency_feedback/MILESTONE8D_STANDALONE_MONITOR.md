# Milestone 8D: standalone compact feedback monitor

## Boundary

The first monitor was implemented and synthesized as a standalone block. It
was not connected to CVA6 yet. This protects the validated full-core flow and
lets behavior, information value, and cost be reviewed independently.

The monitor consumes signals already present in dependency resolution:

```text
qualified sample
RAW-valid decision
eight RAW match bits
selected producer index
scoreboard issue pointer
eight still-issued bits
```

It exports one sticky eight-bit program summary. Reset clears every bit. A
qualifying event sets its bit, and the bit remains set until reset.

## Prototype bit assignment

| Bit | Sticky event |
|---:|---|
| 0 | Any valid RAW dependency |
| 1 | Valid RAW with two or more matching producers |
| 2 | Wrapped RAW producer selection |
| 3 | Non-wrapped RAW producer selection |
| 4 | Empty scoreboard observed |
| 5 | Low occupancy (1--2 live entries) observed |
| 6 | Medium occupancy (3--4 live entries) observed |
| 7 | High occupancy (5--8 live entries) observed |

The monitor reuses the checker's internal match vector. It does not duplicate
the register comparators that generate that vector and does not export the
complete scoreboard.

## Independent replay oracle

`expected_monitor_bitmap.py` calculates the expected byte directly from each
CSV trace. The SystemVerilog testbench independently reconstructs the internal
match vector, clocks each used operand into the monitor, and compares the final
sticky byte with the Python result.

RTL results:

```text
independent               0x30  PASS
same_cycle_bypass         0x30  PASS
load_use                  0x79  PASS
scoreboard_forward        0x3f  PASS
newest_producer_control   0x79  PASS
older_producer            0x7d  PASS
single_producer_control   0x7d  PASS
multiple_producers        0x7f  PASS
wrap_pair_early           0x3b  PASS
wrap_pair_wrapped         0x35  PASS
```

The bytes distinguish the controlled multiplicity and wrap interventions. The
newest and older producer programs are not separated by this prototype because
producer age was deliberately deferred.

## Synthesis

The standalone monitor was synthesized with Yosys 0.67 from the commented RTL:

```text
8 flip-flops
79 combinational generic cells
87 total generic cells
113 wire bits
0 check problems
```

The synthesized netlist was replayed against the same ten traces. Every final
byte matched both the RTL and independent Python oracle.

## Redundancy found before integration

Across the ten evidence-selected programs:

```text
empty-occupancy bit: set by all ten programs
low-occupancy bit:   set by all ten programs
medium bit:          distinguishes dependency-heavy contexts
high bit:            set by none of the ten programs
```

Empty and low occupancy currently provide no novelty information and should
not be integrated merely because they are easy to count. High occupancy has
not been justified by evidence yet.

The four strongest immediately supported bits are:

```text
RAW-valid visited
multiple-producer RAW visited
wrapped RAW visited
non-wrapped RAW visited
```

Medium occupancy remains provisional. High occupancy requires a targeted
program before retention. The next revision should therefore contain four or
five bits, rather than automatically integrating all eight prototype bits.

## Decision

The standalone design validates that the evidence-selected feedback can be
represented by a tiny sticky bitmap and reproduced at gate level. The
eight-bit prototype should not yet be integrated unchanged. First remove the
constant occupancy bits, decide whether medium/high occupancy survives, and
then synthesize the reduced monitor for the actual integration candidate.
