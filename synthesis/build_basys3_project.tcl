# build_basys3_project.tcl: create the Vivado project for basys3_top, run synthesis and implementation, write the bitstream.
# Needs basys3_top.v, rep3_mwpm_decoder.v and basys3_decoder.xdc in the working folder.
# Usage: vivado -mode batch -source build_basys3_project.tcl

set PROJ_NAME "basys3_decoder_proj"
set PROJ_DIR  "./basys3_decoder_proj"
set PART      "xc7a35tcpg236-1"    ;# actual Basys3 part (not the csg324 part used for the paper's main synthesis)
set TOP       "basys3_top"

# ---- Create the project (deletes and recreates if it already exists) ----
if {[file exists $PROJ_DIR]} {
    puts "Removing existing project directory: $PROJ_DIR"
    file delete -force $PROJ_DIR
}
create_project $PROJ_NAME $PROJ_DIR -part $PART -force

# ---- Add RTL sources ----
add_files -norecurse {basys3_top.v rep3_mwpm_decoder.v}

# ---- Add the constraint file ----
add_files -fileset constrs_1 -norecurse {basys3_decoder.xdc}

# ---- Set the top module explicitly ----
set_property top $TOP [current_fileset]

update_compile_order -fileset sources_1

# ---- Run synthesis ----
puts "============================================================"
puts " Running synthesis..."
puts "============================================================"
launch_runs synth_1 -jobs 4
wait_on_run synth_1

if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
    puts "ERROR: synthesis did not complete. Check synth_1 run for errors."
    exit 1
}

# ---- Run implementation (place + route) ----
puts "============================================================"
puts " Running implementation (place and route)..."
puts "============================================================"
launch_runs impl_1 -jobs 4
wait_on_run impl_1

if {[get_property PROGRESS [get_runs impl_1]] != "100%"} {
    puts "ERROR: implementation did not complete. Check impl_1 run for errors."
    exit 1
}

# ---- Generate the bitstream ----
puts "============================================================"
puts " Generating bitstream..."
puts "============================================================"
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1

# ---- Report timing and utilisation for the record ----
open_run impl_1
report_timing_summary -file "${PROJ_DIR}/${PROJ_NAME}.runs/impl_1/post_impl_timing_summary.rpt"
report_utilization     -file "${PROJ_DIR}/${PROJ_NAME}.runs/impl_1/post_impl_utilization.rpt"

puts "============================================================"
puts " DONE."
puts " Bitstream : ${PROJ_DIR}/${PROJ_NAME}.runs/impl_1/${TOP}.bit"
puts " Next step : Hardware Manager -> Open Target -> Program Device"
puts "             (or: open_hw_manager; connect_hw_server; open_hw_target;"
puts "              program_hw_devices; from this same Tcl console)"
puts "============================================================"
