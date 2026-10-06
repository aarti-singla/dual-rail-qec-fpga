`timescale 1ns/1ps
// End-to-end test of basys3_uart_top_d5 using the real uart_rx.v / uart_tx.v.
// Bytes go onto RsRx with 8N1 timing (868 clocks/bit); RsTx is decoded by a second uart_rx.
module tb_basys3_uart_top_d5_real;
    localparam integer CLKS_PER_BIT = 868;
    localparam real    BIT_TIME_NS  = 8680.0;   // CLKS_PER_BIT * 10ns

    reg clk = 0;
    reg RsRx = 1'b1;   // idle high, matches uart_rx's start-bit-on-falling-edge
    wire RsTx;
    wire [15:0] led;
    integer errors = 0;

    basys3_uart_top_d5 dut (
        .clk(clk), .RsRx(RsRx), .RsTx(RsTx), .led(led)
    );

    always #5 clk = ~clk;

    // ---- host-side receiver: a second real uart_rx decoding RsTx ----
    wire [7:0] host_rx_data;
    wire       host_rx_valid;
    uart_rx #(.CLK_FREQ(100_000_000), .BAUD_RATE(115_200)) host_rx (
        .clk(clk), .rst_n(1'b1), .rx(RsTx),
        .data(host_rx_data), .data_valid(host_rx_valid)
    );

    reg [7:0] captured [0:63];
    integer   n_captured = 0;
    always @(posedge clk) begin
        if (host_rx_valid) begin
            captured[n_captured] = host_rx_data;
            n_captured = n_captured + 1;
        end
    end

    // ---- bit-bang one byte onto RsRx with real 8N1 timing ----
    task send_byte(input [7:0] b);
        integer k;
        begin
            RsRx = 1'b0;                 // start bit
            #(BIT_TIME_NS);
            for (k = 0; k < 8; k = k + 1) begin
                RsRx = b[k];              // LSB first
                #(BIT_TIME_NS);
            end
            RsRx = 1'b1;                  // stop bit
            #(BIT_TIME_NS);
        end
    endtask

    localparam NVEC = 6;
    reg [7:0] test_syndrome [0:NVEC-1];
    reg [4:0] test_correction [0:NVEC-1];
    reg [2:0] test_err_idx [0:NVEC-1];

    initial begin
        test_syndrome[0]=8'h0c; test_correction[0]=5'h08; test_err_idx[0]=3'd3;
        test_syndrome[1]=8'h01; test_correction[1]=5'h01; test_err_idx[1]=3'd0;
        test_syndrome[2]=8'h08; test_correction[2]=5'h10; test_err_idx[2]=3'd4;
        test_syndrome[3]=8'h03; test_correction[3]=5'h02; test_err_idx[3]=3'd1;
        test_syndrome[4]=8'h06; test_correction[4]=5'h04; test_err_idx[4]=3'd2;
        test_syndrome[5]=8'h02; test_correction[5]=5'h03; test_err_idx[5]=3'd0;
    end

    integer i;
    reg [7:0] got_byte0, got_byte1, got_byte2;

    initial begin
        #10_000_000;   // 10ms watchdog -- generous for real serial timing
        $display("WATCHDOG TIMEOUT at n_captured=%0d", n_captured);
        $finish;
    end

    initial begin
        repeat (5) @(posedge clk);

        for (i = 0; i < NVEC; i = i + 1) begin
            send_byte(test_syndrome[i]);

            wait (n_captured >= 3 * (i + 1));
            wait (dut.tx_state == 0);

            got_byte0 = captured[3*i + 0];
            got_byte1 = captured[3*i + 1];
            got_byte2 = captured[3*i + 2];

            if (got_byte0[4:0] !== test_correction[i]) begin
                errors = errors + 1;
                $display("MISMATCH vec %0d: correction got=%b expected=%b",
                          i, got_byte0[4:0], test_correction[i]);
            end
            if (!got_byte0[7]) begin
                errors = errors + 1;
                $display("MISMATCH vec %0d: corr_valid bit not set", i);
            end
            if (got_byte1[2:0] !== test_err_idx[i]) begin
                errors = errors + 1;
                $display("MISMATCH vec %0d: err_idx got=%0d expected=%0d",
                          i, got_byte1[2:0], test_err_idx[i]);
            end
            $display("vec %0d: syndrome=%h -> correction=%b err_idx=%0d latency_byte=%0d",
                      i, test_syndrome[i], got_byte0[4:0], got_byte1[2:0], got_byte2);
        end

        if (errors == 0)
            $display("PASS: all %0d vectors matched over REAL bit-level UART (rx.v + tx.v, not stubs).", NVEC);
        else
            $display("FAIL: %0d mismatches.", errors);
        $finish;
    end
endmodule
