# Rotated surface code d=3 vs repetition code d=3 at identical noise.

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import stim
import pymatching

MIN_EVENTS = 20


def _noise_kwargs(p: float) -> dict:
    """Single circuit-level noise spec applied IDENTICALLY to both codes."""
    return dict(
        before_round_data_depolarization=p,
        before_measure_flip_probability=p / 2,
        after_clifford_depolarization=p / 4,
        after_reset_flip_probability=p / 4,
    )


def surface_code_circuit(d: int, p: float, basis: str = "Z") -> stim.Circuit:
    """Rotated surface code memory experiment."""
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis.lower()}",
        rounds=d, distance=d, **_noise_kwargs(p),
    )


def repetition_code_circuit(d: int, p: float) -> stim.Circuit:
    """Repetition code at the SAME 4-term noise as the surface code (fairness)."""
    return stim.Circuit.generated(
        "repetition_code:memory",
        rounds=d, distance=d, **_noise_kwargs(p),
    )


def wilson_ci(n_err: int, n: int, z: float = 1.96):
    if n == 0:
        return 0.0, 0.0
    phat = n_err / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = (z / denom) * np.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def logical_error_rate(circuit: stim.Circuit, n_shots: int, seed: int):
    sampler = circuit.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(n_shots, separate_observables=True)
    dem = circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
        ignore_decomposition_failures=False,   # was True -> silent drop
    )
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pred = matcher.decode_batch(det)
    n_err = int(np.any(pred != obs, axis=1).sum())
    return n_err / n_shots, n_err, n_shots


def threshold_sweep(d: int = 3, n_points: int = 12, n_shots: int = 100_000,
                    seed0: int = 2024):
    p_range = np.logspace(-2.5, -0.7, n_points)
    surf_z, surf_x, rep = [], [], []
    ez, ex, er = [], [], []
    for i, p in enumerate(p_range):
        z, nz, _ = logical_error_rate(surface_code_circuit(d, p, "Z"), n_shots, seed0 + 10 * i + 1)
        x, nx, _ = logical_error_rate(surface_code_circuit(d, p, "X"), n_shots, seed0 + 10 * i + 2)
        r, nr, _ = logical_error_rate(repetition_code_circuit(d, p),  n_shots, seed0 + 10 * i + 3)
        surf_z.append(z); surf_x.append(x); rep.append(r)
        ez.append(nz); ex.append(nx); er.append(nr)
        print(f"  p={p:.4f}   surf-Z={z:.5f} (n={nz})   "
              f"surf-X={x:.5f} (n={nx})   rep={r:.5f} (n={nr})")
    return (p_range, np.array(surf_z), np.array(surf_x), np.array(rep),
            np.array(ez), np.array(ex), np.array(er))


def plot_comparison(p, surf_z, surf_x, rep, ez, ex, er, d, n_shots,
                    fname="surface_d3_threshold.pdf"):
    fig, ax = plt.subplots(figsize=(7, 5))
    for vals, nerr, fmt, col, lab in [
        (surf_z, ez, "o-", "#1D9E75", f"Surface d={d} (Z-mem, X-correction)"),
        (surf_x, ex, "s-", "#534AB7", f"Surface d={d} (X-mem, Z-correction)"),
        (rep,    er, "^--", "#888780", f"Repetition d={d} (single error type)"),
    ]:
        lo = np.array([wilson_ci(int(e), n_shots)[0] for e in nerr])
        hi = np.array([wilson_ci(int(e), n_shots)[1] for e in nerr])
        yerr = np.vstack([np.maximum(vals - lo, 0), np.maximum(hi - vals, 0)])
        ax.errorbar(p, np.maximum(vals, 1e-7), yerr=yerr, fmt=fmt, color=col,
                    lw=1.6, ms=4, capsize=2, label=lab)
    ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Physical error rate  $p_\mathrm{phys}$", fontsize=11)
    ax.set_ylabel(r"Logical error rate  $p_L$", fontsize=11)
    ax.set_title(f"Surface code d={d}: universal protection vs repetition", fontsize=11)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")


def estimate_mode_count(d: int) -> dict:
    n_data = d ** 2
    n_anc_X = (d ** 2 - 1) // 2
    n_anc_Z = (d ** 2 - 1) // 2
    n_anc = n_anc_X + n_anc_Z
    n_qubits = n_data + n_anc
    total_modes = n_qubits * 6 + 6 * n_anc
    return dict(d=d, n_data=n_data, n_anc=n_anc, n_qubits=n_qubits,
                total_modes_heuristic=total_modes)

if __name__ == "__main__":
    for d in (3, 5):
        b = estimate_mode_count(d)
        print(f"\nSurface code d={d} mode budget (HEURISTIC, not paper-derived):")
        for k, v in b.items():
            print(f"  {k:>22} = {v}")
    print("  NOTE: paper Table VI's 'Surface d=3: 9 qubits' counts DATA only; "
          "true physical count is 9 data + 8 ancilla = 17.")

    N_SHOTS = 100_000
    print(f"\nRunning surface-code d=3 sweep ({N_SHOTS} shots, identical noise both codes)...")
    p, surf_z, surf_x, rep, ez, ex, er = threshold_sweep(d=3, n_points=12, n_shots=N_SHOTS)
    plot_comparison(p, surf_z, surf_x, rep, ez, ex, er, d=3, n_shots=N_SHOTS)
    np.savez("surface_d3_data.npz", p=p, surf_z=surf_z, surf_x=surf_x, rep=rep,
             nerr_z=ez, nerr_x=ex, nerr_rep=er)
    print("[OK] saved surface_d3_data.npz")

    # ── Checks ────────────────────────────────────────────────────────────────
    print("\n--- Checks ---")
    # (a) X/Z symmetry: under symmetric depolarizing noise the two memories
    #     should agree.  Compare on well-resolved points (both >= MIN_EVENTS).
    res = (ez >= MIN_EVENTS) & (ex >= MIN_EVENTS)
    if res.sum() >= 3:
        ratio = surf_z[res] / surf_x[res]
        sym = np.median(ratio)
        sym_ok = 0.85 <= sym <= 1.18
        print(f"[{'PASS' if sym_ok else 'FAIL'}] surface X/Z symmetry: "
              f"median pL(Z)/pL(X) = {sym:.3f} (expect ~1.0)")
    else:
        sym_ok = False
        print("[WARN] too few resolved points to test X/Z symmetry; raise shots")

    # (b) Expected trade-off: at matched noise, surface d=3 should be WORSE
    #     (higher pL) than repetition d=3 at a well-resolved mid-p point.
    well = np.where((ez >= MIN_EVENTS) & (er >= MIN_EVENTS))[0]
    if len(well):
        j = well[len(well) // 2]
        worse_ok = surf_z[j] > rep[j]
        print(f"[{'PASS' if worse_ok else 'FAIL'}] surface worse than rep at "
              f"d=3 (p={p[j]:.4f}): surf-Z={surf_z[j]:.5f} vs rep={rep[j]:.5f} "
              f"(expected: universality costs pL at small d)")
    else:
        worse_ok = False
        print("[WARN] no jointly-resolved point for surface-vs-rep check")

    print("\n--- PASS/FAIL ---")
    print(f"[{'PASS' if sym_ok else 'FAIL'}] X/Z memories agree (depolarizing symmetry)")
    print(f"[{'PASS' if worse_ok else 'FAIL'}] surface > rep at d=3 (expected trade-off)")