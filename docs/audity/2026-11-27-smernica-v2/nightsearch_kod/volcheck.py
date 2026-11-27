"""Nezávislá kontrola filtra volatility: pri každom obchode je ATR(14) signálnej sviečky pod (low) / nad (high)
priemerom ATR za `volLookback` barov — počítané tu nanovo z 5m barov. MNQ 5m, posledný rok."""
import sys, json
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import numpy as np, pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.core.candles import resample_ohlcv
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
from tester.webapp.results import timerange_ms
K = "mnq_databento"; inst = INSTRUMENTS[K]; m = A.m1(K); b5 = resample_ohlcv(m, 5).set_index("date"); idx5 = b5.index
pc = b5.close.shift(1); tr = np.maximum(b5.high - b5.low, np.maximum((b5.high - pc).abs(), (b5.low - pc).abs()))
atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
f, t = timerange_ms("20250904-20260904")
for key in sys.argv[1:]:
    out = []
    for mode, n in (("off", 100), ("low", 100), ("high", 50)):
        p = {"_strategy": key, "_instrument": K, "volFilter": mode, "volLookback": n}
        A.TMP.joinpath("v.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "v.json", engine="multicharts")
        res, _ = emulate(cfg, inst, m, 5, from_ms=f, to_ms=t, fee=0.0)
        rows = rows_from_trades(res.trades, inst, 0.0, 1.0); s, _ = summarize(rows, 10000.0, res, currency="USD")
        mean = atr.rolling(n).mean(); bad = near = 0
        if mode != "off":
            for r in rows:
                od = pd.Timestamp(r["open_date"]); i = idx5.searchsorted(od.floor("5min")) - 1
                a, mu = atr.iloc[i], mean.iloc[i]
                ok = a < mu if mode == "low" else a > mu
                if not ok:
                    if abs(a - mu) < 0.03 * mu: near += 1
                    else: bad += 1
        out.append(f"{mode}/{n}: {s['trades']} obch, WR {s['winrate']:.1f} %, PF {s['profit_factor']:.2f}, odchýlok {bad} (na hrane {near})")
    print(key, "|", " | ".join(out))
