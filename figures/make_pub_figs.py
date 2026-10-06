# Publication figures for the architecture and results.
import numpy as np, matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp

# ---- IEEE publication style ----
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
    "legend.fontsize": 6.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "lines.linewidth": 1.0, "lines.markersize": 3.2, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "legend.frameon": True, "legend.framealpha": 0.9, "legend.edgecolor": "0.7",
    "pdf.fonttype": 42, "ps.fonttype": 42,        # embed TrueType (IEEE PDF eXpress safe)
    "figure.dpi": 150, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})
COL, DBL = 3.5, 7.16     # IEEE single / double column width (inches)

# ---- data (real, script-11) ----
p = np.array([0.0032,0.0040,0.0051,0.0065,0.0083,0.0106,0.0135,0.0173,0.0220,0.0280,
              0.0357,0.0455,0.0580,0.0739,0.0941,0.1199,0.1528,0.1947,0.2482,0.3162])
d3=np.array([0.00014,0.00020,0.00034,0.00056,0.00089,0.00135,0.00232,0.00360,0.00588,0.00924,
             0.01440,0.02273,0.03441,0.05500,0.08130,0.12144,0.17643,0.24666,0.32249,0.39907])
d5=np.array([0.00001,0.00001,0.00001,0.00005,0.00006,0.00010,0.00020,0.00037,0.00074,0.00152,
             0.00324,0.00698,0.01337,0.02574,0.04941,0.08848,0.15062,0.23830,0.33963,0.43143])
d7=np.array([1e-6,1e-6,1e-6,1e-6,1e-6,0.00001,0.00001,0.00009,0.00010,0.00024,
             0.00069,0.00171,0.00455,0.01178,0.02824,0.06427,0.13264,0.24033,0.36389,0.45526])
N=200000; pth_nom,pth_eff=0.2109,0.1406
def slope(pl,cap):
    m=(pl>0)&(pl*N>=20)&(p<=cap); s,_=np.polyfit(np.log(p[m]),np.log(pl[m]),1); return s
cap=pth_nom/3; s3,s5,s7=slope(d3,cap),slope(d5,cap),slope(d7,cap)


def wilson(k,n,z=1.96):
    if n==0: return 0,0
    ph=k/n; d=1+z*z/n; c=(ph+z*z/2/n)/d; h=z*np.sqrt(ph*(1-ph)/n+z*z/4/n/n)/d
    return max(c-h,0),c+h

# ===== Fig 4: threshold + suppression =====
fig,(a1,a2)=plt.subplots(1,2,figsize=(DBL,2.7))
for pl,lab,mk,c in [(d3,"$d=3$","o","#1f4e9c"),(d5,"$d=5$","s","#b45309"),(d7,"$d=7$","^","#15803d")]:
    lo=np.array([wilson(int(round(v*N)),N)[0] for v in pl]); hi=np.array([wilson(int(round(v*N)),N)[1] for v in pl])
    a1.loglog(p,pl,mk+"-",label=lab,color=c,mfc="white",mew=0.8)
    a1.fill_between(p,lo,hi,color=c,alpha=0.15,lw=0)
a1.loglog(p,p,"k--",lw=0.8,alpha=.7,label="no QEC")
a1.axvline(pth_nom,color="0.5",ls=":",lw=0.8)
a1.text(pth_nom*1.05,3e-5,r"$p_{\mathrm{th}}\!\approx\!0.21$",fontsize=6.5,color="0.35")
a1.set_xlabel(r"physical error rate $p$"); a1.set_ylabel(r"logical error rate $p_L$")
a1.set_ylim(1e-5,1); a1.legend(loc="lower right",handlelength=1.5); a1.grid(True,which="both",alpha=.2,lw=0.4)
a1.set_title("(a)",loc="left",fontsize=8)
for pl,lab,s,c,d in [(d3,"d3",s3,"#1f4e9c",3),(d5,"d5",s5,"#b45309",5),(d7,"d7",s7,"#15803d",7)]:
    m=(pl>0)&(pl*N>=20)&(p<=cap); a2.loglog(p[m],pl[m],"o",color=c,mfc="white",mew=0.8)
    xx=np.linspace(p[m].min(),p[m].max(),40); b=np.log(pl[m]).mean()-s*np.log(p[m]).mean()
    a2.loglog(xx,np.exp(b)*xx**s,"-",color=c,label=fr"$d={d}$: {s:.2f} ($\lceil d/2\rceil={-(-d//2)}$)")
a2.set_xlabel(r"physical error rate $p\ (\leq p_{\mathrm{th}}/3)$"); a2.set_ylabel(r"logical error rate $p_L$")
a2.legend(loc="lower right",handlelength=1.5); a2.grid(True,which="both",alpha=.2,lw=0.4)
a2.set_title("(b)",loc="left",fontsize=8)
fig.tight_layout(pad=0.4); fig.savefig("fig_threshold_suppression.pdf")

# ===== Fig 5: feedforward timeline =====
fig,ax=plt.subplots(figsize=(DBL,1.9))
for lab,s,d,c in [("SNSPD detection",0,50,"#1f4e9c"),("decode",50,2.5,"#a16207"),
                  ("Pockels",52.5,10,"#15803d"),("system margin",62.5,127.5,"#d7dee8")]:
    ax.add_patch(mp.Rectangle((s,0.5),d,0.34,color=c,ec="black",lw=0.5))
    if d>15: ax.text(s+d/2,0.67,f"{lab}\n{d:g} ns",ha="center",va="center",color="white" if c!="#d7dee8" else "0.2",fontsize=6.5)
    else:
        ax.annotate(f"{lab} ({d:g} ns)",xy=(s+d/2,0.84),xytext=(s+d/2,1.06),ha="center",fontsize=6.3,
                    arrowprops=dict(arrowstyle="-",lw=0.5))
ax.add_patch(mp.Rectangle((0,0.14),100,0.28,fc="none",ec="#7c3aed",lw=0.8,ls="--"))
ax.text(50,0.28,"optical buffer (~100 ns) — decode hidden here",ha="center",va="center",fontsize=6.3,color="#7c3aed")
ax.axvline(190,color="#c0392b",ls=":",lw=1.0); ax.text(188,1.12,"190 ns budget",ha="right",color="#c0392b",fontsize=7)
ax.set_xlim(-3,200); ax.set_ylim(0,1.25); ax.set_yticks([]); ax.set_xlabel("time (ns)")
for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
fig.tight_layout(pad=0.3); fig.savefig("fig_feedforward_timeline.pdf")

# ===== Fig 6: decoder improvement =====
fig,(a1,a2)=plt.subplots(1,2,figsize=(COL,2.3))
a1.bar(["HLS\nest.","RTL\nmeas."],[25,2.5],color=["#9aa7b5","#a16207"],ec="black",lw=0.5,width=0.6)
a1.set_ylabel("decode latency (ns)")
for i,v in enumerate([25,2.5]): a1.text(i,v+0.7,f"{v:g}",ha="center",fontsize=7)
a1.set_title("(a)",loc="left",fontsize=8)
a2.bar(["HLS\nest.","RTL\ncore"],[276,8],color=["#9aa7b5","#a16207"],ec="black",lw=0.5,width=0.6)
a2.set_ylabel("LUTs")
for i,v in enumerate([276,8]): a2.text(i,v+6,f"{v}",ha="center",fontsize=7)
a2.text(1,55,"report\nmeasured",ha="center",fontsize=5.5,color="0.4")
a2.set_title("(b)",loc="left",fontsize=8)
fig.tight_layout(pad=0.4); fig.savefig("fig_decoder_improvement.pdf")

print(f"slopes {s3:.2f}/{s5:.2f}/{s7:.2f}; saved 3 IEEE-styled PDFs")
