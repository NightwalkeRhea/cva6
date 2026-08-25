module dependency_feedback_monitor_tb;

  logic       clk_i;
  logic       rst_ni;
  logic       sample_valid_i;
  logic       raw_valid_i;
  logic [7:0] raw_matches_i;
  logic [2:0] producer_idx_i;
  logic [2:0] issue_pointer_i;
  logic [7:0] still_issued_i;
  logic [7:0] feedback_o;

  dependency_feedback_monitor dut (.*);

  string trace_file;
  string line;
  integer trace_fd;
  integer fields;
  integer issue_port;
  integer operand;
  integer rs_fpr_value;
  integer expected_valid;
  integer operand_used;
  integer expected_bitmap_value;
  integer vectors;
  integer entry;
  longint unsigned cycle;
  logic [31:0] pc;
  logic [4:0] rs;
  logic [39:0] rd_flat;
  logic [7:0] rd_fpr;

  // Give every replayed observation one clean clock edge.
  initial begin
    clk_i = 1'b0;
    forever #5 clk_i = ~clk_i;
  end

  initial begin
    vectors = 0;
    sample_valid_i = 1'b0;
    raw_valid_i = 1'b0;
    raw_matches_i = '0;
    producer_idx_i = '0;
    issue_pointer_i = '0;
    still_issued_i = '0;

    if (!$value$plusargs("trace_file=%s", trace_file)) begin
      $fatal(1, "Missing +trace_file=<RAW checker CSV>");
    end
    if (!$value$plusargs("expected_bitmap=%h", expected_bitmap_value)) begin
      $fatal(1, "Missing +expected_bitmap=<hex byte>");
    end

    trace_fd = $fopen(trace_file, "r");
    if (trace_fd == 0) $fatal(1, "Cannot open trace: %s", trace_file);
    if (!$fgets(line, trace_fd)) $fatal(1, "Cannot read CSV header: %s", trace_file);

    // Reset the sticky bits before replaying a new program.
    rst_ni = 1'b0;
    repeat (2) @(posedge clk_i);
    rst_ni = 1'b1;

    while ($fgets(line, trace_fd)) begin
      fields = $sscanf(
          line,
          "%d,%d,%d,%h,%h,%d,%h,%h,%h,%h,%h,%d,%d",
          cycle, issue_port, operand, pc, rs, rs_fpr_value, rd_flat,
          rd_fpr, still_issued_i, issue_pointer_i, producer_idx_i,
          expected_valid, operand_used
      );
      if (fields != 13) begin
        $fatal(1, "Malformed CSV row after vector %0d: sscanf returned %0d",
               vectors, fields);
      end

      // Rebuild the match vector that is already present inside raw_checker.
      raw_matches_i = '0;
      for (entry = 0; entry < 8; entry++) begin
        raw_matches_i[entry] = still_issued_i[entry] &&
            (rd_fpr[entry] == rs_fpr_value[0]) &&
            (rd_flat[entry*5 +: 5] == rs);
      end

      // Integer x0 is constant, so the official checker suppresses its match.
      if ((rs == '0) && !rs_fpr_value[0]) raw_matches_i = '0;

      // Feed only a semantically used operand into the monitor.
      raw_valid_i = expected_valid[0];
      sample_valid_i = operand_used[0];
      @(posedge clk_i);
      vectors++;
    end

    // Stop sampling before checking the final sticky summary.
    @(negedge clk_i);
    sample_valid_i = 1'b0;
    @(posedge clk_i);
    #1;
    $fclose(trace_fd);

    $display("Trace: %s", trace_file);
    $display("Vectors: %0d", vectors);
    $display("Expected bitmap: 0x%02h", expected_bitmap_value[7:0]);
    $display("Actual bitmap:   0x%02h", feedback_o);
    if (feedback_o !== expected_bitmap_value[7:0]) begin
      $fatal(1, "Dependency feedback bitmap mismatch");
    end
    $display("*** DEPENDENCY MONITOR REPLAY SUCCESS ***");
    $finish;
  end

endmodule
