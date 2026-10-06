# Density-matrix noise model (loss, dark counts, dephasing) for a dual-rail qubit.

import numpy as np

# Kraus channels


def photon_loss_kraus(eta: float):
    """Amplitude-damping Kraus ops for a bosonic mode truncated to {|0>, |1>}."""
    K0 = np.array([[1, 0],
                   [0, np.sqrt(eta)]], dtype=complex)
    K1 = np.array([[0, np.sqrt(1 - eta)],
                   [0, 0]], dtype=complex)
    return [K0, K1]


def apply_kraus_channel(rho: np.ndarray, kraus_ops) -> np.ndarray:
    """Apply a Kraus channel sum_i K_i rho K_i^dag to rho."""
    out = np.zeros_like(rho)
    for K in kraus_ops:
        out += K @ rho @ K.conj().T
    return out


def hom_visibility_to_gate_error(V: float) -> float:
    """HOM visibility V -> CZ gate error p_gate = (1 - V) / 2."""
    return (1 - V) / 2

# Dual-rail loss + dark counts


def simulate_dual_rail_loss(psi_logical, p_loss: float, p_dark: float = 1e-4):
    """Apply loss and dark counts to a dual-rail qubit."""
    alpha, beta = psi_logical
    # Fock basis for two modes truncated to one photon total:
    # |00>, |10>, |01>, |11>
    psi_fock = np.array([0, alpha, beta, 0], dtype=complex)
    rho = np.outer(psi_fock, psi_fock.conj())

    eta = 1 - p_loss

    # Loss on mode 1 (first rail)
    K0_m1 = np.diag([1, np.sqrt(eta), 1, np.sqrt(eta)]).astype(complex)
    K1_m1 = np.zeros((4, 4), dtype=complex)
    K1_m1[0, 1] = np.sqrt(1 - eta)
    K1_m1[2, 3] = np.sqrt(1 - eta)
    rho = apply_kraus_channel(rho, [K0_m1, K1_m1])

    # Loss on mode 2 (second rail)
    K0_m2 = np.diag([1, 1, np.sqrt(eta), np.sqrt(eta)]).astype(complex)
    K1_m2 = np.zeros((4, 4), dtype=complex)
    K1_m2[0, 2] = np.sqrt(1 - eta)
    K1_m2[1, 3] = np.sqrt(1 - eta)
    rho = apply_kraus_channel(rho, [K0_m2, K1_m2])

    p_erasure = float(rho[0, 0].real)

    # Dark counts: vacuum can spuriously click
    rho[1, 1] += p_dark * rho[0, 0]
    rho[2, 2] += p_dark * rho[0, 0]
    rho[0, 0] *= (1 - 2 * p_dark)

    return rho, p_erasure

# HOM dip Monte Carlo


def hom_dip_simulation(V: float, n_trials: int = 100_000) -> float:
    """Monte Carlo of two-photon coincidence at a 50/50 BS."""
    rng = np.random.default_rng(0)
    coinc = 0
    for _ in range(n_trials):
        if rng.random() > V:
            coinc += int(rng.random() < 0.5)
    return coinc / n_trials

# main

if __name__ == "__main__":
    print("Sweeping HOM visibility V...\n")
    print(f"{'V':>8} | {'p_gate=(1-V)/2':>15} | {'coinc rate (MC)':>17}")
    print("-" * 48)
    for V in [0.95, 0.97, 0.99, 0.993, 0.995, 0.999]:
        p_gate = hom_visibility_to_gate_error(V)
        p_coinc = hom_dip_simulation(V, n_trials=50_000)
        print(f"{V:>8.3f} | {p_gate:>15.5f} | {p_coinc:>17.5f}")

    print("\nDual-rail loss check (|+_L> state, p_loss=0.05):")
    psi = np.array([1, 1]) / np.sqrt(2)
    rho, p_era = simulate_dual_rail_loss(psi, p_loss=0.05, p_dark=1e-5)
    trace = float(np.trace(rho).real)
    print(f"  Trace(rho) = {trace:.5f}")
    print(f"  Erasure probability  = {p_era:.5f}")
    print(f"  Diagonal occupation  = {np.round(np.diag(rho).real, 5).tolist()}")
