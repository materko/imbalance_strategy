"""Nezávislá kontrola Scalping 3MA + RSI + fraktál na EURUSD 5m: každý vstup má trend (close pod/nad troma SMMA),
RSI pod/nad 50, fraktál potvrdený signálnym barom, stop 5 pipov a cieľ 10 pipov, najviac 1 obchod denne."""
import sys, json
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import numpy as np, pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.core.candles import resample_ohlcv
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
from tester.webapp.results import timerange_ms
K = "eurusd_dukascopy"; inst = INSTRUMENTS[K]
p = json.load(open("/Users/martin/IBS/tradebot/strategies/scalp3ma/configs/eurusd_dukascopy_5m.json"))
A.TMP.joinpath("s.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "s.json", engine="multicharts")
f, t = timerange_ms("20250904-20260904")
res, _ = emulate(cfg, inst, A.m1(K), 5, from_ms=f, to_ms=t, fee=0.0)
rows = rows_from_trades(res.trades, inst, 0.0, 1.0); s, _ = summarize(rows, 10000.0, res, currency="USD")
print({k: s[k] for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_abs")}, s.get("exits"))
b = resample_ohlcv(A.m1(K), 5).set_index("date")
c = b.close
def smma(x, n):   # SMMA = RMA so štartom na SMA
    out = np.full(len(x), np.nan); v = x.to_numpy()
    out[n - 1] = v[:n].mean()
    for i in range(n, len(v)):
        out[i] = (out[i - 1] * (n - 1) + v[i]) / n
    return pd.Series(out, index=x.index)
m1, m2, m3 = smma(c, 20), smma(c, 60), smma(c, 200)
d = c.diff(); up = smma(d.clip(lower=0).iloc[1:], 14).reindex(c.index); dn = smma((-d).clip(lower=0).iloc[1:], 14).reindex(c.index)
rsi = 100 - 100 / (1 + up / dn)
bad = {"trend": 0, "RSI": 0, "fraktál": 0, "stop/cieľ": 0, "viac než 1 za deň": 0}; days = {}
idx = b.index
for r in rows:
    od = pd.Timestamp(r["open_date"]); i = idx.searchsorted(od.floor("5min")) - 1; sig = idx[i]
    short = r["is_short"]; cl = c.iloc[i]
    hi, lo = max(m1.iloc[i], m2.iloc[i], m3.iloc[i]), min(m1.iloc[i], m2.iloc[i], m3.iloc[i])
    if not (cl < lo if short else cl > hi): bad["trend"] += 1
    if not (rsi.iloc[i] < 50 if short else rsi.iloc[i] > 50): bad["RSI"] += 1
    w = b.iloc[i - 4:i + 1]; mid = w.iloc[2]
    fr = (mid.high > w.high.drop(w.index[2]).max()) if short else (mid.low < w.low.drop(w.index[2]).min())
    if not fr: bad["fraktál"] += 1
    if abs(abs(r["initial_stop_loss_abs"] - cl) - 0.0005) > 2e-5 or abs(abs(r["initial_take_profit_abs"] - cl) - 0.0010) > 2e-5: bad["stop/cieľ"] += 1
    day = sig.tz_convert("America/New_York").date(); days[day] = days.get(day, 0) + 1
bad["viac než 1 za deň"] = sum(1 for v in days.values() if v > 1)
print(len(rows), "obchodov;", bad)
