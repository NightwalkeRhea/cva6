# Study guide: CVA6 dependency feedback work

This guide gives a reading order for explaining the repository, the RTL
changes, the experiments, and the evidence.  Generated files under
`fi-results/` are results, not source code.

## The one-minute hierarchy

```text
cva6.sv
  -> issue_stage.sv
       -> scoreboard.sv produces the live-entry state and issue pointer
       -> issue_read_operands.sv checks dependencies and selects operands
            -> raw_checker.sv finds the newest live producer
            -> dependency_feedback_monitor.sv stores five sticky event bits
```

The monitor is observational: it reads dependency state but does not drive an
instruction, operand, stall, forwarding selection, or architectural register.

## Read these official CVA6 files first

Read them in this order; these files explain where the research code sits.

| Order | File | What it does |
|---:|---|---|
| 1 | `core/include/cv32a65x_config_pkg.sv` | Selects the exact CVA6 configuration used by every experiment, including superscalar issue and eight scoreboard entries. |
| 2 | `core/cva6.sv` | Connects the major pipeline stages and shows where the issue stage belongs in the complete core. |
| 3 | `core/issue_stage.sv` | Connects the scoreboard to operand reading, forwarding, and functional-unit issue. |
| 4 | `core/scoreboard.sv` | Stores in-flight instructions and exports `still_issued`, `issue_pointer`, destinations, results, and writeback information. |
| 5 | `core/raw_checker.sv` | Finds every live destination matching one source register and chooses the newest producer across circular wraparound. |
| 6 | `core/issue_read_operands.sv` | Runs the RAW checkers, determines readiness and stalls, selects forwarded operands, records research traces, and instantiates the monitor. |
| 7 | `core/dependency_feedback_monitor.sv` | Converts qualified dependency observations into the selected five-bit sticky program summary. |
| 8 | `core/Flist.cva6` | Lists the SystemVerilog sources compiled by the official CVA6 Verilator flow, including the new monitor. |

In `issue_read_operands.sv`, focus on these conceptual regions instead of
trying to memorize the whole file:

```text
RAW signal declarations
simulation trace/readout declarations
three raw_checker instances per issue port
RS1/RS2 operand-use qualification
payload PC qualification
dependency_feedback_monitor instance
forwarding and stall decisions
simulation trace writers
```

## Five monitor bits to memorize

| Bit | Meaning | Why it survived selection |
|---:|---|---|
| 0 | A valid RAW dependency occurred. | Dependency-heavy tests exposed many faults missed by independent execution. |
| 1 | At least two live producers matched the same source. | Controlled multiplicity tests changed the detected fault set. |
| 2 | The selected producer came from the wrapped scoreboard side. | Wraparound treatments exposed a different internal selection context. |
| 3 | The selected producer came from the non-wrapped side. | This distinguishes the other half of circular selection. |
| 4 | Three or four scoreboard entries were live. | This was the only tested occupancy bin that added useful separation. |

Every bit is sticky: reset clears it, an event sets it, and it remains set for
the rest of the measured payload.

## Controlled assembly programs

Every payload contains 256 accepted instructions and exports
`dependency_payload_start` and `dependency_payload_end` symbols.

| File | What it does |
|---|---|
| `verif/tests/custom/dependency/independent.S` | Creates an instruction-budget control with independent register operands. |
| `verif/tests/custom/dependency/load_use.S` | Repeatedly consumes loaded values to create load-use dependency behavior. |
| `verif/tests/custom/dependency/same_cycle_bypass.S` | Creates dependencies resolved by same-cycle ALU bypass rather than the scoreboard RAW path. |
| `verif/tests/custom/dependency/scoreboard_forward.S` | Keeps producers live long enough for ordinary scoreboard forwarding. |
| `verif/tests/custom/dependency/newest_producer_control.S` | Selects the newest producer and acts as the control for producer-age testing. |
| `verif/tests/custom/dependency/older_producer.S` | Attempts to force selection of an older live producer under the same payload budget. |
| `verif/tests/custom/dependency/single_producer_control.S` | Creates one matching producer and controls the multiplicity experiment. |
| `verif/tests/custom/dependency/multiple_producers.S` | Keeps multiple same-register producers live before the consumer reads the newest one. |
| `verif/tests/custom/dependency/wrap_pair_early.S` | Exercises a matched dependency pattern before circular scoreboard wraparound. |
| `verif/tests/custom/dependency/wrap_pair_wrapped.S` | Exercises the matched pattern after producer positions cross the scoreboard boundary. |

## Trace and treatment-analysis source

| File | What it does |
|---|---|
| `verif/dependency_trace/analyze_dependency_trace.py` | Checks trace invariants and counts forwarding, bypass, RAW-stall, and source-selection events. |
| `verif/dependency_trace/compare_dependency_treatments.py` | Uses ELF payload symbols to compare equal-budget dependency programs without startup or exit code. |

The dependency trace answers, “What did the real core do?”  It is richer than
the retired-instruction trace because it includes stalled attempts, forwarding
sources, and internal producer readiness.

## Earlier ALU exploration

Read this section to explain why the project moved from combinational ALU
activity toward stateful dependency feedback.

| File | What it does |
|---|---|
| `core/alu.sv` | Implements the official CVA6 combinational ALU that supplied the first transaction traces and mutation target. |
| `verif/alu_replay/rtl/alu_cv32a65x_wrapper.sv` | Fixes the ALU interface to the selected configuration for standalone synthesis and replay. |
| `verif/alu_replay/tb/alu_replay_tb.sv` | Replays recorded operands and operations against golden or mutated ALU netlists. |
| `verif/alu_replay/scripts/synth_alu.ys` | Synthesizes the fixed ALU wrapper into Verilog and JSON netlists. |
| `verif/alu_replay/scripts/run_replay_corpus.sh` | Runs the complete stored ALU trace corpus through a selected replay executable. |
| `verif/alu_trace/analyze_alu_traces.py` | Summarizes operations, input vectors, results, branches, and per-program novelty. |
| `verif/alu_fault/run_fault_campaign.py` | Builds ALU mutants and records detection for every fault/trace pair. |
| `verif/alu_fault/analyze_fault_campaign.py` | Produces corpus, program, trace, mutation-mode, and pairwise coverage tables. |
| `verif/alu_fault/generate_stratified_fault_list.py` | Creates a balanced internal-only ALU mutation population after removing direct-output bias. |
| `verif/alu_fault/compare_fault_campaigns.py` | Compares the original mixed population with cleaner internal and stratified populations. |
| `verif/tests/custom/alu_descriptor/alu_control.S` | Provides the equal-budget control for the targeted shift experiment. |
| `verif/tests/custom/alu_descriptor/alu_sra_target.S` | Greatly increases negative arithmetic-right-shift activity under the same budget. |
| `verif/alu_trace/analyze_alu_descriptors.py` | Confirms that the treatment changed the intended SRA descriptor. |
| `verif/alu_fault/replay_existing_mutants.py` | Reuses the already-built ALU mutants for the new treatment traces. |
| `verif/alu_fault/compare_descriptor_intervention.py` | Shows that the large SRA activity change did not improve the detected fault set. |

The ALU work is not wasted: it validates the complete trace/synthesis/mutation
pipeline and supplies the negative result that generic event counts are not
automatically useful feedback.

## RAW-checker fault-campaign source

| File | What it does |
|---|---|
| `verif/dependency_fault/rtl/raw_checker_cv32a65x_wrapper.sv` | Re-expresses the official checker with fixed flat `cv32a65x` ports for stable cross-tool synthesis and replay. |
| `verif/dependency_fault/scripts/synth_raw_checker.ys` | Maps the fixed RAW checker into a generic Yosys netlist. |
| `verif/dependency_fault/scripts/check_raw_checker_equivalence.ys` | Proves the RTL wrapper and synthesized netlist produce the same outputs. |
| `verif/dependency_fault/generate_internal_fault_list.py` | Selects balanced deterministic `const0`, `const1`, and inversion mutations on internal cell outputs. |
| `verif/dependency_fault/filter_payload_vectors.py` | Keeps only RAW vectors whose PC lies inside the assembly payload symbols. |
| `verif/dependency_fault/tb/raw_checker_replay_tb.sv` | Replays golden vectors and reports whether a mutant changes RAW-valid or a meaningful producer index. |
| `verif/dependency_fault/run_raw_fault_campaign.py` | Builds every mutant, runs every frozen trace, and records detection classifications. |
| `verif/dependency_fault/analyze_raw_fault_campaign.py` | Calculates treatment coverage, pairwise fault-set differences, and combined-corpus coverage. |

Remember the validity rule: producer index is a don't-care when RAW-valid is
zero, so the replay testbench compares the index only when the golden valid bit
is one.

## Descriptor-selection source

| File | What it does |
|---|---|
| `verif/dependency_feedback/extract_raw_descriptors.py` | Converts wide RAW vectors into occupancy, age, multiplicity, wrap, and combined context bins. |
| `verif/dependency_feedback/analyze_descriptor_relevance.py` | Relates descriptor bins to the first vector that detected each mutation without claiming causality. |
| `verif/dependency_feedback/analyze_controlled_pairs.py` | Compares each descriptor intervention only with its closely matched control program. |

This offline stage prevents the hardware monitor from being designed by guess:
a descriptor reaches RTL only after controlled programs show useful variation.

## Monitor prototypes and replay source

| File | What it does |
|---|---|
| `verif/dependency_feedback/rtl/dependency_feedback_monitor.sv` | Implements the original eight-bit standalone prototype used to test candidate occupancy bits. |
| `verif/dependency_feedback/rtl/dependency_feedback_monitor_4bit.sv` | Implements the cheapest reduced candidate containing only RAW, multiplicity, and wrap-side bits. |
| `verif/dependency_feedback/rtl/dependency_feedback_monitor_5bit.sv` | Adds medium occupancy to the four-bit candidate and preserves all seven observed summary classes. |
| `verif/dependency_feedback/expected_monitor_bitmap.py` | Independently calculates the expected 8-, 5-, or 4-bit sticky summary from a RAW trace. |
| `verif/dependency_feedback/tb/dependency_feedback_monitor_tb.sv` | Replays traces against the eight-bit prototype and checks the final byte. |
| `verif/dependency_feedback/tb/dependency_feedback_reduced_tb.sv` | Drives the four- and five-bit candidates from identical observations and checks both summaries. |
| `verif/dependency_feedback/scripts/synth_dependency_feedback_monitor.ys` | Synthesizes the original eight-bit prototype for cost and gate replay. |
| `verif/dependency_feedback/scripts/synth_dependency_feedback_monitor_4bit.ys` | Synthesizes the four-bit candidate. |
| `verif/dependency_feedback/scripts/synth_dependency_feedback_monitor_5bit.ys` | Synthesizes the five-bit candidate that was eventually selected. |

The eight- and four-bit files remain evidence artifacts.  The actual core uses
the parameterized five-bit implementation in `core/`, not these prototypes.

## Integrated validation and cost source

| File | What it does |
|---|---|
| `verif/dependency_feedback/check_integrated_feedback.py` | Numerically compares the final live-core bitmap with the independent payload-scoped oracle. |
| `verif/dependency_feedback/rtl/dependency_feedback_cv32a65x_pair.sv` | Builds matched RAW-only and RAW-plus-monitor wrappers for a fair scoped cost comparison. |
| `verif/dependency_feedback/scripts/synth_dependency_feedback_cv32a65x_baseline.ys` | Synthesizes the four-observation RAW baseline. |
| `verif/dependency_feedback/scripts/synth_dependency_feedback_cv32a65x_monitored.ys` | Synthesizes the identical RAW cone plus the shared five-bit monitor. |
| `verif/dependency_feedback/scripts/check_dependency_feedback_raw_equivalence.ys` | Formally proves the paired monitor cannot change any modeled RAW output. |
| `verif/dependency_feedback/analyze_synthesis_delta.py` | Reads both Yosys JSON netlists and reports hardware-cell, state, and wiring deltas. |

## Important result artifacts

Do not read every generated file.  Start with these tables and logs:

| Artifact | What to learn from it |
|---|---|
| `fi-results/milestone7e-analysis/treatment-summary.csv` | The 12/90, 43/90, and 49/90 treatment-level fault results. |
| `fi-results/milestone8c-analysis/controlled-pair-summary.csv` | Which controlled descriptor changes added or lost fault detections. |
| `fi-results/milestone8f-analysis/windowed-integrated-vs-offline.csv` | All ten live-core summaries match the independent model. |
| `fi-results/milestone8fd-synthesis/cost-delta.csv` | The monitor adds 177 combinational cells and five state cells at the scoped RAW boundary. |
| `fi-results/milestone8fd-synthesis/raw-equivalence.log` | The formal non-interference proof ends in `SUCCESS`. |

## Explain the work in ten steps

1. I fixed the configuration at `cv32a65x` and validated the official Verilator flow.
2. Generic ALU activity did not improve the sampled ALU fault set, so I changed direction.
3. I traced real dependency resolution, including forwarding and stalls hidden from retirement traces.
4. Equal-budget programs showed that different dependency mechanisms detect different RAW-checker mutations.
5. I froze one balanced population of 90 internal mutations for fair comparisons.
6. I calculated candidate descriptors offline before adding hardware.
7. Controlled interventions supported RAW-valid, multiplicity, circular selection side, and medium occupancy.
8. An eight-bit prototype was reduced to five bits without losing observed corpus separation.
9. The five-bit monitor was integrated into CVA6 and matched the independent model on ten payloads.
10. Paired synthesis measured 177 combinational cells plus five state cells, while formal checking proved RAW outputs unchanged.

## Claims to avoid

- Do not call the open-source mutations commercial gate-level fault coverage.
- Do not call 22.11% a whole-core area increase; it is relative to the small RAW boundary.
- Do not call Yosys logic levels a timing or frequency result.
- Do not say a descriptor caused fault detection merely because they correlate.
- Do not include startup and exit activity in MicroGP feedback; it saturates the bitmap.

## Current handoff point

The local repository proves that the feedback mechanism is implementable and
measurable.  The next research question is whether MicroGP using this five-bit
payload summary finds more faults, or finds them sooner, than the same generator
without hardware feedback under identical budgets and seeds.
