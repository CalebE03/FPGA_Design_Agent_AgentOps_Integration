`timescale 1ns/1ps

module demo_module_tb;
  logic clk;
  logic rst_n;
  logic [7:0] in_data;
  logic [7:0] out_data;

  demo_module dut (
    .clk(clk), .rst_n(rst_n), .in_data(in_data), .out_data(out_data)
  );

  initial begin
    $display("Running stub TB for demo_module");
    out_data = clk;
    #10;
    $finish;
  end
endmodule
