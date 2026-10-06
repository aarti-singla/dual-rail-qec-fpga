# Decoder comparison utility (MWPM and alternatives).

import os, sys, importlib.util
import numpy as np
import matplotlib.pyplot as plt
import stim
import pymatching

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "mod04", os.path.join(HERE, "04_erasure_aware_mwpm.py"))
mod04 = importlib.util.module_from_spec(spec)
sys.modules["mod04"] = mod04
spec.loader.exec_module(mod04)

# PANEL A -- circuit-level depolarising-Pauli channel (Stim), 2-term noise
def repetition_circuit(d: int, p: float, rounds: int) -> stim.Circuit:
    """2-term repetition memory: data depolarisation + measurement flip."""
    return stim.Circuit.generated(
        "repetition_code:memory",
        rounds=rounds, distance=d,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p / 2,
        after_clifford_depolarization=0.0,
    )


def _mwpm_rate(circuit: stim.Circuit, n_shots: int, seed: int) -> float:
    sampler = circuit.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(n_shots, separate_observables=True)
    dem = circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
        ignore_decomposition_failures=False,   # raise, never silently drop
    )
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pred = matcher.decode_batch(det)
    return float(np.mean(np.any(pred != obs, axis=1)))


def mwpm_full_logical_rate(d: int, p: float, n_shots: int, seed: int) -> float:
    """Full space-time decoding: d rounds, all temporal information."""
    return _mwpm_rate(repetition_circuit(d, p, rounds=d), n_shots, seed)

# PANEL B -- erasure channel (script 04), d=3 single round
def erasure_logical_rate(p: float, decoder: str, n_shots: int,
                         seed: int) -> float:
    rng = np.random.default_rng(seed)
    return mod04.simulate_vectorized(p, n_shots, decoder, rng)

# leading-order analytics on the erasure channel (p = erasure rate)
def erasure_pauli_analytic(p):        return mod04.pL_pauli_analytic(p)
def erasure_mwpm_h_analytic(p):       return mod04.pL_mwpm_heralded_analytic(p)
def erasure_ml_h_analytic(p):         return mod04.pL_ml_heralded_analytic(p)

# FPGA resource estimates (illustrative; arithmetic only)
def fpga_resource_estimate(d: int, decoder: str) -> dict:
    n_syn = d - 1
    if decoder == "MWPM-LUT-spacetime":
        lut = min(2 ** (n_syn * d), 65536)
        ff = 8 * d * d
        latency_ns = 5 + 4 * d
    elif decoder == "MWPM-LUT-singleround":
        lut = min(2 ** n_syn, 1024)
        ff = 4 * d
        latency_ns = 5 + 2 * d
    elif decoder == "ML-LUT":                         # + d herald bits
        lut = min(2 ** (n_syn + d), 4096)
        ff = 4 * d
        latency_ns = 5 + 2 * d
    else:
        lut = ff = latency_ns = 0
    return dict(decoder=decoder, d=d, LUT=lut, FF=ff, latency_ns=latency_ns)

# Sweeps
def sweep_panelA(distances=(3, 5), n_points: int = 10, n_shots: int = 200_000,
                 base_seed: int = 1600):
    p_range = np.logspace(-2.0, -0.7, n_points)
    rates = {d: [] for d in distances}
    seeds = {d: [] for d in distances}
    print(f"\n[PANEL A] circuit-level Pauli, full space-time, 2-term noise, "
          f"{n_shots} shots/pt")
    header = f"  {'p_nom':>9}{'p_eff(2p/3)':>13}"
    for d in distances:
        header += f"{'d=' + str(d):>11}"
    print(header)
    for i, p in enumerate(p_range):
        row = f"  {p:9.4f}{2*p/3:13.4f}"
        for j, d in enumerate(distances):
            sd = base_seed + 100 * d + i
            r = mwpm_full_logical_rate(d, p, n_shots, sd)
            rates[d].append(r); seeds[d].append(sd)
            row += f"{r:11.5f}"
        print(row)
    rates = {d: np.array(v) for d, v in rates.items()}
    seeds = {d: np.array(v, dtype=int) for d, v in seeds.items()}
    return p_range, rates, seeds


def sweep_panelB(n_points: int = 12, n_shots: int = 200_000,
                 base_seed: int = 1700):
    """Erasure channel: Pauli vs MWPM-heralded vs ML-heralded (d=3)."""
    p_range = np.logspace(-1.5, -0.4, n_points)
    pauli, mwpm_h, ml_h, seeds = [], [], [], []
    print(f"\n[PANEL B] erasure channel, d=3 single round, "
          f"{n_shots} shots/pt")
    print(f"  {'p_eras':>9}{'p_effX(2p/3)':>14}{'Pauli':>11}{'MWPM-H':>11}"
          f"{'ML-H':>11}{'ML/MWPM-H':>11}")
    for i, p in enumerate(p_range):
        s0, s1, s2 = base_seed + 3 * i, base_seed + 3 * i + 1, base_seed + 3 * i + 2
        a = erasure_logical_rate(p, "pauli", n_shots, s0)
        b = erasure_logical_rate(p, "mwpm_heralded", n_shots, s1)
        c = erasure_logical_rate(p, "ml_heralded", n_shots, s2)
        pauli.append(a); mwpm_h.append(b); ml_h.append(c)
        seeds.append((s0, s1, s2))
        g = b / c if c > 0 else float("nan")   # ML-H is the smaller -> >1
        print(f"  {p:9.4f}{2*p/3:14.4f}{a:11.5f}{b:11.6f}{c:11.6f}{g:11.2f}")
    return (p_range, np.array(pauli), np.array(mwpm_h), np.array(ml_h),
            np.array(seeds, dtype=int))

# Plot (two clearly separated panels; the two channels are NEVER overlaid)
def plot(pA, ratesA, pB, pauli, mwpm_h, ml_h,
         fname="decoder_information_depth.pdf"):
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 5.5))

    # ---- Panel A: circuit-level Pauli, full space-time, distance scaling ----
    colors = {3: "#1D9E75", 5: "#534AB7", 7: "#A02060"}
    for d in sorted(ratesA):
        axA.loglog(pA, np.maximum(ratesA[d], 1e-7), "o-",
                   color=colors.get(d, "#444"), lw=1.7, ms=5,
                   label=f"MWPM full space-time, d={d}")
    axA.loglog(pA, pA, "k:", alpha=0.4, label="No QEC")
    axA.set_xlabel(r"Physical error rate $p$ (nominal; $p_{\rm eff}=2p/3$)")
    axA.set_ylabel(r"Logical error rate $p_L$")
    axA.set_title("(A) Circuit-level Pauli (Stim), 2-term noise\n"
                  "distance scaling reference (full space-time MWPM)")
    axA.legend(fontsize=8); axA.grid(alpha=0.3)

    # ---- Panel B: erasure channel ----
    p_an = np.logspace(np.log10(pB[0]) - 0.2, np.log10(pB[-1]) + 0.1, 200)
    axB.loglog(p_an, erasure_pauli_analytic(p_an), "-", color="#888780",
               alpha=0.45, lw=1)
    axB.loglog(pB, pauli, "o", color="#888780", ms=6,
               label="Pauli-MWPM (no herald)")
    axB.loglog(p_an, erasure_mwpm_h_analytic(p_an), "-", color="#1D9E75",
               alpha=0.45, lw=1)
    axB.loglog(pB, np.maximum(mwpm_h, 1e-7), "s", color="#1D9E75", ms=6,
               label="MWPM-heralded")
    axB.loglog(p_an, erasure_ml_h_analytic(p_an), "-", color="#A02060",
               alpha=0.45, lw=1)
    axB.loglog(pB, np.maximum(ml_h, 1e-7), "D", color="#A02060", ms=6,
               label="ML-heralded (NEW)")
    axB.set_xlabel(r"Erasure rate $p$ (effective X-flip $=2p/3$)")
    axB.set_ylabel(r"Logical error rate $p_L$")
    axB.set_title("(B) Erasure channel (script 04), d=3\n"
                  r"ML-H / MWPM-H $\to$ 20/7 $\approx$ 2.86$\times$")
    axB.legend(fontsize=8); axB.grid(alpha=0.3)

    fig.suptitle("Decoder comparison -- two channels shown SEPARATELY; "
                 "axes are NOT comparable and must not be cross-quoted",
                 fontsize=9)
    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"\n[OK] saved {fname}")

if __name__ == "__main__":
    print("FPGA resource estimates (Artix-7; illustrative):")
    print(f"{'decoder':<28}{'d':<4}{'LUT':>8}{'FF':>8}{'latency':>12}")
    for d in (3, 5):
        for dec in ("MWPM-LUT-spacetime", "MWPM-LUT-singleround", "ML-LUT"):
            r = fpga_resource_estimate(d, dec)
            print(f"{r['decoder']:<28}{r['d']:<4}{r['LUT']:>8}{r['FF']:>8}"
                  f"{r['latency_ns']:>9} ns")
    print("\nNote: d=3 ML-LUT = 2^(2 syndrome + 3 herald) = 32 entries.")

    pA, ratesA, seedsA = sweep_panelA(distances=(3, 5), n_shots=200_000)
    pB, pauli, mwpm_h, ml_h, seedsB = sweep_panelB(n_shots=200_000)

    plot(pA, ratesA, pB, pauli, mwpm_h, ml_h)

    np.savez("decoder_information_depth.npz",
             # panel A (circuit-level Pauli, 2-term, full space-time)
             pA=pA, full_d3=ratesA[3], full_d5=ratesA[5],
             seedsA_d3=seedsA[3], seedsA_d5=seedsA[5],
             # panel B (erasure channel)
             pB=pB, erasure_pauli=pauli, erasure_mwpm_h=mwpm_h,
             erasure_ml_h=ml_h, seedsB=seedsB,
             # analytics
             erasure_pauli_analytic=erasure_pauli_analytic(pB),
             erasure_mwpm_h_analytic=erasure_mwpm_h_analytic(pB),
             erasure_ml_h_analytic=erasure_ml_h_analytic(pB))
    print("[OK] saved decoder_information_depth.npz")

    print("\n--- SELF-CHECKS ---")

    # Panel A: in the sub-threshold window (p_eff <= ~0.045, i.e. threshold/3
    # with rep threshold ~0.14 eff), larger distance must suppress pL below
    # smaller distance. Restrict to points where d=3 has >= 20 events.
    p_eff = 2 * pA / 3
    sub = (p_eff <= 0.045) & (ratesA[3] * 200_000 >= 20)
    if np.any(sub):
        okA = np.all(ratesA[5][sub] <= ratesA[3][sub])
    else:
        okA = False
    print(f"[{'PASS' if okA else 'FAIL'}] Panel A: d=5 pL <= d=3 pL in the "
          f"sub-threshold window (distance suppression), "
          f"{int(np.sum(sub))} pts checked")

    # Panel B: 2.86x is ML-heralded vs MWPM-HERALDED in the asymptotic tail.
    tail = slice(0, max(1, len(pB) // 3))   # smallest-p third
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = mwpm_h[tail] / np.where(ml_h[tail] > 0, ml_h[tail], np.nan)
    mean_ratio = np.nanmean(ratio)
    okB = np.isfinite(mean_ratio) and 2.0 <= mean_ratio <= 3.6
    print(f"[{'PASS' if okB else 'FAIL'}] Panel B: ML-H / MWPM-H -> "
          f"{mean_ratio:.2f}x  (asymptote 20/7 = {20/7:.2f}); "
          f"target band [2.0, 3.6]")

    print("\nREMINDER: Panels A and B are DIFFERENT noise channels. Do NOT "
          "quote 'ML beats circuit-level MWPM by 2.86x' -- the 2.86x is the "
          "ML-heralded/MWPM-heralded ratio on the erasure channel (Panel B), "
          "both O(p^3). Panel A is a circuit-level Pauli distance-scaling "
          "reference (full space-time MWPM) with NO ML curve.")
