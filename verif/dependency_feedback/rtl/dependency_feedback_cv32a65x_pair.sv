// Fixed cv32a65x cost model for a fair baseline-versus-monitor comparison.
// Four observations represent RS1 and RS2 on each of the two issue ports.
module dependency_raw_observation_cv32a65x (
    input  logic [4:0]  rs_i,
    input  logic        rs_fpr_i,
    input  logic [39:0] rd_flat_i,
    input  logic [7:0]  rd_fpr_i,
    input  logic [7:0]  still_issued_i,
    input  logic [2:0]  issue_pointer_i,
    output logic [2:0]  producer_idx_o,
    output logic        dependency_valid_o,
    output logic [7:0]  matches_o
);

  logic [7:0] matches_before;
  logic [7:0] matches_after;
  logic [2:0] last_before_idx;
  logic [2:0] last_after_idx;
  logic is_integer_x0;

  assign is_integer_x0 = (rs_i == '0) && !rs_fpr_i;

  for (genvar entry = 0; entry < 8; entry++) begin
    // Reproduce the official checker comparison and live-entry qualification.
    assign matches_o[entry] = !is_integer_x0 &&
        (rs_fpr_i == rd_fpr_i[entry]) &&
        (rs_i == rd_flat_i[entry*5 +: 5]) && still_issued_i[entry];
    assign matches_before[entry] = (entry < issue_pointer_i) && matches_o[entry];
    assign matches_after[entry] = (entry >= issue_pointer_i) && matches_o[entry];
  end

  always_comb begin
    // The last match on each side implements the circular newest-producer rule.
    last_before_idx = '0;
    last_after_idx = '0;
    for (int unsigned entry = 0; entry < 8; entry++) begin
      if (matches_before[entry]) last_before_idx = entry[2:0];
      if (matches_after[entry]) last_after_idx = entry[2:0];
    end
  end

  assign producer_idx_o = |matches_before ? last_before_idx : last_after_idx;
  assign dependency_valid_o = |matches_o;

endmodule


module dependency_feedback_cv32a65x_baseline (
    input  logic [3:0][4:0] rs_i,
    input  logic [3:0]      rs_fpr_i,
    input  logic [39:0]     rd_flat_i,
    input  logic [7:0]      rd_fpr_i,
    input  logic [7:0]      still_issued_i,
    input  logic [2:0]      issue_pointer_i,
    output logic [3:0][2:0] producer_idx_o,
    output logic [3:0]      dependency_valid_o
);

  for (genvar observation = 0; observation < 4; observation++) begin
    // The baseline contains exactly the four RAW decisions used by CVA6.
    dependency_raw_observation_cv32a65x i_raw_observation (
        .rs_i(rs_i[observation]),
        .rs_fpr_i(rs_fpr_i[observation]),
        .rd_flat_i,
        .rd_fpr_i,
        .still_issued_i,
        .issue_pointer_i,
        .producer_idx_o(producer_idx_o[observation]),
        .dependency_valid_o(dependency_valid_o[observation]),
        .matches_o()
    );
  end

endmodule


module dependency_feedback_cv32a65x_monitored (
    input  logic             clk_i,
    input  logic             rst_ni,
    input  logic [3:0]       sample_valid_i,
    input  logic [3:0][4:0]  rs_i,
    input  logic [3:0]       rs_fpr_i,
    input  logic [39:0]      rd_flat_i,
    input  logic [7:0]       rd_fpr_i,
    input  logic [7:0]       still_issued_i,
    input  logic [2:0]       issue_pointer_i,
    output logic [3:0][2:0]  producer_idx_o,
    output logic [3:0]       dependency_valid_o,
    output logic [4:0]       dependency_feedback_o
);

  logic [3:0][7:0] matches;

  for (genvar observation = 0; observation < 4; observation++) begin
    // These are identical to the baseline RAW decisions.
    dependency_raw_observation_cv32a65x i_raw_observation (
        .rs_i(rs_i[observation]),
        .rs_fpr_i(rs_fpr_i[observation]),
        .rd_flat_i,
        .rd_fpr_i,
        .still_issued_i,
        .issue_pointer_i,
        .producer_idx_o(producer_idx_o[observation]),
        .dependency_valid_o(dependency_valid_o[observation]),
        .matches_o(matches[observation])
    );
  end

  // Add only the selected five-bit shared accumulator to the same RAW cone.
  dependency_feedback_monitor #(
      .NrObservations(4),
      .NrSbEntries(8),
      .TransIdBits(3)
  ) i_dependency_feedback_monitor (
      .clk_i,
      .rst_ni,
      .sample_valid_i,
      .raw_valid_i(dependency_valid_o),
      .raw_matches_i(matches),
      .producer_idx_i(producer_idx_o),
      .issue_pointer_i,
      .still_issued_i,
      .feedback_o(dependency_feedback_o)
  );

endmodule


module dependency_feedback_cv32a65x_raw_equivalence (
    input logic             clk_i,
    input logic             rst_ni,
    input logic [3:0]       sample_valid_i,
    input logic [3:0][4:0]  rs_i,
    input logic [3:0]       rs_fpr_i,
    input logic [39:0]      rd_flat_i,
    input logic [7:0]       rd_fpr_i,
    input logic [7:0]       still_issued_i,
    input logic [2:0]       issue_pointer_i,
    output logic            mismatch_o
);

  logic [3:0][2:0] baseline_idx;
  logic [3:0][2:0] monitored_idx;
  logic [3:0] baseline_valid;
  logic [3:0] monitored_valid;
  logic [4:0] unused_feedback;

  // Drive both members with identical symbolic inputs.
  dependency_feedback_cv32a65x_baseline i_baseline (
      .rs_i,
      .rs_fpr_i,
      .rd_flat_i,
      .rd_fpr_i,
      .still_issued_i,
      .issue_pointer_i,
      .producer_idx_o(baseline_idx),
      .dependency_valid_o(baseline_valid)
  );

  dependency_feedback_cv32a65x_monitored i_monitored (
      .clk_i,
      .rst_ni,
      .sample_valid_i,
      .rs_i,
      .rs_fpr_i,
      .rd_flat_i,
      .rd_fpr_i,
      .still_issued_i,
      .issue_pointer_i,
      .producer_idx_o(monitored_idx),
      .dependency_valid_o(monitored_valid),
      .dependency_feedback_o(unused_feedback)
  );

  // The monitor is observational: it must never change an official RAW result.
  assign mismatch_o = (baseline_idx != monitored_idx) ||
                      (baseline_valid != monitored_valid);

endmodule
