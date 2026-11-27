"""IBS Entry Zone s vyšším RR na TradeHube (zadanie používateľa 14. 10. 2026).

Východisko: profily PRESIEL_SMERNICAMI_IBS_Entry_Zone_1..10 (všetky RR 0,5). Pre každý profil a každé cieľové RR
(0,6 · 0,7 · 0,75 · 0,8 · 0,9 · 1,0) sa RR zafixuje a hľadajú sa ostatné parametre tak, aby výsledok ostal čo najbližšie
pôvodnému — podľa smernice: skóre glsearch.score (PF, žiadny rok pod 0,9, ≥ 150 obch/rok), nikdy winrate.

* bod = sused najlepšieho v úlohe: 1 skupina z glsearch.GROUPS["ibsentry"] bez rrRatio, 1–3 parametre (≤ 4 naraz),
  pravidlá smernice (bez trailingu a konca seansy) vždy; počíta hub (glhub.remote, emulátor MultiCharts, obdobie ladenia),
* úloha má rozpočet BUDGET bodov; potom najlepší bod: prejde ladením → plató lokálne → odložený rok raz lokálne,
* stav v rr_state.json, log glrr.log, tabuľka rr_report.md.

python glrr.py — skončí, keď sú všetky úlohy hotové."""
from __future__ import annotations

import json, random, sys, threading, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import glsearch as G
import glhyper as H
import glhub as HB

KEY = "ibsentry"
RRS = [0.6, 0.7, 0.75, 0.8, 0.9, 1.0]
PROFILES = list(range(1, 11))
BUDGET = 100
LOCAL = 6        # procesov na Mac mini (10 jadier; webapp a systém potrebujú rezervu)
STATE = G.ROOT / "rr_state.json"
REPORT = G.ROOT / "rr_report.md"
LOCK = threading.Lock()
GROUPS = [{n: v for n, v in g.items() if n != "rrRatio"} for g in G.GROUPS[KEY]]
GROUPS = [g for g in GROUPS if g]


def log(*a):
    print(time.strftime("%d. %H:%M"), *a, flush=True)


def base(n: int) -> dict:
    d = json.load(open(f"/Users/martin/IBS/tester/profiles/PRESIEL_SMERNICAMI_IBS_Entry_Zone_{n}.json"))
    p = {k: v for k, v in d.items() if not k.startswith("_")}
    p.update(G.NO_EXIT[KEY]); p["_tf"] = int(str(d["_timeframe"]).rstrip("m"))
    return p


def load():
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    for n in PROFILES:
        for rr in RRS:
            t = st.setdefault(f"{n}@{rr}", {"n": n, "rr": rr, "best": None, "best_r": None, "done": 0, "seen": [], "final": None})
            if t["best"] is None:
                p = base(n); p["rrRatio"] = rr; t["start"] = p
    return st


def save(st):
    tmp = STATE.with_suffix(".tmp"); tmp.write_text(json.dumps(st, ensure_ascii=False)); tmp.replace(STATE)


def neighbor(p: dict) -> dict:
    g = random.choice(GROUPS)
    q = dict(p)
    for n in random.sample(list(g), random.randint(1, min(3, len(g)))):
        opts = [v for v in g[n] if v != p.get(n)] or g[n]
        q[n] = random.choice(opts)
    q.update(G.NO_EXIT[KEY])
    return q


def next_point(st):
    """Úloha s najmenej bodmi (najprv nižšie RR), ktorá ešte nemá rozpočet minutý."""
    with LOCK:
        open_ = [t for t in st.values() if t["done"] + t.get("inflight", 0) < BUDGET]
        if not open_:
            return None, None
        t = min(open_, key=lambda t: (t["done"] + t.get("inflight", 0), t["rr"], t["n"]))
        if t["best"] is None and not t.get("inflight"):
            q = dict(t["start"])                       # prvý bod úlohy = pôvodný profil s novým RR
        else:
            src = t["best"] or t["start"]
            for _ in range(20):
                q = neighbor(src)
                if json.dumps(q, sort_keys=True) not in t["seen"]:
                    break
        t["seen"].append(json.dumps(q, sort_keys=True)); t["inflight"] = t.get("inflight", 0) + 1
        return t, q


LOCAL_POOL = None   # Mac mini počíta vlastnými procesmi (nie cez webapp — tá pri výpočtoch z hubu prestala odpovedať, 14. 10.)


def evaluate_local(q):
    _, _, r, err = LOCAL_POOL.submit(G.work, (KEY, q)).result()
    return r, (err or "lokálne Mac mini")


def worker(st, local=False):
    while True:
        t, q = next_point(st)
        if t is None:
            return
        r, info = evaluate_local(q) if local else HB.remote(KEY, q)
        with LOCK:
            t["inflight"] -= 1
            if r is None:
                t["seen"].pop(t["seen"].index(json.dumps(q, sort_keys=True)))
                log("hub chyba", info); err = True
                if "NoCapacity" in str(info):
                    save(st); return
            else:
                err = False
                t["done"] += 1
                with open(G.ROOT / "gl_ibsentry_rr.jsonl", "a") as fh:
                    fh.write(json.dumps({"task": f"{t['n']}@{t['rr']}", "p": q, "r": r, "run": info,
                                         "t": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False) + "\n")
                if G.score(r) > G.score(t["best_r"]):
                    t["best"], t["best_r"] = q, r
                    log(f"IBS EZ {t['n']} RR {t['rr']}: PF {r['profit_factor']:.2f} obch/rok {r['trades'] / G.YEARS:.0f} WR {r['winrate']:.0f} %",
                        {k: v["pf"] for k, v in r["years"].items()}, f"bod {t['done']}")
            save(st)
        if err:
            time.sleep(30)


def finalize(st):
    """Najlepší bod každej úlohy: ladenie → plató → odložený rok raz (lokálne)."""
    import io, contextlib
    with ProcessPoolExecutor(3) as pool:
        for key, t in st.items():
            if t["final"] is not None or not t["best_r"]:
                continue
            r, p = t["best_r"], t["best"]
            fin = {"passes_is": G.passes_is(r), "plateau_min": None, "plateau": [], "oos": None}
            if fin["passes_is"]:
                changed = {n for n in p if p.get(n) != t["start"].get(n) and n != "rrRatio"} or \
                          {n for n in ("slLookback", "minSlDistance", "slBufferTicks") if n in p}
                fin["plateau_min"], fin["plateau"] = H.plateau(pool, KEY, p, r, changed)
                if fin["plateau_min"] is None or fin["plateau_min"] >= 0.8:
                    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                        fin["oos"] = G.evaluate(KEY, p, G.OOS)
            o = fin["oos"]
            combos = sum(x["done"] for x in st.values())
            need = 1.3 if combos > 1000 else 1.2
            fin["passed"] = bool(o and fin["passes_is"] and (fin["plateau_min"] is None or fin["plateau_min"] >= 0.8)
                                 and o["profit_factor"] >= need and o["profit_factor"] >= 0.7 * r["profit_factor"])
            t["final"] = fin; save(st)
            log(f"HOTOVO IBS EZ {t['n']} RR {t['rr']}: ladenie PF {r['profit_factor']:.2f}, plató {fin['plateau_min']},",
                f"OOS PF {o['profit_factor'] if o else '-'} → {'PREŠIEL' if fin['passed'] else 'neprešiel'}")


def report(st):
    orig = {n: json.load(open(f"/Users/martin/IBS/tester/profiles/PRESIEL_SMERNICAMI_IBS_Entry_Zone_{n}.json"))["_title"] for n in PROFILES}
    out = ["# IBS Entry Zone s vyšším RR (hub, 14. 10. 2026)", "",
           "Ladenie 10/2021–9/2025, MNQ, poplatok 1,755e-05, emulátor MultiCharts; posledný rok = odložený rok 9/2025–9/2026.", "",
           "| profil | RR | obch/rok | WR | PF ladenie | PF po rokoch | plató | posl. rok obch | WR | PF | zisk | DD | smernica |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in sorted(st.values(), key=lambda t: (t["n"], t["rr"])):
        r, f = t["best_r"], t.get("final") or {}
        if not r:
            continue
        o = f.get("oos") or {}
        yrs = " / ".join(f"{v['pf']:.2f}" for v in r["years"].values())
        out.append(f"| {t['n']} | {t['rr']} | {r['trades'] / G.YEARS:.0f} | {r['winrate']:.0f} % | {r['profit_factor']:.2f} | {yrs} | "
                   f"{f.get('plateau_min') if f.get('plateau_min') is not None else '-'} | {o.get('trades', '-')} | "
                   f"{(str(round(o['winrate'])) + ' %') if o else '-'} | {o.get('profit_factor', '-')} | {o.get('pnl_abs', '-')} | "
                   f"{o.get('max_drawdown_abs', '-')} | {'PREŠIEL' if f.get('passed') else 'nie'} |")
    out += ["", "Pôvodné profily (RR 0,5):"] + [f"- {n}: {orig[n]}" for n in PROFILES]
    REPORT.write_text("\n".join(out) + "\n")


def main():
    st = load(); save(st)
    from tester.hub import config as hub_config
    from tester.hub.client import HubClient
    agents = HubClient.from_config(hub_config.load()).status()["agents"]
    vers = {a.get("version") for a in agents if a.get("online") and a.get("accept") and a.get("name") != HB.ME and a.get("version")}
    ok = [v for v in vers if HB.git("merge-base", "--is-ancestor", v, "HEAD").returncode == 0]
    oldest = next((v for v in ok if all(HB.git("merge-base", "--is-ancestor", v, w).returncode == 0 for w in ok)), None)
    HB.VERSION[KEY] = oldest if oldest and HB.compute_same(oldest, KEY) else ""
    log("glrr štart, commit na hube:", HB.VERSION[KEY] or "HEAD", "úloh", len(st))
    global LOCAL_POOL
    LOCAL_POOL = ProcessPoolExecutor(LOCAL)
    for _ in range(LOCAL):
        threading.Thread(target=worker, args=(st, True), daemon=True).start()
    log("Mac mini lokálne procesov", LOCAL)
    th: list[threading.Thread] = []
    while True:   # počet výpočtov naraz = sloty prijímajúcich agentov (okrem Mac mini), dorovnáva sa každé 2 min
        if all(t["done"] + t.get("inflight", 0) >= BUDGET for t in st.values()) and not any(x.is_alive() for x in th):
            break
        want = HB.slots()   # ostatné stroje na hube; Mac mini počíta lokálne (LOCAL procesov)
        alive = [x for x in th if x.is_alive()]
        while len(alive) < want:
            x = threading.Thread(target=worker, args=(st,), daemon=True); x.start(); alive.append(x)
            log("výpočtov naraz", len(alive))
        th = alive
        if not th:
            log("hub: žiadny prijímajúci agent okrem Mac mini — čakám")
        time.sleep(120); report(st)
    finalize(st); report(st)
    log("glrr koniec — tabuľka", REPORT)


if __name__ == "__main__":
    main()
