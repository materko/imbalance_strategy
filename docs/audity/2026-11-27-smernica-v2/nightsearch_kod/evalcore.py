"""Rychle vyhodnotenie konfiguracie v procese (emulator MultiCharts, MNQ databento)."""
import json, os, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS")
import pandas as pd
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tester import engines
from tester.webapp.results import timerange_ms
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize

_M1 = None
INST = INSTRUMENTS["mnq_databento"]
TMP = Path(tempfile.mkdtemp(prefix="ns_"))

def m1():
    global _M1
    if _M1 is None:
        _M1 = pd.read_feather(engines.one_minute_file(INST))
    return _M1

def evaluate(params: dict, tf: int, timerange: str, fee=None):
    p = TMP / f"p{os.getpid()}.json"
    p.write_text(json.dumps(params))
    cfg, _ = load_profile(p, engine="multicharts")
    f, t = timerange_ms(timerange)
    t0 = time.time()
    if fee is None:
        fee = 0.0
    elif fee == "market":
        from tester.fees import for_pair
        fee = for_pair("MNQ/USD", f"{tf}m", timerange)[0] or 0.0
    res, _ = emulate(cfg, INST, m1(), tf, from_ms=f, to_ms=t, fee=fee)
    rows = rows_from_trades(res.trades, INST, fee, float(params.get("leverage") or 1.0))
    s, _ = summarize(rows, 10000.0, res, currency=INST.quote_currency)
    keep = ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_abs", "max_drawdown_pct")
    out = {k: s.get(k) for k in keep}
    out["sec"] = round(time.time() - t0, 1)
    return out
