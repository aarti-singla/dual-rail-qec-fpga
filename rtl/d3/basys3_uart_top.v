`timescale 1ns/1ps
// =====================================================================
//  basys3_uart_top.v -- UART-streamed hardware validation of the d=3
//  repetition decoder. Replaces manual switch input with automatic,
//  host-driven syndrome streaming so a full Stim-generated test-vector
//  set (e.g. the existing 40,000-sample co-simulation set) can be
//  driven through the real decoder on real hardware without manual
//  switch-flipping.
//
//  Protocol (8N1, 115200 baud, matches uart_host.py):
//    Host -> board : 1 byte per test vector.
//                    bits[3:0] = syndrome {s_xx12, s_xx01, s_zz12, s_zz01}
//                    bits[7:4] = don't care (sent as 0 by the host script)
//    Board -> host : 2 bytes per response, sent after decoding completes.
//                    byte 0: bits[2:0]=correction, bits[4:3]=err_idx,
//                            bit[5]=corr_valid, bits[7:6]=0
//                    byte 1: measured decode latency in clock cycles
//                            (cycles from syndrome_valid to corr_valid)
// =====================================================================
module basys3_uart_top (
    input  wire clk,        // 100 MHz board clock
    input  wire RsRx,       // USB-UART bridge, host -> board
    output wire RsTx,       // USB-UART bridge, board -> host
    output wire [15:0] led  // led[1:0] = last syndrome, led[2]=heartbeat,
                             // led[7:3]=0, led[15:8]=running vector count (low byte)
);
    wire rst_n = 1'b1;

    // ---- UART receiver: one byte per incoming test vector ----
    wire [7:0] rx_data;
    wire       rx_valid;
    uart_rx #(.CLK_FREQ(100_000_000), .BAUD_RATE(115_200)) u_rx (
        .clk(clk), .rst_n(rst_n), .rx(RsRx),
        .data(rx_data), .data_valid(rx_valid)
    );

    // ---- Decoder under test ----
    reg  [3:0] syndrome_r = 0;
    reg        syndrome_valid_r = 0;
    wire [2:0] correction;
    wire [1:0] err_idx;
    wire       corr_valid;

    rep3_decoder_registered dut (
        .clk(clk), .rst_n(rst_n),
        .syndrome_valid(syndrome_valid_r), .syndrome(syndrome_r),
        .correction(correction), .err_idx(err_idx), .corr_valid(corr_valid)
    );

    // one-cycle pulse to feed the decoder exactly when a new byte lands
    always @(posedge clk) begin
        syndrome_valid_r <= rx_valid;
        if (rx_valid) syndrome_r <= rx_data[3:0];
    end

    // ---- Latency counter: cycles from syndrome_valid_r to corr_valid ----
    reg        counting = 1'b0;
    reg [7:0]  lat = 0, lat_latched = 0;
    always @(posedge clk) begin
        if (syndrome_valid_r) begin
            counting <= 1'b1;
            lat <= 0;
        end else if (counting) begin
            lat <= lat + 1;
            if (corr_valid) begin
                counting <= 1'b0;
                lat_latched <= lat + 1;
            end
        end
    end

    // ---- Response packer: two bytes queued after each corr_valid ----
    reg [7:0] resp_byte0, resp_byte1;
    reg       send_byte0 = 1'b0, send_byte1 = 1'b0;
    reg       corr_valid_d = 1'b0;

    wire tx_busy;
    reg  [7:0] tx_data;
    reg        tx_send;

    // simple 2-byte send sequencer
    localparam TX_IDLE  = 3'd0, TX_SEND0 = 3'd1, TX_WAIT0_UP = 3'd2,
               TX_WAIT0_DN = 3'd3, TX_SEND1 = 3'd4, TX_WAIT1_UP = 3'd5,
               TX_WAIT1_DN = 3'd6;
    reg [2:0] tx_state = TX_IDLE;

    always @(posedge clk) begin
        corr_valid_d <= corr_valid;
        tx_send <= 1'b0;

        // latch a response the cycle corr_valid rises
        if (corr_valid && !corr_valid_d) begin
            resp_byte0 <= {2'b00, corr_valid, err_idx, correction};
            resp_byte1 <= lat_latched;
        end

        case (tx_state)
            TX_IDLE: begin
                if (corr_valid && !corr_valid_d) tx_state <= TX_SEND0;
            end
            TX_SEND0: begin
                tx_data <= resp_byte0;
                tx_send <= 1'b1;
                tx_state <= TX_WAIT0_UP;
            end
            TX_WAIT0_UP: begin
                // wait for uart_tx to actually register busy before
                // watching for it to fall, avoiding a false-early exit
                if (tx_busy) tx_state <= TX_WAIT0_DN;
            end
            TX_WAIT0_DN: begin
                if (!tx_busy) tx_state <= TX_SEND1;
            end
            TX_SEND1: begin
                tx_data <= resp_byte1;
                tx_send <= 1'b1;
                tx_state <= TX_WAIT1_UP;
            end
            TX_WAIT1_UP: begin
                if (tx_busy) tx_state <= TX_WAIT1_DN;
            end
            TX_WAIT1_DN: begin
                if (!tx_busy) tx_state <= TX_IDLE;
            end
            default: tx_state <= TX_IDLE;
        endcase
    end

    uart_tx #(.CLK_FREQ(100_000_000), .BAUD_RATE(115_200)) u_tx (
        .clk(clk), .rst_n(rst_n),
        .data(tx_data), .send(tx_send),
        .tx(RsTx), .busy(tx_busy)
    );

    // ---- Vector counter and status on LEDs ----
    reg [7:0] vec_count = 0;
    always @(posedge clk) begin
        if (rx_valid) vec_count <= vec_count + 1;
    end

    reg heartbeat = 1'b0;
    reg [23:0] hb_div = 0;
    always @(posedge clk) begin
        hb_div <= hb_div + 1;
        if (hb_div == 0) heartbeat <= ~heartbeat;
    end

    assign led[3:0]  = syndrome_r;
    assign led[4]    = heartbeat;
    assign led[7:5]  = 3'b0;
    assign led[15:8] = vec_count;

endmodule
