"""Alternatívy RR 0,5 z tabuľky: najlepší WR (5 rokov) v pásmach počtu obchodov 200-320/rok -> profily + behy."""
import json, subprocess, sys
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
import lqfinal as T
from tradebot.strategies.liquidity.config import LiquidityConfig
ROOT = T.ROOT
rows = [d for d in T.load("lqr05.jsonl") if d["r"].get("w5")]
bands = [(200, 225), (225, 250), (250, 275), (275, 300), (300, 320)]
defaults = LiquidityConfig().to_dict()
for lo, hi in bands:
    g = []
    for d in rows:
        ws = d["r"]["w5"]; tr = sum(w["trades"] for w in ws); wn = sum(w["wins"] for w in ws)
        if lo <= tr / 5 < hi and all(w["pnl_abs"] > 0 for w in ws):
            g.append((100 * wn / tr, d))
    if not g:
        continue
    wr5, d = max(g, key=lambda x: x[0])
    ws = d["r"]["w5"]; last = ws[-1]; tr = sum(w["trades"] for w in ws)
    name = f"LQR05_ALT_{int(tr / 5)}obch_WR{int(wr5)}"
    per = ", ".join(f"{w[2:4]}/{w[11:13]}: {x['trades']} obch {x['winrate']:.1f} % PF {x['profit_factor']:.2f} {x['pnl_abs']:+.0f} $"
                    for w, x in zip(T.W5, ws))
    ttl = (f"Liquidity sweep RR 0.5 (alternativa {lo}-{hi} obch/rok): posl. rok {last['trades']} obch, "
           f"{last['winrate']:.1f} % WR, PF {last['profit_factor']:.2f}; 5 rokov {wr5:.1f} % WR, ziskove 5/5")
    prof = dict(defaults); prof.update(T.enc(d["p"]))
    prof.update({"_title": ttl, "_comment": [ttl, "Po rokoch: " + per, "Testy 27.9.2026, emulator MultiCharts, MNQ, BEZ nakladov, riziko 100 $/obchod."],
                 "_strategy": "liquidity", "_instrument": "mnq_databento", "_timeframe": f"{d['p']['_tf']}m",
                 "_timerange": T.W5[-1], "_fee": 0.0, "_wallet": 10000.0, "_detail": False})
    fn = ROOT / "tester" / "profiles" / f"{name}.json"
    json.dump(prof, open(fn, "w"), ensure_ascii=False, indent=2)
    r = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "run", "--strategy", "liquidity",
                        "--profile", str(fn.relative_to(ROOT)), "--pair", "MNQ/USD", "--engine", "multicharts",
                        "--timeframe", f"{d['p']['_tf']}m", "--timerange", T.W5[-1], "--fee", "0", "--wallet", "10000",
                        "--note", f"Liquidity testy: {name}"], capture_output=True, text=True, cwd=ROOT)
    line = [l for l in r.stdout.splitlines() if "PnL" in l][-1:]
    print(name, line[0] if line else r.stderr[-200:])
