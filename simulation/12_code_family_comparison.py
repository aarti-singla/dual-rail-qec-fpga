# Repetition d=3 vs rotated surface d=3 at identical noise.

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import stim
import pymatching

MIN_EVENTS = 20
INCLUDE_STEANE = False     # set True ONLY after wiring steane_d3() to script 24


def _noise_kwargs(p: float) -> dict:
    """Identical circuit-level noise for every code (fair comparison)."""
    return dict(
        before_round_data_depolarization=p,
        before_measure_flip_probability=p / 2,
        after_clifford_depolarization=p / 4,
        after_reset_flip_probability=p / 4,
    )


def repetition_d3(p: float) -> stim.Circuit:
    return stim.Circuit.generated("repetition_code:memory",
                                  rounds=3, distance=3, **_noise_kwargs(p))


def surface_d3(p: float, basis: str = "Z") -> stim.Circuit:
    return stim.Circuit.generated(f"surface_code:rotated_memory_{basis.lower()}",
                                  rounds=3, distance=3, **_noise_kwargs(p))


def steane_d3(p: float) -> stim.Circuit:
    raise NotImplementedError(
        "Steane [[7,1,3]] has no Stim generator; wire steane_d3() to the "
        "manual construction in script 24 before setting INCLUDE_STEANE=True.")


def wilson_ci(n_err: int, n: int, z: float = 1.96):
    if n == 0:
        return 0.0, 0.0
    phat = n_err / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = (z / denom) * np.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def logical_rate(circuit: stim.Circuit, n_shots: int, seed: int):
    sampler = circuit.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(n_shots, separate_observables=True)
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=True,
        ignore_decomposition_failures=False,
    )
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pred = matcher.decode_batch(det)
    n_err = int(np.any(pred != obs, axis=1).sum())
    return n_err / n_shots, n_err


def run_comparison(n_points: int = 12, n_shots: int = 50_000, seed0: int = 1212):
    p_range = np.logspace(-2.5, -0.7, n_points)
    builders = {
        "Repetition d=3":      lambda p: repetition_d3(p),
        "Surface d=3 (Z-mem)": lambda p: surface_d3(p, "Z"),
        "Surface d=3 (X-mem)": lambda p: surface_d3(p, "X"),
    }
    if INCLUDE_STEANE:
        try:
            steane_d3(0.01)                       # probe availability
            builders["Steane [[7,1,3]]"] = lambda p: steane_d3(p)
        except NotImplementedError as e:
            print(f"[WARN] Steane excluded (NOT substituted): {e}")

    results = {k: [] for k in builders}
    errs = {k: [] for k in builders}
    for i, p in enumerate(p_range):
        row = []
        for j, (name, build) in enumerate(builders.items()):
            pL, n_err = logical_rate(build(p), n_shots, seed0 + 10 * i + j)
            results[name].append(pL); errs[name].append(n_err)
            row.append(f"{name.split()[0][:4]}={pL:.4f}")
        print(f"  p={p:.4f}  " + "  ".join(row))
    return (p_range,
            {k: np.array(v) for k, v in results.items()},
            {k: np.array(v) for k, v in errs.items()})


def plot(p_range, results, errs, n_shots, fname="code_family_comparison.pdf"):
    fig, ax = plt.subplots(figsize=(8, 6))
    styles = {
        "Repetition d=3":      dict(color="#1D9E75", marker="o"),
        "Surface d=3 (Z-mem)": dict(color="#534AB7", marker="s"),
        "Surface d=3 (X-mem)": dict(color="#9B7AC9", marker="^"),
        "Steane [[7,1,3]]":    dict(color="#D85A30", marker="D"),
    }
    for label, rates in results.items():
        ne = errs[label]
        lo = np.array([wilson_ci(int(e), n_shots)[0] for e in ne])
        hi = np.array([wilson_ci(int(e), n_shots)[1] for e in ne])
        yerr = np.vstack([np.maximum(rates - lo, 0), np.maximum(hi - rates, 0)])
        st = styles.get(label, dict(color="k", marker="x"))
        ax.errorbar(p_range, np.maximum(rates, 1e-7), yerr=yerr, fmt="-",
                    lw=1.6, ms=4, capsize=2, label=label, **st)
    ax.loglog(p_range, p_range, "k--", alpha=0.4, label="No QEC")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Physical error rate  $p_\mathrm{phys}$", fontsize=12)
    ax.set_ylabel(r"Logical error rate  $p_L$", fontsize=12)
    ax.set_title("Photonic code-family comparison at d=3", fontsize=12)
    ax.legend(fontsize=10); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")


def code_properties():
    return {
        "Repetition d=3":   dict(n_data=3,  n_anc=2,  modes=33,  mode_src="paper",
                                 protects="bit-flip only", latency_ns=25),
        "Repetition d=5":   dict(n_data=5,  n_anc=4,  modes=55,  mode_src="paper",
                                 protects="bit-flip only", latency_ns=35),
        "Surface d=3":      dict(n_data=9,  n_anc=8,  modes=150, mode_src="heuristic",
                                 protects="X+Z (universal)", latency_ns=180),
        "Surface d=5":      dict(n_data=25, n_anc=24, modes=438, mode_src="heuristic",
                                 protects="X+Z (universal)", latency_ns=420),
        "Steane [[7,1,3]]": dict(n_data=7,  n_anc=6,  modes=92,  mode_src="heuristic",
                                 protects="X+Z (universal, CSS)", latency_ns=80),
    }


def print_overhead_table():
    props = code_properties()
    print(f"\n{'Code':<20}{'qubits':>7}{'modes':>7}{'src':>11}"
          f"{'latency':>9}{'<190ns':>8}  protection")
    print("-" * 84)
    for name, d in props.items():
        tq = d['n_data'] + d['n_anc']
        ok = "yes" if d['latency_ns'] < 190 else "no"
        print(f"{name:<20}{tq:>7}{d['modes']:>7}{d['mode_src']:>11}"
              f"{d['latency_ns']:>7} ns{ok:>8}  {d['protects']}")
    print("  NOTE: rep modes (33/55) are paper-derived; surface/Steane modes "
          "are heuristic estimates (see 08/09).")

if __name__ == "__main__":
    print_overhead_table()
    print("\nRunning code-family threshold comparison...")
    N_SHOTS = 50_000
    p, results, errs = run_comparison(n_points=12, n_shots=N_SHOTS)
    plot(p, results, errs, N_SHOTS)
    np.savez("code_family_comparison.npz", p=p, **{
        k.replace(" ", "_").replace("(", "").replace(")", "").replace("=", "")
         .replace("[", "").replace("]", ""): v for k, v in results.items()})
    print("[OK] saved code_family_comparison.npz")

    # ── Checks ────────────────────────────────────────────────────────────────
    print("\n--- Checks ---")
    rep = results["Repetition d=3"]; e_rep = errs["Repetition d=3"]
    sz = results["Surface d=3 (Z-mem)"]; e_sz = errs["Surface d=3 (Z-mem)"]
    sx = results["Surface d=3 (X-mem)"]; e_sx = errs["Surface d=3 (X-mem)"]

    res = (e_sz >= MIN_EVENTS) & (e_sx >= MIN_EVENTS)
    sym = np.median(sz[res] / sx[res]) if res.sum() >= 3 else float("nan")
    sym_ok = 0.85 <= sym <= 1.18
    print(f"[{'PASS' if sym_ok else 'FAIL'}] surface X/Z symmetry: "
          f"median Z/X = {sym:.3f}")

    well = np.where((e_sz >= MIN_EVENTS) & (e_rep >= MIN_EVENTS))[0]
    j = well[len(well) // 2] if len(well) else None
    worse_ok = bool(j is not None and sz[j] > rep[j])
    if j is not None:
        print(f"[{'PASS' if worse_ok else 'FAIL'}] surface worse than rep at d=3 "
              f"(p={p[j]:.4f}): surf-Z={sz[j]:.4f} vs rep={rep[j]:.4f}")

    print("\n--- PASS/FAIL ---")
    print(f"[{'PASS' if sym_ok else 'FAIL'}] X/Z memories agree")
    print(f"[{'PASS' if worse_ok else 'FAIL'}] surface > rep at d=3 (expected)")
    if not INCLUDE_STEANE:
        print("[INFO] Steane NOT simulated (no Stim generator; wire to script 24 "
              "to include) -- excluded, not substituted")