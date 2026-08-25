# Milestone 8F-D: integrated monitor cost

## Fair comparison boundary

The experiment compares two fixed `cv32a65x` wrappers under one Yosys flow:

```text
baseline:  four RAW observations over the shared eight-entry scoreboard
monitored: the identical four RAW observations plus one five-bit monitor
```

Four observations represent RS1 and RS2 on each of the two `cv32a65x` issue
ports.  The monitored wrapper reuses each checker's match vector.  It does not
instantiate another set of register comparators.

This boundary intentionally measures overhead relative to the small RAW cone.
It does not claim to measure percentage area overhead of the entire CVA6 core.

## Commands

```bash
mkdir -p fi-results/milestone8fd-synthesis

yosys -Q \
  -l fi-results/milestone8fd-synthesis/baseline.log \
  verif/dependency_feedback/scripts/\
synth_dependency_feedback_cv32a65x_baseline.ys

yosys -Q \
  -l fi-results/milestone8fd-synthesis/monitored.log \
  verif/dependency_feedback/scripts/\
synth_dependency_feedback_cv32a65x_monitored.ys

yosys -Q \
  -l fi-results/milestone8fd-synthesis/raw-equivalence.log \
  verif/dependency_feedback/scripts/\
check_dependency_feedback_raw_equivalence.ys

python3 verif/dependency_feedback/analyze_synthesis_delta.py \
  --baseline fi-results/milestone8fd-synthesis/baseline_netlist.json \
  --monitored fi-results/milestone8fd-synthesis/monitored_netlist.json \
  --output fi-results/milestone8fd-synthesis/cost-delta.csv
```

## Results

`$scopeinfo` metadata cells are excluded from hardware-cell totals.

| Metric | Baseline | Monitored | Delta | Delta relative to RAW baseline |
|---|---:|---:|---:|---:|
| Wires | 859 | 1050 | +191 | +22.24% |
| Wire bits | 1278 | 1568 | +290 | +22.69% |
| Hardware cells | 823 | 1005 | +182 | +22.11% |
| Combinational cells | 823 | 1000 | +177 | +21.51% |
| State cells | 0 | 5 | +5 | not applicable |

Both synthesized designs report zero Yosys `check` problems.  The five
`$_DFF_PN0_` cells in the monitored netlist prove that all five sticky state
bits survive synthesis.

The formal paired wrapper drives both RAW cones with the same symbolic inputs.
Yosys SAT proves that all four producer indices and all four RAW-valid outputs
are identical for every possible input:

```text
SAT proof finished - no model found: SUCCESS!
```

## Structural depth and timing limitation

The generic mapped baseline has a longest topological path of 15 logic levels,
ending at a producer-index output.  The monitored wrapper has a 25-level path
ending at a feedback flip-flop input.  The added path is observational and does
not feed an architectural RAW output.

These level counts are not delay or frequency estimates.  The flow has no
target standard-cell timing library, placement, routing, or fanout extraction.
In particular, it cannot quantify whether tapping the match vectors changes a
real CVA6 critical path.  A credible timing claim requires the project's target
technology flow or the supervisors' commercial synthesis environment.

## Conclusion

The actual dual-issue integration costs 182 generic cells at this scoped
boundary: 177 combinational cells plus five state bits.  The percentage looks
large only because the reference is the small four-checker RAW cone.  A
whole-core area percentage must not be inferred from it.

The monitor is synthesizable, survives mapping, reuses existing comparison
results, and is formally observational with respect to RAW decisions.  This is
enough to report an absolute open-source cost and proceed to the controlled
MicroGP feedback experiment.  Whole-core technology area and timing remain
measurements for the commercial flow.

## Artifacts

- Paired RTL wrapper: `verif/dependency_feedback/rtl/dependency_feedback_cv32a65x_pair.sv`
- Baseline and monitored synthesis scripts: `verif/dependency_feedback/scripts/`
- Formal RAW-equivalence script: `check_dependency_feedback_raw_equivalence.ys`
- Cost-analysis script: `verif/dependency_feedback/analyze_synthesis_delta.py`
- Logs, netlists, and CSV result: `fi-results/milestone8fd-synthesis/`
