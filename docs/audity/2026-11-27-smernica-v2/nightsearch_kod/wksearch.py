"""Víkendové hľadanie (2.–5. 10. 2026): JSS, CRT + TBS, Scalping 3MA, Fibo, Volume Profile POC, FVG POLARITY
na MNQ, MGC a BTC, posledný rok. Stále pravidlá testov: bez trailingu a konca seansy (len stop a cieľ),
min. 150 obchodov za rok, WR 70–100 %, RR 0,5–2,0, v priestore aj market / limit a vstupné modely IBS + pin bar.
WK_DEADLINE=<epoch> WK_WORKERS=6 python wksearch.py — výstup wk_<stratégia>.jsonl (dá sa reštartovať)."""
import copy, json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
ROOT = Path("/Users/martin/IBS")
LAST = "20250904-20260904"
PREV = "20240904-20250904"
PREV2 = "20230904-20240904"   #: tretí a štvrtý rok pre „hlavu a pätu" (rok 21/22 ostáva na nezávislú kontrolu)
PREV3 = "20220904-20230904"
INSTS = [i for i in os.environ.get("WK_INSTS", "mnq_databento,mgc_databento,btcusdt_binance").split(",") if i]
KEYS = [k for k in os.environ.get("WK_ONLY", "jss,crt,scalp3ma,fibo,svp,fvgpolarity").split(",") if k]
RRS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
MIN_T = int(os.environ.get("WK_MIN_T", "150"))
MIN_PF = float(os.environ.get("WK_MIN_PF", "0"))      #: napr. 1,5 — profit factor pod ním sa trestá
#: ciele: (min. obchodov, min. reálny zisk:strata v R) — najvyšší WR zvlášť pre KAŽDÉ RR 0,5 až 2,0
#: (prah = 90 % daného RR), aby sa hľadanie nezosypalo len na RR 0,5; "pf" = najvyšší profit factor pri 150+ obchodoch
OBJ = [(MIN_T, round(0.9 * rr, 3)) for rr in RRS] + ["pf"]
#: „hlava a päta": tie isté ciele, ale ráta sa horší zo štyroch rokov (25/26, 24/25, 23/24, 22/23) — len pre nastavenia, ktoré
#: sú na poslednom roku sľubné (150+ obchodov, zisk, WR aspoň 6 bodov nad hranicou ziskovosti) a ziskové aj v 24/25
ROB = [("rob", round(0.9 * rr, 3)) for rr in RRS]


def pay(r):
    """Reálny zisk:strata = priemerný zisk / priemerná strata v peniazoch = PF × prehry / výhry.
    (Priemer v R skresľoval jediný obchod s mikroskopickým stopom — napr. +68 R pri RR 0,5.)"""
    if not r:
        return 0.0
    wr, pf = r.get("winrate") or 0.0, r.get("profit_factor") or 0.0
    if wr <= 0:
        return 0.0
    if wr >= 100:
        return 0.0      # bez straty sa pomer nedá určiť — nezaraďuje sa
    return pf * (100.0 - wr) / wr


def promising(r):
    if not r or (r["trades"] or 0) < MIN_T or r["pnl_abs"] <= 0:
        return False
    pr = pay(r)
    return pr >= 0.45 and r["winrate"] >= 100.0 / (1.0 + pr) + 6.0


def rob_score(r, rp, rp2, rp3, need):
    """Horší zo štyroch rokov: WR, s pokutami za málo obchodov, nízky zisk:strata a stratu."""
    if not r or not rp or not rp2 or not rp3:
        return -1e9
    s = 1e9
    for x in (r, rp, rp2, rp3):
        t = x["trades"] or 0
        v = x["winrate"] - 1.0 * max(0, 120 - t) - 60 * max(0.0, need - pay(x)) - (15 if x["pnl_abs"] <= 0 else 0) \
            - 40 * max(0.0, 0.8 * MIN_PF - (x["profit_factor"] or 0))
        s = min(s, v)
    return s
B = [False, True]
DIR = ["Both", "Both", "Long only", "Short only"]
WIN = {"useTradeWindow": [False, True, True], "tradeStartH": [0, 2, 3, 8, 9, 10], "tradeStartM": [0, 30],
       "tradeEndH": [11, 12, 15, 16, 20], "tradeEndM": [0, 30]}
ORDER = {"entryOrderType": ["market", "market", "limit"], "limitOffsetPct": [25, 50, 75], "limitValidBars": [2, 3, 6]}
CONFIRM = {"entryConfirm": ["none", "none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]}
TREND = {"trendFilter": ["off", "off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60, 240],
         "volFilter": ["off", "off", "low", "high"], "volLookback": [50, 100, 300]}
MODEL = {"imbMinSizeAtr": [0, 0.05, 0.1, 0.2], "pbWickPct": [50, 60, 70], "pbBodyPct": [20, 30]}
PTS = {"mnq_databento": dict(buf=[0, 0, 2, 5, 10, 20], row=[4, 8, 20, 40], sl=[5, 10, 15, 20, 30, 40, 60, 80, 120, 200],
                             fmin=[0, 2, 5, 10, 15, 20, 30, 50], fmax=[0, 10, 20, 30, 50, 80, 120, 200]),
       "mgc_databento": dict(buf=[0, 0, 0.2, 0.5, 1, 2], row=[1, 2, 5, 10], sl=[0.5, 1, 2, 3, 5, 8, 12, 20, 30],
                             fmin=[0, 0.2, 0.5, 1, 2, 3, 5], fmax=[0, 1, 2, 3, 5, 8, 12, 20]),
       "btcusdt_binance": dict(buf=[0, 0, 20, 50, 100, 200], row=[100, 250, 500, 1000], sl=[50, 100, 150, 200, 300, 500, 800, 1200, 2000],
                               fmin=[0, 20, 50, 100, 200, 300, 500], fmax=[0, 100, 200, 300, 500, 800, 1200, 2000])}


def space(key, inst):
    g = PTS[inst]
    if key == "jss":
        return {"_tf": [3, 5, 5, 15], "structTF": [15, 30, 60, 60, 120, 240, 240], "refineTF": [0, 5, 15, 15, 30],
                "swingLen": [2, 3, 3, 4, 5], "triggerMode": ["bos", "choch", "both"], "zoneType": ["ob", "ob", "base"],
                "zoneEdge": ["wick", "body"], "impulseAtr": [0.3, 0.5, 0.75, 1.0, 1.5], "baseMaxBars": [1, 2, 3, 5],
                "zoneMinAtr": [0, 0, 0.1, 0.25], "zoneMaxAtr": [0, 1.0, 1.5, 2.0, 3.0], "zoneMaxAgeBars": [0, 12, 24, 48, 100, 200],
                "useFibo": [False, False, True], "fibMinPct": [38.2, 50, 61.8], "fibMaxPct": [78.6, 100],
                "entryModel": ["touch", "touch", "imbalance", "pinbar", "any"], "entryDepthPct": [0, 0, 25, 50],
                "confirmBars": [2, 4, 6, 10], **MODEL, "tradeDirection": DIR, "maxTradesPerDay": [1, 2, 3, 5, 10],
                "cooldownBars": [0, 3, 6, 12], **WIN, "slFrom": ["refined", "refined", "htf"],
                "slBufferAtr": [0, 0.05, 0.1, 0.25, 0.5], "slBufferPoints": g["buf"], "tpMode": ["rr"], "rrRatio": RRS,
                "maxHoldBars": [0], **ORDER, **TREND}
    if key == "crt":
        return {"_tf": [3, 5, 5, 15], "rangeTF": [60, 120, 240, 240, 480], "rangeMinAtr": [0, 0, 0.5, 0.75, 1.0],
                "rangeMaxAtr": [0, 0, 1.5, 2.0, 3.0], "sweepWithinBars": [1, 1, 2], "validBars": [1, 2, 2, 3],
                "requireHtfClose": [False, False, True], "requireOldHL": [False, False, True], "keyLookback": [3, 6, 12, 24],
                "sweepKind": ["body", "wick", "any"], "sweepMaxAtr": [0, 0, 1.0, 2.0, 4.0],
                "entryModel": ["model1", "cisd", "mss_fvg"], "swingLen": [2, 3, 5], "fvgValidBars": [3, 6, 12],
                "tradeDirection": DIR, "maxTradesPerDay": [1, 2, 3, 5], **WIN,
                "slBufferAtr": [0, 0.05, 0.1, 0.25, 0.5, 1.0], "slBufferPoints": g["buf"], "tpMode": ["rr"], "rrRatio": RRS,
                "maxHoldBars": [0], **ORDER, **CONFIRM, **TREND}
    if key == "scalp3ma":
        return {"_tf": [2, 3, 5, 5, 15], "ma1Len": [10, 20, 20, 30], "ma2Len": [40, 50, 60, 80], "ma3Len": [100, 150, 200, 200, 300],
                "requireMaOrder": B, "rsiLen": [7, 10, 14, 14, 21], "rsiLevel": [45, 50, 50, 55], "rsiExit": [False],
                "fractalLen": [2, 2, 3, 5], "fractalSide": ["pullback", "trend", "any"], "tradeDirection": DIR,
                "maxTradesPerDay": [1, 2, 3, 5, 10], "cooldownBars": [0, 3, 6, 12], **WIN,
                "slMode": ["atr", "atr", "fractal"], "slAtr": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0], "slBufferAtr": [0, 0.1, 0.25, 0.5],
                "rrRatio": RRS, "beAtR": [0], **ORDER, **CONFIRM, **TREND}
    if key == "fibo":
        return {"_tf": [3, 5, 5, 15], "swingTF": [5, 15, 15, 30, 60], "swingLen": [2, 3, 3, 5], "legMinAtr": [1, 2, 3, 4, 6],
                "requireBreak": B, "use382": B, "use50": B, "use618": B, "use786": B, "levelMode": ["zone", "zone", "levels"],
                "levelTolAtr": [0, 0.1, 0.25, 0.5], "setupMaxBars": [20, 40, 60, 120], "entryModel": ["imbalance", "pinbar", "any"],
                "signalMaxBars": [0, 1, 2, 3, 5], **MODEL, "tradeDirection": DIR, "maxTradesPerDay": [1, 2, 3, 5, 10], **WIN,
                "slMode": ["leg", "pullback", "pullback"], "slBufferAtr": [0, 0.05, 0.1, 0.25, 0.5], "slBufferPoints": g["buf"],
                "tpMode": ["rr"], "rrRatio": RRS, "maxHoldBars": [0], **ORDER, **TREND}
    if key == "svp":
        return {"_tf": [2, 3, 5, 5, 15], "rowTicks": g["row"], "valueAreaPct": [70], "pocSource": ["previous", "previous", "developing"],
                "tradeMode": ["rejection", "retest", "both", "both"], "entryModel": ["touch", "touch", "imbalance", "pinbar", "any"],
                "awayAtr": [0.5, 1.0, 1.5, 2.0, 3.0], "touchTolAtr": [0, 0.1, 0.25], "breakBufferAtr": [0, 0.25, 0.5],
                "retestMaxBars": [12, 24, 48, 96], "confirmBars": [2, 4, 6], **MODEL, "tradeDirection": DIR,
                "maxTradesPerDay": [1, 2, 3, 5], "useFibo": [False, False, True], "fibSwingTF": [5, 15, 30],
                "fibSwingLen": [2, 3, 5], "fibLegMinAtr": [1, 2, 3, 5], "fibMinPct": [23.6, 38.2, 50, 61.8], "fibMaxPct": [61.8, 78.6, 100],
                **WIN, "closeAtWindowEnd": [False], "slMode": ["atr"], "slAtr": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
                "tpMode": ["rr"], "rrRatio": RRS, **ORDER, **TREND}
    if key == "mag7":     # SPX sila — bez konca seansy (useEod vypnuté), bez trailingu
        return {"_tf": [5, 10, 15, 15, 30], "thr": [2, 3, 4, 5, 5, 6, 7, 8], "waitMin": [5, 10, 10, 15, 20, 30],
                "entryEnd": [15, 30, 30, 45, 60, 90, 120], "allowL": [True, True, False], "allowS": [True, True, False],
                "useVwap": B, "useEma": B, "emaLen": [20, 50, 100, 200], "useMag": B, "magLen": [3, 5, 9, 14],
                "useOpen": [False, False, True], "minMove": [0, 0, 5, 10, 20], "slMode": ["open", "points"],
                "slPts": [10, 15, 20, 30, 40, 60], "slOpenBuf": [0, 2, 5, 10], "rr": RRS, "useEod": [False],
                "typDays": [10, 20, 40], "zFull": [0.5, 1.0, 1.5, 2.0], "wMag": [0.5, 1.0, 2.0], "wBreadth": [0, 0.5, 1.0, 2.0],
                "spxOnly": [True, True, False], "stockW": [0.5, 1.0, 2.0], "fixedQty": [True], "qty": [1.0],
                **ORDER, **CONFIRM, **TREND}
    if key == "dailyopen":   # DAILY OPEN — bez výstupu v čase (useExit vypnuté), cieľ = stop × RR
        return {"_tf": [5, 15, 30, 60, 60], "refH": [0], "breakPts": [5, 10, 15, 20, 30, 40, 60],
                "entryMode": ["stop", "close"], "breakMode": ["any", "before"], "entryStartH": [2, 3, 8, 8, 9],
                "entryStartM": [0, 30], "entryEndH": [10, 11, 12, 14, 16], "entryEndM": [0], "tradeDirection": DIR,
                "maxTradesPerDay": [1, 1, 2], "slPts": [20, 30, 40, 50, 60, 80, 100], "doRR": RRS, "useExit": [False],
                "fixedQty": [True], "qty": [1.0], **ORDER, **CONFIRM, **TREND}
    if key == "fpc":
        sl = [10, 15, 20, 25, 30, 40, 50]
        return {"_tf": [1], "useS1": [True, True, False], "s1Len": [30, 60, 90, 120], "useS2": B, "s2Len": [30, 60, 90, 120],
                "useS3": [False, False, True], "useS4": [False, False, True], "pmFair": ["open", "morning"],
                "newsMode": ["off", "auto", "auto", "always"], "useNewsWin": B, "useCont": B, "contWin": [3, 5, 10],
                "useBias": B, "biasH": [4, 6, 8, 12], "contSL": sl, "contRR": RRS, "bigBar": [15, 25, 40, 1000],
                "useRev": [True, True, False], "tpMode": ["fixed", "fixed", "fair"], "revSL": sl, "revRR": RRS,
                "minPct": [60, 80, 100], "minDist": [10, 15, 25, 40], "useDisp": B, "useBos": B, "pivLen": [1, 2, 3],
                "tradeDirection": DIR, "maxLossRow": [1, 2, 3, 5], "maxTrades": [1, 2, 3, 5, 10], "useCloseAfter": [False],
                "useTrend": B, "trendPts": [10, 20, 40], "useMaxD": B, "maxDist": [50, 100, 150, 250], "usePause": B,
                "pauseMin": [5, 10, 20], "useRevDel": B, "revDelay": [5, 10, 20, 30], "useTests": B, "minTests": [2, 3],
                "testTol": [2, 3, 5], "useRevBias": B, **ORDER, **CONFIRM, **TREND}
    if key == "fvgpolarity":
        return {"_tf": [3, 5, 15, 15, 30, 60], "slPoints": g["sl"], "fvgMinSize": g["fmin"], "fvgMaxSize": g["fmax"],
                "tpLevel": ["near", "mid", "far"], "tradeDirection": DIR, "entryOrderType": ["market", "market", "limit"],
                "limitOffsetPct": [0, 25, 50, 75, 100], "limitValidBars": [1, 2, 3, 5, 10], "limitKeepRR": B, **CONFIRM, **TREND}
    raise KeyError(key)


def fix(key, c):
    if "tradeEndH" in c and c["tradeEndH"] * 60 + c["tradeEndM"] <= c["tradeStartH"] * 60 + c["tradeStartM"]:
        c["tradeEndH"] = 20
    if key == "jss":
        if c["zoneMaxAtr"] and c["zoneMinAtr"] > c["zoneMaxAtr"]:
            c["zoneMinAtr"] = 0
        if c["fibMinPct"] >= c["fibMaxPct"]:
            c["fibMaxPct"] = 100
    if key == "crt":
        if c["validBars"] < c["sweepWithinBars"]:
            c["validBars"] = c["sweepWithinBars"]
        if c["rangeMaxAtr"] and c["rangeMinAtr"] >= c["rangeMaxAtr"]:
            c["rangeMaxAtr"] = 0
        if c["rangeTF"] % c["_tf"]:
            c["_tf"] = 5
    if key == "fibo" and not (c["use382"] or c["use50"] or c["use618"] or c["use786"]):
        c["use618"] = True
    if key == "svp":
        if c["fibMinPct"] >= c["fibMaxPct"]:
            c["fibMaxPct"] = 100
        if c["tradeEndH"] * 60 + c["tradeEndM"] <= 9 * 60 + 30 and c["useTradeWindow"] and c["pocSource"] == "developing":
            c["tradeEndH"] = 15
    if key == "mag7":
        if c["entryEnd"] < c["waitMin"]:
            c["entryEnd"] = c["waitMin"] + 15
        if not (c["allowL"] or c["allowS"]):
            c["allowL"] = True
    if key == "dailyopen":
        if c["entryEndH"] * 60 <= c["entryStartH"] * 60 + c["entryStartM"]:
            c["entryEndH"] = 16
    if key == "fpc":
        if not (c["useDisp"] or c["useBos"]):
            c["useBos"] = True
        if not (c["useS1"] or c["useS2"] or c["useS3"] or c["useS4"]):
            c["useS1"] = True
        if not (c["useCont"] or c["useRev"]):
            c["useRev"] = True
    if key == "fvgpolarity" and c["fvgMaxSize"] and c["fvgMaxSize"] <= c["fvgMinSize"]:
        c["fvgMaxSize"] = 0
    return c


def enc(key, c):
    p = {k: v for k, v in c.items() if k not in ("_tf", "contRR", "revRR", "doRR")}
    if key == "dailyopen":
        p["tpPts"] = round(c["slPts"] * c["doRR"], 2)
    if key == "fpc":      # cieľ = stop × RR (RR 0,5 až 2)
        p["contTP"] = round(c["contSL"] * c["contRR"], 2)
        p["revTP"] = round(c["revSL"] * c["revRR"], 2)
    p["_strategy"] = key
    return p


def score(r, obj):
    if not r:
        return -1e9
    t = r["trades"] or 0
    if t < 30:
        return -300 + t
    if obj == "pf":
        return min(r["profit_factor"], 5.0) * 20 - 1.0 * max(0, MIN_T - t) - (30 if r["pnl_abs"] <= 0 else 0)
    need, pr = obj
    s = r["winrate"] - 1.0 * max(0, need - t) - 60 * max(0.0, pr - pay(r)) - 40 * max(0.0, MIN_PF - (r["profit_factor"] or 0))
    if r["pnl_abs"] <= 0:
        s -= 15
    return s


def work(key, inst, c):
    from allcore import evaluate
    import io, contextlib
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            r = evaluate(enc(key, c), int(c["_tf"]), LAST, inst)
            rp = evaluate(enc(key, c), int(c["_tf"]), PREV, inst) if promising(r) else None
            rp2 = None
            if rp and rp["pnl_abs"] > 0 and (rp["trades"] or 0) >= 100:
                rp2 = evaluate(enc(key, c), int(c["_tf"]), PREV2, inst)
            rp3 = None
            if rp2 and rp2["pnl_abs"] > 0 and (rp2["trades"] or 0) >= 100:
                rp3 = evaluate(enc(key, c), int(c["_tf"]), PREV3, inst)
        return key, inst, c, r, rp, rp2, rp3, None
    except Exception as e:
        return key, inst, c, None, None, None, None, f"{type(e).__name__}: {e}"[:300]


def main():
    deadline = float(os.environ["WK_DEADLINE"])
    combos = [(k, i) for k in KEYS for i in INSTS]
    arc = {x: [] for x in combos}; rarc = {x: [] for x in combos}; seen = {x: set() for x in combos}; fh = {}
    for k in KEYS:
        fn = ROOT / ".nightsearch" / f"wk_{k}.jsonl"
        bf = ROOT / ".nightsearch" / f"wkbf_{k}.jsonl"     # doplnené tretie roky pre staršie záznamy
        for src in (fn, bf, ROOT / ".nightsearch" / f"wkbf2_{k}.jsonl"):
            if not src.exists():
                continue
            for l in open(src):
                    try:
                        d = json.loads(l)
                    except ValueError:
                        continue
                    x = (k, d["inst"])
                    if x not in seen:
                        continue
                    seen[x].add(json.dumps(d["p"], sort_keys=True))
                    if d["r"] and src is fn:
                        arc[x].append((d["p"], d["r"]))
                    if d.get("rp3"):
                        rarc[x].append((d["p"], d["r"], d["rp"], d["rp2"], d["rp3"]))
        fh[k] = open(fn, "a")
    turn = [0]; top = {}
    def refresh():
        for x in combos:
            for o in OBJ:
                top[(x, o)] = sorted(arc[x], key=lambda y: -score(y[1], o))[:20]
            for o in ROB:
                top[(x, o)] = sorted(rarc[x], key=lambda y: -rob_score(y[1], y[2], y[3], y[4], o[1]))[:20]
    refresh()
    def task():
        x = combos[turn[0] % len(combos)]; turn[0] += 1
        key, inst = x; sp = space(key, inst)
        c = None
        for _ in range(300):
            # hlavné je posledný rok (používateľ 4. 10.): 85 % rodičov z cieľov posledného roka, 15 % z „hlavy a päty"
            o = random.choice(OBJ) if random.random() < float(os.environ.get("WK_LAST_SHARE", "0.85")) else random.choice(ROB)
            t = top.get((x, o)) or []
            if len(arc[x]) < 400 or random.random() < 0.08 or len(t) < 5:
                c = {k: random.choice(v) for k, v in sp.items()}
            else:
                c = copy.deepcopy(random.choices(t, weights=[1 / (i + 1) ** .7 for i in range(len(t))])[0][0])
                for _ in range(random.choice([1, 1, 2, 2, 3, 4])):
                    k = random.choice(list(sp)); vals = sp[k]; cur = c.get(k)
                    if isinstance(vals[0], (int, float)) and not isinstance(vals[0], bool) and cur in vals and random.random() < 0.7:
                        j = vals.index(cur) + random.choice([-1, 1]); c[k] = vals[max(0, min(len(vals) - 1, j))]
                    else:
                        c[k] = random.choice(vals)
            c = fix(key, c); s = json.dumps(c, sort_keys=True)
            if s not in seen[x]:
                seen[x].add(s); return key, inst, c
        return key, inst, c
    n = 0
    with ProcessPoolExecutor(int(os.environ.get("WK_WORKERS", "6"))) as ex:
        pend = {ex.submit(work, *task()) for _ in range(2 * int(os.environ.get("WK_WORKERS", "6")))}
        while pend:
            done, pend = wait(pend, return_when=FIRST_COMPLETED)
            for f in done:
                key, inst, c, r, rp, rp2, rp3, err = f.result()
                fh[key].write(json.dumps({"inst": inst, "p": c, "r": r, "rp": rp, "rp2": rp2, "rp3": rp3, "err": err}) + "\n")
                fh[key].flush(); n += 1
                if r:
                    arc[(key, inst)].append((c, r))
                if rp3:
                    rarc[(key, inst)].append((c, r, rp, rp2, rp3))
                if time.time() < deadline:
                    pend.add(ex.submit(work, *task()))
                if n % 600 == 0:
                    refresh()
                    line = [time.strftime("%d. %H:%M"), str(n)]
                    for x in combos:
                        t = top[(x, ROB[2])]
                        if t:
                            line.append(f"{x[0][:4]}/{x[1][:3]}:" + "+".join(f"{y['winrate']:.0f}" for y in t[0][1:]))
                    print(" ".join(line), flush=True)


if __name__ == "__main__":
    main()
