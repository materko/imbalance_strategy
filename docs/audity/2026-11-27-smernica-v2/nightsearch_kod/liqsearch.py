"""Liquidity: pre kazde RR najvyssi WR pri co najviac obchodoch. MNQ, bez nakladov.

python tlsearch.py <hodiny> <vystup.jsonl> [5y]
"""
import json, random, sys, time, copy, math, os
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
ROOT = Path("/Users/martin/IBS")
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 1.5
OUT = ROOT / ".nightsearch" / (sys.argv[2] if len(sys.argv) > 2 else "tl1.jsonl")
FIVE = len(sys.argv) > 3 and sys.argv[3] == "5y"
DEADLINE = time.time() + HOURS * 3600
W5 = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904"]
RRS = [float(x) for x in os.environ.get("LQ_RRS", "0.5,0.75,1.0,1.25,1.5,2.0,2.5,3.0").split(",")]
B = [True, False]
SPACE = {
    "_tf": [5, 5, 15],
    "liqUse5m": [True, False, False], "liqUse15m": [True, False], "liqUse30m": [True, False],
    "liqUse60m": [True, False], "liqUse240m": [True, False, False],
    "liqPivotLen": [2, 3, 5, 8, 10], "liqMinDispAtr": [0, 0.5, 1.0, 1.5, 2.0, 3.0],
    "liqEqualTolAtr": [0.05, 0.1, 0.15, 0.25], "liqMaxAgeHours": [24, 72, 120, 240],
    "liqMinStrength": [1, 1, 1, 2],
    "tradeMode": [os.environ.get("LQ_MODE", "sweep")], "tradeDirection": ["Both", "Both", "Long only", "Short only"],
    "breakBufferAtr": [0, 0.05, 0.1, 0.2, 0.3], "sweepBars": [1, 2, 3, 5, 8],
    "entryModel": ["imbalance", "pinbar", "any", "close"], "entryOrder": ["market", "market", "limit"],
    "setupMaxBars": [1, 2, 3, 4, 6, 10],
    "entryMaxDistAtr": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0], "imbMinSizeAtr": [0.05, 0.1, 0.2, 0.3, 0.5],
    "pbWickPct": [40, 50, 60, 70], "pbBodyPct": [15, 25, 35],
    "maxTradesPerDay": [2, 3, 5, 10, 20], "cooldownBars": [0, 1, 3, 6],
    "weekdaysOnly": [True, False], "useTradeWindow": [False, True, True],
    "tradeStartH": [2, 3, 8, 9, 10], "tradeStartM": [0, 30], "tradeEndH": [11, 12, 15, 16], "tradeEndM": [0, 30],
    "slMode": ["level", "signal", "swing", "atr"],
    "slBufferAtr": [0, 0.1, 0.2, 0.3, 0.5, 1.0], "slAtrMult": [0.5, 0.75, 1, 1.5, 2, 3],
    "slLookback": [2, 3, 5, 8, 12], "minSlDistance": [0, 0, 0.02, 0.05, 0.1],
}
BASE = {"_strategy": "liquidity", "_instrument": "mnq_databento", "riskDollar": 100.0, "tpMode": "rr"}


def fix(c):
    tf = c["_tf"]
    ok = [m for m in (5, 15, 30, 60, 240) if c[f"liqUse{m}m"] and m >= tf and m % tf == 0]
    if not ok:
        c[f"liqUse{random.choice([15, 60] if tf <= 15 else [60])}m"] = True
    if c["tradeEndH"] * 60 + c["tradeEndM"] <= c["tradeStartH"] * 60 + c["tradeStartM"]:
        c["tradeEndH"] = 16
    if c["pbWickPct"] + c["pbBodyPct"] > 100:
        c["pbBodyPct"] = 100 - c["pbWickPct"]
    return c


def enc(c):
    p = {k: v for k, v in c.items() if k != "_tf"}
    for k in ("liqMinDispAtr", "liqEqualTolAtr", "breakBufferAtr", "entryMaxDistAtr", "imbMinSizeAtr", "slBufferAtr", "slAtrMult"):
        p[k] = {"value": p[k], "unit": "atr"}
    p["minSlDistance"] = {"value": p["minSlDistance"], "unit": "pct"}
    return p


def rand_cfg(rr):
    return fix({**BASE, **{k: random.choice(v) for k, v in SPACE.items()}, "rrRatio": rr})


def mutate(p):
    c = copy.deepcopy(p)
    for _ in range(random.choice([1, 1, 2, 2, 3, 4])):
        k = random.choice(list(SPACE)); vals = SPACE[k]; cur = c.get(k)
        if isinstance(vals[0], (int, float)) and not isinstance(vals[0], bool) and cur in vals and random.random() < 0.7:
            i = vals.index(cur) + random.choice([-1, 1]); c[k] = vals[max(0, min(len(vals) - 1, i))]
        else:
            c[k] = random.choice(vals)
    return fix(c)


def be_wr(rr):
    return 100.0 / (1.0 + rr)


def score1(r, rr):
    """Jeden rok: WR nad hranicou ziskovosti daného RR a čo najviac obchodov (aspoň 100)."""
    if not r:
        return -1e9
    t = r["trades"] or 0
    if t < 60:
        return -200 + t
    # cieľ 300-500 obchodov za rok: pod 300 trest, bonus za počet rastie do 600
    s = (r["winrate"] - be_wr(rr)) * 3 + 25 * math.log10(min(t, 600) / 100) - 0.4 * max(0, 300 - t)
    if r["pnl_abs"] <= 0:
        s -= 15
    return s


def score(r, rr):
    """Vysoký WR nad hranicou ziskovosti pri čo najviac obchodoch."""
    if not r:
        return -1e9
    if FIVE:
        ws = r.get("w5")
        if not ws:
            return -1e6 + (r["trades"] or 0)
        tr = sum(w["trades"] for w in ws); wins = sum(w["wins"] for w in ws)
        wr = 100.0 * wins / max(tr, 1)
        neg = sum(1 for w in ws if w["pnl_abs"] <= 0)
        per_year = tr / 5
        if per_year < 60:
            return -200 + per_year
        if os.environ.get("LQ_SCORE") == "wr":   # WR má prednosť, obchodov stačí 100+ za rok
            hi = float(os.environ.get("LQ_MAX_TR", "600"))
            return ((wr - be_wr(rr)) * 3 + 5 * math.log10(min(per_year, hi) / 100)
                    - 0.4 * max(0, float(os.environ.get("LQ_MIN_TR", "200")) - per_year) - 8 * neg)
        return ((wr - be_wr(rr)) * 3 + 25 * math.log10(min(per_year, 600) / 100)
                - 0.4 * max(0, 300 - per_year) - 8 * neg)
    return score1(r, rr)


def work(c):
    from evalcore import evaluate
    import io, contextlib
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            p = enc(c)
            r = evaluate(p, int(c["_tf"]), W5[-1], fee=None)
            if FIVE and r["trades"] >= (60 if os.environ.get("LQ_SCORE") == "wr" else 150) and r["pnl_abs"] > 0:
                r["w5"] = [evaluate(p, int(c["_tf"]), w, fee=None) for w in W5[:-1]] + [dict(r)]
        return c, r, None
    except Exception as e:
        return c, None, f"{type(e).__name__}: {e}"[:300]


def main():
    arc = {rr: [] for rr in RRS}
    seen = set()
    if OUT.exists():
        for l in OUT.read_text().splitlines():
            d = json.loads(l); seen.add(json.dumps(d["p"], sort_keys=True))
            if d["r"]:
                arc[d["p"]["rrRatio"]].append((score(d["r"], d["p"]["rrRatio"]), d["p"], d["r"]))
    queue = []
    seedf = os.environ.get("TL_SEED")
    if seedf and not any(arc.values()):
        old = [json.loads(l) for l in open(ROOT / ".nightsearch" / seedf)]
        old = [d for d in old if d["r"]]
        for rr in RRS:
            g = sorted([d for d in old if d["p"]["rrRatio"] == rr], key=lambda d: -score1(d["r"], rr))
            if len(g) < 10:   # málo semien pre toto RR — vezmi aj iné RR a prepni ich
                g += [dict(d, p=dict(d["p"], rrRatio=rr)) for d in sorted(old, key=lambda d: -score1(d["r"], d["p"]["rrRatio"]))[:15]]
            queue += [d["p"] for d in g[:15]]
    turn = [0]

    def task():
        for _ in range(100):
            if queue:
                c = queue.pop(0)
            else:
                rr = RRS[turn[0] % len(RRS)]; turn[0] += 1
                a = arc[rr]
                if len(a) < 40 or random.random() < 0.1:
                    c = rand_cfg(rr)
                else:
                    top = sorted(a, key=lambda x: -x[0])[:25]
                    if random.random() < 0.15:
                        x, y = random.sample(top, 2)
                        c = fix({k: (x[1][k] if random.random() < 0.5 else y[1].get(k, x[1][k])) for k in x[1]})
                        c = mutate(c)
                    else:
                        c = mutate(random.choices(top, weights=[1 / (i + 1) ** 0.7 for i in range(len(top))])[0][1])
                    # obcas skus rovnaky setup pri susednom RR
                    if random.random() < 0.1:
                        c["rrRatio"] = random.choice(RRS)
                    c["rrRatio"] = c["rrRatio"] if c["rrRatio"] in RRS else RRS[0]
            k = json.dumps(c, sort_keys=True)
            if k not in seen:
                seen.add(k); return c
        return c

    n = 0
    with ProcessPoolExecutor(9) as ex, open(OUT, "a") as fh:
        pend = {ex.submit(work, task()) for _ in range(18)}
        while pend:
            done, pend = wait(pend, return_when=FIRST_COMPLETED)
            for f in done:
                c, r, err = f.result()
                s = score(r, c["rrRatio"]) if r else None
                fh.write(json.dumps({"p": c, "r": r, "s": s, "err": err}) + "\n"); fh.flush(); n += 1
                if r:
                    arc[c["rrRatio"]].append((s, c, r))
                if time.time() < DEADLINE:
                    pend.add(ex.submit(work, task()))
            if n % 200 == 0:
                line = [time.strftime("%H:%M"), str(n)]
                for rr in RRS:
                    if arc[rr]:
                        b = max(arc[rr], key=lambda x: x[0])[2]
                        line.append(f"RR{rr}:{b['trades']}/{b['winrate']}")
                print(" ".join(line), flush=True)


if __name__ == "__main__":
    main()
