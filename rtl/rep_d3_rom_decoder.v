// rep_d3_rom_decoder.v: ROM decoder, d=3, single round (4 detectors, 16 entries). Table from PyMatching.
module rep_d3_rom_decoder (
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          syndrome_valid,
    input  wire [3:0]                    syndrome,
    output reg                           correction,
    output reg                           corr_valid
);
    `include "rep_d3_decode_rom.vh"

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            correction <= 1'b0;
            corr_valid <= 1'b0;
        end else if (syndrome_valid) begin
            correction <= rom_corr_d3[syndrome];
            corr_valid <= 1'b1;
        end else begin
            corr_valid <= 1'b0;
        end
    end
endmodule
