"""Vyšší winrate pri pevnom RR — top stratégie webapp znova cez smernicu (používateľ 10. 11. 2026).

„zober top 32 z webapp, prehnaj ich smernicou na 75 obchodov, skús zdvihnúť winrate, RR 1:1 ako základ,
keď nič nebude 0,75 a potom 0,5“; „používaj plný výkon hubu“ (Mac mini nepočíta).

* stratégie = horná časť webapp (tester/webapp_vyber.json → Python predloha); bez pevného RR (výstup na signál
  alebo v čase) sa preskočia,
* východisko = nastavenie č. 1 zo stránky výsledkov, RR sa zafixuje na stupeň (1,0 → 0,75 → 0,5);
  stratégie s cieľom/stopom v jednotkách majú cieľ = RR × stop,
* hľadanie = susedia ako glhub (skupiny glsearch.GROUPS bez parametrov cieľa), každý bod na hube,
* skóre: kým bod neprejde ladením smernice (≥ 75 obch./rok, PF ≥ 1,3, najslabší rok PF ≥ 0,9), glsearch.score;
  potom 1000 + winrate + 10 × PF („min 75 obchodov ročne a držať vysoký PF“),
* kandidát = plató ≥ 80 % a odložený rok ako gldash (PF ≥ 1,3 a ≥ 70 % PF ladenia) — na hube,
* stupeň RR sa zníži, keď na ňom po TRIALS bodoch nie je žiadny prejdený kandidát.

Stav wr_state.json, body gl_<kľúč>_wr.jsonl, log glwr.log. Zastaví ho súbor wr_paused. Na stránku nič nezapisuje.
"""
from __future__ import annotations

import json, random, re, sys, threading, time
from pathlib import Path

sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import glsearch as G
import glhub as HB
import glhyper as H

REPO = Path("/Users/martin/IBS")
STATE = G.ROOT / "wr_state.json"
STAGES = [1.0, 0.75, 0.5]
TRIALS = 300          # bodov na stupeň bez prejdeného kandidáta → nižší RR
LOCK = threading.Lock()

NET = {"ibsentrynet": "ibsentry", "ibsentryneteod": "ibsentry", "tksnet": "tks", "tksneteod": "tks", "noanet": "noa",
       "noaneteod": "noa", "vwaporbnet": "vwaporb", "vwaporbneteod": "vwaporb", "vwapadxnet": "vwapadx",
       "vwapadxneteod": "vwapadx", "ibsentryesnet": "ibsentryes", "nyvaesnet": "nyvaes", "fibomgcnet": "fibomgc",
       "voltbreaknet": "voltbreak", "sigmamgcnet": "sigmamgc", "sigmanet": "sigma", "spravynet": "spravy"}

# ako sa v stratégii zafixuje RR: ("set", parameter, {pevné ďalšie}) alebo ("ratio", cieľ, stop)
RR = {}
for k in ("ibsentry", "tks", "ibsentryes", "nyvaes", "m2mnq", "sweepengulf"):
    RR[k] = ("set", "rrRatio", {})
for k in ("vwaporb", "fibomgc", "crt", "jss", "svp"):
    RR[k] = ("set", "rrRatio", {"tpMode": "rr"})
RR["flashorb"] = ("set", "riskReward", {})
RR["lliqmgc"] = ("set", "riskReward", {"tpType": 1})
for k in ("mag7", "onbiasorb"):
    RR[k] = ("set", "rr", {})
for k in ("orb15", "orb15es", "orb15mgc"):
    RR[k] = ("set", "rr", {"targetMode": 0})
RR["voltbreak"] = ("ratio", "tpUsd", "slUsd")
for k in ("ivb", "ivbes", "ivbmgc"):
    RR[k] = ("ratio", "tpAtrMult", "slAtrMult")
RR["nqprecmgc"] = ("ratio", "atrTpMult", "atrSlMult")
RR["dailyopen"] = ("ratio", "tpPts", "slPts")
FIXED_EXTRA = {"minRR"}   # pri cieli RR nemá význam


def log(*a):
    print(time.strftime("%d. %H:%M"), *a, flush=True)


def keys() -> list:
    top = json.loads((REPO / "tester/webapp_vyber.json").read_text())["strategies"]
    out = []
    for k in top:
        b = NET.get(k, k)
        if b not in out:
            out.append(b)
    return out


def fixed_names(key) -> set:
    kind, a, b = RR[key]
    return ({a} | set(b) | FIXED_EXTRA) if kind == "set" else ({a} | FIXED_EXTRA)


def apply_rr(key, q, rr) -> dict:
    kind, a, b = RR[key]
    if kind == "set":
        q[a] = rr; q.update(b)
    else:
        q[a] = round(rr * float(q[b]), 4)
    q.update(G.NO_EXIT[key])
    return q


def page_start(key) -> dict:
    from tester.webapp import profiles as P
    paths = P.all_paths(key)
    n = next(n for n in sorted(paths) if re.match(r"PRESIEL_SMERNICAMI_.+_1$", n))
    prof = json.loads(Path(paths[n]).read_text())
    tf = prof.get("_timeframe", "")
    p = {k: v for k, v in prof.items() if not k.startswith("_")}
    p["_tf"] = int(tf[:-1]) * (60 if tf.endswith("h") else 1)
    return {"name": n, "p": p}


def wr_score(r, key) -> float:
    if not r:
        return -1e9
    if G.passes_is(r, key):
        return 1000.0 + (r.get("winrate") or 0) + 10.0 * min(r.get("profit_factor") or 0, 3.0)   # „držať vysoký PF“
    return G.score(r, key)


def oos_ok(c) -> bool:
    o = c.get("oos")
    return bool(o) and c["is"]["trades"] / G.YEARS >= G.MIN_TRADES_YEAR and o["profit_factor"] >= 1.3 \
        and o["profit_factor"] >= 0.7 * c["is"]["profit_factor"]


def neighbor(key, best) -> dict:
    fx = fixed_names(key)
    groups = [{n: v for n, v in g.items() if n not in fx} for g in G.GROUPS[key]]
    groups = [g for g in groups if g]
    g = random.choice(groups)
    q = dict(best)
    for n in random.sample(list(g), random.randint(1, min(3, len(g)))):
        q[n] = random.choice([v for v in g[n] if v != best.get(n)] or g[n])
    return q


def load():
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    for k in keys():
        if k in RR and k not in st:
            st[k] = {"stage": 0, "trials": 0, "stage_trials": 0, "page": None, "best": None, "best_r": None,
                     "candidates": [], "seen": []}
    return st


def save(st):
    with LOCK:
        blob = json.dumps(st, ensure_ascii=False)
    tmp = STATE.with_suffix(".tmp"); tmp.write_text(blob); tmp.replace(STATE)


def remote(key, q, tr=None):
    for _ in range(3):
        r, info = HB.remote(key, q, tr)
        if r is not None:
            return r, info
        log("hub chyba", key, info); time.sleep(30)
    return None, info


def init_key(st, key):
    """Nastavenie č. 1 zo stránky (východisko winrate) a jeho verzia na aktuálnom stupni RR."""
    S = st[key]
    if S["page"] is None:
        ps = page_start(key)
        r, _ = remote(key, ps["p"])
        S["page"] = {"name": ps["name"], "p": ps["p"], "r": r}
        log(key, "stránka", ps["name"], r and f"WR {r['winrate']} PF {r['profit_factor']} obch {r['trades']}")
    if S["best"] is None:
        q = apply_rr(key, dict(S["page"]["p"]), STAGES[S["stage"]])
        r, _ = remote(key, q)
        S["best"], S["best_r"] = q, r
        log(key, f"RR {STAGES[S['stage']]} východisko", r and f"WR {r['winrate']} PF {r['profit_factor']} obch {r['trades']}")
    save(st)


def next_stage(st, key):
    S = st[key]
    rr = STAGES[S["stage"]]
    if any(c["rr"] == rr and c.get("ok") for c in S["candidates"]):
        return
    if S["stage_trials"] >= TRIALS and S["stage"] + 1 < len(STAGES):
        S["stage"] += 1; S["stage_trials"] = 0; S["best"] = S["best_r"] = None
        log(key, f"RR {rr}: po {TRIALS} bodoch nič neprešlo → RR {STAGES[S['stage']]}")


def done(S) -> bool:
    """Posledný stupeň bez kandidáta po TRIALS bodoch — stratégia končí."""
    return S["stage"] == len(STAGES) - 1 and S["stage_trials"] >= 2 * TRIALS \
        and not any(c["rr"] == STAGES[-1] and c.get("ok") for c in S["candidates"])


SEEN: dict = {}
BUSY: dict = {}


def worker(st, pool):
    while True:
        if (G.ROOT / "wr_paused").exists():
            time.sleep(60); continue
        with LOCK:
            ks = [k for k in st if not done(st[k])]
            # stratégia bez východiska ju dostane jedno vlákno
            free = [k for k in ks if st[k]["best"] is None and not BUSY.get(k)]
            key = free[0] if free else random.choice([k for k in ks if st[k]["best"] is not None] or [None])
            if key and st[key]["best"] is None:
                BUSY[key] = True
        if key is None:
            time.sleep(60); continue
        S = st[key]
        if S["best"] is None:
            try:
                init_key(st, key)
            finally:
                BUSY[key] = False
            continue
        if not S["best_r"]:
            time.sleep(30); continue
        rr = STAGES[S["stage"]]
        with LOCK:
            if key not in SEEN:
                SEEN[key] = set(S["seen"])
            for i in range(90):
                q = neighbor(key, S["best"])
                for _ in range(i // 30):
                    q = neighbor(key, q)
                apply_rr(key, q, rr)
                s = json.dumps(q, sort_keys=True)
                if s not in SEEN[key]:
                    break
            else:
                s = None
            if s:
                SEEN[key].add(s); S["seen"].append(s)
        if s is None:
            time.sleep(30); continue
        r, info = remote(key, q)
        with LOCK:
            S["trials"] += 1; S["stage_trials"] += 1
            with open(G.ROOT / f"gl_{key}_wr.jsonl", "a") as fh:
                fh.write(json.dumps({"rr": rr, "p": q, "r": r, "run": info, "t": time.strftime("%Y-%m-%d %H:%M")},
                                    ensure_ascii=False) + "\n")
            if STAGES[S["stage"]] != rr:      # medzitým iný stupeň
                continue
            better = r and wr_score(r, key) > wr_score(S["best_r"], key) + 1e-9
            prev = S["best"]
            if better:
                S["best"], S["best_r"] = q, r
        if r and better:
            log(key, f"RR {rr} zlepšenie WR {r['winrate']} PF {r['profit_factor']:.2f} obch {r['trades']}",
                {k: v["pf"] for k, v in r["years"].items()})
            if G.passes_is(r, key):
                changed = {n for n in q if q.get(n) != prev.get(n)}
                pmin, ratios = H.plateau(pool, key, q, r, changed)
                c = {"rr": rr, "p": q, "is": r, "plateau_min": pmin, "plateau": ratios, "t": time.strftime("%Y-%m-%d %H:%M")}
                if pmin is None or pmin >= 0.8:
                    c["oos"], _ = remote(key, q, G.OOS)
                c["ok"] = oos_ok(c)
                with LOCK:
                    S["candidates"].append(c)
                log("   KANDIDÁT", key, f"RR {rr} WR {r['winrate']}", "plató", pmin,
                    "OOS", (c.get("oos") or {}).get("profit_factor"), "PREŠIEL" if c["ok"] else "neprešiel")
        with LOCK:
            next_stage(st, key)


def main():
    st = load()
    # verzia na hube: HB.pick_versions (cez HB.slots) nastaví commit agentov pre G.active() — tu sú to naše stratégie
    # (agenti majú git pull vypnutý; commit len so šablónou stránky výpočet nemení)
    G.active = lambda: list(st)
    pool = HB.HubPool()
    import tester.webapp.cli.parser, tester.webapp.cli.run, tester.hub.gitcode, tester.hub.client, tester.hub.config  # noqa: F401
    log("glwr štart —", len(st), "stratégií:", " ".join(st))
    threads = []
    while True:
        save(st)
        # koniec testov (používateľ: „máš na to čas do zajtra večera 18:00“) — wr_stop_at.txt, napr. 2026-11-11T18:00
        try:
            stop = time.mktime(time.strptime((G.ROOT / "wr_stop_at.txt").read_text().strip(), "%Y-%m-%dT%H:%M"))
        except Exception:
            stop = None
        if stop and time.time() >= stop:
            (G.ROOT / "wr_stop").touch(); (G.ROOT / "wr_paused").touch()
            log("koniec testov — termín", (G.ROOT / "wr_stop_at.txt").read_text().strip())
            import os; os._exit(0)
        want = HB.slots() if not (G.ROOT / "wr_paused").exists() else 0
        threads = [t for t in threads if t.is_alive()]
        while len(threads) < want:
            t = threading.Thread(target=worker, args=(st, pool), daemon=True); t.start(); threads.append(t)
        if want and len(threads) == want:
            pass
        time.sleep(120)


if __name__ == "__main__":
    main()
