module dependency_feedback_monitor_4bit (
    input  logic       clk_i,
    input  logic       rst_ni,

    // Sample only a real operand observation from the issue stage.
    input  logic       sample_valid_i,

    // Reuse dependency results that already exist inside the RAW checker.
    input  logic       raw_valid_i,
    input  logic [7:0] raw_matches_i,
    input  logic [2:0] producer_idx_i,
    input  logic [2:0] issue_pointer_i,

    // Export the smallest evidence-supported program summary.
    output logic [3:0] feedback_o
);

  logic [3:0] matching_entries;
  logic [3:0] events;

  always_comb begin
    // Count live register matches to recognize an overwrite chain.
    matching_entries = '0;
    for (int unsigned entry = 0; entry < 8; entry++) begin
      matching_entries = matching_entries + raw_matches_i[entry];
    end
  end

  always_comb begin
    // Default to no new feedback when this observation is invalid.
    events = '0;

    if (sample_valid_i) begin
      // Bit 0 remembers any live RAW dependency.
      events[0] = raw_valid_i;

      // Bit 1 remembers a valid RAW with multiple matching producers.
      events[1] = raw_valid_i && (matching_entries >= 2);

      // Bit 2 remembers selection from the wrapped circular region.
      events[2] = raw_valid_i && (producer_idx_i >= issue_pointer_i);

      // Bit 3 remembers selection from the non-wrapped region.
      events[3] = raw_valid_i && (producer_idx_i < issue_pointer_i);
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
