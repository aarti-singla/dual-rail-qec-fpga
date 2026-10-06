// Exhaustive self-checking testbench for rep5_decoder_registered (all ZZ syndromes, XX bits held at 0).
`timescale 1ns/1ps

module tb_rep5_decoder_registered;

    reg clk = 0;
    reg rst_n = 0;
    reg syndrome_valid = 0;
    reg [7:0] syndrome = 0;
    wire [4:0] correction;
    wire [2:0] err_idx;
    wire corr_valid;
    integer errors = 0;
    integer i;

    rep5_decoder_registered dut (
        .clk(clk), .rst_n(rst_n),
        .syndrome_valid(syndrome_valid), .syndrome(syndrome),
        .correction(correction), .err_idx(err_idx), .corr_valid(corr_valid)
    );

    always #5 clk = ~clk;

    reg [4:0] expected [0:15];
    reg [2:0] expected_eidx [0:15];
    initial begin
        expected[0] = 5'b00000; expected_eidx[0] = 3'd5;
        expected[1] = 5'b00001; expected_eidx[1] = 3'd0;
        expected[2] = 5'b00011; expected_eidx[2] = 3'd0;
        expected[3] = 5'b00010; expected_eidx[3] = 3'd1;
        expected[4] = 5'b11000; expected_eidx[4] = 3'd3;
        expected[5] = 5'b00110; expected_eidx[5] = 3'd1;
        expected[6] = 5'b00100; expected_eidx[6] = 3'd2;
        expected[7] = 5'b00101; expected_eidx[7] = 3'd0;
        expected[8] = 5'b10000; expected_eidx[8] = 3'd4;
        expected[9] = 5'b10001; expected_eidx[9] = 3'd0;
        expected[10] = 5'b01100; expected_eidx[10] = 3'd2;
        expected[11] = 5'b10010; expected_eidx[11] = 3'd1;
        expected[12] = 5'b01000; expected_eidx[12] = 3'd3;
        expected[13] = 5'b01001; expected_eidx[13] = 3'd0;
        expected[14] = 5'b10100; expected_eidx[14] = 3'd2;
        expected[15] = 5'b01010; expected_eidx[15] = 3'd1;
    end

    initial begin
        rst_n = 0; syndrome_valid = 0; syndrome = 0;
        @(posedge clk); @(posedge clk);
        rst_n = 1;
        @(posedge clk);
        for (i = 0; i < 16; i = i + 1) begin
            syndrome = i[7:0];   // ZZ bits only; XX half stays 0
            syndrome_valid = 1;
            @(posedge clk);  // DUT safely samples syndrome_valid=1 here
            #1;              // let this edge's corr_valid settle before checking
            if (!corr_valid) begin
                errors = errors + 1;
                $display("MISSING corr_valid at syndrome=%0d", i);
            end else if (correction !== expected[i] || err_idx !== expected_eidx[i]) begin
                errors = errors + 1;
                $display("MISMATCH syndrome=%0d correction=%b(exp %b) err_idx=%0d(exp %0d)",
                         i, correction, expected[i], err_idx, expected_eidx[i]);
            end
            syndrome_valid = 0;
            @(posedge clk);
        end
        if (errors == 0)
            $display("PASS: all %0d syndromes matched reference decoder exactly (correction + err_idx + corr_valid timing).", 16);
        else
            $display("FAIL: %0d / %0d syndromes mismatched.", errors, 16);
        $finish;
    end

endmodule
