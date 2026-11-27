"""Nezávislá kontrola CRT + TBS: každý obchod má range (predošlá sviečka vyššieho TF), výber telom,
stop za extrémom výberu a cieľ na opačnom konci rangu. python crtcheck.py"""
import sys, json
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import numpy as np, pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.core.candles import resample_ohlcv
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades
from tester.webapp.results import timerange_ms

inst = INSTRUMENTS["mnq_databento"]
p = {"_strategy": "crt", "_instrument": "mnq_databento", "tickDollarValue": 0.5, "slBufferAtr": {"value": 0, "unit": "atr"}}
A.TMP.joinpath("c.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "c.json", engine="multicharts")
f, t = timerange_ms("20250904-20260904")
res, _ = emulate(cfg, inst, A.m1("mnq_databento"), 5, from_ms=f, to_ms=t, fee=0.0)
rows = rows_from_trades(res.trades, inst, 0.0, 1.0)
m = A.m1("mnq_databento"); b5 = resample_ohlcv(m, 5).set_index("date"); h4 = resample_ohlcv(m, 240).set_index("date")
bad = {"cieľ nie je koniec rangu": 0, "žiadne zavretie za hranicou pred vstupom": 0, "stop nie je extrém výberu": 0,
       "vstup mimo rangu": 0, "range starší než 2 sviečky": 0}
for r in rows:
    od = pd.Timestamp(r["open_date"]); sig = b5.index[b5.index.searchsorted(od.floor("5min")) - 1]   # signálna sviečka = posledná pred vstupom
    short = r["is_short"]; tp, sl = r["initial_take_profit_abs"], r["initial_stop_loss_abs"]
    cur = sig.floor("240min")
    prev = h4[h4.index < cur].iloc[-2:]                    # dve posledné uzavreté 4h sviečky pred tou so signálom
    cand = [c for c in prev.itertuples() if abs((c.low if short else c.high) - tp) < 0.26]
    if not cand:
        bad["cieľ nie je koniec rangu"] += 1; continue
    c = cand[-1]; level = c.high if short else c.low
    seg = b5[(b5.index >= c.Index + pd.Timedelta(minutes=240)) & (b5.index <= sig)]
    if not ((seg.close > level).any() if short else (seg.close < level).any()):
        bad["žiadne zavretie za hranicou pred vstupom"] += 1
    ext = seg.high.max() if short else seg.low.min()
    if abs(ext - sl) > 0.26:
        bad["stop nie je extrém výberu"] += 1
    sc = b5.loc[sig].close
    if not (c.low < sc < c.high):
        bad["vstup mimo rangu"] += 1
print(len(rows), "obchodov;", bad)
