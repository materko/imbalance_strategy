"""Finálne tabuľky: všetky stratégie × MNQ/MGC/BTC, RR 1:1, posledný rok, len stop a cieľ.
python allfinal.py [save]"""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import allsearch as A
from allcore import evaluate
from tradebot.strategies import STRATEGIES

ROOT = A.ROOT
SAVE = len(sys.argv) > 1 and sys.argv[1] == "save"
PREV = "20240904-20250904"
PAIR = {"mnq_databento": "MNQ/USD", "mgc_databento": "MGC/USD", "btcusdt_binance": "BTC/USDT:USDT"}
SHORT = {"mnq_databento": "MNQ", "mgc_databento": "MGC", "btcusdt_binance": "BTC"}
BANDS = [(180, 100000, "200+"), (140, 180, "150"), (90, 140, "100"), (50, 90, "60")]


def ok(r):
    return r and r["pnl_abs"] > 0 and r.get("payoff_r", 0) >= 0.9


rows = {}
for k in A.KEYS:
    fn = ROOT / ".nightsearch" / f"all_{k}.jsonl"
    if not fn.exists():
        continue
    for l in open(fn):
        d = json.loads(l)
        if ok(d["r"]):
            rows.setdefault((k, d["inst"]), []).append(d)


def best(g, lo, hi):
    g = [d for d in g if lo <= d["r"]["trades"] < hi]
    return max(g, key=lambda d: (d["r"]["winrate"], d["r"]["profit_factor"])) if g else None


md = ["| stratégia | nástroj | TF | obch | WR | zisk:strata | PF | zisk | maxDD | WR 24/25 |",
      "|---|---|---|---|---|---|---|---|---|---|"]
picked = []
for (k, inst), g in sorted(rows.items(), key=lambda kv: -max((d["r"]["winrate"] for d in kv[1] if d["r"]["trades"] >= 180), default=0)):
    d = best(g, 180, 100000)
    if d is None:
        continue
    r = d["r"]
    prev = evaluate(A.enc(k, d["p"]), int(d["p"]["_tf"]), PREV, inst)
    d["prev"] = prev
    picked.append((k, inst, d))
    md.append(f"| {STRATEGIES[k].title.split(' —')[0]} (`{k}`) | {SHORT[inst]} | {d['p']['_tf']}m | {r['trades']} | **{r['winrate']:.1f} %** | "
              f"{r['payoff_r']:.2f} | {r['profit_factor']:.2f} | {r['pnl_abs']:+.0f} | {r['max_drawdown_abs']:.0f} | {prev['winrate']:.1f} % |")

md2 = ["| stratégia | nástroj | ~60 obch | ~100 obch | ~150 obch | 200+ obch |", "|---|---|---|---|---|---|"]
for (k, inst), g in sorted(rows.items()):
    cells = []
    for lo, hi, _ in reversed(BANDS):
        d = best(g, lo, hi)
        cells.append(f"{d['r']['winrate']:.1f} % ({d['r']['trades']})" if d else "–")
    md2.append(f"| `{k}` | {SHORT[inst]} | " + " | ".join(cells) + " |")

out = "## Najlepšie pri 180+ obchodoch za rok (RR 1:1, posledný rok)\n\n" + "\n".join(md) + \
      "\n\n## Najvyšší WR podľa počtu obchodov (WR, v zátvorke obchody)\n\n" + "\n".join(md2) + "\n"
open(ROOT / ".nightsearch" / "ALL_report.md", "w").write(out)
print(out)

if SAVE:
    for k, inst, d in picked:
        r, p = d["r"], d["p"]
        if r["winrate"] < 63:
            continue
        name = f"R1_{k}_{SHORT[inst]}_{r['trades']}obch_WR{int(r['winrate'])}"
        prof = STRATEGIES[k].config_cls().to_dict(); prof.update(A.enc(k, p))
        ttl = (f"{STRATEGIES[k].title.split(' —')[0]} {SHORT[inst]} RR 1:1: posl. rok {r['trades']} obch, {r['winrate']:.1f} % WR, "
               f"PF {r['profit_factor']:.2f}, {r['pnl_abs']:+.0f} (len stop a cieľ)")
        prof.update({"_title": ttl, "_comment": [ttl, f"Predch. rok 24/25: {d['prev']['trades']} obch, {d['prev']['winrate']:.1f} % WR",
                     "Testy 30.9.-1.10.2026, emulátor MultiCharts, BEZ nákladov, bez konca seansy a trailingu."],
                     "_instrument": inst, "_timeframe": f"{p['_tf']}m", "_timerange": A.LAST, "_fee": 0.0,
                     "_wallet": 10000.0, "_detail": False})
        fn = ROOT / "tester" / "profiles" / f"{name}.json"
        json.dump(prof, open(fn, "w"), ensure_ascii=False, indent=2)
        res = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "run", "--strategy", k,
                              "--profile", str(fn.relative_to(ROOT)), "--pair", PAIR[inst], "--engine", "multicharts",
                              "--timeframe", f"{p['_tf']}m", "--timerange", A.LAST, "--fee", "0", "--wallet", "10000",
                              "--note", f"Testy RR 1:1 (200 obch, posledný rok): {name}"], capture_output=True, text=True, cwd=ROOT)
        line = [x for x in res.stdout.splitlines() if "obchodov" in x][-1:]
        print(name, "|", line[0][:160] if line else res.stderr[-300:])
