# Rotated surface code d=3 vs d=5 threshold crossing.

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import stim
import pymatching

MIN_EVENTS = 20
SURF_PTH_LO, SURF_PTH_HI = 0.002, 0.05      # plausible surface-code band (NOT #7)


def _noise_kwargs(p: float) -> dict:
    return dict(
        before_round_data_depolarization=p,
        before_measure_flip_probability=p / 2,
        after_clifford_depolarization=p / 4,
        after_reset_flip_probability=p / 4,
    )


def surface_circuit(d: int, p: float, basis: str = "Z") -> stim.Circuit:
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis.lower()}",
        rounds=d, distance=d, **_noise_kwargs(p),
    )


def effective_xflip(p: float) -> float:
    return 2.0 * p / 3.0


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
        ignore_decomposition_failures=False,
    )
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pred = matcher.decode_batch(det)
    n_err = int(np.any(pred != obs, axis=1).sum())
    return n_err / n_shots, n_err, n_shots


def sweep(d_list=(3, 5), n_points=13, shots=None, seed0=909):
    shots = shots or {3: 100_000, 5: 50_000}
    p_range = np.logspace(-2.7, -1.0, n_points)        # [0.002, 0.10]
    results, errors = {}, {}
    for di, d in enumerate(d_list):
        n = shots[d]
        print(f"\n[surface d = {d}]  n_shots = {n}")
        rates, nerrs = [], []
        for pi, p in enumerate(p_range):
            pL, n_err, _ = logical_error_rate(surface_circuit(d, p, "Z"),
                                              n, seed0 + 100 * di + pi)
            lo, hi = wilson_ci(n_err, n)
            rates.append(pL); nerrs.append(n_err)
            flag = "" if n_err >= MIN_EVENTS else "  (under-resolved)"
            print(f"   p={p:.4f}  pL={pL:.5f}  [{lo:.5f}, {hi:.5f}]  "
                  f"n={n_err}{flag}")
        results[d] = np.array(rates)
        errors[d] = np.array(nerrs)
    return p_range, results, errors


def find_crossover(p_range, r3, e3, r5, e5):
    diff = r3 - r5
    ok = (e3 >= MIN_EVENTS) & (e5 >= MIN_EVENTS)
    for i in range(len(p_range) - 1):
        if not (ok[i] and ok[i + 1]):
            continue
        if diff[i] == 0:
            return float(p_range[i])
        if diff[i] * diff[i + 1] < 0:
            t = -diff[i] / (diff[i + 1] - diff[i])
            return float(p_range[i] * (p_range[i + 1] / p_range[i]) ** t)
    return None


def plot(p, results, errors, shots, fname="surface_d5_threshold.pdf"):
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = {3: "#1D9E75", 5: "#534AB7"}
    for d, rates in results.items():
        ne = errors[d]; n = shots[d]
        lo = np.array([wilson_ci(int(e), n)[0] for e in ne])
        hi = np.array([wilson_ci(int(e), n)[1] for e in ne])
        yerr = np.vstack([np.maximum(rates - lo, 0), np.maximum(hi - rates, 0)])
        ax.errorbar(p, np.maximum(rates, 1e-7), yerr=yerr, fmt="o-",
                    color=colors[d], lw=1.6, ms=4, capsize=2, label=f"Surface d = {d}")
    ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    p_th = find_crossover(p, results[3], errors[3], results[5], errors[5])
    if p_th:
        ax.axvline(p_th, color="gray", ls=":", alpha=0.6,
                   label=f"p_th ≈ {p_th:.4f}")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Physical error rate  $p_\mathrm{phys}$", fontsize=11)
    ax.set_ylabel(r"Logical error rate  $p_L$", fontsize=11)
    ax.set_title("Rotated surface code: d=3 vs d=5", fontsize=12)
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"\n[OK] saved {fname}")
    return p_th

if __name__ == "__main__":
    shots = {3: 100_000, 5: 50_000}
    p, results, errors = sweep(d_list=(3, 5), n_points=13, shots=shots)
    p_th = plot(p, results, errors, shots)
    np.savez("surface_d5_data.npz", p=p,
             **{f"d{d}": v for d, v in results.items()},
             **{f"nerr_d{d}": v for d, v in errors.items()})
    print("[OK] saved surface_d5_data.npz")

    print("\n--- Surface-code threshold (d=3/d=5 crossover) ---")
    if p_th is None:
        print("  [WARN] no resolved crossover in range; adjust p-range or raise shots")
        cross_ok = False
    else:
        p_th_eff = effective_xflip(p_th)
        cross_ok = SURF_PTH_LO <= p_th <= SURF_PTH_HI
        print(f"  p_th (nominal)        = {p_th:.4f}")
        print(f"  p_th (effective Xflip)= {p_th_eff:.4f}")
        print(f"  [{'PASS' if cross_ok else 'FAIL'}] within plausible surface band "
              f"[{SURF_PTH_LO}, {SURF_PTH_HI}] (much lower than rep's ~0.21)")

    # Ordering sanity: below the crossover, d=5 should beat d=3 on resolved points.
    below = (p < (p_th or 0)) & (errors[3] >= MIN_EVENTS) & (errors[5] >= MIN_EVENTS)
    order_ok = bool(np.all(results[5][below] <= results[3][below])) if below.any() else False
    print(f"\n--- PASS/FAIL ---")
    print(f"[{'PASS' if cross_ok else 'FAIL'}] surface threshold found & in plausible band")
    print(f"[{'PASS' if order_ok else 'FAIL'}] d=5 below d=3 sub-threshold "
          f"(resolved points)")