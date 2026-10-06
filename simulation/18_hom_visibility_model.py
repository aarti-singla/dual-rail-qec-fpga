# Gate error from HOM visibility via the mode-overlap model.

import numpy as np
import matplotlib as mpl
mpl.rcParams.update({
    "font.family":"serif","font.serif":["Nimbus Roman","DejaVu Serif"],
    "mathtext.fontset":"stix","font.size":9,"axes.labelsize":9.5,"legend.fontsize":7.8,
})
import matplotlib.pyplot as plt
from scipy.integrate import quad


def gaussian_pulse(t: float, t0: float, sigma_t: float) -> complex:
    """Normalized Gaussian temporal mode (unit L2 norm)."""
    norm = 1.0 / (2 * np.pi * sigma_t ** 2) ** 0.25
    return norm * np.exp(-(t - t0) ** 2 / (4 * sigma_t ** 2))


def overlap_two_gaussians(delta_omega: float, delta_t: float,
                          sigma_omega: float) -> float:
    sigma_t = 1.0 / (2 * sigma_omega)
    V = (np.exp(-delta_omega ** 2 / (4 * sigma_omega ** 2))
         * np.exp(-delta_t ** 2 / (4 * sigma_t ** 2)))
    return V


def numerical_overlap(delta_omega: float, sigma_omega: float) -> float:
    """Numerical sanity check: integrate |<psi_1|psi_2>|^2 explicitly."""
    sigma_t = 1.0 / (2 * sigma_omega)

    def integrand_re(t):
        p1 = gaussian_pulse(t, 0.0, sigma_t)
        p2 = gaussian_pulse(t, 0.0, sigma_t) * np.exp(-1j * delta_omega * t)
        return (p1.conjugate() * p2).real

    def integrand_im(t):
        p1 = gaussian_pulse(t, 0.0, sigma_t)
        p2 = gaussian_pulse(t, 0.0, sigma_t) * np.exp(-1j * delta_omega * t)
        return (p1.conjugate() * p2).imag

    re, _ = quad(integrand_re, -10 * sigma_t, 10 * sigma_t)
    im, _ = quad(integrand_im, -10 * sigma_t, 10 * sigma_t)
    return re ** 2 + im ** 2


def critical_mismatch(V_target: float = 0.993) -> float:
    return float(np.sqrt(-4.0 * np.log(V_target)))


def hom_visibility_to_gate_error(V, gate: str = "CZ"):
    """Gate error vs HOM visibility."""
    if gate.upper() == "CZ":
        return (1 - V) / 2
    elif gate.upper() == "FUSION":
        return (1 - V) / 4
    return (1 - V) / 2


def plot_visibility(fname="hom_visibility_model.pdf"):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.66, 2.49))

    # ---- panel a: V vs frequency mismatch ----
    sigma_omega = 1.0  # normalised
    delta_omega = np.linspace(0, 1.0, 400)
    V_vals = np.array([overlap_two_gaussians(d, 0.0, sigma_omega)
                       for d in delta_omega])
    crit = critical_mismatch(0.982)        # analytic, exact -- derived crossing
    ax1.plot(delta_omega / sigma_omega, V_vals, color="#185FA5", lw=2)
    ax1.axhline(0.982, color="gray", ls="--", alpha=0.7,
                label=r"$V=0.982$ requirement")
    ax1.axvline(crit, color="#D85A30", ls=":", alpha=0.8,
                label=fr"$\Delta\omega/\sigma$ = {crit:.3f}")
    ax1.set_xlabel(r"Normalised frequency mismatch  $\Delta\omega / \sigma$")
    ax1.set_ylabel(r"HOM visibility  $V$")
    ax1.set_title("(a) V vs spectral mismatch")
    ax1.legend(); ax1.grid(alpha=0.3)
    ax1.set_ylim(0.96, 1.001)
    ax1.set_xlim(0, 0.5)

    # ---- panel b: gate error vs V ----
    V = np.linspace(0.95, 1.0, 200)
    ax2.semilogy(V, hom_visibility_to_gate_error(V, "CZ"), color="#1D9E75",
                 lw=2, label=r"Post-selected CZ:  $p_{gate}=(1-V)/2$")
    ax2.semilogy(V, hom_visibility_to_gate_error(V, "FUSION"), color="#534AB7",
                 lw=2, ls="--",
                 label=r"Fusion (assumed):  $p_{gate}=(1-V)/4$")
    ax2.axvline(0.982, color="gray", ls="--", alpha=0.7, label=r"$V=0.982$")
    ax2.set_xlabel(r"HOM visibility  $V$")
    ax2.set_ylabel(r"Gate error  $p_{gate}$")
    ax2.set_title("(b) Two-qubit gate error vs V")
    ax2.legend(); ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")


def source_quality_table():
    """Source-quality calibration: V <-> required Delta omega/sigma <-> p_gate."""
    print(f"\n{'V':<10}{'dω/σ (req.)':<14}{'p_gate(CZ)':<14}"
          f"{'p_gate(fusion*)':<16}")
    for V in [0.95, 0.97, 0.99, 0.993, 0.995, 0.999, 0.9999]:
        dw = critical_mismatch(V)
        p_cz = hom_visibility_to_gate_error(V, "CZ")
        p_fus = hom_visibility_to_gate_error(V, "FUSION")
        print(f"{V:<10.4f}{dw:<14.4f}{p_cz:<14.5f}{p_fus:<16.5f}")
    print("* fusion column is a modeling assumption, not a derived/paper value.")
    print("Note: pL(V) is produced by feeding p_gate(V) into the d=3 "
          "repetition MC (07/11); it is not tabulated in this source model.")

if __name__ == "__main__":
    # Numerical sanity check (analytic vs explicit integral)
    V_an = overlap_two_gaussians(0.5, 0.0, 1.0)
    V_num = numerical_overlap(0.5, 1.0)
    print(f"Sanity check: analytic V={V_an:.6f}, numerical V={V_num:.6f}, "
          f"diff={abs(V_an - V_num):.2e}")

    crit = critical_mismatch(0.993)
    print(f"Frequency-matching requirement for V>0.993:  "
          f"Delta omega/sigma < {crit:.4f}")

    source_quality_table()
    plot_visibility()

    # ---- self-checks ----
    print("\n--- SELF-CHECKS ---")
    okSanity = abs(V_an - V_num) < 1e-6
    print(f"[{'PASS' if okSanity else 'FAIL'}] analytic == numerical overlap "
          f"(diff {abs(V_an - V_num):.1e})")
    okCrit = abs(critical_mismatch(0.993) - 0.1676) < 1e-3
    print(f"[{'PASS' if okCrit else 'FAIL'}] V=0.993 critical mismatch = "
          f"{critical_mismatch(0.993):.4f} (expected 0.168, NOT 0.25)")
    okThresh = abs(overlap_two_gaussians(critical_mismatch(0.993), 0.0, 1.0)
                   - 0.993) < 1e-4
    print(f"[{'PASS' if okThresh else 'FAIL'}] round-trip: V(crit) = "
          f"{overlap_two_gaussians(critical_mismatch(0.993), 0.0, 1.0):.4f}")
    print("\n[OK] HOM visibility model complete")
