"""FVG POLARITY — finálne tabuľky a profily. python fvpfinal.py [save]"""
import json, subprocess, sys
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import fvpsearch as F
from allcore import evaluate
from tradebot.strategies import STRATEGIES
ROOT = F.ROOT; SAVE = len(sys.argv) > 1 and sys.argv[1] == "save"
PREV = "20240904-20250904"
PAIR = {"mnq_databento": "MNQ/USD", "mgc_databento": "MGC/USD", "btcusdt_binance": "BTC/USDT:USDT"}
SHORT = {"mnq_databento": "MNQ", "mgc_databento": "MGC", "btcusdt_binance": "BTC"}
BANDS = [(30, 60), (60, 100), (100, 150), (150, 200), (200, 300), (300, 500), (500, 1000), (1000, 100000)]
rows = {i: [] for i in F.INSTS}
for l in open(ROOT / ".nightsearch" / "fvp.jsonl"):
    d = json.loads(l)
    if d["r"] and d["r"]["pnl_abs"] > 0 and d["r"]["trades"] >= 30:
        rows[d["inst"]].append(d)
md = []; picked = []
for inst in F.INSTS:
    md += [f"\n## {SHORT[inst]} — {len(rows[inst])} ziskových nastavení\n",
           "| obch/rok | obch | WR | zisk:strata (R) | PF | zisk | maxDD | TF | SL (body) | FVG min–max | cieľ | smer | vstup | WR 24/25 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for lo, hi in BANDS:
        g = [d for d in rows[inst] if lo <= d["r"]["trades"] < hi]
        g.sort(key=lambda d: (-d["r"]["winrate"], -d["r"]["profit_factor"]))
        seen = set(); n = 0
        for d in g:
            key = (d["r"]["trades"], d["r"]["winrate"])
            if key in seen:
                continue
            seen.add(key); n += 1
            r, p = d["r"], d["p"]
            d["prev"] = evaluate(F.enc(p), int(p["_tf"]), PREV, inst)
            picked.append((inst, d))
            ent = "market" if p["entryOrderType"] == "market" else f"limit {p['limitOffsetPct']} % / {p['limitValidBars']} b" + (" RR" if p["limitKeepRR"] else "")
            md.append(f"| {lo}–{hi if hi < 100000 else '…'} | {r['trades']} | **{r['winrate']:.1f} %** | {r['payoff_r']:.2f} | {r['profit_factor']:.2f} | "
                      f"{r['pnl_abs']:+.0f} | {r['max_drawdown_abs']:.0f} | {p['_tf']}m | {p['slPoints']} | {p['fvgMinSize']}–{p['fvgMaxSize'] or '∞'} | "
                      f"{p['tpLevel']} | {p['tradeDirection']} | {ent} | {d['prev']['trades']} / {d['prev']['winrate']:.1f} % |")
            if n >= 2:
                break
out = "\n".join(md)
open(ROOT / ".nightsearch" / "FVP_report.md", "w").write(out); print(out)
if SAVE:
    for inst, d in picked:
        r, p = d["r"], d["p"]
        name = f"FVP_{SHORT[inst]}_{r['trades']}obch_WR{int(r['winrate'])}"
        prof = STRATEGIES[F.KEY].config_cls().to_dict(); prof.update(F.enc(p))
        ttl = (f"FVG POLARITY {SHORT[inst]}: posl. rok {r['trades']} obch, {r['winrate']:.1f} % WR, zisk:strata {r['payoff_r']:.2f} R, "
               f"PF {r['profit_factor']:.2f}, {r['pnl_abs']:+.0f}")
        prof.update({"_title": ttl, "_comment": [ttl, f"Predch. rok 24/25: {d['prev']['trades']} obch, {d['prev']['winrate']:.1f} % WR, {d['prev']['pnl_abs']:+.0f}",
                     "Testy 1.-2.10.2026, emulátor MultiCharts, BEZ nákladov."],
                     "_instrument": inst, "_timeframe": f"{p['_tf']}m" if p["_tf"] < 60 else "1h", "_timerange": F.LAST, "_fee": 0.0,
                     "_wallet": 10000.0, "_detail": False})
        fn = ROOT / "tester" / "profiles" / f"{name}.json"
        json.dump(prof, open(fn, "w"), ensure_ascii=False, indent=2)
        res = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "run", "--strategy", F.KEY,
                              "--profile", str(fn.relative_to(ROOT)), "--pair", PAIR[inst], "--engine", "multicharts",
                              "--timeframe", prof["_timeframe"], "--timerange", F.LAST, "--fee", "0", "--wallet", "10000",
                              "--note", f"FVG POLARITY testy (posledný rok): {name}"], capture_output=True, text=True, cwd=ROOT)
        line = [x for x in res.stdout.splitlines() if "obchodov" in x][-1:]
        print(name, "|", line[0][:160] if line else (res.stdout[-200:] + res.stderr[-300:]))
