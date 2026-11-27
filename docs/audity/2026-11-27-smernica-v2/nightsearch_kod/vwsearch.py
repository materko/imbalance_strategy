"""VWAP Session (vwapdrift) a VWAP ORB (vwaporb): najvyšší WR na poslednom roku pri RR 1-2.
python vwsearch.py <hodiny>  — 6 procesov, strategie sa striedaju; vystup vw_<key>.jsonl"""
import json, random, sys, time, copy, math, os
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
sys.path.insert(0, "/Users/martin/IBS")
ROOT = Path("/Users/martin/IBS")
HOURS = float(sys.argv[1]) if __name__ == "__main__" and len(sys.argv) > 1 else 0
DEADLINE = time.time() + HOURS * 3600
LAST = "20250904-20260904"
RRS = [1.0, 1.1, 1.2, 1.25, 1.3, 1.4, 1.5, 1.75, 2.0]
BANDS = [30, 60, 100, 150, 200, 250, 300]
RR_OBJ = [1.25, 1.5, 1.75, 2.0]
#: 150-200 obchodov za rok má prednosť (používateľ 29. 9.)
W_OBJ = {150: 4, 200: 4, 250: 3, 300: 3, 30: 0.5} if os.environ.get("VW_FREQ") else {}          # min. obchodov za rok — pre každé pásmo vlastný archív
B = [True, False]
COMMON = {"_tf": [5, 5, 3, 3, 2], "rrRatio": RRS, "tradeDirection": ["Both", "Both", "Long only", "Short only"],
          "vwapAnchor": ["ny_open", "ny_open", "session"], "vwapPeriod": ["15", "chart"],
          "closeAtSessionEnd": [True, False, False]}
SPACES = {
 "vwaporb": {**COMMON,
  "sessionMode": ["ny", "ny", "both"], "lonRangeMinutes": [15, 30, 60],
  "maxTradesPerDay": [1, 2, 2, 3],
  "nyRangeMinutes": [5, 10, 15, 15, 20, 30, 45, 60], "entryMode": ["close", "close", "retest", "stop"],
  "retestMaxBars": [3, 5, 10, 20], "breakBufferAtr": [0, 0.05, 0.1, 0.2, 0.3, 0.5],
  "entryWindowMinutes": [0, 30, 60, 90, 120, 180, 240],
  "minRangePct": [0, 0, 0.1, 0.15, 0.2, 0.3, 0.4], "maxRangePct": [0.4, 0.6, 0.8, 1.0, 1.5, 10],
  "useVolumeFilter": [False, False, True], "volMultiplier": [1.0, 1.2, 1.5, 2.0], "volSmaLen": [10, 20, 50],
  "minClosePosPct": [0, 0, 25, 50, 70, 85], "emaFilter": B, "emaRangeFilter": [False, False, True],
  "emaExit": [False, False, True], "emaLen": [20, 50, 100, 200],
  "slMode": ["opposite", "opposite", "mid", "range_pct", "atr", "break_candle"], "slRangePct": [25, 50, 75, 100, 125],
  "slAtrMult": [0.5, 0.75, 1, 1.5, 2, 3], "slBufferAtr": [0, 0.05, 0.1, 0.25, 0.5],
  "enableTrailing": [False, False, False, True], "trailActivationR": [0.5, 0.75, 1.0, 1.5], "trailOffsetR": [0.25, 0.5, 0.75, 1.0],
  "vwapRule": ["break", "direction"], "entryTiming": ["any", "break_candle"], "vwapBreakAtr": [0, 0, 0.1, 0.25, 0.5],
  "closeBeyondVwap": B, "vwapDriftBars": [1, 2, 3, 4, 6], "vwapDriftMinAtr": [0, 0, 0.05, 0.1, 0.2, 0.5],
  "exitMode": ["tp", "tp", "tp", "tp_vwap"], "vwapExitAtr": [0, 0.1, 0.25, 0.5],
  "vwapStop": [False, False, False, True], "vwapStopAtr": [0, 0.1, 0.25, 0.5],
  "vwapTp": [False, False, False, True], "vwapTpAtr": [0, 0.1, 0.25],
 },
 "vwapdrift": {**COMMON,
  "driftBars": [1, 2, 3, 4, 6, 8], "driftMinAtr": [0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8],
  "entryMode": ["close", "limit", "stop", "reaction", "pinbar", "engulfing"], "stopValidBars": [1, 2, 3, 5],
  "confirmBars": [1, 2, 3, 5, 8], "pbWickPct": [40, 50, 60, 70], "pbBodyPct": [15, 25, 35],
  "awayAtr": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0], "touchTolAtr": [0, 0.05, 0.1, 0.2, 0.3, 0.5],
  "failCloseAtr": [0.1, 0.25, 0.5, 1.0], "firstPullbackOnly": B,
  "everyBounce": [False, False, True], "bounceAwayAtr": [0.25, 0.5, 1.0], "maxBouncesPerDay": [1, 2, 3, 5],
  "tradeBreakout": [False, False, True], "breakoutAtr": [0.25, 0.5, 1.0], "breakoutWithBias": B, "maxBreakoutsPerDay": [1, 2],
  "entryDelayMinutes": [0, 15, 15, 30, 45, 60, 90], "entryWindowMinutes": [0, 60, 120, 180, 240],
  "maxTradesPerDay": [1, 2, 2, 3], "sessionEndH": [11, 12, 13, 15, 15, 15], "sessionEndM": [0, 30, 55],
  "slMode": ["pullback", "candle", "vwap", "atr", "swing"], "slBufferAtr": [0, 0.1, 0.25, 0.5, 1.0],
  "slAtr": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0], "slSwingBars": [3, 6, 10, 15],
 },
}

def size_fields(key):
    from tradebot.strategies import get_spec
    return get_spec(key).config_cls.SIZE_FIELDS

_SF = {}
def enc(key, c):
    if key not in _SF:
        _SF[key] = size_fields(key)
    p = {k: v for k, v in c.items() if k != "_tf"}
    for k, u in _SF[key].items():
        if k in p and not isinstance(p[k], dict):
            p[k] = {"value": p[k], "unit": u}
    p.update({"_strategy": key, "_instrument": "mnq_databento", "riskDollar": 100.0, "tickDollarValue": 0.5})
    if key == "vwaporb":
        p.update(tpMode="rr")
        p.setdefault("sessionMode", "ny")
    return p

def fix(key, c):
    if key == "vwapdrift" and c["sessionEndH"] == 15 and c["sessionEndM"] == 0:
        c["sessionEndM"] = 55
    if key == "vwapdrift":
        if c["entryWindowMinutes"] and c["entryWindowMinutes"] <= c["entryDelayMinutes"]:
            c["entryWindowMinutes"] = 0
        end = (c["sessionEndH"] * 60 + c["sessionEndM"]) - 570
        if c["entryDelayMinutes"] >= end - 15:
            c["entryDelayMinutes"] = 15
    if c.get("pbWickPct", 0) + c.get("pbBodyPct", 0) > 100:
        c["pbBodyPct"] = 100 - c["pbWickPct"]
    if key == "vwaporb" and c["minRangePct"] >= c["maxRangePct"]:
        c["maxRangePct"] = 10
    return c

if os.environ.get("VW_ONLY"):
    SPACES = {k: v for k, v in SPACES.items() if k in os.environ["VW_ONLY"].split(",")}
PURE = bool(os.environ.get("VW_PURE"))
if PURE:   # bez konca seansy, trailingu a výstupov cez VWAP — len stop a cieľ (používateľ 29. 9.)
    for _k, _s in SPACES.items():
        _s["closeAtSessionEnd"] = [False]
    SPACES["vwaporb"].update(enableTrailing=[False], vwapStop=[False], vwapTp=[False], exitMode=["tp"], emaExit=[False])

def rand_cfg(key):
    return fix(key, {k: random.choice(v) for k, v in SPACES[key].items()})

def mutate(key, p):
    c = copy.deepcopy(p); S = SPACES[key]
    for _ in range(random.choice([1, 1, 2, 2, 3, 4])):
        k = random.choice(list(S)); vals = S[k]; cur = c.get(k)
        if isinstance(vals[0], (int, float)) and not isinstance(vals[0], bool) and cur in vals and random.random() < 0.7:
            i = vals.index(cur) + random.choice([-1, 1]); c[k] = vals[max(0, min(len(vals) - 1, i))]
        else:
            c[k] = random.choice(vals)
    return fix(key, c)

def score(r, rr, band):
    if not r:
        return -1e9
    t = r["trades"] or 0
    if t < 20:
        return -200 + t
    s = r["winrate"] - 1.5 * max(0, band - t)
    # reálny zisk:strata musí sedieť s RR 1-2 (inak by WR nahnali predčasné výstupy)
    if PURE:   # len stop a cieľ: reálny pomer v R musí byť blízko nastaveného RR
        s -= 60 * max(0.0, 0.9 - r.get("payoff_r", 0.0) / rr)
    else:
        s -= 60 * max(0.0, 0.9 - r["payoff"])
    if r["pnl_abs"] <= 0:
        s -= 10
    return s

def work(key, c):
    from vwcore import evaluate
    import io, contextlib
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            r = evaluate(enc(key, c), int(c["_tf"]), LAST)
        return key, c, r, None
    except Exception as e:
        return key, c, None, f"{type(e).__name__}: {e}"[:300]

def main():
    keys = list(SPACES)
    arc = {k: [] for k in keys}; seen = {k: set() for k in keys}
    fh = {k: open(ROOT / ".nightsearch" / f"vw{os.environ.get('VW_TAG', '')}_{k}.jsonl", "a+") for k in keys}
    for k in keys:
        fh[k].seek(0)
        for l in fh[k]:
            d = json.loads(l); seen[k].add(json.dumps(d["p"], sort_keys=True))
            if d["r"]:
                arc[k].append((d["p"], d["r"]))
    top = {}
    def refresh(k):
        for b in BANDS:
            top[(k, b)] = sorted(arc[k], key=lambda x: -score(x[1], x[0]["rrRatio"], b))[:25]
        # ciele podľa RR: najvyšší WR pri pevnom RR (aspoň 60 obchodov)
        for rr in RR_OBJ:
            g = [x for x in arc[k] if x[0]["rrRatio"] == rr]
            top[(k, f"rr{rr}")] = sorted(g, key=lambda x: -score(x[1], rr, 60))[:25]
    for k in keys:
        refresh(k)
    turn = [0]
    queue = {k: [] for k in keys}
    if PURE and not any(arc.values()):   # semená: najlepšie staré nastavenia prepnuté na čistý stop/cieľ
        for k in keys:
            old = []
            for fn in (f"vw_{k}.jsonl", f"vw2_{k}.jsonl"):
                if not (ROOT / ".nightsearch" / fn).exists():
                    continue
                for l in open(ROOT / ".nightsearch" / fn):
                    d = json.loads(l)
                    if d["r"] and d["r"]["trades"] >= 40:
                        old.append(d)
            old.sort(key=lambda d: -d["r"]["winrate"])
            for d in old[:400]:
                c = dict(d["p"])
                for q, v in SPACES[k].items():
                    if len(v) == 1:
                        c[q] = v[0]
                queue[k].append(fix(k, c))
    def task():
        k = keys[turn[0] % len(keys)]; turn[0] += 1
        if queue[k]:
            c = queue[k].pop(0); seen[k].add(json.dumps(c, sort_keys=True)); return k, c
        for _ in range(200):
            objs = BANDS + [f"rr{r}" for r in RR_OBJ]
            b = random.choices(objs, weights=[W_OBJ.get(o, 1) for o in objs])[0]
            t = top.get((k, b)) or []
            if isinstance(b, str) and len(t) < 5:   # pre RR ešte nie je z čoho, prepni najlepšie pásmo na to RR
                t = [(dict(x[0], rrRatio=float(b[2:])), x[1]) for x in top.get((k, 60)) or []]
            if len(arc[k]) < 300 or random.random() < 0.06 or len(t) < 5:
                c = rand_cfg(k)
            elif random.random() < 0.15:
                x, y = random.sample(t, 2)
                c = mutate(k, fix(k, {q: (x[0][q] if random.random() < .5 else y[0].get(q, x[0][q])) for q in x[0]}))
            else:
                c = mutate(k, random.choices(t, weights=[1 / (i + 1) ** .7 for i in range(len(t))])[0][0])
            if isinstance(b, str) and random.random() < 0.9:
                c["rrRatio"] = float(b[2:])
            s = json.dumps(c, sort_keys=True)
            if s not in seen[k]:
                seen[k].add(s); return k, c
        return k, c
    n = 0
    with ProcessPoolExecutor(int(os.environ.get("VW_WORKERS", "6"))) as ex:
        pend = {ex.submit(work, *task()) for _ in range(12)}
        while pend:
            done, pend = wait(pend, return_when=FIRST_COMPLETED)
            for f in done:
                k, c, r, err = f.result()
                fh[k].write(json.dumps({"p": c, "r": r, "err": err}) + "\n"); fh[k].flush(); n += 1
                if r:
                    arc[k].append((c, r))
                if time.time() < DEADLINE:
                    pend.add(ex.submit(work, *task()))
            if n % 300 == 0:
                for k in keys:
                    refresh(k)
                line = [time.strftime("%H:%M"), str(n)]
                for k in keys:
                    for b in BANDS + [f"rr{r}" for r in RR_OBJ]:
                        x = top[(k, b)][0] if top.get((k, b)) else None
                        if x:
                            line.append(f"{k[-4:]}{b}:{x[1]['trades']}/{x[1]['winrate']}/rr{x[0]['rrRatio']}/po{x[1]['payoff']}")
                print(" ".join(line), flush=True)

if __name__ == "__main__":
    main()
