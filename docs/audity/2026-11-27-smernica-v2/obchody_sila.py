"""Štatistická sila trezoru podľa počtu obchodov (Inžinier B, 27. 11. 2026, k 14_B_obchody_trezor.md).

Model: obchod je +W R alebo -1 R, winrate w, PF = w*W/(1-w) -> W = PF*(1-w)/w.
t = mean/sd*sqrt(n) (výberová sd). t závisí len od počtu výhier k ~ Bin(n, w),
takže sila a falošné poplachy sú presné súčty cez binomické rozdelenie, nie simulácia.
Drawdown a rozptyl PF: Monte Carlo cesty (seed 7).
Spustenie: /Users/martin/IBS/.venv/bin/python -I obchody_sila.py
"""
import numpy as np
from scipy.stats import binom, norm

NS = [150, 220, 300, 500]
PFS = [1.1, 1.2, 1.3, 1.5]
WRS = [0.40, 0.50, 0.60]
TREQ = [2.0, 2.6, 3.0, 3.3]


def per_k(n, w, pf):
    """Pre každé k = 0..n: t, PF výberu a pravdepodobnosť k pri skutočnom winrate w."""
    W = pf * (1 - w) / w
    k = np.arange(n + 1)
    s = k * W - (n - k)
    mean = s / n
    ss = k * W**2 + (n - k)
    var = (ss - n * mean**2) / (n - 1)
    sd = np.sqrt(np.maximum(var, 1e-300))
    t = mean / sd * np.sqrt(n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pfo = np.where(k < n, k * W / np.maximum(n - k, 1), np.inf)
    return t, pfo, binom.pmf(k, n, w), W


def exp_t(n, w, pf):
    W = pf * (1 - w) / w
    m = w * W - (1 - w)
    sd = np.sqrt(w * W**2 + (1 - w) - m**2)
    return m / sd * np.sqrt(n)


def power(n, w, pf, treq):
    t, _, p, _ = per_k(n, w, pf)
    return p[t >= treq].sum()


def null_prob(n, w, pf_test, edge_pf=1.0):
    """Stratégia bez edge (skutočný PF 1,0, výplata W nastavená pre PF 1,0)."""
    t, pfo, p, _ = per_k(n, w, edge_pf)
    return p[pfo >= pf_test].sum(), p[t >= 2.0].sum()


def n_for_power(w, pf, treq, target=0.8):
    for n in range(30, 5001, 5):
        if power(n, w, pf, treq) >= target:
            return n
    return None


def mc(n, w, pf, sims=20000, seed=7):
    rng = np.random.default_rng(seed)
    W = pf * (1 - w) / w
    r = np.where(rng.random((sims, n)) < w, W, -1.0)
    eq = np.cumsum(r, axis=1)
    peak = np.maximum.accumulate(np.concatenate([np.zeros((sims, 1)), eq], axis=1), axis=1)[:, 1:]
    dd = (peak - eq).max(axis=1)
    wins = np.where(r > 0, r, 0).sum(1)
    loss = -np.where(r < 0, r, 0).sum(1)
    pfo = wins / np.maximum(loss, 1e-9)
    return dd, pfo


def main():
    print("== A. E[t] (WR 40 / 50 / 60 %) ==")
    for pf in PFS:
        print(f"PF {pf}: " + "  ".join(
            f"n={n}: " + "/".join(f"{exp_t(n, w, pf):.2f}" for w in WRS) for n in NS))

    print("\n== B. Sila P(t >= t_req), jednostranne, WR 50 % [rozsah WR 40-60 %] ==")
    for treq in TREQ:
        print(f"t_req {treq}")
        for pf in PFS:
            cells = []
            for n in NS:
                ps = [power(n, w, pf, treq) for w in WRS]
                cells.append(f"n={n}: {ps[1]*100:4.0f} % [{min(ps)*100:.0f}-{max(ps)*100:.0f}]")
            print(f"  PF {pf}: " + " | ".join(cells))

    print("\n== C. Jednostranná p pri E[t] (WR 50 %) ==")
    for pf in PFS:
        print(f"PF {pf}: " + "  ".join(f"n={n}: p={norm.sf(exp_t(n, .5, pf)):.4f}" for n in NS))

    print("\n== D. Bez edge (PF 1,0): P(PF_trezor >= 1,2) | P(PF >= 1,1) | P(t >= 2,0) ==")
    for n in NS:
        cells = []
        for w in WRS:
            p12, pt = null_prob(n, w, 1.2)
            p11, _ = null_prob(n, w, 1.1)
            cells.append(f"WR{int(w*100)}: {p12*100:.1f} % | {p11*100:.1f} % | {pt*100:.1f} %")
        print(f"n={n}: " + "   ".join(cells))

    print("\n== E. n pre 80 % silu (WR 40 / 50 / 60 %) ==")
    for treq in TREQ:
        print(f"t_req {treq}: " + "  ".join(
            f"PF {pf}: " + "/".join(str(n_for_power(w, pf, treq)) for w in WRS) for pf in PFS))

    print("\n== F. Monte Carlo WR 50 %: max DD v R (medián / p95), PF výberu p5-p95, P(PF_výber < 1,0) ==")
    for pf in [1.2, 1.3, 1.5]:
        for n in [150, 220, 300]:
            dd, pfo = mc(n, .5, pf)
            print(f"PF {pf} n={n}: DD {np.median(dd):.1f} / {np.percentile(dd, 95):.1f} R, "
                  f"PF {np.percentile(pfo, 5):.2f}-{np.percentile(pfo, 95):.2f}, "
                  f"P(PF<1) {np.mean(pfo < 1)*100:.1f} %")
    print("  (FTMO max strata 10 %: pri riziku 0,5 %/obchod = 20 R, pri 0,25 % = 40 R)")

    from scipy.optimize import brentq
    print("\n== G. Pozorovaný PF potrebný na t_req (WR 40 / 50 / 60 %) ==")
    for n in [150, 210, 300]:
        print(f"n={n}: " + "  ".join(
            f"t {t}: " + "/".join(f"{brentq(lambda p: exp_t(n, w, p) - t, 1.0001, 10):.2f}" for w in WRS)
            for t in TREQ))


if __name__ == "__main__":
    main()
