# Dual-rail photonic repetition code: simulation, decoder RTL and Basys3 validation

Code behind "Error Correction and Feedforward Timing in a Simulated Dual-Rail Photonic Architecture".

Tools: Stim 1.16, PyMatching 2.4, Vivado 2025.2, Yosys 0.33 (Nangate 45 nm), Icarus Verilog.

## Layout
- `simulation/`: Stim/PyMatching scripts (thresholds, noise models, HOM visibility, loss budget, timing and area) and their result tables
- `rtl/d3/`: d=3 decoder, UART interface and testbenches
- `rtl/d5_d7/`: d=5 and d=7 decoders, UART top levels and testbenches
- `rtl/`: lookup-table (ROM) decoders and their generators
- `hardware_validation/`: host scripts, 40,000 test vectors per distance, d=5/7 board results, Vivado reports for d=3/5/7
- `synthesis/`: Vivado and Yosys scripts, constraints
- `figures/`: figure scripts

## Usage
```
pip install -r requirements.txt
make sim                      # all RTL testbenches (needs iverilog)
python3 rtl/gen_decode_rom.py 1               # regenerate the d=3 ROM
python3 rtl/gen_decode_rom_scaling.py 5       # d=5 (or 7)
```
Board test (Basys3 programmed with `basys3_uart_top*.v`):
```
python3 hardware_validation/d3/uart_host.py --port COM5 --vectors hardware_validation/d3/vectors/syndrome_stim_40000.csv
python3 hardware_validation/d5_d7/uart_host_d5_d7.py --distance 5 --port COM5 --vectors hardware_validation/d5_d7/vectors/hw_test_d5.txt
```
For d=5/7, `synthesis/build_basys3_uart_project.tcl` builds the d=3 design; to build another distance, change `TOP` and the source list to the `basys3_uart_top_d5`/`_d7` files and the matching decoder (same `basys3_uart.xdc`).

`cosim_tb.v` reads `cosim_vectors.txt` from the working directory (`hardware_validation/d3/vectors/`).

## Not included
- Not every number in the paper has been re-derived from a fresh run. Checked against a fresh run: the finite-size-scaling threshold (`17_finite_size_scaling.py`: p_th = 0.1944, paper 0.194) and the ceil(d/2) suppression slopes (`07`, about 1.9/2.9/4.0; the paper quotes 1.82/2.86/3.98 from a different fit window). The erasure-decoder gain in `04` varies by sampled point (about 2.8x to 3.8x); the paper's 2.74x at finite error rate is not reproduced exactly by that script. Scripts `02`-`10` and `12`-`15` otherwise run to completion. `12_code_family_comparison.py` leaves the Steane code out.
