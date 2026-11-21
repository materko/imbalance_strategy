"""MGC po správach — 2. kolo: dráha ceny, volatilita, spätný pohyb, asymetria, režim, pred správou."""
import json, math, sys
from datetime import date, datetime, timedelta
import numpy as np, pandas as pd
sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
from news_study import load, daily_atr

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
news_days = {t.date() for t in taken}
K = [-60, -30, -15, -5, 0, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180]
ix = df.index; C = df.c.values; O = df.o.values; H = df.h.values; L = df.l.values

def path(t):
    i0 = ix.searchsorted(t)
    if i0 >= len(ix) or ix[i0] - t > timedelta(minutes=2): return None
    out = {}
    for k in K:
        j = ix.searchsorted(t + timedelta(minutes=k)) - 1
        if k == 0: out[k] = O[i0]; continue
        if j < 0 or abs((ix[j] - (t + timedelta(minutes=k))).total_seconds()) > 180: return None
        out[k] = C[j]
    return i0, out

rows = []
for t, n in taken.items():
    a = atr.get(pd.Timestamp(t.date())); m = ma20.get(pd.Timestamp(t.date()))
    p = path(t)
    if p is None or a is None or a != a or m is None or m != m: continue
    i0, pr = p
    p0 = pr[0]; s = np.sign(pr[15] - p0) or 1.0
    rec = dict(t=t, n=n, y=t.year, s=s, up=s > 0, trend_up=p0 > m, shot=abs(pr[15] - p0) / a)
    for k in K: rec[f"k{k}"] = s * (pr[k] - p0) / a          # v smere výstrelu (prvých 15 min)
    # spätný pohyb: od extrému prvých 15 min, ako hlboko sa vráti do T+60 (v % výstrelu)
    seg = slice(i0, i0 + 15); seg2 = slice(i0 + 15, i0 + 60)
    ext = H[seg].max() if s > 0 else L[seg].min()
    deep = (ext - L[seg2].min()) if s > 0 else (H[seg2].max() - ext)
    rec["retr"] = deep / max(abs(ext - p0), 1e-9)
    # pokračuje za extrém prvých 15 min do T+60?
    rec["newext"] = (H[seg2].max() > ext) if s > 0 else (L[seg2].min() < ext)
    rows.append(rec)
R = pd.DataFrame(rows)

def tz(x):
    x = x.dropna(); return x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 3 else float("nan")

print("1) PRIEMERNÁ DRÁHA v smere prvých 15 min (ATR dňa; + = pokračuje, menej ako k15 = vracia sa). t-štat. pohybu 15→60 a 15→180")
hdr = "".join(f"{k:>7}" for k in K)
print(f"{'typ':9}{'n':>4}{hdr}   t15→60 t15→180")
for n in PRI:
    g = R[R.n == n]
    if len(g) < 15: continue
    print(f"{n:9}{len(g):4}" + "".join(f"{g[f'k{k}'].mean():7.3f}" for k in K)
          + f"   {tz(g.k60 - g.k15):+5.1f} {tz(g.k180 - g.k15):+6.1f}")

print("\n2) SPÄTNÝ POHYB po výstrele: medián hĺbky (v % výstrelu 0→15 min) do T+60 a % nového extrému do T+60")
for n in PRI:
    g = R[R.n == n]
    if len(g) < 15: continue
    print(f"  {n:9} medián spätného pohybu {100*g.retr.median():4.0f}%   ≥50 % {100*(g.retr>=0.5).mean():3.0f}%   ≥100 % (celý výstrel späť) {100*(g.retr>=1).mean():3.0f}%   nový extrém {100*g.newext.mean():3.0f}%")

print("\n3) ASYMETRIA: výstrel hore (zlato rastie) vs dole — pohyb 15→60 a 15→180 v smere výstrelu (ATR)")
for n in ["FOMC", "CPI", "NFP", "PCE", "PPI", "JOLTS", "ISM_M", "RETAIL", "GDP"]:
    g = R[R.n == n]
    u, d = g[g.up], g[~g.up]
    print(f"  {n:7} hore n={len(u):2} {((u.k60-u.k15).mean()):+.3f} / {((u.k180-u.k15).mean()):+.3f}   dole n={len(d):2} {((d.k60-d.k15).mean()):+.3f} / {((d.k180-d.k15).mean()):+.3f}")

print("\n4) REŽIM: výstrel v smere 20-denného trendu zlata (cena nad/pod MA20) vs proti — pohyb 15→180 v smere výstrelu")
for n in ["FOMC", "CPI", "NFP", "PCE", "PPI", "JOLTS", "ISM_M", "RETAIL", "GDP", "CLAIMS"]:
    g = R[R.n == n]; w = g.up == g.trend_up
    a_, b_ = g[w], g[~w]
    print(f"  {n:7} v smere trendu n={len(a_):3} {(a_.k180-a_.k15).mean():+.3f} (t {tz(a_.k180-a_.k15):+.1f})   proti n={len(b_):3} {(b_.k180-b_.k15).mean():+.3f} (t {tz(b_.k180-b_.k15):+.1f})")

print("\n5) VEĽKOSŤ VÝSTRELU (|0→15| v ATR) → pohyb 15→60 / 15→180 v smere (všetky okrem CLAIMS)")
e = R[R.n != "CLAIMS"].copy()
e["b"] = pd.qcut(e.shot, 4, labels=["Q1 malý", "Q2", "Q3", "Q4 veľký"])
for b, x in e.groupby("b", observed=True):
    print(f"  {b:9} n={len(x):3} |výstrel| {x.shot.median():.2f}  15→60 {(x.k60-x.k15).mean():+.3f} (t {tz(x.k60-x.k15):+.1f})  15→180 {(x.k180-x.k15).mean():+.3f} (t {tz(x.k180-x.k15):+.1f})")

print("\n6) PRED SPRÁVOU: pohyb −60→0 v smere následného výstrelu (záporné = výstrel ide proti driftu pred správou)")
for n in PRI:
    g = R[R.n == n]
    if len(g) < 15: continue
    pre = -g["k-60"]       # k-60 = s*(p(-60)-p0) → pohyb −60→0 v smere s = −k-60
    print(f"  {n:9} priem. {pre.mean():+.3f} ATR (t {tz(pre):+.1f})  proti driftu {100*(pre<0).mean():3.0f}%")

# 7) volatilita po 5 min vs rovnaký čas v dňoch bez správ
print("\n7) VOLATILITA: rozpätie 5-min sviečky po správe / rovnaký čas v dňoch bez správy (×) — kedy sa trh upokojí")
r5 = (df.h.resample("5min").max() - df.l.resample("5min").min()).dropna()
r5 = r5 / r5.index.normalize().map(lambda d: atr.get(d, np.nan))
base = r5[~r5.index.normalize().map(lambda d: d.date() in news_days)]
bmed = base.groupby(base.index.time).median()
OFF = [0, 5, 10, 15, 20, 25, 30, 45, 60, 90, 120]
print(f"{'typ':9}" + "".join(f"{'+'+str(o):>6}" for o in OFF))
for n in ["FOMC", "CPI", "NFP", "PCE", "PPI", "JOLTS", "ISM_M", "CLAIMS"]:
    ts = [t for t, x in taken.items() if x == n]
    line = []
    for o in OFF:
        v = []
        for t in ts:
            k = pd.Timestamp(t) + pd.Timedelta(minutes=o)
            if k in r5.index and k.time() in bmed.index: v.append(r5[k] / bmed[k.time()])
        line.append(np.median(v) if v else np.nan)
    print(f"{n:9}" + "".join(f"{x:6.1f}" for x in line))
R.to_csv("/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/news_pattern2.csv", index=False)
