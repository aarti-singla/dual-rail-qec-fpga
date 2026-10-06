// Exhaustive self-checking testbench for rep7_decoder_registered (all ZZ syndromes, XX bits held at 0).
`timescale 1ns/1ps

module tb_rep7_decoder_registered;

    reg clk = 0;
    reg rst_n = 0;
    reg syndrome_valid = 0;
    reg [11:0] syndrome = 0;
    wire [6:0] correction;
    wire [2:0] err_idx;
    wire corr_valid;
    integer errors = 0;
    integer i;

    rep7_decoder_registered dut (
        .clk(clk), .rst_n(rst_n),
        .syndrome_valid(syndrome_valid), .syndrome(syndrome),
        .correction(correction), .err_idx(err_idx), .corr_valid(corr_valid)
    );

    always #5 clk = ~clk;

    reg [6:0] expected [0:63];
    reg [2:0] expected_eidx [0:63];
    initial begin
        expected[0] = 7'b0000000; expected_eidx[0] = 3'd7;
        expected[1] = 7'b0000001; expected_eidx[1] = 3'd0;
        expected[2] = 7'b0000011; expected_eidx[2] = 3'd0;
        expected[3] = 7'b0000010; expected_eidx[3] = 3'd1;
        expected[4] = 7'b0000111; expected_eidx[4] = 3'd0;
        expected[5] = 7'b0000110; expected_eidx[5] = 3'd1;
        expected[6] = 7'b0000100; expected_eidx[6] = 3'd2;
        expected[7] = 7'b0000101; expected_eidx[7] = 3'd0;
        expected[8] = 7'b1110000; expected_eidx[8] = 3'd4;
        expected[9] = 7'b0001110; expected_eidx[9] = 3'd1;
        expected[10] = 7'b0001100; expected_eidx[10] = 3'd2;
        expected[11] = 7'b0001101; expected_eidx[11] = 3'd0;
        expected[12] = 7'b0001000; expected_eidx[12] = 3'd3;
        expected[13] = 7'b0001001; expected_eidx[13] = 3'd0;
        expected[14] = 7'b0001011; expected_eidx[14] = 3'd0;
        expected[15] = 7'b0001010; expected_eidx[15] = 3'd1;
        expected[16] = 7'b1100000; expected_eidx[16] = 3'd5;
        expected[17] = 7'b1100001; expected_eidx[17] = 3'd0;
        expected[18] = 7'b0011100; expected_eidx[18] = 3'd2;
        expected[19] = 7'b1100010; expected_eidx[19] = 3'd1;
        expected[20] = 7'b0011000; expected_eidx[20] = 3'd3;
        expected[21] = 7'b0011001; expected_eidx[21] = 3'd0;
        expected[22] = 7'b1100100; expected_eidx[22] = 3'd2;
        expected[23] = 7'b0011010; expected_eidx[23] = 3'd1;
        expected[24] = 7'b0010000; expected_eidx[24] = 3'd4;
        expected[25] = 7'b0010001; expected_eidx[25] = 3'd0;
        expected[26] = 7'b0010011; expected_eidx[26] = 3'd0;
        expected[27] = 7'b0010010; expected_eidx[27] = 3'd1;
        expected[28] = 7'b1101000; expected_eidx[28] = 3'd3;
        expected[29] = 7'b0010110; expected_eidx[29] = 3'd1;
        expected[30] = 7'b0010100; expected_eidx[30] = 3'd2;
        expected[31] = 7'b0010101; expected_eidx[31] = 3'd0;
        expected[32] = 7'b1000000; expected_eidx[32] = 3'd6;
        expected[33] = 7'b1000001; expected_eidx[33] = 3'd0;
        expected[34] = 7'b1000011; expected_eidx[34] = 3'd0;
        expected[35] = 7'b1000010; expected_eidx[35] = 3'd1;
        expected[36] = 7'b0111000; expected_eidx[36] = 3'd3;
        expected[37] = 7'b1000110; expected_eidx[37] = 3'd1;
        expected[38] = 7'b1000100; expected_eidx[38] = 3'd2;
        expected[39] = 7'b1000101; expected_eidx[39] = 3'd0;
        expected[40] = 7'b0110000; expected_eidx[40] = 3'd4;
        expected[41] = 7'b0110001; expected_eidx[41] = 3'd0;
        expected[42] = 7'b1001100; expected_eidx[42] = 3'd2;
        expected[43] = 7'b0110010; expected_eidx[43] = 3'd1;
        expected[44] = 7'b1001000; expected_eidx[44] = 3'd3;
        expected[45] = 7'b1001001; expected_eidx[45] = 3'd0;
        expected[46] = 7'b0110100; expected_eidx[46] = 3'd2;
        expected[47] = 7'b1001010; expected_eidx[47] = 3'd1;
        expected[48] = 7'b0100000; expected_eidx[48] = 3'd5;
        expected[49] = 7'b0100001; expected_eidx[49] = 3'd0;
        expected[50] = 7'b0100011; expected_eidx[50] = 3'd0;
        expected[51] = 7'b0100010; expected_eidx[51] = 3'd1;
        expected[52] = 7'b1011000; expected_eidx[52] = 3'd3;
        expected[53] = 7'b0100110; expected_eidx[53] = 3'd1;
        expected[54] = 7'b0100100; expected_eidx[54] = 3'd2;
        expected[55] = 7'b0100101; expected_eidx[55] = 3'd0;
        expected[56] = 7'b1010000; expected_eidx[56] = 3'd4;
        expected[57] = 7'b1010001; expected_eidx[57] = 3'd0;
        expected[58] = 7'b0101100; expected_eidx[58] = 3'd2;
        expected[59] = 7'b1010010; expected_eidx[59] = 3'd1;
        expected[60] = 7'b0101000; expected_eidx[60] = 3'd3;
        expected[61] = 7'b0101001; expected_eidx[61] = 3'd0;
        expected[62] = 7'b1010100; expected_eidx[62] = 3'd2;
        expected[63] = 7'b0101010; expected_eidx[63] = 3'd1;
    end

    initial begin
        rst_n = 0; syndrome_valid = 0; syndrome = 0;
        @(posedge clk); @(posedge clk);
        rst_n = 1;
        @(posedge clk);
        for (i = 0; i < 64; i = i + 1) begin
            syndrome = i[11:0];   // ZZ bits only; XX half stays 0
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
            $display("PASS: all %0d syndromes matched reference decoder exactly (correction + err_idx + corr_valid timing).", 64);
        else
            $display("FAIL: %0d / %0d syndromes mismatched.", errors, 64);
        $finish;
    end

endmodule
