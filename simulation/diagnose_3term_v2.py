# Fit-window diagnostic for the 3-term noise model, with multi-start optimisation.
import numpy as np, stim, pymatching, time
from scipy.optimize import minimize


def logical_error_rate(d, p, rounds, shots, seed, after_clifford_mult=0.25):
    circ = stim.Circuit.generated(
        "repetition_code:memory", distance=d, rounds=rounds,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p/2,
        after_clifford_depolarization=after_clifford_mult*p)
    sampler = circ.compile_detector_sampler(seed=seed)
    dets, obs = sampler.sample(shots=shots, separate_observables=True)
    m = pymatching.Matching.from_detector_error_model(
        circ.detector_error_model(decompose_errors=True))
    pred = m.decode_batch(dets)
    fails = np.any(pred != obs, axis=1).sum()
    return fails / shots, fails


def collapse_residual(params, p_arr, pl_arr, d_arr, n_arr):
    p_th, nu, *poly = params
    if nu <= 0.1 or nu > 10 or p_th <= 0 or p_th > 1:
        return 1e10  # keep optimizer in physically sensible region
    x = (p_arr - p_th) * np.array([d**(1.0/nu) for d in d_arr])
    a0,a1,a2,a3 = (poly + [0,0,0])[:4]
    y_fit = a0 + a1*x + a2*x**2 + a3*x**3
    resid = (pl_arr - y_fit)
    w = np.sqrt(np.maximum(pl_arr*(1-pl_arr), 1e-8) / n_arr)
    return np.sum((resid/np.maximum(w,1e-6))**2)


def run_point_estimate_robust(distances, p_range, rounds_map, shots, seed_base):
    p_arr, pl_arr, d_arr, n_arr = [], [], [], []
    for d in distances:
        for pi, p in enumerate(p_range):
            pl, fails = logical_error_rate(d, p, rounds_map[d], shots, seed_base+d*1000+pi)
            p_arr.append(p); pl_arr.append(pl); d_arr.append(d); n_arr.append(shots)
    p_arr, pl_arr = np.array(p_arr), np.array(pl_arr)
    d_arr, n_arr = np.array(d_arr), np.array(n_arr)

    best = None
    p_guesses = np.linspace(p_range.min(), p_range.max(), 6)
    nu_guesses = [1.0, 1.5, 2.0]
    for p_th0 in p_guesses:
        for nu0 in nu_guesses:
            x0 = [p_th0, nu0, 0.01, 0.1, 0.01, 0.001]
            res = minimize(collapse_residual, x0, args=(p_arr, pl_arr, d_arr, n_arr),
                            method="Nelder-Mead",
                            options={"xatol":1e-6,"fatol":1e-8,"maxiter":5000})
            if res.fun < 1e9 and (best is None or res.fun < best.fun):
                best = res
    return best.x[0], best.x[1], best.fun

if __name__ == "__main__":
    distances = [5, 7]
    rounds_map = {5: 5, 7: 7}
    windows = {
        "main-campaign range (0.05-0.14)": np.logspace(-1.3, -0.85, 8),
        "intermediate range (0.10-0.20)": np.logspace(np.log10(0.10), np.log10(0.20), 8),
        "narrow re-eval range (0.16-0.26)": np.logspace(np.log10(0.16), np.log10(0.26), 8),
    }
    print("3-term ablation: p_th as a function of sweep window (robust multi-start fit)\n")
    for name, p_range in windows.items():
        t0 = time.time()
        p_th, nu, resid = run_point_estimate_robust(distances, p_range, rounds_map,
                                                       shots=200_000, seed_base=5000)
        print(f"  {name:35s} p_th={p_th:.4f}  nu={nu:.3f}  resid={resid:.3f}  ({time.time()-t0:.1f}s)")
