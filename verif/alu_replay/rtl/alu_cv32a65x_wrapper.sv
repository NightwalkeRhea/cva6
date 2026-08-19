module alu_cv32a65x_wrapper (
    input  logic [7:0]  operation_i,
    input  logic [31:0] operand_a_i,
    input  logic [31:0] operand_b_i,
    output logic [31:0] result_o,
    output logic        branch_result_o
);

  // Build the complete internal configuration from cv32a65x.
  localparam config_pkg::cva6_cfg_t CVA6Cfg =
      build_config_pkg::build_config(cva6_config_pkg::cva6_cfg);

  // Minimal version of the execution data structure used by CVA6's ALU.
  typedef struct packed {
    ariane_pkg::fu_t                         fu;
    ariane_pkg::fu_op                        operation;
    logic [CVA6Cfg.XLEN-1:0]                 operand_a;
    logic [CVA6Cfg.XLEN-1:0]                 operand_b;
    logic [CVA6Cfg.XLEN-1:0]                 imm;
    logic [CVA6Cfg.TRANS_ID_BITS-1:0]        trans_id;
  } fu_data_t;

  fu_data_t fu_data;
  fu_data_t fu_data_cpop;

  always_comb begin
    // Reconstruct the ALU transaction from the flattened wrapper inputs.
    fu_data           = '0;
    fu_data.fu        = ariane_pkg::ALU;
    fu_data.operation = ariane_pkg::fu_op'(operation_i);
    fu_data.operand_a = operand_a_i;
    fu_data.operand_b = operand_b_i;

    // CPOP uses a second input structure inside the original CVA6 ALU.
    fu_data_cpop           = fu_data;
    fu_data_cpop.operand_a = operand_a_i;
  end

  // Instantiate the official, unmodified CVA6 ALU.
  alu #(
      .CVA6Cfg (CVA6Cfg),
      .HasBranch(1'b1),
      .fu_data_t(fu_data_t)
  ) i_alu (
      .clk_i           (1'b0),
      .rst_ni          (1'b1),
      .fu_data_i       (fu_data),
      .fu_data_cpop_i  (fu_data_cpop),
      .result_o        (result_o),
      .alu_branch_res_o(branch_result_o)
  );

endmodule