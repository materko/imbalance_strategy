"""Scalping 3MA + RSI + fraktál na EURUSD, MNQ, MGC a BTC: najlepšie nastavenia na poslednom roku (stratégia nemá koniec seansy ani trailing).
Ciele: najvyšší WR v pásmach počtu obchodov pri reálnom zisk:strata >= 0,9, a najvyšší PF.
python s3search.py <hodiny> — výstup s3.jsonl"""
import copy, json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
ROOT = Path("/Users/martin/IBS")
LAST = "20250904-20260904"
KEY = "scalp3ma"
INSTS = ["eurusd_dukascopy", "mnq_databento", "mgc_databento", "btcusdt_binance"]
OBJ = [60, 100, 150, 200, "pf"]
PTS = {"mnq_databento": [5, 10, 20, 30, 50], "mgc_databento": [1, 2, 3, 5, 8], "btcusdt_binance": [50, 100, 200, 400],
       "eurusd_dukascopy": [0.0003, 0.0005, 0.0008, 0.0012]}
SPACE = {
    "_tf": [2, 3, 5, 5, 15], "ma1Len": [10, 20, 20, 30], "ma2Len": [40, 50, 60, 80], "ma3Len": [100, 150, 200, 200, 300],
    "requireMaOrder": [False, True], "rsiLen": [7, 10, 14, 14, 21], "rsiLevel": [45, 50, 50, 55],
    "rsiExit": [False, False, True], "fractalLen": [2, 2, 3, 5], "fractalSide": ["pullback", "trend", "any"],
    "tradeDirection": ["Both", "Both", "Long only", "Short only"], "maxTradesPerDay": [1, 1, 2, 3, 5, 10],
    "cooldownBars": [0, 3, 6, 12], "useTradeWindow": [False, True, True], "tradeStartH": [0, 2, 3, 8, 9, 10],
    "tradeStartM": [0, 30], "tradeEndH": [11, 12, 15, 16, 20], "tradeEndM": [0, 30],
    "slMode": ["points", "atr", "atr", "fractal"], "slPoints": [0], "slAtr": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
    "slBufferAtr": [0, 0.1, 0.25, 0.5], "rrRatio": [1.0, 1.0, 1.25, 1.5, 2.0], "beAtR": [0, 0, 0, 1.0],
    "entryOrderType": ["market", "market", "limit"], "limitOffsetPct": [25, 50, 75], "limitValidBars": [2, 3, 6],
}
ATR = ("slAtr", "slBufferAtr")

def fix(c, inst=None):
    if c["tradeEndH"] * 60 + c["tradeEndM"] <= c["tradeStartH"] * 60 + c["tradeStartM"]:
        c["tradeEndH"] = 20
    if inst is not None and c["slPoints"] not in PTS[inst]:
        c["slPoints"] = random.choice(PTS[inst])
    return c

def enc(c):
    p = {k: v for k, v in c.items() if k != "_tf"}
    for k in ATR:
        p[k] = {"value": p[k], "unit": "atr"}
    p["slPoints"] = {"value": p["slPoints"], "unit": "abs"}
    p["_strategy"] = KEY
    return p

def score(r, obj):
    if not r:
        return -1e9
    t = r["trades"] or 0
    if t < 30:
        return -300 + t
    if obj == "pf":
        return min(r["profit_factor"], 5.0) * 20 - 1.0 * max(0, 100 - t) - (30 if r["pnl_abs"] <= 0 else 0)
    s = r["winrate"] - 1.0 * max(0, obj - t) - 60 * max(0.0, 0.9 - r.get("payoff_r", 0.0))
    if r["pnl_abs"] <= 0:
        s -= 15
    return s

def work(inst, c):
    from allcore import evaluate
    import io, contextlib
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            r = evaluate(enc(c), int(c["_tf"]), LAST, inst)
        return inst, c, r, None
    except Exception as e:
        return inst, c, None, f"{type(e).__name__}: {e}"[:300]

def main(hours):
    deadline = time.time() + hours * 3600
    arc = {i: [] for i in INSTS}; seen = {i: set() for i in INSTS}
    fn = ROOT / ".nightsearch" / "s3.jsonl"
    if fn.exists():
        for l in open(fn):
            d = json.loads(l); seen[d["inst"]].add(json.dumps(d["p"], sort_keys=True))
            if d["r"]:
                arc[d["inst"]].append((d["p"], d["r"]))
    fh = open(fn, "a"); turn = [0]; top = {}
    def refresh():
        for i in INSTS:
            for o in OBJ:
                top[(i, o)] = sorted(arc[i], key=lambda x: -score(x[1], o))[:20]
    refresh()
    def task():
        inst = INSTS[turn[0] % len(INSTS)]; turn[0] += 1
        for _ in range(300):
            o = random.choice(OBJ); t = top.get((inst, o)) or []
            if len(arc[inst]) < 300 or random.random() < 0.08 or len(t) < 5:
                c = {k: random.choice(v) for k, v in SPACE.items()}
            else:
                c = copy.deepcopy(random.choices(t, weights=[1 / (i + 1) ** .7 for i in range(len(t))])[0][0])
                for _ in range(random.choice([1, 1, 2, 2, 3, 4])):
                    k = random.choice(list(SPACE)); vals = SPACE[k]; cur = c.get(k)
                    if isinstance(vals[0], (int, float)) and not isinstance(vals[0], bool) and cur in vals and random.random() < 0.7:
                        j = vals.index(cur) + random.choice([-1, 1]); c[k] = vals[max(0, min(len(vals) - 1, j))]
                    else:
                        c[k] = random.choice(vals)
                if k == 'slPoints' or c.get('slPoints') not in PTS[inst]:
                    c['slPoints'] = random.choice(PTS[inst])
            c = fix(c, inst); s = json.dumps(c, sort_keys=True)
            if s not in seen[inst]:
                seen[inst].add(s); return inst, c
        return inst, c
    n = 0
    with ProcessPoolExecutor(int(os.environ.get("ALL_WORKERS", "6"))) as ex:
        pend = {ex.submit(work, *task()) for _ in range(12)}
        while pend:
            done, pend = wait(pend, return_when=FIRST_COMPLETED)
            for f in done:
                inst, c, r, err = f.result()
                fh.write(json.dumps({"inst": inst, "p": c, "r": r, "err": err}) + "\n"); fh.flush(); n += 1
                if r:
                    arc[inst].append((c, r))
                if time.time() < deadline:
                    pend.add(ex.submit(work, *task()))
            if n % 300 == 0:
                refresh()
                line = [time.strftime("%H:%M"), str(n)]
                for i in INSTS:
                    for o in OBJ:
                        if top[(i, o)]:
                            x = top[(i, o)][0][1]
                            line.append(f"{i[:3]}{o}:{x['trades']}/{x['winrate']}/pf{x['profit_factor']}")
                print(" ".join(line), flush=True)

if __name__ == "__main__":
    main(float(sys.argv[1]))
