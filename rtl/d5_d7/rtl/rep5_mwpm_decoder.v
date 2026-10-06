// rep5_mwpm_decoder.v: d=5 repetition-code decoder (bit-flip syndrome, single round).
// Same interface as rep3_mwpm_decoder. Table-driven, generated from PyMatching
// and checked exhaustively against it.
module rep5_mwpm_decoder (
    input  wire s_zz01,   // ZZ01 stabiliser bit (bit-flip syndrome)
    input  wire s_zz12,   // ZZ12 stabiliser bit (bit-flip syndrome)
    input  wire s_zz23,   // ZZ23 stabiliser bit (bit-flip syndrome)
    input  wire s_zz34,   // ZZ34 stabiliser bit (bit-flip syndrome)
    input  wire s_xx01,   // phase - carried for completeness, unused for bit-flip
    input  wire s_xx12,   // phase - carried for completeness, unused for bit-flip
    input  wire s_xx23,   // phase - carried for completeness, unused for bit-flip
    input  wire s_xx34,   // phase - carried for completeness, unused for bit-flip
    output wire c_q0,  // correction: flip q0
    output wire c_q1,  // correction: flip q1
    output wire c_q2,  // correction: flip q2
    output wire c_q3,  // correction: flip q3
    output wire c_q4,  // correction: flip q4
    output wire [2:0] err_idx,  // 0..4 = data qubit; 5 = no error
    output wire valid_corr      // a non-trivial correction is asserted
);
    // table-driven minimum-weight matching, verified exhaustively against
    // PyMatching over all 16 syndromes
    reg [4:0] corr_r;
    always @(*) begin
        case ({s_zz34,s_zz23,s_zz12,s_zz01})
            4'd0: corr_r = 5'b00000;
            4'd1: corr_r = 5'b00001;
            4'd2: corr_r = 5'b00011;
            4'd3: corr_r = 5'b00010;
            4'd4: corr_r = 5'b11000;
            4'd5: corr_r = 5'b00110;
            4'd6: corr_r = 5'b00100;
            4'd7: corr_r = 5'b00101;
            4'd8: corr_r = 5'b10000;
            4'd9: corr_r = 5'b10001;
            4'd10: corr_r = 5'b01100;
            4'd11: corr_r = 5'b10010;
            4'd12: corr_r = 5'b01000;
            4'd13: corr_r = 5'b01001;
            4'd14: corr_r = 5'b10100;
            4'd15: corr_r = 5'b01010;
            default: corr_r = 5'b0;
        endcase
    end

    assign c_q0 = corr_r[0];
    assign c_q1 = corr_r[1];
    assign c_q2 = corr_r[2];
    assign c_q3 = corr_r[3];
    assign c_q4 = corr_r[4];

    assign valid_corr = |corr_r;

    // error index for logical-readout bookkeeping (5 = no detected error)
    // lowest-index qubit wins priority, matching rep3_mwpm_decoder's
    // c_q0 ? ... : c_q1 ? ... ternary-chain convention
    reg [2:0] eidx_r;
    integer k;
    always @(*) begin
        eidx_r = 3'd5;
        for (k = 4; k >= 0; k = k - 1)
            if (corr_r[k]) eidx_r = k[2:0];
    end
    assign err_idx = eidx_r;

    // XX bits intentionally unused for bit-flip correction (structural only)
    wire _unused = s_xx01 | s_xx12 | s_xx23 | s_xx34;
endmodule

//  Registered wrapper: syndrome latched in, correction latched out,
//  with a one-cycle ready/valid handshake. Measured decode latency is
//  exactly the number of clocks between syndrome_valid and corr_valid.
//  Matches rep3_decoder_registered's exact interface convention.
module rep5_decoder_registered (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        syndrome_valid,
    input  wire [7:0]  syndrome,        // {s_xx34,s_xx23,s_xx12,s_xx01,s_zz34,s_zz23,s_zz12,s_zz01}
    output reg  [4:0]  correction,      // {c_q4,c_q3,c_q2,c_q1,c_q0}
    output reg  [2:0]  err_idx,
    output reg         corr_valid
);
    wire [4:0] c;
    wire [2:0] eidx;
    wire vc;

    rep5_mwpm_decoder u_core (
        .s_zz01(syndrome[0]),
        .s_zz12(syndrome[1]),
        .s_zz23(syndrome[2]),
        .s_zz34(syndrome[3]),
        .s_xx01(syndrome[4]),
        .s_xx12(syndrome[5]),
        .s_xx23(syndrome[6]),
        .s_xx34(syndrome[7]),
        .c_q0(c[0]),
        .c_q1(c[1]),
        .c_q2(c[2]),
        .c_q3(c[3]),
        .c_q4(c[4]),
        .err_idx(eidx), .valid_corr(vc)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            correction <= 5'b0;
            err_idx    <= 3'd5;
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
