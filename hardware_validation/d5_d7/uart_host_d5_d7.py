#!/usr/bin/env python3
"""Stream syndrome vectors to the Basys3 over UART and check the d=5/d=7 decoder responses.

Vector file columns: syndrome_hex correction_hex err_idx_dec source_rate
Example: python3 uart_host_d5_d7.py --distance 5 --port COM5 --vectors vectors/hw_test_d5.txt --log d5_results.csv
"""
import argparse
import sys
import time

try:
    import serial
except ImportError:
    print("Missing dependency. Install with: pip install pyserial", file=sys.stderr)
    sys.exit(1)


def load_vectors(path, n_syn_bits, n_corr_bits):
    vectors = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            syn_hex, corr_hex, eidx_dec, rate = line.split()
            vectors.append({
                "syndrome": int(syn_hex, 16),
                "correction": int(corr_hex, 16),
                "err_idx": int(eidx_dec),
                "rate": rate,
            })
    return vectors


def send_syndrome(ser, distance, syndrome):
    if distance == 5:
        ser.write(bytes([syndrome & 0xFF]))
    elif distance == 7:
        ser.write(bytes([syndrome & 0xFF, (syndrome >> 8) & 0x0F]))
    else:
        raise ValueError("distance must be 5 or 7")


def run(args):
    n_syn_bits = 2 * (args.distance - 1)
    n_corr_bits = args.distance

    vectors = load_vectors(args.vectors, n_syn_bits, n_corr_bits)
    print(f"Loaded {len(vectors)} vectors from {args.vectors} (d={args.distance})")

    ser = serial.Serial(args.port, baudrate=115200, timeout=args.timeout)
    time.sleep(2.0)  # let the USB-UART bridge and any board reset settle
    ser.reset_input_buffer()

    mismatches = 0
    timeouts = 0
    results = []

    t_start = time.time()
    for i, v in enumerate(vectors):
        send_syndrome(ser, args.distance, v["syndrome"])

        resp = ser.read(3)
        if len(resp) < 3:
            timeouts += 1
            results.append((i, v, None, None, None, "TIMEOUT"))
            if args.verbose:
                print(f"[{i}] syndrome={v['syndrome']:#x} -> TIMEOUT "
                      f"(got {len(resp)}/3 bytes)")
            continue

        byte0, byte1, byte2 = resp[0], resp[1], resp[2]
        corr_valid = (byte0 >> 7) & 1
        got_correction = byte0 & ((1 << n_corr_bits) - 1)
        got_err_idx = byte1 & 0x07
        got_latency = byte2

        ok = (corr_valid == 1
              and got_correction == v["correction"]
              and got_err_idx == v["err_idx"])

        if not ok:
            mismatches += 1
            results.append((i, v, got_correction, got_err_idx, got_latency, "MISMATCH"))
            if args.verbose or mismatches <= 20:
                print(f"[{i}] syndrome={v['syndrome']:#x} "
                      f"expected correction={v['correction']:#x} err_idx={v['err_idx']} "
                      f"got correction={got_correction:#x} err_idx={got_err_idx} "
                      f"corr_valid={corr_valid}  <-- MISMATCH")
        else:
            results.append((i, v, got_correction, got_err_idx, got_latency, "OK"))

        if (i + 1) % 1000 == 0:
            elapsed = time.time() - t_start
            print(f"  {i+1}/{len(vectors)} vectors, "
                  f"{mismatches} mismatches, {timeouts} timeouts, "
                  f"{elapsed:.1f}s elapsed")

    ser.close()
    elapsed = time.time() - t_start

    print()
    print("=" * 60)
    print(f"Distance d={args.distance}")
    print(f"Total vectors:  {len(vectors)}")
    print(f"Mismatches:     {mismatches}")
    print(f"Timeouts:       {timeouts}")
    print(f"Elapsed:        {elapsed:.1f}s ({elapsed/len(vectors)*1000:.2f} ms/vector)")
    if mismatches == 0 and timeouts == 0:
        print("RESULT: PASS -- all vectors matched, zero mismatches, zero timeouts.")
    else:
        print("RESULT: FAIL -- see mismatches/timeouts above.")
    print("=" * 60)

    if args.log:
        with open(args.log, "w") as f:
            f.write("index,syndrome,expected_correction,expected_err_idx,"
                    "got_correction,got_err_idx,got_latency,status\n")
            for i, v, gc, ge, gl, status in results:
                f.write(f"{i},{v['syndrome']:#x},{v['correction']:#x},{v['err_idx']},"
                        f"{'' if gc is None else hex(gc)},{ge if ge is not None else ''},"
                        f"{gl if gl is not None else ''},{status}\n")
        print(f"Per-vector log written to {args.log}")

    return 0 if (mismatches == 0 and timeouts == 0) else 1

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--distance", type=int, required=True, choices=[5, 7],
                   help="Code distance (5 or 7)")
    p.add_argument("--port", required=True,
                   help="Serial port, e.g. COM5 (Windows) or /dev/ttyUSB1 (Linux)")
    p.add_argument("--vectors", required=True,
                   help="Path to hw_test_d5.txt or hw_test_d7.txt")
    p.add_argument("--timeout", type=float, default=0.5,
                   help="Per-vector read timeout in seconds (default 0.5)")
    p.add_argument("--log", default=None,
                   help="Optional CSV path for a full per-vector log")
    p.add_argument("--verbose", action="store_true",
                   help="Print every vector, not just mismatches")
    args = p.parse_args()
    sys.exit(run(args))
