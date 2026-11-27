"""Hyperopt na lokálne optimá z hľadania podľa smernice (glsearch.py).

Keď sa hľadanie zasekne (okolie bodu je preskúšané), pošle bod do fronty hyper_queue.jsonl a samo skočí
na nové nastavenia. Tento proces si body z fronty berie a jemne ich dolaďuje cez Optunu (TPE):

* podľa smernice vždy najviac 4 parametre naraz (tie isté skupiny ako glsearch), skupina po skupine,
* číselné parametre spojito v rozsahu mriežky rozšírenom o 30 % (mriežka už bola preskúšaná),
  ostatné z mriežky; štart vždy z hodnôt optima (enqueue_trial),
* cieľ je to isté skóre ako v glsearch (PF, roky ≥ 0,9, ≥ 100 obch/rok),
* výsledok, ktorý prejde ladením a je lepší než štart → plató (±10 % pri zmenených číselných parametroch
  ≥ 80 % PF) → odložený rok raz. Kandidáti v hyper_state.json (gldash ich ukáže so značkou hyperopt).

python glhyper.py — beží donekonečna, procesy zo súboru gl_hyper_workers.txt (default 3)."""
from __future__ import annotations

import json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import glsearch as G

Q = G.ROOT / "hyper_queue.jsonl"
STATE = G.ROOT / "hyper_state.json"
TRIALS_PER_GROUP = 40


def hworkers() -> int:
    try:
        return max(1, int((G.ROOT / "gl_hyper_workers.txt").read_text().strip()))
    except Exception:
        return 3


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"done": [], "candidates": [], "trials": {}, "log": []}


def save_state(st):
    tmp = STATE.with_suffix(".tmp"); tmp.write_text(json.dumps(st, ensure_ascii=False)); tmp.replace(STATE)


def space(values):
    """(druh, args) pre Optunu z hodnôt mriežky."""
    if all(isinstance(v, bool) for v in values) or not all(isinstance(v, (int, float)) for v in values):
        return ("cat", values)
    lo, hi = min(values), max(values)
    lo2, hi2 = (0 if lo == 0 else lo * 0.7), hi * 1.3
    if all(isinstance(v, int) for v in values):
        return ("int", (int(round(lo2)), max(int(round(hi2)), int(lo2) + 1)))
    return ("float", (float(lo2), float(hi2)))


def suggest(trial, name, values):
    kind, a = space(values)
    if name == "_tf":
        return trial.suggest_categorical(name, values)
    if kind == "cat":
        return trial.suggest_categorical(name, a)
    if kind == "int":
        return trial.suggest_int(name, *a)
    return round(trial.suggest_float(name, *a), 3)


def run_batch(pool, key, items):
    return list(pool.map(G.work, [(key, q) for q in items]))


def plateau(pool, key, p, r, changed):
    test = []
    for n in changed:
        v = p[n]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or n == "_tf" or v == 0:
            continue
        for f in (0.9, 1.1):
            q = dict(p); q[n] = (int(round(v * f)) if isinstance(v, int) else round(v * f, 3))
            if q[n] != v:
                test.append(q)
    if not test:
        return None, []
    ratios = [round((rr["profit_factor"] or 0) / r["profit_factor"], 3) for _, _, rr, _ in run_batch(pool, key, test) if rr]
    return (min(ratios) if ratios else None), ratios


def refine(pool, st, item):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    key, best, best_r = item["key"], dict(item["p"]), item["r"]
    start_score, changed = G.score(best_r, key), set()
    for gi, group in enumerate(G.GROUPS[key]):
        names = [n for n in group if n in best or n == "_tf"]
        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=random.randint(0, 10**6)))
        study.enqueue_trial({n: best[n] for n in names if n in best})
        done, bs = 0, 1
        while done < TRIALS_PER_GROUP:
            bs = hworkers()
            trials = [study.ask() for _ in range(bs)]
            qs = []
            for t in trials:
                q = dict(best); q.update({n: suggest(t, n, group[n]) for n in names}); q.update(G.NO_EXIT[key]); qs.append(q)
            for t, (_, q, r, err) in zip(trials, run_batch(pool, key, qs)):
                study.tell(t, G.score(r, key) if r else -1e9)
                st["trials"][key] = st["trials"].get(key, 0) + 1
                if r and G.score(r, key) > G.score(best_r, key):
                    changed |= {n for n in names if q.get(n) != best.get(n)}
                    best, best_r = q, r
            done += bs
        print(time.strftime("%d. %H:%M"), "HYPEROPT", key, f"skupina {gi + 1}", f"PF {best_r['profit_factor']:.2f} obch {best_r['trades']}",
              {k: v["pf"] for k, v in best_r.get("years", {}).items()}, flush=True)
        save_state(st)
    improved = G.score(best_r, key) > start_score + 1e-9
    entry = {"key": key, "t": time.strftime("%Y-%m-%d %H:%M"), "start_pf": item["r"]["profit_factor"], "pf": best_r["profit_factor"],
             "improved": improved}
    if improved and G.passes_is(best_r, key):
        pmin, ratios = plateau(pool, key, best, best_r, changed)
        cand = {"p": best, "is": best_r, "plateau_min": pmin, "plateau": ratios, "t": entry["t"], "source": "hyperopt", "key": key}
        if pmin is None or pmin >= 0.8:
            import io, contextlib
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                cand["oos"] = G.evaluate(key, best, G.oos_tr(key))          # odložený rok — raz
        st["candidates"].append(cand)
        print("   KANDIDÁT (hyperopt)", key, "plató", pmin, "OOS", cand.get("oos", {}).get("profit_factor"), flush=True)
    st["log"].append(entry)


def main():
    # pozastavené používateľom („pozastav testovanie“) — aj po reštarte ostať stáť, kým nepovie „zapni“
    if (ROOT / "gl_paused").exists() if "ROOT" in globals() else (G.ROOT / "gl_paused").exists():
        import signal
        os.kill(os.getpid(), signal.SIGSTOP)
    st = load_state()
    while True:
        items = [json.loads(l) for l in open(Q)] if Q.exists() else []
        todo = [x for x in items if x["sig"] not in st["done"] and x["key"] in G.active()]
        if not todo:
            time.sleep(60); continue
        # najprv najsľubnejšie (najvyššie skóre)
        item = max(todo, key=lambda x: G.score(x["r"], x["key"]))
        print(time.strftime("%d. %H:%M"), "HYPEROPT štart", item["key"], f"PF {item['r']['profit_factor']:.2f}", flush=True)
        with ProcessPoolExecutor(hworkers()) as pool:
            refine(pool, st, item)
        st["done"].append(item["sig"]); save_state(st)


if __name__ == "__main__":
    main()
