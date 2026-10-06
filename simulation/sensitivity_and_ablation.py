#!/usr/bin/env python3
# Shot-count sensitivity and 3-term ablation of the threshold fit.
import numpy as np, stim, pymatching, json, time
from scipy.optimize import minimize


def logical_error_rate(d, p, rounds, shots, seed, after_clifford_mult=0.0):
    # after_clifford_mult=0.0 -> 2-term reference; 0.25 -> 3-term (after_clifford = p/4)
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
    x = (p_arr - p_th) * np.array([d**(1.0/nu) for d in d_arr])
    # cubic polynomial collapse function (matches standard FSS practice)
    a0,a1,a2,a3 = (poly + [0,0,0])[:4]
    y_fit = a0 + a1*x + a2*x**2 + a3*x**3
    resid = (pl_arr - y_fit)
    # weight by binomial std err (avoid div by zero)
    w = np.sqrt(np.maximum(pl_arr*(1-pl_arr), 1e-8) / n_arr)
    return np.sum((resid/np.maximum(w,1e-6))**2)


def fit_fss(p_arr, pl_arr, d_arr, n_arr):
    best = None
    for p0 in [0.15, 0.19, 0.22]:
        for nu0 in [1.0, 1.5, 2.0]:
            x0 = [p0, nu0, 0.25, 0.5, 0.0, 0.0]
            res = minimize(collapse_residual, x0, args=(p_arr,pl_arr,d_arr,n_arr),
                            method="Nelder-Mead",
                            options={"maxiter":4000,"xatol":1e-6,"fatol":1e-8})
            if best is None or res.fun < best.fun:
                best = res
    p_th, nu = best.x[0], best.x[1]
    ndof = len(p_arr) - 6
    chi2_ndof = best.fun / max(ndof,1)
    return p_th, nu, chi2_ndof, ndof


def run_campaign(distances, p_range, rounds_map, shots, after_clifford_mult, seed_base):
    p_arr, pl_arr, d_arr, n_arr = [], [], [], []
    raw = {}
    for d in distances:
        rows=[]
        for i,p in enumerate(p_range):
            rate, fails = logical_error_rate(d, p, rounds_map[d], shots,
                                              seed=seed_base+d*1000+i,
                                              after_clifford_mult=after_clifford_mult)
            if fails >= 20:  # same MIN_EVENTS guard as the paper
                p_arr.append(p); pl_arr.append(rate); d_arr.append(d); n_arr.append(shots)
            rows.append((p, rate, fails))
        raw[d]=rows
    p_arr=np.array(p_arr); pl_arr=np.array(pl_arr); d_arr=np.array(d_arr); n_arr=np.array(n_arr)
    p_th, nu, chi2, ndof = fit_fss(p_arr, pl_arr, d_arr, n_arr)
    return p_th, nu, chi2, ndof, raw


def bootstrap_ci(distances, p_range, rounds_map, shots, after_clifford_mult, seed_base,
                  n_boot=40):
    # get raw fails/shots once, then bootstrap by resampling binomial outcomes
    p_th0, nu0, chi2_0, ndof0, raw = run_campaign(distances, p_range, rounds_map,
                                                    shots, after_clifford_mult, seed_base)
    boots_pth, boots_nu = [], []
    rng = np.random.default_rng(12345)
    for b in range(n_boot):
        p_arr, pl_arr, d_arr, n_arr = [], [], [], []
        for d in distances:
            for (p, rate, fails) in raw[d]:
                # resample fails ~ Binomial(shots, rate_hat)
                resampled = rng.binomial(shots, rate) 
                if resampled >= 20:
                    p_arr.append(p); pl_arr.append(resampled/shots)
                    d_arr.append(d); n_arr.append(shots)
        if len(p_arr) < 6: continue
        p_arr=np.array(p_arr); pl_arr=np.array(pl_arr); d_arr=np.array(d_arr); n_arr=np.array(n_arr)
        try:
            pth_b, nu_b, _, _ = fit_fss(p_arr, pl_arr, d_arr, n_arr)
            boots_pth.append(pth_b); boots_nu.append(nu_b)
        except Exception:
            continue
    return p_th0, nu0, chi2_0, ndof0, np.std(boots_pth), np.std(boots_nu), len(boots_pth)

if __name__ == "__main__":
    distances = [5, 7]
    rounds_map = {5: 5, 7: 7}   # rounds = d, matching circuit-level convention
    p_range = np.logspace(np.log10(0.16), np.log10(0.26), 8)  # narrower window, feasible runtime

    results = {}

    # ---------- (A) shot-count sensitivity ----------
    print("=== (A) Shot-count sensitivity sweep ===")
    for shots in [50_000, 200_000, 1_000_000]:
        t0=time.time()
        p_th, nu, chi2, ndof, sd_pth, sd_nu, nboot = bootstrap_ci(
            distances, p_range, rounds_map, shots, after_clifford_mult=0.0,
            seed_base=7000, n_boot=30)
        dt=time.time()-t0
        print(f"shots={shots:>8,}  p_th={p_th:.4f}+/-{sd_pth:.4f}  "
              f"nu={nu:.3f}+/-{sd_nu:.3f}  chi2/ndof={chi2:.2f}  "
              f"(n_boot={nboot}, {dt:.1f}s)")
        results[f"shots_{shots}"] = dict(p_th=p_th, sd_pth=sd_pth, nu=nu, sd_nu=sd_nu,
                                          chi2=chi2, ndof=ndof, n_boot=nboot)

    # ---------- (B) 3-term ablation uncertainty ----------
    print("\n=== (B) 3-term noise ablation, with bootstrap uncertainty ===")
    p_th3, nu3, chi2_3, ndof3, sd_pth3, sd_nu3, nboot3 = bootstrap_ci(
        distances, p_range, rounds_map, shots=200_000, after_clifford_mult=0.25,  # after_clifford = 0.25*p = p/4
        seed_base=9000, n_boot=30)
    print(f"3-term: p_th={p_th3:.4f}+/-{sd_pth3:.4f}  nu={nu3:.3f}+/-{sd_nu3:.3f}  "
          f"chi2/ndof={chi2_3:.2f}  (n_boot={nboot3})")
    results["threeterm"] = dict(p_th=p_th3, sd_pth=sd_pth3, nu=nu3, sd_nu=sd_nu3,
                                 chi2=chi2_3, ndof=ndof3, n_boot=nboot3)

    with open("sensitivity_ablation_results.json","w") as f:
        json.dump(results, f, indent=2)
    print("\nsaved sensitivity_ablation_results.json")
