"""Nezávislá kontrola Volume Profile POC na MNQ 5m: každý obchod (limitka) má vstup na POC predošlej NY seansy
spočítanom tu nanovo z 5m barov, smer podľa strany ceny pred vstupom, stop 1,5 ATR a cieľ 1,5R."""
import sys, json
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import numpy as np, pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.core.candles import resample_ohlcv
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
from tester.webapp.results import timerange_ms
K = "mnq_databento"; inst = INSTRUMENTS[K]
extra = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
p = {"_strategy": "svp", "_instrument": K, "tickDollarValue": 0.5, **extra}
A.TMP.joinpath("svp.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "svp.json", engine="multicharts")
m = A.m1(K); b5 = resample_ohlcv(m, 5).copy()
b5["ny"] = b5.date.dt.tz_convert("America/New_York")
mins = b5.ny.dt.hour * 60 + b5.ny.dt.minute
ses = b5[(mins >= 570) & (mins < 960) & (b5.ny.dt.weekday < 5)]
poc = {}
for d, g in ses.groupby(ses.ny.dt.date):
    rows = {}
    for lo, hi, v in zip(g.low, g.high, g.volume):
        if v <= 0: continue
        a, b = int(np.floor(lo)), int(np.floor(hi))
        for k in range(a, b + 1): rows[k] = rows.get(k, 0) + v / (b - a + 1)
    top = max(rows.values()); best = [k for k, v in rows.items() if v == top]
    mid = (min(rows) + max(rows)) / 2
    poc[d] = (min(best, key=lambda k: abs(k - mid)) + 0.5, g.ny.iloc[-1])
days = sorted(poc)
for tr in ("20250904-20260904", "20240904-20250904"):
    f, t = timerange_ms(tr)
    res, _ = emulate(cfg, inst, m, 5, from_ms=f, to_ms=t, fee=0.0)
    rows = rows_from_trades(res.trades, inst, 0.0, 1.0); s, _ = summarize(rows, 10000.0, res, currency="USD")
    print(tr, {k: s[k] for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_abs")})
    if tr != "20250904-20260904": continue
    bad = {"vstup nie je na POC predošlej seansy": 0, "smer nesedí so stranou": 0, "cieľ nie je 1,5R": 0, "mimo okna": 0}
    idx = b5.set_index("date")
    for r in rows:
        od = pd.Timestamp(r["open_date"]); ny = od.tz_convert("America/New_York")
        done = [d for d in days if poc[d][1] + pd.Timedelta(minutes=5) <= ny]      # seansa skončená pred vstupom
        want = poc[done[-1]][0]
        if abs(r["open_rate"] - want) > 0.26:
            bad["vstup nie je na POC predošlej seansy"] += 1
            if bad["vstup nie je na POC predošlej seansy"] <= 5: print("  POC:", ny, r["open_rate"], "čakal", want)
        prev_close = idx.close[idx.index < od.floor("5min")].iloc[-1]
        if (prev_close < want) != bool(r["is_short"]): bad["smer nesedí so stranou"] += 1
        sl = abs(r["initial_stop_loss_abs"] - r["open_rate"]); tp = abs(r["initial_take_profit_abs"] - r["open_rate"])
        if abs(tp - 1.5 * sl) > 0.6: bad["cieľ nie je 1,5R"] += 1
        mm = ny.hour * 60 + ny.minute
        if not (570 <= mm < 935): bad["mimo okna"] += 1
    print(len(rows), "obchodov;", bad)
    print("long", sum(not r["is_short"] for r in rows), "short", sum(bool(r["is_short"]) for r in rows))
