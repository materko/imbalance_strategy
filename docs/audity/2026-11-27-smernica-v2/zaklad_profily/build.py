"""Základné profily ZAKLAD_<TRH> pre každú stratégiu na 6 trhoch V2: predvolené hodnoty kódu, trh, TF, obdobie L.
Prahy v bodoch (SIZE_FIELDS s jednotkou abs/ticks) sa prepočítajú pomerom mediánu denného ATR(14) (SMERNICA V2 §1)."""
import sys, json
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS")
from tradebot.strategies import STRATEGIES
from tester.webapp import profiles as P
from tradebot.core import config as C
ATR = json.load(open(Path(__file__).with_name("atr.json")))
MK = {"MNQ": ("mnq_databento", "20190505-20220930"), "ES": ("es_databento", "20150101-20250903"),
      "MYM": ("mym_databento", "20190602-20220930"), "MGC": ("mgc_databento", "20230101-20250903"),
      "6E": ("6e_databento", "20160103-20210930"), "BTC": ("btcusdt_binance", "20190908-20220930")}
HOME_MAP = {"nas100_dukascopy": "MNQ", "xau_dukascopy": "MGC", "eurusd_dukascopy": "6E", "btcusdt_binance_spot": "BTC"}
INV = {v[0]: k for k, v in MK.items()}
TICK = {"mnq_databento": .25, "es_databento": .25, "mym_databento": 1, "mgc_databento": .1, "6e_databento": .00005,
        "btcusdt_binance": .1, "btcusdt_binance_spot": .01, "nas100_dukascopy": .01, "xau_dukascopy": .01, "eurusd_dukascopy": .00001}
apply = "--apply" in sys.argv
report, homes = [], {}
for key, spec in STRATEGIES.items():
    dp = P.all_paths(key).get(spec.default_profile)
    dd = json.loads(dp.read_text()) if dp else {}
    prof_home = dd.get("_instrument")
    cfg0 = spec.config_cls(); sz0 = getattr(type(cfg0), "SIZE_FIELDS", {})
    absf = [f for f in sz0 if getattr(cfg0, f).unit in ("abs", "ticks") and getattr(cfg0, f).value]
    same = all(dd.get(f) in (getattr(cfg0, f).value, None) or (isinstance(dd.get(f), dict) and dd[f].get("value") == getattr(cfg0, f).value) for f in absf)
    # predvolené hodnoty kódu patria trhu default profilu len vtedy, keď sa s ním zhodujú v bodových prahoch; inak MNQ (Pine predlohy sú pre Nasdaq)
    present = [f for f in absf if f in dd]
    import re
    copy = bool(re.search(r"(es|mgc|btc|eur|mym|6e)(net)?(eod)?$", key)) and key not in ("ibs",)
    # domovský trh predvolených hodnôt: default profil ich výslovne obsahuje bez zmeny, alebo je to kópia trhu, ktorá ich nemení; inak MNQ
    home = prof_home if prof_home and ((present and same) or (not present and copy)) else "mnq_databento"
    tf = dd.get("_timeframe") or spec.default_timeframe
    cfg = spec.config_cls()
    base = cfg.to_dict()
    size = getattr(type(cfg), "SIZE_FIELDS", {})
    homes[key] = INV.get(home) or HOME_MAP.get(home)
    for m, (inst, tr) in MK.items():
        prm = {}; scaled = []   # profil = len rozdiel proti predvoleným hodnotám kódu
        import re as _re
        fields = [(f, u, "size") for f, u in size.items()]
        fields += [(f, ("ticks" if _re.search(r"Ticks?$", f) else "abs"), "plain") for f, v in base.items()
                   if f not in size and not isinstance(v, bool) and isinstance(v, (int, float)) and v
                   and _re.search(r"(Points|Pts|Point|Ticks|Tick)$", f) and f != "usdPerPoint"]
        bad = []
        for f, unit, kind in fields:
            if kind == "size":
                sp = getattr(cfg, f); cur_unit, cur = sp.unit, sp.value
                if cur_unit not in ("abs", "ticks") or not cur: continue
            else:
                cur_unit, cur = unit, base[f]
            if home not in ATR or inst == home: continue
            v = cur * (TICK.get(home, 1) if cur_unit == "ticks" else 1)       # v cene domovského trhu
            nv = v * ATR[inst] / ATR[home]                                     # v cene trhu M
            tick = TICK[inst]; nt = max(1, round(nv / tick)); note = ""
            if nt * tick > 1.5 * nv: note = f" (zaokrúhlené na 1 tick, o {round(100*(nt*tick/nv-1))} % viac)"
            lo, hi = type(cfg).CONSTRAINTS.get(f, (float("-inf"), float("inf")))
            if unit == "abs":
                val = round(nt * tick, 8)
                if lo <= val <= hi: prm[f] = val; scaled.append(f + note); continue
                if kind == "size": prm[f] = {"value": nt, "unit": "ticks"}; scaled.append(f + " (v tickoch, mimo rozsahu Pine v bodoch)" + note); continue
            else:
                if lo <= nt <= hi: prm[f] = nt; scaled.append(f + note); continue
                if kind == "size": prm[f] = {"value": round(nt * tick, 8), "unit": "abs"}; scaled.append(f + " (v bodoch, mimo rozsahu Pine v tickoch)" + note); continue
            bad.append(f)
        for f in [f for f in prm if prm[f] == base.get(f)]:   # po zaokrúhlení zhodné s defaultom → netreba
            prm.pop(f); scaled[:] = [x for x in scaled if not x.startswith(f)]
        prof = {"_title": f"ZÁKLAD · {m} {tf} · predvolené hodnoty kódu, bez ladenia · L {tr[:4]}–{tr[9:13]} (SMERNICA V2)",
                "_strategy": key, "_instrument": inst, "_timeframe": tf, "_timerange": tr,
                "_comment": ["Základ pre nové testovanie podľa SMERNICE V2 (27. 11. 2026): hodnoty z kódu stratégie, "
                             "žiadne ladenie. Obdobie = ladenie L trhu; trezor a rok A sa tu nepúšťajú."]
                            + ([f"Prahy v bodoch prepočítané pomerom mediánu denného ATR(14) {home} → {inst}, v pevnej cene trhu: {', '.join(scaled)}."] if scaled else [])
                            + (["Domovský trh predvolených hodnôt je predpoklad (MNQ), nie overený zápis — pred prvým behom ho potvrď v hlavičke (SMERNICA V2, krok 3a)."] if home == "mnq_databento" else [])
                            + ([f"NEPLATNÝ ZÁKLAD bez zmeny kódu: {', '.join(bad)} sa nedá prepočítať v rozsahu Pine — trh je pre hypotézu netestovateľný bez zmeny kódu."] if bad else []),
                **({"_engine_overrides": dd["_engine_overrides"]} if "_engine_overrides" in dd else {}), **prm}
        out = Path("/Users/martin/IBS/tradebot/strategies") / key / "configs" / f"ZAKLAD_{m}.json"; out.parent.mkdir(exist_ok=True)
        report.append((key, m, bool(out), scaled, bad))
        if apply and out:
            out.write_text(json.dumps(prof, ensure_ascii=False, indent=2) + "\n")
            C.load_profile(out, strategy=key)   # musí sa dať načítať
json.dump(homes, open(Path(__file__).with_name("homes.json"), "w"), indent=1)
print("stratégií", len(STRATEGIES), "profilov", sum(r[2] for r in report), "bez default profilu", [r[0] for r in report if not r[2]][:6])
print("prepočítané prahy:", sum(1 for r in report if r[3]), "príklad", [r for r in report if r[3]][:3])
print("domovský trh neznámy:", [k for k, v in homes.items() if not v])
print("neplatné základy:", [(r[0], r[1], r[4]) for r in report if r[4]])
