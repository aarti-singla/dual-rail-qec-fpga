#!/usr/bin/env python3
# Stream syndrome vectors to the Basys3 over UART and check the d=3 decoder responses.
# Usage: python3 uart_host.py --port COM5 --vectors vectors/syndrome_stim_40000.csv
# Input CSV columns: s_zz01,s_zz12
import argparse
import csv
import sys
import time

try:
    import serial
except ImportError:
    print("This script requires pyserial: pip install pyserial", file=sys.stderr)
    sys.exit(1)

BAUD_RATE = 115_200


def reference_decode(s_zz01: int, s_zz12: int):
    syn = (s_zz01 << 1) | s_zz12
    mapping = {
        0b00: (0b000, 3),  # no error
        0b10: (0b001, 0),  # q0
        0b11: (0b010, 1),  # q1
        0b01: (0b100, 2),  # q2
    }
    return mapping[syn]


def load_vectors(path):
    vectors = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vectors.append((int(row["s_zz01"]), int(row["s_zz12"])))
    return vectors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="serial port, e.g. /dev/ttyUSB1 or COM5")
    ap.add_argument("--vectors", required=True, help="CSV file of syndrome vectors")
    ap.add_argument("--timeout", type=float, default=0.5, help="per-vector response timeout (s)")
    ap.add_argument("--log", default="uart_results.csv", help="output log file")
    args = ap.parse_args()

    vectors = load_vectors(args.vectors)
    print(f"Loaded {len(vectors)} syndrome vectors from {args.vectors}")

    ser = serial.Serial(args.port, BAUD_RATE, timeout=args.timeout)
    time.sleep(2.0)  # allow the board's UART/USB bridge to settle after opening the port

    mismatches = 0
    timeouts = 0
    results = []

    t_start = time.time()
    for i, (s_zz01, s_zz12) in enumerate(vectors):
        tx_byte = (s_zz01 & 0x1) | ((s_zz12 & 0x1) << 1)  # bits[3:2]=XX left as 0
        ser.write(bytes([tx_byte]))

        resp = ser.read(2)
        if len(resp) < 2:
            timeouts += 1
            results.append((s_zz01, s_zz12, None, None, None, "TIMEOUT"))
            continue

        byte0, byte1 = resp[0], resp[1]
        hw_correction = byte0 & 0x7
        hw_err_idx = (byte0 >> 3) & 0x3
        hw_valid = (byte0 >> 5) & 0x1
        hw_latency_cycles = byte1

        ref_correction, ref_err_idx = reference_decode(s_zz01, s_zz12)
        match = (hw_correction == ref_correction) and (hw_err_idx == ref_err_idx) and hw_valid

        if not match:
            mismatches += 1

        results.append((s_zz01, s_zz12, hw_correction, hw_err_idx,
                         hw_latency_cycles, "OK" if match else "MISMATCH"))

        if (i + 1) % 1000 == 0:
            elapsed = time.time() - t_start
            print(f"  {i+1}/{len(vectors)} vectors sent "
                  f"({mismatches} mismatches, {timeouts} timeouts, {elapsed:.1f}s elapsed)")

    t_total = time.time() - t_start
    ser.close()

    with open(args.log, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["s_zz01", "s_zz12", "hw_correction", "hw_err_idx",
                          "hw_latency_cycles", "status"])
        writer.writerows(results)

    print()
    print("=" * 60)
    print(f" Total vectors     : {len(vectors)}")
    print(f" Mismatches        : {mismatches}")
    print(f" Timeouts          : {timeouts}")
    print(f" Matched reference : {len(vectors) - mismatches - timeouts} / {len(vectors)}")
    print(f" Wall-clock time   : {t_total:.1f} s")
    if results and results[0][4] is not None:
        cycles = [r[4] for r in results if r[4] is not None]
        if cycles:
            print(f" Measured latency  : {min(cycles)}-{max(cycles)} cycles "
                  f"(mode: {max(set(cycles), key=cycles.count)})")
    print(f" Full log written to: {args.log}")
    print("=" * 60)

    if mismatches == 0 and timeouts == 0:
        print("All hardware responses matched the independent reference decoder.")
    else:
        print("WARNING: some responses did not match or timed out -- see log for details.")

if __name__ == "__main__":
    main()
