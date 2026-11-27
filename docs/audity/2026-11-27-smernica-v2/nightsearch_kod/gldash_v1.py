"""Dáta pre dashboard (tester/dashboard/index.html) z hľadania podľa smernice + publikovateľná stránka s dátami v sebe.
python gldash.py → .nightsearch/dash/dashboard_data.json a .nightsearch/dash/tradebot_vysledky.html"""
import json, re, sys, time
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import glsearch as G
NAMES = {"vwaporb": "VWAP ORB", "ibsentry": "IBS Entry Zone", "mag7": "SPX sila"}
SHOW = {"vwaporb": ["_tf", "nyRangeMinutes", "vwapRule", "entryTiming", "slMode", "tpMode", "rrRatio", "sessionMode", "entryOrderType", "entryConfirm", "trendFilter"],
        "ibsentry": ["rrRatio", "slLookback", "minSlDistance", "minImbSizePoints", "imbLookback", "zoneDetectionTF", "fvgMinSize", "indAdx", "maxDailyWins"],
        "mag7": ["_tf", "thr", "waitMin", "entryEnd", "slMode", "slPts", "rr", "useVwap", "useEma", "emaLen", "trendFilter"]}


def trades_for(args):
    key, p, with_oos = args
    import allcore as A, io, contextlib, os
    from tradebot.core import load_profile
    from tradebot.core.types import INSTRUMENTS
    from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades
    from tester.webapp.results import timerange_ms
    K = "mnq_databento"; inst = INSTRUMENTS[K]
    q = {k: v for k, v in p.items() if k != "_tf"}; q.update({"_strategy": key, "_instrument": K})
    fn = A.TMP / f"d{os.getpid()}.json"; fn.write_text(json.dumps(q))
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        cfg, _ = load_profile(fn, engine="multicharts")
        f, t = timerange_ms("20211001-" + ("20260904" if with_oos else "20250904"))
        res, _ = emulate(cfg, inst, A.m1(K), int(p["_tf"]), from_ms=f, to_ms=t, fee=G.FEE)
        rows = rows_from_trades(res.trades, inst, G.FEE, 1.0)
    out = []
    for r in rows:
        out.append({"open": str(r["open_date"])[:19] + "Z", "close": str(r["close_date"])[:19] + "Z",
                    "dir": "short" if r["is_short"] else "long", "entry": r["open_rate"], "exit": r["close_rate"],
                    "pnl": round(r["profit_abs"], 2), "reason": r["exit_reason"]})
    return out


def main():
    st = json.loads((G.ROOT / "gl_state.json").read_text())
    jobs, meta = [], []
    for key, S in st.items():
        seen, items = set(), []
        def add(p, r, status, cand=None):
            sig = json.dumps(p, sort_keys=True)
            if sig in seen or not r:
                return
            seen.add(sig); items.append((p, r, status, cand))
        strict = 1.3 if S["combos"] > 1000 else 1.2
        for c in reversed(S.get("candidates", [])):
            o = c.get("oos")
            ok = o and o["profit_factor"] >= strict and o["profit_factor"] >= 0.7 * c["is"]["profit_factor"]
            add(c["p"], c["is"], "prešiel odloženým rokom" if ok else ("kandidát — neprešiel odloženým rokom" if o else "kandidát — plató pod 80 %"), c)
        add(S["best"], S.get("best_r"), "najlepší na ladení")
        fn = G.ROOT / f"gl_{key}.jsonl"
        rows = [json.loads(l) for l in open(fn)] if fn.exists() else []
        for d in sorted([d for d in rows if d["r"]], key=lambda d: -G.score(d["r"]))[:8]:
            add(d["p"], d["r"], "dobrý na ladení")
        items = items[:6]
        for i, (p, r, status, cand) in enumerate(items):
            jobs.append((key, p, bool(cand and cand.get("oos"))))
            meta.append((key, i, p, r, status, cand))
    with ProcessPoolExecutor(3) as ex:
        trades = list(ex.map(trades_for, jobs))
    data = {"updated": time.strftime("%Y-%m-%d %H:%M"),
            "note": "Testovanie podľa smernice: ladenie 2021-10 – 2025-09 s poplatkom 1,755e-05 (MNQ, emulátor MultiCharts), bez trailingu a konca "
                    "seansy. Odložený rok 2025-09 – 2026-09 sa púšťa len raz na kandidáta. Výsledky z backtestu, nie obchodné odporúčanie.",
            "strategies": []}
    by = {}
    for (key, i, p, r, status, cand), tr in zip(meta, trades):
        daily = {}
        for t in tr:
            daily[t["close"][:10]] = round(daily.get(t["close"][:10], 0.0) + t["pnl"], 2)
        eq, cum = [], 0.0
        for dday in sorted(daily):
            cum += daily[dday]; eq.append([dday, round(cum, 2)])
        o = cand.get("oos") if cand else None
        s = {"id": f"{key}-{i + 1}", "label": ", ".join(f"{k}={p[k]}" for k in SHOW[key] if k in p), "status": status,
             "params": {k: p[k] for k in SHOW[key] if k in p},
             "is": {"pf": r["profit_factor"], "trades": r["trades"], "trades_per_year": round(r["trades"] / G.YEARS),
                    "winrate": r["winrate"], "pnl": r["pnl_abs"], "maxdd": r["max_drawdown_abs"],
                    "years": {k: v["pf"] for k, v in r.get("years", {}).items()}},
             "oos": ({"pf": o["profit_factor"], "trades": o["trades"], "winrate": o["winrate"], "pnl": o["pnl_abs"], "maxdd": o["max_drawdown_abs"]} if o else None),
             "plateau_min": cand.get("plateau_min") if cand else None,
             "equity": eq, "daily": sorted([[k, v] for k, v in daily.items()]), "trades": tr}
        by.setdefault(key, []).append(s)
    for key, S in st.items():
        c = S.get("candidates", [])
        passed = [s for s in by.get(key, []) if s["status"] == "prešiel odloženým rokom"]
        step = "krok 7 — analytika (checkup)" if passed else ("krok 5–6 — plató a odložený rok" if c else "krok 4 — hľadanie nastavení")
        data["strategies"].append({"key": key, "name": NAMES[key], "guideline_step": step, "combos": S["combos"], "step1": "prešiel",
                                   "settings": by.get(key, [])})
    out = G.ROOT / "dash"
    (out / "dashboard_data.json").write_text(json.dumps(data, ensure_ascii=False))
    html = open("/Users/martin/IBS/tester/dashboard/index.html").read()
    html = re.sub(r"<!doctype html>\s*", "", html, flags=re.I)
    html = re.sub(r"</?html[^>]*>|</?head>|</?body>|<meta charset[^>]*>|<meta name=\"viewport\"[^>]*>", "", html)
    html = html.replace("<title>Výsledky testovania</title>", "")
    i = html.rfind("<script>")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = html[:i] + f"<script>window.DASHBOARD_DATA = {payload};</script>\n" + html[i:]
    (out / "tradebot_vysledky.html").write_text("<title>TradeBot výsledky</title>\n" + html.strip() + "\n")
    print("strategie", [(s["name"], len(s["settings"])) for s in data["strategies"]], "veľkosť", round(len(html) / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
