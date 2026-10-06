# run_impl.tcl: synthesis and implementation of the decoder with five placement directives, plus a fast-corner timing report.
# Each run writes timing_run<N>_<directive>.rpt; the other reports come from the last run.
# Usage: vivado -mode batch -source run_impl.tcl

set PART xc7a35tcsg324-2      ;# matches the paper; use xc7a35tcpg236-1 for a Basys3
set TOP  rep3_decoder_registered

read_verilog rep3_mwpm_decoder.v
read_xdc     timing_400mhz.xdc

synth_design -top $TOP -part $PART
opt_design

# ---- Multi-seed: 5 independent placement directives ----
set directives {Default Explore WLDrivenBlockPlacement EarlyBlockPlacement AltSpreadLogic_medium}
set run_num 0
foreach dir $directives {
    incr run_num
    place_design -directive $dir
    route_design
    report_timing_summary -file "timing_run${run_num}_${dir}.rpt"
    puts "============================================================"
    puts " Run $run_num ($dir) complete -> timing_run${run_num}_${dir}.rpt"
    puts "============================================================"
}

# ---- Reports from the final (last-directive) place/route result ----
report_timing_summary -file timing_summary.rpt
report_utilization    -file utilization.rpt
report_timing -delay_type max -max_paths 10 -sort_by slack -file timing_paths.rpt

# ---- Explicit Fast-process-corner check (Slow corner is the default
#      worst-case already covered by report_timing_summary above) ----
report_timing -delay_type max -corner Fast -max_paths 1 -file fast_corner_explicit.rpt

# ---- Power report (vectorless activity estimate, the standard default
#      when no SAIF/VCD switching file is supplied) ----
report_power -file power.rpt

# ---- Headline numbers to the console ----
set path [get_timing_paths -max_paths 1 -nworst 1 -setup]
if {[llength $path] > 0} {
    set wns  [get_property SLACK $path]
    set per  2.500
    set fmax [expr {1000.0 / ($per - $wns)}]
    puts "============================================================"
    puts " Target clock      : $per ns (400 MHz)"
    puts " Worst neg. slack  : $wns ns   (positive => timing CLOSED)"
    puts " Implied Fmax      : [format %.1f $fmax] MHz"
    puts " LUT / FF          : see utilization.rpt"
    puts " Power (vectorless): see power.rpt (Total On-Chip Power line)"
    puts " Multi-seed runs   : see timing_run1_*.rpt through timing_run5_*.rpt"
    puts " Fast corner       : see fast_corner_explicit.rpt"
    puts "============================================================"
} else {
    puts "============================================================"
    puts " No setup timing path found -- check that timing_400mhz.xdc"
    puts " set_input_delay/set_output_delay port names match the design"
    puts " (see rep3_mwpm_decoder.v port list)."
    puts "============================================================"
}

# Optional: prove full implementability (still no board required)
# write_bitstream -force rep3_decoder.bit
