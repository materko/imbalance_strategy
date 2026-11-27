"""Hľadanie podľa smernice testovania (SMERNICA-TESTOVANIA, 8. 10. 2026) — VWAP ORB, IBS Entry Zone, SPX sila.

* ladenie (in-sample) 2021-10-01 – 2025-09-04, s poplatkom 1,755e-05, emulátor MultiCharts,
* naraz najviac 4 parametre (skupina), ostatné na doterajšom najlepšom — postupne skupina po skupine, dokola,
* cieľ: PF na ladení a stabilita po rokoch (žiadny rok pod PF 0,9), min. 100 obchodov za rok — nikdy winrate,
* počíta sa, koľko kombinácií sa skúsilo (smernica: nad 1000 prísnejšie hranice),
* kandidát (PF ≥ 1,3, roky OK) → plató (susedné hodnoty ≥ 80 % PF) → odložený rok 2025-09-04 – 2026-09-04 raz.
Pravidlá používateľa: bez trailingu a bez konca seansy.

python glsearch.py — beží donekonečna; počet procesov sa číta zo súboru gl_workers.txt pri každej skupine.
Výstup: gl_<stratégia>.jsonl (každé vyhodnotenie), gl_state.json (najlepšie, kandidáti, počty)."""
from __future__ import annotations

import itertools, json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
ROOT = Path("/Users/martin/IBS/.nightsearch")
FEE = 1.755e-05
IS = "20211001-20250904"
OOS = "20250904-20260904"
WINDOWS = [("21/22", "2021-10-01", "2022-10-01"), ("22/23", "2022-10-01", "2023-10-01"),
           ("23/24", "2023-10-01", "2024-09-04"), ("24/25", "2024-09-04", "2025-09-04")]
YEARS = 3.93
MIN_TRADES_YEAR = 100
B = [False, True]

NO_EXIT = {  # pravidlá používateľa: bez trailingu a konca seansy
    "vwaporb": {"closeAtSessionEnd": False, "enableTrailing": False, "vwapStop": False, "vwapTp": False, "exitMode": "tp",
                "emaExit": False},
    "ibsentry": {"closeAtSessionEnd": False, "enableTrailing": False},
    "mag7": {"useEod": False},
}
BASE = {
    "vwaporb": ("/Users/martin/IBS/tradebot/strategies/vwaporb/configs/mnq_databento_5m.json", 5),
    "ibsentry": ("/Users/martin/IBS/tester/profiles/NOCNE2_B_stabilny_entry.json", 3),
    "mag7": ("/Users/martin/IBS/tradebot/strategies/mag7/configs/mnq_databento_15m.json", 15),
}
GROUPS = {
    "vwaporb": [
        {"_tf": [3, 5], "nyRangeMinutes": [5, 10, 15, 30, 45, 60], "vwapRule": ["break", "direction"], "entryTiming": ["any", "break_candle"]},
        {"slMode": ["opposite", "mid", "atr", "break_candle"], "tpMode": ["rr", "measured"], "rrRatio": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0],
         "slBufferAtr": [0.0, 0.1, 0.25, 0.5]},
        {"sessionMode": ["ny", "both"], "vwapAnchor": ["ny_open", "session"], "vwapPeriod": ["15", "chart"], "closeBeyondVwap": B},
        {"entryWindowMinutes": [0, 30, 60, 120, 240], "maxTradesPerDay": [1, 2, 3], "minRangePct": [0.0, 0.1, 0.2, 0.3],
         "maxRangePct": [0.5, 1.0, 2.0, 10.0]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"],
         "confirmBars": [2, 3, 5]},
    ],
    "ibsentry": [
        {"rrRatio": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0], "slLookback": [5, 10, 20], "minSlDistance": [0.0, 0.05, 0.1, 0.15],
         "slBufferTicks": [0, 2, 4]},
        {"minImbSizePoints": [2.5, 4, 6, 8, 10], "imbLookback": [5, 10, 20], "state2ConfirmTicks": [1, 3, 6, 10], "imbMaxDistTicks": [40, 100]},
        {"zoneDetectionTF": ["3", "5", "15"], "zoneValidHours": [3, 6, 12], "snapMode": ["Floor", "Ceil"], "fvgMinSize": [5, 15, 30, 50]},
        {"indAdx": B, "adxThreshold": [15.0, 20.0, 25.0], "indSupertrend": B, "stMultiplier": [3, 5]},
        {"enablePinBarEntry": B, "pbWickToBodyRatio": [4, 8], "enableFvgTrading": B, "enableIfvgTrading": B},
        {"maxDailyWins": [3, 5, 9, 99], "state4MaxBars": [5, 10, 20], "state5MaxBars": [5, 10], "state3MaxBars": [1, 2, 4]},
    ],
    "mag7": [
        {"_tf": [5, 10, 15], "thr": [3.0, 4.0, 5.0, 6.0, 7.0], "waitMin": [10, 15, 20, 30], "entryEnd": [30, 60, 90, 120]},
        {"slMode": ["open", "points"], "slPts": [20.0, 30.0, 40.0, 60.0, 80.0], "slOpenBuf": [0.0, 2.0, 5.0, 10.0],
         "rr": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]},
        {"useVwap": B, "useEma": B, "emaLen": [20, 50, 100, 200], "useMag": B},
        {"typDays": [10, 20, 40], "zFull": [0.5, 1.0, 1.5, 2.0], "wBreadth": [0.0, 0.5, 1.0, 2.0], "magLen": [3, 5, 9]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"],
         "confirmBars": [2, 3, 5]},
    ],
}
MAX_PER_GROUP = 160


def evaluate(key: str, params: dict, timerange: str) -> dict:
    import allcore as A
    import pandas as pd
    from tradebot.core import load_profile
    from tradebot.core.types import INSTRUMENTS
    from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
    from tester.webapp.results import timerange_ms
    K = "mnq_databento"; inst = INSTRUMENTS[K]
    p = {k: v for k, v in params.items() if k != "_tf"}
    p.update({"_strategy": key, "_instrument": K})
    fn = A.TMP / f"gl{os.getpid()}.json"; fn.write_text(json.dumps(p))
    cfg, _ = load_profile(fn, engine="multicharts")
    f, t = timerange_ms(timerange)
    res, _ = emulate(cfg, inst, A.m1(K), int(params["_tf"]), from_ms=f, to_ms=t, fee=FEE)
    rows = rows_from_trades(res.trades, inst, FEE, 1.0)
    s, _ = summarize(rows, 60000.0, res, currency="USD")
    out = {k: s.get(k) for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_abs")}
    if timerange == IS:
        yrs = {}
        for name, a, b in WINDOWS:
            ys = [r["profit_abs"] for r in rows if a <= str(r["open_date"])[:10] < b]
            gw, gl = sum(x for x in ys if x > 0), -sum(x for x in ys if x < 0)
            yrs[name] = {"trades": len(ys), "pf": round(gw / gl, 3) if gl > 0 else (9.0 if gw > 0 else 0.0), "pnl": round(sum(ys), 1)}
        out["years"] = yrs
    return out


def score(r: dict) -> float:
    if not r or not r.get("trades"):
        return -1e9
    pf = min(r["profit_factor"] or 0.0, 4.0)
    per_year = r["trades"] / YEARS
    s = pf - 0.02 * max(0.0, MIN_TRADES_YEAR - per_year)
    ys = [y["pf"] for y in r.get("years", {}).values()]
    if ys:
        worst = min(ys)
        s += 0.3 * min(worst, 1.3) - 2.0 * max(0.0, 0.9 - worst)
    return s


def passes_is(r: dict) -> bool:
    ys = [y["pf"] for y in r.get("years", {}).values()]
    return bool(r) and (r["profit_factor"] or 0) >= 1.3 and r["trades"] / YEARS >= MIN_TRADES_YEAR and ys and min(ys) >= 0.9


def work(args):
    key, params = args
    try:
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return key, params, evaluate(key, params, IS), None
    except Exception as e:
        return key, params, None, f"{type(e).__name__}: {e}"[:300]


def workers() -> int:
    try:
        return max(1, int((ROOT / "gl_workers.txt").read_text().strip()))
    except Exception:
        return 6


def main() -> None:
    sf = ROOT / "gl_state.json"
    st = json.loads(sf.read_text()) if sf.exists() else {}
    for key, (prof, tf) in BASE.items():
        if key not in st:
            p = {k: v for k, v in json.load(open(prof)).items() if not k.startswith("_")}
            p.update(NO_EXIT[key]); p["_tf"] = tf
            st[key] = {"best": p, "best_r": None, "combos": 0, "seen": [], "candidates": [], "round": 0}
    seen = {k: set(v["seen"]) for k, v in st.items()}

    def save():
        for k in st:
            st[k]["seen"] = sorted(seen[k])
        sf.write_text(json.dumps(st, ensure_ascii=False))

    def run(batch):
        with ProcessPoolExecutor(workers()) as ex:
            for key, params, r, err in ex.map(work, batch):
                with open(ROOT / f"gl_{key}.jsonl", "a") as fh:
                    fh.write(json.dumps({"p": params, "r": r, "err": err, "t": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False) + "\n")
                yield key, params, r

    def plateau(key, best, r_best, group):
        """Susedné hodnoty každého číselného parametra skupiny (± jeden krok): PF ≥ 80 % víťaza?"""
        batch = []
        for name, vals in group.items():
            if name not in best or isinstance(vals[0], (bool, str)) or best[name] not in vals:
                continue
            i = vals.index(best[name])
            for j in (i - 1, i + 1):
                if 0 <= j < len(vals):
                    q = dict(best); q[name] = vals[j]; batch.append((key, q))
        ratios = []
        for _, q, r in run(batch):
            st[key]["combos"] += 1
            if r and r_best["profit_factor"]:
                ratios.append(round((r["profit_factor"] or 0) / r_best["profit_factor"], 3))
        return min(ratios) if ratios else None, ratios

    while True:
        for key in GROUPS:
            S = st[key]
            if S["best_r"] is None:
                for _, _, r in run([(key, S["best"])]):
                    S["best_r"] = r; S["combos"] += 1
            for gi, group in enumerate(GROUPS[key]):
                names = list(group)
                combos = [dict(zip(names, vals)) for vals in itertools.product(*group.values())]
                random.shuffle(combos)
                batch = []
                for c in combos:
                    q = dict(S["best"]); q.update(c); q.update(NO_EXIT[key])
                    sig = json.dumps(q, sort_keys=True)
                    if sig in seen[key]:
                        continue
                    seen[key].add(sig); batch.append((key, q))
                    if len(batch) >= MAX_PER_GROUP:
                        break
                improved = False
                for _, q, r in run(batch):
                    S["combos"] += 1
                    if r and score(r) > score(S["best_r"]):
                        S["best"], S["best_r"], improved = q, r, True
                print(time.strftime("%d. %H:%M"), key, f"skupina {gi + 1}", "zlepšenie" if improved else "bez zlepšenia",
                      f"PF {S['best_r']['profit_factor']:.2f} obch {S['best_r']['trades']}",
                      {k: v["pf"] for k, v in S["best_r"].get("years", {}).items()}, f"kombinácií {S['combos']}", flush=True)
                if improved and passes_is(S["best_r"]):
                    sig = json.dumps(S["best"], sort_keys=True)
                    if sig not in {json.dumps(c["p"], sort_keys=True) for c in S["candidates"]}:
                        pmin, ratios = plateau(key, S["best"], S["best_r"], group)
                        cand = {"p": S["best"], "is": S["best_r"], "plateau_min": pmin, "plateau": ratios,
                                "combos_at": S["combos"], "t": time.strftime("%Y-%m-%d %H:%M")}
                        if pmin is None or pmin >= 0.8:
                            import io, contextlib
                            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                                cand["oos"] = evaluate(key, S["best"], OOS)      # odložený rok — raz, nikdy na ladenie
                        S["candidates"].append(cand)
                        print("   KANDIDÁT", key, "plató", pmin, "OOS", cand.get("oos", {}).get("profit_factor"), flush=True)
                save()
            S["round"] += 1
            # nové kolo začína z náhodného suseda najlepšieho (aby sa nezasekol v jednom optime)
            if S["round"] % 3 == 0:
                q = dict(S["best"])
                for g in random.sample(GROUPS[key], 2):
                    n = random.choice(list(g)); q[n] = random.choice(g[n])
                q.update(NO_EXIT[key])
                for _, q2, r in run([(key, q)]):
                    S["combos"] += 1
                    if r and score(r) > score(S["best_r"]):
                        S["best"], S["best_r"] = q2, r
            save()


if __name__ == "__main__":
    main()
