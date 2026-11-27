"""Vyhodnotenie ľubovoľnej stratégie na ľubovoľnom nástroji v procese (emulátor MultiCharts, bez nákladov)."""
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS")
import pandas as pd
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tester import engines
from tester.webapp.results import timerange_ms
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize

_M1 = {}
TMP = Path(tempfile.mkdtemp(prefix="all_"))

def m1(inst_key):
    if inst_key not in _M1:
        _M1[inst_key] = pd.read_feather(engines.one_minute_file(INSTRUMENTS[inst_key]))
    return _M1[inst_key]

def evaluate(params, tf, timerange, inst_key):
    inst = INSTRUMENTS[inst_key]
    p = TMP / f"a{os.getpid()}.json"
    p.write_text(json.dumps(dict(params, _instrument=inst_key)))
    cfg, _ = load_profile(p, engine="multicharts")
    f, t = timerange_ms(timerange)
    res, _ = emulate(cfg, inst, m1(inst_key), tf, from_ms=f, to_ms=t, fee=0.0)
    rows = rows_from_trades(res.trades, inst, 0.0, float(params.get("leverage") or 1.0))
    s, _ = summarize(rows, 10000.0, res, currency=inst.quote_currency)
    out = {k: s.get(k) for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_abs")}
    def rmult(r):
        risk = abs(r["open_rate"] - r["initial_stop_loss_abs"]) * r["amount"] * (r.get("point_value") or 1.0)
        return r["profit_abs"] / risk if risk > 0 else 0.0
    w = [rmult(r) for r in rows if r["profit_abs"] > 0]; l = [-rmult(r) for r in rows if r["profit_abs"] < 0]
    out["payoff_r"] = round((sum(w) / len(w)) / (sum(l) / len(l)), 3) if w and l and sum(l) > 0 else (round(sum(w) / len(w), 3) if w else 0.0)   # bez strát: priemerný zisk v R
    return out
