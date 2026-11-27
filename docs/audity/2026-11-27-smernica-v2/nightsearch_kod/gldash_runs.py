"""Do TradeBot Labu (webapp) idú LEN nastavenia, ktoré prešli smernicou (používateľ 9. 10. 2026):
* profil tester/profiles/PRESIEL_SMERNICAMI_<stratégia>_<n>.json — zoznam sa každé ráno zosúladí s dashboardom
  (čo už medzi najlepšími neprešlo, odloží sa do dash/vyradene/, nemaže sa),
* beh do histórie — každé nastavenie len raz (dash/ran.json)."""
import json, subprocess, sys
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import glsearch as G
ROOT = "/Users/martin/IBS"
st = json.loads((G.ROOT / "gl_state.json").read_text())
data = json.loads((G.ROOT / "dash" / "dashboard_data.json").read_text())
ranf = G.ROOT / "dash" / "ran.json"; ran = json.loads(ranf.read_text()) if ranf.exists() else {}
(G.ROOT / "dash" / "profiles").mkdir(exist_ok=True)
# celé parametre nastavení (dashboard nesie len výber) — nájdi podľa výberu v stave a v histórii hľadania
def full(key, params):
    pool = [st[key]["best"]] + [c["p"] for c in st[key].get("candidates", [])]
    fn = G.ROOT / f"gl_{key}.jsonl"
    pool += [json.loads(l)["p"] for l in open(fn)] if fn.exists() else []
    for p in pool:
        if all(p.get(k) == v for k, v in params.items()):
            return p
import re, shutil
def tfname(n):
    """TF tak, ako ho pozná webapp: 60 -> 1h, 240 -> 4h, inak minúty."""
    return {60: "1h", 240: "4h", 1440: "1d"}.get(int(n), f"{int(n)}m")
PROF = G.ROOT.parent / "tester" / "profiles"
keep = set()
for s in data["strategies"]:
    if s.get("page_only"):        # TOP AS 75 (glwr) — len stránka výsledkov, nie webapp (používateľ 10. 11. 2026)
        continue
    key = s["key"]
    passed = [x for x in s["settings"] if x["status"].startswith("prešiel")]
    for i, x in enumerate(passed, 1):
        p = x.get("full_params") or full(key, x["params"])
        if p is None or x.get("short"):     # SPRÁVY majú vlastné PROFIL 1…n v tester/profiles (používateľ 30. 10.)
            continue
        a, ly = x["analysis"]["total"], x["analysis"]["years"][-1]
        prof = {k: v for k, v in p.items() if k != "_tf"}
        prof.update({"_strategy": key, "_instrument": G.instr(key)[0], "_timeframe": tfname(p['_tf']),
                     # krátky názov ako na stránke výsledkov (číslo = poradie od najlepšieho)
                     "_title": (f"{x['label']} · {G.instr(key)[1].split('/')[0]} {tfname(p['_tf'])} · max DD " + f"{a['maxdd']:,.0f}".replace(",", " ")
                                + " $ · posl. rok PF " + f"{ly.get('pf') or 0:.2f}".replace(".", ","))})
        fn = PROF / f"PRESIEL_SMERNICAMI_{re.sub('[^A-Za-z0-9]+', '_', s['name']).strip('_')}_{i}.json"
        fn.write_text(json.dumps(prof, ensure_ascii=False, indent=1)); keep.add(fn.name)
for fn in PROF.glob("PRESIEL_SMERNICAMI_*.json"):
    if fn.name not in keep:
        (G.ROOT / "dash" / "vyradene").mkdir(exist_ok=True)
        shutil.move(str(fn), str(G.ROOT / "dash" / "vyradene" / fn.name)); print("vyradený profil", fn.name)
print("profily PREŠIEL SMERNICAMI:", sorted(keep), flush=True)
for s in data["strategies"]:
    key = s["key"]
    for x in s["settings"]:
        if not x["status"].startswith("prešiel"):
            continue
        p = x.get("full_params") or full(key, x["params"])
        if p is None:
            continue
        sig = key + json.dumps(p, sort_keys=True)
        if sig in ran:
            continue
        tf = tfname(p['_tf'])
        prof = {k: v for k, v in p.items() if k != "_tf"}
        prof.update({"_strategy": key, "_instrument": G.instr(key)[0], "_timeframe": tf,
                     "_title": f"{s['name']} — smernica {x['id']}: ladenie PF {x['is']['pf']:.2f}, {x['status']}"})
        pf = G.ROOT / "dash" / "profiles" / f"{x['id']}.json"
        pf.write_text(json.dumps(prof, ensure_ascii=False, indent=1))
        tr = "20211001-20260904" if x["oos"] else "20211001-20250904"
        note = (f"Smernica {x['id']} ({x['status']}): ladenie 2021-10–2025-09 PF {x['is']['pf']:.2f}"
                + (f", odložený rok PF {x['oos']['pf']:.2f}" if x["oos"] else "") + f" — {x.get('params_label', x['label'])}")
        r = subprocess.run([f"{ROOT}/.venv/bin/python", "-m", "tester.webapp.cli", "run", "--strategy", key, "--profile", str(pf),
                            "--pair", G.instr(key)[1], "--engine", "multicharts", "--timeframe", tf, "--timerange", tr,
                            "--fee", str(G.fee(key)), "--wallet", "60000", "--note", note], capture_output=True, text=True, cwd=ROOT)
        line = [l for l in r.stdout.splitlines() if "obchodov" in l][-1:]
        print(x["id"], "|", line[0][:150] if line else (r.stdout[-200:] + r.stderr[-200:]), flush=True)
        if line:
            ran[sig] = line[0][:22]
            ranf.write_text(json.dumps(ran))
