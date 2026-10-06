# Assembles the multi-panel summary figure from the .npz outputs of scripts 07-12.

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os


def try_load(path):
    return np.load(path) if os.path.exists(path) else None


def _missing(ax, msg):
    ax.text(0.5, 0.5, msg, ha="center", va="center", transform=ax.transAxes,
            fontsize=9, color="gray", style="italic")


def gate_fidelity_vs_epsilon(eps):
    # Script-05 analytic. 0.993 is a PLACEHOLDER (HOM-visibility number, not a
    return 1.0 - 0.993 * eps ** 2


def main():
    fig = plt.figure(figsize=(16, 12))
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.42, wspace=0.32)
    colors = dict(d3="#1D9E75", d5="#534AB7", d7="#D85A30",
                  pauli="#888780", mwpm="#1D9E75", ml="#A02060",
                  surf="#534AB7", rep="#1D9E75")

    # ---- (a) architecture placeholder
    ax = fig.add_subplot(gs[0, 0])
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("(a) 33-mode pipeline architecture", fontsize=11)
    layers = ["L01\nInject", "L02\nEncode", "L03\nZZ", "L04\nXX",
              "L05\nBuffer", "L06\nCorrect", "L08\nCZ", "L11\nReadout"]
    for i, lab in enumerate(layers):
        x = 0.05 + (i / len(layers)) * 0.9
        ax.add_patch(plt.Rectangle((x, 0.35), 0.10, 0.30,
                                    facecolor="#E8F4F0", edgecolor="#1D9E75"))
        ax.text(x + 0.05, 0.50, lab, ha="center", va="center", fontsize=7)
    ax.text(0.5, 0.10, "Replace with the TikZ pipeline figure",
            ha="center", style="italic", color="gray", fontsize=8)

    # ---- (b) gate fidelity vs epsilon (script-05 analytic)
    ax = fig.add_subplot(gs[0, 1])
    eps = np.linspace(0, 0.10, 200)
    ax.plot(eps, gate_fidelity_vs_epsilon(eps), color="#185FA5", lw=1.8,
            label="Gate fidelity F")
    ax.axhline(0.99, color="gray", ls="--", alpha=0.7, label="Target F=0.99")
    ax.axvline(0.01, color="#D85A30", ls=":", alpha=0.7, label=r"Spec $\varepsilon$=0.01")
    ax.set(xlabel=r"Beamsplitter imbalance  $\varepsilon$",
           ylabel="Gate fidelity  F", title=r"(b) Gate fidelity vs $\varepsilon$",
           ylim=(0.985, 1.001))
    ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # ---- (c) HOM visibility vs pL (schematic)
    ax = fig.add_subplot(gs[0, 2])
    V = np.linspace(0.94, 1.0, 200)
    ax.semilogy(V, 0.69 * ((1 - V) / 2) ** 2, color=colors["d3"], lw=1.8, label="d=3")
    ax.semilogy(V, 0.69 * ((1 - V) / 2) ** 3, color=colors["d5"], lw=1.8, label="d=5")
    ax.axvline(0.993, color="gray", ls="--", alpha=0.7, label="V=0.993")
    ax.set(xlabel="HOM visibility V", ylabel=r"Logical error rate $p_L$",
           title="(c) HOM visibility requirement", xlim=(0.94, 1.0))
    ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # ---- (d) repetition d=3,5,7  (script 07)
    ax = fig.add_subplot(gs[1, 0])
    data = try_load("threshold_d5_data.npz")
    if data is not None:
        p = data["p"]
        for d in (3, 5, 7):
            if f"d{d}" in data.files:
                ax.loglog(p, np.maximum(data[f"d{d}"], 1e-7), "o-",
                          color=colors[f"d{d}"], lw=1.6, ms=4, label=f"d={d}")
        ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    else:
        _missing(ax, "Run 07_repetition_d5_simulation.py")
    ax.set(xlabel=r"$p_\mathrm{phys}$", ylabel=r"$p_L$", title="(d) Repetition d=3, 5, 7")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # ---- (e) surface Z/X vs rep at d=3 (script 08)
    ax = fig.add_subplot(gs[1, 1])
    data = try_load("surface_d3_data.npz")
    if data is not None and {"surf_z", "surf_x", "rep"} <= set(data.files):
        p = data["p"]
        ax.loglog(p, np.maximum(data["surf_z"], 1e-7), "o-", color=colors["d3"],
                  lw=1.6, ms=4, label="Surface d=3 Z-mem")
        ax.loglog(p, np.maximum(data["surf_x"], 1e-7), "s-", color=colors["d5"],
                  lw=1.6, ms=4, label="Surface d=3 X-mem")
        ax.loglog(p, np.maximum(data["rep"], 1e-7), "^--", color="#888780",
                  lw=1.4, ms=4, label="Repetition d=3")
        ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    else:
        _missing(ax, "Run 08_surface_code_d3.py")
    ax.set(xlabel=r"$p_\mathrm{phys}$", ylabel=r"$p_L$",
           title="(e) Surface vs repetition at d=3")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # ---- (f) surface d=3 vs d=5 (script 09)
    ax = fig.add_subplot(gs[1, 2])
    data = try_load("surface_d5_data.npz")
    if data is not None:
        p = data["p"]
        for d in (3, 5):
            if f"d{d}" in data.files:
                ax.loglog(p, np.maximum(data[f"d{d}"], 1e-7), "o-",
                          color=colors[f"d{d}"], lw=1.6, ms=4, label=f"Surface d={d}")
        ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    else:
        _missing(ax, "Run 09_surface_code_d5.py")
    ax.set(xlabel=r"$p_\mathrm{phys}$", ylabel=r"$p_L$",
           title="(f) Surface scaling: d=3 vs d=5")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # ---- (g) heralded erasure decoding (script 10): Pauli / MWPM-H / ML-H
    ax = fig.add_subplot(gs[2, 0])
    data = try_load("calibrated_loss_data.npz")
    if data is not None:
        p = data["p"]
        for key, lbl, c, m in [("pauli", "Pauli approx.", colors["pauli"], "o"),
                               ("mwpm_h", "MWPM-heralded", colors["mwpm"], "s"),
                               ("ml_h", "ML-heralded", colors["ml"], "D")]:
            if key in data.files:
                ax.loglog(p, np.maximum(data[key], 1e-7), "-", marker=m,
                          color=c, lw=1.6, ms=4, label=lbl)
        ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    else:
        _missing(ax, "Run 10_calibrated_loss_model.py")
    ax.set(xlabel=r"$p$", ylabel=r"$p_L$", title="(g) Heralded erasure decoding")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # ---- (h) code family comparison (script 12)
    ax = fig.add_subplot(gs[2, 1])
    data = try_load("code_family_comparison.npz")
    if data is not None:
        p = data["p"]
        for key, lbl, c, m in [
            ("Repetition_d3",    "Rep d=3",    colors["d3"], "o"),
            ("Surface_d3_Z-mem", "Surf d=3 Z", colors["d5"], "s"),
            ("Surface_d3_X-mem", "Surf d=3 X", "#9B7AC9",    "^"),
        ]:
            if key in data.files:
                ax.loglog(p, np.maximum(data[key], 1e-7), "-", marker=m,
                          color=c, lw=1.6, ms=4, label=lbl)
        ax.loglog(p, p, "k--", alpha=0.4, label="No QEC")
    else:
        _missing(ax, "Run 12_code_family_comparison.py")
    ax.set(xlabel=r"$p_\mathrm{phys}$", ylabel=r"$p_L$",
           title="(h) Code family comparison")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.legend(fontsize=8); ax.grid(alpha=0.2)

    # ---- (i) resource scaling (formulas consistent with the paper + 08/09/13)
    ax = fig.add_subplot(gs[2, 2])
    d_list = np.array([2, 3, 5, 7, 9, 11])
    modes_rep = 22 * d_list - 11             # 33/55/99 at d=2/3/5 (paper)
    modes_surface = 18 * d_list ** 2 - 12    # 150/438 at d=3/5 (08/09/13)
    ax.semilogy(d_list, modes_rep, "o-", color=colors["d3"], lw=1.8, ms=5,
                label="Repetition (this work)")
    ax.semilogy(d_list, modes_surface, "s-", color=colors["d5"], lw=1.8, ms=5,
                label="Surface code")
    # Phase annotations now lie ON the repetition curve (22d-11).
    for d_p, lbl in [(2, "Phase 1 (33)"), (3, "d=3 ext. (55)"), (5, "Phase 2 (99)")]:
        ax.annotate(lbl, (d_p, 22 * d_p - 11), textcoords="offset points",
                    xytext=(6, 5), fontsize=8)
    ax.set(xlabel="Code distance d", ylabel="Total photonic modes",
           title="(i) Mode-overhead scaling")
    ax.set_xticks(d_list); ax.legend(fontsize=9); ax.grid(alpha=0.2)

    fig.suptitle("Photonic QEC architecture: complete journal-version results",
                 fontsize=13, fontweight="bold", y=0.995)
    plt.savefig("journal_master.pdf", dpi=300, bbox_inches="tight")
    plt.savefig("journal_master.png", dpi=200, bbox_inches="tight")
    print("[OK] saved journal_master.pdf / .png")

if __name__ == "__main__":
    main()