`timescale 1ns/1ps
module tb_equiv;
  reg [1:0] s = 0; integer i, bad = 0;
  wire a0,a1,a2,b0,b1,b2; wire [1:0] ai,bi; wire av;
  rep3_mwpm_core      core(.d0(s[0]),.d1(s[1]),.c_q0(a0),.c_q1(a1),.c_q2(a2),.err_idx(ai),.valid_corr());
  rep3_mwpm_decoder   lut (.s_zz01(s[0]),.s_zz12(s[1]),.s_xx01(1'b0),.s_xx12(1'b0),
                           .c_q0(b0),.c_q1(b1),.c_q2(b2),.err_idx(bi),.valid_corr(av));
  initial begin
    for (i=0;i<4;i=i+1) begin
      s = i[1:0]; #1;
      if ({a2,a1,a0}!=={b2,b1,b0}) begin
        $display("MISMATCH s=%b core=%b%b%b lut=%b%b%b",s,a2,a1,a0,b2,b1,b0); bad=bad+1;
      end else $display("ok s=%b -> corr=%b%b%b (q%0d)",s,a2,a1,a0,ai);
    end
    if (bad==0) $display("[PASS] explicit MWPM core == collapsed LUT for all syndromes");
    else $display("[FAIL] %0d mismatches", bad);
    $finish;
  end
endmodule
