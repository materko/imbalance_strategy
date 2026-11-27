"""Nezávislá kontrola spoločného vstupného modelu: každý obchod s `entryConfirm` vstúpil na zavretí sviečky,
ktorá je pin bar alebo IBS imbalance v smere obchodu. Pre viac stratégií na MNQ 5m, posledný rok."""
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
    for mode in ("none", "any", "pinbar", "imbalance"):
        p = {"_strategy": key, "_instrument": K, "entryConfirm": mode}
        A.TMP.joinpath("c.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "c.json", engine="multicharts")
        res, _ = emulate(cfg, inst, m, 5, from_ms=f, to_ms=t, fee=0.0)
        rows = rows_from_trades(res.trades, inst, 0.0, 1.0); s, _ = summarize(rows, 10000.0, res, currency="USD")
        bad = 0
        if mode != "none":
            for r in rows:
                od = pd.Timestamp(r["open_date"]); i = idx5.searchsorted(od.floor("5min")) - 1
                b0, b1, b2 = b5.iloc[i], b5.iloc[i - 1], b5.iloc[i - 2]; short = bool(r["is_short"])
                rng = b0.high - b0.low; body = abs(b0.close - b0.open)
                wick = (b0.high - max(b0.open, b0.close)) if short else (min(b0.open, b0.close) - b0.low)
                pin = rng > 0 and body <= 0.30 * rng and wick >= 0.60 * rng
                imb = (b0.high < b2.low and b1.close < b2.low) if short else (b0.low > b2.high and b1.close > b2.high)
                ok = {"any": pin or imb, "pinbar": pin, "imbalance": imb}[mode]
                if not ok or abs(r["open_rate"] - b5.iloc[i + 1].open) > 0.26: bad += 1      # market sa plní na otvorení ďalšej sviečky
        out.append(f"{mode}: {s['trades']} obch, WR {s['winrate']:.1f} %, PF {s['profit_factor']:.2f}, odchýlok {bad}")
    print(key, "|", " | ".join(out))
