"""Priebežná tabuľka hľadania podľa smernice → iCloud SMERNICA-TESTOVANIA/PRIEBEH/priebeh_<dátum>.md."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
import glsearch as G
NAMES = {"nyva": "NY VA BREAKOUT", "nyvaes": "NY VA BREAKOUT ES", "vwaporb": "VWAP ORB", "ibsentry": "IBS Entry Zone", "mag7": "SPX sila", "jss": "JSS", "crt": "CRT + TBS", "dailyopen": "DAILY OPEN", "svp": "Volume Profile POC", "voltbreak": "Volt Break", "vwapadx": "VWAP ADX Pullback", "onbiasorb": "Overnight Bias ORB", "sweepfvg": "SWEEP FVG", "sweepengulf": "SWEEPING ENGULF", "varev": "VALUE AREA REVERSION", "fpc": "FPC 1.0 — férová cena", "range": "Range Breakout", "noa": "NOA 1.0", "noaes": "NOA 1.0 ES", "noamgc": "NOA 1.0 MGC", "silverbullet": "Silver Bullet 1.0 (ICT)", "tks": "TKS 1.0 (NQ Kompas)", "nocpon": "NOC + PONDELOK 1.0", "ibsentrymgc": "IBS EZ MGC", "scalp3mamgc": "Scalping 3MA (MGC)", "fibomgc": "Fibo 1.0 (MGC)", "ibsentryes": "IBS EZ ES"}
STEP1 = {"nyva": "✓ (6 / 50 / 20, 0 rozdielov)", "nyvaes": "✓ (6 / 50 / 20, 0 rozdielov)", "vwaporb": "✓ (6 štartov, 50 + 20 utnutí, 0 rozdielov)", "ibsentry": "✓ (6 / 50 / 20, 0 rozdielov)", "mag7": "✓ (6 / 50 / 20, 0 rozdielov)", "jss": "✓ (6 / 50 / 20, 0 rozdielov)", "crt": "✓ (6 / 50 / 20, 0 rozdielov)", "dailyopen": "✓ (6 / 50 / 20, 0 rozdielov)", "svp": "✓ (6 / 50 / 20, 0 rozdielov)", "voltbreak": "✓ (6 / 50 / 20, 0 rozdielov)", "vwapadx": "✓ (6 / 50 / 20, 0 rozdielov)", "onbiasorb": "✓ (6 / 50 / 20, 0 rozdielov)", "sweepfvg": "✓ (6 / 50 / 20, 0 rozdielov)", "sweepengulf": "✓ (6 / 50 / 20, 0 rozdielov)", "varev": "✓ (6 / 50 / 20, 0 rozdielov)", "fpc": "✓ (6 / 50 / 20, 0 rozdielov)", "range": "✓ (6 / 50 / 20, 0 rozdielov, rozbeh 15 dní)", "noa": "✓ (6 / 50 / 20, rozbeh 23 dní; 1 rozdiel = krátky rozbeh porovnania, nie pohľad dopredu)", "silverbullet": "✓ (6 / 43 / 20, 0 rozdielov)", "tks": "✓ (6 / 50 / 20, 0 rozdielov, rozbeh 19 dní)", "nocpon": "✓ (6 / 50 / 20, 0 rozdielov, rozbeh 0 dní — SMA zo seedingu)", "ibsentrymgc": "✓ (MGC)", "scalp3mamgc": "✓ (MGC)", "fibomgc": "✓ (MGC)", "ibsentryes": "✓ (ES)", "noaes": "✓ (ES, logika NOA)", "noamgc": "✓ (MGC, logika NOA)"}
SHOW = {"vwaporb": ["_tf", "nyRangeMinutes", "vwapRule", "entryTiming", "slMode", "tpMode", "rrRatio", "sessionMode", "entryOrderType", "entryConfirm", "trendFilter"],
        "ibsentry": ["rrRatio", "slLookback", "minSlDistance", "minImbSizePoints", "imbLookback", "zoneDetectionTF", "fvgMinSize", "indAdx", "maxDailyWins"],
        "mag7": ["_tf", "thr", "waitMin", "entryEnd", "slMode", "slPts", "rr", "useVwap", "useEma", "emaLen", "trendFilter"],
        "jss": ["_tf", "structTF", "swingLen", "triggerMode", "zoneType", "entryModel", "slFrom", "tpMode", "rrRatio", "tradeStartH", "tradeEndH"],
        "crt": ["_tf", "rangeTF", "sweepKind", "entryModel", "tpMode", "rrRatio", "tradeStartH", "tradeEndH", "tradeDirection", "entryOrderType"],
        "dailyopen": ["_tf", "refH", "breakPts", "entryMode", "slPts", "tpPts", "entryStartH", "entryEndH", "tradeDirection", "maxTradesPerDay", "trendFilter"],
        "svp": ["_tf", "pocSource", "tradeMode", "entryModel", "slMode", "tpMode", "rrRatio", "tradeStartH", "tradeEndH", "tradeDirection", "useFibo"],
        "voltbreak": ["_tf", "noisePct", "tpUsd", "slUsd", "maxTrades", "startHHMM", "endHHMM", "atrSource", "trendFilter"],
        "vwapadx": ["_tf", "orEndHHMM", "vwapAnchor", "adxMin", "tpBars", "slBars", "maxTrades", "exitHHMM", "trendFilter"],
        "onbiasorb": ["_tf", "slPct", "rr", "avgLen", "minEntryHHMM", "exitHHMM", "adxMin", "atrSource", "trendFilter"],
        "sweepfvg": ["_tf", "liqPivotLen", "sweepReclaim", "breakType", "fvgPick", "entryLevel", "tpMode", "rrRatio", "startH", "endH", "tradeDirection"],
        "sweepengulf": ["_tf", "engulfMode", "prevCandle", "slMethod", "atrMult", "rrRatio", "tradeDirection", "trendFilter"],
        "varev": ["_tf", "profileSource", "profileSession", "valueAreaPct", "maxBarsOutside", "tpMode", "rrRatio", "startH", "endH", "tradeDirection"],
        "fpc": ["useS1", "useS2", "useS3", "useS4", "useCont", "contTP", "contSL", "useRev", "revTP", "revSL", "tpMode", "tradeDirection", "trendFilter"],
        "range": ["_tf", "lookbackBars", "boundaryMode", "entryMode", "maxWidthAtr", "slMode", "tpMode", "rrRatio", "maxTradesPerDay", "tradeDirection"],
        "noa": ["_tf", "lookbackDays", "volMult", "gapAdjust", "checkEvery", "lastEntryMin", "trailVwap", "hardStopPct", "maxTradesPerDay", "tradeDirection"],
        "noaes": ["_tf", "lookbackDays", "volMult", "gapAdjust", "checkEvery", "lastEntryMin", "trailVwap", "hardStopPct", "maxTradesPerDay", "tradeDirection"],
        "noamgc": ["_tf", "lookbackDays", "volMult", "gapAdjust", "checkEvery", "lastEntryMin", "trailVwap", "hardStopPct", "maxTradesPerDay", "tradeDirection"],
        "silverbullet": ["_tf", "sbStartH", "sbEndH", "maxTradesPerDay", "liqFromH", "fvgMinAtr", "requireMss", "entryLevel", "tpMode", "rrRatio", "minRR", "tradeDirection"],
        "tks": ["_tf", "loLevel", "hiLevel", "nConf", "rrRatio", "pivLen", "lookbackDays", "entryStartMin", "entryEndMin", "slMode", "maxSlPoints", "tradeDirection"],
        "nocpon": ["_tf", "nightEntryM", "nightExitH", "nightExitM", "useMonday", "monExitH", "useTrend", "smaLen", "skipRoll", "rollFromDay", "rollToDay", "stopPct"]}
SHOW["ibsentrymgc"] = SHOW["ibsentry"]
SHOW["ibsentryes"] = SHOW["ibsentry"]
SHOW["nyva"] = SHOW["nyvaes"] = ["rrRatio", "confirmCloses", "entryMode", "rangeEndH", "rangeEndM", "entryEndH", "useVwap", "maxSlPoints", "trendFilter"]
SHOW["scalp3mamgc"] = ["_tf", "ma1Len", "ma2Len", "ma3Len", "rsiLevel", "slMode", "slAtr", "rrRatio", "tradeStartH", "tradeEndH", "tradeDirection"]
SHOW["fibomgc"] = ["_tf", "swingTF", "legMinAtr", "levelMode", "slMode", "tpMode", "rrRatio", "tradeDirection", "tradeStartH", "tradeEndH"]

# Roboquant šablóny (týždeň 31. 10. 2026) na MNQ, ES, MGC — mená a stĺpce z mriežky glsearch
_RQN = {"orb15": "ORB 15/5", "flashorb": "FLASH ORB", "sigma": "SIGMA", "nqprec": "NQ PRECISION", "lliq": "LONDON IFVG",
        "tmr": "T-MEAN REV", "wpr": "WILLIAMS %R", "ivb": "IVB"}
for _b, _n in _RQN.items():
    for _s, _m in (("", "MNQ"), ("es", "ES"), ("mgc", "MGC")):
        NAMES[_b + _s] = f"{_n} ({_m})"
        SHOW[_b + _s] = [k for g in G.GROUPS.get(_b + _s, [])[:2] for k in g][:11]

# MYM — Micro Dow (12. 11. 2026): kópie stratégií ladené na MYM odznova
for _k, _b, _n in (("ibsentrymym", "ibsentry", "IBS EZ MYM"), ("noamym", "noa", "NOA 1.0 MYM"), ("wprmym", "wpr", "WILLIAMS %R (MYM)"),
                   ("sweepengulfmym", "sweepengulf", "SWEEPING ENGULF (MYM)"), ("tmrmym", "tmr", "T-MEAN REV (MYM)"),
                   ("lliqmym", "lliq", "LONDON IFVG (MYM)"), ("sigmamym", "sigma", "SIGMA (MYM)"), ("nocponmym", "nocpon", "NOC + PONDELOK (MYM)")):
    NAMES[_k] = _n
    if "SHORT" in globals():
        SHORT[_k] = _n.replace("(", "").replace(")", "")
    SHOW[_k] = SHOW.get(_b) or [k for g in G.GROUPS.get(_k, [])[:2] for k in g][:11]
    if "STEP1" in globals():
        STEP1[_k] = f"✓ (MYM, logika {_b})"

# BTC — BTCUSDT.P Binance futures (13. 11. 2026): kópie stratégií ladené na BTC odznova (poplatok maker 0,02 %)
for _k, _b, _n in (("noabtc", "noa", "NOA 1.0 (BTC)"), ("dailyopenbtc", "dailyopen", "DAILY OPEN (BTC)"),
                   ("onbiasorbbtc", "onbiasorb", "OVERNIGHT BIAS ORB (BTC)"), ("flashorbbtc", "flashorb", "FLASH ORB (BTC)"),
                   ("silverbulletbtc", "silverbullet", "SILVER BULLET (BTC)"), ("rangebtc", "range", "RANGE BREAKOUT (BTC)"),
                   ("tmrbtc", "tmr", "T-MEAN REV (BTC)"), ("sweepengulfbtc", "sweepengulf", "SWEEPING ENGULF (BTC)")):
    NAMES[_k] = _n
    if "SHORT" in globals():
        SHORT[_k] = _n.replace("(", "").replace(")", "")
    SHOW[_k] = SHOW.get(_b) or [k for g in G.GROUPS.get(_k, [])[:2] for k in g][:11]
    if "STEP1" in globals():
        STEP1[_k] = f"✓ (BTC, logika {_b})"

# EUR — 6E CME Euro FX (15. 11. 2026): kópie ladené na 6E 2016–2021/9, päť referenčných okien ako čisté overenie
for _k, _b, _n in (("asiasweepeur", "asiasweep", "ASIA SWEEP (6E)"), ("mtkzoneeur", "mtkzone", "MTK ZONE (6E)"),
                   ("lliqeur", "lliq", "LONDON IFVG (6E)"), ("silverbulleteur", "silverbullet", "SILVER BULLET (6E)"),
                   ("wpreur", "wpr", "WILLIAMS %R (6E)"), ("ibsentryeur", "ibsentry", "IBS EZ 6E"),
                   ("sweepengulfeur", "sweepengulf", "SWEEPING ENGULF (6E)")):
    NAMES[_k] = _n
    if "SHORT" in globals():
        SHORT[_k] = _n.replace("(", "").replace(")", "")
    SHOW[_k] = SHOW.get(_b) or [k for g in G.GROUPS.get(_k, [])[:2] for k in g][:11]

for _k, _n in (("m2", "M2 (ES)"), ("m2mnq", "M2 (MNQ)"), ("m2mgc", "M2 (MGC)"), ("m2eur", "M2 (6E)")):
    NAMES[_k] = _n
    SHOW[_k] = ["_tf", "rrRatio", "entryPct", "confirmMaxBars", "minImpulseAtr", "swingBars", "minRiskAtr", "maxRiskAtr",
                "useEmaTrend", "useWindow", "trendFilter"]

def merge_hyper(st):
    """Kandidáti z hyperoptu (hyper_state.json) k stratégiám — ukážu sa spolu s kandidátmi z mriežky."""
    for name in ("hyper_state.json", "hub_state.json", "rr_cands.json"):   # hyperopt lokálne + body z hubu + IBS EZ s vyšším RR
        hf = G.ROOT / name
        if not hf.exists():
            continue
        h = json.loads(hf.read_text())
        for c in h.get("candidates", []):
            if c.get("key") in st:
                st[c["key"]].setdefault("candidates", []).append(c)
        for k, n in h.get("trials", {}).items():
            if k in st:
                st[k]["combos"] = st[k].get("combos", 0) + n
    return st

st = merge_hyper(json.loads((G.ROOT / "gl_state.json").read_text()))
day = time.strftime("%Y-%m-%d")
fmt_years = lambda r: " · ".join(f"{k} {v['pf']:.2f}" for k, v in r.get("years", {}).items())
md = [f"# Testovanie podľa smernice — priebeh {time.strftime('%d. %m. %Y %H:%M')}\n",
      "Ladenie 2021-10 – 2025-09 s poplatkom 1,755e-05 (emulátor MultiCharts, MNQ), bez trailingu a konca seansy. "
      "Odložený rok 2025-09 – 2026-09 sa púšťa len raz na kandidáta. Hranice smernice: PF na ladení ≥ 1,3, ≥ 75 obch./rok, "
      "žiadny rok pod PF 0,9, plató ≥ 80 %, odložený rok PF ≥ 1,2 a ≥ 70 % PF z ladenia (nad 1000 kombinácií PF ≥ 1,3).\n",
      "## Súhrn\n", "| stratégia | krok 1 | skúsených kombinácií | najlepšie na ladení: obch/rok · PF | PF po rokoch | kandidátov | prešli odloženým rokom |",
      "|---|---|---|---|---|---|---|"]
detail = []
for key, S in st.items():
    if key in G.REMOVED:
        continue
    r = S.get("best_r") or {}
    c = S.get("candidates", [])
    strict = 1.3 if S["combos"] > 1000 else 1.2
    ok = [x for x in c if x.get("oos") and x["oos"]["profit_factor"] >= strict and x["oos"]["profit_factor"] >= 0.7 * x["is"]["profit_factor"]]
    md.append(f"| {NAMES.get(key) or G.title(key)} | {STEP1.get(key, "✓")} | {S['combos']} | {r.get('trades', 0) / G.years(key):.0f} · **{r.get('profit_factor', 0):.2f}** | "
              f"{fmt_years(r)} | {len(c)} | **{len(ok)}** |")
    rows = []
    fn = G.ROOT / f"gl_{key}.jsonl"
    for l in (open(fn) if fn.exists() else []):
        d = json.loads(l)
        if d["r"]:
            rows.append(d)
    rows.sort(key=lambda d: -G.score(d["r"]))
    detail += [f"\n## {NAMES.get(key) or G.title(key)} — 5 najlepších na ladení\n", "| obch/rok | PF | WR | zisk $ | max DD $ | PF po rokoch | nastavenie |", "|---|---|---|---|---|---|---|"]
    for d in rows[:5]:
        r2, p = d["r"], d["p"]
        detail.append(f"| {r2['trades'] / G.years(key):.0f} | {r2['profit_factor']:.2f} | {r2['winrate']:.1f} % | {r2['pnl_abs']:+.0f} | {r2['max_drawdown_abs']:.0f} | "
                      f"{fmt_years(r2)} | " + ", ".join(f"{k}={p[k]}" for k in (SHOW.get(key) or list(G.GROUPS.get(key, [{}])[0])) if k in p) + " |")
    if c:
        detail += [f"\n### {NAMES.get(key) or G.title(key)} — kandidáti (PF ≥ 1,3 na ladení, roky ≥ 0,9)\n",
                   "| čas | ladenie PF · obch/rok | plató (min) | odložený rok: obch · WR · PF · zisk | prešiel? |", "|---|---|---|---|---|"]
        for x in c:
            o = x.get("oos")
            okx = o and x["is"]["trades"] / G.years(key) >= G.MIN_TRADES_YEAR and o["profit_factor"] >= strict and o["profit_factor"] >= 0.7 * x["is"]["profit_factor"]
            detail.append(f"| {x['t']} | {x['is']['profit_factor']:.2f} · {x['is']['trades'] / G.years(key):.0f} | {x['plateau_min']} | "
                          + (f"{o['trades']} · {o['winrate']:.1f} % · {o['profit_factor']:.2f} · {o['pnl_abs']:+.0f}" if o else "nespustený (plató < 80 %)")
                          + f" | {'**ÁNO**' if okx else 'nie'} |")
out = "\n".join(md + detail) + "\n"
dst = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/SMERNICA-TESTOVANIA/PRIEBEH"
dst.mkdir(parents=True, exist_ok=True)
(dst / f"priebeh_{day}.md").write_text(out)
(G.ROOT / "GL_report.md").write_text(out)
print(out)
