# Mode-count and logical-error-rate scaling across code distances.

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Paper constants ──────────────────────────────────────────────────────────
A_FIT   = 0.69      # Eq. (3) prefactor (Piquasso, deff≈2, post-selected)
EXP_FIT = 1.95      # Eq. (3) fitted exponent
FIT_PMIN, FIT_PMAX = 1e-4, 2e-2   # Eq.(3) was fitted ONLY on this range
                                  # (Sec. V-B).  Do not extrapolate past it.

P_TH_PIQUASSO = 0.0086   # Sec. V-B / Table VII (deff≈2 post-selected crossover)
P_TH_D3_TABLE = 0.10     # Table IV "~10%" (d=3 repetition-code threshold)

# Table IV: Stim simulation data points at p_phys = 1%
STIM_P     = 0.01
STIM_PL_D2 = 2.13e-2   # d=2 (deff≈2), Pauli, no discard
STIM_PL_D3 = 2.36e-3   # d=3, Pauli, no discard

# Mode counts (paper Section III / Table IV / Conclusion)
MODES = {2: 33, 3: 55, 5: 99}


def pL_deff2(p_phys: float) -> float:
    """Eq. (3): PL = 0.69 * p_phys^1.95  (Piquasso, deff≈2, WITH post-selection)."""
    return A_FIT * p_phys ** EXP_FIT


def threshold_sanity(p_th: float, label: str) -> bool:
    ok = 0.02 <= p_th <= 0.15
    tag = "PASS" if ok else "FAIL"
    band = "within" if ok else "OUTSIDE"
    print(f"[{tag}] threshold sanity ({label}): p_th = {p_th:.4f}  "
          f"({band} repetition-code band 0.02-0.15)")
    return ok


def main():
    # Plot range for the analytic curve is clamped to the FIT domain.
    p_fit = np.logspace(np.log10(FIT_PMIN), np.log10(FIT_PMAX), 80)
    # Wider range only for the no-QEC reference line and the Stim markers.
    p_ref = np.logspace(-2.5, -0.7, 80)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # ── Left panel: error suppression ────────────────────────────────────────
    # Eq.(3): Piquasso deff≈2 WITH post-selection -- only over its fit domain.
    pL_eq3 = [pL_deff2(p) for p in p_fit]
    ax1.loglog(p_fit, pL_eq3, '--', color='#D85A30', lw=1.8,
               label=r'Piquasso fit, Eq.(3), deff≈2 (post-selected)')

    # Stim points: Pauli, NO discard -- a different observable.
    ax1.loglog(STIM_P, STIM_PL_D3, 's', color='#185FA5', ms=9, zorder=5,
               label=r'$d{=}3$ Stim, Pauli ($p_L=2.36\times10^{-3}$)')
    ax1.loglog(STIM_P, STIM_PL_D2, 'o', color='#7A2D12', ms=9,
               markerfacecolor='none', zorder=5,
               label=r'$d{=}2$ Stim, Pauli ($p_L=2.13\times10^{-2}$)')

    # No-QEC baseline
    ax1.loglog(p_ref, p_ref, 'k--', alpha=0.4, label='No QEC (physical)')

    # ROOT CAUSE annotation: the 245x gap between the two "deff≈2" numbers.
    eq3_at_1pct = pL_deff2(STIM_P)
    ax1.annotate('', xy=(STIM_P, STIM_PL_D2), xytext=(STIM_P, eq3_at_1pct),
                 arrowprops=dict(arrowstyle='<->', color='gray', lw=1.2, ls=':'))
    ax1.text(STIM_P * 0.55, np.sqrt(STIM_PL_D2 * eq3_at_1pct),
             f'{STIM_PL_D2/eq3_at_1pct:.0f}×\n(post-sel.\nvs Pauli)',
             color='gray', fontsize=7.5, va='center', ha='right')

    # Two threshold candidates, clearly distinguished.
    ax1.axvline(P_TH_PIQUASSO, color='#D85A30', ls=':', alpha=0.7,
                label=rf'$p_{{th}}={P_TH_PIQUASSO}$ (Piquasso deff≈2)')
    ax1.axvline(P_TH_D3_TABLE, color='#185FA5', ls=':', alpha=0.7,
                label=rf'$p_{{th}}\approx{P_TH_D3_TABLE}$ (Table IV, d=3)')

    # 9x annotation -- labelled as a RATIO, not suppression vs physical.
    ax1.annotate('', xy=(STIM_P, STIM_PL_D3), xytext=(STIM_P, STIM_PL_D2),
                 arrowprops=dict(arrowstyle='<->', color='#1D9E75', lw=1.5))
    ax1.text(STIM_P * 1.10, np.sqrt(STIM_PL_D2 * STIM_PL_D3),
             r'$9\times$ (d2$\to$d3)', color='#1D9E75', fontsize=9, va='center')

    ax1.set_xlabel(r'Physical error rate $p_\mathrm{phys}$')
    ax1.set_ylabel(r'Logical error rate $p_L$')
    ax1.set_title('Error rates: Piquasso (post-sel.) vs Stim (Pauli)')
    ax1.legend(fontsize=7.5, loc='lower right')
    ax1.grid(alpha=0.2)

    # ── Right panel: mode overhead ────────────────────────────────────────────
    d_paper  = [2,  3,  5]
    m_paper  = [33, 55, 99]
    colors_p = ['#D85A30', '#185FA5', '#1D9E75']
    markers  = ['o', 's', '^']
    status   = ['Phase 1\n(33-mode hardware)',
                'd=3 extended\n(55-mode sim)',
                'Phase 2\n(99-mode planned)']

    ax2.plot(d_paper, m_paper, '-', color='gray', lw=1, alpha=0.5, zorder=1)
    for d, m, c, mk, st in zip(d_paper, m_paper, colors_p, markers, status):
        ax2.scatter(d, m, color=c, marker=mk, s=80, zorder=5)
        ax2.annotate(f'  {m} modes\n  {st}', (d, m), fontsize=8, color=c,
                     va='center')

    ax2.set_xlabel('Effective code distance')
    ax2.set_ylabel('Total photonic modes')
    ax2.set_title('Mode-overhead scaling (paper data)')
    ax2.set_xticks(d_paper)
    ax2.set_xlim(1, 6)
    ax2.grid(alpha=0.2)

    plt.tight_layout()
    plt.savefig('resource_scaling.pdf', dpi=300, bbox_inches='tight')
    print("[OK] saved resource_scaling.pdf\n")

    # ── Resource table ────────────────────────────────────────────────────────
    print("Resource overhead table (all values from paper):")
    hdr = (f"{'Phase':<26} {'d':<4} {'Modes':<7} {'Source':<18} "
           f"{'pL @ 1%':<11} {'vs physical':<16} {'Note'}")
    print(hdr)
    print("-" * 100)
    rows = [
        ('Phase 1 (deff≈2)', 2, 33, 'Stim Table IV',   STIM_PL_D2, ''),
        ('d=3 extended sim', 3, 55, 'Stim Table IV',   STIM_PL_D3, '9× vs d=2'),
        ('Phase 2 (d=5)',    5, 99, 'Planned (no sim)', None,       'Future work'),
    ]
    for phase, d, modes, src, pL, note in rows:
        if pL is not None:
            supp = STIM_P / pL
            flag = '✓ better' if supp > 1 else '✗ WORSE'
            supp_str = f"{supp:.2f}× {flag}"
            pL_str = f"{pL:.2e}"
        else:
            supp_str = "—"
            pL_str = "—"
        print(f"{phase:<26} {d:<4} {modes:<7} {src:<18} "
              f"{pL_str:<11} {supp_str:<16} {note}")

    # ── Reconciliation + sanity checks ───────────────────────────────────────
    print("\n--- Threshold reconciliation (paper quotes two values) ---")
    threshold_sanity(P_TH_PIQUASSO, "Piquasso deff≈2, Sec. V-B / Table VII")
    threshold_sanity(P_TH_D3_TABLE, "Table IV ~10%, d=3 repetition")
    print("  -> 0.0086 is a deff≈2 (distance-2 detection) post-selected "
          "crossover, NOT the d=3 repetition threshold.")
    print("  -> Per constraint #7 the d=3 rep-code threshold is ~0.05-0.10; "
          "use Table IV's ~10%, or extract it properly in script 11/17.")

    print("\n--- Eq.(3) vs Stim (same deff≈2 system, different noise model) ---")
    gap = STIM_PL_D2 / pL_deff2(STIM_P)
    print(f"  Eq.(3) PL(1%)  = {pL_deff2(STIM_P):.3e}  (Piquasso, post-selected)")
    print(f"  Stim d=2 PL(1%)= {STIM_PL_D2:.3e}  (Pauli, no discard)")
    print(f"  [WARN] they differ by {gap:.0f}× -- NOT interchangeable; the gap "
          f"is post-selection discard, not numerical error.")

    print("\n--- The '9×' claim, three ways ---")
    print(f"  d=2 -> d=3 ratio      : {STIM_PL_D2/STIM_PL_D3:.2f}×  "
          f"(this is the abstract's 9×)")
    print(f"  d=3 vs physical (1%)  : {STIM_P/STIM_PL_D3:.2f}×  "
          f"(NOT 9×)")
    print(f"  d=2 vs physical (1%)  : {STIM_P/STIM_PL_D2:.2f}×  "
          f"(<1 => d=2 is WORSE than physical)")

    # Expected-sign PASS/FAIL gate.
    print("\n--- PASS/FAIL ---")
    c1 = STIM_PL_D3 < STIM_P          # d=3 beats physical
    c2 = STIM_PL_D2 > STIM_P          # d=2 worse than physical (detection only)
    c3 = abs(STIM_PL_D2/STIM_PL_D3 - 9.0) < 0.5   # the 9× ratio holds
    print(f"[{'PASS' if c1 else 'FAIL'}] d=3 suppresses below physical")
    print(f"[{'PASS' if c2 else 'FAIL'}] d=2 is above physical (detection-only, expected)")
    print(f"[{'PASS' if c3 else 'FAIL'}] d=2/d=3 ratio ≈ 9×")

if __name__ == "__main__":
    main()

