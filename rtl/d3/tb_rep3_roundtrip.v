`timescale 1ns/1ps
// FULL error-correction round trip: encode |0_L> (data=000), inject bit-flip(s),
// compute ZZ syndrome from the corrupted data, decode, apply correction, verify
// recovery. Proves the decoder CORRECTS errors, not just maps syndromes.
module tb_rep3_roundtrip;
  reg  [2:0] data;
  wire d0 = data[0]^data[1];      // ZZ01 parity
  wire d1 = data[1]^data[2];      // ZZ12 parity
  wire c0,c1,c2; wire [1:0] eidx; wire vc;
  reg  [2:0] corrected;
  integer fails = 0;

  rep3_mwpm_core dut(.d0(d0),.d1(d1),.c_q0(c0),.c_q1(c1),.c_q2(c2),.err_idx(eidx),.valid_corr(vc));

  task run(input [2:0] e, input correctable);
    begin
      data = 3'b000 ^ e; #1;
      corrected = data ^ {c2,c1,c0};
      if (correctable) begin
        if (corrected !== 3'b000) begin
          $display("  FAIL err=%b syn=%b%b corr=%b%b%b data=%b", e,d1,d0,c2,c1,c0,corrected);
          fails = fails + 1;
        end else
          $display("  ok   err=%b -> syn=%b%b -> flip q%0d -> recovered 000", e,d1,d0,eidx);
      end else
        $display("  info err=%b (weight 2, uncorrectable at d=3) -> data=%b as expected", e,corrected);
    end
  endtask

  initial begin
    $display("--- single bit-flip correction round trip (d=3) ---");
    run(3'b000,1); run(3'b001,1); run(3'b010,1); run(3'b100,1);
    $display("--- weight-2 (beyond correction capacity, informational) ---");
    run(3'b011,0); run(3'b101,0); run(3'b110,0);
    if (fails==0) $display("[PASS] all weight-<=1 errors corrected to the codeword");
    else          $display("[FAIL] %0d correctable cases not recovered", fails);
    $finish;
  end
endmodule
