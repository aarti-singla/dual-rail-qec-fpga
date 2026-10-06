// Drives the registered decoder with Stim-sampled syndromes (cosim_vectors.txt) and checks each output against the closed-form table.
`timescale 1ns/1ps

module cosim_tb;
    reg clk = 0;
    reg rst_n = 0;
    reg syndrome_valid = 0;
    reg [3:0] syndrome = 0;
    wire [2:0] correction;
    wire [1:0] err_idx;
    wire corr_valid;

    rep3_decoder_registered dut (
        .clk(clk), .rst_n(rst_n), .syndrome_valid(syndrome_valid),
        .syndrome(syndrome), .correction(correction),
        .err_idx(err_idx), .corr_valid(corr_valid)
    );

    always #5 clk = ~clk;  // 10ns period, arbitrary for functional cosim

    integer fd, r, mismatches, total;
    reg [7:0] s_zz01, s_zz12, line_char;
    reg [2:0] expected_correction;

    initial begin
        rst_n = 0;
        #12 rst_n = 1;

        fd = $fopen("cosim_vectors.txt", "r");
        if (fd == 0) begin
            $display("ERROR: could not open cosim_vectors.txt");
            $finish;
        end

        mismatches = 0;
        total = 0;

        while (!$feof(fd)) begin
            r = $fscanf(fd, "%d%d\n", s_zz01, s_zz12);
            if (r != 2) begin
                // end of file or malformed line, stop
                r = 0;
            end else begin
                total = total + 1;
                syndrome = {2'b00, s_zz12[0], s_zz01[0]};  // {xx12,xx01,zz12,zz01}
                syndrome_valid = 1;
                @(posedge clk);
                @(posedge clk);  // allow registered output to settle
                syndrome_valid = 0;

                // closed-form ground truth: {c_q2,c_q1,c_q0}
                case ({s_zz01[0], s_zz12[0]})
                    2'b00: expected_correction = 3'b000;
                    2'b10: expected_correction = 3'b001;
                    2'b11: expected_correction = 3'b010;
                    2'b01: expected_correction = 3'b100;
                    default: expected_correction = 3'bxxx;
                endcase

                if (correction !== expected_correction) begin
                    mismatches = mismatches + 1;
                    $display("MISMATCH at vector %0d: s_zz01=%0d s_zz12=%0d got=%b expected=%b",
                              total, s_zz01, s_zz12, correction, expected_correction);
                end
            end
        end
        $fclose(fd);

        $display("========================================");
        $display("Co-simulation complete.");
        $display("Total real Stim-sampled vectors tested: %0d", total);
        $display("Mismatches against closed-form ground truth: %0d", mismatches);
        if (mismatches == 0)
            $display("RESULT: PASS -- RTL decoder matches ground truth on every real syndrome sample.");
        else
            $display("RESULT: FAIL -- %0d mismatches found.", mismatches);
        $display("========================================");
        $finish;
    end
endmodule
