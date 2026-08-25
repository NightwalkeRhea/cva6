# Milestone 8F-A/B/C: CVA6 integration and harness readout

## 8F-A: exact signal and qualification boundary

The selected five-bit monitor is located beside the official `raw_checker`
instances in `issue_read_operands.sv`.  It uses:

| Monitor input | CVA6 source | Qualification |
|---|---|---|
| RAW valid | `rs1_has_raw` / `rs2_has_raw` | Real source operand only |
| Match vector | New `raw_checker.matches_o` | x0 suppressed by the checker |
| Producer index | `idx_hzd_rs1` / `idx_hzd_rs2` | Meaningful only with RAW valid |
| Issue pointer | `fwd_i.issue_pointer` | Current circular insertion point |
| Live entries | `fwd_i.still_issued` | Issued and not cancelled |
| Sample valid | Issue valid and payload PC | Also rejects flushes and exceptions |

The monitor still observes a stalled valid consumer because an unresolved RAW
dependency is relevant internal activity.  It does not observe a flushed or
exception-bearing consumer.  RS1 is disabled when replaced by a Z-immediate.
RS2 is disabled when the final operand mux replaces it with an ordinary
immediate.

This last rule corrects an old trace limitation: the earlier RAW replay CSV
marked every RS2 checker invocation as used.  Across the ten new full-core
traces, 9433 unused RS2 rows are now explicitly marked and excluded.

## 8F-B: synthesizable integration

`core/dependency_feedback_monitor.sv` is parameterized by scoreboard size,
transaction-ID width, and observation count.  `cv32a65x` supplies two source
observations per issue port.  Simultaneous observations are ORed before one
five-bit sticky register is updated, so the integration does not instantiate a
separate five-bit state vector for every operand.

`raw_checker.sv` now exports its already-computed match vector.  This avoids
duplicating the register comparators merely for research feedback.  The module
was added to `core/Flist.cva6` and the complete official Verilator harness
build succeeds with the pinned Verilator 5.008.

The monitor does not change instruction data, forwarding decisions, stalls, or
architectural state.  The `independent` retired-instruction log is byte-for-byte
identical before and after integration (1556 lines in each file).

## 8F-C: compact Verilator readout

The harness accepts:

```text
+dependency_feedback_file=<output.csv>
+dependency_feedback_pc_start=<hex start address>
+dependency_feedback_pc_end=<hex exclusive end address>
```

The start and end addresses are obtained from the ELF symbols
`dependency_payload_start` and `dependency_payload_end`.  The output contains
the initial zero and only later bitmap changes.  Because the bits are sticky,
the final CSV row is the final payload summary and at most five nonzero updates
can occur.

An initial whole-program experiment was intentionally retained as a warning.
All ten programs saturated to `0x1f` because common startup, trap, and exit code
dominated the small bitmap.  Payload scoping is therefore part of the feedback
definition, not an optional presentation filter.

## Integrated validation

Every program passed on `cv32a65x` with seed 1.  The integrated result was
compared against `expected_monitor_bitmap.py`, calculated independently from
the corrected RAW trace inside the same half-open PC window.

| Program | Integrated | Offline | Result |
|---|---:|---:|---|
| independent | `0x00` | `0x00` | MATCH |
| load_use | `0x19` | `0x19` | MATCH |
| same_cycle_bypass | `0x00` | `0x00` | MATCH |
| scoreboard_forward | `0x09` | `0x09` | MATCH |
| newest_producer_control | `0x19` | `0x19` | MATCH |
| older_producer | `0x1d` | `0x1d` | MATCH |
| single_producer_control | `0x1d` | `0x1d` | MATCH |
| multiple_producers | `0x1f` | `0x1f` | MATCH |
| wrap_pair_early | `0x0b` | `0x0b` | MATCH |
| wrap_pair_wrapped | `0x05` | `0x05` | MATCH |

The corrected `scoreboard_forward` value is `0x09`, rather than the earlier
standalone `0x0f`, because unused encoded RS2 fields no longer create wrapped
and non-wrapped RAW events.  The correction does not reduce the corpus-level
separation: the ten treatments still occupy seven distinct five-bit summaries.

## Artifacts

- Integrated monitor: `core/dependency_feedback_monitor.sv`
- CVA6 connections and readout: `core/issue_read_operands.sv`
- Official checker match output: `core/raw_checker.sv`
- Independent oracle: `verif/dependency_feedback/expected_monitor_bitmap.py`
- Numeric comparison helper: `verif/dependency_feedback/check_integrated_feedback.py`
- Full-core logs: `fi-results/milestone8f-runs/`
- Compact outputs: `fi-results/milestone8f-feedback/`
- Corrected RAW traces: `fi-results/milestone8f-raw-traces/`
- Comparison table: `fi-results/milestone8f-analysis/windowed-integrated-vs-offline.csv`

## Boundary after 8F-C

The simulation readout is now sufficient for an initial MicroGP feedback
experiment.  It is not yet a software-visible CSR or a finalized silicon
interface.  The next separate step should measure the incremental synthesized
cost of the integrated multi-observation cone and then compare MicroGP with and
without the five-bit feedback under the same generation and fault budgets.
