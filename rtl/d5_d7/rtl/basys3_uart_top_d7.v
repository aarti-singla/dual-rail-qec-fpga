`timescale 1ns/1ps
// basys3_uart_top_d7.v: UART hardware test top level for the d=7 decoder (8N1, 115200).
// Host -> board: 2 bytes per vector
//   byte 0: syndrome[7:0]; byte 1: syndrome[11:8] in bits[3:0]
//   (syndrome[5:0] = ZZ bits, syndrome[11:6] = XX bits, sent as 0)
// Board -> host: 3 bytes per vector
//   byte 0: bit7 = corr_valid, bits[6:0] = correction
//   byte 1: bits[2:0] = err_idx
//   byte 2: decode latency in clock cycles (syndrome_valid to corr_valid)
module basys3_uart_top_d7 (
    input  wire clk,        // 100 MHz board clock
    input  wire RsRx,       // USB-UART bridge, host -> board
    output wire RsTx,       // USB-UART bridge, board -> host
    output wire [15:0] led  // led[6:0] = last syndrome (low 7b), led[7]=heartbeat,
                             // led[15:8]=running vector count (low byte)
);
    wire rst_n = 1'b1;

    // ---- UART receiver: two bytes per incoming test vector ----
    wire [7:0] rx_data;
    wire       rx_valid;
    uart_rx #(.CLK_FREQ(100_000_000), .BAUD_RATE(115_200)) u_rx (
        .clk(clk), .rst_n(rst_n), .rx(RsRx),
        .data(rx_data), .data_valid(rx_valid)
    );

    // ---- RX byte assembler: byte 0 = syndrome[7:0], byte 1 = syndrome[11:8] ----
    reg        rx_byte_toggle = 1'b0;   // 0 = expecting byte0, 1 = expecting byte1
    reg [7:0]  syndrome_lo = 0;
    reg [11:0] syndrome_r = 0;
    reg        syndrome_valid_r = 0;

    always @(posedge clk) begin
        syndrome_valid_r <= 1'b0;   // default; pulses for exactly one cycle below
        if (rx_valid) begin
            if (!rx_byte_toggle) begin
                syndrome_lo    <= rx_data;
                rx_byte_toggle <= 1'b1;
            end else begin
                syndrome_r        <= {rx_data[3:0], syndrome_lo};
                syndrome_valid_r  <= 1'b1;   // full 12-bit syndrome now assembled
                rx_byte_toggle    <= 1'b0;
            end
        end
    end

    // ---- Decoder under test ----
    wire [6:0] correction;
    wire [2:0] err_idx;
    wire       corr_valid;

    rep7_decoder_registered dut (
        .clk(clk), .rst_n(rst_n),
        .syndrome_valid(syndrome_valid_r), .syndrome(syndrome_r),
        .correction(correction), .err_idx(err_idx), .corr_valid(corr_valid)
    );

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

    // ---- Response packer: three bytes queued after each corr_valid ----
    reg [7:0] resp_byte0, resp_byte1, resp_byte2;
    reg       corr_valid_d = 1'b0;

    wire tx_busy;
    reg  [7:0] tx_data;
    reg        tx_send;

    // 3-byte send sequencer, extending basys3_uart_top.v's 2-byte pattern
    localparam TX_IDLE  = 4'd0, TX_SEND0 = 4'd1, TX_WAIT0_UP = 4'd2,
               TX_WAIT0_DN = 4'd3, TX_SEND1 = 4'd4, TX_WAIT1_UP = 4'd5,
               TX_WAIT1_DN = 4'd6, TX_SEND2 = 4'd7, TX_WAIT2_UP = 4'd8,
               TX_WAIT2_DN = 4'd9;
    reg [3:0] tx_state = TX_IDLE;

    always @(posedge clk) begin
        corr_valid_d <= corr_valid;
        tx_send <= 1'b0;

        // latch a response the cycle corr_valid rises
        if (corr_valid && !corr_valid_d) begin
            resp_byte0 <= {corr_valid, correction};
            resp_byte1 <= {5'b0, err_idx};
            resp_byte2 <= lat_latched;
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
                if (!tx_busy) tx_state <= TX_SEND2;
            end
            TX_SEND2: begin
                tx_data <= resp_byte2;
                tx_send <= 1'b1;
                tx_state <= TX_WAIT2_UP;
            end
            TX_WAIT2_UP: begin
                if (tx_busy) tx_state <= TX_WAIT2_DN;
            end
            TX_WAIT2_DN: begin
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
        if (syndrome_valid_r) vec_count <= vec_count + 1;
    end

    reg heartbeat = 1'b0;
    reg [23:0] hb_div = 0;
    always @(posedge clk) begin
        hb_div <= hb_div + 1;
        if (hb_div == 0) heartbeat <= ~heartbeat;
    end

    assign led[6:0]  = syndrome_r[6:0];
    assign led[7]    = heartbeat;
    assign led[15:8] = vec_count;

endmodule
