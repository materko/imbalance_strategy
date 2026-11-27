"""Prehrá uložené profily (emulátor MultiCharts) na poslednom roku a 5 referenčných oknách, bez nákladov."""
import json, os, sys, io, contextlib
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS")
W = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904"]
STRATS = set(sys.argv[1].split(","))
_M1 = {}

def ev(args):
    fn, w = args
    import pandas as pd
    from tradebot.core import load_profile
    from tradebot.core.types import INSTRUMENTS
    from tester import engines
    from tester.webapp.results import timerange_ms
    from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
    p = json.load(open(fn))
    inst = INSTRUMENTS[p["_instrument"]]
    tf = int(str(p.get("_timeframe") or "3m").rstrip("m"))
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            if inst.symbol not in _M1:
                _M1[inst.symbol] = pd.read_feather(engines.one_minute_file(inst))
            cfg, _ = load_profile(fn, engine="multicharts")
            f, t = timerange_ms(w)
            res, _ = emulate(cfg, inst, _M1[inst.symbol], tf, from_ms=f, to_ms=t, fee=0.0)
            rows = rows_from_trades(res.trades, inst, 0.0, float(p.get("leverage") or 1.0))
            s, _ = summarize(rows, 10000.0, res, currency=inst.quote_currency)
        return {k: s.get(k) for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_pct")}
    except Exception as e:
        return {"err": str(e)[:120]}

if __name__ == "__main__":
    fs = []
    for f in sorted(os.listdir("/Users/martin/IBS/tester/profiles")):
        if f.endswith(".json"):
            d = json.load(open("/Users/martin/IBS/tester/profiles/" + f))
            if (d.get("_strategy") or "ibs") in STRATS:
                fs.append("/Users/martin/IBS/tester/profiles/" + f)
    jobs = [(f, w) for f in fs for w in W]
    with ProcessPoolExecutor(9) as ex:
        res = list(ex.map(ev, jobs))
    out = {}
    for i, f in enumerate(fs):
        out[os.path.basename(f)[:-5]] = res[i * 5:(i + 1) * 5]
    json.dump(out, open("/Users/martin/IBS/.nightsearch/profeval.json", "w"))
    print(len(out), "profilov")
