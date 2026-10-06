# Mode-layout tables for the surface-code d=3 / d=5 variants.

import csv
from collections import OrderedDict

# Heuristic per-unit mode budget (NOT the paper's 33-mode accounting)
MODES_PER_QUBIT = {
    "data_rail_0": 1, "data_rail_1": 1, "routing": 1,
    "buffer_delay": 1, "cz_ancilla_0": 1, "cz_ancilla_1": 1,
}  # 6 modes / qubit

MODES_PER_STAB = {
    "extraction_anc": 4,   # modes that read out the stabiliser
    "gauge_shared": 2,     # local gauge / reset
}  # 6 modes / stabiliser

LAYERS = {
    "data":  "L01,L02,L06,L08,L11",
    "X_anc": "L03,L09,L10",
    "Z_anc": "L04,L09,L10",
    "X_stab": "L03,L10",
    "Z_stab": "L04,L10",
}


def build_mode_table(d: int):
    """Granular per-mode-block rows for rotated surface code distance d."""
    n_data = d ** 2
    n_X_stab = (d ** 2 - 1) // 2
    n_Z_stab = (d ** 2 - 1) // 2
    n_qubits = n_data + n_X_stab + n_Z_stab

    rows = []
    mode_idx = 1

    def emit(count, qubit, role, layers, cls):
        nonlocal mode_idx
        start, end = mode_idx, mode_idx + count - 1
        label = f"M{start:03d}" if start == end else f"M{start:03d}-M{end:03d}"
        rows.append(dict(mode_range=label, count=count, qubit=qubit,
                         role=role, active_layers=layers, qclass=cls))
        mode_idx += count

    for q in range(n_data):
        for role, n in MODES_PER_QUBIT.items():
            emit(n, f"data_q{q}", role, LAYERS["data"], "data")

    for s in range(n_X_stab):
        for role, n in MODES_PER_QUBIT.items():
            emit(n, f"X_anc{s}", role, LAYERS["X_anc"], "X_anc")
        for role, n in MODES_PER_STAB.items():
            emit(n, f"X_anc{s}", f"stab_support:{role}", LAYERS["X_stab"], "X_anc")

    for s in range(n_Z_stab):
        for role, n in MODES_PER_QUBIT.items():
            emit(n, f"Z_anc{s}", role, LAYERS["Z_anc"], "Z_anc")
        for role, n in MODES_PER_STAB.items():
            emit(n, f"Z_anc{s}", f"stab_support:{role}", LAYERS["Z_stab"], "Z_anc")

    total_modes = mode_idx - 1
    info = dict(d=d, n_data=n_data, n_X_stab=n_X_stab, n_Z_stab=n_Z_stab,
                n_qubits=n_qubits)
    return rows, total_modes, info


def group_rows(rows):
    groups = OrderedDict()
    for r in rows:
        key = (r["qclass"], r["role"])
        g = groups.setdefault(key, dict(qclass=r["qclass"], role=r["role"],
                                        per_unit=r["count"], units=0,
                                        total=0, layers=r["active_layers"]))
        g["units"] += 1
        g["total"] += r["count"]
    return list(groups.values())


def write_csv(rows, path):
    fields = ["mode_range", "count", "qubit", "role", "active_layers"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[OK] wrote {path}  ({len(rows)} granular rows)")


def write_tex(rows, total, info, path):
    """Compact GROUPED LaTeX table (~22 rows), safe inside a table* float."""
    groups = group_rows(rows)
    with open(path, "w") as f:
        f.write(f"% Grouped mode-level layout for surface code d={info['d']}\n")
        f.write("\\begin{table*}[t]\n\\centering\n")
        f.write("\\caption{Mode-level layout for the photonic surface code "
                f"$d={info['d']}$ architecture "
                f"({info['n_data']} data, {info['n_X_stab']} X-stab, "
                f"{info['n_Z_stab']} Z-stab; {total} total photonic modes, "
                "heuristic budget).}\n")
        f.write("\\begin{tabular}{llrrrl}\n\\hline\n")
        f.write("Class & Role & Modes/unit & Units & Total & Active Layers \\\\\n")
        f.write("\\hline\n")
        cur = None
        for g in groups:
            cls = g["qclass"].replace("_", r"\_")
            role = g["role"].replace("_", r"\_")
            cls_disp = cls if g["qclass"] != cur else ""
            cur = g["qclass"]
            f.write(f"{cls_disp} & {role} & {g['per_unit']} & {g['units']} & "
                    f"{g['total']} & {g['layers']} \\\\\n")
        f.write("\\hline\n")
        f.write(f"\\multicolumn{{4}}{{l}}{{\\textbf{{Total}}}} & "
                f"\\textbf{{{total}}} & \\\\\n")
        f.write("\\hline\n\\end{tabular}\n\\end{table*}\n")
    print(f"[OK] wrote {path}  ({len(groups)} grouped rows)")


def print_summary(rows, total, info):
    print(f"\nSurface code d={info['d']} mode budget (heuristic)")
    print("=" * 70)
    print(f"  Data qubits:       {info['n_data']}")
    print(f"  X-stabilisers:     {info['n_X_stab']}")
    print(f"  Z-stabilisers:     {info['n_Z_stab']}")
    print(f"  Total qubits:      {info['n_qubits']}")
    print(f"  Total modes:       {total}")
    print(f"  Modes per qubit:   {total / info['n_qubits']:.1f}")
    print(f"  Granular rows:     {len(rows)}")
    print(f"  Grouped rows:      {len(group_rows(rows))}")
    # consistency check: grouped totals must equal granular total
    gtot = sum(g["total"] for g in group_rows(rows))
    ok = gtot == total
    print(f"  [{'PASS' if ok else 'FAIL'}] grouped total ({gtot}) == granular total ({total})")

if __name__ == "__main__":
    for d in (3, 5):
        rows, total, info = build_mode_table(d)
        print_summary(rows, total, info)
        write_csv(rows, f"surface_d{d}_mode_table.csv")
        write_tex(rows, total, info, f"surface_d{d}_mode_table.tex")