// rep7_mwpm_decoder.v: d=7 repetition-code decoder (bit-flip syndrome, single round).
// Same interface as rep3_mwpm_decoder. Table-driven, generated from PyMatching
// and checked exhaustively against it.
module rep7_mwpm_decoder (
    input  wire s_zz01,   // ZZ01 stabiliser bit (bit-flip syndrome)
    input  wire s_zz12,   // ZZ12 stabiliser bit (bit-flip syndrome)
    input  wire s_zz23,   // ZZ23 stabiliser bit (bit-flip syndrome)
    input  wire s_zz34,   // ZZ34 stabiliser bit (bit-flip syndrome)
    input  wire s_zz45,   // ZZ45 stabiliser bit (bit-flip syndrome)
    input  wire s_zz56,   // ZZ56 stabiliser bit (bit-flip syndrome)
    input  wire s_xx01,   // phase - carried for completeness, unused for bit-flip
    input  wire s_xx12,   // phase - carried for completeness, unused for bit-flip
    input  wire s_xx23,   // phase - carried for completeness, unused for bit-flip
    input  wire s_xx34,   // phase - carried for completeness, unused for bit-flip
    input  wire s_xx45,   // phase - carried for completeness, unused for bit-flip
    input  wire s_xx56,   // phase - carried for completeness, unused for bit-flip
    output wire c_q0,  // correction: flip q0
    output wire c_q1,  // correction: flip q1
    output wire c_q2,  // correction: flip q2
    output wire c_q3,  // correction: flip q3
    output wire c_q4,  // correction: flip q4
    output wire c_q5,  // correction: flip q5
    output wire c_q6,  // correction: flip q6
    output wire [2:0] err_idx,  // 0..6 = data qubit; 7 = no error
    output wire valid_corr      // a non-trivial correction is asserted
);
    // table-driven minimum-weight matching, verified exhaustively against
    // PyMatching over all 64 syndromes
    reg [6:0] corr_r;
    always @(*) begin
        case ({s_zz56,s_zz45,s_zz34,s_zz23,s_zz12,s_zz01})
            6'd0: corr_r = 7'b0000000;
            6'd1: corr_r = 7'b0000001;
            6'd2: corr_r = 7'b0000011;
            6'd3: corr_r = 7'b0000010;
            6'd4: corr_r = 7'b0000111;
            6'd5: corr_r = 7'b0000110;
            6'd6: corr_r = 7'b0000100;
            6'd7: corr_r = 7'b0000101;
            6'd8: corr_r = 7'b1110000;
            6'd9: corr_r = 7'b0001110;
            6'd10: corr_r = 7'b0001100;
            6'd11: corr_r = 7'b0001101;
            6'd12: corr_r = 7'b0001000;
            6'd13: corr_r = 7'b0001001;
            6'd14: corr_r = 7'b0001011;
            6'd15: corr_r = 7'b0001010;
            6'd16: corr_r = 7'b1100000;
            6'd17: corr_r = 7'b1100001;
            6'd18: corr_r = 7'b0011100;
            6'd19: corr_r = 7'b1100010;
            6'd20: corr_r = 7'b0011000;
            6'd21: corr_r = 7'b0011001;
            6'd22: corr_r = 7'b1100100;
            6'd23: corr_r = 7'b0011010;
            6'd24: corr_r = 7'b0010000;
            6'd25: corr_r = 7'b0010001;
            6'd26: corr_r = 7'b0010011;
            6'd27: corr_r = 7'b0010010;
            6'd28: corr_r = 7'b1101000;
            6'd29: corr_r = 7'b0010110;
            6'd30: corr_r = 7'b0010100;
            6'd31: corr_r = 7'b0010101;
            6'd32: corr_r = 7'b1000000;
            6'd33: corr_r = 7'b1000001;
            6'd34: corr_r = 7'b1000011;
            6'd35: corr_r = 7'b1000010;
            6'd36: corr_r = 7'b0111000;
            6'd37: corr_r = 7'b1000110;
            6'd38: corr_r = 7'b1000100;
            6'd39: corr_r = 7'b1000101;
            6'd40: corr_r = 7'b0110000;
            6'd41: corr_r = 7'b0110001;
            6'd42: corr_r = 7'b1001100;
            6'd43: corr_r = 7'b0110010;
            6'd44: corr_r = 7'b1001000;
            6'd45: corr_r = 7'b1001001;
            6'd46: corr_r = 7'b0110100;
            6'd47: corr_r = 7'b1001010;
            6'd48: corr_r = 7'b0100000;
            6'd49: corr_r = 7'b0100001;
            6'd50: corr_r = 7'b0100011;
            6'd51: corr_r = 7'b0100010;
            6'd52: corr_r = 7'b1011000;
            6'd53: corr_r = 7'b0100110;
            6'd54: corr_r = 7'b0100100;
            6'd55: corr_r = 7'b0100101;
            6'd56: corr_r = 7'b1010000;
            6'd57: corr_r = 7'b1010001;
            6'd58: corr_r = 7'b0101100;
            6'd59: corr_r = 7'b1010010;
            6'd60: corr_r = 7'b0101000;
            6'd61: corr_r = 7'b0101001;
            6'd62: corr_r = 7'b1010100;
            6'd63: corr_r = 7'b0101010;
            default: corr_r = 7'b0;
        endcase
    end

    assign c_q0 = corr_r[0];
    assign c_q1 = corr_r[1];
    assign c_q2 = corr_r[2];
    assign c_q3 = corr_r[3];
    assign c_q4 = corr_r[4];
    assign c_q5 = corr_r[5];
    assign c_q6 = corr_r[6];

    assign valid_corr = |corr_r;

    // error index for logical-readout bookkeeping (7 = no detected error)
    // lowest-index qubit wins priority, matching rep3_mwpm_decoder's
    // c_q0 ? ... : c_q1 ? ... ternary-chain convention
    reg [2:0] eidx_r;
    integer k;
    always @(*) begin
        eidx_r = 3'd7;
        for (k = 6; k >= 0; k = k - 1)
            if (corr_r[k]) eidx_r = k[2:0];
    end
    assign err_idx = eidx_r;

    // XX bits intentionally unused for bit-flip correction (structural only)
    wire _unused = s_xx01 | s_xx12 | s_xx23 | s_xx34 | s_xx45 | s_xx56;
endmodule

//  Registered wrapper: syndrome latched in, correction latched out,
//  with a one-cycle ready/valid handshake. Measured decode latency is
//  exactly the number of clocks between syndrome_valid and corr_valid.
//  Matches rep3_decoder_registered's exact interface convention.
module rep7_decoder_registered (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        syndrome_valid,
    input  wire [11:0]  syndrome,        // {s_xx56,s_xx45,s_xx34,s_xx23,s_xx12,s_xx01,s_zz56,s_zz45,s_zz34,s_zz23,s_zz12,s_zz01}
    output reg  [6:0]  correction,      // {c_q6,c_q5,c_q4,c_q3,c_q2,c_q1,c_q0}
    output reg  [2:0]  err_idx,
    output reg         corr_valid
);
    wire [6:0] c;
    wire [2:0] eidx;
    wire vc;

    rep7_mwpm_decoder u_core (
        .s_zz01(syndrome[0]),
        .s_zz12(syndrome[1]),
        .s_zz23(syndrome[2]),
        .s_zz34(syndrome[3]),
        .s_zz45(syndrome[4]),
        .s_zz56(syndrome[5]),
        .s_xx01(syndrome[6]),
        .s_xx12(syndrome[7]),
        .s_xx23(syndrome[8]),
        .s_xx34(syndrome[9]),
        .s_xx45(syndrome[10]),
        .s_xx56(syndrome[11]),
        .c_q0(c[0]),
        .c_q1(c[1]),
        .c_q2(c[2]),
        .c_q3(c[3]),
        .c_q4(c[4]),
        .c_q5(c[5]),
        .c_q6(c[6]),
        .err_idx(eidx), .valid_corr(vc)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            correction <= 7'b0;
            err_idx    <= 3'd7;
            corr_valid <= 1'b0;
        end else if (syndrome_valid) begin
            correction <= c;
            err_idx    <= eidx;
            corr_valid <= 1'b1;        // result available 1 clock after syndrome_valid
        end else begin
            corr_valid <= 1'b0;
        end
    end
endmodule
