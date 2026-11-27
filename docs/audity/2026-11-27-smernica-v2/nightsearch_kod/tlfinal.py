"""Záver nočných testov Trendlines: finalisti po RR z 1-ročnej a 5-ročnej fázy, profily, behy, tabuľky.

python tlfinal.py [--dry]
"""
import json, sys, subprocess, math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
ROOT = Path("/Users/martin/IBS")
NS = ROOT / ".nightsearch"
W5 = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904"]
RRS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
DRY = "--dry" in sys.argv


def enc(c):
    p = {k: v for k, v in c.items() if k != "_tf"}
    for k in ("touchTolAtr", "breakBufferAtr", "slBufferAtr", "slAtrMult"):
        if not isinstance(p[k], dict):
            p[k] = {"value": p[k], "unit": "atr"}
    if not isinstance(p["minSlDistance"], dict):
        p["minSlDistance"] = {"value": p["minSlDistance"], "unit": "pct"}
    return p


def ev(args):
    """Súhrn aj priemerný zisk/strata na obchod (v $ a v R) — reálny pomer výhry k strate."""
    c, tr = args
    import io, contextlib, os, tempfile
    import pandas as pd
    from evalcore import m1, INST, TMP
    from tradebot.core import load_profile
    from tester.webapp.results import timerange_ms
    from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        pth = TMP / f"f{os.getpid()}.json"
        pth.write_text(json.dumps(enc(c)))
        cfg, _ = load_profile(pth, engine="multicharts")
        f, t = timerange_ms(tr)
        res, _ = emulate(cfg, INST, m1(), int(c["_tf"]), from_ms=f, to_ms=t, fee=0.0)
        rows = rows_from_trades(res.trades, INST, 0.0, 1.0)
        s, _ = summarize(rows, 10000.0, res, currency=INST.quote_currency)
    df = pd.DataFrame(rows) if len(rows) else None
    out = {k: s.get(k) for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_pct")}
    if df is not None and "profit_abs" in df:
        w = df[df.profit_abs > 0].profit_abs; l = df[df.profit_abs <= 0].profit_abs
        out["avg_win"] = float(w.mean()) if len(w) else 0.0
        out["avg_loss"] = float(-l.mean()) if len(l) else 0.0
    return out


def load(fn):
    p = NS / fn
    if not p.exists():
        return []
    return [d for d in (json.loads(l) for l in open(p)) if d["r"]]


def _score(r, rr, five):
    be = 100.0 / (1.0 + rr)
    if five:
        ws = r.get("w5") or []
        if not ws:
            return -1e9
        tr = sum(w["trades"] for w in ws); wn = sum(w["wins"] for w in ws)
        py = tr / 5
        if py < 60:
            return -1e6
        return ((100.0 * wn / tr - be) * 3 + 25 * math.log10(min(py, 600) / 100) - 0.4 * max(0, 300 - py)
                - 8 * sum(1 for w in ws if w["pnl_abs"] <= 0))
    t = r["trades"] or 0
    if t < 60 or r["pnl_abs"] <= 0:
        return -1e6
    return (r["winrate"] - be) * 3 + 25 * math.log10(min(t, 600) / 100) - 0.4 * max(0, 300 - t)


def pick(rows, rr, five):
    g = [d for d in rows if d["p"]["rrRatio"] == rr]
    g = [(d, _score(d["r"], rr, five)) for d in g]
    g = [x for x in g if x[1] > -1e5]
    return max(g, key=lambda x: x[1])[0] if g else None


def main():
    one, five = load("tl1.jsonl"), load("tl5.jsonl")
    finals = []
    for phase, rows, fv in (("1R", one, False), ("5R", five, True)):
        for rr in RRS:
            d = pick(rows, rr, fv)
            if d:
                finals.append({"phase": phase, "rr": rr, "p": d["p"]})
    jobs = [(f["p"], w) for f in finals for w in W5]
    with ProcessPoolExecutor(9) as ex:
        res = list(ex.map(ev, jobs))
    for i, f in enumerate(finals):
        f["win"] = dict(zip(W5, res[i * 5:(i + 1) * 5]))
    json.dump(finals, open(NS / "tlfinal.json", "w"))

    from tradebot.strategies.trendlines.config import TrendlineConfig
    defaults = TrendlineConfig().to_dict()
    md = ["# Trendlines — nočné testy 26.–27. 9. 2026 (MNQ, emulátor MultiCharts, bez nákladov, riziko 100 $/obchod)", ""]
    for phase, title in (("1R", "1. fáza — najlepšie na poslednom roku (20250904–20260904)"),
                         ("5R", "2. fáza — najlepšie na piatich rokoch (2021–2026)")):
        md += [f"## {title}", "",
               "| RR | profil | TF grafu / čiar | vstup | posl. rok: obch / WR / PF / zisk | reálny zisk:strata | 5 rokov: obch / WR / PF | ziskové roky |",
               "|---|---|---|---|---|---|---|---|"]
        for f in [x for x in finals if x["phase"] == phase]:
            ws = [f["win"][w] for w in W5]; last = ws[-1]; p = f["p"]
            tt = sum(w["trades"] for w in ws); wn = sum(w["wins"] for w in ws)
            gp = sum(w["pnl_abs"] for w in ws if w["pnl_abs"] > 0); prof_years = sum(1 for w in ws if w["pnl_abs"] > 0)
            pf5 = (sum(w["profit_factor"] * 1 for w in ws) / 5)
            payoff = (last.get("avg_win", 0) / last["avg_loss"]) if last.get("avg_loss") else 0
            name = f"TL_{phase}_RR{str(f['rr']).replace('.', '_')}_{last['trades']}obch_WR{int(last['winrate'])}"
            f["name"] = name
            md.append(f"| {f['rr']} | `{name}` | {p['_tf']}m / {p['lineTF']}m | {p['entryMode']} | "
                      f"{last['trades']} / {last['winrate']:.1f} % / {last['profit_factor']:.2f} / {last['pnl_abs']:+.0f} $ | "
                      f"{payoff:.2f} | {tt} / {100 * wn / max(tt, 1):.1f} % / {pf5:.2f} | {prof_years}/5 |")
            per = ", ".join(f"{w[2:4]}/{w[11:13]}: {x['trades']} obch {x['winrate']:.1f} % PF {x['profit_factor']:.2f} {x['pnl_abs']:+.0f} $"
                            for w, x in zip(W5, ws))
            prof = dict(defaults); prof.update(enc(p))
            ttl = (f"Trendlines {phase} RR {f['rr']}: posl. rok {last['trades']} obch, {last['winrate']:.1f} % WR, "
                   f"PF {last['profit_factor']:.2f}; 5 rokov {tt} obch, {100 * wn / max(tt, 1):.1f} % WR, ziskove {prof_years}/5")
            prof.update({"_title": ttl, "_comment": [ttl, "Po rokoch: " + per,
                         "Nocne testy 26.-27.9.2026, emulator MultiCharts, MNQ, BEZ nakladov, riziko 100 $/obchod."],
                         "_strategy": "trendlines", "_instrument": "mnq_databento", "_timeframe": f"{p['_tf']}m",
                         "_timerange": W5[-1], "_fee": 0.0, "_wallet": 10000.0, "_detail": False})
            f["profile"] = prof
        md.append("")
    md += ["„Reálny zisk:strata“ je priemerný ziskový obchod delený priemerným stratovým (posledný rok) — "
           "pri trailingu a časovom limite sa líši od nastaveného RR.", ""]
    (NS / "tl_report.md").write_text("\n".join(md))
    print("\n".join(md))
    if DRY:
        return
    for f in finals:
        fn = ROOT / "tester" / "profiles" / f"{f['name']}.json"
        json.dump(f["profile"], open(fn, "w"), ensure_ascii=False, indent=2)
        r = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "run", "--strategy", "trendlines",
                            "--profile", str(fn.relative_to(ROOT)), "--pair", "MNQ/USD", "--engine", "multicharts",
                            "--timeframe", f"{f['p']['_tf']}m", "--timerange", W5[-1], "--fee", "0", "--wallet", "10000",
                            "--note", f"Trendlines nocne testy: {f['name']}"], capture_output=True, text=True, cwd=ROOT)
        print(f["name"], [l for l in r.stdout.splitlines() if "PnL" in l][-1:] or r.stderr[-200:])


if __name__ == "__main__":
    main()
