"""Základné profily ZAKLAD_<TRH> pre každú stratégiu na 6 trhoch V2: predvolené hodnoty kódu, trh, TF, obdobie L.

SMERNICA V2, krok 3a: cenové polia z výslovného zoznamu PRICE_FIELDS (nie z regexu mien) sa prepočítajú pomerom
mediánu denného ATR(14) ATR_M / ATR_domov v pevnej cene trhu M. Domovský trh predvolených hodnôt je ručný zoznam
s dôkazom `domov.json` (= `.nightsearch/kritika/25_B_domovsky_trh.json`, audit B 27. 11. 2026).
Spustenie z koreňa repozitára: `.venv/bin/python -I docs/audity/2026-11-27-smernica-v2/zaklad_profily/build.py --apply`.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/martin/IBS")
from tester.webapp import profiles as P  # noqa: E402
from tradebot.core import config as C  # noqa: E402
from tradebot.core.types import SizeSpec  # noqa: E402
from tradebot.strategies import STRATEGIES  # noqa: E402

HERE = Path(__file__).parent
ATR = json.load(open(HERE / "atr.json"))
DOMOV = json.load(open(HERE / "domov.json"))
MK = {"MNQ": ("mnq_databento", "20190505-20220930"), "ES": ("es_databento", "20150101-20250903"),
      "MYM": ("mym_databento", "20190602-20220930"), "MGC": ("mgc_databento", "20230101-20250903"),
      "6E": ("6e_databento", "20160103-20210930"), "BTC": ("btcusdt_binance", "20190908-20220930")}
TICK = {"mnq_databento": .25, "es_databento": .25, "mym_databento": 1, "mgc_databento": .1, "6e_databento": .00005,
        "btcusdt_binance": .1}

# ---- výslovný zoznam cenových polí (C4): pole -> "abs" (cena) | "ticks" (ticky trhu) | "usd" ($ cez usdPerPoint) ----
_IBS = {"minImbSizePoints": "abs", "pbMinRangePoints": "abs", "engMinRangePoints": "abs", "srClusterPoints": "abs",
        "liqSweepMinWick": "abs", "ewMinWavePoints": "abs", "imbMaxDistTicks": "ticks", "state2ConfirmTicks": "ticks",
        "slBufferTicks": "ticks"}
_IBSENTRY = {**_IBS, "fvgMinSize": "abs"}
_TKS = {"slPoints": "abs", "maxSlPoints": "abs"}
_FAM = {
    ("ibs", "ibsnet", "ibszones"): _IBS,
    ("ibsentry", "ibsentrymgc", "ibsentryes", "ibsentryesnet", "ibsentrynet", "ibsentryneteod", "ibsfvg",
     "ibsentrymym", "ibsentrymymnet", "ibsentryeur"): _IBSENTRY,
    ("vwapdrift",): {"slPointsLong": "abs", "tpPointsLong": "abs", "slPointsShort": "abs", "tpPointsShort": "abs"},
    ("voltbreak", "voltbreaknet"): {"tpUsd": "usd", "slUsd": "usd"},
    ("scalp3ma", "scalp3mamgc"): {"slPoints": "abs"},
    ("svp",): {"rowTicks": "ticks", "slPoints": "abs"},
    ("fvgpolarity", "fvgpolaritymgc"): {"fvgMinSize": "abs", "fvgMaxSize": "abs", "slPoints": "abs"},
    ("fpc",): {"contTP": "abs", "contSL": "abs", "bigBar": "abs", "revTP": "abs", "revSL": "abs", "minDist": "abs",
               "trendPts": "abs", "maxDist": "abs", "testTol": "abs"},
    ("mag7",): {"slPts": "abs", "slOpenBuf": "abs", "minMove": "abs"},
    ("asiasweep", "asiasweepeur"): {"vpRowTicks": "ticks"},
    ("dailyopen", "dailyopenbtc"): {"breakPts": "abs", "slPts": "abs", "tpPts": "abs"},
    ("tks", "tksnet", "tksneteod", "tkses", "tksmgc", "tksmym", "tksbtc", "tkseur", "tksesnet", "tksmgcnet",
     "tksmymnet", "tksbtcnet", "tkseurnet"): _TKS,
    ("nyvaes", "nyvaesnet"): {"vaMinPoints": "abs", "vaMaxPoints": "abs", "slBufferTicks": "ticks", "maxSlPoints": "abs"},
    ("nb",): {"entryOffsetTicks": "ticks"},
    ("m2", "m2mnq", "m2eur", "m2mgc"): {"slTicks": "ticks"},
    ("orb15", "orb15es", "orb15mgc", "mtkorb", "mtkorbnet"): {"targetPoints": "abs"},
    ("mtkzone", "mtkzonenet", "mtkzoneeur"): {"minImbSize": "abs", "imbMaxDistTicks": "ticks", "st2ConfTicks": "ticks",
                                              "pbMinRange": "abs", "slBufTicks": "ticks", "maxRiskTicks": "ticks"},
    ("flashorb", "flashorbes", "flashorbmgc", "flashorbbtc"): {"trailActivatePoints": "abs", "trailBufferPoints": "abs"},
    ("sweepfvg",): {"tpPoints": "abs"},
    # bodové pole len s defaultom 0 (vypnuté) — domov bez_bodov, nič sa neprepočíta
    ("jss", "crt", "fibo", "fibomgc", "fibomgcnet"): {"slBufferPoints": "abs"},
}
PRICE_FIELDS = {k: f for ks, f in _FAM.items() for k in ks}
# C5: predvolene zapnutý trailing alebo koniec seansy / dňa (bool zapnutý, alebo číslo > 0)
EXIT_FLAGS = ("closeAtSessionEnd", "closeAtEnd", "useCloseAtEnd", "useEodClose", "flattenEod", "useEod", "enableTrailing",
              "trailVwap", "useTimeExit", "activateTrailing", "trailAtr", "useCloseAfter", "useExit", "useExitTime",
              "useTimeClose", "useCloseTime", "closeEOD")
# Koniec seansy / dňa napevno v kóde, bez prepínača: {kľúč: "čas a súbor:riadok"} (nález C 28/N1, prechod všetkých
# enginov 27. 11.: ostatné časové výstupy majú prepínač — useExitTime, useCloseTime, closeEOD, closeAtSessionEnd,
# closeAtWindowEnd, flattenEod, useEod… — a sú v EXIT_FLAGS, ak sú predvolene zapnuté; tmr / nocpon / spravy majú
# výstup v čase ako jadro pravidla, nie koniec seansy; maxHoldHours/maxHoldBars sú limity držania).
_NOA = ("16:00 New York, pozícia z predošlého dňa sa zavrie na prvom bare seansy — tradebot/strategies/noa/engine.py:126 "
        "(_CLOSE_MIN :38, deň :116), C# tradebot/strategies/noa/ports/csharp/NoaEngine.cs:228 (CloseMin :26)")
_EOD = ("15:59 New York (EodCloseEngine pre prop účty: posledný bar zatvárajúci sa najneskôr 15:59, zrušia sa aj "
        "čakajúce ordery) — tradebot/core/ports/csharp/TradeBot.Core/EodClose.cs:54 (CloseMin), obal :48")
FIXED_EXITS: dict[str, str] = {
    **{k: _NOA for k in ("noa", "noanet", "noaes", "noaesnet", "noamgc", "noamgcnet", "noamym", "noamymnet",
                         "noabtc", "noabtcnet")},
    "noaneteod": _NOA + "; navyše " + _EOD + " — tradebot/strategies/noa/ports/csharp/NoaEodEngine.cs",
    "ibsentryneteod": _EOD + " — tradebot/strategies/ibsentry/ports/csharp/IbsEntryEodEngine.cs",
    "tksneteod": _EOD + " — tradebot/strategies/tks/ports/csharp/TksEodEngine.cs",
    "vwapadxneteod": _EOD + " — tradebot/strategies/vwapadx/ports/csharp/VwapAdxEodEngine.cs",
    "vwaporbneteod": _EOD + " — tradebot/strategies/vwaporb/ports/csharp/VwapOrbEodEngine.cs",
}


def fmt(x):
    return f"{x:.6g}"


def scale(cfg, f, unit, home, inst, ratio):
    """Vráti (nová hodnota do profilu alebo None, poznámka, chyba)."""
    raw = getattr(cfg, f)
    size = isinstance(raw, SizeSpec)
    if size:
        if raw.unit not in ("abs", "ticks"):
            return None, None, None
        cu, cur = raw.unit, raw.value
    else:
        cu, cur = ("ticks" if unit == "ticks" else unit), raw
    if not cur:
        return None, None, None
    lo, hi = type(cfg).CONSTRAINTS.get(f, (float("-inf"), float("inf")))
    tick = TICK[inst]
    v = cur * (TICK[home] if cu == "ticks" else 1)   # v cene domovského trhu
    nv = v * ratio                                   # v cene trhu M
    nt = max(1, round(nv / tick))
    dev = nt * tick / nv - 1
    rnote = f" (zaokrúhlené na {nt} tick{'y' if nt > 1 else ''}, o {round(100 * dev)} % viac)" if abs(dev) > .5 else ""
    default_json = cur
    if cu == "abs":
        val = round(nt * tick, 8)
        if lo <= val <= hi:
            return (None if val == default_json else val), f"{f} {fmt(cur)} → {fmt(val)}{rnote}", None
        if size:
            return {"value": nt, "unit": "ticks"}, f"{f} {fmt(cur)} → {nt} tickov (mimo rozsahu Pine v bodoch){rnote}", None
        return None, f"{f} {fmt(cur)} → {fmt(val)}{rnote}", f"{f} ({fmt(val)} mimo rozsahu Pine {fmt(lo)}–{fmt(hi)})"
    if lo <= nt <= hi:
        return (None if nt == default_json else nt), f"{f} {fmt(cur)} t → {nt} t{rnote}", None
    if size:
        return {"value": round(nt * tick, 8), "unit": "abs"}, f"{f} {fmt(cur)} t → {fmt(nt * tick)} b (mimo rozsahu Pine v tickoch){rnote}", None
    return None, f"{f} {fmt(cur)} t → {nt} t{rnote}", f"{f} ({nt} t mimo rozsahu Pine {fmt(lo)}–{fmt(hi)})"


def scale_usd(cfg, ufields, inst, ratio):
    """Polia v $ cez usdPerPoint (body = $ / usdPerPoint) spolu: body × pomer ATR, zaokrúhlené na tick M.
    Najprv pri pevnom usdPerPoint; keď niektoré $ vyjde mimo rozsahu Pine, skúsi sa krajná hodnota usdPerPoint
    v jeho rozsahu (PORT_ONLY, používa sa len v tp/sl_points) — logika sa tým nemení."""
    if not ufields:
        return {}, [], []
    upp0 = cfg.usdPerPoint
    cons = type(cfg).CONSTRAINTS
    tick = TICK[inst]
    pts = {}
    for f in ufields:
        cur = getattr(cfg, f)
        if cur:
            nv = cur / upp0 * ratio
            pts[f] = (cur, nv, max(1, round(nv / tick)))
    if not pts:
        return {}, [], []
    ulo, uhi = cons.get("usdPerPoint", (upp0, upp0))
    for upp in (upp0, uhi, ulo):
        vals = {f: round(nt * tick * upp, 8) for f, (_, _, nt) in pts.items()}
        if all(cons.get(f, (float("-inf"), float("inf")))[0] <= v <= cons.get(f, (float("-inf"), float("inf")))[1]
               for f, v in vals.items()):
            break
    else:
        upp = upp0
    prm, notes, bad = {}, [], []
    for f, (cur, nv, nt) in pts.items():
        val = round(nt * tick * upp, 8)
        dev = nt * tick / nv - 1
        note = (f"{f} {fmt(cur)} $ = {fmt(cur / upp0)} b domov → {nt} t = {fmt(nt * tick)} b na M = {fmt(val)} $ "
                f"pri usdPerPoint {fmt(upp)}" + (f" (zaokrúhlené na tick, o {round(100 * dev)} % viac)" if abs(dev) > .5 else ""))
        notes.append(note)
        lo, hi = cons.get(f, (float("-inf"), float("inf")))
        if not lo <= val <= hi:
            bad.append(f"{f} ({fmt(val)} $ mimo rozsahu {fmt(lo)}–{fmt(hi)} ani pri usdPerPoint v rozsahu {fmt(ulo)}–{fmt(uhi)})")
        elif val != cur:
            prm[f] = val
    if upp != upp0 and not bad:
        prm["usdPerPoint"] = upp
        notes.append(f"usdPerPoint {fmt(upp0)} → {fmt(upp)} (pri {fmt(upp0)} by $ vyšli pod rozsah Pine; pole je PORT_ONLY "
                     "a slúži len na prevod $ → body, logiku nemení). Pozor: tieto „$“ nie sú skutočné doláre trhu M "
                     "(napr. 6E má 125 000 $ za bod) — berte ich len ako prepočet bodov.")
    return prm, notes, bad


def main():
    apply = "--apply" in sys.argv
    assert set(DOMOV) == set(STRATEGIES), "domov.json musí mať všetky stratégie registra"
    report = []
    for key, spec in STRATEGIES.items():
        dp = P.all_paths(key).get(spec.default_profile)
        dd = json.loads(dp.read_text()) if dp else {}
        tf = dd.get("_timeframe") or spec.default_timeframe
        cfg = spec.config_cls()
        dom = DOMOV[key]
        home, istota = dom["home"], dom["istota"]
        fields = PRICE_FIELDS.get(key, {}) if home != "bez_bodov" else {}
        exits = []
        for f in EXIT_FLAGS:
            v = getattr(cfg, f, None)
            if v is True or (f == "trailAtr" and isinstance(v, (int, float)) and v > 0):
                exits.append(f"{f}={v}")
        for m, (inst, tr) in MK.items():
            prm, notes, bad = {}, [], []
            pair = ATR["pairs"].get(f"{home}->{inst}")
            ratio = pair["pomer"] if pair else 1.0
            if pair:
                up, un, ub = scale_usd(cfg, [f for f, u in fields.items() if u == "usd"], inst, ratio)
                prm.update(up); notes.extend(un); bad.extend(ub)
                for f, unit in fields.items():
                    if unit == "usd":
                        continue
                    val, note, err = scale(cfg, f, unit, home, inst, ratio)
                    if note:
                        notes.append(note)
                    if err:
                        bad.append(err)
                    elif val is not None:
                        prm[f] = val
            com = ["Základ pre nové testovanie podľa SMERNICE V2 (27. 11. 2026): hodnoty z kódu stratégie, "
                   "žiadne ladenie. Obdobie = ladenie L trhu; trezor a rok A sa tu nepúšťajú."]
            if home == "bez_bodov":
                com.append("Domovský trh: bez_bodov — stratégia nemá aktívne cenové prahy, nič sa neprepočítava "
                           f"(25_B: {dom['dokaz']}).")
            else:
                com.append(f"Domovský trh predvolených hodnôt: {home}, istota {istota} (25_B: {dom['dokaz']}).")
                if istota == "nízka":
                    com.append("Domov je ODVODENÝ, nie doložený — hypotéza smie ísť len ako „zo štúdie“ (krok 10), "
                               "kým ho hlavička nepotvrdí dôkazom.")
                if pair and fields:
                    com.append(f"Pomer ATR = medián denného ATR(14) {inst} {fmt(pair['atr_m'])} / {home} "
                               f"{fmt(pair['atr_domov'])} v okne {pair['okno']} ({pair['zdroj']}) = "
                               f"{fmt(ratio)}; z rôznych období L by bol {fmt(pair['pomer_rozne_L'])} "
                               f"({round(100 * (pair['pomer_rozne_L'] / ratio - 1)):+d} %). Prepočet v pevnej cene trhu M (C6).")
                    com.append("Cenové polia (PRICE_FIELDS): " + "; ".join(notes) + "."
                               + (" Pole zhodné s defaultom sa do profilu nezapisuje (len poznámka)."
                                  if len(prm) < len(notes) else ""))
                elif inst == home:
                    com.append("Trh = domovský trh, prahy ostávajú ako v kóde.")
            if exits:
                com.append(f"Default má zapnutý trailing / koniec seansy ({', '.join(exits)}): hlavička musí výslovne "
                           "povoliť, inak vypnúť (§0).")
            if key in FIXED_EXITS:
                com.append(f"Koniec seansy je v kóde bez prepínača ({FIXED_EXITS[key]}): hlavička ho prijme ako logiku "
                           "hypotézy (§0).")
            if bad:
                com.append(f"NEPLATNÝ ZÁKLAD bez zmeny kódu: {', '.join(bad)} — trh je pre hypotézu netestovateľný "
                           "bez zmeny kódu (nie ❌).")
            prof = {"_title": f"ZÁKLAD · {m} {tf} · predvolené hodnoty kódu, bez ladenia · L {tr[:4]}–{tr[9:13]} (SMERNICA V2)",
                    "_strategy": key, "_instrument": inst, "_timeframe": tf, "_timerange": tr, "_comment": com,
                    **({"_engine_overrides": dd["_engine_overrides"]} if "_engine_overrides" in dd else {}), **prm}
            out = Path("/Users/martin/IBS/tradebot/strategies") / key / "configs" / f"ZAKLAD_{m}.json"
            report.append((key, m, prm, bad, home, istota))
            if apply:
                out.parent.mkdir(exist_ok=True)
                out.write_text(json.dumps(prof, ensure_ascii=False, indent=2) + "\n")
                C.load_profile(out, strategy=key)   # musí sa dať načítať
    print("stratégií", len(STRATEGIES), "profilov", len(report))
    print("s prepočítanými poľami:", sum(1 for r in report if r[2]))
    print("neplatné základy:", len([r for r in report if r[3]]))
    for r in report:
        if r[3]:
            print("  ", r[0], r[1], r[3])


if __name__ == "__main__":
    main()
