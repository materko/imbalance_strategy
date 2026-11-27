"""Štúdia: POC volume profilu predošlého dňa na akciách Mag7 (IBKR 1m, len hlavná seansa 9:30–16:00 NY).

Volume profile dňa: objem každej 1m sviečky sa rozdelí rovnomerne medzi koše ceny od low po high (kôš 0,05 % ceny);
POC = kôš s najväčším objemom. Nasledujúci deň na 5m sviečkach (zavretie):
  V1  prvé prekríženie POC zavretím (z ktorejkoľvek strany) → obchod v smere prekríženia, drž do 16:00
  V2  pri otvorení: cena nad POC → long, pod → short, drž do 16:00 (bez čakania na prekríženie)
  V3  vždy v smere poslednej strany POC: každé prekríženie zavretím obráti pozíciu (stop and reverse), do 16:00
Náklady: 0,01 % na stranu (provízia IBKR + sklz ~1 cent). Porovnanie: náhodný smer (rovnaké vstupy, hod mincou).
"""
import glob, sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/martin/IBS")
from tradebot.core.candles import resample_ohlcv

SYMS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
FEE = 0.0001          # na stranu
BIN = 0.0005          # kôš profilu = 0,05 % ceny
rng = np.random.default_rng(11)
TF = int(sys.argv[1]) if len(sys.argv) > 1 else 5      # TF sviečok pre prieraz (min)


def load(sym):
    fs = sorted(glob.glob(f"/Users/martin/IBS/data_archive/tester/ibkr/futures/{sym}_USD-1m.*.feather"))
    m = pd.concat([pd.read_feather(f) for f in fs]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    m["day"] = m["date"].dt.tz_convert("America/New_York").dt.date
    return m


def poc(day_bars):
    lo, hi = day_bars["low"].min(), day_bars["high"].max()
    step = max(0.01, round(day_bars["close"].iloc[-1] * BIN, 2))
    edges = np.arange(lo - step, hi + step * 2, step)
    vol = np.zeros(len(edges))
    for l, h, v in zip(day_bars["low"].values, day_bars["high"].values, day_bars["volume"].values):
        a, b = np.searchsorted(edges, l, "right") - 1, np.searchsorted(edges, h, "right") - 1
        vol[a:b + 1] += v / (b - a + 1)
    k = int(vol.argmax())
    return edges[k] + step / 2


def trade(p_in, p_out, side):
    return side * (p_out / p_in - 1) - 2 * FEE


res = {v: [] for v in ("V1", "V2", "V3", "V1 náhodný smer", "kúp na otvorení, predaj 16:00")}
per = {}
for sym in SYMS:
    m = load(sym)
    days = list(m.groupby("day"))
    out = {k: [] for k in res}
    for (d0, b0), (d1, b1) in zip(days[:-1], days[1:]):
        if len(b0) < 300 or len(b1) < 300:          # skrátené dni (sviatky) vynechať
            continue
        P = poc(b0)
        f = resample_ohlcv(b1[["date", "open", "high", "low", "close", "volume"]], TF).reset_index(drop=True)
        c = f["close"].values; o = f["open"].values
        last = c[-1]
        out["kúp na otvorení, predaj 16:00"].append(trade(o[0], last, 1))
        # V2: strana pri otvorení
        out["V2"].append(trade(o[0], last, 1 if o[0] > P else -1))
        # V1: prvé prekríženie zavretím (vstup na otvorení ďalšej 5m sviečky)
        side0 = np.sign(o[0] - P) or 1
        cross = None
        for i in range(len(c) - 1):
            s = np.sign(c[i] - P)
            if s and s != side0:
                cross = (i, int(s)); break
        if cross:
            i, s = cross
            out["V1"].append(trade(o[i + 1], last, s))
            out["V1 náhodný smer"].append(trade(o[i + 1], last, rng.choice([-1, 1])))
        # V3: stop and reverse na každom prekrížení, začiatok podľa strany pri otvorení
        side, entry, r = (1 if o[0] > P else -1), o[0], 0.0
        for i in range(len(c) - 1):
            s = np.sign(c[i] - P)
            if s and s != side:
                r += trade(entry, o[i + 1], side); side, entry = int(s), o[i + 1]
        r += trade(entry, last, side)
        out["V3"].append(r)
    per[sym] = out
    for k in res:
        res[k] += out[k]


def line(name, v):
    v = np.array(v)
    if not len(v):
        return f"{name:32s}   —"
    eq = np.cumprod(1 + v); dd = (1 - eq / np.maximum.accumulate(eq)).max()
    return (f"{name:32s} {len(v):5d}  ziskových {100*(v>0).mean():5.1f} %  priemer {100*v.mean():+6.3f} %  "
            f"PF {(v[v>0].sum()/-v[v<0].sum() if (v<0).any() else float('inf')):4.2f}  spolu {100*(eq[-1]-1):+7.0f} %  max DD {100*dd:5.1f} %")


print(f"POC predošlého dňa, akcie Mag7 2019–2026, {TF}m zavretia, výstup 16:00, náklady 0,01 % na stranu\n")
for sym in SYMS:
    print(f"== {sym}")
    for k in ("V1", "V2", "V3"):
        print("  " + line(k, per[sym][k]))
print("\n== SPOLU 7 akcií")
for k, v in res.items():
    print("  " + line(k, v))
