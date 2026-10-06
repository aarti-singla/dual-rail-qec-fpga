# Wilson and bootstrap confidence intervals for the logical error rate.

import numpy as np
import matplotlib.pyplot as plt
import csv
import stim
import pymatching

MIN_EVENTS = 20   # methodology floor for a trustworthy CI / slope point


def repetition_circuit(d: int, p: float) -> stim.Circuit:
    """2-term repetition memory (after_clifford_depolarization = 0.0)."""
    return stim.Circuit.generated(
        "repetition_code:memory",
        rounds=d, distance=d,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p / 2,
        after_clifford_depolarization=0.0,
    )


def decode_batch(d: int, p: float, n_shots: int, seed: int):
    circuit = repetition_circuit(d, p)
    sampler = circuit.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(n_shots, separate_observables=True)
    dem = circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
        ignore_decomposition_failures=False,
    )
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pred = matcher.decode_batch(det)
    return np.any(pred != obs, axis=1)


def wilson_interval(k: int, N: int, z: float = 1.96):
    """Wilson score 95% interval for a proportion (valid at low counts)."""
    if N == 0:
        return 0.0, 0.0
    ph = k / N
    den = 1.0 + z * z / N
    centre = (ph + z * z / (2 * N)) / den
    half = z * np.sqrt(ph * (1 - ph) / N + z * z / (4 * N * N)) / den
    return max(centre - half, 0.0), centre + half


def bootstrap_pL(failures: np.ndarray, n_boot: int, seed: int):
    rng = np.random.default_rng(seed)
    N = len(failures)
    n_events = int(failures.sum())
    pL_mean = n_events / N
    sigma = float(np.sqrt(pL_mean * (1 - pL_mean) / N)) if 0 < pL_mean < 1 \
        else 1.0 / N
    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, N, size=N)
        boots[b] = failures[idx].mean()
    lo = float(np.percentile(boots, 2.5))
    hi = float(np.percentile(boots, 97.5))
    return pL_mean, sigma, lo, hi, n_events


def sweep_with_bootstrap(d_list=(3, 5, 7), n_points=10, n_shots=200_000,
                         n_boot=1000, base_seed=2000):
    # near-threshold range so points are countable (deep sub-threshold starves
    # d=5/7); under-powered points are still computed but flagged.
    p_range = np.logspace(-1.3, -0.85, n_points)   # ~0.050 .. 0.141 nominal
    rows = []
    fig_data = {d: dict(p=[], pL=[], lo=[], hi=[], wlo=[], whi=[],
                        nev=[], powered=[]) for d in d_list}
    for di, d in enumerate(d_list):
        print(f"\n[d = {d}]")
        for pi, p in enumerate(p_range):
            seed = base_seed + 1000 * di + pi
            failures = decode_batch(d, p, n_shots, seed)
            pL, sig, lo, hi, nev = bootstrap_pL(failures, n_boot,
                                                seed + 500_000)
            wlo, whi = wilson_interval(nev, n_shots)
            powered = nev >= MIN_EVENTS
            rows.append(dict(d=d, p=p, p_eff=2 * p / 3, n_shots=n_shots,
                             pL=pL, n_events=nev, sigma_binom=sig,
                             boot_lo95=lo, boot_hi95=hi,
                             wilson_lo95=wlo, wilson_hi95=whi,
                             powered=powered))
            fd = fig_data[d]
            fd["p"].append(p); fd["pL"].append(pL); fd["lo"].append(lo)
            fd["hi"].append(hi); fd["wlo"].append(wlo); fd["whi"].append(whi)
            fd["nev"].append(nev); fd["powered"].append(powered)
            flag = "" if powered else "  [under-powered <20 ev]"
            print(f"  p={p:.4f} (eff {2*p/3:.4f})  pL={pL:.5f}  "
                  f"events={nev:5d}  boot=[{lo:.5f},{hi:.5f}]  "
                  f"wilson=[{wlo:.5f},{whi:.5f}]{flag}")
    return rows, fig_data


def plot(fig_data, fname="bootstrap_intervals.pdf"):
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    colors = {3: "#1D9E75", 5: "#534AB7", 7: "#D85A30"}
    for d, dat in fig_data.items():
        p = np.array(dat["p"]); pL = np.array(dat["pL"])
        lo = np.array(dat["lo"]); hi = np.array(dat["hi"])
        powered = np.array(dat["powered"])
        c = colors.get(d, "k")
        # powered points: solid with bootstrap error bars
        if powered.any():
            yerr = np.array([pL[powered] - lo[powered], hi[powered] - pL[powered]])
            yerr = np.clip(yerr, 0, None)
            ax.errorbar(p[powered], pL[powered], yerr=yerr, fmt="o-", color=c,
                        lw=1.6, ms=4, capsize=3, label=f"d={d}")
        # under-powered points: faint open markers, no error bars
        if (~powered).any():
            ax.plot(p[~powered], np.maximum(pL[~powered], 1e-7), "o", color=c,
                    mfc="none", alpha=0.4, ms=4)
    p_any = np.array(list(fig_data.values())[0]["p"])
    ax.loglog(p_any, p_any, "k--", alpha=0.4, label="No QEC")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Physical error rate $p_{\rm phys}$ (nominal)")
    ax.set_ylabel(r"Logical error rate $p_L$ with 95% CI")
    ax.set_title("Threshold curves with bootstrap 95% CIs (2-term)\n"
                 "open markers = under-powered (<20 events), no CI")
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")


def export_csv(rows, path="bootstrap_intervals.csv"):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[OK] wrote {path}")

if __name__ == "__main__":
    print("Running bootstrap sweep (2-term, 200k shots)...")
    rows, fig_data = sweep_with_bootstrap(d_list=(3, 5, 7), n_points=10,
                                          n_shots=200_000, n_boot=1000)
    plot(fig_data)
    export_csv(rows)

    # ---- self-checks ----
    print("\n--- SELF-CHECKS ---")
    powered_rows = [r for r in rows if r["powered"]]
    print(f"[{'PASS' if powered_rows else 'FAIL'}] >=1 powered point "
          f"({len(powered_rows)}/{len(rows)} points have >=20 events)")
    # bootstrap and Wilson agree on powered points (relative width within 30%)
    agree = []
    for r in powered_rows:
        bw = r["boot_hi95"] - r["boot_lo95"]
        ww = r["wilson_hi95"] - r["wilson_lo95"]
        if ww > 0:
            agree.append(abs(bw - ww) / ww)
    okAgree = (np.mean(agree) < 0.30) if agree else False
    print(f"[{'PASS' if okAgree else 'FAIL'}] bootstrap CI width ~ Wilson CI "
          f"width on powered points (mean rel. diff {np.mean(agree):.2f})")
    # Wilson lower bound strictly positive wherever events>0
    okPos = all(r["wilson_lo95"] > 0 for r in rows if r["n_events"] > 0)
    print(f"[{'PASS' if okPos else 'FAIL'}] Wilson lower bound > 0 for all "
          f"points with events (normal SE would go negative)")
    # docstring arithmetic
    sig = np.sqrt(2.36e-3 * (1 - 2.36e-3) / 1e5)
    okDoc = abs(sig - 1.5e-4) < 0.1e-4
    print(f"[{'PASS' if okDoc else 'FAIL'}] docstring SE check: "
          f"pL=2.36e-3,N=1e5 -> sigma={sig:.2e} (~1.5e-4)")
