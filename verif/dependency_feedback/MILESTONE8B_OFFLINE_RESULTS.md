# Milestone 8B: offline descriptor calculation

## Why this was done offline

The monitor should not be designed by guessing which internal activity looks
interesting. The candidate descriptors were first calculated from the frozen
Milestone 7E payload vectors. Only descriptors that distinguish fault-relevant
contexts should later become RTL state.

## Validity correction found by the analysis

Joining first fault detections to descriptor rows exposed three detections on
vectors where RAW-valid was zero. Inspection found that the replay testbench
always compared `producer_idx_o`, even though that index is a don't-care when
no dependency exists.

The testbench now:

```text
always compares dependency_valid_o
compares producer_idx_o only when golden dependency-valid is one
```

The same frozen 90 faults and four payload traces were rerun. All 360 runs
were classified with zero infrastructure errors.

Corrected fault coverage:

```text
independent             12 / 90   13.33%
same_cycle_bypass       12 / 90   13.33%
load_use                43 / 90   47.78%
scoreboard_forward      49 / 90   54.44%
combined corpus         69 / 90   76.67%
```

Independent and same-cycle bypass still detect identical sets. Load-use adds
32 faults over independent, and scoreboard forwarding adds 37. The validity
correction therefore removes false detections while strengthening the relative
separation produced by live scoreboard dependencies.

## Descriptor observations

### RAW-valid

Keep this candidate. All 32 incremental load-use faults are first exposed on
valid RAW vectors. Of the 37 incremental scoreboard-forwarding faults, 34 are
first exposed on valid RAW vectors. The remaining three are genuine valid-bit
errors: a mutant incorrectly asserts RAW-valid on a golden no-RAW vector.

### Scoreboard occupancy

Keep this candidate provisionally. Load-use reaches the `medium_3_4` bin,
which no other treatment reaches. Fourteen incremental load-use faults are
first exposed in this bin. Occupancy alone is insufficient, because both
load-use and scoreboard-forwarding also expose new faults at low occupancy.

### Producer age

Reject this binning for the current monitor candidate. Every valid RAW in the
four controlled payloads selects the newest producer. The descriptor therefore
adds no information beyond RAW-valid in this experiment. It may be revisited
after adding deliberately older-producer programs.

### Matching-producer multiplicity

Keep this candidate provisionally. Scoreboard forwarding reaches one
multiple-producer vector. Despite being rare, it is the first exposing context
for ten incremental faults after validity gating. This requires confirmation
with a dedicated overwrite-chain treatment before hardware implementation.

### Scoreboard wrap selection

Keep this candidate provisionally. Scoreboard forwarding produces 32 wrapped
RAW vectors, and wrapped contexts first expose 13 incremental faults. Load-use
does not reach this bin.

### Combined context bin

Keep this only as an offline reference until redundant fields are removed.
Seven combined bins are populated. Independent and same-cycle bypass visit the
same two bins and detect the same faults. Load-use and scoreboard forwarding
each introduce distinct bins and distinct fault sets.

## Current shortlist

```text
retain:       RAW-valid
provisional:  occupancy, matching multiplicity, wrap selection
defer:        producer age until an older-producer treatment exists
reference:    combined context bin
```

This is not yet the final monitor. Milestone 8C should add small controlled
treatments that vary one provisional descriptor at a time, especially
multiple-producer chains, wraparound selection, and older producer age. That
intervention is needed to distinguish a useful descriptor from a feature that
merely happens to correlate with one existing program.
