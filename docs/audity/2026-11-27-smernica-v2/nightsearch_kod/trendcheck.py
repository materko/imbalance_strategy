"""Nezávislá kontrola filtra trendu: každý obchod s `trendFilter` je na správnej strane EMA (počítanej tu nanovo
z hodinových / 5m zavretí). MNQ 5m, posledný rok."""
import sys, json
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.core.candles import resample_ohlcv
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
from tester.webapp.results import timerange_ms
K = "mnq_databento"; inst = INSTRUMENTS[K]; m = A.m1(K); b5 = resample_ohlcv(m, 5).set_index("date"); idx5 = b5.index
f, t = timerange_ms("20250904-20260904")
for key in sys.argv[1:]:
    out = []
    for mode, tf, n in (("off", 0, 200), ("with", 60, 200), ("against", 60, 50), ("with", 0, 100)):
        p = {"_strategy": key, "_instrument": K, "trendFilter": mode, "trendTF": tf, "trendEmaLen": n}
        A.TMP.joinpath("t.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "t.json", engine="multicharts")
        res, _ = emulate(cfg, inst, m, 5, from_ms=f, to_ms=t, fee=0.0)
        rows = rows_from_trades(res.trades, inst, 0.0, 1.0); s, _ = summarize(rows, 10000.0, res, currency="USD")
        bad = near = 0
        if mode != "off":
            h = (resample_ohlcv(m, tf).set_index("date") if tf else b5).close
            ema = h.ewm(span=n, adjust=False).mean()
            for r in rows:
                od = pd.Timestamp(r["open_date"]); i = idx5.searchsorted(od.floor("5min")) - 1; sig = idx5[i]
                known = sig + pd.Timedelta(minutes=5) - pd.Timedelta(minutes=tf or 5)     # posledný uzavretý bar TF filtra
                e = ema[ema.index <= known].iloc[-1]; c = b5.close.iloc[i]; short = bool(r["is_short"])
                ok = ((c > e) != short) if mode == "with" else ((c > e) == short)
                if not ok:
                    if abs(c - e) < 0.0005 * c: near += 1
                    else: bad += 1
        out.append(f"{mode}/{tf}m/EMA{n}: {s['trades']} obch, WR {s['winrate']:.1f} %, PF {s['profit_factor']:.2f}, odchýlok {bad} (na hrane {near})")
    print(key, "|", " | ".join(out))
