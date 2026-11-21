"""Kontrola kalendára SPRÁVY na skutočných 1m sviečkach MGC: je výbuch volatility presne v čase správy (cez engine prevod)?"""
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/martin/document/IBS")
from tester import engines
from tradebot.core.types import INSTRUMENTS
from tradebot.strategies.spravy.calendar import events_utc
from tradebot.strategies.spravy.engine import sk_time

df = pd.read_feather(engines.one_minute_file(INSTRUMENTS["mgc_databento"]))
t = pd.to_datetime(df["date"], utc=True).astype("int64") // 10**6
rng = pd.Series((df.high - df.low).values, index=t.values)
ix = rng.index.values; rv = rng.values

def win(ms, a, b):
    i, j = np.searchsorted(ix, ms + a * 60000), np.searchsorted(ix, ms + b * 60000)
    return rv[i:j]

rows = []
for ms, typ in events_utc():
    if ms < ix[0] or ms > ix[-1]:
        continue
    base = win(ms, -40, -5)
    if len(base) < 20:
        rows.append((ms, typ, np.nan, np.nan, np.nan, "bez dát")); continue
    med = np.median(base) or 1e-9
    at = win(ms, 0, 3).max(initial=0) / med                       # výbuch v čase správy
    early = win(ms, -62, -57).max(initial=0) / np.median(win(ms, -100, -65)) if len(win(ms, -100, -65)) > 20 else np.nan
    late = win(ms, 58, 63).max(initial=0) / np.median(win(ms, 20, 55)) if len(win(ms, 20, 55)) > 20 else np.nan
    rows.append((ms, typ, at, early, late, ""))
R = pd.DataFrame(rows, columns=["ms", "typ", "x", "early", "late", "pozn"])
R["sk"] = R.ms.map(sk_time)
R["d"] = R.ms.map(lambda m: datetime.fromtimestamp(m / 1000, tz=ZoneInfo("America/New_York")).strftime("%Y-%m-%d %a"))
print(f"{'typ':9}{'n':>5} {'výbuch v T (medián ×)':>22} {'v T ≥ 3×':>9} {'o hodinu inde silnejšie':>24}")
for typ, g in R.groupby("typ", sort=False):
    g = g.dropna(subset=["x"])
    shift = ((g.early > 2 * g.x) | (g.late > 2 * g.x)) & (g.x < 3)
    print(f"{typ:9}{len(g):5} {g.x.median():22.1f} {100*(g.x>=3).mean():8.0f}% {int(shift.sum()):24d}")
sus = R[(R.x < 2) & R.typ.isin(["FOMC", "CPI", "NFP", "PPI", "PCE", "JOLTS"])]
print(f"\nPodozrivé (FOMC/CPI/NFP/PPI/PCE/JOLTS bez výbuchu v T, < 2×): {len(sus)}")
print(sus[["d", "typ", "sk", "x", "early", "late"]].to_string(index=False) if len(sus) else "  žiadne")
# týždne posunu času — všetky správy v nich
dst = R[R.ms.map(lambda m: (lambda d: (d.month == 3 and d.day <= 31) or (d.month in (10, 11) and (d.month == 10 and d.day >= 20 or d.month == 11 and d.day <= 8)))(datetime.fromtimestamp(m/1000, tz=timezone.utc)))]
dst = dst[dst.typ.isin(["FOMC", "CPI", "NFP", "PPI", "PCE", "JOLTS", "ISM_M", "ISM_S", "RETAIL", "GDP"])]
odd = dst[dst.sk.str[:5] != dst.sk.str[:5]]  # placeholder
print("\nTýždne posunu času (marec, koniec okt. – zač. nov.), hlavné správy: čas SK a výbuch v T:")
for _, r in dst.iterrows():
    if r.d[5:7] in ("03", "10", "11"):
        mark = "OK" if r.x >= 3 else ("?" if r.x >= 2 else "!!")
        print(f"  {r.d} {r.typ:7} {r.sk:22} výbuch {r.x:5.1f}×  {mark}")

print("\nPodozrivé — výbuch v iných štandardných časoch (±1 deň, 8:30 / 10:00 / 14:00 NY):")
NYZ = ZoneInfo("America/New_York")
def spike(ms):
    base = win(ms, -40, -5)
    return win(ms, 0, 3).max(initial=0) / (np.median(base) or 1e-9) if len(base) >= 20 else np.nan
from datetime import timedelta
for _, r in R[(R.x < 2.5) & R.typ.isin(["FOMC", "CPI", "NFP", "PPI", "PCE", "JOLTS", "GDP", "RETAIL"])].iterrows():
    d0 = datetime.fromtimestamp(r.ms / 1000, tz=NYZ)
    best = []
    for dd in (-1, 0, 1):
        for hh, mm in ((8, 30), (10, 0), (14, 0)):
            c = (d0 + timedelta(days=dd)).replace(hour=hh, minute=mm)
            v = spike(int(c.timestamp() * 1000))
            if v == v: best.append((v, c.strftime("%m-%d %H:%M")))
    best.sort(reverse=True)
    print(f"  {r.d} {r.typ:6} v kalendári {r.x:4.1f}× | najsilnejšie: " + ", ".join(f"{c} {v:.1f}×" for v, c in best[:3]))
print("\nCPI pod 3×:", R[(R.typ == "CPI") & (R.x < 3)][["d", "sk", "x"]].to_string(index=False))
