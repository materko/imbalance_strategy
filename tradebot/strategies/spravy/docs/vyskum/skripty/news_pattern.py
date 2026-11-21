"""MGC po červených správach USA — opakujúce sa vzorce (1m, čas New York, 2021–2026)."""
import json, sys
from datetime import date, datetime, timedelta
import numpy as np, pandas as pd
sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
from news_study import load, daily_atr, close_at, price_at

CAL = json.load(open("/Users/martin/document/IBS/tradebot/strategies/spravy/calendar.json"))["events"]
PRI = ["FOMC", "CPI", "NFP", "PCE", "GDP", "PPI", "RETAIL", "ISM_M", "ISM_S", "JOLTS", "FOMC_MIN", "CLAIMS"]
df = load("mgc_databento"); atr = daily_atr(df)
M = timedelta(minutes=1)
taken = {}
for n in PRI:
    hh, mm = map(int, CAL[n]["time_et"].split(":"))
    for d in CAL[n]["dates"]:
        t = datetime.combine(date.fromisoformat(d), datetime.min.time()) + timedelta(hours=hh, minutes=mm)
        taken.setdefault(t, n)
rows = []
for t, n in taken.items():
    a = atr.get(pd.Timestamp(t.date()))
    p0 = price_at(df, t, "o"); pre = close_at(df, t - 60 * M)
    cap = t.replace(hour=16, minute=59)          # denná prestávka CME 17:00 NY
    c = {k: close_at(df, min(t + k * M, cap)) for k in (5, 15, 25, 30, 60, 90, 120, 240)}
    if a is None or a != a or p0 is None or pre is None or None in c.values():
        continue
    w = df.loc[t: min(t + 239 * M, cap)]
    if len(w) < 150:
        continue
    hi, lo = w.h.values, w.l.values
    s5 = np.sign(c[5] - p0) or 1
    # extrém v smere prvých 5 min — kedy (min po správe)
    ext_t = int(np.argmax(hi) if s5 > 0 else np.argmin(lo))
    # návrat k cene pred správou po prvom výstrele (od T+5 do T+240)
    after = w.iloc[5:]
    back = bool((after.l <= p0).any() if s5 > 0 else (after.h >= p0).any())
    nxt = df.loc[t.replace(hour=0, minute=0) + timedelta(days=1): t.replace(hour=0, minute=0) + timedelta(days=2)]
    nd = (nxt.c.iloc[-1] - nxt.o.iloc[0]) if len(nxt) > 300 else np.nan
    rows.append(dict(t=t, n=n, y=t.year, atr=a, pre=(p0 - pre) / a, r5=(c[5] - p0) / a, r15=(c[15] - p0) / a,
                     r60=(c[60] - p0) / a, r240=(c[240] - p0) / a, f5_60=(c[60] - c[5]) / a, f15_60=(c[60] - c[15]) / a,
                     f60_240=(c[240] - c[60]) / a, f25=(c[25] - p0) / a, f30_90=(c[90] - c[30]) / a,
                     ext_t=ext_t, back=back, rng60=(w.h.iloc[:60].max() - w.l.iloc[:60].min()) / a,
                     nd=nd / a if nd == nd else np.nan, ndir=np.sign(c[240] - p0)))
R = pd.DataFrame(rows)
R.to_csv("/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/news_pattern.csv", index=False)

def same(a, b):  # % prípadov, kde b ide v smere a
    m = (a != 0) & (b != 0)
    return 100 * (np.sign(a[m]) == np.sign(b[m])).mean()

def yrs(g, a, b, want):  # rokov, kde platí smer (pokrač. >50 alebo otočka <50)
    k = 0; tot = 0
    for _, x in g.groupby("y"):
        if len(x) < 4: continue
        tot += 1; v = same(x[a], x[b]); k += (v > 50) if want else (v < 50)
    return f"{k}/{tot}"

import math
def z(a, b):
    m = (a != 0) & (b != 0); k = m.sum(); return (same(a, b) / 100 - 0.5) / math.sqrt(0.25 / k)
print(f"{'typ':9}{'n':>4} {'pred→5m':>8} {'5→60':>6} {'15→60':>6} {'60→240':>7} {'rng60':>6} {'ext min':>8} {'návrat%':>8} {'deň po':>7}")
for n in PRI + ["SPOLU"]:
    g = R if n == "SPOLU" else R[R.n == n]
    if len(g) < 15: continue
    s5 = np.sign(g.r5)
    print(f"{n:9}{len(g):4} {same(g.pre, g.r5):7.0f}% {same(g.r5, g.f5_60):5.0f}% {same(g.r15, g.f15_60):5.0f}% "
          f"{same(g.r60, g.f60_240):6.0f}% {g.rng60.median():6.2f} {g.ext_t.median():8.0f} {100*g.back.mean():7.0f}% "
          f"{same(g.r240, g.nd.fillna(0)):6.0f}%   z15→60 {z(g.r15, g.f15_60):+.1f}  rokov pokr/otočka {yrs(g,'r15','f15_60',True)} / {yrs(g,'r15','f15_60',False)}")
print("\n(pred→5m = % pohyb 60 min pred správou rovnakým smerom ako prvých 5 min; 5→60 = % pokračovanie po prvých 5 min do T+60;"
      "\n ext min = medián minúty, kedy je extrém v smere prvých 5 min v okne 4 h; návrat% = cena sa po T+5 vrátila na cenu pred správou)")

f = R[R.n == "FOMC"]
print(f"\nFOMC 14:00, tlačovka 14:30: smer 14:00→14:25 vs 14:30→15:30 rovnaký v {same(f.f25, f.f30_90):.0f}% (n={len(f)})")
print("FOMC po rokoch (pokračovanie 15→60 %, 60→240 %):")
for y, x in f.groupby("y"):
    print(f"  {y}: n={len(x)}  15→60 {same(x.r15, x.f15_60):.0f}%  60→240 {same(x.r60, x.f60_240):.0f}%  14:00-25 vs 14:30-15:30 {same(x.f25, x.f30_90):.0f}%")

print("\nVeľkosť prvého výstrelu (|T→T+15| v ATR) a čo nasleduje do T+60 (všetky 8:30 správy CPI/NFP/PPI/PCE/RETAIL/GDP):")
e = R[R.n.isin(["CPI", "NFP", "PPI", "PCE", "RETAIL", "GDP"])].copy()
e["b"] = pd.cut(e.r15.abs(), [0, 0.1, 0.2, 0.35, 10], labels=["<0,1", "0,1–0,2", "0,2–0,35", ">0,35"])
for b, x in e.groupby("b", observed=True):
    cont = same(x.r15, x.f15_60)
    mv = (np.sign(x.r15) * x.f15_60).mean()
    print(f"  {b:>9}: n={len(x):3}  pokračuje {cont:3.0f}%  priem. pohyb v smere {mv:+.3f} ATR")

print("\nDeň v týždni a správy 8:30 — pokračovanie 15→60 %:")
for d, x in e.groupby(e.t.dt.dayofweek):
    print(f"  {'Po Ut St Št Pi'.split()[d]}: n={len(x)} {same(x.r15, x.f15_60):.0f}%")

print("\nTrend pred správou (pohyb 60 min pred) proti prvému výstrelu — čo potom T+15→T+240:")
for n in ["FOMC", "CPI", "NFP", "PCE", "PPI"]:
    x = R[R.n == n]; opp = np.sign(x.pre) != np.sign(x.r15)
    for lab, m in (("proti", opp), ("v smere", ~opp)):
        z = x[m]
        if len(z) >= 8:
            print(f"  {n:5} výstrel {lab:8} trendu pred: n={len(z):3} pokračovanie 15→240 {same(z.r15, z.r240 - z.r15):.0f}%")
