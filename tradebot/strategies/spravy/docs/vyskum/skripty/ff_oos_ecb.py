"""ECB na odloženom období 4/2025 – 9/2026 (oficiálne termíny ecb.europa.eu), tie isté obchody ako vo výbere."""
import numpy as np, pandas as pd
S = "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad"
exec(open(f"{S}/ffwork/ff_gold.py", encoding="utf-8").read().split("rows = []")[0])
DATES = ["2025-04-17", "2025-06-05", "2025-07-24", "2025-09-11", "2025-10-30", "2025-12-18",
         "2026-02-05", "2026-03-19", "2026-04-30", "2026-06-11", "2026-07-23", "2026-09-10"]
def ms_at(d, hm): return int(pd.Timestamp(f"{d} {hm}").tz_localize("Europe/Berlin").tz_convert("UTC").timestamp() * 1000)
def trade(ms, fa, fb, sg, en, ex):
    p0, p1, pe, px_ = px(ms, fa), px(ms, fb), px(ms, en), px(ms, ex)
    if None in (p0, p1, pe, px_) or p1 == p0: return np.nan
    s = sg * (1 if p1 > p0 else -1)
    return 10 * (s * (px_ - pe) - 1.755e-5 * (pe + px_) - 0.2)
X = pd.read_csv(f"{S}/ffwork/ff_gold_trades.csv")
for typ, hm, h in (("ECB_TK", "14:45", "trend 0→15, drž do T+120"), ("ECB", "14:15", "trend 15→60, drž do T+240")):
    ins = X[(X.typ == typ) & ~X.usd][h].dropna()
    oos = pd.Series([trade(ms_at(d, hm), *HYP[h]) for d in DATES]).dropna()
    sp = [spike(ms_at(d, hm)) for d in DATES]
    def st(x):
        g, l = x[x > 0].sum(), -x[x < 0].sum()
        return f"n {len(x):2} WR {100*(x > 0).mean():3.0f}% PF {g/l if l else 99:5.2f} spolu {x.sum():+6.0f}$ priem. {x.mean():+5.0f}$"
    print(f"{typ} {hm} SEČ — {h}")
    print(f"   výber 2021 – 3/2025:   {st(ins)}")
    print(f"   odložené 4/2025 – 9/2026: {st(oos)}   (výbuch volatility v čase: medián {np.nanmedian(sp):.1f}×)")
    print("   obchody:", " ".join(f"{d[2:]}:{v:+.0f}" for d, v in zip(DATES, [trade(ms_at(d, hm), *HYP[h]) for d in DATES])))
