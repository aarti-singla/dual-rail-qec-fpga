# Gate-fidelity band figure.
import numpy as np, matplotlib as mpl
mpl.use("Agg"); import matplotlib.pyplot as plt
mpl.rcParams.update({"font.family":"serif","font.serif":["Nimbus Roman","DejaVu Serif"],
 "mathtext.fontset":"stix","font.size":8,"axes.labelsize":8,"legend.fontsize":6.8,
 "xtick.labelsize":7,"ytick.labelsize":7,"axes.linewidth":0.6,
 "pdf.fonttype":42,"savefig.bbox":"tight","savefig.pad_inches":0.02})
eps=np.linspace(0,0.05,400)
c_lo,c_hi=7.0,14.0
F_lo=1-c_lo*eps**2      # optimistic model (upper fidelity curve)
F_hi=1-c_hi*eps**2      # conservative model (lower fidelity curve)
e99=np.sqrt(0.01/c_hi)  # conservative F=0.99 crossing = 0.0267
fig,ax=plt.subplots(figsize=(3.4,2.5))
ax.fill_between(eps,F_hi,F_lo,color="#1f4e9c",alpha=0.18,lw=0,
                label=r"model range $c=7$–$14$")
ax.plot(eps,F_lo,lw=1.0,color="#1f4e9c")
ax.plot(eps,F_hi,lw=1.0,color="#1f4e9c",ls="--")
ax.axhline(0.99,ls="--",lw=0.8,color="0.45",label="target $F=0.99$")
ax.axvline(0.01,ls=":",lw=0.9,color="#c0392b",label=r"design point $\epsilon=0.01$")
ax.axvline(e99,ls="-.",lw=0.9,color="#b45309",
           label=fr"$F\!=\!0.99$ at $\epsilon={e99:.3f}$")
ax.set_xlabel(r"beamsplitter imbalance $\epsilon$")
ax.set_ylabel("CZ gate fidelity $F$")
ax.set_xlim(0,0.05); ax.set_ylim(0.984,1.001)
ax.grid(alpha=0.22,lw=0.4); ax.legend(loc="lower left",handlelength=1.5)
fig.tight_layout(pad=0.3); fig.savefig("fig4_fidelity_band.pdf")
print(f"F at eps=0.01: {1-c_hi*1e-4:.5f} (conservative) .. {1-c_lo*1e-4:.5f} (optimistic)")
print(f"conservative F=0.99 crossing: eps = {e99:.4f}")
