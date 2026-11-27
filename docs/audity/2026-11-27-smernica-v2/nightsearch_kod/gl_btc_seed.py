"""Východiská smernice pre BTC kópie do gl_state.json (13. 11. 2026) — hub čaká na best_r, glsearch ide po skupinách
a východisko by inak dopočítal až keď na kľúč príde. Volá gl_mym_koniec.sh pri prepnutí na BTC (procesy stoja)."""
import json
import glsearch as G
st = json.loads((G.ROOT / "gl_state.json").read_text())
for k in [l.strip() for l in (G.ROOT / "gl_active.txt").read_text().splitlines() if l.strip()]:
    if k in st and st[k].get("best_r"):
        continue
    p = json.loads(open(G.BASE[k][0]).read()); p = {a: b for a, b in p.items() if not a.startswith("_")}
    p.update(G.NO_EXIT.get(k, {})); p["_tf"] = G.BASE[k][1]
    r = G.evaluate(k, p, G.is_tr(k))
    st[k] = {"best": p, "best_r": r, "combos": 0, "seen": [], "candidates": [], "round": 0, "cur": p, "cur_r": r}
    print(k, r["trades"], r["profit_factor"], flush=True)
(G.ROOT / "gl_state.json").write_text(json.dumps(st, ensure_ascii=False))
