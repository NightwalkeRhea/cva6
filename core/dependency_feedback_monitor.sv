// Compact research feedback for dependency-resolution activity.
//
// This monitor deliberately stores only five sticky novelty bits.  The wide
// scoreboard and register identities stay inside the core.
module dependency_feedback_monitor #(
    parameter int unsigned NrObservations = 2,
    parameter int unsigned NrSbEntries = 8,
    parameter int unsigned TransIdBits = 3
) (
    input logic clk_i,
    input logic rst_ni,

    // Each observation is one real source operand from one valid instruction.
    input logic [NrObservations-1:0] sample_valid_i,
    input logic [NrObservations-1:0] raw_valid_i,
    input logic [NrObservations-1:0][NrSbEntries-1:0] raw_matches_i,
    input logic [NrObservations-1:0][TransIdBits-1:0] producer_idx_i,

    // These describe the shared circular scoreboard at the sampling cycle.
    input logic [TransIdBits-1:0] issue_pointer_i,
    input logic [NrSbEntries-1:0] still_issued_i,

    // Software cannot see these bits; the research harness reads the summary.
    output logic [4:0] feedback_o
);

  localparam int unsigned CountBits = $clog2(NrSbEntries + 1);

  logic [CountBits-1:0] live_entries;
  logic [NrObservations-1:0][CountBits-1:0] matching_entries;
  logic [4:0] events;

  always_comb begin
    // Count the shared occupancy once and the matching producers per operand.
    live_entries = '0;
    matching_entries = '0;
    for (int unsigned entry = 0; entry < NrSbEntries; entry++) begin
      live_entries = live_entries + CountBits'(still_issued_i[entry]);
      for (int unsigned observation = 0; observation < NrObservations; observation++) begin
        matching_entries[observation] =
            matching_entries[observation] +
            CountBits'(raw_matches_i[observation][entry]);
      end
    end
  end

  always_comb begin
    // OR all simultaneous operands into one set of events for this cycle.
    events = '0;
    for (int unsigned observation = 0; observation < NrObservations; observation++) begin
      if (sample_valid_i[observation]) begin
        events[0] |= raw_valid_i[observation];
        events[1] |= raw_valid_i[observation] &&
                     (matching_entries[observation] >= 2);
        events[2] |= raw_valid_i[observation] &&
                     (producer_idx_i[observation] >= issue_pointer_i);
        events[3] |= raw_valid_i[observation] &&
                     (producer_idx_i[observation] < issue_pointer_i);
        events[4] |= (live_entries >= 3) && (live_entries <= 4);
      end
    end
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      // A processor reset starts a fresh generated-program summary.
      feedback_o <= '0;
    end else begin
      // Remember every selected context reached before the next reset.
      feedback_o <= feedback_o | events;
    end
  end

endmodule
