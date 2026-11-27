"""Kroky 7–9 smernice pre priečinok TOP AS 75 (wr_<stratégia>, glwr.py) — automaticky, ako pri bežných stratégiách
(používateľ 12. 11. 2026: „doplň všetky body 7–9 všade, kde nie sú“).

Nastavenie č. 1 každej wr stratégie (to isté poradie ako gldash.wr_strategies) → profil wr_steps/wr_<kľúč>.json, potom:
  7. analytika  — cli checkup do wr_steps/wr_<kľúč>_ANALYTIKA.md (dokument stratégie v repe sa neprepíše),
  8. iný trh    — ten istý prepočet ako glnas100.py (CFD Dukascopy podľa glsearch.OTHER_MARKET),
  9. robustnosť — tester.robust (2× poplatok, vstup o sviečku neskôr, Deflated Sharpe).
Výsledky: wr_steps/vysledky.json {wr_<kľúč>: {"params", "analytics", "nas", "robust"}}. Počíta len to, čo chýba alebo
sa zmenilo (iné nastavenie č. 1). Volá ranná úloha (glmorning.sh)."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/Users/martin/IBS"); NS = ROOT / ".nightsearch"; OUT = NS / "wr_steps"
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(NS))
import glsearch as G  # noqa: E402
import glwr as W  # noqa: E402
from tradebot.core.types import INSTRUMENTS  # noqa: E402
from tradebot.strategies import STRATEGIES  # noqa: E402

OUT.mkdir(exist_ok=True)
RES = OUT / "vysledky.json"
PY = str(ROOT / ".venv/bin/python")
YRS = [("21/22", "2021-10-01", "2022-10-01"), ("22/23", "2022-10-01", "2023-10-01"), ("23/24", "2023-10-01", "2024-09-04"),
       ("24/25", "2024-09-04", "2025-09-04"), ("25/26", "2025-09-04", "2026-09-04")]


def first_set(key, S):
    ok = sorted([c for c in S.get("candidates", []) if c.get("ok")], key=lambda c: -W.wr_score(c["is"], key))
    return ok[0] if ok else None


def nas_stats(trades):
    out = {}
    for n, a, b in YRS:
        p = [t["profit_abs"] for t in trades if a <= t["close_date"][:10] < b]
        gw, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
        out[n] = {"trades": len(p), "pf": round(gw / gl, 2) if gl else None}
    p = [t["profit_abs"] for t in trades]; gw, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
    return {"trades": len(p), "pf": round(gw / gl, 2) if gl else None,
            "wr": round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None, "years": out}


def step7(key, wk, prof, tf, pair):
    doc = OUT / f"{wk}_ANALYTIKA.md"
    r = subprocess.run([PY, "-m", "tester.webapp.cli", "checkup", "--strategy", key, "--profile", str(prof), "--pair", pair,
                        "--engine", "multicharts", "--timeframe", tf, "--fee", str(G.FEE), "--wallet", "60000",
                        "--out", str(doc), "--note", f"Smernica krok 7: analytika {wk} (TOP AS 75, nastavenie 1)"],
                       cwd=ROOT, capture_output=True, text=True)
    return str(doc) if doc.exists() else None, (r.stdout + r.stderr)[-200:]


def step8(key, wk, d):
    src = d["_instrument"]
    if src not in G.OTHER_MARKET:
        return None
    dst, pair, label, fee = G.OTHER_MARKET[src]
    d = dict(d)
    si, di = INSTRUMENTS[src], INSTRUMENTS[dst]
    mult = round(si.tick_size / di.tick_size, 6)
    size_fields = set(getattr(STRATEGIES[key].config_cls, "SIZE_FIELDS", {}) or {})
    for x, v in list(d.items()):
        if isinstance(v, dict) and v.get("unit") == "ticks":
            d[x] = {**v, "value": v["value"] * mult}
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and x.lower().endswith("ticks"):
            d[x] = {"value": v * si.tick_size, "unit": "abs"} if x in size_fields else type(v)(round(v * mult, 6))
    if d.get("tickDollarValue") is not None:
        d["tickDollarValue"] = round(di.tick_size * di.point_value, 10)
    d["_instrument"] = dst
    d["_title"] = f"{label} test (krok 8) — {wk}"
    pf = OUT / f"{wk}_{label.replace('/', '')}.json"; pf.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    r = subprocess.run([PY, "-m", "tester.webapp.cli", "run", "--strategy", key, "--profile", str(pf), "--pair", pair,
                        "--engine", "multicharts", "--timeframe", d["_timeframe"], "--timerange", "20211001-20260904",
                        "--fee", fee, "--wallet", "60000", "--note", f"Smernica krok 8: {label} (Dukascopy CFD) — {wk}"],
                       cwd=ROOT, capture_output=True, text=True)
    line = [ln for ln in r.stdout.splitlines() if "obchodov" in ln]
    if not line:
        print(wk, "krok 8 CHYBA", (r.stdout + r.stderr)[-300:], flush=True)
        return None
    rid = line[-1].split()[0]
    trades = json.load(open(ROOT / "tester/runs" / rid / "trades.json"))
    return {"run": rid, "market": label, **nas_stats(trades)}


def step9(key, prof, tf, pair, trials):
    from tester.robust import robustness
    if tf.endswith("h"):
        tf = f"{int(tf[:-1]) * 60}m"
    rep = robustness(str(prof), pair, tf, G.FEE, trials, log=lambda s: print(s, flush=True))
    return {"pair": pair, "timeframe": tf, "trials": trials, "total": rep.total, "dsr": rep.dsr, "verdict": rep.verdict,
            "windows": rep.windows, "date": time.strftime("%Y-%m-%d")}


def main():
    done = json.loads(RES.read_text()) if RES.exists() else {}
    state = json.loads((NS / "wr_state.json").read_text())
    for key, S in state.items():
        c = first_set(key, S)
        if not c:
            continue
        wk = f"wr_{key}"
        p = dict(c["p"])
        tf = f"{int(p.pop('_tf'))}m" if "_tf" in p else "3m"
        d = G.one_contract(key, {k: v for k, v in p.items()})
        d.update({"_strategy": key, "_instrument": G.instr(key)[0], "_timeframe": tf,
                  "_title": f"TOP AS 75 — {G.title(key)} nastavenie 1 (RR {c['rr']})"})
        prof = OUT / f"{wk}.json"
        sig = json.dumps({k: v for k, v in d.items() if not k.startswith("_")}, sort_keys=True)
        R = done.get(wk) or {}
        if R.get("params") != sig:
            R = {"params": sig}
        prof.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        pair = G.instr(key)[1]
        if not R.get("analytics"):
            print(f"== {wk} krok 7", flush=True)
            R["analytics"], info = step7(key, wk, prof, tf, pair)
            if not R["analytics"]:
                print("   krok 7 zlyhal:", info, flush=True)
        if "nas" not in R:
            print(f"== {wk} krok 8", flush=True)
            R["nas"] = step8(key, wk, d)
        if not R.get("robust"):
            print(f"== {wk} krok 9", flush=True)
            try:
                R["robust"] = step9(key, prof, tf, pair, max(1, int(S.get("trials") or 1)))
            except Exception as e:  # noqa: BLE001 — jedna stratégia nesmie zastaviť ostatné
                print("   krok 9 zlyhal:", type(e).__name__, str(e)[:200], flush=True)
        done[wk] = R
        RES.write_text(json.dumps(done, ensure_ascii=False, indent=1))
    print("hotovo", time.strftime("%H:%M"), flush=True)


if __name__ == "__main__":
    main()
