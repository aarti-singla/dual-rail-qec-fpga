# Generates syndrome/correction vectors for the co-simulation testbench.
import numpy as np, stim, pymatching


def gen_vectors(p=0.05, shots=5000, seed=123):
    circ = stim.Circuit.generated(
        "repetition_code:memory", distance=3, rounds=1,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p/2)
    sampler = circ.compile_detector_sampler(seed=seed)
    dets, obs = sampler.sample(shots=shots, separate_observables=True)
    syndrome = dets[:, 0:2].astype(int)   # s_zz01, s_zz12 -- matches the paper
    return syndrome

# Ground truth: the paper's own closed-form syndrome-to-error table
def closed_form(s_zz01, s_zz12):
    if s_zz01==0 and s_zz12==0: return (0,0,0)   # no error
    if s_zz01==1 and s_zz12==0: return (1,0,0)   # q0
    if s_zz01==1 and s_zz12==1: return (0,1,0)   # q1
    if s_zz01==0 and s_zz12==1: return (0,0,1)   # q2

if __name__ == "__main__":
    syndrome = gen_vectors()
    unique, counts = np.unique(syndrome, axis=0, return_counts=True)
    print(f"Real Stim-sampled syndrome distribution (p=0.05, {len(syndrome)} shots):")
    for s, c in zip(unique, counts):
        print(f"  s_zz01={s[0]} s_zz12={s[1]}: {c} occurrences ({c/len(syndrome)*100:.2f}%)")

    with open("cosim_vectors.txt", "w") as f:
        for s in syndrome:
            f.write(f"{s[0]} {s[1]}\n")
    print(f"\nWrote {len(syndrome)} real Stim-sampled syndrome vectors to cosim_vectors.txt")
