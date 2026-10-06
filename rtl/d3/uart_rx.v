`timescale 1ns/1ps
// =====================================================================
//  uart_rx.v -- standard 8N1 UART receiver
//  Parameterised for a 100 MHz system clock and configurable baud rate.
// =====================================================================
module uart_rx #(
    parameter CLK_FREQ  = 100_000_000,
    parameter BAUD_RATE = 115_200
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx,          // serial input pin (board's RsRx)
    output reg  [7:0] data,
    output reg        data_valid   // single-cycle pulse when a byte is ready
);
    localparam integer CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

    localparam IDLE  = 3'd0;
    localparam START = 3'd1;
    localparam DATA  = 3'd2;
    localparam STOP  = 3'd3;

    reg [2:0]  state = IDLE;
    reg [15:0] clk_count = 0;
    reg [2:0]  bit_index = 0;
    reg [7:0]  rx_shift = 0;

    // two-stage synchroniser for the async serial input
    reg rx_meta = 1'b1, rx_sync = 1'b1;
    always @(posedge clk) begin
        rx_meta <= rx;
        rx_sync <= rx_meta;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            clk_count <= 0;
            bit_index <= 0;
            data_valid <= 1'b0;
        end else begin
            data_valid <= 1'b0;
            case (state)
                IDLE: begin
                    clk_count <= 0;
                    bit_index <= 0;
                    if (rx_sync == 1'b0) state <= START;  // falling edge = start bit
                end

                START: begin
                    // sample at the middle of the start bit to confirm it's real
                    if (clk_count == (CLKS_PER_BIT/2)) begin
                        if (rx_sync == 1'b0) begin
                            clk_count <= 0;
                            state <= DATA;
                        end else begin
                            state <= IDLE;  // false start (glitch)
                        end
                    end else begin
                        clk_count <= clk_count + 1;
                    end
                end

                DATA: begin
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        clk_count <= 0;
                        rx_shift[bit_index] <= rx_sync;
                        if (bit_index < 7) begin
                            bit_index <= bit_index + 1;
                        end else begin
                            bit_index <= 0;
                            state <= STOP;
                        end
                    end
                end

                STOP: begin
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        clk_count <= 0;
                        data <= rx_shift;
                        data_valid <= 1'b1;
                        state <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end
endmodule
