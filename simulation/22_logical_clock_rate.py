# Logical clock rate from feedforward latency, post-selection and loss.

import numpy as np
import matplotlib.pyplot as plt
import csv

T_CYCLE_REF = 190e-9          # paper feedforward budget -> logical cycle time
F_CYCLE_REF = 1.0 / T_CYCLE_REF
SOURCE_REP_HZ = 5e9           # photon source rep rate (multiplexing, NOT clock)


def logical_clock_rate(f_cycle_Hz: float, p_CZ: float, n_CZ: int,
                       p_loss_per_photon: float, n_photons: int) -> float:
    return (f_cycle_Hz
            * (p_CZ ** n_CZ)
            * ((1 - p_loss_per_photon) ** n_photons))


def scenarios():
    return [
        ("Post-sel CZ d=3 (rep)",        190e-9, 1/9,  2, 0.01,  5),
        ("Paper 75%-discard d=3 (rep)",  190e-9, 0.25, 2, 0.01,  5),
        ("Fusion-based d=3 (rep)",       190e-9, 0.5,  2, 0.01,  5),
        ("Optimistic future (SiN)",      190e-9, 0.5,  2, 0.001, 5),
        ("Surface d=3 (est.)",           250e-9, 0.5,  6, 0.01,  17),
        ("Surface d=5 (est.)",           400e-9, 0.5,  6, 0.005, 49),
    ]


def report_table():
    rows = []
    print(f"\nSource rep rate (multiplexing, not the logical clock): "
          f"{SOURCE_REP_HZ/1e9:.0f} GHz")
    print(f"Feedforward ceiling 1/190ns = {F_CYCLE_REF/1e6:.2f} MHz "
          f"(max sequential logical clock)\n")
    print(f"{'Scenario':<30}{'T_cyc':>8}{'f_cyc':>9}{'p_CZ':>7}{'n_ph':>6}"
          f"{'p_loss':>9}{'f_logical':>13}")
    print("-" * 82)
    for name, Tcyc, pCZ, nCZ, pL, nPh in scenarios():
        f_cyc = 1.0 / Tcyc
        f_log = logical_clock_rate(f_cyc, pCZ, nCZ, pL, nPh)
        rows.append(dict(scenario=name, T_cycle_s=Tcyc, f_cycle_Hz=f_cyc,
                         p_CZ=pCZ, n_CZ=nCZ, p_loss_per_photon=pL,
                         n_photons=nPh, f_logical_Hz=f_log))
        print(f"{name:<30}{Tcyc*1e9:>6.0f}n{f_cyc/1e6:>7.2f}M{pCZ:>7.3f}"
              f"{nPh:>6}{pL:>9.4f}{f_log/1e3:>11.2f}k")
    return rows


def plot_sensitivity(fname="logical_clock_rate.pdf"):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # (a) f_logical vs p_CZ  (base = feedforward ceiling)
    p_CZ_range = np.linspace(0.05, 0.6, 50)
    for n_CZ in [2, 4, 6, 8]:
        f = [logical_clock_rate(F_CYCLE_REF, pCZ, n_CZ, 0.005, 5)
             for pCZ in p_CZ_range]
        ax1.semilogy(p_CZ_range, f, lw=1.8, label=f"{n_CZ} CZs / op")
    ax1.axhline(F_CYCLE_REF, color="gray", ls="--", alpha=0.7,
                label=f"feedforward ceiling ({F_CYCLE_REF/1e6:.1f} MHz)")
    ax1.set_xlabel("Post-selected CZ success probability $p_{CZ}$")
    ax1.set_ylabel("Logical clock rate (Hz)")
    ax1.set_title("(a) f_logical vs CZ success (n_ph=5, p_loss=0.005)")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    # (b) f_logical vs per-photon loss
    p_loss_range = np.logspace(-4, -1, 50)
    for n_photons in [5, 9, 17, 49]:
        f = [logical_clock_rate(F_CYCLE_REF, 0.5, 4, pL, n_photons)
             for pL in p_loss_range]
        ax2.loglog(p_loss_range, f, lw=1.8, label=f"{n_photons} photons")
    ax2.axhline(F_CYCLE_REF, color="gray", ls="--", alpha=0.7,
                label=f"feedforward ceiling")
    ax2.set_xlabel("Per-photon loss probability")
    ax2.set_ylabel("Logical clock rate (Hz)")
    ax2.set_title("(b) f_logical vs per-photon loss (p_CZ=0.5, 4 CZ/op)")
    ax2.legend(fontsize=8); ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")


def export_csv(rows, path="logical_clock_rate.csv"):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[OK] wrote {path}")

if __name__ == "__main__":
    rows = report_table()
    plot_sensitivity()
    export_csv(rows)

    # ---- self-checks ----
    print("\n--- SELF-CHECKS ---")
    # no scenario may exceed its own feedforward ceiling
    okCeil = all(r["f_logical_Hz"] <= r["f_cycle_Hz"] + 1e-6 for r in rows)
    print(f"[{'PASS' if okCeil else 'FAIL'}] every f_logical <= its feedforward "
          f"ceiling 1/T_cycle (no impossible rates)")
    test = [logical_clock_rate(F_CYCLE_REF, pCZ, 2, 0.01, 5)
            for pCZ in (0.1, 0.2, 0.3, 0.5)]
    okMono = all(np.diff(test) > 0)
    print(f"[{'PASS' if okMono else 'FAIL'}] f_logical increases with p_CZ")
    # sane magnitude: rep scenarios land in kHz..low-MHz
    rep = [r["f_logical_Hz"] for r in rows if "(rep)" in r["scenario"]]
    okMag = all(1e3 <= f <= F_CYCLE_REF for f in rep)
    print(f"[{'PASS' if okMag else 'FAIL'}] rep-code logical rates in "
          f"[1 kHz, ceiling] (sane): "
          f"{', '.join(f'{f/1e3:.0f}k' for f in rep)}")
    print("\nNOTE: the source rep rate (5 GHz) does NOT set the logical clock; "
          "it enables multiplexing that can recover the rate toward the "
          "feedforward ceiling at a resource (photon-count) cost. The numbers "
          "above are the single-attempt (un-multiplexed) effective rate.")
