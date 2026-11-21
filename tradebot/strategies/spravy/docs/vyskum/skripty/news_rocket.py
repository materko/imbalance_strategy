"""Zlato po FOMC / PCE (trend): ako chytiť raketu — výstup v čase vs trailing stop; ladenie 2021–2024, odložené 2025–2026.

Vstup: close(T+60) v smere close(T+15) → close(T+60). Počiatočný stop: druhý extrém nohy T+15..T+60 (± rezerva).
Výstupy: (a) čas h, (b) trailing stop m × ATR dňa od najlepšej ceny, najdlhšie H hodín, (c) presun na break-even po 1 R.
Výsledok v R (riziko = vstup → počiatočný stop), po poplatku.
"""

from __future__ import annotations

import math
import sys
from datetime import timedelta

import pandas as pd

sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
from news_gold import assign  # noqa: E402
from news_study import close_at, daily_atr, load  # noqa: E402

FEE = 1.755e-05


def trade(df, atr, t, a, b, exit_mode, h_hours, trail_atr):
    p0 = close_at(df, t + timedelta(minutes=a))
    p1 = close_at(df, t + timedelta(minutes=b))
    at = atr.get(pd.Timestamp(t.date()))
    if None in (p0, p1) or p0 == p1 or at is None or at != at:
        return None
    side = 1 if p1 > p0 else -1
    leg = df.loc[t + timedelta(minutes=a): t + timedelta(minutes=b - 1)]
    stop = (leg.l.min() if side > 0 else leg.h.max()) - side * 0.1 * at
    risk = abs(p1 - stop)
    if risk <= 0:
        return None
    path = df.loc[t + timedelta(minutes=b): t + timedelta(minutes=b) + timedelta(hours=h_hours)]
    if path.empty:
        return None
    best = p1
    exit_px = float(path.c.iloc[-1])
    for _, bar in path.iterrows():
        if (side > 0 and bar.l <= stop) or (side < 0 and bar.h >= stop):
            exit_px = stop
            break
        best = max(best, bar.h) if side > 0 else min(best, bar.l)
        if exit_mode == "trail":
            stop = max(stop, best - trail_atr * at) if side > 0 else min(stop, best + trail_atr * at)
    pnl = side * (exit_px - p1) - FEE * (p1 + exit_px)
    return {"y": t.year, "r": pnl / risk, "pts": pnl, "max_r": side * (best - p1) / risk}


def evaluate(df, atr, when, **kw):
    rows = [x for t in when if (x := trade(df, atr, t, **kw))]
    return pd.DataFrame(rows)


def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum()
    return g / l if l else float("inf")


def main():
    df = load("mgc_databento")
    atr = daily_atr(df)
    g = assign()
    when = sorted(g["FOMC"] + g["PCE"])
    ins = [t for t in when if t.year <= 2024]
    oos = [t for t in when if t.year >= 2025]
    variants = []
    for a, b in ((15, 60), (0, 60)):
        for h in (4, 8, 24, 48):
            variants.append(dict(a=a, b=b, exit_mode="time", h_hours=h, trail_atr=0))
            for m in (0.5, 0.75, 1.0, 1.5):
                variants.append(dict(a=a, b=b, exit_mode="trail", h_hours=h, trail_atr=m))
    res = []
    for v in variants:
        r = evaluate(df, atr, ins, **v)
        if len(r) < 20:
            continue
        res.append((pf(r.r), v, r))
    res.sort(key=lambda x: -x[0])
    print("== ladenie 2021–2024 (FOMC + PCE trend), 10 najlepších z", len(res))
    for p, v, r in res[:10]:
        yr = r.groupby("y").r.apply(pf)
        big = (r.r >= 3).sum()
        print(f"  noha {v['a']}→{v['b']} {v['exit_mode']:5s} max {v['h_hours']:2d} h trail {v['trail_atr']}: n={len(r)} PF {p:.2f} "
              f"priem {r.r.mean():+.2f} R | rakiet ≥ 3 R: {big} | najväčšia {r.r.max():+.1f} R | " +
              " ".join(f"{y%100}:{x:.2f}" for y, x in yr.items()))
    print("== medián PF všetkých variantov (ladenie):", round(sorted(x[0] for x in res)[len(res)//2], 2))
    p, v, r = res[0]
    o = evaluate(df, atr, oos, **v)
    print(f"== ODLOŽENÉ 2025–2026, víťaz ladenia: n={len(o)} PF {pf(o.r):.2f} priem {o.r.mean():+.2f} R | rakiet ≥ 3 R: {(o.r >= 3).sum()} "
          f"| najväčšia {o.r.max():+.1f} R | " + " ".join(f"{y%100}:{x:.2f}" for y, x in o.groupby('y').r.apply(pf).items()))
    allo = [pf(evaluate(df, atr, oos, **vv).r) for _, vv, _ in res[:10]]
    print("== odložené PF 10 najlepších z ladenia:", [round(x, 2) for x in allo])
    print("== odložené: medián PF všetkých variantov:",
          round(sorted(pf(evaluate(df, atr, oos, **vv).r) for _, vv, _ in res)[len(res) // 2], 2))


if __name__ == "__main__":
    main()
