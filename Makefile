IV = iverilog -I rtl
VP = vvp
D3 = rtl/d3
.PHONY: all sim table equiv roundtrip rom_sim cores d5 d7 impl clean
all: sim
sim: table equiv roundtrip rom_sim cores d5 d7
table:     ; $(IV) -o b_table $(D3)/rep3_mwpm_decoder.v $(D3)/tb_rep3_decoder.v && $(VP) b_table
equiv:     ; $(IV) -o b_equiv $(D3)/rep3_mwpm_core.v $(D3)/rep3_mwpm_decoder.v $(D3)/tb_equiv.v && $(VP) b_equiv
roundtrip: ; $(IV) -o b_rt $(D3)/rep3_mwpm_core.v $(D3)/tb_rep3_roundtrip.v && $(VP) b_rt
cores:     ; python3 rtl/check_mwpm_core.py
rom_sim:   ; $(IV) -o b_rom $(D3)/rep3_rom_decoder.v $(D3)/tb_rep3_rom.v && $(VP) b_rom
d5:        ; $(IV) -o b_d5 rtl/d5_d7/rtl/rep5_mwpm_decoder.v rtl/d5_d7/tb/tb_rep5_decoder_registered.v && $(VP) b_d5
d7:        ; $(IV) -o b_d7 rtl/d5_d7/rtl/rep7_mwpm_decoder.v rtl/d5_d7/tb/tb_rep7_decoder_registered.v && $(VP) b_d7
impl:      ; vivado -mode batch -source synthesis/run_impl.tcl   # needs Vivado
clean:     ; rm -f b_* *.vcd
