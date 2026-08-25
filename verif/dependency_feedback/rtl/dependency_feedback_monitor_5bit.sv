module dependency_feedback_monitor_5bit (
    input  logic       clk_i,
    input  logic       rst_ni,

    // Sample only a real operand observation from the issue stage.
    input  logic       sample_valid_i,

    // Reuse dependency and scoreboard state that CVA6 already computes.
    input  logic       raw_valid_i,
    input  logic [7:0] raw_matches_i,
    input  logic [2:0] producer_idx_i,
    input  logic [2:0] issue_pointer_i,
    input  logic [7:0] still_issued_i,

    // Add one medium-occupancy bit to the four-bit base summary.
    output logic [4:0] feedback_o
);

  logic [3:0] matching_entries;
  logic [3:0] live_entries;
  logic [4:0] events;

  always_comb begin
    // Count matching producers and live entries in the same small loop.
    matching_entries = '0;
    live_entries = '0;
    for (int unsigned entry = 0; entry < 8; entry++) begin
      matching_entries = matching_entries + raw_matches_i[entry];
      live_entries = live_entries + still_issued_i[entry];
    end
  end

  always_comb begin
    // Default to no new feedback when this observation is invalid.
    events = '0;

    if (sample_valid_i) begin
      // Bits 0--3 keep the evidence-supported RAW context summary.
      events[0] = raw_valid_i;
      events[1] = raw_valid_i && (matching_entries >= 2);
      events[2] = raw_valid_i && (producer_idx_i >= issue_pointer_i);
      events[3] = raw_valid_i && (producer_idx_i < issue_pointer_i);

      // Bit 4 remembers the only occupancy bin that varied usefully so far.
      events[4] = (live_entries >= 3) && (live_entries <= 4);
    end
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      // Start each generated test with an empty novelty summary.
      feedback_o <= '0;
    end else begin
      // Keep every context observed during the current test.
      feedback_o <= feedback_o | events;
    end
  end

endmodule
