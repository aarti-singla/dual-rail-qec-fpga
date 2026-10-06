# X-memory (phase-flip) version of the architecture circuit in 21.

import numpy as np
import matplotlib.pyplot as plt
import stim
import pymatching


def build_33mode_xmemory(p: float = 0.01, n_rounds: int = 3) -> stim.Circuit:
    """X-memory (phase-flip) repetition code, 2-term Pauli noise."""
    c = stim.Circuit()
    DATA = [0, 1, 2]
    ANC = [3, 4]                                   # XX01 -> anc0, XX12 -> anc1
    c.append("RX", DATA + ANC)                     # |+++>, ancillas |+>

    for r in range(n_rounds):
        c.append("DEPOLARIZE1", DATA, p)           # basis-symmetric data noise
        if r > 0:
            c.append("RX", ANC)                    # reset ancillas to |+>
        # XX syndrome extraction: ancilla is CONTROL (|+>), data are TARGETS
        c.append("CX", [ANC[0], DATA[0], ANC[0], DATA[1]])   # XX01
        c.append("CX", [ANC[1], DATA[1], ANC[1], DATA[2]])   # XX12
        c.append("Z_ERROR", ANC, p / 2)            # anticommutes with MX
        c.append("MX", ANC)
        if r == 0:
            c.append("DETECTOR", [stim.target_rec(-2)])
            c.append("DETECTOR", [stim.target_rec(-1)])
        else:
            c.append("DETECTOR", [stim.target_rec(-2), stim.target_rec(-4)])
            c.append("DETECTOR", [stim.target_rec(-1), stim.target_rec(-3)])

    # logical X readout + final-closure detectors
    c.append("Z_ERROR", DATA, p / 2)
    c.append("MX", DATA)                           # -3=q0, -2=q1, -1=q2
    c.append("DETECTOR", [stim.target_rec(-3), stim.target_rec(-2),
                          stim.target_rec(-5)])    # (X0X1) ^ anc0_last
    c.append("DETECTOR", [stim.target_rec(-2), stim.target_rec(-1),
                          stim.target_rec(-4)])    # (X1X2) ^ anc1_last
    c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-3), stim.target_rec(-2),
                                    stim.target_rec(-1)], 0)   # logical X parity
    return c


def generic_repetition_circuit(d: int, p: float) -> stim.Circuit:
    return stim.Circuit.generated(
        "repetition_code:memory",
        rounds=d, distance=d,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p / 2,
        after_clifford_depolarization=0.0,
    )


def logical_rate(circuit: stim.Circuit, n_shots: int, seed: int) -> float:
    sampler = circuit.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(n_shots, separate_observables=True)
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=True,
        ignore_decomposition_failures=False)
    matcher = pymatching.Matching.from_detector_error_model(dem)
    return float(np.mean(np.any(matcher.decode_batch(det) != obs, axis=1)))


def validate_circuit(n_rounds: int = 3) -> bool:
    noiseless = build_33mode_xmemory(p=0.0, n_rounds=n_rounds)
    det_ok = not noiseless.compile_detector_sampler(seed=1).sample(4000).any()
    arch = build_33mode_xmemory(p=0.01, n_rounds=n_rounds)
    try:
        arch.detector_error_model(decompose_errors=True,
                                  approximate_disjoint_errors=True,
                                  ignore_decomposition_failures=False)
        dem_ok = True
    except Exception as ex:
        print(f"  [warn] DEM build failed: {ex}"); dem_ok = False
    sgl = len(arch.shortest_graphlike_error())
    try:
        sue = len(arch.search_for_undetectable_logical_errors(
            dont_explore_detection_event_sets_with_size_above=4,
            dont_explore_edges_with_degree_above=4,
            dont_explore_edges_increasing_symptom_degree=False))
    except Exception as ex:
        print(f"  [warn] undetectable search failed: {ex}"); sue = -1
    dist_ok = (sgl == 3 and sue == 3)
    print(f"  deterministic detectors: {'PASS' if det_ok else 'FAIL'}")
    print(f"  DEM builds (False): {'PASS' if dem_ok else 'FAIL'}")
    print(f"  distance graphlike={sgl} undetectable={sue} (expect 3): "
          f"{'PASS' if dist_ok else 'FAIL'}")
    return det_ok and dem_ok and dist_ok


def compare_xmem_vs_generic(n_points=10, n_shots=200_000, base_seed=2800):
    p_range = np.logspace(-2.0, -0.85, n_points)
    xmem, gen = [], []
    print(f"\n{'p_nom':>9}{'p_eff':>9}{'x-mem':>11}{'generic-Z':>11}{'ratio':>9}")
    for i, p in enumerate(p_range):
        x = logical_rate(build_33mode_xmemory(p=p), n_shots, base_seed + i)
        g = logical_rate(generic_repetition_circuit(3, p), n_shots,
                         base_seed + 500 + i)
        xmem.append(x); gen.append(g)
        print(f"  {p:7.4f}{2*p/3:9.4f}{x:11.5f}{g:11.5f}"
              f"{(x/g if g>0 else float('nan')):9.2f}")
    return p_range, np.array(xmem), np.array(gen)


def plot(p, xmem, gen, fname="zmem_vs_xmem_threshold.pdf"):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.loglog(p, gen, "o-", color="#888780", lw=1.6, ms=4,
              label="Generic repetition (Z-memory, 2-term)")
    ax.loglog(p, np.maximum(xmem, 1e-7), "D--", color="#A02060", lw=1.6, ms=4,
              label="33-mode X-memory (phase-flip)")
    ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    ax.set_xlabel(r"Physical error rate $p$ (nominal; $p_{\rm eff}=2p/3$)")
    ax.set_ylabel(r"Logical error rate $p_L$")
    ax.set_title("X-memory (phase-flip) vs generic threshold (d=3, 2-term)")
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")

if __name__ == "__main__":
    print("Validating X-memory circuit...")
    valid = validate_circuit(n_rounds=3)
    c = build_33mode_xmemory(p=0.01, n_rounds=3)
    with open("xmemory_circuit.stim", "w") as f:
        f.write(str(c))
    print(f"[OK] wrote xmemory_circuit.stim ({c.num_qubits} qubits, "
          f"{c.num_detectors} detectors, {c.num_observables} observable)")

    print("\nRunning X-memory vs generic comparison...")
    p, xmem, gen = compare_xmem_vs_generic(n_points=10, n_shots=200_000)
    plot(p, xmem, gen)
    np.savez("xmemory_data.npz", p=p, xmem=xmem, gen=gen)
    print("[OK] saved xmemory_data.npz")

    print("\n--- SELF-CHECKS ---")
    print(f"[{'PASS' if valid else 'FAIL'}] circuit validation "
          f"(deterministic detectors + distance 3)")
    n = 200_000
    ok_pts = tested = 0
    for x, g in zip(xmem, gen):
        if np.isnan(x) or g <= 0:
            continue
        tested += 1
        se = np.sqrt(x * (1 - x) / n + g * (1 - g) / n)
        if abs(x - g) <= 4 * se + 1e-9:
            ok_pts += 1
    okAgree = tested > 0 and ok_pts >= tested - 1
    print(f"[{'PASS' if okAgree else 'FAIL'}] X-memory ~ Z-memory within 4 sigma "
          f"({ok_pts}/{tested}) -- XX layer matches ZZ, no extra overhead")
    print("\nNOTE: this is a SINGLE-BASIS X-memory (dual of the single-basis "
          "Z-memory in 21). It does NOT provide simultaneous X+Z protection -- "
          "a repetition code cannot. Simultaneous correction of both Pauli types "
          "requires a CSS code (Steane/surface). the XX-extraction "
          "layer is validated and symmetric to ZZ, NOT 'universal correction'.")
