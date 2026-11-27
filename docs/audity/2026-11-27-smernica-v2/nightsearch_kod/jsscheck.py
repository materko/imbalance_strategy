"""Kontrola kresieb a vstupov JSS: sedia BOS čiary, zóny a vstupy so sviečkami?
python jsscheck.py <run_id>"""
import json, sys, time, urllib.request
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/martin/IBS")
from tester import engines
from tradebot.core.candles import resample_ohlcv
from tradebot.core.types import INSTRUMENTS

R = sys.argv[1]
U = "http://127.0.0.1:8765/api/runs/" + R
urllib.request.urlopen(urllib.request.Request(U + "/chart", method="POST")).read()
for _ in range(100):
    if b"ready" in urllib.request.urlopen(U + "/chart/status").read():
        break
    time.sleep(2)
rec = json.load(urllib.request.urlopen(U))["record"]
P = rec["params"]; tf = int(rec["settings"]["timeframe"].rstrip("m"))
stf = int(P.get("structTF", 5)); stf = -(-max(stf, tf) // tf) * tf
n = int(P.get("swingLen", 3))
objs = json.load(urllib.request.urlopen(U + "/chart?from=0&to=99999999999999"))["objects"]
m1 = pd.read_feather(engines.one_minute_file(INSTRUMENTS["mnq_databento"]))
S = resample_ohlcv(m1, stf); st = S.date.astype("int64").to_numpy() // 10**6
C = resample_ohlcv(m1, tf); ct = C.date.astype("int64").to_numpy() // 10**6
sc, sh, sl = S.close.to_numpy(), S.high.to_numpy(), S.low.to_numpy()
ch, cl = C.high.to_numpy(), C.low.to_numpy()
err = {"BOS: sviečka nezavrela za úrovňou": 0, "BOS: skoršie zavretie za úrovňou": 0,
       "zóna: hrany nesedia so sviečkou": 0, "zóna: dotyk pred koncom": 0,
       "vstup: nie na hrane zóny": 0, "vstup: stop nie za zónou": 0}
L = [o for o in objs if o["k"] in ("jss_bos", "jss_choch")]
for o in L:
    y = o["y1"]; i2 = np.searchsorted(st, o["x2"]); i1 = np.searchsorted(st, o["x1"])
    if i2 >= len(st) or st[i2] != o["x2"]:
        continue
    up = sh[i1] == y   # prerazený swing high
    if (up and not sc[i2] > y) or (not up and not sc[i2] < y):
        err["BOS: sviečka nezavrela za úrovňou"] += 1
    mid = slice(i1 + n + 1, i2)
    if (up and (sc[mid] > y).any()) or (not up and (sc[mid] < y).any()):
        err["BOS: skoršie zavretie za úrovňou"] += 1
Z = [o for o in objs if o["k"] == "jss_zone"]
wick = P.get("zoneEdge", "wick") == "wick" and P.get("zoneType", "ob") == "ob"
for o in Z:
    top, bot = max(o["y1"], o["y2"]), min(o["y1"], o["y2"])
    i = np.searchsorted(st, o["x1"])
    if wick and (i >= len(st) or abs(sh[i] - top) > 1e-6 or abs(sl[i] - bot) > 1e-6):
        err["zóna: hrany nesedia so sviečkou"] += 1
tr = json.load(urllib.request.urlopen(U))["record"].get("trades") or json.load(open(f"/Users/martin/IBS/tester/runs/{R}/trades.json"))
tr = tr if isinstance(tr, list) else tr.get("trades", [])
ends = {}
REF = [o for o in objs if o["k"] == "jss_refine"]
for o in REF + Z:
    ends.setdefault(o["x2"], []).append(o)
touch = P.get("entryModel", "touch") == "touch"
for t in tr:
    od = int(pd.Timestamp(t["open_date"]).value // 10**6) // (tf * 60_000) * (tf * 60_000)   # minúta plnenia -> bar grafu
    zs = ends.get(od, [])
    short = t["is_short"]
    ok = [z for z in zs if (abs(min(z["y1"], z["y2"]) - t["open_rate"]) < 0.26 if short else abs(max(z["y1"], z["y2"]) - t["open_rate"]) < 0.26)]
    if touch and P.get("entryDepthPct", 0) == 0 and not ok:
        err["vstup: nie na hrane zóny"] += 1
    for z in (ok or zs)[:1]:
        top, bot = max(z["y1"], z["y2"]), min(z["y1"], z["y2"])
        s = t.get("initial_stop_loss_abs") or t.get("stop_loss_abs")
        if s is not None and ((short and s < top) or (not short and s > bot)):
            err["vstup: stop nie za zónou"] += 1
print(f"{R}: BOS/CHoCH čiar {len(L)}, zón {len(Z)}, upresnených {len(REF)}, obchodov {len(tr)}")
if REF:   # upresnená zóna leží v zóne TF štruktúry
    zz = {(z["x2"], round(max(z["y1"], z["y2"]), 2)): z for z in Z}
    out_of = sum(1 for r in REF if not any(r["x2"] == z["x2"] and max(r["y1"], r["y2"]) <= max(z["y1"], z["y2"]) + 1e-6
                                            and min(r["y1"], r["y2"]) >= min(z["y1"], z["y2"]) - 1e-6 for z in Z))
    err["upresnená zóna mimo zóny štruktúry"] = out_of
for k, v in err.items():
    print(f"  {k}: {v}")
