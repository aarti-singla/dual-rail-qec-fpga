// rep3_rom_decoder.v: registered ROM decoder for the d=3 code, contents from PyMatching.
// Set NDET to match the generated rep3_decode_rom.vh (4 = single round, 8 = three rounds).
module rep3_rom_decoder #(
    parameter NDET = 4
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             syndrome_valid,
    input  wire [NDET-1:0]  syndrome,
    output reg              correction,   // predicted logical correction
    output reg              corr_valid
);
    `include "rep3_decode_rom.vh"          // defines rom_corr[] + initial load

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            correction <= 1'b0;
            corr_valid <= 1'b0;
        end else if (syndrome_valid) begin
            correction <= rom_corr[syndrome];
            corr_valid <= 1'b1;
        end else begin
            corr_valid <= 1'b0;
        end
    end
endmodule
