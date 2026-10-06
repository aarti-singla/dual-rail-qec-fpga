## timing_400mhz.xdc: 2.5 ns (400 MHz) clock plus input/output delays so report_timing_summary has port paths to analyse.
## Fmax = 1000 / (period_ns - WNS_ns) [MHz]. Update the get_ports names if the wrapper's ports change.

create_clock -period 2.500 -name clk [get_ports clk]

## Input delay: assume syndrome bits arrive up to half a clock period after
## the clock edge (a conservative, standard assumption for an external
## classical source such as the SNSPD readout chain).
set_input_delay -clock clk 1.25 [get_ports {syndrome[*] syndrome_valid}]

## Output delay: assume the downstream correction-logic block needs the
## output stable at least a quarter clock period before ITS next capturing
## edge (a standard setup-margin assumption for an external receiver).
set_output_delay -clock clk 0.625 [get_ports {correction[*] err_idx[*] corr_valid}]

## After running, report_timing_summary will show a REAL Worst Negative
## Slack (WNS) number here instead of "NA". Positive WNS = timing closed at
## 400 MHz; report that number, plus this quote:
##   Fmax = 1000 / (period_ns - WNS_ns)   [MHz]
##
## If your decoder module uses different port names (check rep3_mwpm_decoder.v
## for the actual registered wrapper's port list), update the get_ports calls
## above to match exactly -- Vivado silently ignores a constraint on a
## nonexistent port name rather than erroring, so a typo here would quietly
## produce a meaningless "NA" again.
