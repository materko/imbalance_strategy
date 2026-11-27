import sys, json
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.core.candles import resample_ohlcv
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades
from tester.webapp.results import timerange_ms
K = "mnq_databento"; inst = INSTRUMENTS[K]; m = A.m1(K); b5 = resample_ohlcv(m, 5).set_index("date"); idx5 = b5.index
f, t = timerange_ms("20250904-20260904")
p = {"_strategy": "range", "_instrument": K, "entryConfirm": "pinbar"}
A.TMP.joinpath("c.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "c.json", engine="multicharts")
res, _ = emulate(cfg, inst, m, 5, from_ms=f, to_ms=t, fee=0.0)
rows = rows_from_trades(res.trades, inst, 0.0, 1.0)
for r in rows[:8]:
    od = pd.Timestamp(r["open_date"]); i = idx5.searchsorted(od.floor("5min"))
    print(od, "short" if r["is_short"] else "long", r["open_rate"])
    print(b5.iloc[i-3:i+1][["open","high","low","close"]].to_string())
