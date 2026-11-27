"""Hladanie Divergence na MNQ: zisk stabilny na poslednych dvoch rokoch, dost obchodov."""
import json, random, sys, time, copy, os
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
ROOT = Path("/Users/martin/IBS")
OUT = ROOT / ".nightsearch" / "div2.jsonl"
TR, PREV = "20250904-20260904", "20240904-20250904"
DEADLINE = time.time() + float(sys.argv[1]) * 3600
B = [True, False]
IND = [f"div{n}{s}" for s in ("Long", "Short") for n in ("Macd", "MacdHist", "Rsi", "Stoch", "Cci", "Mom", "Obv", "Vwmacd", "Cmf", "Mfi", "Cdv")]
SPACE = {
    "_tf": [3, 5, 10, 15, 30],
    "prd": [2, 3, 4, 5, 6, 8, 10], "source": ["close", "high/low"],
    "searchDiv": ["regular", "hidden", "regular/hidden"], "maxPp": [3, 5, 8, 10, 15],
    "maxBars": [50, 100, 150, 200, 300], "dontConfirm": B,
    "minDivsLong": [1, 1, 2, 3, 4], "minDivsShort": [1, 1, 2, 3, 4], "signalBars": [1, 2, 3, 4, 6],
    **{k: B for k in IND},
    "stLen": [5, 7, 10, 14, 20], "stMult": [1.5, 2, 3, 4, 5],
    "htfMinutes": [15, 30, 60, 120, 240], "htf2Minutes": [60, 120, 240, 480, 1440],
    "stMultHtf": [1.5, 2, 2.5, 3, 3.5, 5], "pullbackFilter": B,
    "rsiLen": [7, 10, 14, 21], "rsiLongMax": [40, 50, 55, 60, 70, 80, 100], "rsiShortMin": [0, 20, 30, 40, 45, 50, 60],
    "zoneFilter": B, "zoneSearchDiv": ["regular", "hidden", "regular/hidden"],
    "zonePrd1": [3, 5, 8], "zoneWindow1": [3, 6, 12, 24], "zonePrd2": [2, 3, 5], "zoneWindow2": [10, 22, 44, 88],
    "tradeDirection": ["Both", "Both", "Long only", "Short only"], "entryMode": ["confirm", "immediate"],
    "atrLen": [7, 10, 14, 21], "slAtrMult": [0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5],
    "rrRatio": [0, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4],
    "trendExit": B, "enableTrailing": B,
    "beActivationPct": [0.1, 0.15, 0.2, 0.3, 0.5, 0.8, 1.2], "beLockPct": [0.02, 0.05, 0.08, 0.1, 0.2],
    "trailActivationPct": [0.2, 0.3, 0.5, 0.8, 1.2, 2], "trailOffsetPct": [0.05, 0.1, 0.15, 0.25, 0.4, 0.6],
    "maxHoldBars": [0, 0, 20, 40, 80, 160],
}
BASE = {"_strategy": "divergence", "_instrument": "mnq_databento", "_tf": 15, "leverage": 1.0}


def fix(c):
    if c["htf2Minutes"] < c["htfMinutes"]:
        c["htf2Minutes"] = c["htfMinutes"]
    for m in ("htfMinutes", "htf2Minutes"):  # HTF musí byť násobkom TF grafu
        if c[m] % c["_tf"]:
            c[m] = max(c["_tf"], c[m] // c["_tf"] * c["_tf"])
    if c["beLockPct"] >= c["beActivationPct"]:
        c["beLockPct"] = round(c["beActivationPct"] / 3, 3)
    for s in ("Long", "Short"):
        if not any(c[f"div{n}{s}"] for n in ("Macd", "MacdHist", "Rsi", "Stoch", "Cci", "Mom", "Obv", "Vwmacd", "Cmf", "Mfi", "Cdv")):
            c[f"divRsi{s}"] = True
    return c


def rand_cfg():
    return fix({**BASE, **{k: random.choice(v) for k, v in SPACE.items()}})


def mutate(p):
    c = copy.deepcopy(p)
    for _ in range(random.choice([1, 1, 2, 2, 3, 4])):
        k = random.choice(list(SPACE)); vals = SPACE[k]; cur = c.get(k)
        if isinstance(vals[0], (int, float)) and not isinstance(vals[0], bool) and cur in vals and random.random() < 0.7:
            i = vals.index(cur) + random.choice([-1, 1]); c[k] = vals[max(0, min(len(vals) - 1, i))]
        else:
            c[k] = random.choice(vals)
    return fix(c)


def score(r):
    if not r or r.get("trades") is None:
        return -1e9
    t = r["trades"]
    if t < 25:
        return -5000 + t * 10 + (r["pnl_abs"] or 0) / 100
    p = r.get("prev")
    s = r["pnl_abs"]
    if p:
        s = min(r["pnl_abs"], p["pnl_abs"]) * 1.5 + max(r["pnl_abs"], p["pnl_abs"]) * 0.5
        if p["trades"] < 20:
            s -= 3000
    else:
        s -= 4000
    return s / 100 - (r["max_drawdown_pct"] or 0) * 2


def work(params):
    from evalcore import evaluate
    import io, contextlib
    try:
        p = {k: v for k, v in params.items() if k != "_tf"}
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            r = evaluate(p, int(params["_tf"]), TR, fee="market")
            if r["trades"] >= 25 and (r["pnl_abs"] or 0) > 0:
                r["prev"] = evaluate(p, int(params["_tf"]), PREV, fee="market")
        return params, r, None
    except Exception as e:
        return params, None, f"{type(e).__name__}: {e}"[:300]


def main():
    arc, seen = [], set()
    if OUT.exists():
        for l in OUT.read_text().splitlines():
            d = json.loads(l)
            seen.add(json.dumps(d["p"], sort_keys=True))
            if d["r"]:
                arc.append((score(d["r"]), d["p"], d["r"]))

    if not arc:
        old = [json.loads(l) for l in open(ROOT / ".nightsearch" / "div.jsonl")]
        old = [d for d in old if d["r"] and d["r"].get("prev")]
        old.sort(key=lambda d: -score(d["r"]))
        queue = [d["p"] for d in old[:40]]
    else:
        queue = []

    def task():
        if queue:
            c = queue.pop(0); seen.add(json.dumps(c, sort_keys=True)); return c
        for _ in range(100):
            if len(arc) < 60 or random.random() < 0.12:
                c = rand_cfg()
            else:
                top = sorted(arc, key=lambda x: -x[0])[:30]
                if random.random() < 0.15:
                    a, b = random.sample(top, 2)
                    c = fix({k: (a[1][k] if random.random() < 0.5 else b[1].get(k, a[1][k])) for k in a[1]})
                    c = mutate(c)
                else:
                    c = mutate(random.choices(top, weights=[1 / (i + 1) ** 0.7 for i in range(len(top))])[0][1])
            k = json.dumps(c, sort_keys=True)
            if k not in seen:
                seen.add(k); return c
        return c

    n = 0
    with ProcessPoolExecutor(9) as ex, open(OUT, "a") as fh:
        pend = {ex.submit(work, task()) for _ in range(9)}
        while pend:
            done, pend = wait(pend, return_when=FIRST_COMPLETED)
            for f in done:
                p, r, err = f.result()
                fh.write(json.dumps({"p": p, "r": r, "err": err}) + "\n"); fh.flush(); n += 1
                if r:
                    arc.append((score(r), p, r))
                if time.time() < DEADLINE:
                    pend.add(ex.submit(work, task()))
            if n % 50 == 0 and arc:
                b = max(arc, key=lambda x: x[0])
                print(time.strftime("%H:%M"), n, "best", round(b[0], 1), b[2]["trades"], b[2]["winrate"], round(b[2]["pnl_abs"]),
                      b[2].get("prev") and (b[2]["prev"]["trades"], round(b[2]["prev"]["pnl_abs"])), flush=True)


if __name__ == "__main__":
    main()
