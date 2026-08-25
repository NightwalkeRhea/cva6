# Milestone 8A: candidate compact descriptors

## Goal

Replace a wide RAW-checker trace with a few small feedback values that a
future hardware monitor could maintain using counters and coverage bits.

Milestone 8A defines candidates. It does not claim that they are useful yet.
Milestone 8B computes them from existing traces, and Milestone 8C tests which
ones explain genuinely different fault detections.

## Candidates available in the current RAW-checker trace

| Descriptor | Definition | Compact hardware form | Why it may matter |
|---|---|---|---|
| Scoreboard occupancy | Population count of `still_issued` | Four bins: 0, 1--2, 3--4, 5--8 | Distinguishes empty, lightly occupied, and congested dependency state. |
| RAW-valid | Official checker `valid` result | One counter or one visited bit | Separates ordinary reads from reads that match a live producer. |
| Producer age | `(issue_pointer - 1 - producer_idx) mod 8` | Four bins: newest, next, middle, old | Describes how far the selected producer is behind the insertion pointer. |
| Matching producers | Number of live entries with the same register and register-file type | Three bins: 0, 1, 2+ | Exposes overwrite chains hidden by the single selected producer ID. |
| Wrap selection | Valid producer index at or above the issue pointer | One counter or visited bit | Exercises the wraparound half of the newest-producer selection logic. |
| Context bin | Tuple of the five values above | Small visited-bin bitmap or hash | Preserves useful interactions without exporting the full scoreboard. |

Integer register `x0` never forms a valid RAW dependency, matching the
official checker. Producer age, match count, and wrap selection are therefore
reported as `none` when RAW-valid is false.

## What is deliberately excluded for now

- A repeated RAW match is not called a stall. Producer readiness and issue
  acceptance are required to prove a dependency-induced stall.
- Producer functional-unit class is not present in the RAW-checker vector.
  It must be joined from the richer Milestone 7B dependency trace.
- Exact registers, complete destination vectors, PCs, and cycle numbers are
  diagnostic data, not compact feedback candidates.
- Trace length is a budget variable, not a descriptor of interesting state.

## Selection rule

A descriptor should reach hardware only if the offline study shows that it:

1. distinguishes treatments that detect different fault sets;
2. identifies contexts associated with first fault detections;
3. adds information beyond simpler descriptors; and
4. can be implemented with small counters or a compact visited-bin bitmap.

Descriptors that fail these checks remain useful diagnostics but are not
implemented in the monitor.
