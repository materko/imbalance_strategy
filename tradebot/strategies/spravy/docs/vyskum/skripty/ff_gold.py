"""MGC po červených správach iných mien (FF 2021 – 3/2025): reaguje zlato a ako? Čas UTC, 1m MGC Databento."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/martin/document/IBS")
from tester import engines
from tradebot.core.types import INSTRUMENTS
EV = pd.read_csv("/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/ffwork/ff_types.csv")
EV["ms"] = pd.to_datetime(EV.t, utc=True, format="ISO8601").astype("datetime64[ms, UTC]").astype("int64")
df = pd.read_feather(engines.one_minute_file(INSTRUMENTS["mgc_databento"]))
ix = pd.to_datetime(df["date"], utc=True).astype("datetime64[ms, UTC]").astype("int64").values
O, H, L, C = (df[c].values for c in ("open", "high", "low", "close"))
R = H - L
MIN = 60000
d = pd.Series(C, index=pd.to_datetime(ix, unit="ms", utc=True)).resample("1D").agg(["max", "min", "last"]).dropna()
dh = pd.DataFrame({"h": pd.Series(H, index=pd.to_datetime(ix, unit="ms", utc=True)).resample("1D").max(),
                   "l": pd.Series(L, index=pd.to_datetime(ix, unit="ms", utc=True)).resample("1D").min(), "c": d["last"]}).dropna()
tr = pd.concat([dh.h - dh.l, (dh.h - dh.c.shift()).abs(), (dh.l - dh.c.shift()).abs()], axis=1).max(axis=1)
ATR = tr.rolling(14).mean().shift(1)

def px(ms, k):
    """k=0: open baru v T; inak close baru končiaceho v T+k (tolerancia 3 min)."""
    t = ms + k * MIN
    if k == 0:
        i = np.searchsorted(ix, t)
        return O[i] if i < len(ix) and ix[i] - t <= 2 * MIN else None
    i = np.searchsorted(ix, t) - 1
    return C[i] if i >= 0 and t - ix[i] <= 3 * MIN else None

def spike(ms):
    i0, i1 = np.searchsorted(ix, ms - 40 * MIN), np.searchsorted(ix, ms - 5 * MIN)
    j0, j1 = np.searchsorted(ix, ms), np.searchsorted(ix, ms + 3 * MIN)
    if i1 - i0 < 20 or j1 <= j0: return np.nan
    return R[j0:j1].max() / (np.median(R[i0:i1]) or 1e-9)

HYP = {  # meno: (smer z nohy a→b, znamienko, vstup, výstup)
    "trend 0→15, drž do T+120": (0, 15, +1, 15, 120),
    "fade 0→15, drž do T+60": (0, 15, -1, 15, 60),
    "fade 0→15, drž do T+180": (0, 15, -1, 15, 180),
    "fade 0→60, drž do T+120": (0, 60, -1, 60, 120),
    "trend 15→60, drž do T+240": (15, 60, +1, 60, 240),
    "pred: proti −60→0, drž do T+25": (-60, 0, -1, 0, 25),
    "pred: proti −60→0, drž do T+120": (-60, 0, -1, 0, 120),
}
rows = []
for r in EV.itertuples():
    a = ATR.get(pd.Timestamp(r.ms, unit="ms", tz="UTC").normalize())
    if a is None or a != a: continue
    sp = spike(r.ms)
    rec = dict(typ=r.typ, ms=r.ms, y=pd.Timestamp(r.ms, unit="ms").year, spike=sp, atr=a)
    for name, (fa, fb, sg, en, ex) in HYP.items():
        p0, p1, pe, px_ = px(r.ms, fa), px(r.ms, fb), px(r.ms, en), px(r.ms, ex)
        if None in (p0, p1, pe, px_) or p1 == p0:
            rec[name] = np.nan; continue
        s = sg * (1 if p1 > p0 else -1)
        rec[name] = 10 * (s * (px_ - pe) - 1.755e-5 * (pe + px_) - 0.2)    # $ na 1 MGC, poplatok + 2 ticky
    rows.append(rec)
X = pd.DataFrame(rows)
X.to_csv("/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/ffwork/ff_gold_trades.csv", index=False)

def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum(); return g / l if l else 99
print(f"{'typ':8}{'n':>4} {'výbuch×':>8} | najlepšia hypotéza (z 7): n WR PF t rokov+ | 2. najlepšia")
res = []
for typ, g in X.groupby("typ"):
    best = []
    for name in HYP:
        x = g[name].dropna()
        if len(x) < 12: continue
        t = x.mean() / (x.std() / np.sqrt(len(x))) if x.std() > 0 else 0
        yp = g.dropna(subset=[name]).groupby("y")[name].sum()
        best.append((t, name, len(x), (x > 0).mean(), pf(x), int((yp > 0).sum()), len(yp), x.sum()))
        res.append((typ, name, len(x), (x > 0).mean(), pf(x), t, int((yp > 0).sum()), len(yp), x.sum(), g.spike.median()))
    best.sort(reverse=True)
    if best:
        b = best[0]; c = best[1] if len(best) > 1 else None
        print(f"{typ:8}{len(g):4} {g.spike.median():8.1f} | {b[1]:32} n{b[2]:3} WR {100*b[3]:3.0f}% PF {b[4]:4.2f} t {b[0]:+.1f} r+ {b[5]}/{b[6]} {b[7]:+6.0f}$"
              + (f" | {c[1][:24]} t {c[0]:+.1f}" if c else ""))
pd.DataFrame(res, columns=["typ", "hyp", "n", "wr", "pf", "t", "rokov_plus", "rokov", "zisk", "vybuch"]).to_csv(
    "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/ffwork/ff_gold_hyp.csv", index=False)
print(f"\nhypotéz spolu: {len(res)} — pri toľkých dá náhoda t > 2 asi {0.023*len(res):.0f}×")
