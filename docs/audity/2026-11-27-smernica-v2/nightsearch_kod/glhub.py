"""Hľadanie podľa smernice aj na TradeHube — ďalšie stroje počítajú body okolia najlepšieho nastavenia.

Hyperopt na hube ide len cez Freqtrade, smernica počíta emulátorom MultiCharts — preto sa na hub posielajú
jednotlivé backtesty (`cli run --remote --engine multicharts`) na období ladenia, s poplatkom:

* stratégie z gl_active.txt, východisko = doterajšie najlepšie z gl_state.json (to, čo našlo glsearch),
* bod = náhodný sused: 1 skupina z glsearch.GROUPS, v nej 1–3 parametre na iné hodnoty z mriežky (≤ 4 naraz),
  pravidlá smernice (NO_EXIT: bez trailingu a konca seansy) vždy,
* z vrátených obchodov PF po rokoch a skóre presne ako glsearch.evaluate / score,
* lepší než doterajší najlepší a prejde ladením → plató lokálne (glhyper.plateau) → odložený rok raz lokálne
  → kandidát v hub_state.json (gldash / glreport ho načítajú spolu s hyper_state.json, značka „hub“).

Počet výpočtov naraz = voľné sloty ostatných prijímajúcich agentov hubu (Mac mini počíta lokálne, z hubu nie).
python glhub.py — beží donekonečna; „pozastav testovanie“ (gl_paused) ho zastaví tiež."""
from __future__ import annotations

import json, random, re, subprocess, sys, threading, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import glsearch as G
import glhyper as H

REPO = Path("/Users/martin/IBS")
PY = str(REPO / ".venv/bin/python")
STATE = G.ROOT / "hub_state.json"
TMP = G.ROOT / "hub_tmp"; TMP.mkdir(exist_ok=True)
ME = "MACMINIMARTIN"
SEARCH_NAME = "MACMINI-SEARCH"   # meno, pod ktorým hľadanie zadáva body na hub
LOCK = threading.Lock()
BEST: dict = {}    # kľúč → {"best", "best_r"} z gl_state.json
SEEN: dict = {}
RUN_ID = re.compile(r"^(\d{8}-\d{6}-[0-9a-f]{6})\s", re.M)


def log(*a):
    print(time.strftime("%d. %H:%M"), *a, flush=True)


def load_state():
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    for k in ("candidates", "log"):
        st.setdefault(k, [])
    st.setdefault("trials", {}); st.setdefault("seen", {})
    return st


_DIRTY = threading.Event()


def save_state(st):
    """Len označí zmenu — zapisuje vlákno saver() najviac raz za 30 s (zápis po každom bode zo 22 vlákien
    s rastúcim zoznamom skúšaných bodov bral na Mac mini celé jadro, 17. 10.)."""
    _DIRTY.set()


def _write_state(st):
    with LOCK:
        blob = json.dumps(st, ensure_ascii=False)
    tmp = STATE.with_suffix(".tmp"); tmp.write_text(blob); tmp.replace(STATE)


def saver(st):
    while True:
        time.sleep(30)
        if _DIRTY.is_set():
            _DIRTY.clear()
            _write_state(st)


def paused() -> bool:
    return (G.ROOT / "gl_paused").exists()


def slots(include_me: bool = False) -> int:
    """Sloty agentov, ktoré prijímajú výpočty (bez tohto stroja, ak include_me nie je zapnuté)."""
    try:
        from tester.hub import config as hub_config
        from tester.hub.client import HubClient
        cfg = hub_config.load()
        agents = HubClient.from_config(cfg).status()["agents"]
        pick_versions(agents)
        # Mac mini nesmie počítať výpočty z hubu v webapp (14. 10. ju to zahltilo) — keď sa prijímanie zapne, vypnúť
        if any(a.get("name") == ME and a.get("accept") for a in agents) and cfg.admin_token:
            import dataclasses
            HubClient.from_config(dataclasses.replace(cfg, token=cfg.admin_token)).set_accept(ME, False)
            log("hub: Mac mini mal zapnuté prijímanie výpočtov — vypnuté")
        free = sum(int(a.get("slots") or 0) for a in agents
                   if a.get("online") and a.get("accept") and (include_me or a.get("name") != ME))
        return max(0, min(free, 64))
    except Exception as e:  # noqa: BLE001 — hub mimo: skúsiť neskôr
        log("hub: sloty sa nedali zistiť:", type(e).__name__, str(e)[:120])
        return 0


def stats(rows: list, timerange: str | None = None, key: str | None = None) -> dict:
    """To isté, čo glsearch.evaluate vráti (roky len pre obdobie ladenia)."""
    pnl = [r["profit_abs"] for r in rows]
    gw, gl = sum(x for x in pnl if x > 0), -sum(x for x in pnl if x < 0)
    eq = peak = dd = 0.0
    for x in pnl:
        eq += x; peak = max(peak, eq); dd = max(dd, peak - eq)
    wins = sum(1 for x in pnl if x > 0)
    out = {"trades": len(rows), "wins": wins, "winrate": round(100 * wins / len(rows), 2) if rows else 0.0,
           "pnl_abs": round(sum(pnl), 2), "profit_factor": round(gw / gl, 3) if gl > 0 else (9.0 if gw > 0 else 0.0),
           "max_drawdown_abs": round(dd, 2)}
    if timerange not in (None, G.is_tr(key)):
        return out
    yrs = {}
    for name, a, b in G.windows(key):
        ys = [r["profit_abs"] for r in rows if a <= str(r["open_date"])[:10] < b]
        w, l = sum(x for x in ys if x > 0), -sum(x for x in ys if x < 0)
        yrs[name] = {"trades": len(ys), "pf": round(w / l, 3) if l > 0 else (9.0 if w > 0 else 0.0), "pnl": round(sum(ys), 1)}
    out["years"] = yrs
    return out


_TL = threading.local()


def client():
    """Klient hubu pre toto vlákno (drží trvalé spojenie, nezdieľať medzi vláknami)."""
    if getattr(_TL, "c", None) is None:
        from tester.hub import config as hub_config
        from tester.hub.client import HubClient
        import dataclasses
        # vlastná identita na hube: výsledky si webapp Mac mini nevyzdvihuje (2 375 bodov ju zahltilo, 14. 10.)
        tok = (G.ROOT / "hub_search_token").read_text().strip()
        _TL.c = HubClient.from_config(dataclasses.replace(hub_config.load(), name=SEARCH_NAME, token=tok, admin_token=""))
    return _TL.c


# Plán pre hub (docs/HUB.md „Plán“, používateľ 25. 10. 2026): koľko výpočtov hľadanie ešte pošle do konca testov
# (gl_stop_at.txt, napr. 2026-10-25T18:00) pri rýchlosti za poslednú hodinu, a koľko už má hotových.
_PLAN_LOCK = threading.Lock()
_PLAN = {"done": 0, "times": []}


def plan_numbers() -> tuple[int | None, int | None]:
    f = G.ROOT / "gl_stop_at.txt"
    if not f.exists():
        return None, None
    try:
        stop = time.mktime(time.strptime(f.read_text().strip(), "%Y-%m-%dT%H:%M"))
    except ValueError:
        return None, None
    now = time.time()
    with _PLAN_LOCK:
        _PLAN["times"] = [t for t in _PLAN["times"] if now - t < 3600]
        done, last_hour = _PLAN["done"], len(_PLAN["times"])
    rate = last_hour / 3600.0 if last_hour >= 5 else slots() / 60.0   # na začiatku odhad: sloty × 1 beh za minútu
    left = max(0, int(rate * max(0.0, stop - now)))
    return done + left + 1, done


def _plan_count() -> None:
    with _PLAN_LOCK:
        _PLAN["done"] += 1
        _PLAN["times"].append(time.time())


def remote(key: str, p: dict, timerange: str | None = None) -> tuple[dict | None, str | None]:
    """Jeden bod na hube priamo z tohto procesu — bez CLI podprocesu a bez `git status` pri každom zadaní
    (21 podprocesov s git status vyťažilo Mac mini ~4 jadrami). Parametre a nastavenia skladá tá istá
    funkcia ako `cli run` (_prepare), takže výpočet je ten istý."""
    from tester.webapp.cli.parser import build_parser
    from tester.webapp.cli.run import _prepare
    from tester.hub import gitcode
    tf = int(p["_tf"])
    prof = {k: v for k, v in p.items() if k != "_tf"}
    prof.update({"_strategy": key, "_instrument": G.instr(key)[0], "_timeframe": f"{tf}m"})
    G.one_contract(key, prof)                      # ako glsearch.evaluate: výsledky smernice na 1 kontrakt
    tr = timerange or G.is_tr(key)
    fn = TMP / f"{key}_{threading.get_ident()}.json"; fn.write_text(json.dumps(prof))
    a, b = tr.split("-")
    note = f"SMERNICA hub: {key} bod okolia najlepšieho (ladenie {a}–{b})"
    try:
        args = build_parser("glhub").parse_args(
            ["run", "--strategy", key, "--profile", str(fn), "--timerange", tr, "--timeframe", f"{tf}m",
             "--engine", "multicharts", "--pair", G.instr(key)[1], "--fee", str(G.fee(key)), "--wallet", "60000", "--note", note])
        # bez redirect_stdout: vo vláknach si ho prepisujú navzájom a výstup procesu sa stratí
        params, settings = _prepare(args)
        c = client()
        total, done = plan_numbers()
        job = c.submit("backtest", {"params": params, "settings": settings, "note": note, "user": "glhub"},
                       queue=True, max_wait_seconds=7200, estimate_seconds=60, note=note,
                       version=VERSION.get(key) or gitcode.version() or None, plan_total=total, plan_done=done)
        job = c.wait(job["id"], poll=2)   # 12. 11.: krátke výpočty (MYM pár sekúnd) — 10 s čakania brzdilo hub
        if job.get("status") == "done":
            _plan_count()
        # výsledok do dočasného priečinka, nie do histórie — webapp sa hľadania vôbec nedotkne (14. 10.: mazanie
        # tisícov bodov cez jej API ju zahltilo)
        root = TMP / "runs" / job["id"]; root.mkdir(parents=True, exist_ok=True)
        run_ids = c.collect(job["id"], root)
    except Exception as e:  # noqa: BLE001 — hub mimo, odmietnutie: bod sa skúsi inokedy
        _TL.c = None
        return None, f"{type(e).__name__}: {str(e)[:200]}"
    import shutil
    try:
        if job.get("status") != "done" or not run_ids:
            return None, f"{job['id']} {job.get('status')} {str(job.get('error'))[:200]}"
        rid = job.get("run_id") if job.get("run_id") in run_ids else run_ids[0]
        tf_ = root / rid / "trades.json"
        if not tf_.exists():
            return None, f"beh {rid} bez trades.json"
        return stats(json.loads(tf_.read_text()), tr, key), rid
    finally:
        shutil.rmtree(root, ignore_errors=True)   # dočasný priečinok bodu (nie história)


def forget(run_id: str) -> None:
    """Bod z hubu je len medzivýsledok hľadania (ako lokálne body, tie do histórie nejdú) — po prečítaní
    sa zmaže cez webapp, aby sa dorovnal aj index. Čísla ostávajú v gl_<kľúč>_hub.jsonl. Súhlas používateľa 13. 10. 2026."""
    import urllib.request
    try:
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:8765/api/runs/{run_id}", method="DELETE"), timeout=30)
    except Exception as e:  # noqa: BLE001
        log("hub: beh", run_id, "sa nepodarilo zmazať:", str(e)[:100])


COMPUTE_PATHS = ["tradebot/core", "tradebot/adapters/multicharts", "tester/webapp/runner.py", "tester/webapp/results.py",
                 "tester/webapp/batches.py"]
VERSION: dict = {}   # kľúč → commit, na ktorom sa má na hube počítať


def git(*a) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, timeout=60)


#: Zmeny jadra, ktoré Python stratégie nevolajú (strážca pre C# engine, commit bc812fca6) — výsledok nemenia.
HARMLESS = {'if getattr(engine, "native_entry_layers", False):   # C# engine má obaly vstupov v sebe', "return engine"}


def compute_same(old: str, key: str) -> bool:
    paths = [f"tradebot/strategies/{key}"]
    try:   # variant trhu (m2mnq, …) počíta logikou predlohy — aj jej zmena mení výsledok (28. 10. 2026)
        from tradebot.strategies import STRATEGIES
        base = getattr(STRATEGIES[key], "logic_of", None)
        if base:
            paths.append(f"tradebot/strategies/{base}")
    except Exception:
        paths = []   # nevieme — radšej HEAD
    if not paths:
        return False
    d = git("diff", "-U0", f"{old}..HEAD", "--", *COMPUTE_PATHS, *paths).stdout
    lines = [l[1:].strip() for l in d.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    return all(l in HARMLESS or not l for l in lines)


def pick_versions(agents: list) -> None:
    """Najstarší commit prijímajúcich agentov, ak je predkom HEAD a od neho sa nezmenil kód výpočtu stratégie;
    inak HEAD (agenti, čo si ho nevedia pullnúť, výpočet odmietnu a hub ho dá inému)."""
    vers = {a.get("version") for a in agents if a.get("online") and a.get("accept") and a.get("name") != ME and a.get("version")}
    ok = [v for v in vers if git("merge-base", "--is-ancestor", v, "HEAD").returncode == 0]
    oldest = None
    for v in ok:
        if all(git("merge-base", "--is-ancestor", v, w).returncode == 0 for w in ok):
            oldest = v
    for key in G.active():
        same = oldest and compute_same(oldest, key)
        new = oldest if same else ""
        if VERSION.get(key) != new:
            log("hub:", key, "počíta sa na commite", new or "HEAD")
        VERSION[key] = new


def cleanup() -> None:
    """Body z hubu, ktoré ostali v histórii (glhub bol prerušený skôr, než ich prečítal) — zmazať, ak už nič nebeží."""
    import urllib.parse, urllib.request
    try:
        q = urllib.parse.quote('note~"SMERNICA hub:"')
        d = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8765/api/runs?q={q}&limit=5000", timeout=60).read())
        rows = d.get("runs", d) if isinstance(d, dict) else d
        old = [r["id"] for r in rows if r.get("status") in ("done", "failed", "error")
               and time.time() - (REPO / "tester/runs" / r["id"]).stat().st_mtime > 3600]
    except Exception as e:  # noqa: BLE001
        log("hub: upratovanie zlyhalo:", str(e)[:100]); return
    for rid in old:
        forget(rid)
    if old:
        log("hub: zmazaných starých bodov z histórie", len(old))


def neighbor(key: str, best: dict) -> dict:
    group = random.choice(G.GROUPS[key])
    names = random.sample(list(group), random.randint(1, min(3, len(group))))
    q = dict(best)
    for n in names:
        opts = [v for v in group[n] if v != best.get(n)] or group[n]
        q[n] = random.choice(opts)
    q.update(G.NO_EXIT[key])
    return q


def oos_eval(args):
    key, q = args
    import io, contextlib
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        return G.evaluate(key, q, G.oos_tr(key))


def check(st, key, q, r, best, pool):
    """Kandidát: plató lokálne, odložený rok raz lokálne — ako glhyper.refine."""
    changed = {n for n in q if q.get(n) != best.get(n)}
    pmin, ratios = H.plateau(pool, key, q, r, changed)
    cand = {"p": q, "is": r, "plateau_min": pmin, "plateau": ratios, "t": time.strftime("%Y-%m-%d %H:%M"),
            "source": "hub", "key": key}
    if pmin is None or pmin >= 0.8:
        # v procese poolu, nie v tomto (17. 10.: výpočet tu bral glhubu 2 jadrá a redirect_stdout vo vláknach rozbíjal log)
        cand["oos"] = pool.submit(oos_eval, (key, q)).result()
    with LOCK:
        st["candidates"].append(cand); save_state(st)
    log("   KANDIDÁT (hub)", key, "plató", pmin, "OOS", cand.get("oos", {}).get("profit_factor"))


class HubPool:
    """Náhrada lokálneho ProcessPoolExecutor pre plató a odložený rok: každý bod ide na hub (používateľ 8. 11. 2026:
    „Mac mini na tieto testy vynechaj“, súbor gl_hub_only). `map(G.work, [(kľúč, bod)…])` a `submit(oos_eval, …)`
    vrátia to isté, čo lokálny pool."""

    def map(self, fn, items):
        from concurrent.futures import ThreadPoolExecutor
        items = list(items)
        with ThreadPoolExecutor(max(1, len(items))) as ex:
            return list(ex.map(self._one, [(fn, it) for it in items]))

    @staticmethod
    def _one(arg):
        fn, (key, q) = arg
        tr = G.oos_tr(key) if fn is oos_eval else G.is_tr(key)
        for _ in range(3):
            r, info = remote(key, q, tr)
            if r is not None:
                break
            time.sleep(60)
        return r if fn is oos_eval else (key, q, r, None if r is not None else info)

    def submit(self, fn, arg):
        from concurrent.futures import Future
        f = Future(); f.set_result(self._one((fn, arg)))
        return f


def hub_local() -> set:
    """Stratégie len na Mac mini (gl_hub_local.txt): kód ešte nie je na GitHube, agenti hubu by ho nepoznali (21. 11. 2026)."""
    f = G.ROOT / "gl_hub_local.txt"
    return set(f.read_text().split()) if f.exists() else set()


def hub_only() -> bool:
    return (G.ROOT / "gl_hub_only").exists()


HUB_UP = threading.Event()   # nastavuje hlavné vlákno: na hube je aspoň 1 prijímajúci stroj okrem Mac mini
LOCAL_POOL = None


def local_workers() -> int:
    """Koľko procesov dá Mac mini, keď na hube nepočíta nikto (posledná možnosť); súbor gl_hub_fallback_workers.txt."""
    try:
        return max(1, int((G.ROOT / "gl_hub_fallback_workers.txt").read_text().strip()))
    except Exception:
        return 3


def local_eval(key, q):
    _, _, r, err = LOCAL_POOL.submit(G.work, (key, q)).result()
    return r, (err or "lokálne Mac mini (hub bez kapacity)")


def worker(st, pool, best_seen, local=False):
    while True:
        if local and HUB_UP.is_set():            # hub sa vrátil — lokálny záskok končí
            return
        if paused() or not G.active() or (G.ROOT / "gl_hub_off").exists():   # gl_hub_off: hľadanie len na Mac mini (MTK ZONE, 10. 11. 2026)
            time.sleep(60); continue
        keys = [k for k in G.active() if k not in hub_local()]
        if not keys:
            time.sleep(60); continue
        key = random.choice(keys)
        gl = BEST.get(key)   # gl_state.json má ~170 MB — číta ho len hlavné vlákno raz za 5 min
        if gl and not gl.get("best_r") and key not in best_seen:   # 12. 11.: aj bez gl_hub_only — glsearch ide po stratégiách postupne, hub nečaká hodiny
            r0, _ = remote(key, gl["best"])               # stratégia, ktorú glsearch ešte nepočítal: východisko na hube
            if r0:
                best_seen[key] = {"p": gl["best"], "r": r0}; BEST[key] = {"best": gl["best"], "best_r": r0}
            continue
        if not gl or not gl.get("best_r"):
            time.sleep(60); continue
        best, best_r = gl["best"], gl["best_r"]
        if G.score(best_seen.get(key, {}).get("r"), key) > G.score(best_r, key):   # hub našiel lepšie než glsearch
            best, best_r = best_seen[key]["p"], best_seen[key]["r"]
        with LOCK:
            if key not in SEEN:                      # množina sa zloží raz, nie pri každom pokuse
                SEEN[key] = set(st["seen"].get(key, []))
            for i in range(90):                      # nový, ešte neskúšaný sused; keď ho niet, chvíľu počkať
                q = neighbor(key, best)
                for _ in range(i // 30):             # okolie preskúšané → 2 a 3 kroky ďalej (viac skupín naraz)
                    q = neighbor(key, q)
                s = json.dumps(q, sort_keys=True)
                if s not in SEEN[key] and G.valid(key, q):   # neplatné kombinácie na hub neposielať
                    break
            else:
                s = None
            if s is not None:
                SEEN[key].add(s); st["seen"].setdefault(key, []).append(s)
        if s is None:
            time.sleep(30)
            continue
        r, info = local_eval(key, q) if local else remote(key, q)
        with LOCK:
            st["trials"][key] = st["trials"].get(key, 0) + 1
            with open(G.ROOT / f"gl_{key}_hub.jsonl", "a") as fh:
                fh.write(json.dumps({"p": q, "r": r, "run": info, "t": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False) + "\n")
            save_state(st)
        if r is None:
            log("hub chyba", key, info); time.sleep(30); continue
        if G.score(r, key) > G.score(best_r, key) + 1e-9:
            best_seen[key] = {"p": q, "r": r}
            log("hub", key, "zlepšenie", f"PF {r['profit_factor']:.2f} obch {r['trades']}", {k: v["pf"] for k, v in r["years"].items()},
                f"beh {info}")
            if G.passes_is(r, key):
                check(st, key, q, r, best, pool)


def main():
    import faulthandler, signal
    faulthandler.register(signal.SIGUSR1, file=open(G.ROOT / "glhub_stacks.txt", "w"), all_threads=True)   # kill -USR1 → kde stoja vlákna
    st = load_state()
    best_seen: dict = {}
    # lokálne preverenie kandidátov z hubu — 1 proces (používateľ: „zníž testy 2+1“); s gl_hub_only aj to na hube
    pool = HubPool() if hub_only() else ProcessPoolExecutor(1)
    threads: list[threading.Thread] = []
    local_threads: list[threading.Thread] = []
    # moduly CLI a hubu načítať tu, v hlavnom vlákne — 10 vlákien, ktoré ich importovali naraz, sa zaseklo (17. 10.)
    import tester.webapp.cli.parser, tester.webapp.cli.run, tester.hub.gitcode, tester.hub.client, tester.hub.config  # noqa: F401
    log("glhub štart")
    threading.Thread(target=saver, args=(st,), daemon=True).start()
    n = 0
    while True:
        if n % 12 == 0:
            cleanup()
        n += 1
        try:
            mt = (G.ROOT / "gl_state.json").stat().st_mtime
            if mt == BEST.get("_mtime"):
                raise FileNotFoundError   # nezmenený — netreba čítať 190 MB znova
            gs = json.loads((G.ROOT / "gl_state.json").read_text()); BEST["_mtime"] = mt
            BEST.update({k: {"best": v["best"], "best_r": v.get("best_r")} for k, v in gs.items()
                         if v.get("best_r") or not (BEST.get(k) or {}).get("best_r")}); del gs   # východisko z hubu neprepísať prázdnym
        except FileNotFoundError:
            pass
        except Exception as e:  # noqa: BLE001 — glsearch práve zapisuje: použiť staré
            log("gl_state.json sa nedal načítať:", str(e)[:80])
        if not paused():
            want = slots()
            if want > 0:
                if not HUB_UP.is_set():
                    log("hub: stroje na hube dostupné — počíta hub")
                HUB_UP.set()
                threads = [t for t in threads if t.is_alive()]
                while len(threads) < want:
                    t = threading.Thread(target=worker, args=(st, pool, best_seen), daemon=True); t.start(); threads.append(t)
                    log("hub: výpočtov naraz", len(threads))
            elif hub_only():
                log("hub: žiadny prijímajúci stroj — čakám (gl_hub_only: Mac mini nepočíta)")
            else:
                # na hube nepočíta nikto (spadol hub alebo všetky stroje) → Mac mini ako posledná možnosť, mimo webapp
                global LOCAL_POOL
                if HUB_UP.is_set() or not any(getattr(t, "local", False) and t.is_alive() for t in local_threads):
                    HUB_UP.clear()
                    n_loc = local_workers()
                    if LOCAL_POOL is None:
                        LOCAL_POOL = ProcessPoolExecutor(n_loc)
                    local_threads = [t for t in local_threads if t.is_alive()]
                    while len(local_threads) < n_loc:
                        t = threading.Thread(target=worker, args=(st, pool, best_seen, True), daemon=True)
                        t.local = True; t.start(); local_threads.append(t)
                    log("hub: žiadny stroj na hube nepočíta — záskok na Mac mini,", n_loc, "procesov")
        time.sleep(120 if not HUB_UP.is_set() else 300)


if __name__ == "__main__":
    main()
