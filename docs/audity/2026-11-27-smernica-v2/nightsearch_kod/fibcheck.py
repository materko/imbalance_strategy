"""Nezávislá kontrola Fibo na MNQ 5m: každý obchod má nohu medzi potvrdenými swingmi na 15m, cieľ na extenzii −27 %,
stop za začiatkom nohy, dno návratu v zóne 38,2–78,6 % a vstupnú sviečku (pin bar alebo IBS imbalance)."""
import sys, json
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import numpy as np, pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.core.candles import resample_ohlcv
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
from tester.webapp.results import timerange_ms
K = "mnq_databento"; inst = INSTRUMENTS[K]
p = {"_strategy": "fibo", "_instrument": K, "tickDollarValue": 0.5, "slBufferAtr": {"value": 0, "unit": "atr"},
     "levelTolAtr": {"value": 0, "unit": "atr"}}
A.TMP.joinpath("f.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "f.json", engine="multicharts")
f, t = timerange_ms("20250904-20260904")
res, _ = emulate(cfg, inst, A.m1(K), 5, from_ms=f, to_ms=t, fee=0.0)
rows = rows_from_trades(res.trades, inst, 0.0, 1.0); s, _ = summarize(rows, 10000.0, res, currency="USD")
print({k: s[k] for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_abs")})
m = A.m1(K); b5 = resample_ohlcv(m, 5).set_index("date"); b15 = resample_ohlcv(m, 15).reset_index(drop=True)
n = 3; H, L = b15.high.to_numpy(), b15.low.to_numpy(); T = b15.date
ph = [i for i in range(n, len(b15) - n) if all(H[i] > H[j] for j in range(i - n, i + n + 1) if j != i)]
pl = [i for i in range(n, len(b15) - n) if all(L[i] < L[j] for j in range(i - n, i + n + 1) if j != i)]
ph_t = np.array([T[i].value for i in ph]); pl_t = np.array([T[i].value for i in pl])
bad = {"noha / cieľ nesedí": 0, "stop nie je začiatok nohy": 0, "návrat mimo zóny": 0, "žiadna vstupná sviečka": 0}
idx5 = b5.index
for r in rows:
    od = pd.Timestamp(r["open_date"]); i = idx5.searchsorted(od.floor("5min")) - 1; sig = idx5[i]
    short = r["is_short"]; tp, sl = r["initial_take_profit_abs"], r["initial_stop_loss_abs"]
    ends, starts, et, stt = (pl, ph, pl_t, ph_t) if short else (ph, pl, ph_t, pl_t)
    known = sig.value + 5 * 60 * 10**9 - (n + 1) * 15 * 60 * 10**9      # swing musí byť potvrdený pri zavretí signálnej sviečky
    ok = None
    for k in range(np.searchsorted(et, known, side="right") - 1, max(-1, np.searchsorted(et, known, side="right") - 60), -1):
        e_i = ends[k]; j = np.searchsorted(stt, et[k]) - 1
        if j < 0: continue
        s_i = starts[j]
        hi, lo = (H[s_i], L[e_i]) if short else (H[e_i], L[s_i])
        size = hi - lo
        want = (lo - 0.27 * size) if short else (hi + 0.27 * size)
        if abs(want - tp) < 0.26:
            ok = (s_i, e_i, hi, lo, size); break
    if ok is None:
        bad["noha / cieľ nesedí"] += 1; print("  noha:", sig, "short" if short else "long", "tp", tp, "sl", sl); continue
    s_i, e_i, hi, lo, size = ok
    if abs(sl - (hi if short else lo)) > 0.26: bad["stop nie je začiatok nohy"] += 1
    seg = b5[(b5.index >= T[e_i] + pd.Timedelta(minutes=15)) & (b5.index <= sig)]   # návrat sa ráta od baru za swingom
    ext = seg.high.max() if short else seg.low.min()
    depth = (ext - lo) / size if short else (hi - ext) / size
    if not (0.382 - 1e-9 <= depth <= 0.786 + 1e-9):
        bad["návrat mimo zóny"] += 1; print("  zóna:", sig, "short" if short else "long", "noha", lo, hi, "ext", ext, "hĺbka", round(depth, 3))
    b0, b1, b2 = b5.iloc[i], b5.iloc[i - 1], b5.iloc[i - 2]
    rng = b0.high - b0.low; body = abs(b0.close - b0.open)
    wick = (b0.high - max(b0.open, b0.close)) if short else (min(b0.open, b0.close) - b0.low)
    pin = rng > 0 and body <= 0.30 * rng and wick >= 0.60 * rng
    imb = (b0.high < b2.low and b1.close < b2.low) if short else (b0.low > b2.high and b1.close > b2.high)
    if not (pin or imb): bad["žiadna vstupná sviečka"] += 1
print(len(rows), "obchodov;", bad)
