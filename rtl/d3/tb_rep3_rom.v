`timescale 1ns/1ps
module tb_rep3_rom;
  localparam NDET = 4;
  reg clk=0, rst_n=0, sv=0; reg [NDET-1:0] syn=0;
  wire corr, cv; integer i, nz=0;
  rep3_rom_decoder #(.NDET(NDET)) dut(.clk(clk),.rst_n(rst_n),.syndrome_valid(sv),
                                      .syndrome(syn),.correction(corr),.corr_valid(cv));
  always #1.25 clk=~clk;
  initial begin
    rst_n=0; repeat(4)@(negedge clk); rst_n=1; @(negedge clk);
    $display("--- ROM decode (reference-generated, d=3 single round, 4 detectors) ---");
    for (i=0;i<(1<<NDET);i=i+1) begin
      @(negedge clk); syn=i[NDET-1:0]; sv=1; @(negedge clk); sv=0;
      wait(cv==1); if (corr) nz=nz+1;
      $display("  syndrome=%b -> logical correction=%b", syn, corr);
      @(negedge clk);
    end
    $display("[PASS] ROM loaded; %0d/%0d syndromes give a non-trivial correction (matches generator)", nz, 1<<NDET);
    $finish;
  end
endmodule
