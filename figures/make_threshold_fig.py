# Threshold and suppression figure.
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from numpy.polynomial import polynomial as P

p = np.array([0.0032,0.0040,0.0051,0.0065,0.0083,0.0106,0.0135,0.0173,0.0220,0.0280,
              0.0357,0.0455,0.0580,0.0739,0.0941,0.1199,0.1528,0.1947,0.2482,0.3162])
d3=np.array([0.00014,0.00020,0.00034,0.00056,0.00089,0.00135,0.00232,0.00360,0.00588,0.00924,
             0.01440,0.02273,0.03441,0.05500,0.08130,0.12144,0.17643,0.24666,0.32249,0.39907])
d5=np.array([0.00001,0.00001,0.00001,0.00005,0.00006,0.00010,0.00020,0.00037,0.00074,0.00152,
             0.00324,0.00698,0.01337,0.02574,0.04941,0.08848,0.15062,0.23830,0.33963,0.43143])
d7=np.array([1e-6,1e-6,1e-6,1e-6,1e-6,0.00001,0.00001,0.00009,0.00010,0.00024,
             0.00069,0.00171,0.00455,0.01178,0.02824,0.06427,0.13264,0.24033,0.36389,0.45526])
N=200000
pth_nom=0.2109; pth_eff=0.1406


def slope(p,pl,cap):
    m=(pl>0)&(pl*N>=20)&(p<=cap)
    s,_=np.polyfit(np.log(p[m]),np.log(pl[m]),1); return s
s3=slope(p,d3,pth_nom/3); s5=slope(p,d5,pth_nom/3); s7=slope(p,d7,pth_nom/3)

fig,(ax1,ax2)=plt.subplots(1,2,figsize=(11,4.4))

# Panel A: threshold crossing
for pl,lab,mk,c in [(d3,"d = 3","o","#1d4ed8"),(d5,"d = 5","s","#b45309"),(d7,"d = 7","^","#15803d")]:
    ax1.loglog(p,pl,mk+"-",ms=4.5,lw=1.4,label=lab,color=c)
ax1.loglog(p,p,"k--",lw=1,alpha=.6,label="no QEC (pL = p)")
ax1.axvline(pth_nom,color="gray",ls=":",lw=1.2)
ax1.annotate(f"threshold\n$p_{{th}}$ = {pth_nom:.3f} nom\n= {pth_eff:.3f} eff",
             xy=(pth_nom,0.25),xytext=(0.045,0.33),fontsize=8.5,
             arrowprops=dict(arrowstyle="->",color="gray"))
ax1.set_xlabel("physical error rate $p$ (nominal)"); ax1.set_ylabel("logical error rate $p_L$")
ax1.set_title("(a) Sub-threshold crossing, d = 3/5/7  (2-term, 200k shots)",fontsize=10)
ax1.legend(fontsize=8.5,loc="lower right"); ax1.grid(True,which="both",alpha=.25)
ax1.set_ylim(1e-5,1)

# Panel B: suppression slopes in asymptotic window
cap=pth_nom/3
for pl,lab,s,c in [(d3,"d=3",s3,"#1d4ed8"),(d5,"d=5",s5,"#b45309"),(d7,"d=7",s7,"#15803d")]:
    m=(pl>0)&(pl*N>=20)&(p<=cap)
    ax2.loglog(p[m],pl[m],"o",ms=5,color=c)
    xx=np.linspace(p[m].min(),p[m].max(),50)
    b=np.log(pl[m]).mean()-s*np.log(p[m]).mean()
    ax2.loglog(xx,np.exp(b)*xx**s,"-",lw=1.6,color=c,
               label=f"{lab}: slope {s:.2f}  (target {int(np.ceil(int(lab[2])/2))})")
ax2.set_xlabel("physical error rate $p$  ($p \\leq p_{th}/3$)"); ax2.set_ylabel("logical error rate $p_L$")
ax2.set_title("(b) Suppression slopes $\\rightarrow \\lceil d/2 \\rceil$",fontsize=10)
ax2.legend(fontsize=8.5,loc="lower right"); ax2.grid(True,which="both",alpha=.25)

plt.tight_layout()
plt.savefig("fig_threshold_suppression.pdf"); plt.savefig("fig_threshold_suppression.png",dpi=150)
print(f"slopes: d3={s3:.2f} d5={s5:.2f} d7={s7:.2f}  (targets 2/3/4)")
print("saved fig_threshold_suppression.{pdf,png}")
