"""Krok 12 smernice — kontrola (používateľ 10. 11. 2026, nápad kamaráta): pre AS stratégie (horná časť webapp)
na stránke výsledkov — LEN stránka, webapp sa nemení.

* **CI90** — 90 % interval spoľahlivosti priemerného zisku obchodu (bootstrap 2 000×) z obchodov v ladení
  (do 2025-09-04) aj v odloženom roku. Edge je štatisticky istý, keď je CI90 ladenia celý nad nulou.
* **SHA-256 dát** — odtlačok 1m súboru trhu (data/tester/…, z ktorého počíta emulátor) a ročných súborov
  archívu 2021–2026. Prvé spočítanie sa uloží (dash/data_hashes.json); ďalšie ho porovná — zmena dát = výsledky
  vznikli z iných dát, než sa na ne dá odvolať.
* **Druhý model** — iný AI model (Sonnet) nezávisle prepočíta vzorku obchodov nastavenia č. 1 z 1m dát a pravidiel
  (bez kódu stratégie) a zapíše verdikt do dash/krok12_model/<kľúč>.json; tu sa len načíta.

`apply(data)` volá gldash pred zápisom stránky: stratégiám doplní `check12` a krok 12 do `steps`.
"""
from __future__ import annotations

import hashlib, json, random, sys, time
from pathlib import Path

sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import glsearch as G

REPO = Path("/Users/martin/IBS")
DASH = G.ROOT / "dash"
HASHES = DASH / "data_hashes.json"
MODEL_DIR = DASH / "krok12_model"
OOS_FROM = "2025-09-04"
NET = {"ibsentrynet": "ibsentry", "ibsentryneteod": "ibsentry", "tksnet": "tks", "tksneteod": "tks", "noanet": "noa",
       "noaneteod": "noa", "vwaporbnet": "vwaporb", "vwaporbneteod": "vwaporb", "vwapadxnet": "vwapadx",
       "vwapadxneteod": "vwapadx", "ibsentryesnet": "ibsentryes", "nyvaesnet": "nyvaes", "fibomgcnet": "fibomgc",
       "voltbreaknet": "voltbreak", "sigmamgcnet": "sigmamgc", "sigmanet": "sigma", "spravynet": "spravy"}
SYMBOL = {"mnq_databento": "MNQ_USD", "mgc_databento": "MGC_USD", "es_databento": "ES_USD", "6e_databento": "6E_USD"}


def as_keys() -> list[str]:
    top = json.loads((REPO / "tester/webapp_vyber.json").read_text())["strategies"]
    out = []
    for k in top:
        b = NET.get(k, k)
        if b not in out:
            out.append(b)
    return out


def ci90(xs: list[float], n_boot: int = 2000, seed: int = 12) -> tuple[float, float] | None:
    if len(xs) < 10:
        return None
    rnd = random.Random(seed)
    n = len(xs)
    means = sorted(sum(xs[rnd.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return round(means[int(0.05 * n_boot)], 2), round(means[int(0.95 * n_boot) - 1], 2)


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def data_files(inst_key: str) -> list[Path]:
    from tester import engines
    from tradebot.core.types import INSTRUMENTS
    files = [Path(engines.one_minute_file(INSTRUMENTS[inst_key]))]
    sym = SYMBOL.get(inst_key)
    if sym:
        files += sorted((REPO / "data/archive/tester/databento/futures").glob(f"{sym}-1m.20[2][1-6].feather"))
    return [f for f in files if f.exists()]


def hash_check(inst_key: str, base: dict, cache: dict) -> dict:
    """Odtlačky súborov trhu; prvé spočítanie sa uloží ako východisko, ďalšie sa s ním porovná."""
    if inst_key in cache:
        return cache[inst_key]
    now = time.strftime("%Y-%m-%d %H:%M")
    files = []
    changed = []
    for f in data_files(inst_key):
        rel = str(f.relative_to(REPO))
        h = _sha(f)
        old = base.get(rel)
        if old is None:
            base[rel] = {"sha256": h, "since": now}
        elif old["sha256"] != h:
            changed.append(rel)
            old.setdefault("history", []).append({"sha256": old["sha256"], "until": now})
            old["sha256"], old["since"] = h, now
        files.append({"file": rel, "sha256": h, "since": base[rel]["since"]})
    out = {"files": files, "changed": changed, "ok": not changed}
    cache[inst_key] = out
    return out


def model_review(key: str) -> dict | None:
    f = MODEL_DIR / f"{key}.json"
    try:
        return json.loads(f.read_text())
    except Exception:
        return None


def apply(data: dict) -> None:
    keys = set(as_keys())
    base = json.loads(HASHES.read_text()) if HASHES.exists() else {}
    cache: dict = {}
    for s in data["strategies"]:
        key = s["key"]
        if key not in keys or not s.get("settings"):
            continue
        rows = []
        for st in s["settings"]:
            tr = st.get("trades") or []
            ins = [t["pnl"] for t in tr if t["close"] < OOS_FROM]
            oos = [t["pnl"] for t in tr if t["close"] >= OOS_FROM]
            ci_is, ci_oos = ci90(ins), ci90(oos)
            rows.append({"id": st["id"], "label": st.get("label"), "n_is": len(ins), "n_oos": len(oos),
                         "mean_is": round(sum(ins) / len(ins), 2) if ins else None,
                         "mean_oos": round(sum(oos) / len(oos), 2) if oos else None,
                         "ci_is": ci_is, "ci_oos": ci_oos, "ci_ok": bool(ci_is and ci_is[0] > 0)})
        h = hash_check(G.instr(key)[0], base, cache)
        m = model_review(key)
        ci_ok = bool(rows) and rows[0]["ci_ok"]
        m_ok = bool(m) and m.get("verdict") == "ok"
        s["check12"] = {"ci": rows, "data": h, "model": m, "ci_ok": ci_ok, "data_ok": h["ok"], "model_ok": m_ok,
                        "date": time.strftime("%Y-%m-%d %H:%M")}
        steps = [x for x in s.get("steps", []) if x[0] != "12"]
        steps.append(["12", "kontrola (CI90 · SHA-256 · druhý model)", ci_ok and h["ok"] and m_ok])
        s["steps"] = steps
    HASHES.write_text(json.dumps(base, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    d = json.loads((DASH / "dashboard_data.json").read_text())
    apply(d)
    for s in d["strategies"]:
        c = s.get("check12")
        if c:
            r = c["ci"][0]
            print(f"{s['key']:12} CI90 IS {r['ci_is']} OOS {r['ci_oos']} · dáta {'OK' if c['data_ok'] else 'ZMENENÉ'} · model "
                  f"{(c['model'] or {}).get('verdict', '—')}")
