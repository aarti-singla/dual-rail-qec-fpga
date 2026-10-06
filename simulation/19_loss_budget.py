# Per-photon loss budget for the 33-mode circuit.

import numpy as np
import matplotlib.pyplot as plt
import csv

# Standardized references (see scripts 17, and paper Limitations sec. VII)
P_TH_EFF = 0.14          # 2-term repetition Pauli threshold, EFFECTIVE X-flip
LOSS_TO_PAULI = 0.5      # paper: p_Pauli = p_loss / 2 (erasure conversion)
N_LAYERS = 11            # pipeline layers (paper's 11-layer framing)


def db_to_linear(db: float) -> float:
    """Loss in dB -> linear transmission probability."""
    return 10 ** (-db / 10)


def linear_to_db(linear: float) -> float:
    return -10 * np.log10(max(linear, 1e-12))


class PhotonicComponent:
    def __init__(self, name: str, loss_db: float, count: int = 1,
                 kind: str = "path"):
        assert kind in ("terminal", "path")
        self.name = name
        self.loss_db = loss_db
        self.count = count
        self.kind = kind                       # "terminal" (rate) or "path" (QEC)
        self.total_db = loss_db * count
        self.transmission = db_to_linear(self.total_db)


def architecture_loss_budget(scenario: str = "Si_baseline"):
    if scenario == "Si_baseline":
        cs = [
            PhotonicComponent("SPDC heralded source",       3.0, 1, "terminal"),
            PhotonicComponent("Source-to-chip coupling",    1.0, 1, "terminal"),
            PhotonicComponent("Si waveguide (2 cm path)",   1.0, 2, "path"),   # 1 dB/cm
            PhotonicComponent("MZI insertion (11 layers)",  0.3, 11, "path"),
            PhotonicComponent("Fibre loop coupling",        1.0, 2, "path"),
            PhotonicComponent("Fibre propagation (20.5m)",  0.0042, 20.5, "path"),
            PhotonicComponent("Chip-to-detector coupling",  1.0, 1, "terminal"),
            PhotonicComponent("SNSPD detection (~85%)",     0.7, 1, "terminal"),
        ]
    elif scenario == "SiN_baseline":
        cs = [
            PhotonicComponent("Quantum-dot source",         1.5, 1, "terminal"),
            PhotonicComponent("Source-to-chip coupling",    0.8, 1, "terminal"),
            PhotonicComponent("SiN waveguide (2 cm path)",  0.1, 2, "path"),
            PhotonicComponent("MZI insertion (11 layers)",  0.2, 11, "path"),
            PhotonicComponent("Fibre loop coupling",        0.8, 2, "path"),
            PhotonicComponent("Fibre propagation (20.5m)",  0.0042, 20.5, "path"),
            PhotonicComponent("Chip-to-detector coupling",  0.8, 1, "terminal"),
            PhotonicComponent("SNSPD detection (~90%)",     0.5, 1, "terminal"),
        ]
    elif scenario == "future_optimistic":
        cs = [
            PhotonicComponent("Deterministic source",       0.5, 1, "terminal"),
            PhotonicComponent("Source-to-chip coupling",    0.3, 1, "terminal"),
            PhotonicComponent("SiN-LN waveguide (2 cm)",    0.05, 2, "path"),
            PhotonicComponent("MZI insertion (11 layers)",  0.1, 11, "path"),
            PhotonicComponent("Fibre loop coupling",        0.3, 2, "path"),
            PhotonicComponent("Fibre propagation (20.5m)",  0.0042, 20.5, "path"),
            PhotonicComponent("Chip-to-detector coupling",  0.3, 1, "terminal"),
            PhotonicComponent("SNSPD detection (~95%)",     0.22, 1, "terminal"),
        ]
    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    total_db = sum(c.total_db for c in cs)
    term_db = sum(c.total_db for c in cs if c.kind == "terminal")
    path_db = sum(c.total_db for c in cs if c.kind == "path")
    return cs, total_db, term_db, path_db


def per_layer_path_p_loss(path_db: float, n_layers: int = N_LAYERS) -> float:
    T_path = db_to_linear(path_db)
    return 1.0 - T_path ** (1.0 / n_layers)


def report_scenario(scenario: str):
    cs, total_db, term_db, path_db = architecture_loss_budget(scenario)
    T_total = db_to_linear(total_db)
    T_term = db_to_linear(term_db)
    p_loss_layer = per_layer_path_p_loss(path_db)
    p_pauli_layer = LOSS_TO_PAULI * p_loss_layer
    headroom = P_TH_EFF / p_pauli_layer if p_pauli_layer > 0 else float("inf")
    multiplex = 1.0 / T_term

    print(f"\n=== Scenario: {scenario} ===")
    print(f"{'Component':<35}{'kind':>10}{'loss(dB)':>10}{'cumul(dB)':>11}")
    print("-" * 70)
    cumul = 0.0
    for c in cs:
        cumul += c.total_db
        print(f"{c.name:<35}{c.kind:>10}{c.total_db:>10.2f}{cumul:>11.2f}")
    print("-" * 70)
    print(f"{'TOTAL':<35}{'':>10}{total_db:>10.2f} dB  "
          f"(survival {T_total:.3%})")
    print(f"  terminal (heralding/rate): {term_db:6.2f} dB  -> survival "
          f"{T_term:.3%}  -> multiplexing ~{multiplex:.0f}x")
    print(f"  on-chip path (QEC loss)  : {path_db:6.2f} dB")
    print(f"  per-layer path p_loss (n={N_LAYERS})           : "
          f"{p_loss_layer:.4f}  (erasure)")
    print(f"  -> p_Pauli = p_loss/2 (paper conversion)       : "
          f"{p_pauli_layer:.4f}")
    print(f"  headroom vs p_th(eff)={P_TH_EFF} (script 17)    : "
          f"{headroom:.2f}x  [{'PASS' if headroom >= 1 else 'OVER BUDGET'}]")
    print("  note: HERALDED loss is erasure (d=3 rep suppresses for any "
          "erasure<1); the binding terminal constraint is RATE, not threshold.")
    return dict(scenario=scenario, total_db=total_db, term_db=term_db,
                path_db=path_db, T_total=T_total, p_loss_layer=p_loss_layer,
                p_pauli_layer=p_pauli_layer, headroom=headroom,
                multiplex=multiplex)


def plot_waterfall(scenarios=("Si_baseline", "SiN_baseline", "future_optimistic"),
                   fname="loss_budget.pdf"):
    fig, axes = plt.subplots(1, len(scenarios), figsize=(15, 5))
    if len(scenarios) == 1:
        axes = [axes]
    color = {"terminal": "#888780", "path": "#1D9E75"}
    for ax, scenario in zip(axes, scenarios):
        cs, total_db, term_db, path_db = architecture_loss_budget(scenario)
        names = [c.name for c in cs]
        vals = [c.total_db for c in cs]
        cols = [color[c.kind] for c in cs]
        ax.barh(range(len(names)), vals, color=cols, alpha=0.8)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=7)
        ax.set_xlabel("Loss (dB)")
        T_total = db_to_linear(total_db)
        ax.set_title(f"{scenario}\nTotal {total_db:.1f} dB "
                     f"({T_total:.1%} survive)\n"
                     f"terminal {term_db:.1f} / path {path_db:.1f} dB",
                     fontsize=9)
        ax.invert_yaxis()
        ax.grid(alpha=0.3, axis="x")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=color["terminal"], label="terminal (rate)"),
                        Patch(color=color["path"], label="path (QEC loss)")],
               loc="lower center", ncol=2, fontsize=9)
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    plt.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"[OK] saved {fname}")


def csv_export(path="loss_budget.csv"):
    rows = []
    for scenario in ("Si_baseline", "SiN_baseline", "future_optimistic"):
        cs, total_db, term_db, path_db = architecture_loss_budget(scenario)
        for c in cs:
            rows.append(dict(scenario=scenario, component=c.name, kind=c.kind,
                             count=c.count, loss_db_each=c.loss_db,
                             total_loss_db=c.total_db,
                             scenario_total_db=total_db,
                             scenario_terminal_db=term_db,
                             scenario_path_db=path_db))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[OK] wrote {path}")

if __name__ == "__main__":
    results = [report_scenario(sc) for sc in
               ("Si_baseline", "SiN_baseline", "future_optimistic")]
    plot_waterfall()
    csv_export()

    # ---- self-checks ----
    print("\n--- SELF-CHECKS ---")
    # dB round-trip
    okRT = abs(linear_to_db(db_to_linear(7.3)) - 7.3) < 1e-9
    print(f"[{'PASS' if okRT else 'FAIL'}] dB<->linear round-trip")
    # total = terminal + path for every scenario
    okSplit = all(abs(r["total_db"] - (r["term_db"] + r["path_db"])) < 1e-9
                  for r in results)
    print(f"[{'PASS' if okSplit else 'FAIL'}] total dB == terminal + path "
          f"(all scenarios)")
    # scenarios improve monotonically (Si -> SiN -> future)
    hs = [r["headroom"] for r in results]
    okMono = hs[0] < hs[1] < hs[2]
    print(f"[{'PASS' if okMono else 'FAIL'}] headroom improves "
          f"Si->SiN->future: {hs[0]:.2f} < {hs[1]:.2f} < {hs[2]:.2f}")
    # future scenario should clear the QEC threshold
    okFuture = results[-1]["headroom"] >= 1.0
    print(f"[{'PASS' if okFuture else 'FAIL'}] future_optimistic clears "
          f"p_th(eff) (headroom {results[-1]['headroom']:.2f}x)")
    print("\nNOTE: terminal loss (source/detector/couplings) dominates and is a "
          "RATE problem (multiplexing), distinct from the per-layer QEC erasure "
          "judged against p_th(eff)=0.14. Do not conflate the two.")
