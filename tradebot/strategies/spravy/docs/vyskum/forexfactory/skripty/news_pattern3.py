"""MGC po správach — 3. kolo: vzorce ako obchod (1 kontrakt = 10 oz, poplatok 1,755e-5 na stranu + 1 tick sklz)."""
import json, sys
from datetime import date, datetime, timedelta
import numpy as np, pandas as pd
sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
from news_study import load, daily_atr, close_at, price_at

CAL = json.load(open("/Users/martin/document/IBS/tradebot/strategies/spravy/calendar.json"))["events"]
PRI = ["FOMC", "CPI", "NFP", "PCE", "GDP", "PPI", "RETAIL", "ISM_M", "ISM_S", "JOLTS", "FOMC_MIN", "CLAIMS"]
df = load("mgc_databento"); atr = daily_atr(df)
dc = df.c.resample("1D").last().dropna(); ma20 = dc.rolling(20).mean().shift(1)
taken = {}
for n in PRI:
    hh, mm = map(int, CAL[n]["time_et"].split(":"))
    for d in CAL[n]["dates"]:
        t = datetime.combine(date.fromisoformat(d), datetime.min.time()) + timedelta(hours=hh, minutes=mm)
        taken.setdefault(t, n)
M = timedelta(minutes=1)

def px(t, k):
    """cena v čase t+k min (k=0 → open baru správy); po 16:59 NY sa skráti."""
    cap = t.replace(hour=16, minute=59)
    return price_at(df, t, "o") if k == 0 else close_at(df, min(t + k * M, cap))

def trade(types, sig, ent, ext, extra=None):
    """sig(t) → +1/−1/0 smer; vstup cena v T+ent, výstup v T+ext."""
    out = []
    for t, n in taken.items():
        if n not in types: continue
        s = sig(t)
        if not s: continue
        if extra and not extra(t, s): continue
        a, b = px(t, ent), px(t, ext)
        if a is None or b is None: continue
        pnl = 10 * (s * (b - a) - 1.755e-5 * (a + b) - 0.2)      # $; 0,2 = 2 ticky sklzu spolu
        out.append((t.year, t, pnl))
    return pd.DataFrame(out, columns=["y", "t", "p"])

def rep(name, r):
    if len(r) < 10: print(f"{name:60} n={len(r)} málo"); return
    g, l = r.p[r.p > 0].sum(), -r.p[r.p < 0].sum()
    yp = r.groupby("y").p.sum()
    oos = r[r.t >= datetime(2025, 9, 4)]
    go, lo = oos.p[oos.p > 0].sum(), -oos.p[oos.p < 0].sum()
    t = r.p.mean() / (r.p.std() / np.sqrt(len(r)))
    print(f"{name:60} n={len(r):3} WR {100*(r.p>0).mean():3.0f}% PF {g/l if l else 99:4.2f} spolu {r.p.sum():+7.0f}$ t {t:+.1f} "
          f"rokov+ {(yp>0).sum()}/{len(yp)} | posl. rok n={len(oos)} PF {go/lo if lo else 99:4.2f} {oos.p.sum():+6.0f}$")

def drift(k0, k1):
    def f(t):
        a, b = px(t, k0), px(t, k1)
        return 0 if a is None or b is None or a == b else (1 if b > a else -1)
    return f

anti = lambda f: (lambda t: -f(t))
pre60 = lambda t: (lambda a, b: 0 if a is None or b is None or a == b else (1 if b > a else -1))(close_at(df, t - 60 * M), px(t, 0))

print("— FOMC —")
rep("H1 proti driftu 13:00→14:00, vstup 14:00, výstup 14:25", trade({"FOMC"}, lambda t: -pre60(t), 0, 25))
rep("H1b proti driftu 13:00→14:00, vstup 14:00, výstup 16:55", trade({"FOMC"}, lambda t: -pre60(t), 0, 175))
rep("H2 tlačovka: smer 14:00→14:25, vstup 14:30, výstup 15:30", trade({"FOMC"}, drift(0, 25), 30, 90))
rep("H2b smer 14:00→14:25, vstup 14:30, výstup 16:55", trade({"FOMC"}, drift(0, 25), 30, 175))
rep("H3 smer 14:15→15:00 (noha), vstup 15:00, výstup 16:55 [SPRÁVY]", trade({"FOMC"}, drift(15, 60), 60, 175))
rep("H3b smer 14:00→15:00, vstup 15:00, výstup 16:55", trade({"FOMC"}, drift(0, 60), 60, 175))
rep("H3c smer 14:00→14:45, vstup 14:45, výstup 16:55", trade({"FOMC"}, drift(0, 45), 45, 175))
rep("H4 proti výstrelu 14:00→14:15, vstup 14:15, výstup 14:30 (pred tlačovkou)", trade({"FOMC"}, anti(drift(0, 15)), 15, 30))

print("— 8:30 a 10:00 —")
for n in ["CPI", "NFP", "PPI", "PCE", "RETAIL", "GDP", "JOLTS", "ISM_M", "ISM_S", "CLAIMS"]:
    rep(f"{n}: v smere 0→15, vstup T+15, výstup T+180", trade({n}, drift(0, 15), 15, 180))
    rep(f"{n}: proti 0→15, vstup T+15, výstup T+60", trade({n}, anti(drift(0, 15)), 15, 60))
    rep(f"{n}: proti 0→60, vstup T+60, výstup T+120", trade({n}, anti(drift(0, 60)), 60, 120))

print("— s režimom MA20 —")
intrend = lambda t, s: (lambda m, p: m == m and p is not None and (s > 0) == (p > m))(ma20.get(pd.Timestamp(t.date()), np.nan), px(t, 0))
against = lambda t, s: not intrend(t, s)
rep("ISM_M v smere 0→15 a v smere MA20, T+15→T+180", trade({"ISM_M"}, drift(0, 15), 15, 180, intrend))
rep("JOLTS v smere 0→15 a v smere MA20, T+15→T+180", trade({"JOLTS"}, drift(0, 15), 15, 180, intrend))
rep("CLAIMS proti 0→15, ak výstrel v smere MA20, T+15→T+180", trade({"CLAIMS"}, anti(drift(0, 15)), 15, 180, lambda t, s: not intrend(t, -s)))
rep("PPI proti 0→15 (všetky), T+15→T+180", trade({"PPI"}, anti(drift(0, 15)), 15, 180))
rep("PPI+RETAIL+PCE proti 0→15, T+15→T+180", trade({"PPI", "RETAIL", "PCE"}, anti(drift(0, 15)), 15, 180))
