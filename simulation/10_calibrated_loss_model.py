# Pauli approximation vs MWPM-heralded vs ML-heralded decoding for the d=3 repetition code.

import os, sys, importlib.util
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "mod04", os.path.join(HERE, "04_erasure_aware_mwpm.py"))
mod04 = importlib.util.module_from_spec(spec)
sys.modules["mod04"] = mod04
spec.loader.exec_module(mod04)


def sweep(n_points=12, n_shots=200_000):
    p_range = np.logspace(-1.5, -0.4, n_points)
    rng = np.random.default_rng(seed=42)
    pauli, mwpm_h, ml_h = [], [], []
    print(f"Calibrated 3-way comparison ({n_shots} shots/point):\n")
    print(f"{'p':>8}  {'Pauli':>10}  {'MWPM-H':>10}  {'ML-H':>10}")
    for p in p_range:
        a = mod04.simulate_vectorized(p, n_shots, "pauli",         rng)
        b = mod04.simulate_vectorized(p, n_shots, "mwpm_heralded", rng)
        c = mod04.simulate_vectorized(p, n_shots, "ml_heralded",   rng)
        pauli.append(a); mwpm_h.append(b); ml_h.append(c)
        print(f"{p:8.4f}  {a:10.5f}  {b:10.5f}  {c:10.5f}")
    return p_range, np.array(pauli), np.array(mwpm_h), np.array(ml_h)


def plot(p, pauli, mwpm_h, ml_h, fname="calibrated_loss_comparison.pdf"):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    p_an = np.logspace(np.log10(p[0]) - 0.3, np.log10(p[-1]) + 0.1, 200)
    ax1.loglog(p_an, mod04.pL_pauli_analytic(p_an), "-", color="#888780",
               alpha=0.45, label="Pauli analytic")
    ax1.loglog(p, pauli, "o", color="#888780", ms=6, label="Pauli")
    ax1.loglog(p_an, mod04.pL_mwpm_heralded_analytic(p_an), "-",
               color="#1D9E75", alpha=0.45, label="MWPM-heralded analytic")
    ax1.loglog(p, np.maximum(mwpm_h, 1e-7), "s", color="#1D9E75", ms=6,
               label="MWPM-heralded")
    ax1.loglog(p_an, mod04.pL_ml_heralded_analytic(p_an), "-",
               color="#A02060", alpha=0.45, label="ML-heralded analytic")
    ax1.loglog(p, np.maximum(ml_h, 1e-7), "D", color="#A02060", ms=6,
               label="ML-heralded (NEW)")
    ax1.loglog(p_an, p_an, "k--", alpha=0.4, label="No QEC")
    ax1.set_xlabel(r"Physical error rate $p$")
    ax1.set_ylabel(r"Logical error rate $p_L$")
    ax1.set_title("(a) Three-decoder comparison")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    g_mwpm = pauli / np.maximum(mwpm_h, 1.0 / 200_000)
    g_ml   = pauli / np.maximum(ml_h,   1.0 / 200_000)
    ax2.loglog(p, g_mwpm, "s-", color="#1D9E75", lw=1.6, ms=5,
               label="MWPM-heralded vs Pauli")
    ax2.loglog(p, g_ml,   "D-", color="#A02060", lw=1.8, ms=6,
               label="ML-heralded vs Pauli")
    ax2.axhline(1.0, color="gray", ls=":", alpha=0.6)
    ax2.set_xlabel(r"Physical error rate $p$")
    ax2.set_ylabel("Gain over Pauli baseline")
    ax2.set_title("(b) Heralding advantage")
    ax2.legend(fontsize=9); ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"\n[OK] saved {fname}")

if __name__ == "__main__":
    p, pauli, mwpm_h, ml_h = sweep(n_points=12, n_shots=200_000)
    plot(p, pauli, mwpm_h, ml_h)
    np.savez("calibrated_loss_data.npz",
             p=p, pauli=pauli, mwpm_h=mwpm_h, ml_h=ml_h)
    print("[OK] saved calibrated_loss_data.npz")