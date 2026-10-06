// rep3_mwpm_core.v: explicit minimum-weight matching for the d=3 syndrome graph.
// Graph: BL --q0-- D0 --q1-- D1 --q2-- BR (D0 = ZZ01, D1 = ZZ12, BL/BR boundaries).
// If both detectors fire, pairing them (flip q1, weight 1) beats the two boundary matches (q0 and q2, weight 2).
module rep3_mwpm_core (
    input  wire d0,            // ZZ01 detector
    input  wire d1,            // ZZ12 detector
    output reg  c_q0,
    output reg  c_q1,
    output reg  c_q2,
    output reg  [1:0] err_idx, // 0/1/2 data qubit, 3 = none
    output wire valid_corr
);
    // edge weights (unit lattice); written explicitly so the matching is visible
    localparam W_BND_L = 1;    // D0 -- BL  (data qubit q0)
    localparam W_PAIR  = 1;    // D0 -- D1  (data qubit q1)
    localparam W_BND_R = 1;    // D1 -- BR  (data qubit q2)

    integer w_pair, w_bnd;
    always @* begin
        c_q0 = 1'b0; c_q1 = 1'b0; c_q2 = 1'b0; err_idx = 2'd3;
        case ({d1, d0})
            2'b00: ;                                   // no fired detector
            2'b01: begin c_q0 = 1'b1; err_idx = 2'd0; end   // only D0 -> nearest boundary BL -> q0
            2'b10: begin c_q2 = 1'b1; err_idx = 2'd2; end   // only D1 -> nearest boundary BR -> q2
            2'b11: begin                                    // both fired: compare the two matchings
                w_pair = W_PAIR;                  // match D0--D1
                w_bnd  = W_BND_L + W_BND_R;       // match each to its boundary
                if (w_pair <= w_bnd) begin c_q1 = 1'b1; err_idx = 2'd1; end
                else                 begin c_q0 = 1'b1; c_q2 = 1'b1; err_idx = 2'd1; end
            end
        endcase
    end
    assign valid_corr = c_q0 | c_q1 | c_q2;
endmodule
