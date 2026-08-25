module raw_checker_replay_tb;

  logic [4:0]  rs_i;
  logic        rs_fpr_i;
  logic [39:0] rd_flat_i;
  logic [7:0]  rd_fpr_i;
  logic [7:0]  still_issued_i;
  logic [2:0]  issue_pointer_i;
  logic [2:0]  producer_idx_o;
  logic        dependency_valid_o;

  raw_checker_cv32a65x_wrapper dut (.*);

  string trace_file;
  string line;
  integer trace_fd;
  integer fields;
  integer issue_port;
  integer operand;
  integer rs_fpr_value;
  integer expected_valid;
  integer operand_used;
  integer vectors;
  integer errors;
  integer valid_errors;
  integer producer_index_errors;
  integer first_error_vector;
  longint unsigned cycle;
  logic [31:0] pc;
  logic [2:0] expected_idx;
  bit fault_campaign;

  initial begin
    vectors = 0;
    errors = 0;
    valid_errors = 0;
    producer_index_errors = 0;
    first_error_vector = 0;
    fault_campaign = $test$plusargs("fault_campaign");

    if (!$value$plusargs("trace_file=%s", trace_file)) begin
      $fatal(1, "Missing +trace_file=<RAW checker CSV>");
    end
    trace_fd = $fopen(trace_file, "r");
    if (trace_fd == 0) $fatal(1, "Cannot open trace: %s", trace_file);
    if (!$fgets(line, trace_fd)) $fatal(1, "Cannot read CSV header: %s", trace_file);

    while ($fgets(line, trace_fd)) begin
      fields = $sscanf(
          line,
          "%d,%d,%d,%h,%h,%d,%h,%h,%h,%h,%h,%d,%d",
          cycle, issue_port, operand, pc, rs_i, rs_fpr_value, rd_flat_i,
          rd_fpr_i, still_issued_i, issue_pointer_i, expected_idx,
          expected_valid, operand_used
      );
      if (fields != 13) begin
        $fatal(1, "Malformed CSV row after vector %0d: sscanf returned %0d", vectors, fields);
      end
      rs_fpr_i = rs_fpr_value[0];
      // Allow a synthesized multi-level combinational network to settle too.
      repeat (4) #1;
      vectors++;

      // The valid flag always matters: it decides whether a dependency exists.
      if (dependency_valid_o !== expected_valid[0]) begin
        valid_errors++;
        errors++;
        if (first_error_vector == 0) first_error_vector = vectors;
        if (errors <= 5) begin
          $display(
              "RAW_VALID_MISMATCH vector=%0d cycle=%0d port=%0d operand=%0d pc=%0h expected_valid=%0d actual_valid=%0d",
              vectors, cycle, issue_port, operand, pc, expected_valid,
              dependency_valid_o
          );
          $display("  rs=%0h rd_flat=%0h still=%0h pointer=%0h", rs_i,
                   rd_flat_i, still_issued_i, issue_pointer_i);
        end
      end

      // The producer index matters only when the golden checker found a RAW.
      // When valid is zero, RTL is free to leave any value on this output.
      if (expected_valid[0] && dependency_valid_o === 1'b1 &&
          producer_idx_o !== expected_idx) begin
        producer_index_errors++;
        errors++;
        if (first_error_vector == 0) first_error_vector = vectors;
        if (errors <= 5) begin
          $display(
              "RAW_INDEX_MISMATCH vector=%0d cycle=%0d port=%0d operand=%0d pc=%0h expected_idx=%0d actual_idx=%0d",
              vectors, cycle, issue_port, operand, pc, expected_idx,
              producer_idx_o
          );
          $display("  rs=%0h rd_flat=%0h still=%0h pointer=%0h", rs_i,
                   rd_flat_i, still_issued_i, issue_pointer_i);
        end
      end
    end

    $fclose(trace_fd);
    $display("Trace: %s", trace_file);
    $display("Vectors: %0d", vectors);
    $display("Errors: %0d", errors);
    $display("Valid errors: %0d", valid_errors);
    $display("Producer-index errors: %0d", producer_index_errors);
    $display("First error vector: %0d", first_error_vector);

    if (fault_campaign) begin
      if (errors == 0) $display("*** RAW FAULT NOT DETECTED ***");
      else $display("*** RAW FAULT DETECTED ***");
    end else begin
      if (errors != 0) $fatal(1, "Golden RAW checker replay failed");
      $display("*** RAW REPLAY SUCCESS ***");
    end
    $finish;
  end

endmodule
