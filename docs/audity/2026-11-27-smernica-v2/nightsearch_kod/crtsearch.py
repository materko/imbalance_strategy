"""CRT + TBS na MNQ, MGC a BTC: najlepšie nastavenia na poslednom roku (stratégia nemá koniec seansy ani trailing).
Ciele: najvyšší WR v pásmach počtu obchodov pri reálnom zisk:strata >= 0,9, a najvyšší PF.
python crtsearch.py <hodiny> — výstup crt.jsonl"""
import copy, json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
ROOT = Path("/Users/martin/IBS")
LAST = "20250904-20260904"
KEY = "crt"
INSTS = ["mnq_databento", "mgc_databento", "btcusdt_binance"]
OBJ = [60, 100, 150, 200, "pf"]
SPACE = {
    "_tf": [3, 5, 5, 15], "rangeTF": [60, 120, 240, 240, 480], "rangeMinAtr": [0, 0, 0.5, 0.75, 1.0],
    "rangeMaxAtr": [0, 0, 1.5, 2.0, 3.0], "sweepWithinBars": [1, 1, 2], "validBars": [1, 2, 2, 3],
    "requireHtfClose": [False, False, True], "requireOldHL": [False, False, True], "keyLookback": [3, 6, 12, 24],
    "sweepKind": ["body", "wick", "any"], "sweepMaxAtr": [0, 0, 1.0, 2.0, 4.0],
    "entryModel": ["model1", "cisd", "mss_fvg"], "swingLen": [2, 3, 5], "fvgValidBars": [3, 6, 12],
    "tradeDirection": ["Both", "Both", "Long only", "Short only"], "maxTradesPerDay": [1, 2, 3, 5],
    "useTradeWindow": [False, True, True], "tradeStartH": [0, 2, 3, 8, 9, 10], "tradeStartM": [0, 30],
    "tradeEndH": [11, 12, 15, 16, 20], "tradeEndM": [0, 30],
    "slBufferAtr": [0, 0.05, 0.1, 0.25, 0.5, 1.0], "tpMode": ["mid", "opposite", "rr"],
    "rrRatio": [1.0, 1.25, 1.5, 2.0, 3.0], "minRR": [0.5, 0.75, 1.0, 1.5, 2.0],
    "entryOrderType": ["market", "market", "limit"], "limitOffsetPct": [25, 50, 75], "limitValidBars": [2, 3, 6],
}
ATR = ("rangeMinAtr", "rangeMaxAtr", "sweepMaxAtr", "slBufferAtr")

def fix(c):
    if c["validBars"] < c["sweepWithinBars"]:
        c["validBars"] = c["sweepWithinBars"]
    if c["rangeMaxAtr"] and c["rangeMinAtr"] >= c["rangeMaxAtr"]:
        c["rangeMaxAtr"] = 0
    if c["tradeEndH"] * 60 + c["tradeEndM"] <= c["tradeStartH"] * 60 + c["tradeStartM"]:
        c["tradeEndH"] = 20
    if c["rangeTF"] % c["_tf"]:
        c["_tf"] = 5
    return c

def enc(c):
    p = {k: v for k, v in c.items() if k != "_tf"}
    for k in ATR:
        p[k] = {"value": p[k], "unit": "atr"}
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
    fn = ROOT / ".nightsearch" / "crt.jsonl"
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
            c = fix(c); s = json.dumps(c, sort_keys=True)
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
