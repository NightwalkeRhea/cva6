# Milestone 7A: CVA6 dependency-resolution signal map

Configuration: `cv32a65x`

This milestone only maps existing RTL. It does not add a monitor.

## Relevant configuration

`cv32a65x_config_pkg.sv` enables superscalar issue and ALU bypass and selects
eight scoreboard entries. `build_config_pkg.sv` therefore derives:

- two issue ports;
- two ALUs;
- two commit ports;
- an eight-entry speculative scoreboard;
- five writeback ports because CV-X-IF is enabled;
- same-cycle ALU-to-ALU bypass enabled.

## Dependency detection

The main logic is in `core/issue_read_operands.sv`. It instantiates one
`core/raw_checker.sv` for each source operand and issue port.

| Local signal | Meaning |
| --- | --- |
| `issue_instr_valid_i[i]` | An instruction is present at issue port `i`. |
| `issue_instr_i[i].pc` | PC of that consumer instruction. |
| `issue_instr_i[i].trans_id` | Consumer scoreboard identifier. |
| `issue_instr_i[i].rs1`, `rs2` | Architectural source-register addresses. |
| `rs1_has_raw[i]`, `rs2_has_raw[i]` | The source matches an older, still-issued scoreboard destination. |
| `idx_hzd_rs1[i]`, `idx_hzd_rs2[i]` | Scoreboard ID of the newest matching producer. |
| `fwd_i.still_issued[j]` | Scoreboard entry `j` is live and not cancelled. |
| `fwd_i.sbe[j].rd` | Destination register belonging to producer `j`. |

`raw_checker.sv` excludes integer register `x0` and handles scoreboard-pointer
wraparound when selecting the newest producer.

The RAW flags are useful for checking the implementation, but a RAW count by
itself is mostly reconstructable from an instruction trace.

## Result availability and ordinary forwarding

The selected producer result is considered ready when its scoreboard entry is
valid without an exception, or when a matching result is arriving on a live
writeback port in the current cycle.

| Local signal | Meaning |
| --- | --- |
| `fwd_res_valid[j]` | Producer `j` currently has an exception-free result. |
| `rs1_valid[i]`, `rs2_valid[i]` | The selected producer result is available for the consumer. |
| `forward_rs1[i]`, `forward_rs2[i]` | The consumer operand is selected from the producer result instead of the register file. |
| `rs1_res[i]`, `rs2_res[i]` | Forwarded operand value. |
| `fu_data_n[i].operand_a`, `operand_b` | Final values selected by the operand mux. |

The writeback-port source can be derived by testing, for each port `p`:

```text
fwd_i.wb[p].valid
&& !fwd_i.wb[p].ex_valid
&& fwd_i.wb[p].trans_id == idx_hzd_rsX[i]
```

The port labels are:

| Port | RTL name | Producer class |
| --- | --- | --- |
| 0 | `FLU_WB` | ALU, branch, CSR, AES, multiply/divide shared fixed-latency path |
| 1 | `STORE_WB` | store completion |
| 2 | `LOAD_WB` | load result |
| 3 | `FPU_WB` | floating-point path, disabled by this configuration |
| 4 | `X_WB` | CV-X-IF result |

If no matching live writeback port exists but `fwd_i.sbe[j].valid` is set, the
value comes from the result already stored in scoreboard entry `j`. The RTL
does not provide generic `EX`, `MEM`, and `WB` forwarding labels; the monitor
must use these actual sources instead of inventing pipeline-stage names.

## Dependency stalls

For source operand `X`, the dependency is unresolved when:

```text
issue_instr_valid_i[i]
&& rsX_has_raw[i]
&& !rsX_valid[i]
```

This condition sets `stall_rsX[i]` and `stall_raw[i]`. The instruction is
accepted only when `issue_ack_o[i]` becomes high.

`stall_raw` is initialized from the external `stall_i`, so it is not a pure
dependency-stall classification in every configuration. The explicit
`rsX_has_raw && !rsX_valid` expression is the safer monitor event.

`fu_busy[i]` is a structural hazard. It must remain separate from a RAW stall.
For the second issue port, failure to accept port zero also suppresses port
one, which must not automatically be counted as an operand dependency.

## Same-cycle ALU bypass

The dual-issue configuration has a separate path for a consumer in issue port
one that depends on an ALU producer in issue port zero in the same cycle:

| Local signal | Meaning |
| --- | --- |
| `is_alu_bypass` | Both issue slots contain compatible ALU operations. |
| `alu_bypass.rs1_from_rd` | Port-one RS1 consumes port-zero ALU output directly. |
| `alu_bypass.rs2_from_rd` | Port-one RS2 consumes port-zero ALU output directly. |

If the pair is dependent but cannot use this bypass, `stall_raw[1]` is set.
This event is strongly microarchitectural and should remain distinct from
ordinary scoreboard forwarding.

## Valid, accepted, flush, and cancellation context

| Signal | Meaning |
| --- | --- |
| `issue_instr_valid_i[i]` | Qualifies an issue attempt, including attempts that stall. |
| `issue_ack_o[i]` | The issue attempt is accepted. |
| `issue_instr_valid_i[i] && issue_ack_o[i]` | Accepted issue transaction. |
| `flush_i` in `issue_read_operands` | Suppresses functional-unit valid outputs for flushed work. |
| `flush_unissued_instr_i` in `scoreboard` | Prevents unissued decoded work from entering the scoreboard. |
| `resolved_branch_i.valid && resolved_branch_i.is_mispredict` | Branch-mispredict cancellation event, named `bmiss` in the scoreboard. |
| `mem_q[j].cancelled` / `still_issued[j]` | Tracks speculative scoreboard entries killed by a misprediction. |
| top-level `flush_ctrl_id` | Full issue-stage/scoreboard flush. |

## Proposed trace record for Milestone 7B

An issue-attempt record should contain:

```text
cycle
issue_port
consumer_pc
consumer_trans_id
consumer_fu
rs1_address
rs2_address
rs1_has_raw
rs2_has_raw
rs1_producer_id
rs2_producer_id
rs1_ready
rs2_ready
rs1_forwarded
rs2_forwarded
rs1_source
rs2_source
same_cycle_alu_bypass_rs1
same_cycle_alu_bypass_rs2
raw_stall_rs1
raw_stall_rs2
structural_stall
issue_accepted
flush
```

Recommended source encoding:

```text
REGFILE
SCOREBOARD
FLU_WB
STORE_WB
LOAD_WB
FPU_WB
X_WB
SAME_CYCLE_ALU
UNAVAILABLE
```

Forwarding counts should be incremented only on an accepted issue transaction.
Unresolved-dependency stall duration should be counted on every valid issue
attempt where `rsX_has_raw && !rsX_valid` remains true. Flush and cancellation
events need their own records because killed instructions do not appear in the
retired-instruction trace.

## Signals with credible incremental value

Most likely to add information beyond a retired trace:

- actual writeback source used by each operand;
- same-cycle ALU bypass selection;
- unresolved-dependency stall cycles;
- structural stall versus dependency stall;
- speculative dependency activity later cancelled by a misprediction.

Mostly software-derivable and therefore only useful as controls:

- source and destination register numbers;
- static RAW distance;
- opcode and operand-use counts for retired instructions.
