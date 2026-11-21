"""Fade po CPI/NFP: stop ako násobok prvého pohybu, citlivosť na čas vstupu (k), výstup h; MNQ a ES."""
import sys
from datetime import timedelta
import pandas as pd
sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
sys.path.insert(0, "/Users/martin/document/IBS")
from news_study import close_at, event_times, load, price_at
from tradebot.core.types import INSTRUMENTS
FEE = 1.755e-05
def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum(); return g / l if l else float("inf")
def sim(df, when, k, h, m):
    out = []
    for t in when:
        o = price_at(df, t, "o"); c1 = close_at(df, t + timedelta(minutes=k))
        if o is None or c1 is None or c1 == o: continue
        side = -1 if c1 > o else 1
        stop = c1 - side * m * abs(c1 - o) if m else None
        path = df.loc[t + timedelta(minutes=k): t + timedelta(minutes=k + h - 1)]
        if path.empty: continue
        px = float(path.c.iloc[-1])
        if stop is not None:
            hit = path[path.h >= stop] if side < 0 else path[path.l <= stop]
            if not hit.empty: px = stop
        out.append((t.year, side * (px - c1) - FEE * (c1 + px)))
    return pd.DataFrame(out, columns=["y", "p"])
ev = event_times(["CPI", "NFP"])
for key in ("mnq_databento", "es_databento"):
    df = load(key)
    for k in (10, 15, 16, 20):
        for h in (60, 90, 120):
            for m in (0, 1.0, 1.5, 2.0):
                r = sim(df, ev, k, h, m)
                yr = r.groupby("y").p.apply(pf)
                print(f"{key[:3].upper()} k={k:2d} h={h:3d} stop={m}×pohyb: PF {pf(r.p):.2f} WR {100*(r.p>0).mean():.0f}% rokov>1 {int((yr>1).sum())}/{len(yr)} min rok {yr.min():.2f}")
