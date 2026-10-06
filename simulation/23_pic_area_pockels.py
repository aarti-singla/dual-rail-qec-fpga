# Chip area estimate and electro-optic / thermo-optic driver power.

import numpy as np
import csv


def mzi_footprint_um(platform: str = "Si_AMF") -> dict:
    """MZI footprint / phase-shifter parameters per PDK (published 2022-2024)."""
    catalog = {
        "Si_AMF":       dict(L_um=400,  W_um=80,  loss_dB=0.3,  V_pi=4.0,
                             phase_shifter="thermo-optic", R_heater_ohm=1000),
        "Si_IMEC":      dict(L_um=300,  W_um=60,  loss_dB=0.25, V_pi=3.5,
                             phase_shifter="thermo-optic", R_heater_ohm=1200),
        "SiN_Ligentec": dict(L_um=600,  W_um=100, loss_dB=0.15, V_pi=10.0,
                             phase_shifter="thermo-optic", R_heater_ohm=2000),
        "LNOI_NanoLN":  dict(L_um=2000, W_um=80,  loss_dB=0.2,  V_pi=1.5,
                             phase_shifter="electro-optic", R_heater_ohm=None),
        "TFLN":         dict(L_um=5000, W_um=100, loss_dB=0.1,  V_pi=2.0,
                             phase_shifter="electro-optic Pockels",
                             R_heater_ohm=None),
    }
    return catalog.get(platform, catalog["Si_AMF"])


def estimate_pic_area(n_modes: int = 33, n_mzi_layers: int = 11,
                      platform: str = "Si_AMF") -> dict:
    mzi = mzi_footprint_um(platform)
    n_total_MZI = n_modes * n_mzi_layers // 2     # paired-mode MZI count
    L_total_um = n_mzi_layers * (mzi["L_um"] + 50)
    W_total_um = n_modes * (mzi["W_um"] + 50)
    L_with_border_um = L_total_um + 2 * 200
    W_with_border_um = W_total_um + 2 * 200
    area_mm2 = (L_with_border_um / 1000) * (W_with_border_um / 1000)
    return dict(
        platform=platform, n_modes=n_modes, n_layers=n_mzi_layers,
        n_MZI=n_total_MZI,
        chip_length_mm=round(L_with_border_um / 1000, 2),
        chip_width_mm=round(W_with_border_um / 1000, 2),
        area_mm2=round(area_mm2, 2),
        total_insertion_dB=round(mzi["loss_dB"] * n_mzi_layers, 2),
        V_pi=mzi["V_pi"], phase_shifter=mzi["phase_shifter"],
    )


def pockels_driver_specs(load_pF: float, V_pi: float, risetime_ns: float,
                         f_repetition_MHz: float) -> dict:
    """Electro-optic (Pockels/EOM) capacitive driver requirements."""
    E_per_switch_pJ = 0.5 * load_pF * V_pi ** 2
    avg_power_uW = E_per_switch_pJ * f_repetition_MHz        # pJ*MHz = uW
    slew_V_per_ns = V_pi / risetime_ns
    peak_current_mA = load_pF * slew_V_per_ns                # pF*(V/ns) = mA
    return dict(
        drive="electro-optic (capacitive)",
        load_pF=load_pF, V_pi=V_pi, risetime_ns=risetime_ns,
        f_repetition_MHz=f_repetition_MHz,
        energy_per_switch_pJ=round(E_per_switch_pJ, 3),
        avg_power_uW=round(avg_power_uW, 3),
        slew_V_per_ns=round(slew_V_per_ns, 2),
        peak_current_mA=round(peak_current_mA, 2),
    )


def thermo_optic_specs(V_pi: float, R_heater_ohm: float,
                       duty_cycle: float = 1.0) -> dict:
    P_pi_mW = (V_pi ** 2 / R_heater_ohm) * 1e3 * duty_cycle   # W->mW
    return dict(
        drive="thermo-optic (resistive DC)",
        V_pi=V_pi, R_heater_ohm=R_heater_ohm, duty_cycle=duty_cycle,
        P_pi_mW=round(P_pi_mW, 3),
        note="continuous DC; ~us-ms response; no capacitive switching energy",
    )


def electro_optic_scenarios():
    # (name, C_pF, V_pi, t_rise_ns, f_rep_MHz)
    return [
        ("EO fast (1 ns rise)",            5.0, 4.0, 1.0,  1.0),
        ("EO paper Pockels (10 ns)",       5.0, 4.0, 10.0, 1.0),   # paper budget
        ("EO moderate (5 ns rise)",        5.0, 4.0, 5.0,  1.0),
        ("LNOI fast Pockels (100 ps)",     2.0, 1.5, 0.1,  10.0),
    ]


def main():
    print("\n=== PIC area estimates (conservative upper bound) ===\n")
    pic_rows = []
    for platform in ("Si_AMF", "Si_IMEC", "SiN_Ligentec",
                     "LNOI_NanoLN", "TFLN"):
        info = estimate_pic_area(n_modes=33, platform=platform)
        pic_rows.append(info)
        print(f"{platform}:")
        for k, v in info.items():
            print(f"  {k:>20} = {v}")
        print()
    with open("pic_area_estimate.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=pic_rows[0].keys())
        w.writeheader()
        for r in pic_rows:
            w.writerow(r)
    print("[OK] wrote pic_area_estimate.csv")

    # ---- electro-optic (Pockels) capacitive drivers ----
    print("\n=== Electro-optic (Pockels) driver specs ===\n")
    print(f"{'scenario':<32}{'E/sw':>11}{'P_avg':>11}{'slew':>12}{'I_peak':>10}")
    print("-" * 80)
    driver_rows = []
    for name, C, V, t_r, f_rep in electro_optic_scenarios():
        d = pockels_driver_specs(C, V, t_r, f_rep)
        d["scenario"] = name
        driver_rows.append(d)
        print(f"{name:<32}{d['energy_per_switch_pJ']:>8.2f} pJ"
              f"{d['avg_power_uW']:>8.2f} uW{d['slew_V_per_ns']:>9.2f} V/ns"
              f"{d['peak_current_mA']:>7.2f} mA")

    # ---- thermo-optic (resistive DC) shifters ----
    print("\n=== Thermo-optic (resistive DC) phase-shifter power ===\n")
    print(f"{'platform':<16}{'V_pi':>7}{'R(ohm)':>9}{'P_pi':>12}")
    print("-" * 46)
    for platform in ("Si_AMF", "Si_IMEC", "SiN_Ligentec"):
        m = mzi_footprint_um(platform)
        t = thermo_optic_specs(m["V_pi"], m["R_heater_ohm"])
        t["scenario"] = platform
        driver_rows.append(t)
        print(f"{platform:<16}{m['V_pi']:>7.1f}{m['R_heater_ohm']:>9}"
              f"{t['P_pi_mW']:>9.2f} mW")

    # union of keys across the two driver models
    fields = []
    for r in driver_rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open("driver_specs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in driver_rows:
            w.writerow(r)
    print("\n[OK] wrote driver_specs.csv")

    # ---- self-checks ----
    print("\n--- SELF-CHECKS ---")
    d = pockels_driver_specs(5.0, 4.0, 1.0, 1.0)
    okP = abs(d["avg_power_uW"] - 40.0) < 1e-6
    print(f"[{'PASS' if okP else 'FAIL'}] avg power: 40 pJ @ 1 MHz = "
          f"{d['avg_power_uW']:.1f} uW (expect 40, not 0.04)")
    okI = abs(d["peak_current_mA"] - 20.0) < 1e-6
    print(f"[{'PASS' if okI else 'FAIL'}] peak current: 5 pF * 4 V/ns = "
          f"{d['peak_current_mA']:.1f} mA (I = C dV/dt)")
    t = thermo_optic_specs(4.0, 1000)
    okT = 5.0 <= t["P_pi_mW"] <= 50.0
    print(f"[{'PASS' if okT else 'FAIL'}] thermo-optic DC power: V^2/R = "
          f"{t['P_pi_mW']:.1f} mW (10-40 mW range, NOT sub-uW)")
    print("\nNOTE: capacitive (pJ/switch) and resistive (mW continuous) drive "
          "models are physically distinct; thermo-optic platforms do not use "
          "the Pockels switching-energy formula.")

if __name__ == "__main__":
    main()
