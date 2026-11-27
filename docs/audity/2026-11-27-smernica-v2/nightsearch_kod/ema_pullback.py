"""Návrat k EMA 50 v trende nad EMA 200 (denný graf, Mag7 10/2019 – 10/2026, vstup/výstup na otvorení ďalšieho dňa).
  P1  cena nad EMA 200, low sa dotkne EMA 50 a zavretie ostane nad EMA 50 → kúp; predaj pri zavretí pod EMA 200
  P2  ten istý vstup; predaj pri zavretí pod EMA 50
  B   obyčajná EMA 200 (kúp pri prieraze nahor, predaj pri zavretí pod) — porovnanie"""
import glob, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/martin/IBS")
from tradebot.core.candles import resample_ohlcv
SYMS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
START = 200
def daily(sym):
    fs = sorted(glob.glob(f"/Users/martin/IBS/data_archive/tester/ibkr/futures/{sym}_USD-1m.*.feather"))
    m = pd.concat([pd.read_feather(f) for f in fs]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    d = resample_ohlcv(m, 1440).reset_index(drop=True)
    return d[d["volume"] > 0].reset_index(drop=True)
def sim(d, entry, exit_):
    c, o = d["close"].values, d["open"].values
    cur, pos, tr, eq, din = 1.0, None, [], [1.0], 0
    for i in range(START, len(d) - 1):
        if pos is None and entry[i]:
            pos, ent = o[i + 1], i + 1
        elif pos is not None and exit_[i]:
            r = o[i + 1] / pos - 1; tr.append(r); cur *= 1 + r; din += i + 1 - ent; pos = None
        eq.append(cur * (c[i] / pos if pos else 1))
    if pos is not None:
        r = c[-1] / pos - 1; tr.append(r); cur *= 1 + r; din += len(d) - 1 - ent
    eq = np.array(eq); tr = np.array(tr)
    return len(tr), 100 * (tr > 0).mean() if len(tr) else 0, 100 * tr.mean() if len(tr) else 0, 100 * (cur - 1), \
        100 * (1 - eq / np.maximum.accumulate(eq)).max(), 100 * din / (len(d) - START)
R = {"P1 návrat k EMA50, predaj pod EMA200": [], "P2 návrat k EMA50, predaj pod EMA50": [], "B  EMA200 prieraz/predaj": [], "kúp a drž": []}
for s in SYMS:
    d = daily(s); c, l = d["close"], d["low"]
    e50, e200 = c.ewm(span=50, adjust=False).mean(), c.ewm(span=200, adjust=False).mean()
    pull = ((c > e200) & (l <= e50) & (c > e50)).values
    up200 = ((c > e200) & (c.shift() <= e200.shift())).values
    rs = {"P1 návrat k EMA50, predaj pod EMA200": sim(d, pull, (c < e200).values),
          "P2 návrat k EMA50, predaj pod EMA50": sim(d, pull, (c < e50).values),
          "B  EMA200 prieraz/predaj": sim(d, up200, (c < e200).values)}
    cc = c.values[START:]
    rs["kúp a drž"] = (1, 0, 0, 100 * (cc[-1] / d["open"].values[START] - 1), 100 * (1 - cc / np.maximum.accumulate(cc)).max(), 100)
    print(f"== {s}   dnes: nad EMA50 {100*(c.iloc[-1]/e50.iloc[-1]-1):+.1f} %, nad EMA200 {100*(c.iloc[-1]/e200.iloc[-1]-1):+.1f} %")
    for k, r in rs.items():
        R[k].append(r)
        print(f"   {k:38s} obch {r[0]:3d}  ziskových {r[1]:3.0f} %  priemer {r[2]:+6.2f} %  spolu {r[3]:+7.0f} %  max prepad {r[4]:3.0f} %  v trhu {r[5]:3.0f} %")
print("\n== PRIEMER 7 akcií")
for k, rs in R.items():
    a = np.array(rs)
    print(f"   {k:38s} obch {a[:,0].mean():4.0f}  ziskových {a[:,1].mean():3.0f} %  priemer {a[:,2].mean():+6.2f} %  spolu {a[:,3].mean():+7.0f} % (medián {np.median(a[:,3]):+.0f} %)  max prepad {a[:,4].mean():3.0f} %  v trhu {a[:,5].mean():3.0f} %")
