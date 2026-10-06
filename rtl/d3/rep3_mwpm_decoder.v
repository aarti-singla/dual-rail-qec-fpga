// =====================================================================
//  rep3_mwpm_decoder.v
//  Minimum-weight matching decoder for the distance-3 dual-rail
//  repetition code (bit-flip / Z-basis syndrome), single round.
//
//  Syndrome graph: 4 nodes, 6 edges.  For d=3 the minimum-weight perfect
//  matching has a closed combinational form (the syndrome-to-error table
//  in the paper): the matching that pairs each flipped stabiliser to the
//  unique minimum-weight data-qubit support.
//
//    s_zz01 s_zz12 | corrected data qubit
//      0      0    | none
//      1      0    | q0
//      1      1    | q1
//      0      1    | q2
//
//  The core is purely combinational (resolves sub-ns); a registered
//  wrapper below gives a deterministic, measurable single-cycle latency.
// =====================================================================
module rep3_mwpm_decoder (
    input  wire s_zz01,   // ZZ01 stabiliser bit (bit-flip syndrome)
    input  wire s_zz12,   // ZZ12 stabiliser bit
    input  wire s_xx01,   // XX01 (phase) - carried for completeness, unused for bit-flip
    input  wire s_xx12,   // XX12 (phase) - carried for completeness, unused for bit-flip
    output wire c_q0,     // correction: flip q0
    output wire c_q1,     // correction: flip q1
    output wire c_q2,     // correction: flip q2
    output wire [1:0] err_idx,  // 0,1,2 = data qubit; 3 = no error
    output wire valid_corr      // a non-trivial correction is asserted
);
    // minimum-weight matching, closed form for d=3
    assign c_q0 =  s_zz01 & ~s_zz12;
    assign c_q1 =  s_zz01 &  s_zz12;
    assign c_q2 = ~s_zz01 &  s_zz12;

    assign valid_corr = c_q0 | c_q1 | c_q2;

    // error index for logical-readout bookkeeping (3 = no detected error)
    assign err_idx = c_q0 ? 2'd0 :
                     c_q1 ? 2'd1 :
                     c_q2 ? 2'd2 : 2'd3;

    // XX bits intentionally unused for bit-flip correction (structural only)
    wire _unused = s_xx01 | s_xx12;
endmodule


// ---------------------------------------------------------------------
//  Registered wrapper: syndrome latched in, correction latched out,
//  with a one-cycle ready/valid handshake.  Measured decode latency is
//  exactly the number of clocks between syndrome_valid and corr_valid.
// ---------------------------------------------------------------------
module rep3_decoder_registered (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        syndrome_valid,
    input  wire [3:0]  syndrome,        // {s_xx12, s_xx01, s_zz12, s_zz01}
    output reg  [2:0]  correction,      // {c_q2, c_q1, c_q0}
    output reg  [1:0]  err_idx,
    output reg         corr_valid
);
    wire c0, c1, c2, vc;
    wire [1:0] eidx;

    rep3_mwpm_decoder u_core (
        .s_zz01(syndrome[0]), .s_zz12(syndrome[1]),
        .s_xx01(syndrome[2]), .s_xx12(syndrome[3]),
        .c_q0(c0), .c_q1(c1), .c_q2(c2),
        .err_idx(eidx), .valid_corr(vc)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            correction <= 3'b000;
            err_idx    <= 2'd3;
            corr_valid <= 1'b0;
        end else if (syndrome_valid) begin
            correction <= {c2, c1, c0};
            err_idx    <= eidx;
            corr_valid <= 1'b1;        // result available 1 clock after syndrome_valid
        end else begin
            corr_valid <= 1'b0;
        end
    end
endmodule
