# Gate-fidelity figure (corrected version).
import numpy as np, matplotlib as mpl
mpl.use("Agg"); import matplotlib.pyplot as plt
mpl.rcParams.update({"font.family":"serif","font.serif":["Nimbus Roman","DejaVu Serif"],
 "mathtext.fontset":"stix","font.size":8,"axes.labelsize":8,"legend.fontsize":7,
 "xtick.labelsize":7,"ytick.labelsize":7,"axes.linewidth":0.6,
 "pdf.fonttype":42,"savefig.bbox":"tight","savefig.pad_inches":0.02})

# >>> SET THIS from script 05's fit. 7.61 = conservative end of the 6.09-7.61 range,
#     and is the value consistent with Table III's upper bound eps=0.036.
C = 7.61

eps = np.linspace(0, 0.10, 400)
F   = 1 - C*eps**2
eps99 = np.sqrt(0.01/C)

fig, ax = plt.subplots(figsize=(3.5, 2.6))
ax.plot(eps, F, lw=1.2, color="#1f4e9c", label=fr"$F = 1 - {C:.2f}\,\epsilon^2$")
ax.axhline(0.99, ls="--", lw=0.8, color="0.45", label="target $F = 0.99$")
ax.axvline(0.01, ls=":", lw=0.9, color="#c0392b", label=r"spec $\epsilon = 0.01$")
ax.axvline(eps99, ls="-.", lw=0.9, color="#b45309",
           label=fr"$F\!=\!0.99$ at $\epsilon={eps99:.3f}$")
ax.fill_betweenx([0.985,1.001], 0.001, eps99, color="#dcfce7", alpha=0.5, zorder=0)
ax.set_xlabel(r"beamsplitter imbalance $\epsilon$")
ax.set_ylabel("CZ gate fidelity $F$")
ax.set_xlim(0, 0.10); ax.set_ylim(0.985, 1.001)
ax.grid(alpha=0.25, lw=0.4); ax.legend(loc="lower left", handlelength=1.6)
fig.tight_layout(pad=0.3)
fig.savefig("fig4_gate_fidelity_corrected.pdf"); fig.savefig("fig4_gate_fidelity_corrected.png", dpi=160)
print(f"C = {C}")
print(f"F at eps=0.01     : {1-C*1e-4:.6f}")
print(f"F=0.99 crossing   : eps = {eps99:.4f}")
print(f"shaded region     : eps in [0.001, {eps99:.3f}]  <- Table III tolerance range")
