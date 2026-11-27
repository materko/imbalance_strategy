"""Nocne hladanie: max obchodov pri WR>=80 %, RRR>=0.5, bez S/R, LQ a engulfingu. MNQ, posledny rok."""
import json, random, sys, time, copy, os, traceback
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")

ROOT = Path("/Users/martin/IBS")
OUT = ROOT / ".nightsearch" / os.environ.get("NS_OUT", "stageA.jsonl")
TR = "20250904-20260904"
DEADLINE = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 9.5) * 3600
WORKERS = 9

FIXED = {"enableSrTrading": False, "enableLqTrading": False, "enableEngulfingEntry": False,
         "enableTrading": True, "leverage": 1.0, "enableFvgTrading": True}
SEEDS = ["NOCNE_TESTY_A_max_winrate", "NOCNE_TESTY_B_stabilita", "SD_IMB_80wr_378obch_1rok",
         "MNQ_R05_WR80_najviac", "MNQ_R05_WR80_najzisk", "MNQ_R05_WR80_najlepsi_pomer",
         "MNQ_R05_WR797_jednoduchy", "MNQ_WR70_zoneTF5"]
MODES = {
    "fvg": {"enableFvgTrading": True, "enableIfvgTrading": False},
    "ifvg": {"enableFvgTrading": False, "enableIfvgTrading": True},
    "both": {"enableFvgTrading": True, "enableIfvgTrading": True},
}
SD = os.environ.get("NS_SD", "0") == "1"
for _m in MODES.values():
    _m["enableZoneDetection"] = SD
SUFFIX = {m: "entry" for m in os.environ.get("NS_MODES", "fvg,ifvg,both").split(",")}

R = lambda a, b: list(range(a, b + 1))
SPACE = {
    "_tf": [2, 3, 4, 5],
    "zoneDetectionTF": ["1", "3", "5", "15"],
    "zoneValidHours": R(1, 12) + [16, 24],
    "minImbSizePoints": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14],
    "imbLookback": [3, 5, 8, 10, 15, 20, 25, 30],
    "imbMaxDistTicks": [10, 20, 30, 40, 60, 80, 100, 150, 200],
    "state1MaxBars": R(1, 12), "state2MaxBars": R(2, 15), "state2ConfirmTicks": [0, 1, 2, 4, 6, 8, 12],
    "state3MaxBars": R(1, 6), "state4MaxBars": R(2, 15), "state5MaxBars": R(1, 8),
    "rrRatio": [0.5, 0.5, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8],
    "slLookback": [3, 5, 8, 10, 12, 15, 20, 25, 30], "slBufferTicks": [0, 2, 4, 6, 8, 12, 16],
    "maxDailyWins": R(1, 20),
    "enablePinBarEntry": [True, False], "enableImbEntry": [True, True, False],
    "pbWickToBodyRatio": [1.5, 2, 2.5, 3, 4, 5, 6, 8], "pbBodyPositionPct": [10, 15, 20, 25, 30, 35, 40],
    "pbMinRangePoints": [0, 1, 2, 3, 4, 6, 8, 10], "pbEngOrderType": ["Limit", "Market", "Stop"],
    "tradeDirection": ["Both", "Indicator"],
    "indAdx": [True, False], "adxTimeframe": ["15", "30", "60", "120", "240"],
    "adxThreshold": [5, 8, 10, 12, 15, 18, 20, 25, 30], "adxDiLength": [7, 10, 14, 20, 28],
    "adxSmoothing": [3, 5, 7, 10, 14],
    "ruleAdxSide": ["Both", "No trade"], "ruleAdxUp": ["Both", "Long only"], "ruleAdxDown": ["Both", "Short only"],
    "indSupertrend": [True, False], "stTimeframe": ["15", "60", "240"], "stMultiplier": [1.5, 2, 3, 3.5, 5],
    "ruleStUp": ["Both", "Long only"], "ruleStDown": ["Both", "Short only"],
    "minSlDistance": [0, 0.05, 0.08, 0.1, 0.13, 0.15, 0.18, 0.22, 0.3],
    "sess1On": [True, False], "sess2On": [True, True, False], "sess3On": [True, False],
    "_sess": ["shift"],
    "useStructureFilter": [True, False], "useVolumeFilter": [False, False, True],
    "volumeFilterBlockTrading": [True, False],
    "enableGapDetection": [True, False], "invalidateOnFill": [True, False],
    "snapMode": ["Off", "Floor", "Ceil", "Round"], "closeAtSessionEnd": [True, False],
    "weekdaysOnly": [True, False],
    "enableTrailing": [False, False, True], "trailActivationR": [0.3, 0.5, 0.8, 1.0], "trailOffsetR": [0.2, 0.3, 0.5],
    "maxSdZones": [50, 100, 200, 400],
}
ENTRY_SPACE = {"fvgUse5m": [True, False], "fvgUse15m": [True, False],
               "fvgUse30m": [True, False], "fvgUse60m": [True, False],
               "enableZoneDetection": [True, True, False],
               "fvgMinSize": ["1", "2", "3", "4", "5", "6", "8", "10", "12", "15", "20", "25", "30", "40",
                              "0.1@atr", "0.25@atr", "0.5@atr", "0.75@atr", "1@atr", "1.5@atr", "2@atr", "3@atr"],
               "fvgMinSize2": ["x"]}


def load_seed(name, strat):
    d = json.loads((ROOT / "tester/profiles" / f"{name}_{SUFFIX[strat]}.json").read_text())
    d = {k: v for k, v in d.items() if not k.startswith("_") or k == "_instrument"}
    d["_strategy"] = strat
    d["_tf"] = 3
    d.update(FIXED)
    return d


def mutate(p, strat):
    c = copy.deepcopy(p)
    space = dict(SPACE, **ENTRY_SPACE)
    for _ in range(random.choice([1, 1, 2, 2, 3, 4])):
        k = random.choice(list(space))
        if k == "_sess":
            n = random.choice([1, 2, 3])
            f = random.choice(["TradeStartH", "TradeEndH", "ZoneStartH", "ZoneEndH", "TradeStartM", "TradeEndM"])
            key = f"sess{n}{f}"
            if f.endswith("M"):
                c[key] = random.choice([0, 15, 30, 45])
            else:
                c[key] = (int(c.get(key, 0)) + random.choice([-2, -1, 1, 2])) % 24
            continue
        cur = c.get(k)
        vals = space[k]
        if isinstance(cur, dict):
            cur = cur.get("value")
        # preferuj susedne hodnoty pri ciselnych zoznamoch
        if isinstance(vals[0], (int, float)) and not isinstance(vals[0], bool) and cur in vals and random.random() < 0.7:
            i = vals.index(cur) + random.choice([-1, 1])
            v = vals[max(0, min(len(vals) - 1, i))]
        else:
            v = random.choice(vals)
        if k == "fvgMinSize2":
            continue
        if k == "fvgMinSize":
            val, _, unit = v.partition("@")
            c[k] = {"value": float(val), "unit": unit or "abs"}
            continue
        c[k] = {"value": v, "unit": "pct"} if k == "minSlDistance" else v
    if not c.get("enableImbEntry") and not c.get("enablePinBarEntry"):
        c["enableImbEntry"] = True
    c.update(MODES[strat])
    c["_strategy"] = "ibsentry"
    if not any(c.get(f"fvgUse{t}") for t in ("5m", "15m", "30m", "60m")):
        c["fvgUse15m"] = True
    c.update(FIXED)
    c.update(MODES[strat])
    return c


def score(r):
    if not r or r.get("trades") is None:
        return -1e9
    t, wr = r["trades"], r["winrate"] or 0
    if t < 30:
        return t - 500
    return min(t, 800) - (0 if wr >= 80 else 45 * (80 - wr))


def work_tr(strat, params, tr):
    from evalcore import evaluate
    import io, contextlib
    try:
        p = {k: v for k, v in params.items() if k != "_tf"}
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            r = evaluate(p, int(params["_tf"]), tr)
        return strat, params, r, None
    except Exception as e:
        return strat, params, None, f"{type(e).__name__}: {e}"


def work(strat, params):
    from evalcore import evaluate
    import io, contextlib
    try:
        p = {k: v for k, v in params.items() if k != "_tf"}
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            r = evaluate(p, int(params["_tf"]), TR)
        return strat, params, r, None
    except Exception as e:
        return strat, params, None, f"{type(e).__name__}: {e}"


def main():
    archive = {s: [] for s in SUFFIX}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("r"):
                archive[rec["strat"]].append((score(rec["r"]), rec["p"], rec["r"]))
    queue = []
    if not any(archive.values()):
        stA = [d for d in (json.loads(l) for l in open(ROOT / ".nightsearch" / "stageA.jsonl")) if d["r"]]
        old = [d for fn in ("results.jsonl", "results2.jsonl") for d in (json.loads(l) for l in open(ROOT / ".nightsearch" / fn))]
        old = [d for d in old if d["r"] and d["strat"] == "ibsentry"]
        bases = []
        for m in ("fvg", "ifvg", "both"):
            f = [d for d in stA if d["strat"] == m]
            for lo in (75, 78, 80, 82):
                g = sorted([d for d in f if d["r"]["winrate"] >= lo], key=lambda d: -d["r"]["trades"])
                bases += [g[0]["p"]] if g else []
        for lo in (80, 82):
            g = sorted([d for d in old if d["r"]["winrate"] >= lo], key=lambda d: -d["r"]["trades"])
            bases += [g[0]["p"]] if g else []
        for m in SUFFIX:
            for b in bases:
                c = copy.deepcopy(b); c.update(FIXED); c.update(MODES[m]); c["_strategy"] = "ibsentry"
                queue.append((m, c))
        for s in []:
            for n in SEEDS:
                try:
                    queue.append((s, load_seed(n, s)))
                except FileNotFoundError:
                    pass
    turn = [0]
    seen = set()
    for st in archive:
        for _, p, _ in archive[st]:
            seen.add((st, json.dumps(p, sort_keys=True)))

    def next_task():
        for _ in range(200):
            s, c = _next_task()
            key = (s, json.dumps(c, sort_keys=True))
            if key not in seen:
                seen.add(key)
                return s, c
        return s, c

    def _next_task():
        if queue:
            return queue.pop(0)
        s = list(SUFFIX)[turn[0] % len(SUFFIX)]
        turn[0] += 1
        arc = sorted(archive[s], key=lambda x: -x[0])
        top = arc[:25] if arc else []
        # nika: najlepsie v nahodnom (TF grafu, detekcny TF), aby sa nezasekol v jednej oblasti
        if arc and random.random() < 0.35:
            niche = (random.choice([2, 3, 4, 5]), random.choice(["1", "3", "5", "15"]))
            nt = [x for x in arc if (x[1].get("_tf"), x[1].get("zoneDetectionTF")) == niche][:10]
            if nt:
                top = nt
            else:
                base = copy.deepcopy(random.choice(arc[:10])[1])
                base["_tf"], base["zoneDetectionTF"] = niche
                return s, mutate(base, s)
        if not top:
            return s, mutate(load_seed(random.choice(SEEDS[:3]), "ibsentry"), s)
        # obcas krizenie dvoch dobrych
        if random.random() < 0.15 and len(top) > 3:
            a, b = random.sample(top, 2)
            child = {k: (a[1][k] if random.random() < 0.5 else b[1].get(k, a[1][k])) for k in a[1]}
            return s, mutate(child, s)
        w = [1.0 / (i + 1) ** 0.7 for i in range(len(top))]
        parent = random.choices(top, weights=w)[0][1]
        return s, mutate(parent, s)

    n = 0
    with ProcessPoolExecutor(WORKERS) as ex, open(OUT, "a") as fh:
        pend = {ex.submit(work, *next_task()) for _ in range(WORKERS)}
        while pend:
            done, pend = wait(pend, return_when=FIRST_COMPLETED)
            for f in done:
                strat, p, r, err = f.result()
                fh.write(json.dumps({"strat": strat, "p": p, "r": r, "err": err, "t": time.time()}) + "\n")
                fh.flush()
                n += 1
                if r:
                    archive[strat].append((score(r), p, r))
                if time.time() < DEADLINE:
                    pend.add(ex.submit(work, *next_task()))
            if n % 50 == 0:
                for s in SUFFIX:
                    feas = [x for x in archive[s] if x[2]["winrate"] >= 80]
                    b = max(feas, key=lambda x: x[2]["trades"]) if feas else None
                    print(time.strftime("%H:%M"), s, n, "best80:", b and (b[2]["trades"], b[2]["winrate"]), flush=True)


if __name__ == "__main__":
    main()
