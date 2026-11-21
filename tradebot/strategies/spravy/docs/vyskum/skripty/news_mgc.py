"""MGC po správach: trend (smer prvého pohybu) aj fade, CPI / NFP / FOMC zvlášť, dlhšie horizonty, stop × prvý pohyb."""
import sys
from datetime import timedelta
import pandas as pd
sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
sys.path.insert(0, "/Users/martin/document/IBS")
from news_study import close_at, event_times, load, price_at, daily_atr
FEE = 1.755e-05
def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum(); return g / l if l else float("inf")
def sim(df, atr, when, k, h, m, direction, min_atr=0.0):
    out = []
    for t in when:
        o = price_at(df, t, "o"); c1 = close_at(df, t + timedelta(minutes=k))
        a = atr.get(pd.Timestamp(t.date()))
        if o is None or c1 is None or c1 == o or a is None or a != a: continue
        if abs(c1 - o) < min_atr * a: continue
        first = 1 if c1 > o else -1
        side = direction * first
        stop = c1 - side * m * abs(c1 - o) if m else None
        path = df.loc[t + timedelta(minutes=k): t + timedelta(minutes=k + h - 1)]
        if path.empty: continue
        px = float(path.c.iloc[-1])
        if stop is not None:
            hit = path[path.h >= stop] if side < 0 else path[path.l <= stop]
            if not hit.empty: px = stop
        out.append((t.year, side * (px - c1) - FEE * (c1 + px)))
    return pd.DataFrame(out, columns=["y", "p"])
df = load("mgc_databento"); atr = daily_atr(df)
for name, ev in (("CPI", ["CPI"]), ("NFP", ["NFP"]), ("CPI+NFP", ["CPI", "NFP"]), ("FOMC", ["FOMC"])):
    when = event_times(ev)
    best = []
    for d, dn in ((1, "TREND"), (-1, "FADE")):
        for k in (5, 15, 30):
            for h in (60, 120, 240, 480):
                for m in (0, 1.0, 2.0):
                    for mn in (0.0, 0.3):
                        r = sim(df, atr, when, k, h, m, d, mn)
                        if len(r) < 15: continue
                        yr = r.groupby("y").p.apply(pf)
                        best.append((pf(r.p), f"{name:7s} {dn:5s} k={k:2d} h={h:3d} stop={m}× min={mn}ATR: n={len(r)} PF {pf(r.p):.2f} WR {100*(r.p>0).mean():.0f}% rokov>1 {int((yr>1).sum())}/{len(yr)} min rok {yr.min():.2f}"))
    best.sort(reverse=True)
    print(f"== {name}: 6 najlepších z {len(best)} variant (trend aj fade)")
    for _, s in best[:6]: print("  ", s)
    print(f"   medián PF všetkých variant: {sorted(b[0] for b in best)[len(best)//2]:.2f}")
