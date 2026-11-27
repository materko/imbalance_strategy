"""Ranný krok: doterajšie najlepšie nastavenia IBS Entry Zone s vyšším RR (glrr.py, hub) → kandidáti pre tabuľku,
stránku TradeBot výsledky a webapp — ako pri hľadaní podľa smernice.

Pre každé RR sa vezmú 2 najlepšie úlohy (skóre glsearch.score), ktoré prejdú ladením; ich najlepší bod → plató
lokálne (± 10 % zmenených číselných parametrov okrem RR, ≥ 80 % PF) → odložený rok raz lokálne. Výsledok v
rr_cands.json (rovnaký tvar ako hyper_state.json: candidates + trials), ktorý gldash / glreport načítajú.
Bod, ktorý už bol preverený, sa znova nepočíta. glrr.py je počas ranného nahrávania pozastavený (glpause mstop)."""
from __future__ import annotations

import contextlib, io, json, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import glsearch as G
import glhyper as H

KEY = "ibsentry"
SRC = G.ROOT / "rr_state.json"
OUT = G.ROOT / "rr_cands.json"
PER_RR = 2


def main():
    if not SRC.exists():
        return
    st = json.loads(SRC.read_text())
    out = json.loads(OUT.read_text()) if OUT.exists() else {"candidates": [], "trials": {}}
    done = {json.dumps(c["p"], sort_keys=True) for c in out["candidates"]}
    pick = []
    for rr in sorted({t["rr"] for t in st.values()}):
        ts = [t for t in st.values() if t["rr"] == rr and t.get("best_r") and G.passes_is(t["best_r"])]
        pick += sorted(ts, key=lambda t: -G.score(t["best_r"]))[:PER_RR]
    with ProcessPoolExecutor(4) as pool:
        for t in pick:
            p, r = t["best"], t["best_r"]
            if json.dumps(p, sort_keys=True) in done:
                continue
            changed = {n for n in p if p.get(n) != t["start"].get(n) and n != "rrRatio"} or \
                      {n for n in ("slLookback", "minSlDistance", "slBufferTicks") if n in p}
            pmin, ratios = H.plateau(pool, KEY, p, r, changed)
            cand = {"p": p, "is": r, "plateau_min": pmin, "plateau": ratios, "t": time.strftime("%Y-%m-%d %H:%M"),
                    "source": "hub RR", "key": KEY, "from_profile": t["n"], "rr": t["rr"]}
            if pmin is None or pmin >= 0.8:
                with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                    cand["oos"] = G.evaluate(KEY, p, G.OOS)
            out["candidates"].append(cand)
            print(time.strftime("%d. %H:%M"), f"RR kandidát z profilu {t['n']} RR {t['rr']}: ladenie PF {r['profit_factor']:.2f}",
                  f"plató {pmin} OOS PF {cand.get('oos', {}).get('profit_factor')}", flush=True)
            OUT.write_text(json.dumps(out, ensure_ascii=False))
    out["trials"] = {KEY: sum(t["done"] for t in st.values())}
    OUT.write_text(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
