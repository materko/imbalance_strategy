"""Dáta pre dashboard (tester/dashboard/index.html) z hľadania podľa smernice + publikovateľná stránka s dátami v sebe.
python gldash.py → .nightsearch/dash/dashboard_data.json a .nightsearch/dash/tradebot_vysledky.html"""
import json, re, sys, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import glsearch as G
ACCOUNT = 60000.0
# Krátke mená pre názvy nastavení („IBS EZ 1 · PF 1,55 · …“) — rovnaké na stránke výsledkov aj vo webapp.
SHORT = {"mtkzone": "MTK ZONE", "nyva": "NY VA", "nyvaes": "NY VA ES", "vwaporb": "VWAP ORB", "ibsentry": "IBS EZ", "mag7": "SPX", "jss": "JSS", "crt": "CRT", "dailyopen": "DAILY OPEN",
         "svp": "SVP POC", "voltbreak": "VOLT", "vwapadx": "VWAP ADX", "onbiasorb": "ON BIAS", "sweepfvg": "SWEEP FVG",
         "sweepengulf": "SW ENGULF", "varev": "VA REV", "fpc": "FPC", "range": "RANGE", "noa": "NOA", "noaes": "NOA ES", "noamgc": "NOA MGC", "silverbullet": "SILVER BULLET", "tks": "TKS", "nocpon": "NOC+PON", "ibsentrymgc": "IBS EZ MGC", "scalp3mamgc": "Scalping 3MA (MGC)", "fibomgc": "Fibo 1.0 (MGC)", "ibsentryes": "IBS EZ ES", "mtkzone": "MTK ZONE"}


#: priečinok na stránke výsledkov podľa trhu (používateľ 20. 10. 2026); čo tu nie je, je NASDAQ
MARKET: dict[str, str] = {"ibsentrymgc": "GOLD", "scalp3mamgc": "GOLD", "fibomgc": "GOLD", "ibsentryes": "SP 500", "nyvaes": "SP 500"}


def short_label(key, i, st):
    t = st["analysis"]["total"]
    f = lambda v, d=2: "—" if v is None else f"{v:.{d}f}".replace(".", ",")   # 26. 10.: PF None zhodil celú stránku
    fp = st.get("full_params") or {}
    rr = next((fp[k] for k in ("rrRatio", "rr") if isinstance(fp.get(k), (int, float)) and not isinstance(fp.get(k), bool)), None)
    rr_txt = f" · RR {f(rr, 2).rstrip('0').rstrip(',')}" if rr is not None else ""   # aby sa dalo vyčítať, ktoré RR je ktoré
    if st.get("short"):                                   # 30. 10.: SPRÁVY ako PROFIL 1…4 (rovnaké mená ako vo webapp)
        return f"{st['short']} {i} · PF {f(t['pf'])} · WR {round(t['winrate'] or 0)} % · {st['is']['trades_per_year']} obch/rok"
    k0 = key[3:] if key.startswith("wr_") else key       # TOP AS 75 (glwr): meno predlohy
    return (f"{SHORT.get(k0, NAMES.get(k0, k0))} {i}{rr_txt} · PF {f(t['pf'])} · WR {round(t['winrate'] or 0)} % · {st['is']['trades_per_year']} obch/rok")


NAMES = {"nyva": "NY VA BREAKOUT", "nyvaes": "NY VA BREAKOUT ES", "vwaporb": "VWAP ORB", "ibsentry": "IBS Entry Zone", "mag7": "SPX sila", "jss": "JSS", "crt": "CRT + TBS", "dailyopen": "DAILY OPEN", "svp": "Volume Profile POC", "voltbreak": "Volt Break", "vwapadx": "VWAP ADX Pullback", "onbiasorb": "Overnight Bias ORB", "sweepfvg": "SWEEP FVG", "sweepengulf": "SWEEPING ENGULF", "varev": "VALUE AREA REVERSION", "fpc": "FPC 1.0 — férová cena", "range": "Range Breakout", "noa": "NOA 1.0", "noaes": "NOA 1.0 ES", "noamgc": "NOA 1.0 MGC", "silverbullet": "Silver Bullet 1.0 (ICT)", "tks": "TKS 1.0 (NQ Kompas)", "nocpon": "NOC + PONDELOK 1.0", "ibsentrymgc": "IBS EZ MGC", "scalp3mamgc": "Scalping 3MA (MGC)", "fibomgc": "Fibo 1.0 (MGC)", "ibsentryes": "IBS EZ ES"}
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
        SHORT[_b + _s] = f"{_n} {_m}"
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

for _k, _n in (("m2", "M2 (ES)"), ("m2mnq", "M2 (MNQ)"), ("m2mgc", "M2 (MGC)"), ("m2eur", "M2 (6E)")):
    NAMES[_k] = _n
    SHORT[_k] = _n
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

def trades_for(args):
    key, p, with_oos = args
    import allcore as A, io, contextlib, os
    from tradebot.core import load_profile
    from tradebot.core.types import INSTRUMENTS
    from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades
    from tester.webapp.results import timerange_ms
    K = G.instr(key)[0]; inst = INSTRUMENTS[K]
    q = {k: v for k, v in p.items() if k != "_tf"}; q.update({"_strategy": key, "_instrument": K})
    G.one_contract(key, q)
    fn = A.TMP / f"d{os.getpid()}.json"; fn.write_text(json.dumps(q))
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        cfg, _ = load_profile(fn, engine="multicharts")
        _a, _cut = span(key)[:2]
        f, t = timerange_ms(_a + "-" + ("20260904" if with_oos else _cut.replace("-", "")))
        res, _ = emulate(cfg, inst, A.m1(K), int(p["_tf"]), from_ms=f, to_ms=t, fee=G.fee(key))
        rows = rows_from_trades(res.trades, inst, G.fee(key), 1.0)
    out = []
    for r in rows:
        out.append({"open": str(r["open_date"])[:19] + "Z", "close": str(r["close_date"])[:19] + "Z",
                    "dir": "short" if r["is_short"] else "long", "entry": r["open_rate"], "exit": r["close_rate"],
                    "pnl": round(r["profit_abs"], 2), "reason": r["exit_reason"],
                    # pre prop simuláciu: R (zisk / riziko obchodu) a čisté body na 1 kontrakt
                    "r": (round(r["profit_abs"] / risk, 4) if (risk := abs(r["open_rate"] - (r.get("initial_stop_loss_abs") or r["open_rate"]))
                                                                 * r["point_value"] * r["amount"]) > 0 else None),
                    "pts": round(r["profit_abs"] / (r["point_value"] * r["amount"]), 3) if r["amount"] else None})
    return {"trades": out, "analysis": analyze(key, p, rows, with_oos)}


def span(key):
    """(začiatok behu stránky, hranica odloženého obdobia, roky) — MTK ORB ladí na všetkých dátach MGC, 2 roky odložené."""
    if key in G.PERIODS:
        a, b = G.PERIODS[key][0].split("-")[0], G.PERIODS[key][1].split("-")[0]
        cut = f"{b[:4]}-{b[4:6]}-{b[6:]}"
        oos = G.PERIODS[key][4] if len(G.PERIODS[key]) > 4 else [("24/25", "2024-09-04", "2025-09-04"), ("25/26", "2025-09-04", "2026-09-04")]
        ys = [(n, x, y) for n, x, y in G.windows(key)] + [(f"{n} (odložený)", x, y) for n, x, y in oos]   # EUR: päť okien
        return a, cut, ys
    return "20211001", "2025-09-04", YEARS


YEARS = [("21/22", "2021-10-01", "2022-10-01"), ("22/23", "2022-10-01", "2023-10-01"), ("23/24", "2023-10-01", "2024-09-04"),
         ("24/25", "2024-09-04", "2025-09-04"), ("25/26 (odložený)", "2025-09-04", "2026-09-04")]


def basic(pn):
    """Štatistiky zo zoznamu PnL obchodov v poradí zatvorenia."""
    w = [x for x in pn if x > 0]; l = [x for x in pn if x < 0]
    eq = peak = dd = 0.0; ls = ws = mls = mws = 0
    for x in pn:
        eq += x; peak = max(peak, eq); dd = max(dd, peak - eq)
        ls, ws = (ls + 1, 0) if x < 0 else ((0, ws + 1) if x > 0 else (0, 0))
        mls, mws = max(mls, ls), max(mws, ws)
    gl = -sum(l)
    return {"trades": len(pn), "winrate": round(100 * len(w) / len(pn), 1) if pn else None,
            "pf": round(sum(w) / gl, 2) if gl else None, "pnl": round(sum(pn), 0), "maxdd": round(dd, 0),
            "loss_streak": mls, "win_streak": mws, "max_win": round(max(w), 0) if w else None,
            "max_loss": round(min(l), 0) if l else None, "avg_win": round(sum(w) / len(w), 0) if w else None,
            "avg_loss": round(sum(l) / len(l), 0) if l else None}


def analyze(key, p, rows, with_oos):
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    from tester import nulltest as nt, montecarlo as mc
    ny = ZoneInfo("America/New_York")
    rows = sorted(rows, key=lambda r: str(r["close_date"]))
    for x in rows:
        o, sl, tp = x["open_rate"], x.get("initial_stop_loss_abs"), x.get("initial_take_profit_abs")
        if sl and o and sl != o:
            x["_sl_pct"] = abs(o - sl) / o * 100; x["_plan_src"] = "chart"
            if tp:
                x["_rr_planned"] = abs(tp - o) / abs(o - sl)
    years = []
    _start, _cut, _years = span(key)
    for name, a, b in _years:
        if not with_oos and a >= _cut:
            years.append({"year": name, "pending": True}); continue
        pn = [x["profit_abs"] for x in rows if a <= str(x["close_date"])[:10] < b]
        years.append({"year": name, **basic(pn)})
    allpn = [x["profit_abs"] for x in rows]
    tot = basic(allpn)
    days, hours = {}, {}
    for x in rows:
        d = str(x["close_date"])[:10]; days[d] = days.get(d, 0) + x["profit_abs"]
        h = datetime.fromisoformat(str(x["open_date"]).replace("Z", "+00:00")).astimezone(ny).strftime("%H")
        hours[h] = hours.get(h, 0) + 1
    perday = {}
    for x in rows:
        d = str(x["open_date"])[:10]; perday[d] = perday.get(d, 0) + 1
    tr = _start + "-" + ("20260904" if with_oos else _cut.replace("-", ""))
    null = {}
    for kind in ("session", "anytime"):
        try:
            r = nt.compare(rows, pair=G.instr(key)[1], timeframe=f"{int(p['_tf'])}m", timerange=tr, iterations=300, null=kind)
            null[kind] = {"sigma": r.sigma, "percentile": r.percentile, "observed": r.observed, "mean": r.mean, "lo": r.lo, "hi": r.hi}
        except Exception as e:  # noqa: BLE001
            null[kind] = {"error": str(e)[:200]}
    m = mc.analyze(rows, fee_pct=G.fee(key) * 100, iterations=5000, account=ACCOUNT)
    acc = m["account"]
    mcs = {"dd_median": round(acc["drawdown_abs"]["median"]), "dd_p95": round(acc["drawdown_abs"]["p95"]),
           "dd_max": round(acc["drawdown_abs"]["max"]), "streak_median": round(acc["losing_streak"]["median"]),
           "streak_p95": round(acc["losing_streak"]["p95"]), "wait_p95": round(acc["wait_for_high"]["p95"]),
           "p_positive": round(100 * m["net"]["p_positive"], 1), "be_lo": m["break_even"]["lo"], "be_hi": m["break_even"]["hi"]}
    return {"total": tot, "years": years, "null": null, "mc": mcs,
            "worst_day": round(min(days.values()), 0) if days else None, "best_day": round(max(days.values()), 0) if days else None,
            "max_trades_day": max(perday.values()) if perday else 0,
            "hours": sorted(hours.items()), "long_share": round(100 * sum(1 for x in rows if not x["is_short"]) / len(rows)) if rows else None}


def advice(key, p, status, a, oos_ok):
    """Odporúčania v bodoch — z čísel, nie z dojmu."""
    t, m, nl = a["total"], a["mc"], a["null"].get("session", {})
    out = []
    if oos_ok:
        out.append("Prešlo krokmi 1–6 smernice (naživo = história, ladenie, plató, odložený rok). Na trh ešte nie — "
                   "zostáva krok 7 analytika, 8 NAS100, 9 robustnosť a 10 forward test aspoň 4–8 týždňov.")
    elif "neprešiel" in status:
        out.append("NEZAPÍNAŤ: na roku, ktorý ladenie nevidelo, neprešlo — výsledok z ladenia je pravdepodobne preladený.")
    else:
        out.append("Zatiaľ len výsledok z ladenia — odložený rok ešte nebežal. Nezapínať, kým neprejde smernicou.")
    sg = nl.get("sigma")
    if sg is not None:
        out.append(("Test proti náhode: edge je odlíšiteľný od náhody" if sg >= 2 else
                    "Test proti náhode: len náznak, nie dôkaz" if sg >= 1 else
                    "Test proti náhode: neodlíšiteľné od náhody — vstup nepridáva nič") + f" ({sg:+.1f} σ).")
    out.append(f"Veľkosť účtu: pri 1 kontrakte MNQ počítaj s prepadom až {m['dd_p95']:,} $ (Monte Carlo, 95 % ciest), "
               f"skutočný bol {t['maxdd']:,.0f} $. Účet aspoň {2 * m['dd_p95']:,} $ na kontrakt, inak menšia pozícia.".replace(",", " "))
    out.append(f"Séria strát: v histórii najviac {t['loss_streak']} po sebe, Monte Carlo až {m['streak_p95']} (95 %). "
               f"Na nové maximum účtu sa môže čakať až {m['wait_p95']} obchodov — to je normálne, nie dôvod vypnúť.")
    if a.get("worst_day") is not None:
        out.append(f"Denný limit straty: najhorší deň v histórii {a['worst_day']:,.0f} $ — limit nastav o niečo nižšie, "
                   f"napr. {abs(a['worst_day']) * 1.25:,.0f} $; najviac obchodov za deň {a['max_trades_day']}.".replace(",", " "))
    if a["hours"]:
        tot_n, acc_n, top = sum(n for _, n in a["hours"]), 0, []
        for h, n in sorted(a["hours"], key=lambda x: -x[1]):
            top.append(int(h)); acc_n += n
            if acc_n >= 0.9 * tot_n:
                break
        out.append(f"Vstupy v NY čase hlavne {min(top):02d}:00 – {max(top) + 1:02d}:00 ({round(100 * acc_n / tot_n)} % obchodov); "
                   f"longy {a['long_share']} % obchodov. "
                   "Bez trailingu a bez zatvárania na konci seansy — tak, ako bolo testované.")
    out.append("Ako zapnúť: TradeBot Lab → Nový beh → stratégia " + (NAMES.get(key) or G.title(key)) + ", "
               + G.BASE_LABEL.get(G.instr(key)[0], "MNQ") + ", TF " + str(p["_tf"]) +
               "m, nastavenie z tejto stránky (je uložené aj v histórii behov s poznámkou „Smernica …“). "
               "V NinjaTraderi tieto stratégie zatiaľ nebežia — treba C# port ako pri IBSNet/ORBNet.")
    return out


def analytics_doc(key, check=True, path=None):
    """Výťah z tradebot/strategies/<key>/docs/ANALYTIKA.md (krok 7 smernice) pre stránku výsledkov."""
    import re as _re
    p = Path(path) if path else Path(f"/Users/martin/IBS/tradebot/strategies/{key}/docs/ANALYTIKA.md")
    if not p.exists():
        return None
    t = p.read_text()
    if check and "presiel" not in t.lower():          # analytika nie je z profilu, ktorý prešiel smernicou
        return None
    def sec(name):
        m = _re.search(r"^## " + name + r"\n(.*?)(?=^## |\Z)", t, _re.S | _re.M)
        return m.group(1) if m else ""
    bullets = lambda x: [l[2:].strip() for l in x.splitlines() if l.startswith("- ")]
    date = (_re.search(r"Zmerané (\d{4}-\d{2}-\d{2})", t) or [None, None])[1]
    rows = []
    for l in sec("Päť referenčných okien").splitlines():
        c = [x.strip() for x in l.strip("|").split("|")]
        if len(c) >= 7 and c[0][:2] == "20":
            rows.append({"okno": c[0], "obchody": c[1], "pnl": c[2], "be": c[3], "dd": c[4], "wr": c[5], "seria": c[6]})
    nul = _re.search(r"\| session[^|]*\|[^|]*\|[^|]*\| ([+-][\d.]+) \|", t)
    any_ = _re.search(r"\| anytime[^|]*\|[^|]*\|[^|]*\| ([+-][\d.]+) \|", t)
    mc = sec("Interval okolo výsledku a čo to robí s účtom")
    pos = _re.search(r"<!-- POSUDOK cisla=[^>]*-->\n(.*?)\n<!-- POSUDOK KONIEC -->", t, _re.S)
    char = (_re.search(r"^\*\*(.+?)\*\* \(istota (\w+)\)", sec("Charakter"), _re.M))
    return {"date": date, "good": bullets(sec("V čom je dobrá")), "bad": bullets(sec("Kde má chyby")), "windows": rows,
            "sigma": float(any_.group(1)) if any_ else None, "sigma_session": float(nul.group(1)) if nul else None,
            "mc": [l[2:] for l in mc.splitlines() if l.startswith("- ")][:5],
            "character": f"{char.group(1)} (istota {char.group(2)})" if char else None,
            "posudok": pos.group(1).strip() if pos else None,
            "link": f"https://github.com/materko/imbalance_strategy/blob/main/tradebot/strategies/{key}/docs/ANALYTIKA.md"}


NAS = json.loads((G.ROOT / "nas100" / "vysledky.json").read_text()) if (G.ROOT / "nas100" / "vysledky.json").exists() else {}
ROBUST = json.loads((G.ROOT / "robust" / "vysledky.json").read_text()) if (G.ROOT / "robust" / "vysledky.json").exists() else {}


EXTRA = G.ROOT / "spravy" / "stranka.json"


def extra_strategies(data):
    """Stratégie mimo hľadania podľa smernice, ktoré používateľ schválil na stránku (29. 10. 2026: SPRÁVY 3.0 so
    zlatom MGC — výnimka z pravidla 150 obchodov za rok). Profil z `spravy/stranka.json`, päť okien, krok 8 = XAU, krok 9."""
    if not EXTRA.exists():
        return
    for x in json.loads(EXTRA.read_text()):
        key = x["key"]
        G.INSTR[key] = (x["instrument"], x["pair"])
        p = {k: v for k, v in json.loads(Path(x["profile"]).read_text()).items() if not k.startswith("_")}
        p["_tf"] = x["tf"]
        res = trades_for((key, p, True))
        tr, an = res["trades"], res["analysis"]
        daily = {}
        for t in tr:
            daily[t["close"][:10]] = round(daily.get(t["close"][:10], 0.0) + t["pnl"], 2)
        eq, cum = [], 0.0
        for dday in sorted(daily):
            cum += daily[dday]; eq.append([dday, round(cum, 2)])
        tot, yrs = an["total"], {y["year"][:5]: y for y in an["years"]}
        ins = [y for y in an["years"] if "odložený" not in y["year"] and y.get("trades")]
        oos = next((y for y in an["years"] if "odložený" in y["year"]), {})
        status = x.get("status") or "prešiel — " + x.get("exception", "")
        show = {k: p[k] for k in x.get("show", []) if k in p}
        st = {"id": f"{key}-1", "label": x.get("label") or ", ".join(f"{k}={v}" for k, v in show.items()), "status": status,
              "params": show, "full_params": G.one_contract(key, dict(p)),
              "is": {"pf": round(sum(max(0, t["pnl"]) for t in tr if t["close"] < span(key)[1]) /
                                 max(1e-9, -sum(min(0, t["pnl"]) for t in tr if t["close"] < span(key)[1])), 3),
                     "trades": sum(y["trades"] for y in ins), "trades_per_year": round(sum(y["trades"] for y in ins) / G.years(key)),
                     "winrate": tot.get("winrate"), "pnl": sum(t["pnl"] for t in tr if t["close"] < span(key)[1]),
                     "maxdd": tot.get("maxdd") or tot.get("max_dd"), "years": {k: v.get("pf") for k, v in yrs.items() if "25/26" not in k}},
              "oos": {"pf": oos.get("pf"), "trades": oos.get("trades"), "winrate": oos.get("winrate"), "pnl": oos.get("pnl"),
                      "maxdd": oos.get("maxdd") or oos.get("max_dd")},
              "plateau_min": None, "analysis": an,
              "advice": [x.get("advice") or x.get("exception", "") + ". Obchoduje len po červených správach USA (~55 obchodov za rok), viac ich z princípu nebude."],
              "short": x.get("short"), "order": 1 if x.get("short") else None,
              "equity": eq, "daily": sorted([[k, v] for k, v in daily.items()]), "trades": tr}
        settings = [st]
        # ďalšie nastavenia stratégie (29.–30. 10.: profily z ladenia SPRÁV), každé ako samostatný riadok
        for i, m in enumerate(x.get("more", []), 2):
            q = {k: v for k, v in json.loads(Path(m["profile"]).read_text()).items() if not k.startswith("_")}
            q["_tf"] = x["tf"]
            r2 = trades_for((key, q, True))
            ch = {k: v for k, v in q.items() if k != "_tf" and p.get(k) != v}
            d2 = {}
            for t in r2["trades"]:
                d2[t["close"][:10]] = round(d2.get(t["close"][:10], 0.0) + t["pnl"], 2)
            e2, c2 = [], 0.0
            for dday in sorted(d2):
                c2 += d2[dday]; e2.append([dday, round(c2, 2)])
            y2 = [y for y in r2["analysis"]["years"] if "odložený" not in y["year"] and y.get("trades")]
            o2 = next((y for y in r2["analysis"]["years"] if "odložený" in y["year"]), {})
            t2 = r2["trades"]
            st2 = dict(st, id=f"{key}-{i}", status=m["status"], label=m["label"],
                       params=dict(list(ch.items())[:12]), full_params=G.one_contract(key, dict(q)), analysis=r2["analysis"], trades=t2, equity=e2,
                       daily=sorted([[k, v] for k, v in d2.items()]), advice=[m.get("advice") or m["status"]],
                       order=i if x.get("short") else None,
                       oos={"pf": o2.get("pf"), "trades": o2.get("trades"), "winrate": o2.get("winrate"), "pnl": o2.get("pnl"),
                            "maxdd": o2.get("maxdd") or o2.get("max_dd")})
            st2["is"] = {"pf": round(sum(max(0, t["pnl"]) for t in t2 if t["close"] < span(key)[1]) /
                                     max(1e-9, -sum(min(0, t["pnl"]) for t in t2 if t["close"] < span(key)[1])), 3),
                         "trades": sum(y["trades"] for y in y2), "trades_per_year": round(sum(y["trades"] for y in y2) / G.years(key)),
                         "winrate": r2["analysis"]["total"].get("winrate"),
                         "pnl": sum(t["pnl"] for t in t2 if t["close"] < span(key)[1]),
                         "maxdd": r2["analysis"]["total"].get("maxdd"),
                         "years": {y["year"][:5]: y.get("pf") for y in y2}}
            settings.append(st2)
        an_doc = analytics_doc_any(key)
        rob = ROBUST.get(key)
        nas = NAS.get(key)
        if nas:
            nas = dict(nas); nas["years_pos"] = sum(1 for y in nas["years"].values() if y["pf"] and y["pf"] > 1)
            nas["passed"] = bool(nas["pf"] and nas["pf"] >= 1.1 and nas["years_pos"] >= 4)
        steps = [["1", "naživo = história", True], ["2–3", "logika a východisko", True], ["4", "hľadanie nastavení", True],
                 ["5", "plató", False], ["6", "odložený rok", False], ["7", "analytika", bool(an_doc)],
                 ["8", "XAU/USD / iný trh", bool(nas and nas.get("passed"))], ["9", "robustnosť (info)", bool(rob)],
                 ["10", "forward test", False], ["11", "ostrá prevádzka", False]]
        data["strategies"].append({"key": key, "name": x["name"], "market": x["market"],
                                   "guideline_step": x.get("guideline_step") or "krok 10 — forward test · " + x["exception"],
                                   "exception": x.get("exception"), "no_audit": bool(x.get("no_audit")),
                                   "steps": steps, "analytics": an_doc, "nas100": nas, "robust": rob, "testing": False,
                                   "combos": 0, "step1": "prešiel", "settings": settings})


def analytics_doc_any(key):
    """analytics_doc bez kontroly „prešiel“ — pre stratégie mimo hľadania (EXTRA)."""
    return analytics_doc(key, check=False)


WR_STATE = G.ROOT / "wr_state.json"
WR_STEPS = json.loads((G.ROOT / "wr_steps" / "vysledky.json").read_text()) if (G.ROOT / "wr_steps" / "vysledky.json").exists() else {}
WR_FOLDER = "TOP AS 75"


def wr_strategies(data):
    """Priečinok TOP AS 75 (používateľ 10. 11. 2026): top stratégie webapp znova cez smernicu — min. 75 obch./rok,
    dobré PF, pevné RR 1 → 0,75 → 0,5, vyšší winrate (glwr.py na hube). Len na stránku výsledkov: kľúč wr_<stratégia>,
    page_only (gldash_runs z nich nerobí profily ani behy webapp), audit ich nehodnotí. Najviac 3 prejdené nastavenia."""
    if not WR_STATE.exists():
        return
    import glwr as W
    for key, S in json.loads(WR_STATE.read_text()).items():
        ok = sorted([c for c in S.get("candidates", []) if c.get("ok")], key=lambda c: -W.wr_score(c["is"], key))
        sets, seen = [], set()
        for c in ok:
            sig = (c["is"]["trades"], round(c["is"]["profit_factor"], 3))
            if sig in seen:
                continue
            seen.add(sig)
            p, r, o = c["p"], c["is"], c["oos"]
            res = trades_for((key, p, True))
            tr, an = res["trades"], res["analysis"]
            daily = {}
            for t in tr:
                daily[t["close"][:10]] = round(daily.get(t["close"][:10], 0.0) + t["pnl"], 2)
            eq, cum = [], 0.0
            for dday in sorted(daily):
                cum += daily[dday]; eq.append([dday, round(cum, 2)])
            show = SHOW.get(key) or list(G.GROUPS.get(key, [{}])[0])
            pg = ((S.get("page") or {}).get("r") or {})
            sets.append({"id": f"wr_{key}-{len(sets) + 1}", "label": f"RR {c['rr']} · " + ", ".join(f"{k}={p[k]}" for k in show if k in p),
                         "status": "prešiel odloženým rokom", "params": {k: p[k] for k in show if k in p},
                         "full_params": G.one_contract(key, dict(p)),
                         "is": {"pf": r["profit_factor"], "trades": r["trades"], "trades_per_year": round(r["trades"] / G.years(key)),
                                "winrate": r["winrate"], "pnl": r["pnl_abs"], "maxdd": r["max_drawdown_abs"],
                                "years": {k: v["pf"] for k, v in r.get("years", {}).items()}},
                         "oos": {"pf": o["profit_factor"], "trades": o["trades"], "winrate": o["winrate"], "pnl": o["pnl_abs"], "maxdd": o["max_drawdown_abs"]},
                         "plateau_min": c.get("plateau_min"), "analysis": an,
                         "advice": [f"Pevné RR {c['rr']}, hľadaný vyšší winrate pri min. 75 obch./rok a dobrom PF. Nastavenie č. 1 zo stránky: "
                                    f"WR {pg.get('winrate', 0):.1f} %, PF {pg.get('profit_factor', 0):.2f}, {pg.get('trades', 0) / G.years(key):.0f} obch./rok (ladenie)."],
                         "equity": eq, "daily": sorted([[k, v] for k, v in daily.items()]), "trades": tr})
            if len(sets) == 3:
                break
        if not sets:
            continue
        # kroky 7–9 pre nastavenie č. 1 (glwr_steps.py, 12. 11. 2026)
        WS = (WR_STEPS.get(f"wr_{key}") or {})
        an_doc = analytics_doc(key, check=False, path=WS["analytics"]) if WS.get("analytics") else None
        nas = dict(WS["nas"]) if WS.get("nas") else None
        if nas:
            nas["years_pos"] = sum(1 for y in nas["years"].values() if y["pf"] and y["pf"] > 1)
            nas["passed"] = bool(nas["pf"] and nas["pf"] >= 1.1 and nas["years_pos"] >= 4)
        rob = WS.get("robust")
        steps = [["1", "naživo = história", True], ["2–3", "logika a východisko", True], ["4", "hľadanie nastavení", True],
                 ["5", "plató", True], ["6", "odložený rok", True], ["7", "analytika", bool(an_doc)],
                 ["8", G.OTHER_MARKET.get(G.instr(key)[0], (0, 0, "iný trh"))[2] + " / iný trh", bool(nas and nas["passed"])],
                 ["9", "robustnosť (info)", bool(rob)], ["10", "forward test", False], ["11", "ostrá prevádzka", False]]
        data["strategies"].append({"key": f"wr_{key}", "name": f"{NAMES.get(key) or G.title(key)} · TOP AS 75", "market": WR_FOLDER,
                                   "guideline_step": f"krok 6 — prešiel odloženým rokom pri RR {sets[0]['label'].split(' ·')[0][3:]}",
                                   "no_audit": True, "page_only": True, "steps": steps, "analytics": an_doc, "nas100": nas,
                                   "robust": rob, "testing": False, "combos": S.get("trials", 0), "step1": "prešiel", "settings": sets})


def main():
    st = merge_hyper(json.loads((G.ROOT / "gl_state.json").read_text()))
    jobs, meta = [], []
    for key, S in st.items():
        if key in G.REMOVED:
            continue
        seen, items = set(), []
        def add(p, r, status, cand=None):
            sig = json.dumps(p, sort_keys=True)
            if sig in seen or not r:
                return
            seen.add(sig); items.append((p, r, status, cand))
        strict = 1.3 if S["combos"] > 1000 else 1.2
        passed, failed = [], []
        for c in reversed(S.get("candidates", [])):
            o = c.get("oos")
            ok = o and c["is"]["trades"] / G.years(key) >= G.MIN_TRADES_YEAR and o["profit_factor"] >= strict and o["profit_factor"] >= 0.7 * c["is"]["profit_factor"]
            (passed if ok else failed).append(c)
        res_seen = set()
        def add_u(p, r, status, cand=None):
            rs = (r["trades"], round(r["profit_factor"], 3)) if r else None
            if rs in res_seen:
                return
            n0 = len(items); add(p, r, status, cand)
            if len(items) > n0:
                res_seen.add(rs)
        # Na stránke len to, čo prešlo smernicou (používateľ 11. 10. 2026) — stratégia bez prejdeného nastavenia sa neukáže.
        for c in sorted(passed, key=lambda c: -c["oos"]["profit_factor"]):
            add_u(c["p"], c["is"], "prešiel odloženým rokom", c)
        # Stratégie práve v teste (gl_active.txt) bez prejdeného nastavenia: 3 najlepší kandidáti do sekcie „V teste“.
        if not passed and key in G.active():
            same = [c for c in failed if json.dumps(c["p"], sort_keys=True) == json.dumps(S["best"], sort_keys=True)]
            if not same:
                add_u(S["best"], S.get("best_r"), "najlepší na ladení — odložený rok ešte nebežal")
            for c in sorted(failed, key=lambda c: -(c.get("oos") or {}).get("profit_factor", 0)):
                add_u(c["p"], c["is"], "kandidát — neprešiel odloženým rokom" if c.get("oos") else "kandidát — plató pod 80 %", c)
            items = items[:3]
        items = items[:3]   # 8. 11. 2026 používateľ: najviac 3 nastavenia na stratégiu (najlepšie), nie 10
        for i, (p, r, status, cand) in enumerate(items):
            jobs.append((key, p, bool(cand and cand.get("oos"))))
            meta.append((key, i, p, r, status, cand))
    # Plánované stratégie (gl_planned.txt, 13. 11. 2026: BTC) — na stránke už pred štartom testov, s východiskom ladenia
    _pf = G.ROOT / "gl_planned.txt"
    planned = [k for k in ([l.split("#")[0].strip() for l in _pf.read_text().splitlines()] if _pf.exists() else [])
               if k and k not in st and k in G.GROUPS]
    for key in planned:
        p = {a: b for a, b in json.loads(open(G.BASE[key][0]).read()).items() if not a.startswith("_")}
        p.update(G.NO_EXIT.get(key, {})); p["_tf"] = G.BASE[key][1]
        r = G.evaluate(key, p, G.is_tr(key))
        jobs.append((key, p, False)); meta.append((key, 0, p, r, "východisko (predloha z MNQ) — testy ešte nebežali", None))
    with ProcessPoolExecutor(6) as ex:
        trades = list(ex.map(trades_for, jobs))
    data = {"updated": time.strftime("%Y-%m-%d %H:%M"),
            "note": "Len najlepšie nastavenia. Testovanie podľa smernice: ladenie 2021-10 – 2025-09 s poplatkom 1,755e-05 (MNQ, emulátor MultiCharts), bez trailingu a konca "
                    "seansy. Odložený rok 2025-09 – 2026-09 sa púšťa len raz na kandidáta. Čísla sú na 1 kontrakt MNQ, z backtestu — nie obchodné odporúčanie.",
            "strategies": []}
    by = {}
    for (key, i, p, r, status, cand), res in zip(meta, trades):
        tr, an = res["trades"], res["analysis"]
        daily = {}
        for t in tr:
            daily[t["close"][:10]] = round(daily.get(t["close"][:10], 0.0) + t["pnl"], 2)
        eq, cum = [], 0.0
        for dday in sorted(daily):
            cum += daily[dday]; eq.append([dday, round(cum, 2)])
        o = cand.get("oos") if cand else None
        s = {"id": f"{key}-{i + 1}", "label": ", ".join(f"{k}={p[k]}" for k in (SHOW.get(key) or list(G.GROUPS.get(key, [{}])[0])) if k in p), "status": status,
             "params": {k: p[k] for k in (SHOW.get(key) or list(G.GROUPS.get(key, [{}])[0])) if k in p}, "full_params": G.one_contract(key, dict(p)),
             "is": {"pf": r["profit_factor"], "trades": r["trades"], "trades_per_year": round(r["trades"] / G.years(key)),
                    "winrate": r["winrate"], "pnl": r["pnl_abs"], "maxdd": r["max_drawdown_abs"],
                    "years": {k: v["pf"] for k, v in r.get("years", {}).items()}},
             "oos": ({"pf": o["profit_factor"], "trades": o["trades"], "winrate": o["winrate"], "pnl": o["pnl_abs"], "maxdd": o["max_drawdown_abs"]} if o else None),
             "plateau_min": cand.get("plateau_min") if cand else None,
             "analysis": an, "advice": advice(key, p, status, an, status == "prešiel odloženým rokom"),
             "equity": eq, "daily": sorted([[k, v] for k, v in daily.items()]), "trades": tr}
        by.setdefault(key, []).append(s)
    for key, S in st.items():
        if key in G.REMOVED:
            continue
        c = S.get("candidates", [])
        passed = [s for s in by.get(key, []) if s["status"] == "prešiel odloženým rokom"]
        step = "krok 7 — analytika (checkup)" if passed else ("krok 5–6 — plató a odložený rok" if c else "krok 4 — hľadanie nastavení")
        an_doc = analytics_doc(key) if passed else None
        nas = NAS.get(key) if passed else None
        rob = ROBUST.get(key) if passed else None   # krok 9 (len informácia, glrobust_missing.py)
        if nas:
            nas = dict(nas); nas["years_pos"] = sum(1 for y in nas["years"].values() if y["pf"] and y["pf"] > 1)
            nas["passed"] = bool(nas["pf"] and nas["pf"] >= 1.1 and nas["years_pos"] >= 4)
        steps = [["1", "naživo = história", True], ["2–3", "logika a východisko", True], ["4", "hľadanie nastavení", True],
                 ["5", "plató", bool(passed)], ["6", "odložený rok", bool(passed)], ["7", "analytika", bool(an_doc)],
                 ["8", G.OTHER_MARKET.get(G.instr(key)[0], (0, 0, "iný trh"))[2] + " / iný trh", bool(nas and nas["passed"])], ["9", "robustnosť (info)", bool(rob)], ["10", "forward test", False], ["11", "ostrá prevádzka", False]]
        if an_doc:
            step = "krok 8 — NAS100 / iný trh"
        if nas:
            step = "krok 10 — forward test" if nas["passed"] else f"krok 8 — {G.OTHER_MARKET.get(G.instr(key)[0], (0, 0, 'iný trh'))[2]} NEPREŠIEL (ide iným smerom)"
        data["strategies"].append({"key": key, "name": NAMES.get(key) or G.title(key), "market": MARKET.get(key) or G.FOLDER.get(G.instr(key)[0], "NASDAQ"), "guideline_step": step, "steps": steps, "analytics": an_doc, "nas100": nas, "robust": rob, "testing": not passed,
                                   "combos": S["combos"], "step1": "prešiel",
                                   "settings": by.get(key, [])})
    for key in planned:
        data["strategies"].append({"key": key, "name": NAMES.get(key) or G.title(key), "market": MARKET.get(key) or G.FOLDER.get(G.instr(key)[0], "NASDAQ"),
                                   "guideline_step": "krok 4 — čaká na štart testov (ne 15. 11. po MYM)",
                                   "steps": [["1", "naživo = história", True], ["2–3", "logika a východisko", True], ["4", "hľadanie nastavení", False],
                                             ["5", "plató", False], ["6", "odložený rok", False], ["7", "analytika", False], ["8", "iný trh", False],
                                             ["9", "robustnosť (info)", False], ["10", "forward test", False], ["11", "ostrá prevádzka", False]],
                                   "analytics": None, "nas100": None, "robust": None, "testing": True, "combos": 0, "step1": "prešiel",
                                   "settings": by.get(key, [])})
    extra_strategies(data)
    wr_strategies(data)
    # Od najlepších po najhoršie: najprv to, čo prešlo smernicou ďalej, potom podľa PF.
    def rank(x):
        if x.get("order"):                                  # pevné poradie PROFIL 1…n (používateľ 30. 10.)
            return (-1, x["order"])
        st_ = x["status"]
        lvl = 0 if st_.startswith("prešiel") else 1 if "ešte nebežal" in st_ else 2 if "plató" in st_ else 3
        pf_ = (x["oos"] or {}).get("pf") if lvl == 0 else x["analysis"]["total"]["pf"]
        return (lvl, -(pf_ or 0))
    for S_ in data["strategies"]:
        S_["settings"].sort(key=rank)
        for i, st in enumerate(S_["settings"], 1):          # číslo = poradie od najlepšieho, rovnaké ako profil vo webapp
            st["params_label"] = st["label"]
            st["id"] = f"{S_['key']}-{i}"
            st["label"] = short_label(S_["key"], i, st)
    data["strategies"].sort(key=lambda S_: rank(S_["settings"][0]) if S_["settings"] else (9, 0))
    data["strategies"] = [S_ for S_ in data["strategies"] if S_["settings"]]
    # krok 12 — kontrola CI90 · SHA-256 dát · druhý model (AS stratégie, len stránka; používateľ 10. 11. 2026)
    try:
        import glcheck12
        glcheck12.apply(data)
    except Exception as e:  # noqa: BLE001 — kontrola nesmie zhodiť ranné generovanie
        print("krok 12 zlyhal:", type(e).__name__, str(e)[:200])
    out = G.ROOT / "dash"
    # karta Live (tester/dashboard/live.py z MacBooku, 16. 10. 2026): zrkadlo live telemetrie webapp; kým modul nie je, nič
    try:
        from tester.dashboard.live import build_live
        data["live"] = build_live()
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001 — chyba live dát nesmie zhodiť ranné generovanie
        print("live sekcia zlyhala:", type(e).__name__, str(e)[:200])
    # nasadenia na hube (karta Účty: čo sa bude brať) — len bezpečné polia, bez tokenov a celého configu
    try:
        import urllib.request
        deps = json.loads(urllib.request.urlopen("http://localhost:8765/api/live/deployments", timeout=20).read())
        data["deployments"] = [{
            "strategy": x.get("strategy"), "symbol": x.get("symbol"), "tf": x.get("tf"), "platform": x.get("platform"),
            "account": x.get("account"), "agent": x.get("agent"), "profile": x.get("profile"), "active": x.get("active"),
            "mode": x.get("mode"), "created": x.get("created"), "updated": x.get("updated"), "by": x.get("by"),
            "applied": (x.get("applied") or {}).get("status"), "alive": (x.get("live") or {}).get("alive"),
            "riskDollar": (x.get("config") or {}).get("riskDollar"), "fixedQty": (x.get("config") or {}).get("fixedQty"),
            "qty": (x.get("config") or {}).get("qty")} for x in deps]
    except Exception as e:  # noqa: BLE001 — webapp nebeží → bez nasadení
        print("nasadenia z webapp zlyhali:", type(e).__name__, str(e)[:200])
    # karta Audit (bod 5 týždňa 31. 10.–8. 11. 2026): triedy A / B / C a najlepší trh, každé ráno nanovo
    try:
        import glaudit
        data["audit"] = glaudit.compute(data, time.strftime("%Y-%m-%d"))
        glaudit.write_md(data["audit"])
        glaudit.write_webapp(data["audit"])
    except Exception as e:  # noqa: BLE001 — chyba auditu nesmie zhodiť ranné generovanie
        print("audit zlyhal:", type(e).__name__, str(e)[:200])
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
