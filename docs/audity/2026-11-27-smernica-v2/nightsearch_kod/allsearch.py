"""Všetky stratégie × MNQ, MGC, BTC: ~200 obchodov a čo najvyšší WR pri RR 1:1 na poslednom roku.
Len stop a cieľ — bez konca seansy, trailingu, break-even a iných výstupov.

python allsearch.py <hodiny>   (env ALL_WORKERS, default 8) — výstup all_<strategia>.jsonl
Priestor parametrov sa odvodí z configu stratégie (bool, enum, čísla okolo defaultu v rámci
CONSTRAINTS); semená sú default a uložené profily stratégie.
"""
import copy, json, math, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from dataclasses import fields
from enum import Enum
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
from tradebot.core.types import SizeSpec
from tradebot.strategies import STRATEGIES

ROOT = Path("/Users/martin/IBS")
LAST = "20250904-20260904"
INSTS = ["mnq_databento", "mgc_databento", "btcusdt_binance"]
KEYS = [k for k in STRATEGIES if k not in ("ibsnet", "orbnet", "demo_breakout")]
if os.environ.get("ALL_ONLY"):
    KEYS = [k for k in KEYS if k in os.environ["ALL_ONLY"].split(",")]
TARGET = 200

#: len stop a cieľ, RR 1:1 (prepíše sa v každom kandidátovi)
FORCE = {"rrRatio": 1.0, "rr": 1.0, "tpMode": "rr", "enableTrailing": False, "closeAtSessionEnd": False,
         "closeAtWindowEnd": False, "maxHoldBars": 0, "maxHoldMinutes": 0, "emaExit": False, "trendExit": False,
         "vwapTp": False, "vwapStop": False, "useBE": False, "closeEOD": False, "leverage": 1.0}
FORCE_BY = {"structure": {"exitMode": "rr"}, "vwaporb": {"exitMode": "tp"}}
SKIP = {"riskDollar", "riskPercent", "tickDollarValue", "legacyPineSizing", "tradeTZ", "trailActivationR",
        "trailOffsetR", "trailActivationPct", "trailOffsetPct", "beActivationPct", "beLockPct", "minRR", "maxRR"}


def _num_grid(d, lo, hi, is_int):
    if d == 0:
        base = [0, 0.1, 0.25, 0.5, 1, 2, 5] if not is_int else [0, 1, 2, 3, 5, 10]
    else:
        base = [d * m for m in (0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3)]
    out = []
    for v in base:
        if lo is not None:
            v = max(lo, v)
        if hi is not None:
            v = min(hi, v)
        v = int(round(v)) if is_int else round(v, 3)
        if v not in out:
            out.append(v)
    return out


def build_space(key):
    spec = STRATEGIES[key]
    cls = spec.config_cls
    cfg = cls()
    cons = getattr(cls, "CONSTRAINTS", {})
    force = {**FORCE, **FORCE_BY.get(key, {})}
    sp = {}
    for f in fields(cfg):
        n = f.name
        if n in force or n in SKIP or n.startswith("show") or n.startswith("draw") or n.startswith("color"):
            continue
        v = getattr(cfg, n)
        lo, hi = cons.get(n, (None, None))
        if isinstance(v, bool):
            sp[n] = [True, False]
        elif isinstance(v, Enum):
            sp[n] = [e.value for e in type(v)]
        elif isinstance(v, SizeSpec):
            sp[n] = _num_grid(v.value, 0.0, hi, False)
        elif isinstance(v, int):
            if n.endswith("H") and hi == 23:
                sp[n] = sorted({v, 0, 2, 3, 8, 9, 10, 13, 15, 16})
            elif n.endswith("M") and hi == 59:
                sp[n] = sorted({v, 0, 15, 30, 45})
            else:
                sp[n] = _num_grid(v, lo, hi, True)
        elif isinstance(v, float):
            sp[n] = _num_grid(v, lo, hi, False)
    sp["_tf"] = [2, 3, 3, 5, 5, 15]
    return sp, force


SPACES = {k: build_space(k) for k in KEYS}


def default_cfg(key):
    cfg = STRATEGIES[key].config_cls()
    c = {}
    for n in SPACES[key][0]:
        if n == "_tf":
            continue
        v = getattr(cfg, n)
        c[n] = v.value if isinstance(v, (Enum, SizeSpec)) else v
    c["_tf"] = int(str(STRATEGIES[key].default_timeframe or "5m").rstrip("m") or 5)
    if c["_tf"] not in (2, 3, 5, 15):
        c["_tf"] = 5
    return c


def seeds(key):
    """Default + uložené profily stratégie (len polia z priestoru)."""
    out = [default_cfg(key)]
    for fn in sorted((ROOT / "tester" / "profiles").glob("*.json")):
        try:
            d = json.load(open(fn))
        except Exception:
            continue
        if d.get("_strategy") != key:
            continue
        c = default_cfg(key)
        for n in SPACES[key][0]:
            if n in d:
                v = d[n]
                c[n] = v["value"] if isinstance(v, dict) and "value" in v else v
        tf = str(d.get("_timeframe", "")).rstrip("m")
        if tf.isdigit() and int(tf) in (2, 3, 5, 15):
            c["_tf"] = int(tf)
        out.append(c)
    return out[:60]


def enc(key, c):
    p = {n: v for n, v in c.items() if n != "_tf"}
    p.update(SPACES[key][1])
    cls = STRATEGIES[key].config_cls
    known = {f.name for f in fields(cls())}
    p = {n: v for n, v in p.items() if n in known}
    for n, u in getattr(cls, "SIZE_FIELDS", {}).items():
        if n in p and not isinstance(p[n], dict):
            p[n] = {"value": p[n], "unit": u}
    p["_strategy"] = key
    return p


def mutate(key, c):
    c = copy.deepcopy(c); S = SPACES[key][0]
    for _ in range(random.choice([1, 1, 2, 2, 3, 4, 6])):
        n = random.choice(list(S)); vals = S[n]; cur = c.get(n)
        if isinstance(vals[0], (int, float)) and not isinstance(vals[0], bool) and cur in vals and random.random() < 0.7:
            i = vals.index(cur) + random.choice([-1, 1]); c[n] = vals[max(0, min(len(vals) - 1, i))]
        else:
            c[n] = random.choice(vals)
    return c


def score(r):
    if not r:
        return -1e9
    t = r["trades"] or 0
    if t < 30:
        return -300 + t
    s = r["winrate"] - 1.0 * max(0, TARGET - 20 - t) - 0.1 * max(0, t - (TARGET + 100))
    s -= 60 * max(0.0, 0.9 - r.get("payoff_r", 0.0))   # RR 1:1 musí naozaj platiť (len stop a cieľ)
    if r["pnl_abs"] <= 0:
        s -= 10
    return s


def work(key, inst, c):
    from allcore import evaluate
    import io, contextlib
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            r = evaluate(enc(key, c), int(c["_tf"]), LAST, inst)
        return key, inst, c, r, None
    except Exception as e:
        return key, inst, c, None, f"{type(e).__name__}: {e}"[:300]


def main(hours):
    deadline = time.time() + hours * 3600
    combos = [(k, i) for k in KEYS for i in INSTS]
    arc = {cb: [] for cb in combos}; seen = {cb: set() for cb in combos}; errs = {cb: 0 for cb in combos}
    fh = {}
    for k in KEYS:
        fn = ROOT / ".nightsearch" / f"all_{k}.jsonl"
        if fn.exists():
            for l in open(fn):
                d = json.loads(l); cb = (k, d["inst"])
                if cb not in arc:
                    continue
                seen[cb].add(json.dumps(d["p"], sort_keys=True))
                if d["r"]:
                    arc[cb].append((score(d["r"]), d["p"], d["r"]))
                else:
                    errs[cb] += 1
        fh[k] = open(fn, "a")
    queue = {cb: ([] if arc[cb] else seeds(cb[0])) for cb in combos}
    turn = [0]

    def task():
        # viac času kombináciám, ktoré sú bližšie k cieľu (váha rastie s najlepším WR nad 60 %)
        def weight(cb):
            if errs[cb] > 200 and errs[cb] > 5 * len(arc[cb]):
                return 0.0   # stratégia na tomto nástroji nebeží
            if not arc[cb] or len(arc[cb]) < 300:
                return 3.0
            wr = max(arc[cb], key=lambda x: x[0])[2]["winrate"]
            return 1.0 + max(0.0, wr - 60.0) / 2.0
        cb = random.choices(combos, weights=[weight(x) for x in combos])[0]
        k, inst = cb
        for _ in range(100):
            if queue[cb]:
                c = queue[cb].pop(0)
            else:
                top = sorted(arc[cb], key=lambda x: -x[0])[:20]
                if len(top) < 5 or random.random() < 0.07:
                    base = random.choice(seeds(k)[:5]) if random.random() < 0.5 or not top else top[0][1]
                    c = mutate(k, mutate(k, base))
                elif random.random() < 0.15:
                    x, y = random.sample(top, 2)
                    c = mutate(k, {q: (x[1][q] if random.random() < .5 else y[1].get(q, x[1][q])) for q in x[1]})
                else:
                    c = mutate(k, random.choices(top, weights=[1 / (i + 1) ** .7 for i in range(len(top))])[0][1])
            s = json.dumps(c, sort_keys=True)
            if s not in seen[cb]:
                seen[cb].add(s); return k, inst, c
        return k, inst, c

    n = 0
    with ProcessPoolExecutor(int(os.environ.get("ALL_WORKERS", "8"))) as ex:
        pend = {ex.submit(work, *task()) for _ in range(16)}
        while pend:
            done, pend = wait(pend, return_when=FIRST_COMPLETED)
            for f in done:
                k, inst, c, r, err = f.result(); cb = (k, inst)
                fh[k].write(json.dumps({"inst": inst, "p": c, "r": r, "err": err}) + "\n"); fh[k].flush(); n += 1
                if r:
                    arc[cb].append((score(r), c, r))
                else:
                    errs[cb] += 1
                if time.time() < deadline:
                    pend.add(ex.submit(work, *task()))
            if n % 500 == 0:
                best = []
                for cb in combos:
                    if arc[cb]:
                        s, c, r = max(arc[cb], key=lambda x: x[0])
                        best.append(f"{cb[0]}/{cb[1][:3]}:{r['trades']}/{r['winrate']}")
                print(time.strftime("%H:%M"), n, " ".join(best), flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]))
