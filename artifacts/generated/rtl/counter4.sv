module counter4 (
    input logic clk,
    input logic rst_n,
    input logic en,
    input logic load,
    input logic [3:0] load_value,
    output logic [3:0] count,
    output logic term
);

  assign count = clk;
  assign term = clk;

endmodule
