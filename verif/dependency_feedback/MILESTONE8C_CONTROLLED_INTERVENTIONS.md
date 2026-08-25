# Milestone 8C: controlled descriptor interventions

## Goal

Milestone 8B found correlations between compact internal descriptors and RAW
checker fault coverage. Milestone 8C changes one intended descriptor at a time
using matched assembly programs. Every program is self-checking, uses seed 1,
and contains exactly 256 uncompressed payload instructions.

## Matched pairs

### Producer age

`newest_producer_control.S` immediately consumes a long-latency divider
result, then executes two independent ALU instructions. `older_producer.S`
executes the same instructions but moves the independent work before the
consumer.

```text
control:    639 newest, 1 next-age RAW evaluations
treatment:   62 next-age, 570 middle-age RAW evaluations
```

This intervention also changes occupancy and issue timing. It is therefore an
age-plus-live-context experiment, not a clean age-only experiment.

### Matching-producer multiplicity

Both programs execute a divider, load, consumer, and neutral padding
instruction in the same order. In `single_producer_control.S`, the divider
writes `t2`. In `multiple_producers.S`, it writes `t0`, the same destination
as the newer load.

```text
control:    135 single-match RAW evaluations
treatment:  134 multiple-match, 3 single-match RAW evaluations
```

Both sides contain 2,766 replay rows, 49 unique checker input vectors, and the
same occupancy distribution. This is the cleanest descriptor intervention.

### Circular scoreboard wrap

`wrap_pair_early.S` and `wrap_pair_wrapped.S` contain exactly the same
256-instruction payload: one ALU producer, one store consumer, and six neutral
instructions in each eight-instruction group. The wrapped treatment executes
four neutral instructions before the marked payload to shift the circular
allocation position without changing the measured instruction budget.

```text
control:    33 non-wrapped, 0 wrapped RAW evaluations
treatment:   0 non-wrapped, 32 wrapped RAW evaluations
```

Both sides contain 576 replay rows and the same occupancy distribution. They
contain 18 and 16 unique checker inputs respectively.

## Full-core validation

All six programs passed on the official CVA6 Verilator harness:

```text
newest_producer_control   SUCCESS
older_producer            SUCCESS
single_producer_control   SUCCESS
multiple_producers        SUCCESS
wrap_pair_early           SUCCESS
wrap_pair_wrapped         SUCCESS
```

The trace extractor independently reconstructed every RAW-valid result without
an error. Pilot programs that failed to create their intended internal state
were not included in the final campaign.

## Frozen fault campaign

The corrected validity-gated replay testbench, same 90 internal mutations, and
same simulator versions were used:

```text
90 faults x 6 treatments = 540 executions
infrastructure errors = 0
```

Individual coverage:

```text
newest producer control   34 / 90   37.78%
older producer            30 / 90   33.33%
single producer control   42 / 90   46.67%
multiple producers        54 / 90   60.00%
non-wrapped control       36 / 90   40.00%
wrapped treatment         28 / 90   31.11%
six-treatment corpus      74 / 90   82.22%
```

Matched-pair fault-set changes:

| Intervention | Control | Treatment | Added | Lost | Shared | Pair union |
|---|---:|---:|---:|---:|---:|---:|
| Producer age/context | 34 | 30 | 6 | 10 | 24 | 40 |
| Producer multiplicity | 42 | 54 | 13 | 1 | 41 | 55 |
| Scoreboard wrap | 36 | 28 | 13 | 21 | 15 | 49 |

The six new treatments detect seven faults not detected by the corrected
Milestone 7E corpus. Combining both corpora detects 76 of the 90 frozen faults.

## Interpretation

### Multiplicity survives descriptor selection

Changing only the divider destination converts single-producer contexts into
multiple-producer contexts while preserving instruction count, instruction
order, occupancy distribution, total replay rows, and unique input count. The
treatment adds 13 faults and loses only one. Matching-producer multiplicity is
therefore the strongest compact monitor candidate from this study.

### Wrap is useful for diversity, not monotonic coverage

The wrapped treatment detects fewer total faults, so a higher wrap count is
not inherently better. However, it detects 13 faults missed by the matched
non-wrapped control. The two circular regions exercise complementary logic.
A visited-wrap-context bit is therefore more defensible than maximizing a wrap
counter.

### Producer age remains unresolved

Older producer contexts change the detected fault set, adding six and losing
ten faults, but the reordering also changes occupancy and timing. Producer age
cannot yet be credited as the cause. It should not enter the first hardware
monitor unless a cleaner intervention is found.

## Updated shortlist

```text
retain strongly:
    RAW-valid
    matching-producer multiplicity

retain as diversity coverage:
    wrapped RAW context visited
    non-wrapped RAW context visited

retain provisionally:
    scoreboard occupancy

defer:
    producer age
```

The next step is to define the smallest hardware summary containing only the
surviving descriptors, then synthesize it separately and measure its area
before integrating it into the full core.
