import sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
from news_gold import assign, run, pf, stat
from news_study import load, daily_atr
import pandas as pd
df = load("mgc_databento"); atr = daily_atr(df); g = assign()
def show(title, names, a, b, h, sign):
    when = sorted(sum((g[n] for n in names), []))
    r = run(df, atr, when, a, b, h); r["p"] = sign * r.p - (0 if sign > 0 else 2 * 1.755e-05 * 0)  # poplatok už v run
    if sign < 0:   # fade: obrátený smer, poplatok sa nesmie obrátiť
        r = run(df, atr, when, a, b, h); r["p"] = -r.p - 2 * 1.755e-05 * 0
    s = stat(r); yr = r.groupby("y").p.apply(pf)
    print(f"{title:40s} noha {a}→{b} drž {h}: n={s['n']} ({s['n']/5.8:.0f}/rok) PF {s['pf']:.2f} t={s['t']:+.2f} rokov>1 {s['yrs']} | " + " ".join(f"{y%100}:{v:.2f}" for y, v in yr.items()))
for a, b, h in ((0, 60, 120), (0, 60, 240), (15, 60, 240), (0, 30, 240)):
    show("TREND  FOMC+PCE", ["FOMC", "PCE"], a, b, h, 1)
    show("TREND  FOMC+PCE+GDP+NFP", ["FOMC", "PCE", "GDP", "NFP"], a, b, h, 1)
for a, b, h in ((0, 30, 120), (0, 60, 60), (0, 15, 240), (0, 30, 240)):
    show("FADE   CPI+PPI+JOLTS", ["CPI", "PPI", "JOLTS"], a, b, h, -1)
