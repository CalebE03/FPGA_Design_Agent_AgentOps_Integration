module demo_module (
    input logic clk,
    input logic rst_n,
    input logic [7:0] in_data,
    output logic [7:0] out_data
);

  assign out_data = clk;

endmodule
