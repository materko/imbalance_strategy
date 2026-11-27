"""Webapp = C# jadro s nastaveniami zo stránky výsledkov (používateľ 8. 11. 2026).

Pre každú C# stratégiu zo stránky výsledkov prepíše jej profily č. 1–3 na presne tie parametre, ktoré má
na stránke Python predloha (PRESIEL_SMERNICAMI_<meno>_1..3), a zapíše tester/webapp_vyber.json: webapp
potom ukáže navrchu tieto stratégie a profily (+ profily aktívnych živých nasadení). Ostatné stratégie sú dole
(„dole“): stratégia zo stránky výsledkov s nastaveniami 1–3 zo stránky, ostatné s najviac 3 najlepšími profilmi,
ktoré majú analytiku (Výkon na 5 oknách, podľa PF). Profily bez analytiky zo stránky idú do webvyber_checkup.txt
(glwebcheckup.sh ich dopočíta). Profil, na ktorý sa odvoláva živé nasadenie, sa nikdy neprepisuje. Nič sa nemaže.

python glwebvyber.py [--apply]
"""
import json, re, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path("/Users/martin/IBS")
sys.path.insert(0, str(ROOT))
from tester.webapp import profiles as P          # noqa: E402
from tradebot.core.paths import WEBAPP_SELECTION, PROFILES_DIR   # noqa: E402
from tradebot.strategies import STRATEGIES        # noqa: E402

TOP = 3
AUDIT = ROOT / "tester" / "audit.json"
# predloha → (C# stratégia, meno C# profilu {n}); None = profily v configs C# stratégie s rovnakým menom ako predloha
MAP = {
    "ibsentry": [("ibsentrynet", "SMERNICE_CS_IBS_Entry_Zone_{n}"), ("ibsentryneteod", "SMERNICE_CS_EOD_IBS_Entry_Zone_{n}")],
    "tks": [("tksnet", "SMERNICE_CS_TKS_{n}"), ("tksneteod", "SMERNICE_CS_EOD_TKS_{n}")],
    "noa": [("noanet", "SMERNICE_CS_NOA_{n}"), ("noaneteod", "SMERNICE_CS_EOD_NOA_{n}")],
    "vwaporb": [("vwaporbnet", "SMERNICE_CS_VWAP_ORB_{n}"), ("vwaporbneteod", "SMERNICE_CS_EOD_VWAP_ORB_{n}")],
    "vwapadx": [("vwapadxnet", "SMERNICE_CS_VWAP_ADX_Pullback_{n}"), ("vwapadxneteod", "SMERNICE_CS_EOD_VWAP_ADX_Pullback_{n}")],
    "ibsentryes": [("ibsentryesnet", None)], "nyvaes": [("nyvaesnet", None)], "fibomgc": [("fibomgcnet", None)],
    "voltbreak": [("voltbreaknet", None)], "sigmamgc": [("sigmamgcnet", None)], "sigma": [("sigmanet", None)],
    "wpr": [("wprnet", None)], "spravy": [("spravynet", "profil_{n}")],
    "spravyeur": [("spravyeurnet", "profil_{n}")],   # 21. 11. 2026: schválil používateľ (výnimka < 75 obch/rok), audit ju nehodnotí
    "noamgc": [("noamgcnet", None)], "mtkorb": [("mtkorbnet", None)],   # 12. 11. 2026: prešli smernicou (používateľ: aj na webapp)
}
NO_WEBAPP: set = set()
APPROVED = {"spravyeur"}   # prešli so súhlasom používateľa mimo auditu (no_audit na stránke)
EOD = {"ibsentryneteod", "tksneteod", "noaneteod", "vwaporbneteod", "vwapadxneteod"}


def page_top(base):
    """[(n, meno, súbor)] nastavení 1..TOP predlohy zo stránky (SPRÁVY: všetky štyri profily)."""
    if base in ("spravy", "spravyeur"):
        return [(i, n, p) for i, (n, p) in enumerate(sorted((n, p) for n, p in P.all_paths(base).items() if n.startswith("profil_")), 1)]
    out = []
    for n, p in P.all_paths(base).items():
        m = re.match(r"PRESIEL_SMERNICAMI_(.+)_(\d+)$", n)
        if m and int(m.group(2)) <= TOP and str(p).startswith(str(PROFILES_DIR)):
            out.append((int(m.group(2)), n, p))
    return sorted(out)


API = "http://127.0.0.1:8765"


def perf(key, name):
    """(okien s behom, PF) z karty Výkon webapp."""
    try:
        d = json.load(urllib.request.urlopen(f"{API}/api/catalog/{key}/report?profile={urllib.parse.quote(name)}", timeout=120))
    except Exception:
        return 0, None
    pf = d.get("performance") or {}
    wins = [w for w in pf.get("windows") or [] if w.get("id")]
    if wins and not runs_match(key, name, [w["id"] for w in wins]):
        return 0, None   # behy na karte Výkon sú zo starších parametrov profilu — prepočítať (16. 11. 2026)
    return len(wins), (pf.get("stats") or {}).get("profit_factor")


def runs_match(key, name, ids):
    """Behy karty Výkon majú parametre, TF a poplatok terajšieho profilu (inak ukazujú iné čísla než stránka výsledkov)."""
    try:
        prof = json.loads(P.all_paths(key)[name].read_text())
    except Exception:
        return True
    import glsearch as G
    for rid in ids:
        try:
            run = json.loads((ROOT / "tester" / "runs" / rid / "run.json").read_text())
        except Exception:
            return False
        rp, st = run.get("params") or {}, run.get("settings") or {}
        for k, v in prof.items():
            if k.startswith("_") or k in ("fixedQty", "qty", "skipOverRisk"):
                continue
            if k in rp and rp[k] != v and not (isinstance(v, (int, float)) and isinstance(rp[k], (int, float)) and abs(rp[k] - v) < 1e-9):
                return False
        if prof.get("_timeframe") and st.get("timeframe") != prof["_timeframe"]:
            return False
        if st.get("fee") is not None and abs(float(st["fee"]) - G.fee(key)) > 1e-9:
            return False
    return True


def removed(key: str) -> bool:
    """Stratégia odstránená zo stránky (`glsearch.REMOVED`) aj s C# portom a EOD kópiou."""
    import glsearch as G
    base = key[:-6] if key.endswith("neteod") else key[:-3] if key.endswith("net") else key
    return key in G.REMOVED or base in G.REMOVED


def bottom(top_keys):
    """Ostatné stratégie: zo stránky nastavenia 1–3, inak 3 najlepšie profily s analytikou; + chýbajúca analytika."""
    dole, missing = {}, []
    for key in STRATEGIES:
        if key in top_keys:
            continue
        if removed(key):                  # 21. 11. 2026: odstránené zo stránky — vo webapp bez profilov
            dole[key] = []
            continue
        page = [n for _, n, _ in page_top(key)]
        if page:
            dole[key] = page
            missing += [(key, n) for n in page if perf(key, n)[0] < 5]
            continue
        scored = []
        for n in P.all_names(key):
            w, pf = perf(key, n)
            if w >= 5 and pf:
                scored.append((pf, n))
        dole[key] = [n for _, n in sorted(scored, reverse=True)[:TOP]]
    return dole, missing


def live_profiles():
    try:
        deps = json.load(urllib.request.urlopen("http://127.0.0.1:8765/api/live/deployments", timeout=20))
    except Exception:
        deps = []
    return {(d["strategy"], d["profile"]) for d in deps if d.get("active")}


def main(apply):
    live = live_profiles()
    sel, changed = {}, []
    for base, nets in MAP.items():
        top = page_top(base)
        for net, pat in nets:
            names = []
            for n, bname, bpath in top:
                src = json.loads(bpath.read_text())
                if base in ("spravy", "spravyeur"):
                    names.append(bname); continue
                name = pat.format(n=n) if pat else bname
                path = (PROFILES_DIR / f"{name}.json") if pat else STRATEGIES[net].profile_dir / f"{name}.json"
                old = json.loads(path.read_text()) if path.exists() else {}
                new = {k: v for k, v in src.items() if not k.startswith("_")}
                new.update({k: v for k, v in src.items() if k.startswith("_")})
                new["_strategy"] = net
                new["_title"] = (src.get("_title") or name) + (" · C# EOD" if net in EOD else " · C#")
                same = {k: v for k, v in old.items() if not k.startswith("_")} == {k: v for k, v in new.items() if not k.startswith("_")}
                if (net, name) in live and not same:
                    print("ŽIVÉ NASADENIE — neprepisujem", net, name); names.append(name); continue
                if not same or old.get("_title") != new["_title"]:
                    changed.append((net, name, "nový" if not old else "parametre" if not same else "popis"))
                    if apply:
                        path.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n")
                names.append(name)
            names += [p for s, p in sorted(live) if s == net and p not in names]
            sel[net] = names
    # navrchu len stratégie, ktoré prešli smernicou a Sortino (používateľ 8. 11. 2026); C# port, keď ho má, inak
    # Python stratégia s nastaveniami 1–3 zo stránky. Stratégia so živým nasadením ostáva navrchu vždy.
    audit = json.loads(AUDIT.read_text()).get("strategies", {}) if AUDIT.exists() else {}
    good = {k for k, a in audit.items() if a.get("cls") in ("A", "B") and a.get("sortino_ok")} | APPROVED
    down, top_missing = {}, []
    for base, nets in MAP.items():
        for net, _ in nets:
            if base not in good and not any(s_ == net for s_, _p in live):
                down[net] = sel.pop(net)
    for base in sorted(good - set(MAP)):
        if base in NO_WEBAPP or base.endswith(("mym", "btc")):   # MYM: na webapp vyberie používateľ (12. 11. 2026)
            continue
        names = [n for _, n, _ in page_top(base)]
        if names:
            sel[base] = names
            top_missing.extend((base, n) for n in names if perf(base, n)[0] < 5)
    for net, names in sel.items():   # aj C# porty navrchu: Výkon musí byť z terajších parametrov (16. 11. 2026)
        top_missing.extend((net, n) for n in names if (net, n) not in top_missing and perf(net, n)[0] < 5)
    print("navrchu:", sorted(sel), "| C# dole (neprešli Sortino):", sorted(down))
    for c in changed:
        print("zmena", *c)
    for k, v in sel.items():
        print(k, v)
    dole, missing = bottom(set(sel) | set(down))
    dole.update(down)
    dole.update({k: [] for k in dole if removed(k)})
    missing = top_missing + missing
    print("dole:", sum(len(v) for v in dole.values()), "profilov,", sum(1 for v in dole.values() if not v), "stratégií bez analytiky;",
          "chýba analytika:", len(missing))
    if apply:
        WEBAPP_SELECTION.write_text(json.dumps({"_popis": "navrchu webapp tieto stratégie a profily, dole ostatné len s profilmi z „dole“ "
                                                "— .nightsearch/glwebvyber.py", "strategies": sel, "dole": dole}, ensure_ascii=False, indent=1) + "\n")
        (ROOT / ".nightsearch" / "webvyber_checkup.txt").write_text("".join(f"{k} {n}\n" for k, n in missing))


if __name__ == "__main__":
    main("--apply" in sys.argv)
