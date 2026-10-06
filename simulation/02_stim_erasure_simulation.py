# Erasure-aware threshold simulation for the dual-rail repetition code.

import numpy as np
import matplotlib.pyplot as plt

try:
    import stim
    import pymatching
except ImportError as ex:
    raise SystemExit("Install stim and pymatching: pip install stim pymatching") from ex


def build_erasure_circuit(d: int, p_loss: float, p_gate: float) -> stim.Circuit:
    """Repetition code of distance d with photon loss + gate depolarisation."""
    return stim.Circuit.generated(
        "repetition_code:memory",
        rounds=d,
        distance=d,
        before_round_data_depolarization=p_gate,
        before_measure_flip_probability=p_loss / 2,
        after_clifford_depolarization=p_gate / 2,
    )


def threshold_sweep(d_list=(3, 5, 7), n_shots=50_000):
    p_range = np.logspace(-2.5, -0.7, 12)
    results = {}

    for d in d_list:
        print(f"\n[d = {d}]")
        rates = []
        for p in p_range:
            circuit = build_erasure_circuit(d, p_loss=p, p_gate=p * 0.5)
            sampler = circuit.compile_detector_sampler()
            det, obs = sampler.sample(n_shots, separate_observables=True)
            matcher = pymatching.Matching.from_detector_error_model(
                circuit.detector_error_model(
                    decompose_errors=True,
                    approximate_disjoint_errors=True,
                    ignore_decomposition_failures=True))
            pred = matcher.decode_batch(det)
            pL = float(np.mean(np.any(pred != obs, axis=1)))
            rates.append(pL)
            print(f"   p_loss={p:.4f}   pL={pL:.5f}")
        results[d] = rates
    return p_range, results


def plot_threshold_curves(p_range, results):
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = {3: '#1D9E75', 5: '#534AB7', 7: '#D85A30'}
    for d, rates in results.items():
        ax.loglog(p_range, rates, 'o-', color=colors.get(d, 'k'),
                  lw=1.6, ms=4, label=f'd = {d}')
    ax.loglog(p_range, p_range, 'k--', alpha=0.4, label='No QEC')
    ax.set_xlabel('Physical error rate $p_{phys}$', fontsize=12)
    ax.set_ylabel('Logical error rate $p_L$', fontsize=12)
    ax.set_title('Erasure-aware dual-rail threshold simulation', fontsize=12)
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('threshold_erasure.pdf', dpi=300, bbox_inches='tight')
    print("[OK] saved threshold_erasure.pdf")

if __name__ == "__main__":
    p_range, results = threshold_sweep(d_list=(3, 5, 7), n_shots=50_000)
    plot_threshold_curves(p_range, results)
