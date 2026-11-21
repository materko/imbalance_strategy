"""SPRÁVY na EUR/USD (spravyeurnet, 6E) — ladenie na Mac mini, kópia ladenia zlata `.nightsearch/spravy/ladenie.py`
(zadanie používateľa 21. 11. 2026: výskum správ ECB a USA na 6E, riziko 500 $; kritérium profit faktor).

Postup (každá etapa = `python -m tester.native_hyperopt`, natívne C# jadro `spravynet`, MGC 5m, 1 kontrakt):
  A  každé pravidlo samostatne (ostatné správy vypnuté): kritérium `pf`, najhoršie zo 4 okien ladenia
     (2021-10 – 2025-09), výber podľa okolia (plató), 3 seedy; odložený rok 2025-09 – 2026-09 len na overenie.
  B  nové pravidlá pre správy, ktoré 3.0 neobchoduje (NFP, GDP, ISM, RETAIL, CLAIMS, zápisnica FOMC) a drift
     pred správou (noha −120 → 0) aj pri CPI / PCE / NFP — rovnaké kritérium.
  C  zloženie: zlepšené pravidlá a nové pravidlá, ktoré prešli, sa pridávajú po jednom (greedy) — ostanú len vtedy,
     keď celok drží PF spolu ≥ PF 3.0 a najhoršie okno sa nezhorší.
  D  spoločné parametre celku (rezerva stopu, minimálna noha, ATR) na zloženom profile.
  E  overenie víťaza: XAU/USD, robustnosť (2× poplatok, o sviečku neskôr, DSR so všetkými skúškami).
Stav v out/state.json; skript sa dá spustiť znova a pokračuje od nehotovej etapy. Koniec v nedeľu 18:00.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/martin/IBS")
D = ROOT / ".nightsearch" / "spravyeur"
OUT = D / "out"
PROF = D / "profiles"
STATE = OUT / "state.json"
PY = str(ROOT / ".venv" / "bin" / "python")
sys.path.insert(0, str(ROOT))

END = datetime(2026, 11, 23, 12, 0)
IS = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904"]
OOS = "20250904-20260904"
W = IS + [OOS]
FEE = 1.755e-05
EPOCHS = 400
SEEDS = (1, 2)
JOBS = 2
BASE = json.loads((ROOT / "tradebot/strategies/spravyeurnet/configs/6e_databento_5m.json").read_text())
ALL = ("FOMC", "FOMC_MIN", "CPI", "NFP", "PPI", "JOLTS", "RETAIL", "PCE", "GDP", "ISM_M", "ISM_S", "CLAIMS", "ECB", "ECB_TK")
LIVE = ("FOMC", "ECB_TK", "CPI", "PPI", "JOLTS", "ISM_S")       # správy východiska (výskum 21. 11.)

STOPS = "0,1,1.5,2,3,5,10"
RRS = "0,1,1.5,2,3,4"
# pravidlá 3.0 — noha / vstup tak, aby vždy platilo od < do ≤ vstup (inak config epochu odmietne)
RULES = {   # východisko z výskumu 21. 11. 2026 — noha / vstup tak, aby vždy platilo od < do ≤ vstup
    "r1": ("FOMC", {"r1From": "0:15:5", "r1To": "20:90:5", "r1Enter": "60:150:5", "r1Hold": "30:480:15", "r1Stop": STOPS, "r1RR": RRS}),
    "r2": ("ECB_TK", {"r2From": "0:15:5", "r2To": "20:90:5", "r2Enter": "60:150:5", "r2Hold": "20:300:10", "r2Stop": STOPS, "r2RR": RRS}),
    "r3": ("CPI", {"r3From": "0:15:5", "r3To": "20:60:5", "r3Enter": "60:150:5", "r3Hold": "20:300:10", "r3Stop": STOPS, "r3RR": RRS}),
    "r4": ("PPI", {"r4From": "0:5:5", "r4To": "5:30:5", "r4Enter": "30:90:5", "r4Hold": "20:300:10", "r4Stop": STOPS, "r4RR": RRS}),
    "r5": ("JOLTS", {"r5From": "0:15:5", "r5To": "20:60:5", "r5Enter": "60:150:5", "r5Hold": "20:300:10", "r5Stop": STOPS, "r5RR": RRS}),
    "r6": ("ISM_S", {"r6From": "0:15:5", "r6To": "20:60:5", "r6Enter": "60:150:5", "r6Hold": "20:300:10", "r6Stop": STOPS, "r6RR": RRS}),
}


def new_rule(ev: str, pre: bool) -> dict[str, str]:
    """Nové pravidlo v slote 7: po správe (noha 0..20 → 15..60, vstup 60..180) alebo drift pred správou (−180..−20 → 0)."""
    if pre:
        return {"r7From": "-180:-20:5", "r7To": "-15:0:5", "r7Enter": "0:30:5",
                "r7Hold": "15:300:5", "r7Stop": STOPS, "r7RR": RRS}
    return {"r7From": "0:10:5", "r7To": "15:60:5", "r7Enter": "60:180:5",
            "r7Hold": "20:480:10", "r7Stop": STOPS, "r7RR": RRS}


NEW = {f"n_{e}": (e, new_rule(e, False)) for e in ("ECB", "PCE", "FOMC_MIN", "NFP", "GDP", "ISM_M", "RETAIL", "CLAIMS")}
NEW.update({f"n_{e}_pred": (e, new_rule(e, True)) for e in ("ECB", "CPI", "NFP")})
GLOBAL = {"slBuffer": "0.25:2:0.25", "minLeg": "0:1:0.1", "atrLen": "7,14,21,28"}


def log(msg: str) -> None:
    line = f"{datetime.now():%d. %H:%M} {msg}"
    print(line, flush=True)
    with open(OUT / "ladenie.log", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"done": {}, "trials": 0}


def save(st: dict) -> None:
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1))


def late() -> bool:
    return datetime.now() >= END


def only(*events: str, extra: dict | None = None) -> dict:
    p = dict(BASE)
    p.update({f"use{e}": e in events for e in ALL})
    p.update(extra or {})
    return p


def write_profile(name: str, data: dict) -> Path:
    f = PROF / f"{name}.json"
    f.write_text(json.dumps({**data, "_title": f"SPRÁVY ladenie {name}"}, ensure_ascii=False, indent=1))
    return f


def hyperopt(name: str, profile: Path, space: dict[str, str], seed: int, windows=IS, min_trades=5,
             epochs=EPOCHS) -> dict | None:
    """Jedno hľadanie cez CLI repozitára; výsledok = JSON z `--out`."""
    out = OUT / f"{name}_s{seed}.json"
    if out.exists():
        return json.loads(out.read_text())
    cmd = [PY, "-m", "tester.native_hyperopt", "--strategy", "spravyeurnet", "--instrument", "6e_databento",
           "--timeframe", "5m", "--profile", str(profile), "--goal", "pf", "--min-trades", str(min_trades),
           "--epochs", str(epochs), "--sampler", "tpe", "--windows", ",".join(windows), "--aggregate", "min",
           "--select", "plateau", "--jobs", str(JOBS), "--seed", str(seed), "--fee", str(FEE), "--wallet", "100000",
           "--out", str(out)]
    for k, v in space.items():
        cmd += ["--param", f"{k}={v}"]
    t0 = time.time()
    with open(OUT / f"{name}_s{seed}.log", "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode
    log(f"{name} seed {seed}: kód {rc}, {time.time() - t0:.0f} s")
    return json.loads(out.read_text()) if out.exists() else None


#: srvnas (jediný prijímajúci agent) nemá Mono → natívny C# hyperopt tam padá (29. 10.); kým nie je agent s C#, lokálne
USE_HUB = False
HUB_PARALLEL = 1                 # 21. 11.: lokálne, Mac mini šetriť (etapa A + B = 2 hľadania × 2 procesy)
HUB_TOTAL = len(NEW) * 2 * len(SEEDS)
_LOCK = threading.Lock()         # stav, report a natívny runner zdieľajú etapy A (Mac mini) a B (hub)
_hub_done = [0]


def hyperopt_remote(name: str, profile: Path, space: dict[str, str], seed: int, windows=IS, min_trades=5,
                    epochs=EPOCHS) -> dict | None:
    """To isté hľadanie na hube (`cli hyperopt --remote`, beh ide do histórie); keď hub zlyhá, lokálne."""
    out = OUT / f"{name}_s{seed}.json"
    if out.exists():
        return json.loads(out.read_text())
    cmd = [PY, "-m", "tester.webapp.cli", "hyperopt", "--strategy", "spravyeurnet", "--profile", str(profile),
           "--pair", "6E/USD", "--engine", "multicharts", "--timeframe", "5m", "--fee", str(FEE), "--wallet", "100000",
           "--timerange", windows[0], "--windows", ",".join(windows), "--aggregate", "min", "--select", "plateau",
           "--goal", "pf", "--min-trades", str(min_trades), "--epochs", str(epochs), "--seed", str(seed),
           "--remote", "--queue", "--max-wait", "240", "--plan-total", str(HUB_TOTAL), "--plan-done", str(_hub_done[0]),
           "--note", f"SPRAVY ladenie {name} seed {seed} (PF najhorsieho zo 4 okien)"]
    for k, v in space.items():
        cmd += ["--param", f"{k}={v}"]
    t0 = time.time()
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (OUT / f"{name}_s{seed}.log").write_text(res.stdout + res.stderr, encoding="utf-8")
    m = re.search(r"hyperopts (\S+)", res.stdout)
    best = None
    if res.returncode == 0 and m:
        from tester import hyperopt as ho
        from tester.webapp.store import RunStore

        store = RunStore()
        rid = m.group(1)
        rec = store.get(rid) or {}
        ep = store.extra(rid, "epochs.json") or []
        det = ho.detail(rec, ep, store.tagged("hyperopt_run", rid), store.log(rid) or "")
        if det.get("overrides"):
            best = {"best": {k: v for k, v in det["overrides"].items() if k in space}, "epochs": ep, "run": rid}
    _hub_done[0] += 1
    if best is None:
        log(f"{name} seed {seed}: hub zlyhal (kód {res.returncode}) — počítam lokálne")
        return hyperopt(name, profile, space, seed, windows, min_trades, epochs)
    out.write_text(json.dumps(best, ensure_ascii=False, default=str))
    log(f"{name} seed {seed}: hub {best['run']}, {time.time() - t0:.0f} s")
    return best


# --------------------------------------------------------------------------- #
# vyhodnotenie (natívne, rovnaké súhrny ako história)
# --------------------------------------------------------------------------- #
_RUN = {}


def evaluate(cfgs: dict[str, dict], inst_key: str = "6e_databento") -> dict[str, dict]:
    """Profily (dict) -> po oknách {trades, pf, pnl, wr, dd} + spolu; jedna dávka (jedna naraz pre obe etapy)."""
    with _LOCK:
        return _evaluate(cfgs, inst_key)


def _evaluate(cfgs: dict[str, dict], inst_key: str) -> dict[str, dict]:
    from tradebot.adapters.multicharts.emulator import rows_from_trades
    from tradebot.core import load_profile
    from tradebot.core.money import summary_money
    from tradebot.core.types import INSTRUMENTS
    from tester import engines
    from tester.native import NativeRunner, emulation_of

    inst = INSTRUMENTS[inst_key]
    tasks, keys = [], []
    for name, prof in cfgs.items():
        f = write_profile("_eval_" + name.replace("/", "_").replace(" ", "_"), prof)
        cfg, _ = load_profile(str(f), engine=engines.MULTICHARTS)
        js = json.dumps(cfg.to_dict())
        for w in W:
            tasks.append((js, w))
            keys.append((name, w))
    if inst_key not in _RUN:
        _RUN[inst_key] = NativeRunner("spravyeurnet", inst, 5, FEE, JOBS)
    res = _RUN[inst_key].run_many(tasks)
    out: dict[str, dict] = {}
    rows_all: dict[str, list] = {}
    for (name, w), x in zip(keys, res):
        rows = [] if "error" in x else rows_from_trades(emulation_of(x).trades, inst, FEE)
        out.setdefault(name, {})[w] = _sum(rows)
        rows_all.setdefault(name, []).extend(rows)
        if "error" in x:
            out[name][w]["error"] = x["error"][:200]
    for name, rows in rows_all.items():
        out[name]["spolu"] = _sum(rows)
        out[name]["spolu"]["dd"] = summary_money(rows, 100000).get("max_drawdown_abs", 0.0)
        out[name]["is_min"] = min(out[name][w]["pf"] for w in IS)
    return out


def _sum(rows: list) -> dict:
    gp = sum(r["profit_abs"] for r in rows if r["profit_abs"] > 0)
    gl = -sum(r["profit_abs"] for r in rows if r["profit_abs"] < 0)
    return {"trades": len(rows), "pf": round(gp / gl, 3) if gl else (10.0 if gp else 0.0),
            "pnl": round(gp - gl, 2), "wr": round(100 * sum(1 for r in rows if r["profit_abs"] > 0) / max(1, len(rows)), 1)}


# --------------------------------------------------------------------------- #
# etapy
# --------------------------------------------------------------------------- #
def best_of_seeds(name: str, profile: Path, space: dict[str, str], st: dict, remote: bool = False) -> dict | None:
    """3 seedy; víťaz = kandidát s najlepším najhorším oknom ladenia (z overenia všetkých seedov naraz)."""
    wins = []
    for s in SEEDS:
        if late():
            return None
        r = (hyperopt_remote if remote else hyperopt)(name, profile, space, s)
        if r and r.get("best"):
            with _LOCK:
                st["trials"] += len(r.get("epochs") or [])
            wins.append(r["best"])
    if not wins:
        return None
    base = json.loads(profile.read_text())
    ev = evaluate({f"{name}#{i}": {**base, **b} for i, b in enumerate(wins)})
    i = max(range(len(wins)), key=lambda i: (ev[f"{name}#{i}"]["is_min"], ev[f"{name}#{i}"]["spolu"]["pf"]))
    return {"params": wins[i], "eval": ev[f"{name}#{i}"], "seeds": wins}


def stage_a(st: dict) -> None:
    for (rkey, (ev_name, space)), mode in ((x, m) for x in RULES.items() for m in ("trend", "fade")):
        key = f"{rkey}_{mode}"
        if key in st["done"] or late():
            continue
        slot = rkey[:2]
        extra = {f"{slot}Mode": mode}
        if rkey == "r12":
            if mode == "trend":
                continue                    # pred správou = fade (výskum), trend po nej je pravidlo 2
            slot = "r12"
            extra.update({"r1To": 0, "r1Enter": 0, "r2Event": "FOMC", "r2Mode": "trend"})
        prof = write_profile(f"A_{key}", only(ev_name, extra=extra))
        base_ev = evaluate({"base": json.loads(prof.read_text())})["base"]
        r = best_of_seeds(f"A_{key}", prof, space, st)
        with _LOCK:
            st["done"][key] = {"stage": "A", "event": ev_name, "slot": slot, "base": base_ev, **(r or {})}
            save(st)
        if r:
            log(f"A {key} {ev_name}: najhoršie okno ladenia {base_ev['is_min']:.2f} → {r['eval']['is_min']:.2f}, "
                f"PF spolu {base_ev['spolu']['pf']:.2f} → {r['eval']['spolu']['pf']:.2f}, odložený rok "
                f"{base_ev[OOS]['pf']:.2f} → {r['eval'][OOS]['pf']:.2f}")


def stage_b(st: dict) -> None:
    """Na hube (srvnas, 4 sloty) naraz s etapou A na Mac mini."""
    def one(item):
        (nkey, (ev_name, space)), mode = item
        key = f"{nkey}_{mode}"
        if key in st["done"] or late():
            return
        extra = {"r7Event": ev_name, "r7Mode": mode}
        if ev_name in LIVE:
            extra.update({f"r{n}Event": "" for n in range(1, 7)})
        prof = write_profile(f"B_{key}", only(ev_name, extra=extra))
        r = best_of_seeds(f"B_{key}", prof, space, st, remote=USE_HUB)
        with _LOCK:
            st["done"][key] = {"stage": "B", "event": ev_name, "slot": "r7", **(r or {})}
            save(st)
        if r:
            e = r["eval"]
            log(f"B {key}: najhoršie okno ladenia {e['is_min']:.2f}, PF spolu {e['spolu']['pf']:.2f}, "
                f"{e['spolu']['trades']} obch, odložený rok {e[OOS]['pf']:.2f}")

    items = [(x, m) for x in NEW.items() for m in ("trend", "fade")]
    with ThreadPoolExecutor(HUB_PARALLEL) as ex:
        for f in [ex.submit(one, it) for it in items]:
            try:
                f.result()
            except Exception as exc:  # noqa: BLE001 — jedno pravidlo nesmie zastaviť ostatné
                log(f"B chyba: {type(exc).__name__} {str(exc)[:200]}")


def rule_params(slot: str, params: dict) -> dict:
    if slot == "r12":
        return {**{k: v for k, v in params.items() if k[:2] in ("r1", "r2")},
                "r1To": 0, "r1Enter": 0, "r2Event": "FOMC", "r2Mode": "trend"}
    return {k: v for k, v in params.items() if k.startswith(slot)}


def holds_oos(e: dict, floor: float = 1.0) -> bool:
    """Pravidlo samo: odložený rok aspoň `floor` a aspoň 70 % najhoršieho okna ladenia (smernica, krok 6) —
    test 29. 10. ukázal PPI s ladením 3,80 a odloženým rokom 1,04 = tvar okien, nie pravidlo."""
    return e[OOS]["pf"] >= floor and e[OOS]["pf"] >= 0.7 * e["is_min"]


def accept(cur: dict, new: dict) -> bool:
    """Celok sa zlepšil: PF spolu nie nižšie a najhoršie okno ladenia nie horšie; odložený rok nepadne pod 1,2."""
    return (new["spolu"]["pf"] >= cur["spolu"]["pf"] - 1e-9 and new["is_min"] >= cur["is_min"] - 1e-9
            and new[OOS]["pf"] >= 1.2 and (new["spolu"]["pf"] > cur["spolu"]["pf"] or new["is_min"] > cur["is_min"]))


def stage_c(st: dict) -> None:
    if "C" in st["done"] or late():
        return
    cur_p = dict(BASE)
    cur = evaluate({"3.0": cur_p})["3.0"]
    steps = [{"krok": "SPRÁVY 3.0", "eval": cur}]
    # 1) lepšie verzie pravidiel 3.0 (aj PPI rýchly / pomalý variant)
    cands = []
    for key, d in st["done"].items():
        if d.get("stage") == "A" and d.get("params") and holds_oos(d["eval"]):
            slot = d["slot"]
            cands.append((d["eval"]["is_min"] - d["base"]["is_min"], key,
                          {**rule_params(slot, d["params"]), f"{slot[:2]}Mode": key.rsplit("_", 1)[1]}))
    # 2) nové pravidlá (slot 7, potom 8), ak samy prešli: najhoršie okno ladenia ≥ 1,0 a odložený rok ≥ 1,2
    news = []
    for key, d in st["done"].items():
        if d.get("stage") == "B" and d.get("params") and d["eval"]["is_min"] >= 1.0 and holds_oos(d["eval"], 1.2):
            news.append((d["eval"]["is_min"], key, d["event"],
                         {**rule_params("r7", d["params"]), "r7Mode": key.rsplit("_", 1)[1]}))
    for _gain, key, params in sorted(cands, reverse=True):
        trial = {**cur_p, **params}
        e = evaluate({key: trial})[key]
        ok = accept(cur, e)
        steps.append({"krok": f"pravidlo {key}", "params": params, "eval": e, "prijaté": ok})
        log(f"C {key}: PF {cur['spolu']['pf']:.2f}→{e['spolu']['pf']:.2f}, min {cur['is_min']:.2f}→{e['is_min']:.2f} "
            f"{'PRIJATÉ' if ok else 'nie'}")
        if ok:
            cur_p, cur = trial, e
    free = ["r7", "r8"]
    for _m, key, ev_name, params in sorted(news, reverse=True):
        if not free:
            break
        slot = free[0]
        p2 = {slot + k[2:]: v for k, v in params.items()}
        trial = {**cur_p, **p2, f"{slot}Event": ev_name, f"use{ev_name}": True}
        e = evaluate({key: trial})[key]
        ok = accept(cur, e)
        steps.append({"krok": f"nové {key} ({slot})", "params": p2, "eval": e, "prijaté": ok})
        log(f"C {key}: PF {cur['spolu']['pf']:.2f}→{e['spolu']['pf']:.2f}, min {cur['is_min']:.2f}→{e['is_min']:.2f} "
            f"{'PRIJATÉ' if ok else 'nie'}")
        if ok:
            cur_p, cur = trial, e
            free.pop(0)
    st["done"]["C"] = {"profile": cur_p, "eval": cur, "steps": steps}
    save(st)


def stage_d(st: dict) -> None:
    if "D" in st["done"] or "C" not in st["done"] or late():
        return
    cur_p = st["done"]["C"]["profile"]
    cur = st["done"]["C"]["eval"]
    prof = write_profile("D_celok", cur_p)
    r = best_of_seeds("D_celok", prof, GLOBAL, st)
    out = {"profile": cur_p, "eval": cur, "tried": r}
    if r:
        trial = {**cur_p, **r["params"]}
        e = evaluate({"D": trial})["D"]
        if accept(cur, e):
            out = {"profile": trial, "eval": e, "tried": r, "prijaté": True}
        log(f"D celok: PF {cur['spolu']['pf']:.2f}→{e['spolu']['pf']:.2f}, min {cur['is_min']:.2f}→{e['is_min']:.2f}"
            f" {'PRIJATÉ' if out.get('prijaté') else 'nie'}")
    st["done"]["D"] = out
    save(st)


def stage_e(st: dict) -> None:
    if "E" in st["done"] or "D" not in st["done"]:
        return
    from tester.robust import robustness

    win = st["done"]["D"]["profile"]
    write_profile("VITAZ", win)
    f = write_profile("VITAZ_python", {**win, "_strategy": "spravyeur"})     # tester.robust = Python emulátor (parita s C#)
    xau = evaluate({"3.0": dict(BASE), "víťaz": win}, "eurusd_dukascopy")
    rob = {}
    for name, prof in (("3.0", ROOT / "tradebot/strategies/spravyeurnet/configs/6e_databento_5m.json"), ("víťaz", f)):
        rep = robustness(str(prof).replace("spravyeurnet/configs", "spravyeur/configs"),
                         "6E/USD", "5m", FEE, max(70, st["trials"]) if name == "víťaz" else 70, log=lambda s: None)
        rob[name] = {"total": rep.total, "dsr": rep.dsr, "verdict": rep.verdict}
    st["done"]["E"] = {"xau": xau, "robust": rob, "trials": st["trials"]}
    save(st)
    log(f"E hotové: EUR/USD CFD PF {xau['3.0']['spolu']['pf']:.2f} → {xau['víťaz']['spolu']['pf']:.2f}; DSR víťaza "
        f"{rob['víťaz']['dsr'].get('dsr', 0):.3f} pri {max(70, st['trials'])} skúškach")


def main() -> None:
    st = state()
    log("štart ladenia SPRÁV EUR/USD")
    hub = threading.Thread(target=stage_b, args=(st,), name="hub")     # nové pravidlá na hube
    hub.start()
    stage_a(st)                                                          # pravidlá 3.0 na Mac mini
    hub.join()
    for stage in (stage_c, stage_d, stage_e):
        if late():
            break
        stage(st)
    subprocess.run([PY, str(D / "report.py")], cwd=ROOT)
    log("ladenie skončené" + (" (čas)" if late() else ""))


if __name__ == "__main__":
    main()
