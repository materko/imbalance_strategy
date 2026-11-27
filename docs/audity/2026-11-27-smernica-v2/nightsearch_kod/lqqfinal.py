import json, sys, subprocess
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
import lqq, liqsearch as L
from evalcore import evaluate
from tradebot.strategies.liquidity.config import LiquidityConfig
ROOT = lqq.ROOT
rows = [d for d in map(json.loads, open("lqq.jsonl")) if d["r"]]
pick = {}
for name, lo, hi in [("A", 170, 200), ("B", 130, 160), ("C", 190, 230)]:
    g = [d for d in rows if lo <= d["r"]["last"]["trades"] < hi and (d["r"].get("prev") or {}).get("winrate", 0) >= 69]
    pick[name] = max(g, key=lambda d: (d["r"]["last"]["winrate"], d["r"]["last"]["pnl_abs"]))
defaults = LiquidityConfig().to_dict()
for name, d in pick.items():
    p = lqq.enc(d["p"]); tf = d["p"]["_tf"]
    ws = [evaluate(p, tf, w) for w in L.W5]
    last = ws[-1]; tr = sum(w["trades"] for w in ws); wn = sum(w["wins"] for w in ws)
    fname = f"LQQ_{name}_RR0_5_{last['trades']}obch_WR{int(last['winrate'])}"
    per = ", ".join(f"{w[2:4]}/{w[11:13]}: {x['trades']} obch {x['winrate']:.1f} % PF {x['profit_factor']:.2f} {x['pnl_abs']:+.0f} $" for w, x in zip(L.W5, ws))
    ttl = (f"Liquidity sweep RR 0.5, filtre kvality zón: posl. rok {last['trades']} obch, {last['winrate']:.1f} % WR, "
           f"PF {last['profit_factor']:.2f}; 5 rokov {100*wn/tr:.1f} % WR")
    prof = dict(defaults); prof.update(p)
    prof.update({"_title": ttl, "_comment": [ttl, "Po rokoch: " + per, "Testy 28.9.2026, emulátor MultiCharts, MNQ, BEZ nákladov."],
                 "_strategy": "liquidity", "_instrument": "mnq_databento", "_timeframe": f"{tf}m",
                 "_timerange": L.W5[-1], "_fee": 0.0, "_wallet": 10000.0, "_detail": False})
    fn = ROOT / "tester" / "profiles" / f"{fname}.json"
    json.dump(prof, open(fn, "w"), ensure_ascii=False, indent=2)
    r = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "run", "--strategy", "liquidity",
                        "--profile", str(fn.relative_to(ROOT)), "--pair", "MNQ/USD", "--engine", "multicharts",
                        "--timeframe", f"{tf}m", "--timerange", L.W5[-1], "--fee", "0", "--wallet", "10000",
                        "--note", f"Liquidity filtre kvality zón: {fname}"], capture_output=True, text=True, cwd=ROOT)
    rid = [l for l in r.stdout.split() if l.startswith("2026")][:1]
    print(json.dumps({"name": fname, "rid": rid, "ws": ws, "wr5": round(100*wn/tr, 1), "tr5": tr,
                      "p": {k: d["p"][k] for k in ("tradeDirection", "entryModel", "sweepMinDepthAtr", "sweepMaxDepthAtr", "trendFilter", "trendEmaLen", "liqMinAgeBars", "sweepVolMult", "liqMinStrength")}}))
    print(r.stdout[-400:], r.stderr[-300:])
