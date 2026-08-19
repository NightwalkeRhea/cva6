// Copyright 2025 ETH Zurich and University of Bologna.
// Copyright and related rights are licensed under the Solderpad Hardware
// License, Version 0.51 (the "License"); you may not use this file except in
// compliance with the License.  You may obtain a copy of the License at
// http://solderpad.org/licenses/SHL-0.51. Unless required by applicable law
// or agreed to in writing, software, hardware and materials distributed under
// this License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.
//
// Original authors: Gianmarco Ottavi,  University of Bologna
//                   Riccardo Tedeschi, University of Bologna
// Description: ALU(s) wrapper

module alu_wrapper
  import ariane_pkg::*;
#(
    parameter config_pkg::cva6_cfg_t CVA6Cfg = config_pkg::cva6_cfg_empty,
    parameter type fu_data_t = logic
) (
    input  logic                                               clk_i,
    input  logic                                               rst_ni,
    // ALU-to-ALU forwarding controls
    input  alu_bypass_t                                        alu_bypass_i,
    // Tracer signals
    input  logic        [CVA6Cfg.NrIssuePorts-1:0]             alu_valid_i,     // a valid instruction was routed to primary ALU 0
    input  logic        [CVA6Cfg.NrIssuePorts-1:0]             alu2_valid_i,    // a valid instruction was routed to primary ALU 1
    input  logic        [CVA6Cfg.NrIssuePorts-1:0]             branch_valid_i,  // branch comparison also genuinely use ALU 0
    // Operation and operands sent to each ALU
    input  fu_data_t    [CVA6Cfg.NrALUs-1:0]                   fu_data_i,
    output logic        [CVA6Cfg.NrALUs-1:0][CVA6Cfg.XLEN-1:0] result_o,
    output logic                                               alu_branch_res_o
);
  `ifndef SYNTHESIS
    // Simulation-only ALU transaction tracer.
    // Excluded when the module is synthesized with -D SYNTHESIS.

    // Output file handles for the two ALUs.
    integer alu0_trace_fd;
    integer alu1_trace_fd;

    // Simulation cycle recorded with every transaction.
    longint unsigned alu_trace_cycle;

    // File paths supplied through simulator plusargs.
    string alu0_trace_file;
    string alu1_trace_file;

    initial begin
      // Zero means that no trace file is open.
      alu0_trace_fd = 0;
      alu1_trace_fd = 0;
      alu_trace_cycle = 0;

      // Open ALU 0 trace only when its filename is provided.
      if ($value$plusargs("alu0_trace_file=%s", alu0_trace_file)) begin
        alu0_trace_fd = $fopen(alu0_trace_file, "w");

        // Stop immediately if the requested file cannot be opened.
        if (alu0_trace_fd == 0) begin
          $fatal(1, "Cannot open ALU0 trace file: %s", alu0_trace_file);
        end

        // CSV column names.
        $fdisplay(
            alu0_trace_fd,
            "cycle,alu_id,is_branch,operation,operand_a,operand_b,result"
        );
      end

      // Open ALU 1 trace only when its filename is provided.
      if ($value$plusargs("alu1_trace_file=%s", alu1_trace_file)) begin
        alu1_trace_fd = $fopen(alu1_trace_file, "w");

        // Stop immediately if the requested file cannot be opened.
        if (alu1_trace_fd == 0) begin
          $fatal(1, "Cannot open ALU1 trace file: %s", alu1_trace_file);
        end

        // CSV column names.
        $fdisplay(
            alu1_trace_fd,
            "cycle,alu_id,is_branch,operation,operand_a,operand_b,result"
        );
      end
    end

    // Count active clock cycles after reset.
    always_ff @(posedge clk_i or negedge rst_ni) begin
      if (!rst_ni) begin
        alu_trace_cycle <= 0;
      end else begin
        alu_trace_cycle <= alu_trace_cycle + 1;
      end
    end
  `endif

  alu #(
      .CVA6Cfg  (CVA6Cfg),
      .HasBranch(1'b1),
      .fu_data_t(fu_data_t)
  ) alu_i (
      .clk_i           (clk_i),
      .rst_ni          (rst_ni),
      .fu_data_i       (fu_data_i[0]),
      .fu_data_cpop_i  (fu_data_i[0]),
      .result_o        (result_o[0]),
      .alu_branch_res_o(alu_branch_res_o)
  );

  `ifndef SYNTHESIS
    // Record ALU 0 only when it performs a real ALU operation
    // or a real branch comparison.
    always_ff @(posedge clk_i) begin
      if (rst_ni && alu0_trace_fd != 0 &&
          (|(alu_valid_i | branch_valid_i))) begin

        // Save the cycle, operation, actual inputs and result.
        $fdisplay(
            alu0_trace_fd,
            "%0d,0,%0d,%0h,%0h,%0h,%0h",
            alu_trace_cycle,
            |branch_valid_i,          // 1 when this is a branch comparison.
            fu_data_i[0].operation,   // Encoded ALU operation.
            fu_data_i[0].operand_a,   // First ALU input.
            fu_data_i[0].operand_b,   // Second ALU input.
            result_o[0]               // ALU output.
        );
      end
    end
  `endif

  if (CVA6Cfg.SuperscalarEn) begin : gen_alu2
    // inputs that will actually reach alu1
    fu_data_t fu_data_bypass;

    always_comb begin
      // normally alu1 receives its issued operands unchanged
      fu_data_bypass = fu_data_i[1];

      //forward alu0's result directly into alu1 operand A
      if (alu_bypass_i.rs1_from_rd) begin
        fu_data_bypass.operand_a = result_o[0];
      end

      //forward alu0's result directly into alu1 operand B
      if (alu_bypass_i.rs2_from_rd) begin
        fu_data_bypass.operand_b = result_o[0];
      end
    end

    alu #(
        .CVA6Cfg  (CVA6Cfg),
        .HasBranch(1'b0),
        .fu_data_t(fu_data_t)
    ) alu2_i (
        .clk_i           (clk_i),
        .rst_ni          (rst_ni),
        .fu_data_i       (fu_data_bypass),
        .fu_data_cpop_i  (fu_data_i[1]),
        .result_o        (result_o[1]),
        .alu_branch_res_o(  /* Unconnected */)
    );

    `ifndef SYNTHESIS
        // Record ALU 1 only when a real instruction is assigned to it.
        always_ff @(posedge clk_i) begin
          if (rst_ni && alu1_trace_fd != 0 && (|alu2_valid_i)) begin

            // Use fu_data_bypass because it contains ALU 1's actual
            // inputs after possible forwarding from ALU 0.
            $fdisplay(
                alu1_trace_fd,
                "%0d,1,0,%0h,%0h,%0h,%0h",
                alu_trace_cycle,
                fu_data_bypass.operation,  // Encoded ALU operation.
                fu_data_bypass.operand_a,  // Actual first input.
                fu_data_bypass.operand_b,  // Actual second input.
                result_o[1]                // ALU 1 output.
            );
          end
        end
    `endif
  end
  // flush and close the csv files when simulation is done
  `ifndef SYNTHESIS
    final begin
      if (alu0_trace_fd != 0) $fclose(alu0_trace_fd);
      if (alu1_trace_fd != 0) $fclose(alu1_trace_fd);
    end
  `endif
endmodule
