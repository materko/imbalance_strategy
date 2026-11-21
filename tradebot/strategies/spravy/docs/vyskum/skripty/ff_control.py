"""Kontrola: ten istý obchod v rovnaký deň v týždni a čas o týždeň skôr / neskôr (bez tej správy)."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/ffwork")
import importlib.util
spec = importlib.util.spec_from_file_location("g", "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/ffwork/ff_gold.py")
S = "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad"
src = open(f"{S}/ffwork/ff_gold.py", encoding="utf-8").read().split("rows = []")[0]
exec(src)
X = pd.read_csv(f"{S}/ffwork/ff_gold_trades.csv")
allnews = np.sort(np.concatenate([X.ms.values]))
def trade(ms, fa, fb, sg, en, ex):
    p0, p1, pe, px_ = px(ms, fa), px(ms, fb), px(ms, en), px(ms, ex)
    if None in (p0, p1, pe, px_) or p1 == p0: return np.nan
    s = sg * (1 if p1 > p0 else -1)
    return 10 * (s * (px_ - pe) - 1.755e-5 * (pe + px_) - 0.2)
CANDS = [("CA_JOBS", "trend 15→60, drž do T+240"), ("BOJ_TK", "trend 15→60, drž do T+240"), ("ECB", "trend 15→60, drž do T+240"),
         ("EZ_PMI", "fade 0→60, drž do T+120"), ("CN_DATA", "trend 15→60, drž do T+240"), ("CA_GDP", "trend 15→60, drž do T+240"),
         ("UK_PMI", "fade 0→15, drž do T+180"), ("BOC", "fade 0→60, drž do T+120"), ("ECB_TK", "trend 0→15, drž do T+120"),
         ("SNB", "pred: proti −60→0, drž do T+120")]
W = 7 * 86400000
print(f"{'typ':8} {'hypotéza':32} | so správou: n PF t | kontrola ±1 týždeň: n PF t | rozdiel")
for typ, h in CANDS:
    g = X[(X.typ == typ) & ~X.usd]
    real = g[h].dropna()
    ctl = []
    for ms in g.ms:
        for sh in (-W, W, -2 * W, 2 * W):
            m2 = ms + sh
            if np.min(np.abs(allnews - m2)) < 30 * 60000: continue
            ctl.append(trade(m2, *HYP[h]))
    ctl = pd.Series(ctl).dropna()
    def st(x): 
        g_, l_ = x[x > 0].sum(), -x[x < 0].sum()
        return len(x), (g_ / l_ if l_ else 99), x.mean() / (x.std() / np.sqrt(len(x)))
    a, b = st(real), st(ctl)
    diff_t = (real.mean() - ctl.mean()) / np.sqrt(real.var() / len(real) + ctl.var() / len(ctl))
    print(f"{typ:8} {h:32} | n {a[0]:3} PF {a[1]:4.2f} t {a[2]:+.1f} | n {b[0]:3} PF {b[1]:4.2f} t {b[2]:+.1f} | t rozdielu {diff_t:+.1f}")
