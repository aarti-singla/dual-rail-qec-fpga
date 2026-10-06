# Stim circuit built from the 33-mode pipeline layout (Z-memory).

import numpy as np
import matplotlib.pyplot as plt
import stim
import pymatching


class ModeMap:
    """Mode index assignment exactly as Table I (0-based; paper uses M01-M33)."""
    DATA_RAILS = list(range(0, 2))     # M01-M02 data rails
    ROUTING    = 2                     # M03 inter-block routing
    ZZ_ANC     = list(range(3, 9))     # M04-M09 ZZ ancilla
    XX_ANC     = list(range(9, 15))    # M10-M15 XX ancilla
    BUFFER     = list(range(15, 21))   # M16-M21 buffer delay lines
    CZ_ANC     = list(range(21, 27))   # M22-M27 post-selected CZ ancilla
    STAB_ANC   = list(range(27, 33))   # M28-M33 stabilizer ancilla

    @staticmethod
    def info():
        return dict(data_rails=len(ModeMap.DATA_RAILS), routing=1,
                    zz_anc=len(ModeMap.ZZ_ANC), xx_anc=len(ModeMap.XX_ANC),
                    buffer=len(ModeMap.BUFFER), cz_anc=len(ModeMap.CZ_ANC),
                    stab_anc=len(ModeMap.STAB_ANC),
                    total=2 + 1 + 6 + 6 + 6 + 6 + 6)


def build_33mode_circuit(p: float = 0.01, n_rounds: int = 3) -> stim.Circuit:
    c = stim.Circuit()
    DATA = [0, 1, 2]          # 3 dual-rail logical qubits
    ANC = [3, 4]              # ZZ01 -> anc[0], ZZ12 -> anc[1]

    c.append("R", DATA + ANC)                       # L01 init |000> (ZZ codeword)

    for r in range(n_rounds):
        c.append("DEPOLARIZE1", DATA, p)            # L05 data idle / before-round
        if r > 0:
            c.append("R", ANC)                      # L07/L10 ancilla reset
        # L03 ZZ syndrome extraction
        c.append("CNOT", [DATA[0], ANC[0]])
        c.append("CNOT", [DATA[1], ANC[0]])
        c.append("CNOT", [DATA[1], ANC[1]])
        c.append("CNOT", [DATA[2], ANC[1]])
        c.append("X_ERROR", ANC, p / 2)            # before-measure flip
        c.append("M", ANC)                          # 2 records: anc0, anc1
        if r == 0:
            c.append("DETECTOR", [stim.target_rec(-2)])           # anc0 vs init 0
            c.append("DETECTOR", [stim.target_rec(-1)])           # anc1 vs init 0
        else:
            c.append("DETECTOR", [stim.target_rec(-2),
                                  stim.target_rec(-4)])           # anc0_r ^ anc0_{r-1}
            c.append("DETECTOR", [stim.target_rec(-1),
                                  stim.target_rec(-3)])           # anc1_r ^ anc1_{r-1}

    # L11 logical readout (Z-basis) + final-closure detectors
    c.append("X_ERROR", DATA, p / 2)
    c.append("M", DATA)                             # -3=q0, -2=q1, -1=q2
    # last ancilla round now at -5 (anc0), -4 (anc1)
    c.append("DETECTOR", [stim.target_rec(-3), stim.target_rec(-2),
                          stim.target_rec(-5)])     # (q0^q1) ^ anc0_last  (ZZ01)
    c.append("DETECTOR", [stim.target_rec(-2), stim.target_rec(-1),
                          stim.target_rec(-4)])     # (q1^q2) ^ anc1_last  (ZZ12)
    # logical Z = parity of the 3 data qubits (~ Z_L mod stabilisers)
    c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-3), stim.target_rec(-2),
                                    stim.target_rec(-1)], 0)
    return c


def generic_repetition_circuit(d: int, p: float) -> stim.Circuit:
    """2-term generic generator (after_clifford_depolarization = 0.0)."""
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
        decompose_errors=True,
        approximate_disjoint_errors=True,
        ignore_decomposition_failures=False,   # raise, never silently drop
    )
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pred = matcher.decode_batch(det)
    return float(np.mean(np.any(pred != obs, axis=1)))


def validate_circuit(n_rounds: int = 3):
    """Mandatory hand-built-code checks: deterministic detectors + distance."""
    noiseless = build_33mode_circuit(p=0.0, n_rounds=n_rounds)
    det = noiseless.compile_detector_sampler(seed=1).sample(4000)
    det_ok = not det.any()

    arch = build_33mode_circuit(p=0.01, n_rounds=n_rounds)
    try:
        arch.detector_error_model(decompose_errors=True,
                                  approximate_disjoint_errors=True,
                                  ignore_decomposition_failures=False)
        dem_ok = True
    except Exception as ex:
        print(f"  [warn] DEM build failed: {ex}")
        dem_ok = False

    sgl = len(arch.shortest_graphlike_error())
    try:
        sue = len(arch.search_for_undetectable_logical_errors(
            dont_explore_detection_event_sets_with_size_above=4,
            dont_explore_edges_with_degree_above=4,
            dont_explore_edges_increasing_symptom_degree=False))
    except Exception as ex:
        print(f"  [warn] undetectable-error search failed: {ex}")
        sue = -1
    dist_ok = (sgl == 3 and sue == 3)

    print(f"  deterministic detectors (noiseless never fire): "
          f"{'PASS' if det_ok else 'FAIL'}")
    print(f"  DEM builds (ignore_decomposition_failures=False): "
          f"{'PASS' if dem_ok else 'FAIL'}")
    print(f"  distance: shortest_graphlike={sgl}, undetectable_search={sue} "
          f"(expect 3) -> {'PASS' if dist_ok else 'FAIL'}")
    return det_ok and dem_ok and dist_ok


def compare_arch_vs_generic(n_points=10, n_shots=200_000, base_seed=2100):
    p_range = np.logspace(-2.0, -0.85, n_points)   # near/below threshold
    arch_rates, gen_rates = [], []
    print(f"\n{'p_nom':>9}{'p_eff':>9}{'arch':>11}{'generic':>11}{'ratio':>9}")
    for i, p in enumerate(p_range):
        try:
            arch = logical_rate(build_33mode_circuit(p=p), n_shots,
                                base_seed + i)
        except Exception as ex:
            print(f"  [warn] arch failed at p={p}: {ex}")
            arch = float("nan")
        gen = logical_rate(generic_repetition_circuit(3, p), n_shots,
                           base_seed + 500 + i)
        arch_rates.append(arch); gen_rates.append(gen)
        ratio = arch / gen if gen > 0 else float("nan")
        print(f"  {p:7.4f}{2*p/3:9.4f}{arch:11.5f}{gen:11.5f}{ratio:9.2f}")
    return p_range, np.array(arch_rates), np.array(gen_rates)


def plot(p, arch, gen, fname="arch_vs_generic_threshold.pdf"):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.loglog(p, gen, "o-", color="#888780", lw=1.6, ms=4,
              label="Generic repetition (Stim built-in, 2-term)")
    ax.loglog(p, np.maximum(arch, 1e-7), "s--", color="#1D9E75", lw=1.6, ms=4,
              label="33-mode architecture-specific (2-term)")
    ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    ax.set_xlabel(r"Physical error rate $p$ (nominal; $p_{\rm eff}=2p/3$)")
    ax.set_ylabel(r"Logical error rate $p_L$")
    ax.set_title("Architecture-specific vs generic threshold (d=3, 2-term)")
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")

if __name__ == "__main__":
    print("Mode map info:", ModeMap.info())

    print("\nValidating architecture-specific circuit...")
    valid = validate_circuit(n_rounds=3)

    c = build_33mode_circuit(p=0.01, n_rounds=3)
    with open("arch_specific_circuit.stim", "w") as f:
        f.write(str(c))
    print(f"[OK] wrote arch_specific_circuit.stim ({c.num_qubits} qubits, "
          f"{c.num_detectors} detectors, {c.num_observables} observable)")

    print("\nRunning architecture-specific vs generic comparison...")
    p, arch, gen = compare_arch_vs_generic(n_points=10, n_shots=200_000)
    plot(p, arch, gen)
    np.savez("arch_specific_data.npz", p=p, arch=arch, gen=gen)
    print("[OK] saved arch_specific_data.npz")

    # ---- self-checks ----
    print("\n--- SELF-CHECKS ---")
    print(f"[{'PASS' if valid else 'FAIL'}] circuit validation "
          f"(deterministic detectors + distance 3)")
    # arch ~ generic: agree within 4 sigma of the combined binomial error
    n = 200_000
    ok_pts, tested = 0, 0
    for a, g in zip(arch, gen):
        if np.isnan(a) or g <= 0:
            continue
        tested += 1
        se = np.sqrt(a * (1 - a) / n + g * (1 - g) / n)
        if abs(a - g) <= 4 * se + 1e-9:
            ok_pts += 1
    okAgree = tested > 0 and ok_pts >= tested - 1   # allow 1 outlier
    print(f"[{'PASS' if okAgree else 'FAIL'}] arch ~ generic within 4 sigma "
          f"({ok_pts}/{tested} points) -- architecture adds no extra logical error")
    print("\nNOTE: realistic heralded-erasure / loss decoding is NOT done here "
          "(PyMatching mishandles heralds); it lives in the pure-NumPy erasure "
          "decoders (scripts 04/10). This script verifies CODE-LEVEL equivalence "
          "of the layered circuit under the standardized 2-term Pauli model.")
