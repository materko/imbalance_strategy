"""Druhá noha po správe: smer close(T+a) → close(T+b) a jeho pokračovanie close(T+b) → close(T+b+h). MGC aj MNQ."""
import sys, math
from datetime import timedelta
import pandas as pd
sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
sys.path.insert(0, "/Users/martin/document/IBS")
from news_study import close_at, event_times, load, daily_atr
FEE = 1.755e-05
def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum(); return g / l if l else float("inf")
for key in ("mgc_databento", "mnq_databento"):
    df = load(key); atr = daily_atr(df)
    for name, ev in (("CPI+NFP", ["CPI", "NFP"]), ("FOMC", ["FOMC"])):
        for a, b in ((0, 15), (15, 60), (0, 60), (30, 90)):
            for h in (60, 120, 240, 480):
                out = []
                for t in event_times(ev):
                    p0 = close_at(df, t + timedelta(minutes=a)) if a else close_at(df, t + timedelta(minutes=0.5))
                    p1 = close_at(df, t + timedelta(minutes=b)); p2 = close_at(df, t + timedelta(minutes=b + h))
                    if None in (p0, p1, p2) or p1 == p0: continue
                    s = 1 if p1 > p0 else -1
                    out.append((t.year, s * (p2 - p1) - FEE * 2 * p1))
                r = pd.DataFrame(out, columns=["y", "p"]); x = r.p.values
                if len(r) < 10: continue
                t_ = x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))
                yr = r.groupby("y").p.apply(pf)
                print(f"{key[:3].upper()} {name:7s} smer {a:2d}→{b:2d} min, potom {h:3d} min: n={len(r):3d} PF {pf(r.p):.2f} pokračuje {100*(r.p>0).mean():.0f}% t={t_:+.2f} rokov>1 {int((yr>1).sum())}/{len(yr)}")
