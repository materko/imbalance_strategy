"""Finálne tabuľky a profily zo súboru hľadania. python genfinal.py <modul hľadania> <prefix profilov> [save]
Modul (crtsearch / s3search) dáva KEY, INSTS, enc, LAST a súbor výsledkov."""
import importlib, json, subprocess, sys
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
M = importlib.import_module(sys.argv[1]); PRE = sys.argv[2]; SAVE = len(sys.argv) > 3 and sys.argv[3] == "save"
from allcore import evaluate
from tradebot.strategies import STRATEGIES
from tradebot.core.types import INSTRUMENTS
ROOT = M.ROOT; PREV = "20240904-20250904"
FILE = {"crt": "crt.jsonl", "scalp3ma": "s3.jsonl"}[M.KEY]
SHORT = {"mnq_databento": "MNQ", "mgc_databento": "MGC", "btcusdt_binance": "BTC", "eurusd_dukascopy": "EURUSD"}
PAIR = {"mnq_databento": "MNQ/USD", "mgc_databento": "MGC/USD", "btcusdt_binance": "BTC/USDT:USDT", "eurusd_dukascopy": "EURUSD/USD"}
BANDS = [(30, 60), (60, 100), (100, 150), (150, 200), (200, 300), (300, 100000)]
SHOW = {"crt": ["rangeTF", "sweepKind", "entryModel", "tpMode", "rrRatio", "requireHtfClose", "tradeDirection", "entryOrderType"],
        "scalp3ma": ["ma1Len", "ma2Len", "ma3Len", "fractalSide", "slMode", "rrRatio", "rsiExit", "beAtR", "tradeDirection", "entryOrderType"]}[M.KEY]
rows = {i: [] for i in M.INSTS}
for l in open(ROOT / ".nightsearch" / FILE):
    d = json.loads(l)
    if d["r"] and d["r"]["pnl_abs"] > 0 and d["r"]["trades"] >= 30:
        rows[d["inst"]].append(d)
md, picked = [], []
def line(tag, inst, d):
    r, p = d["r"], d["p"]
    d["prev"] = d.get("prev") or evaluate(M.enc(p), int(p["_tf"]), PREV, inst)
    desc = ", ".join(f"{k}={p[k]}" for k in SHOW)
    return (f"| {tag} | {r['trades']} | **{r['winrate']:.1f} %** | {r['payoff_r']:.2f} | {r['profit_factor']:.2f} | {r['pnl_abs']:+.0f} | "
            f"{r['max_drawdown_abs']:.0f} | {p['_tf']}m | {desc} | {d['prev']['trades']} / {d['prev']['winrate']:.1f} % / PF {d['prev']['profit_factor']:.2f} |")
HDR = ["| | obch | WR | zisk:strata (R) | PF | zisk | maxDD | TF | nastavenie | rok 24/25: obch / WR / PF |", "|---|---|---|---|---|---|---|---|---|---|"]
for inst in M.INSTS:
    g = rows[inst]
    md += [f"\n## {SHORT[inst]} — {len(g)} ziskových nastavení\n", "### Najvyšší WR podľa počtu obchodov (zisk:strata aspoň 0,9)\n"] + HDR
    for lo, hi in BANDS:
        h = [d for d in g if lo <= d["r"]["trades"] < hi and d["r"].get("payoff_r", 0) >= 0.9]
        if h:
            d = max(h, key=lambda d: (d["r"]["winrate"], d["r"]["profit_factor"]))
            md.append(line(f"{lo}–{hi if hi < 100000 else '…'}", inst, d)); picked.append((inst, d))
    md += ["\n### Najvyšší profit factor (aspoň 100 obchodov) a najvyšší zisk\n"] + HDR
    h = [d for d in g if d["r"]["trades"] >= 100]
    if h:
        for tag, key in (("PF", lambda d: d["r"]["profit_factor"]), ("zisk", lambda d: d["r"]["pnl_abs"])):
            d = max(h, key=key); md.append(line(tag, inst, d)); picked.append((inst, d))
out = "\n".join(md)
open(ROOT / ".nightsearch" / f"{PRE}_report.md", "w").write(out); print(out)
if SAVE:
    seen = set()
    for inst, d in picked:
        r, p = d["r"], d["p"]
        name = f"{PRE}_{SHORT[inst]}_{r['trades']}obch_WR{int(r['winrate'])}_PF{str(round(r['profit_factor'], 1)).replace('.', '_')}"
        if name in seen:
            continue
        seen.add(name)
        prof = STRATEGIES[M.KEY].config_cls().to_dict(); prof.update(M.enc(p))
        ttl = (f"{STRATEGIES[M.KEY].title} {SHORT[inst]}: posl. rok {r['trades']} obch, {r['winrate']:.1f} % WR, zisk:strata {r['payoff_r']:.2f} R, "
               f"PF {r['profit_factor']:.2f}, {r['pnl_abs']:+.0f}")
        tf = f"{p['_tf']}m" if p["_tf"] < 60 else "1h"
        prof.update({"_title": ttl, "_comment": [ttl, f"Predch. rok 24/25: {d['prev']['trades']} obch, {d['prev']['winrate']:.1f} % WR, PF {d['prev']['profit_factor']:.2f}",
                     "Testy 2.10.2026, emulátor MultiCharts, BEZ nákladov."],
                     "_instrument": inst, "_timeframe": tf, "_timerange": M.LAST, "_fee": 0.0, "_wallet": 10000.0, "_detail": False})
        fn = ROOT / "tester" / "profiles" / f"{name}.json"
        json.dump(prof, open(fn, "w"), ensure_ascii=False, indent=2)
        res = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "run", "--strategy", M.KEY,
                              "--profile", str(fn.relative_to(ROOT)), "--pair", PAIR[inst], "--engine", "multicharts",
                              "--timeframe", tf, "--timerange", M.LAST, "--fee", "0", "--wallet", "10000",
                              "--note", f"{STRATEGIES[M.KEY].title} testy (posledný rok): {name}"], capture_output=True, text=True, cwd=ROOT)
        ln = [x for x in res.stdout.splitlines() if "obchodov" in x][-1:]
        print(name, "|", ln[0][:150] if ln else (res.stdout[-200:] + res.stderr[-300:]))
