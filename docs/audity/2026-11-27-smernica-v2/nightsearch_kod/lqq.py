"""Liquidity sweep RR 0.5: filtre kvality zón, cieľ ~200 obchodov a 80-85 % WR na poslednom roku.
python lqq.py <minuty> — 5 procesov (šetrí RAM)."""
import json, random, sys, time, copy, math
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
import liqsearch as L
ROOT = Path("/Users/martin/IBS")
OUT = ROOT / ".nightsearch" / "lqq.jsonl"
DEADLINE = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 0) * 60
LAST, PREV = L.W5[-1], L.W5[-2]
SPACE = dict(L.SPACE)
SPACE["tradeMode"] = ["sweep"]
SPACE.update({
    "liqMinAgeBars": [0, 0, 6, 12, 24, 48, 96], "sweepMinDepthAtr": [0, 0, 0.05, 0.1, 0.2, 0.3],
    "sweepMaxDepthAtr": [0, 0, 0.5, 0.75, 1.0, 1.5, 2.0], "sweepVolMult": [0, 0, 1.0, 1.2, 1.5, 2.0],
    "trendFilter": ["off", "off", "with", "against"], "trendEmaLen": [20, 50, 100, 200],
    "liqMinStrength": [1, 1, 2], "rrRatio": [0.5],
})
L.SPACE = SPACE
ATR = ("sweepMinDepthAtr", "sweepMaxDepthAtr")

def enc(c):
    p = L.enc(c)
    for k in ATR:
        p[k] = {"value": p[k], "unit": "atr"}
    p["showOnlyQuality"] = True
    return p

def score(r):
    a, b = r["last"], r.get("prev")
    t = a["trades"] or 0
    if t < 120:
        return -100 + t * 0.5
    s = a["winrate"] - 0.2 * max(0, 180 - t) - 0.05 * max(0, t - 260)
    if b and b["trades"]:
        s += 0.25 * min(0, b["winrate"] - 75)   # predchádzajúci rok nesmie byť slabý
    if a["pnl_abs"] <= 0:
        s -= 10
    return s

def work(c):
    from evalcore import evaluate
    import io, contextlib
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            p = enc(c)
            r = {"last": evaluate(p, int(c["_tf"]), LAST)}
            if r["last"]["trades"] >= 120 and r["last"]["winrate"] >= 74:
                r["prev"] = evaluate(p, int(c["_tf"]), PREV)
        return c, r, None
    except Exception as e:
        return c, None, f"{type(e).__name__}: {e}"[:300]

def main():
    user = json.load(open(ROOT / "tester/runs/20260928-041040-ea877a/run.json"))["params"]
    base = {**L.BASE, "_tf": 5}
    for k in SPACE:
        if k in user:
            v = user[k]; base[k] = v["value"] if isinstance(v, dict) else v
    base.update(liqMinAgeBars=0, sweepMinDepthAtr=0, sweepMaxDepthAtr=0, sweepVolMult=0, trendFilter="off",
                trendEmaLen=50, rrRatio=0.5)
    arc, seen = [], set()
    if OUT.exists():
        for l in OUT.read_text().splitlines():
            d = json.loads(l); seen.add(json.dumps(d["p"], sort_keys=True))
            if d["r"]:
                arc.append((score(d["r"]), d["p"], d["r"]))
    queue = [base] if not arc else []
    def task():
        for _ in range(100):
            if queue:
                c = queue.pop(0)
            elif len(arc) < 5:
                c = L.mutate(base)
            else:
                top = sorted(arc, key=lambda x: -x[0])[:20]
                if random.random() < 0.15:
                    x, y = random.sample(top, 2)
                    c = L.fix({k: (x[1][k] if random.random() < .5 else y[1].get(k, x[1][k])) for k in x[1]})
                c = L.mutate(random.choices(top, weights=[1 / (i + 1) ** .7 for i in range(len(top))])[0][1])
            c["rrRatio"] = 0.5; c["tradeMode"] = "sweep"
            k = json.dumps(c, sort_keys=True)
            if k not in seen:
                seen.add(k); return c
        return c
    n = 0
    with ProcessPoolExecutor(5) as ex, open(OUT, "a") as fh:
        pend = {ex.submit(work, task()) for _ in range(8)}
        while pend:
            done, pend = wait(pend, return_when=FIRST_COMPLETED)
            for f in done:
                c, r, err = f.result()
                s = score(r) if r else None
                fh.write(json.dumps({"p": c, "r": r, "s": s, "err": err}) + "\n"); fh.flush(); n += 1
                if r:
                    arc.append((s, c, r))
                if time.time() < DEADLINE:
                    pend.add(ex.submit(work, task()))
            if n % 100 == 0 and arc:
                b = max(arc, key=lambda x: x[0])[2]
                print(time.strftime("%H:%M"), n, b["last"]["trades"], b["last"]["winrate"],
                      (b.get("prev") or {}).get("winrate"), flush=True)

if __name__ == "__main__":
    main()
