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

  localparam config_pkg::cva6_cfg_t CVA6Cfg =
      build_config_pkg::build_config(cva6_config_pkg::cva6_cfg);

  logic [CVA6Cfg.NR_SB_ENTRIES-1:0][ariane_pkg::REG_ADDR_SIZE-1:0] rd;

  // Convert the flat research-harness port into the official scoreboard array.
  for (genvar i = 0; i < CVA6Cfg.NR_SB_ENTRIES; i++) begin
    assign rd[i] = rd_flat_i[i*ariane_pkg::REG_ADDR_SIZE +: ariane_pkg::REG_ADDR_SIZE];
  end

  // Instantiate the official CVA6 dependency detector without modifying it.
  raw_checker #(
      .CVA6Cfg(CVA6Cfg)
  ) i_raw_checker (
      .clk_i          (1'b0),
      .rst_ni         (1'b1),
      .rs_i,
      .rs_fpr_i,
      .rd_i           (rd),
      .rd_fpr_i,
      .still_issued_i,
      .issue_pointer_i,
      .idx_o          (producer_idx_o),
      .valid_o        (dependency_valid_o)
  );

endmodule
