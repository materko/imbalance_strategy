"""Klasický test: denný graf, kúp keď cena zavrie nad EMA N (predtým pod), drž kým nezavrie pod EMA N.
Vstup aj výstup na otvorení ďalšieho dňa. EMA 10 / 20 / 50 / 200, akcie Mag7 2019–2026. Porovnanie s kúp a drž."""
import glob, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/martin/IBS")
from tradebot.core.candles import resample_ohlcv
SYMS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
def daily(sym):
    fs = sorted(glob.glob(f"/Users/martin/IBS/data_archive/tester/ibkr/futures/{sym}_USD-1m.*.feather"))
    m = pd.concat([pd.read_feather(f) for f in fs]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    d = resample_ohlcv(m, 1440).reset_index(drop=True)
    return d[d["volume"] > 0].reset_index(drop=True)
START = 200                                    # od 200. dňa (aby mala aj EMA 200 rozbeh), rovnaké obdobie pre všetky
def run(d, n):
    e = d["close"].ewm(span=n, adjust=False).mean().values; c, o = d["close"].values, d["open"].values
    eq, cur, pos, tr, days_in = [1.0], 1.0, None, [], 0
    for i in range(START, len(d) - 1):
        if pos is None and c[i] > e[i] and c[i - 1] <= e[i - 1]:
            pos = o[i + 1]; ent = i + 1
        elif pos is not None and c[i] < e[i]:
            r = o[i + 1] / pos - 1; tr.append(r); cur *= 1 + r; days_in += i + 1 - ent; pos = None
        eq.append(cur * (c[i] / pos if pos else 1.0))
    if pos is not None:
        r = c[-1] / pos - 1; tr.append(r); cur *= 1 + r; days_in += len(d) - 1 - ent
    eq = np.array(eq); dd = (1 - eq / np.maximum.accumulate(eq)).max()
    tr = np.array(tr)
    return len(tr), 100 * (tr > 0).mean(), 100 * tr.mean(), 100 * (cur - 1), 100 * dd, 100 * days_in / (len(d) - START)
T = {n: [] for n in (10, 20, 50, 200)}; BH = []
for s in SYMS:
    d = daily(s)
    c = d["close"].values[START:]; bh = 100 * (c[-1] / d["open"].values[START] - 1); bdd = 100 * (1 - c / np.maximum.accumulate(c)).max()
    BH.append((bh, bdd))
    print(f"== {s} (od {d['date'].iloc[START]:%Y-%m-%d})   kúp a drž: {bh:+.0f} %, max prepad {bdd:.0f} %")
    for n in T:
        r = run(d, n); T[n].append(r)
        print(f"   EMA {n:3d}: obchodov {r[0]:3d}, ziskových {r[1]:4.0f} %, priemer {r[2]:+6.2f} %, spolu {r[3]:+7.0f} %, max prepad {r[4]:4.0f} %, v trhu {r[5]:3.0f} %")
print("\n== PRIEMER 7 akcií")
print(f"   kúp a drž : spolu {np.mean([b[0] for b in BH]):+7.0f} % (medián {np.median([b[0] for b in BH]):+.0f} %), max prepad {np.mean([b[1] for b in BH]):4.0f} %")
for n, rs in T.items():
    a = np.array(rs)
    print(f"   EMA {n:3d}: obchodov {a[:,0].mean():4.0f}/akcia, ziskových {a[:,1].mean():3.0f} %, priemer {a[:,2].mean():+6.2f} %, spolu {a[:,3].mean():+7.0f} % (medián {np.median(a[:,3]):+.0f} %), max prepad {a[:,4].mean():4.0f} %, v trhu {a[:,5].mean():3.0f} %")
