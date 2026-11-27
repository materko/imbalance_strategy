"""Prehľad glwr: nastavenie zo stránky vs. najlepší prejdený kandidát pri pevnom RR (python glwrreport.py)."""
import json, sys
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
import glsearch as G
import glwr as W

st = json.loads(W.STATE.read_text())
print(f"{'stratégia':12} {'stránka WR/PF/obch-rok':24} {'RR':>4} {'body':>5}  najlepší prejdený (WR / PF / obch-rok / OOS PF / OOS WR)")
for k, S in st.items():
    pg = (S.get("page") or {}).get("r") or {}
    pgs = f"{pg.get('winrate', 0):5.1f} / {pg.get('profit_factor', 0):4.2f} / {pg.get('trades', 0) / G.YEARS:4.0f}" if pg else "-"
    ok = [c for c in S["candidates"] if c.get("ok")]
    best = max(ok, key=lambda c: W.wr_score(c["is"], k)) if ok else None
    if best:
        r, o = best["is"], best["oos"]
        b = f"RR {best['rr']}: {r['winrate']:5.1f} / {r['profit_factor']:4.2f} / {r['trades'] / G.YEARS:4.0f} / {o['profit_factor']:4.2f} / {o['winrate']:5.1f}"
    else:
        b = "nič neprešlo"
    print(f"{k:12} {pgs:24} {W.STAGES[S['stage']]:>4} {S['trials']:>5}  {b}")
