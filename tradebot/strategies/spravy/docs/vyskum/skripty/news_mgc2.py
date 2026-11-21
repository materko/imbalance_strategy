import sys, math
sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
from news_mgc import sim, pf, df, atr
from news_study import event_times
import numpy as np
def line(name, ev, d, k, h, m, mn):
    r = sim(df, atr, event_times(ev), k, h, m, d, mn)
    yr = r.groupby("y").p.apply(pf); x = r.p.values
    t = x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))
    return f"{name} {'TREND' if d>0 else 'FADE '} k={k:2d} h={h:3d} stop={m} min={mn}: n={len(r):3d} PF {pf(r.p):.2f} t={t:+.2f} rokov>1 {int((yr>1).sum())}/{len(yr)} | " + " ".join(f"{y%100}:{v:.2f}" for y, v in yr.items())
print("== FOMC trend — okolie")
for k in (15, 30, 45):
    for h in (120, 240, 480):
        print(line("FOMC", ["FOMC"], 1, k, h, 2.0, 0.0))
print("== CPI+NFP fade veľkého pohybu — okolie")
for mn in (0.2, 0.3, 0.4):
    for k in (10, 15, 20):
        for h in (60, 120, 240):
            print(line("CPI+NFP", ["CPI", "NFP"], -1, k, h, 2.0, mn))
