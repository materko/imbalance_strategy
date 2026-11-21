"""Označí udalosti do 5 min od americkej správy (červenej / oranžovej) a vypíše najlepšie hypotézy bez nich."""
import numpy as np, pandas as pd
S = "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad"
raw = pd.read_csv(f"{S}/ffdata/forex_factory_cache.csv", usecols=["DateTime", "Currency", "Impact", "Event"])
raw = raw[(raw.DateTime >= "2020-12-20") & (raw.Currency == "USD") & raw.Impact.str.startswith(("High", "Medium"))].copy()
fix = (raw.DateTime.str[:4] >= "2023") & raw.DateTime.str.endswith("+04:30")
raw.loc[fix, "DateTime"] = raw.loc[fix, "DateTime"].str[:-6] + "+03:30"
raw["missing"] = raw.DateTime.str[11:19].isin(["00:00:00", "23:59:59"])
raw["t"] = pd.to_datetime(raw.DateTime, utc=True)
usd = []
for ev, g in raw.groupby("Event"):
    k = g[~g.missing]
    loc = k.t.dt.tz_convert("America/New_York").dt.strftime("%H:%M")
    for r in g.itertuples():
        if not r.missing: usd.append(r.t)
        elif len(k):
            ref = pd.Timestamp(r.DateTime[:10]).tz_localize("UTC"); j = abs(k.t - ref).values.argmin()
            usd.append(pd.Timestamp(f"{r.DateTime[:10]} {loc.iloc[j]}").tz_localize("America/New_York").tz_convert("UTC"))
usd = np.array(sorted(pd.Series(usd).astype("datetime64[ms, UTC]").astype("int64").unique()))
X = pd.read_csv(f"{S}/ffwork/ff_gold_trades.csv")
def near(ms):
    i = np.searchsorted(usd, ms)
    return any(0 <= j < len(usd) and abs(usd[j] - ms) <= 5 * 60000 for j in (i - 1, i))
X["usd"] = X.ms.map(near)
X.to_csv(f"{S}/ffwork/ff_gold_trades.csv", index=False)
print("v čase americkej správy (%):", {k: v for k, v in X.groupby("typ").usd.mean().mul(100).round(0).astype(int).sort_values(ascending=False).items() if v > 0})
HYP = [c for c in X.columns if "drž" in c]
def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum(); return g / l if l else 99
out = []
for typ, g in X[~X.usd].groupby("typ"):
    for h in HYP:
        x = g[h].dropna()
        if len(x) < 12: continue
        t = x.mean() / (x.std() / np.sqrt(len(x)))
        yp = g.dropna(subset=[h]).groupby("y")[h].sum()
        out.append((t, typ, h, len(x), (x > 0).mean(), pf(x), int((yp > 0).sum()), len(yp), x.sum(), g.spike.median()))
out.sort(reverse=True)
print("\nnajlepšie (bez amerických správ v tú istú minútu):")
for t, typ, h, n, wr, p, yp, ny, s, sp in out[:14]:
    print(f"  {typ:8} {h:32} n {n:3} výbuch {sp:4.1f}× WR {100*wr:3.0f}% PF {p:4.2f} t {t:+.1f} rokov+ {yp}/{ny} {s:+6.0f}$")
print("najhoršie (opačný obchod by bol dobrý):")
for t, typ, h, n, wr, p, yp, ny, s, sp in out[-6:]:
    print(f"  {typ:8} {h:32} n {n:3} výbuch {sp:4.1f}× WR {100*wr:3.0f}% PF {p:4.2f} t {t:+.1f} rokov+ {yp}/{ny} {s:+6.0f}$")
print(f"  hypotéz {len(out)}, náhoda dá |t| > 2 asi {0.046*len(out):.0f}×; t > 2: {sum(o[0] > 2 for o in out)}, t < −2: {sum(o[0] < -2 for o in out)}")
