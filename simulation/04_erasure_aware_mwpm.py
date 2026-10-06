# d=3 repetition code with erasure noise: standard MWPM vs erasure-aware MWPM vs ML decoding.

import math
import numpy as np
import matplotlib.pyplot as plt

# Decoders
def standard_mwpm_d3(s01: int, s12: int) -> np.ndarray:
    if s01 == 0 and s12 == 0: return np.array([0, 0, 0], dtype=int)
    if s01 == 1 and s12 == 0: return np.array([1, 0, 0], dtype=int)
    if s01 == 0 and s12 == 1: return np.array([0, 0, 1], dtype=int)
    return np.array([0, 1, 0], dtype=int)


def erasure_aware_mwpm_d3(s01: int, s12: int,
                          heralds: np.ndarray) -> np.ndarray:
    """MWPM-style with heralding: min flips subject to herald respect."""
    best, best_w = np.array([0, 0, 0], dtype=int), float("inf")
    for x0 in (0, 1):
        for x1 in (0, 1):
            for x2 in (0, 1):
                if (x0 ^ x1) != s01: continue
                if (x1 ^ x2) != s12: continue
                w = 0
                for q, x in enumerate((x0, x1, x2)):
                    if x:
                        w += 1 if heralds[q] else 1000
                if w < best_w:
                    best_w = w
                    best = np.array([x0, x1, x2], dtype=int)
    return best


def erasure_aware_ml_d3(s01: int, s12: int,
                        heralds: np.ndarray,
                        p_flip: float = 2.0 / 3.0) -> np.ndarray:
    """Maximum-likelihood decoder under heralded depolarising erasure."""
    w_h1 = -math.log(p_flip)         # ~0.405 for p_flip=2/3
    w_h0 = -math.log(1.0 - p_flip)   # ~1.099 for p_flip=2/3

    best, best_w = np.array([0, 0, 0], dtype=int), float("inf")
    for x0 in (0, 1):
        for x1 in (0, 1):
            for x2 in (0, 1):
                if (x0 ^ x1) != s01: continue
                if (x1 ^ x2) != s12: continue
                w = 0.0
                valid = True
                for q, x in enumerate((x0, x1, x2)):
                    if heralds[q] == 0:
                        if x == 1:
                            valid = False
                            break
                    else:
                        w += w_h1 if x == 1 else w_h0
                if not valid: continue
                if w < best_w:
                    best_w = w
                    best = np.array([x0, x1, x2], dtype=int)
    return best

# Monte Carlo simulation (vectorized noise sampling)
def simulate_vectorized(p: float, n_shots: int, decoder: str,
                        rng: np.random.Generator) -> float:
    erasures = (rng.random((n_shots, 3)) < p).astype(int)
    pauli_choice = rng.integers(0, 3, size=(n_shots, 3))   # 0=X, 1=Y, 2=Z
    x_flip_given_erasure = (pauli_choice != 2).astype(int)
    x_flips = erasures * x_flip_given_erasure

    s01 = x_flips[:, 0] ^ x_flips[:, 1]
    s12 = x_flips[:, 1] ^ x_flips[:, 2]

    n_errors = 0
    for i in range(n_shots):
        if decoder == "pauli":
            correction = standard_mwpm_d3(int(s01[i]), int(s12[i]))
        elif decoder == "mwpm_heralded":
            correction = erasure_aware_mwpm_d3(int(s01[i]), int(s12[i]),
                                                erasures[i])
        elif decoder == "ml_heralded":
            correction = erasure_aware_ml_d3(int(s01[i]), int(s12[i]),
                                              erasures[i])
        else:
            raise ValueError(decoder)
        residual = x_flips[i] ^ correction
        if int(residual.sum()) >= 2:
            n_errors += 1
    return n_errors / n_shots

# Analytical predictions
def pL_pauli_analytic(p):
    """3 * p_X^2 * (1-p_X) + p_X^3  where p_X = 2p/3."""
    pX = 2.0 * p / 3.0
    return 3 * pX ** 2 * (1 - pX) + pX ** 3


def pL_mwpm_heralded_analytic(p):
    """3-erasure failures: 1 weight-3 (8/27) + 3 weight-2 mis-IDs (12/27)."""
    return p ** 3 * 20.0 / 27.0


def pL_ml_heralded_analytic(p):
    """3-erasure ML failures: decoder picks higher-probability pattern."""
    return p ** 3 * 7.0 / 27.0

# Sweep & plot
def compare_all_decoders(n_shots: int = 200_000, n_points: int = 12):
    p_range = np.logspace(-1.5, -0.4, n_points)
    rng = np.random.default_rng(seed=42)
    results = {"pauli": [], "mwpm_heralded": [], "ml_heralded": []}

    print(f"d=3 single-round, depolarising erasure, {n_shots} shots/point\n")
    print(f"{'p':>8}  {'Pauli':>10}  {'MWPM-H':>10}  {'ML-H':>10}  "
          f"{'gMWPM':>7}  {'gML':>7}")
    for p in p_range:
        for d in results.keys():
            results[d].append(simulate_vectorized(p, n_shots, d, rng))
        a, b, c = results["pauli"][-1], results["mwpm_heralded"][-1], \
                  results["ml_heralded"][-1]
        gMWPM = a / max(b, 1.0 / n_shots)
        gML   = a / max(c, 1.0 / n_shots)
        print(f"{p:8.4f}  {a:10.5f}  {b:10.5f}  {c:10.5f}  "
              f"{gMWPM:6.1f}x  {gML:6.1f}x")

    return p_range, {k: np.array(v) for k, v in results.items()}


def plot_three_way(p, results, fname="decoder_comparison.pdf"):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    p_an = np.logspace(np.log10(p[0]) - 0.3, np.log10(p[-1]) + 0.1, 200)

    # panel (a): all three decoders + analytical
    ax1.loglog(p_an, pL_pauli_analytic(p_an), "-", color="#888780",
               alpha=0.45, lw=1, label="Pauli analytic")
    ax1.loglog(p, results["pauli"], "o", color="#888780", ms=6,
               label="Standard MWPM (baseline)")
    ax1.loglog(p_an, pL_mwpm_heralded_analytic(p_an), "-", color="#1D9E75",
               alpha=0.45, lw=1, label="MWPM-heralded analytic")
    ax1.loglog(p, np.maximum(results["mwpm_heralded"], 1e-7), "s",
               color="#1D9E75", ms=6, label="MWPM-heralded")
    ax1.loglog(p_an, pL_ml_heralded_analytic(p_an), "-", color="#A02060",
               alpha=0.45, lw=1, label="ML-heralded analytic")
    ax1.loglog(p, np.maximum(results["ml_heralded"], 1e-7), "D",
               color="#A02060", ms=6, label="ML-heralded (NEW)")
    ax1.loglog(p_an, p_an, "k--", alpha=0.3, label="No QEC")
    ax1.set_xlabel(r"Physical error rate $p$")
    ax1.set_ylabel(r"Logical error rate $p_L$")
    ax1.set_title("(a) Three decoders compared (d=3, 1 round)")
    ax1.legend(loc="lower right", fontsize=8); ax1.grid(alpha=0.3)

    # panel (b): gain factors
    gain_mwpm = results["pauli"] / np.maximum(results["mwpm_heralded"],
                                              1.0 / 200_000)
    gain_ml   = results["pauli"] / np.maximum(results["ml_heralded"],
                                              1.0 / 200_000)
    ax2.loglog(p, gain_mwpm, "s-", color="#1D9E75", lw=1.6, ms=5,
               label="MWPM-heralded vs Pauli")
    ax2.loglog(p, gain_ml,   "D-", color="#A02060", lw=1.8, ms=6,
               label="ML-heralded vs Pauli")
    ax2.loglog(p, gain_ml / gain_mwpm, ":", color="black", lw=1.2,
               label="ML / MWPM (extra gain from ML)")
    ax2.axhline(1.0, color="gray", ls="--", alpha=0.5)
    ax2.axhline(20.0 / 7.0, color="red", ls=":", alpha=0.5,
                label=r"ML/MWPM asymptote 20/7 $\approx$ 2.86")
    ax2.set_xlabel(r"Physical error rate $p$")
    ax2.set_ylabel("Gain factor over Pauli")
    ax2.set_title("(b) Decoder advantage")
    ax2.legend(loc="upper right", fontsize=8); ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"\n[OK] saved {fname}")

if __name__ == "__main__":
    p_range, results = compare_all_decoders(n_shots=200_000)
    plot_three_way(p_range, results)
    np.savez("decoder_comparison_data.npz",
             p=p_range, **results,
             pauli_analytic=pL_pauli_analytic(p_range),
             mwpm_heralded_analytic=pL_mwpm_heralded_analytic(p_range),
             ml_heralded_analytic=pL_ml_heralded_analytic(p_range))
    print("[OK] saved decoder_comparison_data.npz")

    g_mwpm = results["pauli"] / np.maximum(results["mwpm_heralded"], 1/200_000)
    g_ml   = results["pauli"] / np.maximum(results["ml_heralded"],   1/200_000)
    print(f"\nMean gain over Pauli baseline:")
    print(f"  MWPM-heralded: {g_mwpm.mean():.1f}x")
    print(f"  ML-heralded:   {g_ml.mean():.1f}x")
    print(f"  ML gives an extra {(g_ml/g_mwpm).mean():.2f}x over MWPM-heralded "
          f"(asymptotic limit: 20/7 ~ 2.86x)")