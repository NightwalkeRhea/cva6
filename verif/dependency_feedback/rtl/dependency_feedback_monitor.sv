module dependency_feedback_monitor (
    input  logic       clk_i,
    input  logic       rst_ni,

    // Qualify one real RAW-checker observation from the issue stage.
    input  logic       sample_valid_i,

    // Reuse decisions and state that already exist in the dependency logic.
    input  logic       raw_valid_i,
    input  logic [7:0] raw_matches_i,
    input  logic [2:0] producer_idx_i,
    input  logic [2:0] issue_pointer_i,
    input  logic [7:0] still_issued_i,

    // Export only compact sticky feedback, never the complete scoreboard.
    output logic [7:0] feedback_o
);

  logic [3:0] live_entries;
  logic [3:0] matching_entries;
  logic [7:0] events;

  always_comb begin
    // Count live scoreboard entries to choose one occupancy bin.
    live_entries = '0;
    for (int unsigned entry = 0; entry < 8; entry++) begin
      live_entries = live_entries + still_issued_i[entry];
    end

    // Count matching producers to detect an overwrite chain.
    matching_entries = '0;
    for (int unsigned entry = 0; entry < 8; entry++) begin
      matching_entries = matching_entries + raw_matches_i[entry];
    end
  end

  always_comb begin
    // Start with no new feedback event in this observation.
    events = '0;

    if (sample_valid_i) begin
      // Bit 0 remembers that at least one live RAW dependency occurred.
      events[0] = raw_valid_i;

      // Bit 1 remembers a valid RAW with two or more matching producers.
      events[1] = raw_valid_i && (matching_entries >= 2);

      // Bit 2 covers the wrapped half of circular producer selection.
      events[2] = raw_valid_i && (producer_idx_i >= issue_pointer_i);

      // Bit 3 covers the ordinary non-wrapped producer-selection half.
      events[3] = raw_valid_i && (producer_idx_i < issue_pointer_i);

      // Bits 4--7 record which scoreboard occupancy regions were visited.
      events[4] = (live_entries == 0);
      events[5] = (live_entries >= 1) && (live_entries <= 2);
      events[6] = (live_entries >= 3) && (live_entries <= 4);
      events[7] = (live_entries >= 5);
    end
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      // Clear the program-level summary before a new test begins.
      feedback_o <= '0;
    end else begin
      // Keep every observed event until software or the harness resets us.
      feedback_o <= feedback_o | events;
    end
  end

endmodule
