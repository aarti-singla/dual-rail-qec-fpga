# Checks pL(V) with the circuit configuration used in scripts 07 and 11.
import numpy as np, stim, pymatching


def repetition_circuit(d, p, after_clifford=0.0):
    # EXACT config from scripts 07 and 11
    return stim.Circuit.generated(
        "repetition_code:memory",
        rounds=d, distance=d,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p/2,
        after_clifford_depolarization=after_clifford,
    )


def logical_error_rate(d, p, n_shots, seed):
    circuit = repetition_circuit(d, p)
    sampler = circuit.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(n_shots, separate_observables=True)
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=True,
        ignore_decomposition_failures=False)
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pred = matcher.decode_batch(det)
    n_err = int(np.any(pred != obs, axis=1).sum())
    return n_err/n_shots, n_err

print("d=3, rounds=3, 2-term model (exact 07/11 config), 200k shots")
print("p = p_gate(V) = (1-V)/2\n")
print(f"{'V':<10}{'p_gate':<12}{'pL':<14}{'n_err':<8}{'vs 1e-3'}")
V_list = [0.95, 0.96, 0.97, 0.98, 0.985, 0.99, 0.993, 0.995, 0.999]
res = {}
for i, V in enumerate(V_list):
    p_gate = (1-V)/2
    pL, n_err = logical_error_rate(3, p_gate, 200_000, seed=4000+i)
    res[V] = pL
    mark = "BELOW" if pL < 1e-3 else "above"
    print(f"{V:<10.4f}{p_gate:<12.5f}{pL:<14.3e}{n_err:<8}{mark}")

# find crossing
print()
Vs = np.array(V_list); pLs = np.array([res[v] for v in V_list])
for i in range(len(Vs)-1):
    if (pLs[i]-1e-3)*(pLs[i+1]-1e-3) <= 0 and pLs[i]!=pLs[i+1]:
        lo, hi = np.log10(max(pLs[i],1e-12)), np.log10(max(pLs[i+1],1e-12))
        t = (np.log10(1e-3)-lo)/(hi-lo)
        Vc = Vs[i] + t*(Vs[i+1]-Vs[i])
        print(f">>> pL crosses 1e-3 at V = {Vc:.4f}")
        print(f">>> paper claims V > 0.993")
        break
