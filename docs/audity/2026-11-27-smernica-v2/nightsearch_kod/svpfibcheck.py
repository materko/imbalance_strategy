"""Nezávislá kontrola Fibonacciho filtra vo Volume Profile POC (MNQ 5m): pri každom obchode existuje noha medzi
potvrdenými swingmi na 15m (neprerazená, predĺžená po aktuálny extrém), na ktorej POC leží v pásme 38,2–78,6 %."""
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
p = {"_strategy": "svp", "_instrument": K, "tickDollarValue": 0.5, "useFibo": True}
A.TMP.joinpath("svpf.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "svpf.json", engine="multicharts")
m = A.m1(K); b5 = resample_ohlcv(m, 5).set_index("date"); b15 = resample_ohlcv(m, 15).reset_index(drop=True)
n = 3; H, L = b15.high.to_numpy(), b15.low.to_numpy(); T = b15.date
ph = [i for i in range(n, len(b15) - n) if all(H[i] > H[j] for j in range(i - n, i + n + 1) if j != i)]
pl = [i for i in range(n, len(b15) - n) if all(L[i] < L[j] for j in range(i - n, i + n + 1) if j != i)]
ph_t = np.array([T[i].value for i in ph]); pl_t = np.array([T[i].value for i in pl])
f, t = timerange_ms("20250904-20260904")
res, _ = emulate(cfg, inst, m, 5, from_ms=f, to_ms=t, fee=0.0)
rows = rows_from_trades(res.trades, inst, 0.0, 1.0); s, _ = summarize(rows, 10000.0, res, currency="USD")
print({k: s[k] for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_abs")})
idx5 = b5.index; bad = 0
for r in rows:
    od = pd.Timestamp(r["open_date"]); i = idx5.searchsorted(od.floor("5min")) - 1; sig = idx5[i]   # bar, na ktorom bola limitka zadaná
    short = bool(r["is_short"]); P = r["open_rate"]
    ends, starts, et, stt = (pl, ph, pl_t, ph_t) if short else (ph, pl, ph_t, pl_t)
    known = sig.value + 5 * 60 * 10**9 - (n + 1) * 15 * 60 * 10**9
    k0 = np.searchsorted(et, known, side="right") - 1; ok = False
    for k in range(k0, max(-1, k0 - 80), -1):
        e_i = ends[k]; j = np.searchsorted(stt, et[k]) - 1
        if j < 0: continue
        s_i = starts[j]
        seg = b5[(b5.index >= T[s_i] + pd.Timedelta(minutes=15)) & (b5.index <= sig)]
        if short:
            start = H[s_i]; end = min(L[e_i], b5[(b5.index >= T[e_i]) & (b5.index <= sig)].low.min())
            if seg.high.max() > start: continue
            ret = (P - end) / (start - end)
        else:
            start = L[s_i]; end = max(H[e_i], b5[(b5.index >= T[e_i]) & (b5.index <= sig)].high.max())
            if seg.low.min() < start: continue
            ret = (end - P) / (end - start)
        if 0.382 - 0.002 <= ret <= 0.786 + 0.002: ok = True; break
    if not ok:
        bad += 1; print("  bez nohy:", sig, "short" if short else "long", P)
print(len(rows), "obchodov; bez nohy v pásme:", bad)
