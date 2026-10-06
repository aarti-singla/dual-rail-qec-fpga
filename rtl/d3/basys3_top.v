`timescale 1ns/1ps
// basys3_top.v: switch/LED demonstrator for the d=3 decoder.
//   sw[1:0] = {s_zz12, s_zz01}, sw[3:2] = {s_xx12, s_xx01} (unused), btnC = issue syndrome
//   led[2:0] = correction, led[4:3] = err_idx, led[15:8] = measured decode latency (cycles)
module basys3_top (
    input  wire        clk,        // 100 MHz board clock
    input  wire        btnC,
    input  wire [3:0]  sw,
    output wire [15:0] led
);
    // --- simple synchroniser + one-shot for the button ---
    reg [2:0] btn_sync = 0;
    always @(posedge clk) btn_sync <= {btn_sync[1:0], btnC};
    wire issue = btn_sync[1] & ~btn_sync[2];   // rising edge, one cycle

    // --- decoder under test ---
    wire [2:0] correction;
    wire [1:0] err_idx;
    wire       corr_valid;
    rep3_decoder_registered dut (
        .clk(clk), .rst_n(1'b1),
        .syndrome_valid(issue), .syndrome(sw),
        .correction(correction), .err_idx(err_idx), .corr_valid(corr_valid)
    );

    // --- hardware latency counter: count clocks from issue to corr_valid ---
    reg        counting = 0;
    reg [7:0]  lat = 0, lat_latched = 0;
    always @(posedge clk) begin
        if (issue) begin counting <= 1; lat <= 0; end
        else if (counting) begin
            lat <= lat + 1;
            if (corr_valid) begin counting <= 0; lat_latched <= lat + 1; end
        end
    end

    assign led[2:0]   = correction;
    assign led[4:3]   = err_idx;
    assign led[5]     = corr_valid;
    assign led[7:6]   = 2'b00;
    assign led[15:8]  = lat_latched;   // should read 1 (single-cycle decode)
endmodule
