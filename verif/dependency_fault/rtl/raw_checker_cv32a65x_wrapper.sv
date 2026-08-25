module raw_checker_cv32a65x_wrapper (
    input  logic [4:0]  rs_i,
    input  logic        rs_fpr_i,
    input  logic [39:0] rd_flat_i,
    input  logic [7:0]  rd_fpr_i,
    input  logic [7:0]  still_issued_i,
    input  logic [2:0]  issue_pointer_i,
    output logic [2:0]  producer_idx_o,
    output logic        dependency_valid_o
);

  logic [7:0] same_rd_as_rs;
  logic [7:0] same_rd_as_rs_before;
  logic [7:0] same_rd_as_rs_after;
  logic [2:0] last_before_idx;
  logic [2:0] last_after_idx;

  // Fixed cv32a65x (8 x 5-bit) form of core/raw_checker.sv.  Keeping the
  // scoreboard input flat avoids cross-frontend packed-array reordering.
  for (genvar i = 0; i < 8; i++) begin
    assign same_rd_as_rs[i] =
        (rs_fpr_i == rd_fpr_i[i]) &&
        (rs_i == rd_flat_i[i*5 +: 5]) && still_issued_i[i];
    assign same_rd_as_rs_before[i] =
        (i < issue_pointer_i) && same_rd_as_rs[i];
    assign same_rd_as_rs_after[i] =
        (i >= issue_pointer_i) && same_rd_as_rs[i];
  end

  always_comb begin
    // Scan upward so the final assignment is the newest index on each side.
    last_before_idx = '0;
    last_after_idx = '0;
    for (int unsigned i = 0; i < 8; i++) begin
      if (same_rd_as_rs_before[i]) last_before_idx = i[2:0];
      if (same_rd_as_rs_after[i]) last_after_idx = i[2:0];
    end
  end

  // Prefer the ordinary side; use the wrapped side only when no earlier index matches.
  assign producer_idx_o = |same_rd_as_rs_before ? last_before_idx : last_after_idx;
  // Integer x0 is constant and must never wait for a scoreboard producer.
  assign dependency_valid_o = |same_rd_as_rs && !((rs_i == '0) && !rs_fpr_i);

endmodule
