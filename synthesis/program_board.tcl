# program_board.tcl: program the built bitstream onto a connected Basys3. Usage: vivado -mode batch -source program_board.tcl

set PROJ_DIR "./basys3_decoder_proj"
set PROJ_NAME "basys3_decoder_proj"
set BITSTREAM "${PROJ_DIR}/${PROJ_NAME}.runs/impl_1/basys3_top.bit"

if {![file exists $BITSTREAM]} {
    puts "ERROR: bitstream not found at $BITSTREAM"
    puts "Run build_basys3_project.tcl first."
    exit 1
}

open_hw_manager
connect_hw_server
open_hw_target

set device [lindex [get_hw_devices] 0]
puts "Found hardware device: $device"

set_property PROGRAM.FILE $BITSTREAM $device
program_hw_devices $device

puts "============================================================"
puts " Programming complete."
puts " sw[1:0] sets the syndrome bits, btnC issues it,"
puts " led[2:0] shows the correction, led[15:8] shows the"
puts " measured decode latency in clock cycles."
puts "============================================================"
