"""Finálne tabuľky a profily víkendového hľadania. python wkfinal.py [save]
Pre každú stratégiu a nástroj: najvyšší WR pri 150+ obchodoch v triedach reálneho zisk:strata (RR), najvyšší PF a zisk;
ku každému riadku predošlý rok. Výstup WK_report.md, profily WK_* a behy v histórii webapp."""
import json, os, subprocess, sys
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import wksearch as W
from allcore import evaluate as _evaluate
from tradebot.strategies import STRATEGIES
SAVE = len(sys.argv) > 1 and sys.argv[1] == "save"
COLLECT = len(sys.argv) > 1 and sys.argv[1] == "prefetch"
ROOT = W.ROOT; PREV = "20240904-20250904"
PY = str(ROOT / ".venv/bin/python")
CACHE_F = ROOT / ".nightsearch" / "wkfinal_cache.json"
JOBS_F = ROOT / ".nightsearch" / "wkfinal_jobs.json"
if SAVE:
    # prepočty ďalších rokov najprv paralelne (inak by záver trval ~1,5 h): zber úloh → wkprefetch.py → cache
    subprocess.run([PY, __file__, "prefetch"], cwd=ROOT / ".nightsearch", stdout=subprocess.DEVNULL)
    subprocess.run([PY, str(ROOT / ".nightsearch" / "wkprefetch.py")], cwd=ROOT / ".nightsearch")
CACHE = json.load(open(CACHE_F)) if CACHE_F.exists() else {}
JOBS = {}
DUMMY = {"trades": 0, "wins": 0, "winrate": 0.0, "pnl_abs": 0.0, "profit_factor": 0.0, "max_drawdown_abs": 0.0, "payoff_r": 0.0}


def evaluate(params, tf, timerange, inst):
    k = json.dumps([params, tf, timerange, inst], sort_keys=True)
    if k in CACHE:
        return CACHE[k]
    if COLLECT:
        JOBS[k] = [params, tf, timerange, inst]
        return dict(DUMMY)
    CACHE[k] = _evaluate(params, tf, timerange, inst)
    return CACHE[k]

PREV2 = W.PREV2                                         #: tretí rok, hľadanie ho použilo na „hlavu a pätu"
PREV3 = W.PREV3
OOS = ["20210904-20220904"]                             #: rok, ktorý hľadanie nikdy nevidelo — nezávislá kontrola
SHORT = {"mnq_databento": "MNQ", "mgc_databento": "MGC", "btcusdt_binance": "BTC"}
PAIR = {"mnq_databento": "MNQ/USD", "mgc_databento": "MGC/USD", "btcusdt_binance": "BTC/USDT:USDT"}
SHOW = {"jss": ["structTF", "refineTF", "triggerMode", "zoneType", "entryModel", "useFibo", "rrRatio", "tradeDirection", "entryOrderType"],
        "crt": ["rangeTF", "sweepKind", "entryModel", "rrRatio", "tradeDirection", "entryConfirm", "entryOrderType"],
        "scalp3ma": ["ma1Len", "ma2Len", "ma3Len", "fractalSide", "slMode", "rrRatio", "tradeDirection", "entryConfirm", "entryOrderType"],
        "fibo": ["swingTF", "legMinAtr", "levelMode", "entryModel", "slMode", "rrRatio", "tradeDirection", "entryOrderType"],
        "svp": ["pocSource", "tradeMode", "entryModel", "useFibo", "slAtr", "rrRatio", "tradeDirection", "entryOrderType"],
        "fvgpolarity": ["slPoints", "fvgMinSize", "fvgMaxSize", "tpLevel", "tradeDirection", "entryConfirm", "entryOrderType"]}
THR = [round(0.9 * rr, 3) for rr in W.RRS] + [2.3]   # RR len do 2 (s rezervou na reálny pomer)
#: triedy podľa reálneho zisk:strata: riadok „RR 1" = zisk:strata od 0,9 po 1,125 (ďalšie RR)
CLASSES = [(f"RR {str(rr).replace('.', ',')}", THR[i], THR[i + 1]) for i, rr in enumerate(W.RRS)]
HDR = ["| | obch | WR | zisk:strata (R) | PF | zisk | maxDD | TF | nastavenie | 24/25: obch / WR / PF / zisk | 23/24: obch / WR / PF / zisk | "
       "22/23: WR / PF / zisk | nevidený 21/22: obch / WR / PF / zisk |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
md = ["# Víkendové hľadanie 2.–5. 10. 2026 — posledný rok (4. 9. 2025 – 4. 9. 2026)\n",
      "Bez trailingu a konca seansy (len stop a cieľ), bez nákladov, emulátor MultiCharts. Hľadalo sa min. 150 obchodov, WR 70–100 %, RR 0,5–2,0; „hlava a päta“ = ziskové v 4 rokoch, rok 21/22 je nezávislá kontrola.\n"]
summary = ["| stratégia | nástroj | skúšaných | 150+ obch a zisk | najvyšší WR pri 150+ (obch, zisk:strata) | to isté v 24/25 | WR ≥ 70 % pri 150+ |", "|---|---|---|---|---|---|---|"]
picked = []
robust = ["| stratégia | nástroj | ziskových v 4 rokoch | najlepšie: 25/26 | 24/25 | 23/24 | 22/23 | nevidený 21/22 |", "|---|---|---|---|---|---|---|---|"]
for key in W.KEYS:
    fn = ROOT / ".nightsearch" / f"wk_{key}.jsonl"
    if not fn.exists():
        continue
    rows = {i: [] for i in W.INSTS}; n_all = {i: 0 for i in W.INSTS}; rob = {i: [] for i in W.INSTS}
    bf = ROOT / ".nightsearch" / f"wkbf_{key}.jsonl"
    bf2 = ROOT / ".nightsearch" / f"wkbf2_{key}.jsonl"
    for l in [*open(fn), *(open(bf) if bf.exists() else []), *(open(bf2) if bf2.exists() else [])]:
        try:
            d = json.loads(l)
        except ValueError:
            continue
        n_all[d["inst"]] += 1
        r = d["r"]
        if r and r["pnl_abs"] > 0 and r["trades"] >= W.MIN_T:
            rows[d["inst"]].append(d)
            rp, rp2, rp3 = d.get("rp"), d.get("rp2"), d.get("rp3")
            if rp:
                d["prev"] = rp
            if rp and rp2 and rp3 and min(x["pnl_abs"] for x in (rp, rp2, rp3)) > 0 and min(x["trades"] for x in (rp, rp2, rp3)) >= 120:
                rob[d["inst"]].append(d)
    title = STRATEGIES[key].title.split(" —")[0]
    def line(tag, inst, d):
        r, p = d["r"], d["p"]
        if "prev" not in d:
            d["prev"] = evaluate(W.enc(key, p), int(p["_tf"]), PREV, inst)
        pv = d["prev"]
        if not d.get("rp2"):
            d["rp2"] = evaluate(W.enc(key, p), int(p["_tf"]), PREV2, inst)
        if "oos" not in d:
            d["oos"] = [evaluate(W.enc(key, p), int(p["_tf"]), w, inst) for w in OOS]
        if not d.get("rp3"):
            d["rp3"] = evaluate(W.enc(key, p), int(p["_tf"]), PREV3, inst)
        p2, p3 = d["rp2"], d["rp3"]
        oo = "; ".join(f"{x['trades']} / {x['winrate']:.1f} % / PF {x['profit_factor']:.2f} / {x['pnl_abs']:+.0f}" for x in d["oos"])
        desc = ", ".join(f"{k}={p[k]}" for k in SHOW[key] if k in p)
        return (f"| {tag} | {r['trades']} | **{r['winrate']:.1f} %** | {W.pay(r):.2f} | {r['profit_factor']:.2f} | {r['pnl_abs']:+.0f} | "
                f"{r['max_drawdown_abs']:.0f} | {p['_tf']}m | {desc} | {pv['trades']} / {pv['winrate']:.1f} % / PF {pv['profit_factor']:.2f} / {pv['pnl_abs']:+.0f} | "
                f"{p2['trades']} / {p2['winrate']:.1f} % / PF {p2['profit_factor']:.2f} / {p2['pnl_abs']:+.0f} | "
                f"{p3['winrate']:.1f} % / PF {p3['profit_factor']:.2f} / {p3['pnl_abs']:+.0f} | {oo} |")
    for inst in W.INSTS:
        g = rows[inst]
        md += [f"\n## {title} — {SHORT[inst]} ({n_all[inst]} skúšaných, {len(g)} ziskových so 150+ obchodmi)\n"] + HDR
        best = None
        for tag, lo, hi in CLASSES:
            h = [d for d in g if lo <= W.pay(d["r"]) < hi]
            if h:
                d = max(h, key=lambda d: (d["r"]["winrate"], d["r"]["profit_factor"]))
                md.append(line(tag, inst, d)); picked.append((key, inst, d))
                if best is None or d["r"]["winrate"] > best["r"]["winrate"]:
                    best = d
            else:
                md.append(f"| {tag} | – | – | – | – | – | – | – | žiadne ziskové nastavenie so 150+ obchodmi | – | – | – | – |")
        if g:
            for tag, kf in (("najvyšší PF", lambda d: d["r"]["profit_factor"]), ("najvyšší zisk", lambda d: d["r"]["pnl_abs"])):
                d = max(g, key=kf); md.append(line(tag, inst, d))
        # „hlava a päta": ziskové v oboch rokoch, radené podľa horšieho z dvoch WR
        md += [f"\n### {title} — {SHORT[inst]}: drží v štyroch rokoch ({len(rob[inst])} nastavení ziskových v 25/26, 24/25, 23/24 aj 22/23)\n"] + HDR
        rbest = None
        for tag, lo, hi in CLASSES:
            h = [d for d in rob[inst] if lo <= min(W.pay(d["r"]), W.pay(d["prev"]), W.pay(d["rp2"]), W.pay(d["rp3"])) and W.pay(d["r"]) < hi]
            if h:
                d = max(h, key=lambda d: (min(d["r"]["winrate"], d["prev"]["winrate"], d["rp2"]["winrate"], d["rp3"]["winrate"]),
                                          d["r"]["profit_factor"]))
                md.append(line(tag, inst, d)); picked.append((key, inst, d))
                if rbest is None or min(d["r"]["winrate"], d["prev"]["winrate"], d["rp2"]["winrate"], d["rp3"]["winrate"]) > \
                        min(rbest["r"]["winrate"], rbest["prev"]["winrate"], rbest["rp2"]["winrate"], rbest["rp3"]["winrate"]):
                    rbest = d
            else:
                md.append(f"| {tag} | – | – | – | – | – | – | – | nič ziskové v štyroch rokoch | – | – | – | – |")
        robust.append(f"| {title} | {SHORT[inst]} | {len(rob[inst])} | " + (f"**{rbest['r']['winrate']:.1f} %** ({rbest['r']['trades']} obch, {W.pay(rbest['r']):.2f} R, PF {rbest['r']['profit_factor']:.2f}) | "
                      f"**{rbest['prev']['winrate']:.1f} %** ({rbest['prev']['trades']} obch, PF {rbest['prev']['profit_factor']:.2f}) | "
                      f"**{rbest['rp2']['winrate']:.1f} %** ({rbest['rp2']['trades']} obch, PF {rbest['rp2']['profit_factor']:.2f}) | "
                      f"**{rbest['rp3']['winrate']:.1f} %** ({rbest['rp3']['trades']} obch, PF {rbest['rp3']['profit_factor']:.2f}) | "
                      + "; ".join(f"{x['winrate']:.1f} % PF {x['profit_factor']:.2f}" for x in rbest["oos"]) + " |" if rbest else "– | – | – | – | – |"))
        n70 = sum(1 for d in g if d["r"]["winrate"] >= 70 and W.pay(d["r"]) >= 0.45)
        if best:
            r, pv = best["r"], best["prev"]
            summary.append(f"| {title} | {SHORT[inst]} | {n_all[inst]} | {len(g)} | **{r['winrate']:.1f} %** ({r['trades']}, {W.pay(r):.2f} R) | "
                           f"{pv['winrate']:.1f} % ({pv['trades']} obch, PF {pv['profit_factor']:.2f}) | {n70} |")
        else:
            summary.append(f"| {title} | {SHORT[inst]} | {n_all[inst]} | 0 | – | – | 0 |")
if COLLECT:
    json.dump(JOBS, open(JOBS_F, "w")); print("úloh na prepočet:", len(JOBS)); sys.exit(0)
out = "\n".join(md[:2] + ["\n## Súhrn — najvyšší WR na poslednom roku\n"] + summary
                + ["\n## Súhrn — čo drží v štyroch rokoch (25/26 až 22/23, radené podľa najhoršieho roka; 21/22 je nevidený)\n"] + robust + md[2:])
open(ROOT / ".nightsearch" / "WK_report.md", "w").write(out); print(out)
if SAVE:
    seen = set()
    for key, inst, d in picked:
        r, p = d["r"], d["p"]
        name = f"WK_{key}_{SHORT[inst]}_{r['trades']}obch_WR{int(r['winrate'])}_R{str(round(W.pay(r), 1)).replace('.', '_')}"
        if name in seen:
            continue
        seen.add(name)
        title = STRATEGIES[key].title.split(" —")[0]
        prof = STRATEGIES[key].config_cls().to_dict(); prof.update(W.enc(key, p))
        ttl = (f"{title} {SHORT[inst]}: posl. rok {r['trades']} obch, {r['winrate']:.1f} % WR, zisk:strata {W.pay(r):.2f} R, "
               f"PF {r['profit_factor']:.2f}, {r['pnl_abs']:+.0f}")
        pv = d["prev"]; tf = f"{p['_tf']}m" if p["_tf"] < 60 else "1h"
        oo = d["oos"]; p2 = d["rp2"]; p3 = d["rp3"]
        prof.update({"_title": ttl, "_comment": [ttl, f"Predch. rok 24/25: {pv['trades']} obch, {pv['winrate']:.1f} % WR, PF {pv['profit_factor']:.2f}, {pv['pnl_abs']:+.0f}",
                     f"Rok 23/24: {p2['trades']} obch, {p2['winrate']:.1f} % WR, PF {p2['profit_factor']:.2f}, {p2['pnl_abs']:+.0f}",
                     f"Rok 22/23: {p3['trades']} obch, {p3['winrate']:.1f} % WR, PF {p3['profit_factor']:.2f}, {p3['pnl_abs']:+.0f}",
                     "Rok, ktorý hľadanie nevidelo (21/22): " + "; ".join(f"{x['trades']} obch, {x['winrate']:.1f} % WR, PF {x['profit_factor']:.2f}, {x['pnl_abs']:+.0f}" for x in oo),
                     "Víkendové hľadanie 2.–5. 10. 2026, emulátor MultiCharts, BEZ nákladov, bez trailingu a konca seansy."],
                     "_instrument": inst, "_timeframe": tf, "_timerange": W.LAST, "_fee": 0.0, "_wallet": 10000.0, "_detail": False})
        fn = ROOT / "tester" / "profiles" / f"{name}.json"
        json.dump(prof, open(fn, "w"), ensure_ascii=False, indent=2)
        res = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "run", "--strategy", key,
                              "--profile", str(fn.relative_to(ROOT)), "--pair", PAIR[inst], "--engine", "multicharts",
                              "--timeframe", tf, "--timerange", W.LAST, "--fee", "0", "--wallet", "10000",
                              "--note", f"Víkendové hľadanie (150+ obch, WR 70+, RR 0,5–2): {name}"], capture_output=True, text=True, cwd=ROOT)
        ln = [x for x in res.stdout.splitlines() if "obchodov" in x][-1:]
        print(name, "|", ln[0][:150] if ln else (res.stdout[-200:] + res.stderr[-300:]))
    res = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "push"], capture_output=True, text=True, cwd=ROOT)
    print("push:", (res.stdout + res.stderr)[-300:])
