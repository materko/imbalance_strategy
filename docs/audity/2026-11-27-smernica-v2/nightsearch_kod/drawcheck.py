"""Kontrola kresieb Liquidity: sedia čiary a štítky s cenou?

python drawcheck.py <run_id>

Overí na 5m sviečkach (rovnaké pravidlo skladania ako graf):
 1. čiara likvidity je vodorovná a x2 >= x1,
 2. po potvrdení swingu ju cena pred koncom neprerazí (inak ide cez sviečky),
 3. ak skončila skôr ako dáta a nie vypršaním, na poslednom bare ju cena naozaj prerazila,
 4. z jedného swingu (strana + čas + cena) nevedie viac čiar,
 5. štítky sweep/prerazenie sedia na bare, kde cena nejakú likviditu prerazila.
"""
import json, sys, urllib.request, time
import numpy as np
import pandas as pd
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
run = json.load(urllib.request.urlopen(U))["record"]
tf = int(run["settings"]["timeframe"].rstrip("m"))
piv = int(run["params"].get("liqPivotLen", 5))
max_age = int(run["params"].get("liqMaxAgeHours", 120)) * 3_600_000
sweep_bars = int(run["params"].get("sweepBars", 3))
objs = json.load(urllib.request.urlopen(U + "/chart?from=0&to=99999999999999"))["objects"]
m1 = pd.read_feather(engines.one_minute_file(INSTRUMENTS["mnq_databento"]))
b = resample_ohlcv(m1, tf)
t = b.date.astype("int64").to_numpy() // 10**6
hi, lo = b.high.to_numpy(), b.low.to_numpy()
step = tf * 60_000
L = [o for o in objs if o["k"] in ("liq_buy", "liq_sell")]
last_t = t[np.searchsorted(t, max(o["x2"] for o in L)) - 1] if L else 0
err = {"koniec mimo sviecky vybratia": 0, "nie vodorovna": 0, "ide cez cenu": 0, "koniec bez prerazenia": 0, "duplicitny swing": 0}
seen = {}
for o in L:
    buy = o["k"] == "liq_buy"
    y = o["y1"]
    if o["y1"] != o["y2"] or o["x2"] < o["x1"]:
        err["nie vodorovna"] += 1
        continue
    tfs = o["tx"].split()[1]
    ltf = int(tfs[:-1]) * (60 if tfs.endswith("h") else 1)
    a = np.searchsorted(t, o["x1"] + (piv + 1) * ltf * 60_000)
    e = np.searchsorted(t, o["x2"])              # posledný bar čiary = sviečka, ktorá ju prerazila
    body = slice(a, max(a, e))
    if (buy and (hi[body] > y).any()) or (not buy and (lo[body] < y).any()):
        err["ide cez cenu"] += 1
    if 0 <= e < len(t) and o["x2"] < last_t and e >= a:
        crossed = hi[e] > y if buy else lo[e] < y
        expired = o["x2"] - o["x1"] >= max_age          # vypršanie platnosti (aj po zlúčení)
        if not crossed and not expired:
            err["koniec bez prerazenia"] += 1
            # je prerazenie o bar skôr? potom čiara končí o sviečku neskoro
            if e - 1 >= 0 and ((hi[e - 1] > y) if buy else (lo[e - 1] < y)):
                err["koniec mimo sviecky vybratia"] += 1
    key = (o["k"], o["x1"], y)
    seen[key] = seen.get(key, 0) + 1
err["duplicitny swing"] = sum(1 for v in seen.values() if v > 1)
ev = [o for o in objs if o["k"] == "liq_event"]
ends = {}
for o in L:
    ends.setdefault(o["x2"], []).append(o)
    # čiara musí končiť presne na čase otvorenia sviečky (nie o bar ďalej)

take_bars = sorted(ends)
def near_take(x):
    i = np.searchsorted(take_bars, x, side="right") - 1
    if i < 0:
        return False
    # neskorý sweep: do sweepBars SVIEČOK po prerazení (cez víkend/sviatok je to viac času)
    return 0 <= np.searchsorted(t, x) - np.searchsorted(t, take_bars[i]) <= sweep_bars
bad_ev = sum(1 for o in ev if not near_take(o["x"]))
print(f"{R}: ciar {len(L)}, stitkov {len(ev)}")
for k, v in err.items():
    print(f"  {k}: {v}")
print(f"  stitok mimo baru vybratia: {bad_ev}")
