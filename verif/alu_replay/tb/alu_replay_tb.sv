module alu_replay_tb;

  logic [7:0]  operation_i;
  logic [31:0] operand_a_i;
  logic [31:0] operand_b_i;

  logic [31:0] result_o;
  logic        branch_result_o;

  string trace_file;
  string header;
  string row_line;


  integer trace_fd;
  integer scan_count;

  integer cycle_value;
  integer alu_id;
  integer is_branch;
  integer operation_value;

  logic [31:0] operand_a_value;
  logic [31:0] operand_b_value;
  logic [31:0] expected_result;

  integer transaction_count;
  integer result_errors;
  integer branch_errors;
  integer fault_campaign_mode;

  alu_cv32a65x_wrapper dut (
      .operation_i    (operation_i),
      .operand_a_i    (operand_a_i),
      .operand_b_i    (operand_b_i),
      .result_o       (result_o),
      .branch_result_o(branch_result_o)
  );

  function automatic logic calculate_branch_result(
      input logic [7:0]  operation,
      input logic [31:0] operand_a,
      input logic [31:0] operand_b
  );
    case (operation)
      8'd13: calculate_branch_result = $signed(operand_a) <  $signed(operand_b);
      8'd14: calculate_branch_result = operand_a < operand_b;
      8'd15: calculate_branch_result = $signed(operand_a) >= $signed(operand_b);
      8'd16: calculate_branch_result = operand_a >= operand_b;
      8'd17: calculate_branch_result = operand_a == operand_b;
      8'd18: calculate_branch_result = operand_a != operand_b;
      default: calculate_branch_result = 1'b1;
    endcase
  endfunction

  initial begin
    operation_i      = '0;
    operand_a_i      = '0;
    operand_b_i      = '0;
    transaction_count = 0;
    result_errors      = 0;
    branch_errors      = 0;
    fault_campaign_mode = $test$plusargs("fault_campaign");

    if (!$value$plusargs("trace_file=%s", trace_file)) begin
      $fatal(1, "Missing +trace_file=<CSV path>");
    end

    trace_fd = $fopen(trace_file, "r");

    if (trace_fd == 0) begin
      $fatal(1, "Cannot open trace file: %s", trace_file);
    end

    if ($fgets(header, trace_fd) == 0) begin
      $fatal(1, "Cannot read CSV header: %s", trace_file);
    end

    while ($fgets(row_line, trace_fd) != 0) begin
      scan_count = $sscanf(
          row_line,
          "%d,%d,%d,%h,%h,%h,%h\n",
          cycle_value,
          alu_id,
          is_branch,
          operation_value,
          operand_a_value,
          operand_b_value,
          expected_result
      );

        if (scan_count != 7) begin
        $fatal(
            1,
            "Malformed CSV row after transaction %0d: fscanf returned %0d",
            transaction_count,
            scan_count
        );
    end

      if (scan_count == 7) begin
        operation_i = operation_value[7:0];
        operand_a_i = operand_a_value;
        operand_b_i = operand_b_value;

        #1;

        transaction_count = transaction_count + 1;

        if (result_o !== expected_result) begin
          result_errors = result_errors + 1;

          $display(
              "RESULT_MISMATCH row=%0d cycle=%0d alu=%0d op=%0d a=%08h b=%08h expected=%08h actual=%08h",
              transaction_count,
              cycle_value,
              alu_id,
              operation_value,
              operand_a_value,
              operand_b_value,
              expected_result,
              result_o
          );
        end

        if (is_branch != 0 &&
            branch_result_o !==
                calculate_branch_result(
                    operation_value[7:0],
                    operand_a_value,
                    operand_b_value
                )) begin
          branch_errors = branch_errors + 1;

          $display(
              "BRANCH_MISMATCH row=%0d cycle=%0d op=%0d a=%08h b=%08h expected=%0d actual=%0d",
              transaction_count,
              cycle_value,
              operation_value,
              operand_a_value,
              operand_b_value,
              calculate_branch_result(
                  operation_value[7:0],
                  operand_a_value,
                  operand_b_value
              ),
              branch_result_o
          );
        end
      end
    end

    $fclose(trace_fd);

    $display("Trace: %s", trace_file);
    $display("Transactions: %0d", transaction_count);
    $display("Result errors: %0d", result_errors);
    $display("Branch errors: %0d", branch_errors);

        if (fault_campaign_mode != 0) begin
      if (result_errors != 0 || branch_errors != 0) begin
        $display("*** FAULT DETECTED ***");
      end else begin
        $display("*** FAULT NOT DETECTED ***");
      end
    end else begin
      if (result_errors != 0 || branch_errors != 0) begin
        $fatal(1, "ALU replay FAILED");
      end

      $display("*** ALU REPLAY SUCCESS ***");
    end

    $finish;
  end

endmodule