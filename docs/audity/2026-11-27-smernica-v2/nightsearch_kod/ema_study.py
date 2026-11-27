"""Štúdia pre vlastný kapitál: EMA 10 / 50 na dennom grafe akcií (Mag7, IBKR 2019–2026).

Signály (denná sviečka, vyhodnotené po zavretí, nákup market na otvorení ďalšieho dňa):
  A  zavretie nad EMA 10 (predtým pod)          → long;  zrkadlo: zavretie pod EMA 10 → short / predaj
  B  EMA 10 prekríži EMA 50 nahor                → long;  zrkadlo: nadol → short / predaj
Meria sa: v koľkých % prípadov je cena po 1 / 5 / 10 / 20 dňoch vyššie (pri zrkadle nižšie) než pri vstupe,
priemerný pohyb, a obchod „drž do opačného signálu“. Porovnanie s náhodou: všetky dni (drift akcie).
"""
import glob, sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/martin/IBS")
from tradebot.core.candles import resample_ohlcv

SYMS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]   # GOOG je tá istá firma ako GOOGL
H = [1, 5, 10, 20]


def daily(sym):
    fs = sorted(glob.glob(f"/Users/martin/IBS/data_archive/tester/ibkr/futures/{sym}_USD-1m.*.feather"))
    m = pd.concat([pd.read_feather(f) for f in fs]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    d = resample_ohlcv(m, 1440).reset_index(drop=True)
    d = d[d["volume"] > 0].reset_index(drop=True)
    d["e10"] = d["close"].ewm(span=10, adjust=False).mean()
    d["e50"] = d["close"].ewm(span=50, adjust=False).mean()
    return d


def study(d, sig, sign):
    """sig: bool séria signálov na zavretí dňa t; vstup na otvorení t+1. sign +1 long, -1 short."""
    idx = np.where(sig.values)[0]
    idx = idx[idx >= 50]                       # EMA 50 potrebuje rozbeh
    out = {"n": 0}
    rows = []
    for i in idx:
        if i + 1 >= len(d):
            continue
        entry = d["open"].iloc[i + 1]
        r = {}
        for h in H:
            j = i + h
            if j < len(d):
                r[h] = sign * (d["close"].iloc[j] / entry - 1)
        rows.append(r)
    out["n"] = len(rows)
    for h in H:
        v = np.array([r[h] for r in rows if h in r])
        out[h] = (100 * (v > 0).mean(), 100 * v.mean(), 100 * np.median(v)) if len(v) else (None, None, None)
    return out


def hold(d, up, down):
    """Obchod long od signálu `up` po signál `down` (vstup aj výstup na otvorení ďalšieho dňa)."""
    res, pos = [], None
    for i in range(50, len(d) - 1):
        if pos is None and up.iloc[i]:
            pos = d["open"].iloc[i + 1]
        elif pos is not None and down.iloc[i]:
            res.append(d["open"].iloc[i + 1] / pos - 1); pos = None
    v = np.array(res)
    return (len(v), 100 * (v > 0).mean(), 100 * v.mean(), 100 * (np.prod(1 + v) - 1)) if len(v) else (0, None, None, None)


def fmt(t):
    return "  —  " if t[0] is None else f"{t[0]:5.1f} % ({t[1]:+5.2f} %)"


tot = {}
print("Akcie Mag7, denný graf z 1m IBKR (len hlavná seansa, upravené o splity, bez dividend), vstup na otvorení ďalšieho dňa\n")
for sym in SYMS:
    d = daily(sym)
    c, e10, e50 = d["close"], d["e10"], d["e50"]
    S = {
        "A long  (zavretie nad EMA10)": (((c > e10) & (c.shift() <= e10.shift())), 1),
        "A short (zavretie pod EMA10)": (((c < e10) & (c.shift() >= e10.shift())), -1),
        "B long  (EMA10 nad EMA50)   ": (((e10 > e50) & (e10.shift() <= e50.shift())), 1),
        "B short (EMA10 pod EMA50)   ": (((e10 < e50) & (e10.shift() >= e50.shift())), -1),
        "všetky dni (náhoda, long)   ": (pd.Series(True, index=d.index), 1),
    }
    print(f"== {sym}  {d['date'].iloc[0]:%Y-%m-%d} – {d['date'].iloc[-1]:%Y-%m-%d}, {len(d)} dní")
    print(f"{'signál':30s} {'počet':>5s}   " + "   ".join(f"po {h:>2d} d: % nárast (priem.)" for h in H))
    for name, (sig, sign) in S.items():
        r = study(d, sig, sign)
        tot.setdefault(name, []).append(r)
        print(f"{name:30s} {r['n']:5d}   " + "   ".join(fmt(r[h]).ljust(26) for h in H))
    for lbl, up, dn in (("A drž long od nad EMA10 po pod EMA10", S["A long  (zavretie nad EMA10)"][0], S["A short (zavretie pod EMA10)"][0]),
                        ("B drž long od kríža nahor po kríž nadol", S["B long  (EMA10 nad EMA50)   "][0], S["B short (EMA10 pod EMA50)   "][0])):
        n, wr, avg, comp = hold(d, up, dn)
        tot.setdefault(lbl, []).append((n, wr, avg, comp))
        print(f"  {lbl}: obchodov {n}, ziskových {wr:.0f} %, priemer {avg:+.2f} %, spolu {comp:+.0f} %  (kúp a drž: {100*(d['close'].iloc[-1]/d['open'].iloc[50]-1):+.0f} %)")
    print()

print("== SPOLU (priemer cez 7 akcií, vážený počtom signálov)")
for name in [k for k in tot if not k.startswith(("A drž", "B drž"))]:
    rs = tot[name]; n = sum(r["n"] for r in rs)
    line = []
    for h in H:
        w = [(r["n"], r[h]) for r in rs if r[h][0] is not None]
        p = sum(a * b[0] for a, b in w) / sum(a for a, _ in w); av = sum(a * b[1] for a, b in w) / sum(a for a, _ in w)
        line.append(f"{p:5.1f} % ({av:+5.2f} %)".ljust(26))
    print(f"{name:30s} {n:5d}   " + "   ".join(line))
for lbl in [k for k in tot if k.startswith(("A drž", "B drž"))]:
    rs = tot[lbl]; n = sum(r[0] for r in rs)
    wr = sum(r[0] * r[1] for r in rs) / n; av = sum(r[0] * r[2] for r in rs) / n
    print(f"  {lbl}: obchodov {n}, ziskových {wr:.0f} %, priemer na obchod {av:+.2f} %")
