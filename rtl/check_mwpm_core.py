#!/usr/bin/env python3
# Checks the case tables in rep5/rep7_mwpm_decoder.v against brute-force
# minimum-weight decoding of the bit-flip repetition code.
import re, sys, itertools

def table(d):
    src = open(f"rtl/d5_d7/rtl/rep{d}_mwpm_decoder.v").read()
    rows = re.findall(r"\d+'d(\d+):\s*corr_r\s*=\s*\d+'b([01]+);", src)
    return {int(k): v for k, v in rows}

def syndrome(err, d):
    return sum((((err >> i) ^ (err >> (i + 1))) & 1) << i for i in range(d - 1))

def check(d):
    t = table(d)
    assert len(t) == 1 << (d - 1), f"d={d}: {len(t)} entries"
    best = {}
    for e in range(1 << d):
        s = syndrome(e, d)
        w = bin(e).count("1")
        best[s] = min(best.get(s, d + 1), w)
    for s, bits in t.items():
        e = int(bits, 2)               # string is MSB-first: q(d-1)..q0
        assert syndrome(e, d) == s, f"d={d} syn {s}: wrong syndrome"
        assert bin(e).count("1") == best[s], f"d={d} syn {s}: not minimum weight"
    print(f"d={d}: {len(t)} syndromes OK (valid and minimum weight)")

if __name__ == "__main__":
    for d in (5, 7):
        check(d)
