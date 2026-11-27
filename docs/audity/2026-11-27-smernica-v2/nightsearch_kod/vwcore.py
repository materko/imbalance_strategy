"""Vyhodnotenie VWAP stratégií v procese: WR, PF, zisk, DD a reálny pomer zisk:strata."""
import json, os, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS")
import evalcore as E
from tradebot.core import load_profile
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
from tester.webapp.results import timerange_ms

def evaluate(params, tf, timerange):
    p = E.TMP / f"v{os.getpid()}.json"
    p.write_text(json.dumps(params))
    cfg, _ = load_profile(p, engine="multicharts")
    f, t = timerange_ms(timerange)
    res, _ = emulate(cfg, E.INST, E.m1(), tf, from_ms=f, to_ms=t, fee=0.0)
    rows = rows_from_trades(res.trades, E.INST, 0.0, 1.0)
    s, _ = summarize(rows, 10000.0, res, currency=E.INST.quote_currency)
    w = [r["profit_abs"] for r in rows if r["profit_abs"] > 0]
    l = [-r["profit_abs"] for r in rows if r["profit_abs"] < 0]
    out = {k: s.get(k) for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_abs")}
    out["payoff"] = round((sum(w) / len(w)) / (sum(l) / len(l)), 3) if w and l else (9.0 if w else 0.0)
    # pomer v R (nezávislý od počtu kontraktov): zisk / počiatočné riziko obchodu
    def rmult(r):
        risk = abs(r["open_rate"] - r["initial_stop_loss_abs"]) * r["amount"] * (r.get("point_value") or 1.0)
        return r["profit_abs"] / risk if risk > 0 else 0.0
    wr_ = [rmult(r) for r in rows if r["profit_abs"] > 0]; lr_ = [-rmult(r) for r in rows if r["profit_abs"] < 0]
    out["payoff_r"] = round((sum(wr_) / len(wr_)) / (sum(lr_) / len(lr_)), 3) if wr_ and lr_ and sum(lr_) > 0 else (9.0 if wr_ else 0.0)
    out["longs"] = sum(1 for r in rows if not r["is_short"])
    return out
