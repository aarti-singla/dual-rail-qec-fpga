# Bacon-Shor [[9,1,3]] subsystem code at d=3.

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import stim
import pymatching

GAUGES_Z = [(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8)]   # horizontal
GAUGES_X = [(0, 3), (3, 6), (1, 4), (4, 7), (2, 5), (5, 8)]   # vertical
LOG_Z = [0, 3, 6]        # column 0  -> Z-bar
LOG_X = [0, 1, 2]        # row 0     -> X-bar
MIN_EVENTS = 20


def bacon_shor_circuit(d: int, p: float, basis: str = "Z", rounds: int = 3) -> stim.Circuit:
    if d != 3:
        raise NotImplementedError("Template is for d=3 only.")
    z_mem = basis.upper() == "Z"
    gauges = GAUGES_Z if z_mem else GAUGES_X
    anc = list(range(9, 9 + len(gauges)))     # 6 ancillas
    ng = len(gauges)

    c = stim.Circuit()
    c.append("RX" if not z_mem else "R", range(9))
    if p > 0:
        # init error must ANTICOMMUTE with the prep basis to be physical:
        #   Z-memory prepares |0> -> the meaningful error is X_ERROR
        #   X-memory prepares |+> -> the meaningful error is Z_ERROR
        c.append("X_ERROR" if z_mem else "Z_ERROR", range(9), p)
    c.append("TICK")

    for r in range(rounds):
        c.append("R", anc)
        if p > 0:
            c.append("DEPOLARIZE1", range(9), p)
        if not z_mem:
            c.append("H", anc)
        for k, (qi, qj) in enumerate(gauges):
            if z_mem:                       # Z-parity: data-controlled onto ancilla
                c.append("CNOT", [qi, anc[k]])
                c.append("CNOT", [qj, anc[k]])
            else:                           # X-parity: ancilla-controlled onto data
                c.append("CNOT", [anc[k], qi])
                c.append("CNOT", [anc[k], qj])
        if not z_mem:
            c.append("H", anc)
        if p > 0:
            c.append("X_ERROR", anc, p / 2)
        c.append("M", anc)

        if r == 0:
            for k in range(ng):             # init eigenstate -> each gauge = 0
                c.append("DETECTOR", [stim.target_rec(-ng + k)], [float(k), 0.0])
        else:
            for k in range(ng):             # round-to-round (only one gauge type measured)
                c.append("DETECTOR",
                         [stim.target_rec(-ng + k), stim.target_rec(-2 * ng + k)],
                         [float(k), float(r)])
        c.append("TICK")

    # Final data readout in the protected basis, then close the detector chain
    c.append("MX" if not z_mem else "M", range(9))
    for k, (qi, qj) in enumerate(gauges):
        # last-round ancilla k is rec(-9-ng+k); data q is rec(-9+q)
        c.append("DETECTOR",
                 [stim.target_rec(-9 + qi), stim.target_rec(-9 + qj),
                  stim.target_rec(-9 - ng + k)], [float(k), float(rounds)])
    log = LOG_Z if z_mem else LOG_X
    c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-9 + q) for q in log], 0)
    return c


def logical_rate(circuit, n_shots, seed):
    sampler = circuit.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(n_shots, separate_observables=True)
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=True,
        ignore_decomposition_failures=False)
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pred = matcher.decode_batch(det)
    n_err = int(np.any(pred != obs, axis=1).sum())
    return n_err / n_shots, n_err


def check_distance(basis="Z"):
    """Verify the circuit is genuinely distance 3 (noiseless graphlike search)."""
    c = bacon_shor_circuit(3, 1e-3, basis)
    try:
        return len(c.shortest_graphlike_error())
    except Exception as e:
        return f"ERROR: {e}"


def sweep(n_points=12, n_shots=50_000, seed0=1515):
    p_range = np.logspace(-2.5, -0.7, n_points)
    z, x, ez, ex = [], [], [], []
    for i, p in enumerate(p_range):
        zr, zn = logical_rate(bacon_shor_circuit(3, p, "Z"), n_shots, seed0 + i)
        xr, xn = logical_rate(bacon_shor_circuit(3, p, "X"), n_shots, seed0 + 100 + i)
        z.append(zr); x.append(xr); ez.append(zn); ex.append(xn)
        print(f"  p={p:.4f}   Z={zr:.5f} (n={zn})   X={xr:.5f} (n={xn})")
    return (p_range, np.array(z), np.array(x), np.array(ez), np.array(ex))


def slope_lowp(p, pL, nerr, pmax=0.03):
    m = (np.asarray(nerr) >= MIN_EVENTS) & (p <= pmax) & (pL > 0)
    if m.sum() < 3:
        return float("nan")
    return float(np.polyfit(np.log(p[m]), np.log(pL[m]), 1)[0])


def mode_budget_bacon_shor(d):
    n_data = d ** 2
    n_gauge_anc = 2 * d * (d - 1)
    n_qubits = n_data + n_gauge_anc
    return dict(d=d, n_data=n_data, n_gauge_anc=n_gauge_anc, n_qubits=n_qubits,
                modes_per_qubit=6, total_modes_heuristic=n_qubits * 6)


def plot(p, z, x, ez, ex, n_shots, fname="bacon_shor_d3_threshold.pdf"):
    fig, ax = plt.subplots(figsize=(7, 5))
    for vals, ne, fmt, col, lab in [
        (z, ez, "o-", "#1D9E75", "Bacon-Shor d=3 (Z-mem)"),
        (x, ex, "s-", "#534AB7", "Bacon-Shor d=3 (X-mem)")]:
        sig = np.sqrt(np.maximum(vals, 1e-9) * (1 - np.maximum(vals, 1e-9)) / n_shots)
        ax.errorbar(p, np.maximum(vals, 1e-7), yerr=sig, fmt=fmt, color=col,
                    lw=1.6, ms=4, capsize=2, label=lab)
    ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Physical error rate $p_\mathrm{phys}$", fontsize=11)
    ax.set_ylabel(r"Logical error rate $p_L$", fontsize=11)
    ax.set_title("Bacon-Shor [[9,1,3]]: universal protection with NN wiring", fontsize=11)
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")

if __name__ == "__main__":
    b = mode_budget_bacon_shor(3)
    print("Bacon-Shor d=3 mode budget (heuristic):")
    for k, v in b.items():
        print(f"  {k:>22} = {v}")

    print("\n--- Circuit distance self-check (must be 3) ---")
    for basis in ("Z", "X"):
        dz = check_distance(basis)
        ok = (dz == 3)
        print(f"  [{'PASS' if ok else 'FAIL'}] {basis}-memory shortest_graphlike_error = {dz} "
              f"(expect 3)")

    print("\nRunning Bacon-Shor d=3 sweep...")
    p, z, x, ez, ex = sweep(n_points=12, n_shots=50_000)
    plot(p, z, x, ez, ex, 50_000)
    np.savez("bacon_shor_d3_data.npz", p=p, z=z, x=x, nerr_z=ez, nerr_x=ex)
    print("[OK] saved bacon_shor_d3_data.npz")

    print("\n--- PASS/FAIL (protection sanity) ---")
    sz = slope_lowp(p, z, ez); sx = slope_lowp(p, x, ex)
    lowp_ok = (z[0] < p[0]) and (x[0] < p[0])
    slope_ok = (not np.isnan(sz) and abs(sz - 2) < 0.7) and \
               (not np.isnan(sx) and abs(sx - 2) < 0.7)
    print(f"  Z slope={sz:.2f}  X slope={sx:.2f}  (expect ~2)")
    print(f"  [{'PASS' if lowp_ok else 'FAIL'}] pL < p at lowest point (code protects)")
    print(f"  [{'PASS' if slope_ok else 'FAIL'}] sub-threshold slope ~ 2 (distance-3 suppression)")