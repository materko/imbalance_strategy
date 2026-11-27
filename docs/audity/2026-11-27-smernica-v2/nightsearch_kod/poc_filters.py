"""Krok 1 pre POC stratégiu: filtre na prvý prieraz POC predošlého dňa (15m zavretie, výstup 16:00).
Ladenie len na rokoch 2019–2024; 2025–2026 je odložený (nepoužíva sa tu).
Pre každý obchod sa zapíšu vlastnosti dňa a filter sa hodnotí na všetkých 7 akciách: PF spolu a na koľkých akciách je PF > 1.
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
from poc_study import SYMS, load, poc, trade, FEE
from tradebot.core.candles import resample_ohlcv

TF = 15
IS_END = "2100-01-01"   # rýchly test: celé obdobie (bez odloženého roka)
rows = []
for sym in SYMS:
    m = load(sym)
    days = list(m.groupby("day"))
    dc = pd.Series({d: b["close"].iloc[-1] for d, b in days})
    ema50 = dc.ewm(span=50, adjust=False).mean()
    for (d0, b0), (d1, b1) in zip(days[:-1], days[1:]):
        if str(d1) >= IS_END or len(b0) < 300 or len(b1) < 300:
            continue
        P = poc(b0)
        f = resample_ohlcv(b1[["date", "open", "high", "low", "close", "volume"]], TF).reset_index(drop=True)
        f0 = resample_ohlcv(b0[["date", "open", "high", "low", "close", "volume"]], TF)
        c, o, v = f["close"].values, f["open"].values, f["volume"].values
        side0 = np.sign(o[0] - P) or 1
        for i in range(len(c) - 1):
            s = np.sign(c[i] - P)
            if s and s != side0:
                trend = 1 if dc[d0] > ema50[d0] else -1
                rows.append({"sym": sym, "day": d1, "side": int(s), "ret": trade(o[i + 1], c[-1], s),
                             "minute": (i + 1) * TF, "gap": abs(o[0] / P - 1) * 100,
                             "vol": v[i] / max(np.median(f0["volume"].values), 1), "trend": trend})
                break
t = pd.DataFrame(rows)
t.to_csv("/Users/martin/IBS/.nightsearch/poc_trades_is.csv", index=False)
q1, q2 = t["gap"].quantile([1 / 3, 2 / 3])


def rep(name, x):
    if len(x) < 30:
        return f"{name:44s} {len(x):5d}  (málo)"
    pf = lambda r: r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else np.inf
    per = x.groupby("sym")["ret"].apply(pf)
    return (f"{name:44s} {len(x):5d}  ziskových {100*(x.ret>0).mean():5.1f} %  priemer {100*x.ret.mean():+6.3f} %  "
            f"PF {pf(x.ret):4.2f}  akcií s PF>1: {(per > 1).sum()}/7  (najhoršia {per.min():.2f}, najlepšia {per.max():.2f})")


F = {
    "všetky (bez filtra)": t,
    "len long": t[t.side == 1],
    "len short": t[t.side == -1],
    "s trendom (EMA50 denná)": t[t.side == t.trend],
    "proti trendu": t[t.side != t.trend],
    "s trendom, len long": t[(t.side == 1) & (t.trend == 1)],
    f"prieraz v prvej hodine (≤ 60 min)": t[t.minute <= 60],
    "prieraz 60–180 min": t[(t.minute > 60) & (t.minute <= 180)],
    "prieraz po 180 min": t[t.minute > 180],
    f"malý odstup otvorenia od POC (< {q1:.2f} %)": t[t.gap < q1],
    f"stredný odstup ({q1:.2f}–{q2:.2f} %)": t[(t.gap >= q1) & (t.gap < q2)],
    f"veľký odstup (> {q2:.2f} %)": t[t.gap >= q2],
    "objem prierazu nadpriemerný (> 1,5× medián)": t[t.vol > 1.5],
    "objem prierazu podpriemerný": t[t.vol <= 1.5],
    "s trendom + prvá hodina": t[(t.side == t.trend) & (t.minute <= 60)],
    "s trendom + veľký odstup": t[(t.side == t.trend) & (t.gap >= q2)],
    "s trendom + nadpriemerný objem": t[(t.side == t.trend) & (t.vol > 1.5)],
}
print(f"POC prvý prieraz, {TF}m, akcie Mag7, 2019–2026 (celé obdobie), náklady 0,01 %/strana\n")
for k, x in F.items():
    print(rep(k, x))
