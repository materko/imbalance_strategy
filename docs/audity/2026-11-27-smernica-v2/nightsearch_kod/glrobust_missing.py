"""Krok 9 v rannej úlohe: robustnosť (tester.robust — 2× poplatok, vstup o sviečku neskôr, Deflated Sharpe) pre každý
profil PREŠIEL_SMERNICAMI_*_1, ktorý ešte nemá výsledok alebo sa od posledného merania zmenil. Len informácia, na
prejdenie smernicou nemá vplyv (docs/SMERNICA_TESTOVANIA.md, krok 9). Počet skúšok = kombinácie z gl_state.json."""
import glob, json, sys
from pathlib import Path
ROOT = Path("/Users/martin/IBS"); NS = ROOT / ".nightsearch"; OUT = NS / "robust" / "vysledky.json"
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(NS))
import glsearch as G  # noqa: E402
from tester.robust import robustness  # noqa: E402

OUT.parent.mkdir(exist_ok=True)
done = json.loads(OUT.read_text()) if OUT.exists() else {}
mt = OUT.stat().st_mtime if OUT.exists() else 0
state = json.loads((NS / "gl_state.json").read_text())
todo = []
for f in sorted(glob.glob(str(ROOT / "tester/profiles/PRESIEL_SMERNICAMI_*_1.json"))):
    d = json.load(open(f))
    k = d["_strategy"]
    if k not in done or Path(f).stat().st_mtime > mt or done[k].get("profile") != f:
        todo.append((k, f, d.get("_timeframe", "3m")))
print("krok 9 chýba:", [k for k, _, _ in todo] or "nič", flush=True)
for k, f, tf in todo:
    pair = G.instr(k)[1]
    if tf.endswith("h"):                 # tester.robust berie TF v minútach („1h“ → „60m“)
        tf = f"{int(tf[:-1]) * 60}m"
    trials = max(1, int((state.get(k) or {}).get("combos") or 1))
    print(f"== {k} {pair} {tf} skúšok {trials}", flush=True)
    try:
        rep = robustness(f, pair, tf, G.fee(k), trials, log=lambda s: print(s, flush=True))
    except Exception as e:  # noqa: BLE001 — jedna stratégia nesmie zastaviť ostatné
        print("  zlyhalo:", type(e).__name__, str(e)[:200], flush=True)
        continue
    done[k] = {"profile": f, "pair": pair, "timeframe": tf, "trials": trials, "total": rep.total, "dsr": rep.dsr,
               "verdict": rep.verdict, "windows": rep.windows, "date": __import__("time").strftime("%Y-%m-%d")}
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1))
