# Hardware-scaling figures (decoder timing and LUT count vs distance).
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
import numpy as np

# ---------- Figure: feedforward timing budget ----------
fig,ax=plt.subplots(figsize=(10,3.2))
budget=190
# (label, start, dur, color)
stages=[("SNSPD detection (PNR)",0,50,"#1d4ed8"),
        ("MWPM decode (measured)",50,2.5,"#a16207"),
        ("Pockels switch",52.5,10,"#15803d"),
        ("system margin",62.5,127.5,"#cbd5e1")]
for lab,s,d,c in stages:
    ax.add_patch(mp.Rectangle((s,0.55),d,0.32,color=c,ec="black",lw=0.8))
    if d>8:
        ax.text(s+d/2,0.71,f"{lab}\n{d:g} ns",ha="center",va="center",fontsize=8.5,
                color="white" if c!="#cbd5e1" else "#222")
    else:
        ax.text(s+d/2,1.0,f"{lab}\n{d:g} ns",ha="center",va="bottom",fontsize=8,
                rotation=0)
        ax.plot([s+d/2,s+d/2],[0.87,0.98],"k-",lw=0.6)
# optical buffer in parallel
ax.add_patch(mp.Rectangle((0,0.12),100,0.28,fc="none",ec="#7c3aed",lw=1.4,ls="--"))
ax.text(50,0.26,"optical buffer (data path) ~100 ns — decode hides here",ha="center",va="center",
        fontsize=8.5,color="#7c3aed")
ax.axvline(budget,color="red",ls=":",lw=1.3)
ax.text(budget-2,1.18,"190 ns budget",ha="right",color="red",fontsize=9)
ax.set_xlim(-3,200); ax.set_ylim(0,1.35); ax.set_yticks([])
ax.set_xlabel("time (ns)"); ax.set_title("New Fig.  Feedforward latency budget — decoder is 2.5 ns of 190 ns",fontsize=10)
for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
plt.tight_layout(); plt.savefig("fig_feedforward_timeline.pdf"); plt.savefig("fig_feedforward_timeline.png",dpi=150)

# ---------- Figure: HLS estimate vs measured RTL ----------
fig,(a1,a2)=plt.subplots(1,2,figsize=(8,3.4))
a1.bar(["HLS\nestimate","RTL\nmeasured"],[25,2.5],color=["#94a3b8","#a16207"],ec="black")
a1.set_ylabel("decoder latency (ns)"); a1.set_title("(a) Latency  (10x faster)",fontsize=10)
for i,v in enumerate([25,2.5]): a1.text(i,v+0.6,f"{v} ns",ha="center",fontsize=9)
a2.bar(["HLS\nestimate","RTL core\n(synth.)"],[276,8],color=["#94a3b8","#a16207"],ec="black")
a2.set_ylabel("LUTs"); a2.set_title("(b) Resources  (report measured)",fontsize=10)
for i,v in enumerate([276,8]): a2.text(i,v+5,f"{v}"+("" if i else ""),ha="center",fontsize=9)
a2.text(1,40,"single-digit\ncore (confirm\nin Vivado)",ha="center",fontsize=7.5,color="#555")
plt.tight_layout(); plt.savefig("fig_decoder_improvement.pdf"); plt.savefig("fig_decoder_improvement.png",dpi=150)
print("saved fig_feedforward_timeline.{pdf,png} and fig_decoder_improvement.{pdf,png}")
