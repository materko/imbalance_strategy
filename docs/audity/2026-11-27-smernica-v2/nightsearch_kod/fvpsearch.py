"""FVG POLARITY na MNQ, MGC a BTC: najvyšší WR na poslednom roku (stratégia nemá koniec seansy ani trailing).
python fvpsearch.py <hodiny> — výstup fvp.jsonl"""
import copy, json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
ROOT = Path("/Users/martin/IBS")
LAST = "20250904-20260904"
KEY = "fvgpolarity"
BANDS = [50, 100, 200, 400]
# stop a veľkosť FVG sú v bodoch ceny — mriežka podľa nástroja
PTS = {"mnq_databento": dict(sl=[5, 10, 15, 20, 30, 40, 60, 80, 120, 200, 300], fmin=[0, 2, 5, 10, 15, 20, 30, 50, 80],
                             fmax=[0, 10, 20, 30, 50, 80, 120, 200]),
       "mgc_databento": dict(sl=[0.5, 1, 2, 3, 5, 8, 12, 20, 30, 50], fmin=[0, 0.2, 0.5, 1, 2, 3, 5, 8],
                             fmax=[0, 1, 2, 3, 5, 8, 12, 20]),
       "btcusdt_binance": dict(sl=[50, 100, 150, 200, 300, 500, 800, 1200, 2000, 3000], fmin=[0, 20, 50, 100, 200, 300, 500, 800],
                               fmax=[0, 100, 200, 300, 500, 800, 1200, 2000])}
INSTS = list(PTS)

def space(inst):
    g = PTS[inst]
    return {"_tf": [3, 5, 15, 15, 30, 60], "slPoints": g["sl"], "fvgMinSize": g["fmin"], "fvgMaxSize": g["fmax"],
            "tpLevel": ["near", "mid", "far"], "tradeDirection": ["Both", "Both", "Long only", "Short only"],
            "entryOrderType": ["market", "market", "limit"], "limitOffsetPct": [0, 25, 50, 75, 100],
            "limitValidBars": [1, 2, 3, 5, 10], "limitKeepRR": [False, True], "atrLen": [14]}

def fix(c):
    if c["fvgMaxSize"] and c["fvgMaxSize"] <= c["fvgMinSize"]:
        c["fvgMaxSize"] = 0
    return c

def enc(c):
    p = {k: v for k, v in c.items() if k != "_tf"}
    for k in ("slPoints", "fvgMinSize", "fvgMaxSize"):
        p[k] = {"value": p[k], "unit": "abs"}
    p["_strategy"] = KEY
    return p

def score(r, band):
    if not r:
        return -1e9
    t = r["trades"] or 0
    if t < 20:
        return -300 + t
    s = r["winrate"] - 1.5 * max(0, band - t)
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
    fn = ROOT / ".nightsearch" / "fvp.jsonl"
    if fn.exists():
        for l in open(fn):
            d = json.loads(l); seen[d["inst"]].add(json.dumps(d["p"], sort_keys=True))
            if d["r"]:
                arc[d["inst"]].append((d["p"], d["r"]))
    fh = open(fn, "a"); turn = [0]
    def task():
        inst = INSTS[turn[0] % 3]; turn[0] += 1; S = space(inst)
        for _ in range(300):
            b = random.choice(BANDS)
            top = sorted(arc[inst], key=lambda x: -score(x[1], b))[:20] if len(arc[inst]) >= 200 else []
            if not top or random.random() < 0.1:
                c = {k: random.choice(v) for k, v in S.items()}
            else:
                c = copy.deepcopy(random.choices(top, weights=[1 / (i + 1) ** .7 for i in range(len(top))])[0][0])
                for _ in range(random.choice([1, 1, 2, 3])):
                    k = random.choice(list(S)); vals = S[k]; cur = c.get(k)
                    if isinstance(vals[0], (int, float)) and not isinstance(vals[0], bool) and cur in vals and random.random() < 0.7:
                        i = vals.index(cur) + random.choice([-1, 1]); c[k] = vals[max(0, min(len(vals) - 1, i))]
                    else:
                        c[k] = random.choice(vals)
            c = fix(c); s = json.dumps(c, sort_keys=True)
            if s not in seen[inst]:
                seen[inst].add(s); return inst, c
        return inst, c
    n = 0
    with ProcessPoolExecutor(int(os.environ.get("ALL_WORKERS", "8"))) as ex:
        pend = {ex.submit(work, *task()) for _ in range(16)}
        while pend:
            done, pend = wait(pend, return_when=FIRST_COMPLETED)
            for f in done:
                inst, c, r, err = f.result()
                fh.write(json.dumps({"inst": inst, "p": c, "r": r, "err": err}) + "\n"); fh.flush(); n += 1
                if r:
                    arc[inst].append((c, r))
                if time.time() < deadline:
                    pend.add(ex.submit(work, *task()))
            if n % 500 == 0:
                line = [time.strftime("%H:%M"), str(n)]
                for i in INSTS:
                    for b in BANDS:
                        if arc[i]:
                            x = max(arc[i], key=lambda x: score(x[1], b))
                            line.append(f"{i[:3]}{b}:{x[1]['trades']}/{x[1]['winrate']}/po{x[1]['payoff_r']}")
                print(" ".join(line), flush=True)

if __name__ == "__main__":
    main(float(sys.argv[1]))
