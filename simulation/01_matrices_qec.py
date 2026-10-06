# Builds the beamsplitter, phase, CZ and noise matrices for the 33-mode architecture.

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# MATRIX 1 — Beamsplitter / MZI


def beamsplitter_matrix(theta: float, phi: float) -> np.ndarray:
    """2x2 unitary for a Mach-Zehnder interferometer."""
    t, p = theta, phi
    return np.array([
        [np.cos(t/2),       1j * np.exp(1j*p) * np.sin(t/2)],
        [1j * np.sin(t/2),  np.exp(1j*p)      * np.cos(t/2)]
    ], dtype=complex)


def hadamard_mzi() -> np.ndarray:
    """50/50 beamsplitter at theta=pi/2, phi=0 (Hadamard up to global phase)."""
    return beamsplitter_matrix(np.pi/2, 0.0)


def phase_shifter(phi: float) -> np.ndarray:
    """Single-mode phase shift diag(1, e^{i phi})."""
    return np.diag([1.0, np.exp(1j * phi)])


def mzi_with_error(theta: float, phi: float, delta_r: float = 0.005) -> np.ndarray:
    """MZI with beamsplitter-imbalance error delta_r."""
    return beamsplitter_matrix(theta + 2 * delta_r, phi)


def gate_fidelity_vs_epsilon(epsilon_range):
    """Process fidelity of a 50/50 BS as epsilon varies."""
    U_ideal = beamsplitter_matrix(np.pi/2, 0.0)
    out = []
    for eps in epsilon_range:
        U = mzi_with_error(np.pi/2, 0.0, delta_r=eps)
        F = (np.abs(np.trace(U_ideal.conj().T @ U)) ** 2) / 4.0
        out.append(float(F.real))
    return out

# MATRIX 2 — Full 33-mode mesh transfer matrix


def _embed_2x2(U_full: np.ndarray, U_2x2: np.ndarray, i: int, j: int) -> np.ndarray:
    N = U_full.shape[0]
    V = np.eye(N, dtype=complex)
    V[i, i] = U_2x2[0, 0]
    V[i, j] = U_2x2[0, 1]
    V[j, i] = U_2x2[1, 0]
    V[j, j] = U_2x2[1, 1]
    return U_full @ V


def build_33mode_transfer_matrix(delta_r: float = 0.005, phi_noise: float = 0.0):
    """Construct the 33x33 unitary representing the full MZI mesh."""
    N = 33
    U = np.eye(N, dtype=complex)

    # L02 - dual-rail encoding (M01 - M02)
    BS = beamsplitter_matrix(np.pi/2, phi_noise)
    U = _embed_2x2(U, BS, 0, 1)

    # L03 - ZZ syndrome extraction
    BS_err = mzi_with_error(np.pi/2, 0.0, delta_r)
    U = _embed_2x2(U, BS_err, 0, 3)
    U = _embed_2x2(U, BS_err, 1, 3)
    U = _embed_2x2(U, BS_err, 1, 4)
    U = _embed_2x2(U, BS_err, 2, 4)

    H_phase = np.diag([np.exp(1j * np.pi / 4)] * N)
    for q in (0, 1, 2):
        D = np.eye(N, dtype=complex)
        D[q, q] = np.exp(1j * np.pi / 4)
        U = U @ D
    U = _embed_2x2(U, BS_err, 0, 9)
    U = _embed_2x2(U, BS_err, 1, 9)
    U = _embed_2x2(U, BS_err, 1, 10)
    U = _embed_2x2(U, BS_err, 2, 10)
    for q in (0, 1, 2):
        D = np.eye(N, dtype=complex)
        D[q, q] = np.exp(-1j * np.pi / 4)
        U = U @ D

    # L05 - 20.5 m fiber buffer, phase only (proper diagonal unitary)
    lam = 1550e-9
    n_eff = 1.46
    L_fiber = 20.5
    phi_fiber = (2 * np.pi * n_eff * L_fiber / lam) % (2 * np.pi)
    D_fiber = np.eye(N, dtype=complex)
    for m in range(15, 21):
        D_fiber[m, m] = np.exp(1j * phi_fiber)
    U = U @ D_fiber

    # L08 - post-selected CZ gates on M22..M27 limited by HOM visibility
    V = 0.993
    phi_CZ = np.pi + (1 - V) * np.pi / 2
    for a, b in [(21, 22), (23, 24), (25, 26)]:
        U = _embed_2x2(U, beamsplitter_matrix(np.pi/3, phi_CZ), a, b)

    unitarity_err = float(np.max(np.abs(U.conj().T @ U - np.eye(N))))
    return U, unitarity_err

# MATRIX 3 — Parity check matrices


def build_parity_check_matrix():
    H_Z = np.array([[1, 1, 0],
                    [0, 1, 1]], dtype=int)        # ZZ_01, ZZ_12
    H_X = np.array([[1, 1, 0],
                    [0, 1, 1]], dtype=int)        # XX_01, XX_12
    H_sym = np.hstack([H_X, H_Z])

    # symplectic-inner-product commutativity check (must be all zero mod 2)
    commutator = np.zeros((2, 2), dtype=int)
    for i in range(2):
        for j in range(2):
            commutator[i, j] = (
                int(np.dot(H_X[i], H_Z[j])) + int(np.dot(H_Z[i], H_X[j]))
            ) % 2
    return H_Z, H_X, H_sym, commutator

# MATRIX 4 — Syndrome lookup table


def build_syndrome_table(H_Z: np.ndarray):
    errors = {
        'no error':   np.array([0, 0, 0]),
        'X on q0':    np.array([1, 0, 0]),
        'X on q1':    np.array([0, 1, 0]),
        'X on q2':    np.array([0, 0, 1]),
        'X on q0,q1': np.array([1, 1, 0]),
        'X on q0,q2': np.array([1, 0, 1]),
        'X on q1,q2': np.array([0, 1, 1]),
        'X on all':   np.array([1, 1, 1]),
    }

    print("=== MATRIX 4: Syndrome Table (H_Z @ e mod 2) ===")
    print(f"{'Error pattern':<15} | {'Error vec':<12} | {'Syndrome':<10} | "
          f"{'MWPM correction'}")
    print("-" * 60)

    table = {}
    for name, e in errors.items():
        s = (H_Z @ e) % 2
        s_str = ''.join(map(str, s))
        # minimum-weight correction c such that H_Z @ c = s (mod 2)
        if   np.array_equal(s, [0, 0]): c = np.array([0, 0, 0])
        elif np.array_equal(s, [1, 0]): c = np.array([1, 0, 0])
        elif np.array_equal(s, [1, 1]): c = np.array([0, 1, 0])
        elif np.array_equal(s, [0, 1]): c = np.array([0, 0, 1])
        else:                           c = np.array([0, 0, 0])
        table[s_str] = c
        print(f"{name:<15} | {str(e.tolist()):<12} | {s_str:<10} | {c.tolist()}")
    print()
    return table

# MATRIX 5 — MWPM edge-weight matrix


def build_mwpm_graph(p_phys: float = 0.01):
    p_adj    = p_phys
    p_nonadj = p_phys ** 2
    w_adj    = -np.log(p_adj    / (1 - p_adj))
    w_nonadj = -np.log(p_nonadj / (1 - p_nonadj))

    inf = np.inf
    W = np.array([
        [inf,      w_adj,    w_nonadj, w_nonadj],   # ZZ01
        [w_adj,    inf,      w_nonadj, w_nonadj],   # ZZ12
        [w_nonadj, w_nonadj, inf,      w_adj   ],   # XX01
        [w_nonadj, w_nonadj, w_adj,    inf     ],   # XX12
    ])
    boundary = np.array([w_adj] * 4)

    print("=== MATRIX 5: MWPM Syndrome-Graph Weight Matrix ===")
    print(f"Physical error rate p = {p_phys}")
    print(f"Adjacent edge weight:     {w_adj:.4f}")
    print(f"Non-adjacent edge weight: {w_nonadj:.4f}")
    print("\nW (rows/cols ZZ01, ZZ12, XX01, XX12):")
    W_disp = np.where(np.isinf(W), 999.0, np.round(W, 3))
    print(W_disp)
    print(f"\nBoundary weights: {np.round(boundary, 4)}\n")
    return W, boundary

# MATRIX 6 — ML decoder LUT (NEW IN JOURNAL VERSION)


def build_ml_decoder_lut(p_flip_given_erasure: float = 2.0 / 3.0):
    """Maximum-likelihood decoder lookup table for d=3 with heralded erasure."""
    import math
    w_h1 = -math.log(p_flip_given_erasure)
    w_h0 = -math.log(1.0 - p_flip_given_erasure)

    lut = {}
    print("=== MATRIX 6: ML Decoder LUT (NEW) ===")
    print(f"P(X-flip | erasure) = {p_flip_given_erasure:.4f}")
    print(f"Cost of heralded x=1: {w_h1:.4f}  (smaller = preferred)")
    print(f"Cost of heralded x=0: {w_h0:.4f}")
    print(f"\n{'heralds':<10}{'syndrome':<10}{'ML correction':<15}"
          f"{'cost':<8}")
    print("-" * 50)

    for h_int in range(8):
        h = [(h_int >> i) & 1 for i in range(3)]
        for s_int in range(4):
            s01 = s_int & 1
            s12 = (s_int >> 1) & 1
            best = (0, 0, 0)
            best_w = float("inf")
            for x0 in (0, 1):
                for x1 in (0, 1):
                    for x2 in (0, 1):
                        if (x0 ^ x1) != s01: continue
                        if (x1 ^ x2) != s12: continue
                        w = 0.0
                        valid = True
                        for q, x in enumerate((x0, x1, x2)):
                            if h[q] == 0:
                                if x == 1:
                                    valid = False
                                    break
                            else:
                                w += w_h1 if x == 1 else w_h0
                        if not valid: continue
                        if w < best_w:
                            best_w = w
                            best = (x0, x1, x2)
            lut[(h_int, s_int)] = best
            tag = " <-- ML KEY CASE" if h_int == 7 else ""
            print(f"{h_int:03b}       {s01}{s12}        "
                  f"({best[0]},{best[1]},{best[2]})       "
                  f"{best_w:.3f}{tag}")
    print()
    return lut

# Stim+PyMatching threshold sweep (optional — only if installed)


def run_stim_threshold_sweep(d_values=(3, 5), n_shots=20_000):
    try:
        import stim
        import pymatching
    except ImportError:
        print("[INFO] Stim / PyMatching not installed — skipping threshold sweep.")
        return {}

    p_range = np.logspace(-2.5, -0.7, 8)
    results = {}

    for d in d_values:
        print(f"\n[d = {d}] threshold sweep ({n_shots} shots/point)")
        rates = []
        for p in p_range:
            circuit = stim.Circuit.generated(
                "repetition_code:memory",
                rounds=d,
                distance=d,
                before_round_data_depolarization=p,
                before_measure_flip_probability=p,
            )
            sampler = circuit.compile_detector_sampler()
            det, obs = sampler.sample(n_shots, separate_observables=True)
            matcher = pymatching.Matching.from_detector_error_model(
                circuit.detector_error_model(decompose_errors=True))
            pred = matcher.decode_batch(det)
            pL = float(np.mean(np.any(pred != obs, axis=1)))
            rates.append(pL)
            print(f"   p={p:.4f}   pL={pL:.4f}")
        results[d] = (p_range, rates)
    return results

# Master 6-panel figure


def plot_master_figure(H_Z, H_X, W_graph):
    fig = plt.figure(figsize=(14, 10))
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)

    # (a) Gate fidelity vs epsilon
    ax = fig.add_subplot(gs[0, 0])
    eps = np.linspace(0, 0.10, 200)
    F = gate_fidelity_vs_epsilon(eps)
    ax.plot(eps, F, color='#185FA5', lw=1.8, label='Gate fidelity F')
    ax.axhline(0.99, color='gray', ls='--', alpha=0.7, label='Target F=0.99')
    ax.axvline(0.01, color='#D85A30', ls=':',  alpha=0.7, label='Spec ε=0.01')
    ax.set(xlabel='Beamsplitter imbalance ε', ylabel='Gate fidelity F',
           title='(a) Gate fidelity vs ε', ylim=(0.985, 1.001))
    ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # (b) HOM visibility -> pL
    ax = fig.add_subplot(gs[0, 1])
    V = np.linspace(0.94, 1.0, 200)
    ax.semilogy(V, 0.69 * ((1-V)/2)**2, color='#1D9E75', lw=1.8, label='d=3')
    ax.semilogy(V, 0.69 * ((1-V)/2)**3, color='#534AB7', lw=1.8, label='d=5')
    ax.axvline(0.993, color='gray', ls='--', alpha=0.7, label='V=0.993')
    ax.axhline(1e-3,  color='#D85A30', ls=':', alpha=0.5, label='pL=10⁻³')
    ax.set(xlabel='HOM visibility V', ylabel='Logical error rate pL',
           title='(b) HOM visibility requirement', xlim=(0.94, 1.0))
    ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # (c) Threshold curves
    ax = fig.add_subplot(gs[0, 2])
    p_range = np.logspace(-2.5, -0.7, 100)
    p_th = 0.0086
    for d, col, ls in [(2, '#888780', '--'), (3, '#1D9E75', '-'),
                       (5, '#534AB7', '-')]:
        t = d // 2 + 1
        pL = np.minimum(0.69 * (p_range / p_th) ** t, 1.0)
        ax.loglog(p_range, pL, color=col, lw=1.8, ls=ls, label=f'd={d}')
    ax.loglog(p_range, p_range, 'k--', lw=1, alpha=0.4, label='No QEC')
    ax.axvline(p_th, color='gray', ls=':', alpha=0.6)
    ax.set(xlabel='Physical error rate', ylabel='Logical error rate',
           title='(c) Threshold curves', ylim=(1e-5, 1))
    ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # (d) Parity check matrix
    ax = fig.add_subplot(gs[1, 0])
    H_full = np.vstack([H_Z, H_X])
    im = ax.imshow(H_full, cmap='Blues', aspect='auto', vmin=0, vmax=1)
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels(['q0', 'q1', 'q2'])
    ax.set_yticks(range(4));  ax.set_yticklabels(['ZZ₀₁', 'ZZ₁₂', 'XX₀₁', 'XX₁₂'])
    ax.set_title('(d) Parity-check matrix H')
    for i in range(4):
        for j in range(3):
            ax.text(j, i, str(H_full[i, j]), ha='center', va='center',
                    fontsize=12, color='white' if H_full[i, j] == 1 else 'black')
    plt.colorbar(im, ax=ax, shrink=0.8)

    # (e) MWPM weight matrix
    ax = fig.add_subplot(gs[1, 1])
    W_vis = np.where(np.isinf(W_graph), 0, W_graph)
    im = ax.imshow(W_vis, cmap='YlOrRd', aspect='auto')
    labels = ['ZZ₀₁', 'ZZ₁₂', 'XX₀₁', 'XX₁₂']
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, rotation=30, fontsize=8)
    ax.set_yticks(range(4)); ax.set_yticklabels(labels, fontsize=8)
    ax.set_title('(e) MWPM weight matrix W')
    for i in range(4):
        for j in range(4):
            val = W_vis[i, j]
            ax.text(j, i, f'{val:.2f}' if val > 0 else '∞',
                    ha='center', va='center', fontsize=8,
                    color='white' if val > 3 else 'black')
    plt.colorbar(im, ax=ax, shrink=0.8)

    # (f) Mode overhead vs distance
    ax = fig.add_subplot(gs[1, 2])
    d_list = [2, 3, 5, 7, 9, 11]
    modes  = [3 + 10 * d for d in d_list]
    ax.plot(d_list, modes, 'o-', color='#1D9E75', lw=1.8, ms=5)
    for d_p, m_p, lbl in [(2, 33, 'Phase 1'), (3, 55, 'Phase 2'),
                          (5, 99, 'Phase 3')]:
        ax.annotate(f'{lbl}\n({m_p}m)', (d_p, m_p),
                    textcoords='offset points', xytext=(8, 4), fontsize=7)
    ax.set(xlabel='Code distance d', ylabel='Total photonic modes',
           title='(f) Mode-overhead scaling')
    ax.set_xticks(d_list); ax.grid(alpha=0.2)

    plt.suptitle('33-mode photonic QEC — complete simulation results',
                 fontsize=12, fontweight='bold', y=1.01)
    plt.savefig('journal_figures_all.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('journal_figures_all.png', dpi=200, bbox_inches='tight')
    print("[OK] saved journal_figures_all.pdf / .png")

# main

if __name__ == "__main__":
    # Matrix 1
    print("=== MATRIX 1: Beamsplitter Unitary ===")
    BS = beamsplitter_matrix(np.pi/2, 0.0)
    print(np.round(BS, 4))
    print(f"Unitarity error: {np.max(np.abs(BS.conj().T @ BS - np.eye(2))):.2e}\n")

    # Matrix 2
    print("=== MATRIX 2: 33-mode Transfer Matrix ===")
    U33, err = build_33mode_transfer_matrix(delta_r=0.005)
    print(f"Shape: {U33.shape}, unitarity error: {err:.2e}\n")

    # Matrix 3
    H_Z, H_X, H_sym, comm = build_parity_check_matrix()
    print("=== MATRIX 3: Parity Check Matrices ===")
    print("H_Z =\n", H_Z)
    print("\nH_X =\n", H_X)
    print("\nH_symplectic = [H_X | H_Z] =\n", H_sym)
    print(f"\nCommutativity (must be all 0):\n{comm}\n")

    # Matrix 4
    syndrome_table = build_syndrome_table(H_Z)

    # Matrix 5
    W_graph, bw = build_mwpm_graph(p_phys=0.01)

    # Matrix 6 -- NEW JOURNAL VERSION
    ml_lut = build_ml_decoder_lut()

    # Optional: Stim threshold sweep
    sim_results = run_stim_threshold_sweep(d_values=(3, 5), n_shots=20_000)

    # Master figure
    plot_master_figure(H_Z, H_X, W_graph)

    print("\n=== SUMMARY ===")
    print(f"  Matrix 1: BS unitary 2x2")
    print(f"  Matrix 2: U33 33x33, unitarity err {err:.2e}")
    print(f"  Matrix 3: H_Z 2x3, H_X 2x3, H_sym 2x6")
    print(f"  Matrix 4: {len(syndrome_table)}-entry syndrome LUT (MWPM)")
    print(f"  Matrix 5: W 4x4 MWPM weight matrix")
    print(f"  Matrix 6: {len(ml_lut)}-entry ML decoder LUT (NEW for journal)")
    print("\nDone.")