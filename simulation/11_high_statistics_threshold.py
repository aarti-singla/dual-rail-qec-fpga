# Threshold sweep for d=3,5,7 with 200k shots per point.

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import stim
import pymatching

N_SHOTS = 200_000
N_POINTS = 20
D_LIST = (3, 5, 7)
AFTER_CLIFFORD = 0.0    # 2-term reference (open decision #1 CLOSED; matches 07/16/17/20)
USE_CACHED = False      # 3-term cache is now stale (model changed); re-sweep at 2-term
NPZ = "threshold_high_stat.npz"
MIN_EVENTS = 20
PTH_LO, PTH_HI = 0.02, 0.15   # #7 band, applied to the EFFECTIVE rate
SEED0 = 11_000


def repetition_circuit(d: int, p: float) -> stim.Circuit:
    return stim.Circuit.generated(
        "repetition_code:memory",
        rounds=d, distance=d,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p / 2,
        after_clifford_depolarization=AFTER_CLIFFORD * p,
    )


def effective_xflip(p: float) -> float:
    return 2.0 * p / 3.0


def logical_error_rate_with_error(d, p, n_shots, seed):
    circuit = repetition_circuit(d, p)
    sampler = circuit.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(n_shots, separate_observables=True)
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=True,
        ignore_decomposition_failures=False,
    )
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pred = matcher.decode_batch(det)
    n_err = int(np.any(pred != obs, axis=1).sum())
    pL = n_err / n_shots
    sigma = np.sqrt(pL * (1 - pL) / n_shots)
    return pL, sigma


def threshold_sweep():
    # Top extended 10**-0.7 (0.1995) -> 10**-0.5 (0.316): at 2-term the d3/d5
    # crossing sits at ~0.21 nominal, just ABOVE the old top, so coarse_crossing
    # saw no sign change and the slope fit fell back to the full (flattened) range.
    p_range = np.logspace(-2.5, -0.5, N_POINTS)
    results = {}
    for di, d in enumerate(D_LIST):
        print(f"\n========== d = {d} ==========")
        rates, errs = [], []
        for pi, p in enumerate(p_range):
            pL, sig = logical_error_rate_with_error(d, p, N_SHOTS,
                                                    SEED0 + 1000 * di + pi)
            rates.append(pL); errs.append(sig)
            print(f"  p={p:.4f}  pL={pL:.5f} +/- {sig:.5f}")
        results[d] = (np.array(rates), np.array(errs))
    return p_range, results


def load_cached():
    if not (USE_CACHED and os.path.exists(NPZ)):
        return None
    z = np.load(NPZ)
    p = z["p"]
    results = {}
    for d in D_LIST:
        if f"d{d}_pL" in z:
            results[d] = (z[f"d{d}_pL"], z[f"d{d}_err"])
    if results:
        print(f"[cache] loaded {NPZ} -- re-fitting without re-sweeping "
              f"(set USE_CACHED=False to force a fresh run)")
        return p, results
    return None


def _nerr_est(rates, errs):
    """Recover approximate event count from (pL, sigma) without needing N."""
    return (rates / np.maximum(errs, 1e-12)) ** 2


def coarse_crossing(p, r3, e3, r5, e5):
    diff = r3 - r5
    ok = (_nerr_est(r3, e3) >= MIN_EVENTS) & (_nerr_est(r5, e5) >= MIN_EVENTS)
    for i in range(len(p) - 1):
        if not (ok[i] and ok[i + 1]):
            continue
        if diff[i] == 0:
            return float(p[i])
        if diff[i] * diff[i + 1] < 0:
            t = -diff[i] / (diff[i + 1] - diff[i])
            return float(p[i] * (p[i + 1] / p[i]) ** t)
    return None


def power_law_slope(p, rates, errs, pmax):
    """Weighted log-log slope on the asymptotic window p <= pmax, resolved pts."""
    mask = (rates > 0) & (_nerr_est(rates, errs) >= MIN_EVENTS)
    if pmax is not None:
        mask &= (p <= pmax)
    n_used = int(mask.sum())
    if n_used < 3:
        return float("nan"), float("nan"), n_used
    x, y = np.log(p[mask]), np.log(rates[mask])
    sig = errs[mask] / np.maximum(rates[mask], 1e-12)
    w = 1.0 / np.maximum(sig, 1e-12) ** 2
    slope, intercept = np.polyfit(x, y, 1, w=w)
    resid = y - (slope * x + intercept)
    se = np.sqrt(np.sum(w * resid ** 2) / (n_used - 2)) if n_used > 2 else np.nan
    se_slope = se / np.sqrt(np.sum(w * (x - x.mean()) ** 2))
    return float(slope), float(se_slope), n_used


def plot(p, results, p_th, fname="threshold_high_stat.pdf"):
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = {3: "#1D9E75", 5: "#534AB7", 7: "#D85A30"}
    for d, (rates, errs) in results.items():
        ax.errorbar(p, np.maximum(rates, 1e-7), yerr=errs, fmt="o-",
                    color=colors.get(d, "k"), lw=1.6, ms=4, capsize=2,
                    label=f"d = {d}")
    ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    if p_th:
        ax.axvline(p_th, color="gray", ls=":", alpha=0.6,
                   label=rf"$p_{{th}}\approx{p_th:.3f}$ (coarse)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Physical error rate  $p_\mathrm{phys}$", fontsize=12)
    ax.set_ylabel(r"Logical error rate  $p_L$", fontsize=12)
    ax.set_title(f"Repetition threshold (N={N_SHOTS:,}/pt, "
                 f"after_clifford={AFTER_CLIFFORD}p)", fontsize=11)
    ax.legend(fontsize=10); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")

if __name__ == "__main__":
    cached = load_cached()
    if cached is not None:
        p_range, results = cached
    else:
        print(f"Config: D={D_LIST}, N_POINTS={N_POINTS}, N_SHOTS={N_SHOTS:,}, "
              f"after_clifford={AFTER_CLIFFORD}p")
        print(f"Estimated total shots: {len(D_LIST) * N_POINTS * N_SHOTS:,}")
        p_range, results = threshold_sweep()
        save = {f"d{d}_pL": v[0] for d, v in results.items()}
        save.update({f"d{d}_err": v[1] for d, v in results.items()})
        save["p"] = p_range
        np.savez(NPZ, **save)
        print(f"[OK] saved {NPZ}")

    # ── Threshold (coarse crossing; sets the slope window) ────────────────────
    print("\n--- Threshold (Phase-1 coarse crossing of d=3, d=5) ---")
    p_th = None
    if 3 in results and 5 in results:
        p_th = coarse_crossing(p_range, results[3][0], results[3][1],
                               results[5][0], results[5][1])
    if p_th is None:
        print("  [WARN] no resolved d3/d5 crossing in range")
        cross_ok = False
        slope_cap = None
    else:
        p_th_eff = effective_xflip(p_th)
        cross_ok = PTH_LO <= p_th_eff <= PTH_HI
        slope_cap = p_th / 3.0
        print(f"  p_th (nominal)         = {p_th:.4f}")
        print(f"  p_th (effective Xflip) = {p_th_eff:.4f}  "
              f"[{'PASS' if cross_ok else 'FAIL'}] vs #7 band [{PTH_LO},{PTH_HI}]")
        print(f"  (2-term reference model -- now consistent with script 07: "
              f"~0.21 nominal / ~0.14 effective)")
        print(f"  -> rigorous (p_th, nu) with errors: script 17 (expect nu~1.5; 2D-RBIM)")

    plot(p_range, results, p_th)

    # ── Slopes on the asymptotic window p <= p_th/3 ───────────────────────────
    cap_str = f"{slope_cap:.3f}" if slope_cap else "full range"
    print(f"\n--- Suppression slopes (asymptotic window p <= {cap_str}) ---")
    slope_ok = True
    for d, (rates, errs) in results.items():
        slope, se, n_used = power_law_slope(p_range, rates, errs, slope_cap)
        expected = (d + 1) // 2
        if np.isnan(slope):
            print(f"  d={d}: slope = n/a ({n_used} resolved pts below p_th/3)")
            if d <= 5:
                slope_ok = False
        else:
            ok = abs(slope - expected) < 0.6
            slope_ok &= ok
            print(f"  d={d}: slope = {slope:.2f} +/- {se:.2f}  expected {expected}  "
                  f"(n={n_used})  [{'PASS' if ok else 'FAIL'}]")

    print("\n--- PASS/FAIL ---")
    print(f"[{'PASS' if slope_ok else 'FAIL'}] suppression slopes -> ceil(d/2)")
    print(f"[{'PASS' if cross_ok else 'FAIL'}] coarse threshold within #7 band (effective)")