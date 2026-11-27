"""Krok 8 smernice: profil PREŠIEL SMERNICAMI č. 1 na inom trhu (CFD Dukascopy) — ten istý podklad ako futures.

Trh berie z `glsearch.OTHER_MARKET` podľa inštrumentu profilu (MNQ → NAS100, MGC → XAU/USD, ES → US500); nový trh je
len riadok tam. Tickové polia sa prepočítajú pomerom tickov (MNQ 0,25 → NAS100 0,01 = ×25), polia vzdialeností
v tickoch na absolútne body, tickDollarValue = tick × hodnota bodu cieľa; prahy v ATR / % ostávajú.
Výsledok: nas100/<kľúč>.json + vysledky.json (s `market`)."""
import glob, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, "/Users/martin/IBS"); sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
import glsearch as G
from tradebot.core.types import INSTRUMENTS
ROOT = Path("/Users/martin/IBS"); OUT = ROOT / ".nightsearch" / "nas100"
from tradebot.strategies import STRATEGIES
YRS = [("21/22", "2021-10-01", "2022-10-01"), ("22/23", "2022-10-01", "2023-10-01"), ("23/24", "2023-10-01", "2024-09-04"),
       ("24/25", "2024-09-04", "2025-09-04"), ("25/26", "2025-09-04", "2026-09-04")]


def stats(trades):
    out = {}
    for n, a, b in YRS:
        p = [t["profit_abs"] for t in trades if a <= t["close_date"][:10] < b]
        gw, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
        out[n] = {"trades": len(p), "pf": round(gw / gl, 2) if gl else None}
    p = [t["profit_abs"] for t in trades]; gw, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
    return {"trades": len(p), "pf": round(gw / gl, 2) if gl else None, "wr": round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None, "years": out}


keys = sys.argv[1:] or None
res = {}
for f in sorted(glob.glob(str(ROOT / "tester/profiles/PRESIEL_SMERNICAMI_*_1.json"))):
    d = json.load(open(f)); k = d["_strategy"]
    if keys and k not in keys:
        continue
    src = d.get("_instrument") or G.instr(k)[0]
    if src not in G.OTHER_MARKET:
        print(k, f"krok 8: pre trh {src} nie je v glsearch.OTHER_MARKET iný trh — preskočené", flush=True)
        continue
    dst, pair, label, fee = G.OTHER_MARKET[src]
    si, di = INSTRUMENTS[src], INSTRUMENTS[dst]
    mult = round(si.tick_size / di.tick_size, 6)
    size_fields = set(getattr(STRATEGIES[k].config_cls, "SIZE_FIELDS", {}) or {})   # SizeSpec polia: zadať v bodoch
    for x, v in list(d.items()):
        if isinstance(v, dict) and v.get("unit") == "ticks":
            d[x] = {**v, "value": v["value"] * mult}
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and x.lower().endswith("ticks"):
            d[x] = {"value": v * si.tick_size, "unit": "abs"} if x in size_fields else type(v)(round(v * mult, 6))
    if d.get("tickDollarValue") is not None:
        d["tickDollarValue"] = round(di.tick_size * di.point_value, 10)
    d["_instrument"] = dst
    base = G.BASE_LABEL.get(src, src)
    d["_title"] = d.get("_title", k).replace("PREŠIEL SMERNICAMI —", f"{label} test (krok 8) —").replace(base, label)
    pf = OUT / f"{k}.json"; pf.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    r = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "run", "--strategy", k, "--profile", str(pf),
                        "--pair", pair, "--engine", "multicharts", "--timeframe", d["_timeframe"], "--timerange", "20211001-20260904",
                        "--fee", fee, "--wallet", "60000", "--note", f"Smernica krok 8: {label} (Dukascopy CFD) — {d['_title']}"],
                       cwd=ROOT, capture_output=True, text=True)
    line = [l for l in r.stdout.splitlines() if "obchodov" in l]
    if not line:
        print(k, "CHYBA", (r.stdout + r.stderr)[-300:], flush=True); continue
    rid = line[-1].split()[0]
    trades = json.load(open(ROOT / "tester/runs" / rid / "trades.json"))
    res[k] = {"run": rid, "market": label, **stats(trades)}
    print(k, label, rid, res[k]["trades"], "PF", res[k]["pf"], {n: y["pf"] for n, y in res[k]["years"].items()}, flush=True)
old = json.loads((OUT / "vysledky.json").read_text()) if (OUT / "vysledky.json").exists() else {}
old.update(res); (OUT / "vysledky.json").write_text(json.dumps(old, ensure_ascii=False, indent=1))
