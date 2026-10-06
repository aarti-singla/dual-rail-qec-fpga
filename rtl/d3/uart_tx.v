`timescale 1ns/1ps
// =====================================================================
//  uart_tx.v -- standard 8N1 UART transmitter
//  Parameterised for a 100 MHz system clock and configurable baud rate.
// =====================================================================
module uart_tx #(
    parameter CLK_FREQ  = 100_000_000,
    parameter BAUD_RATE = 115_200
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data,
    input  wire        send,        // pulse high for one cycle to start a send
    output reg         tx = 1'b1,   // serial output pin (board's RsTx); idle high
    output reg         busy = 1'b0
);
    localparam integer CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

    localparam IDLE  = 2'd0;
    localparam START = 2'd1;
    localparam DATA  = 2'd2;
    localparam STOP  = 2'd3;

    reg [1:0]  state = IDLE;
    reg [15:0] clk_count = 0;
    reg [2:0]  bit_index = 0;
    reg [7:0]  tx_shift = 0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            tx <= 1'b1;
            busy <= 1'b0;
            clk_count <= 0;
            bit_index <= 0;
        end else begin
            case (state)
                IDLE: begin
                    tx <= 1'b1;
                    if (send) begin
                        busy <= 1'b1;
                        tx_shift <= data;
                        clk_count <= 0;
                        state <= START;
                    end else begin
                        busy <= 1'b0;
                    end
                end

                START: begin
                    tx <= 1'b0;  // start bit
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        clk_count <= 0;
                        bit_index <= 0;
                        state <= DATA;
                    end
                end

                DATA: begin
                    tx <= tx_shift[bit_index];
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        clk_count <= 0;
                        if (bit_index < 7) begin
                            bit_index <= bit_index + 1;
                        end else begin
                            state <= STOP;
                        end
                    end
                end

                STOP: begin
                    tx <= 1'b1;  // stop bit
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        clk_count <= 0;
                        busy <= 1'b0;
                        state <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end
endmodule
