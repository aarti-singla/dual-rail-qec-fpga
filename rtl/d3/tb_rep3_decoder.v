`timescale 1ns/1ps
// Exhaustive self-checking testbench + latency measurement for the
// d=3 repetition MWPM decoder.  Verifies every syndrome pattern against
// the paper's syndrome-to-error table, and measures decode latency in
// clock cycles from syndrome_valid to corr_valid.
module tb_rep3_decoder;
    reg        clk = 0, rst_n = 0, syndrome_valid = 0;
    reg  [3:0] syndrome = 4'b0000;
    wire [2:0] correction;
    wire [1:0] err_idx;
    wire       corr_valid;

    integer errors = 0;
    integer i;
    integer t_issue, t_done, latency_cycles;
    integer cyc = 0;

    rep3_decoder_registered dut (
        .clk(clk), .rst_n(rst_n),
        .syndrome_valid(syndrome_valid), .syndrome(syndrome),
        .correction(correction), .err_idx(err_idx), .corr_valid(corr_valid)
    );

    always #1.25 clk = ~clk;          // 400 MHz: 2.5 ns period
    always @(posedge clk) cyc = cyc + 1;

    // golden model (paper table), driven by the two ZZ bits
    function [2:0] golden_corr(input [1:0] zz);
        case (zz)                      // {s_zz12, s_zz01}
            2'b00: golden_corr = 3'b000;          // none
            2'b01: golden_corr = 3'b001;          // s01=1,s12=0 -> q0
            2'b11: golden_corr = 3'b010;          // s01=1,s12=1 -> q1
            2'b10: golden_corr = 3'b100;          // s01=0,s12=1 -> q2
        endcase
    endfunction

    task check_pattern(input [3:0] s);
        reg [2:0] exp;
        begin
            exp = golden_corr(s[1:0]);
            @(negedge clk);
            syndrome = s; syndrome_valid = 1;
            t_issue = cyc;
            @(negedge clk);
            syndrome_valid = 0;
            // wait for corr_valid
            wait (corr_valid == 1);
            t_done = cyc;
            if (correction !== exp) begin
                $display("  FAIL syndrome=%b  got corr=%b  exp=%b  err_idx=%0d",
                          s, correction, exp, err_idx);
                errors = errors + 1;
            end else begin
                $display("  ok   syndrome=%b -> corr=%b err_idx=%0d", s, correction, err_idx);
            end
            @(negedge clk);
        end
    endtask

    initial begin
        $dumpfile("tb_rep3_decoder.vcd"); $dumpvars(0, tb_rep3_decoder);
        rst_n = 0; repeat (4) @(negedge clk); rst_n = 1; @(negedge clk);

        $display("--- exhaustive syndrome sweep (ZZ bits; XX swept but unused) ---");
        for (i = 0; i < 16; i = i + 1) check_pattern(i[3:0]);

        // measure latency on a clean single transaction
        $display("--- latency measurement ---");
        @(negedge clk); cyc = 0;
        @(negedge clk); syndrome = 4'b0011; syndrome_valid = 1; t_issue = cyc;
        @(negedge clk); syndrome_valid = 0;
        wait (corr_valid == 1); t_done = cyc;
        latency_cycles = t_done - t_issue;
        $display("  syndrome_valid @cyc %0d, corr_valid @cyc %0d -> latency = %0d clk = %0d ns @400MHz",
                  t_issue, t_done, latency_cycles, latency_cycles*1000/400);

        $display("--- RESULT ---");
        if (errors == 0) $display("  [PASS] all 16 syndrome patterns decode correctly");
        else             $display("  [FAIL] %0d mismatches", errors);
        $finish;
    end
endmodule
