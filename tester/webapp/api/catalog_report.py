"""Hodnotenie stratégie s profilom (`/api/catalog/{key}/report`) — okno po kliknutí na kartu
v katalógu: výkon, analytika, posudok, nastavenie, behy a dokumenty na jednom mieste.

Nič sa tu nepočíta nanovo z dát trhu — všetko sa skladá z toho, čo už je:

- **výkon** z behov profilu na piatich referenčných oknách (`REFERENCE_WINDOWS`), prednostne
  z jedného `cli checkup` (`settings.checkup.id`); z `series.equity` behov (`[čas, zisk
  obchodu %, súčet]`) sa poskladá spojitá krivka a z nej čísla po obchodoch, rokoch a mesiacoch.
  Okná sa prekrývajú (3. a 4. o mesiac) — obchod, ktorý už bol v predošlom okne, sa vynechá;
- **analytika a posudok** z `tradebot/strategies/<key>/docs/ANALYTIKA.md` (píše ho `cli checkup`),
  rozdelená po sekciách `##`, aby ich stránka mohla ukázať oddelene;
- **nastavenie** = parametre profilu, ktoré sa líšia od Pine defaultov;
- **dokumenty** = ostatné `.md` v `docs/` stratégie a merania z `docs/merania/`, ktoré ju menujú.
"""

from __future__ import annotations

import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException

from tradebot.core.paths import MERANIA_DIR
from tradebot.strategies import STRATEGIES, canonical_key

from ...checkup import DOC_NAME, doc_path, extract_posudok
from ...hyperopt import REFERENCE_WINDOWS
from ..repo_profiles import default_params, profile_info
from ..store import strategy_of
from .catalog import _metrics, _profile_stem, explainer_lead, payoff_ratio, profile_group, realized_r, title_metrics

#: Krivka do okna: dosť bodov na tvar aj na roky, nie celý zoznam obchodov.
CURVE_POINTS = 400
#: Toľko posledných behov profilu ukáže tabuľka behov.
RECENT_RUNS = 15

_MEASURED = re.compile(r"^Zmerané .+$", re.M)
_DOC_PROFILE = re.compile(r"profil `([^`]+)`")
_SECTION = re.compile(r"^## (.+)$", re.M)


# --------------------------------------------------------------------------- #
# ANALYTIKA.md
# --------------------------------------------------------------------------- #

def _bullets(markdown: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^- (.+)$", markdown, re.M)]


def parse_analytika(text: str) -> dict[str, Any]:
    """Sekcie generovaného dokumentu `cli checkup`; posudok zvlášť (bez výzvy a značiek)."""
    if not text.strip():
        return {"exists": False}
    measured = (m.group(0) if (m := _MEASURED.search(text)) else "")
    profile = _profile_stem(m.group(1)) if (m := _DOC_PROFILE.search(measured)) else ""
    posudok, _stamp = extract_posudok(text)
    heads = list(_SECTION.finditer(text))
    sections = []
    for i, h in enumerate(heads):
        body = text[h.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)].strip()
        title = h.group(1).strip()
        if title.startswith("Posudok"):
            continue                       # posudok ide zvlášť, výzva a značky na stránku nepatria
        sections.append({"title": title, "markdown": body})
    by_title = {s["title"]: s["markdown"] for s in sections}
    char = by_title.get("Charakter", "")
    character = re.sub(r"\*\*", "", char.splitlines()[0]).strip() if char else ""
    return {
        "exists": True, "measured": measured, "profile": profile, "character": character,
        "good": _bullets(by_title.get("V čom je dobrá", "")),
        "bad": _bullets(by_title.get("Kde má chyby", "")),
        "sections": [s for s in sections if s["title"] not in ("V čom je dobrá", "Kde má chyby")],
        "posudok": posudok,
    }


# --------------------------------------------------------------------------- #
# výkon z behov piatich okien
# --------------------------------------------------------------------------- #

def _profile_runs(records: list[dict[str, Any]], key: str, profile: str) -> list[dict[str, Any]]:
    stem = profile.lower()
    return [r for r in records if strategy_of(r) == key
            and _profile_stem((r.get("settings") or {}).get("profile")) == stem]


def pick_windows(runs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    """Behy piatich okien: najúplnejší `cli checkup` (pri zhode najnovší), inak najnovší beh
    každého okna na tom istom páre a TF ako najnovší beh vôbec. Vráti (behy podľa okien, id checkupu)."""
    done = [r for r in runs if r.get("status") == "done"
            and (r.get("settings") or {}).get("timerange") in REFERENCE_WINDOWS]
    if not done:
        return [], None
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for r in sorted(done, key=lambda x: x.get("id") or ""):          # novší prepíše starší
        cid = ((r.get("settings") or {}).get("checkup") or {}).get("id")
        if cid:
            groups.setdefault(cid, {})[r["settings"]["timerange"]] = r
    if groups:
        cid, win = max(groups.items(), key=lambda kv: (len(kv[1]), max(x["id"] for x in kv[1].values())))
        return [win[w] for w in REFERENCE_WINDOWS if w in win], cid
    newest = max(done, key=lambda x: x.get("id") or "")
    market = lambda r: ((r.get("settings") or {}).get("pair"), (r.get("settings") or {}).get("timeframe"))  # noqa: E731
    latest: dict[str, dict[str, Any]] = {}
    for r in sorted(done, key=lambda x: x.get("id") or ""):
        if market(r) == market(newest):
            latest[r["settings"]["timerange"]] = r
    return [latest[w] for w in REFERENCE_WINDOWS if w in latest], None


def chain_trades(full_runs: list[dict[str, Any] | None]) -> list[tuple[str, float]]:
    """Obchody (čas výstupu, zisk %) z behov po sebe; čo už bolo v predošlom okne, vypadne."""
    out: list[tuple[str, float]] = []
    for rec in full_runs:
        for p in ((rec or {}).get("series") or {}).get("equity") or []:
            if not (isinstance(p, (list, tuple)) and len(p) > 1 and isinstance(p[1], (int, float))):
                continue
            t = str(p[0])
            if out and t <= out[-1][0]:
                continue                   # prekryv okien — obchod už je započítaný
            out.append((t, float(p[1])))
    return out


def _max_streak(pnls: list[float], sign: int) -> int:
    best = cur = 0
    for v in pnls:
        cur = cur + 1 if (v > 0 if sign > 0 else v < 0) else 0
        best = max(best, cur)
    return best


def trade_stats(trades: list[tuple[str, float]]) -> dict[str, Any]:
    """Čísla zo spojených obchodov: zisk, PF, RR, WR, očakávaná hodnota, DD krivky, série."""
    pnls = [v for _, v in trades]
    if not pnls:
        return {}
    wins, losses = [v for v in pnls if v > 0], [v for v in pnls if v < 0]
    cum = peak = dd = 0.0
    for v in pnls:
        cum += v
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    gross_w, gross_l = sum(wins), -sum(losses)
    first, last = datetime.fromisoformat(trades[0][0]), datetime.fromisoformat(trades[-1][0])
    years = max((last - first).days / 365.25, 1 / 12)
    return {
        "trades": len(pnls), "pnl_pct": round(cum, 2),
        "profit_factor": round(gross_w / gross_l, 3) if gross_l else None,
        "winrate": round(len(wins) / len(pnls) * 100, 1),
        "rr": round((gross_w / len(wins)) / (gross_l / len(losses)), 3) if wins and losses else None,
        "avg_win": round(gross_w / len(wins), 3) if wins else None,
        "avg_loss": round(-gross_l / len(losses), 3) if losses else None,
        "expectancy": round(cum / len(pnls), 4),
        "max_dd_pct": round(dd, 2),
        "recovery": round(cum / dd, 2) if dd else None,
        "trades_year": round(len(pnls) / years, 1),
        "pnl_year": round(cum / years, 2),
        "best": round(max(pnls), 3), "worst": round(min(pnls), 3),
        "win_streak": _max_streak(pnls, 1), "loss_streak": _max_streak(pnls, -1),
        "first": trades[0][0], "last": trades[-1][0],
    }


def by_period(trades: list[tuple[str, float]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    """Kalendárne roky (obchody, zisk, PF, WR, DD) a mesiace (`{rok: {mesiac: zisk}}`)."""
    years: dict[str, list[float]] = {}
    months: dict[str, dict[str, float]] = {}
    for t, v in trades:
        years.setdefault(t[:4], []).append(v)
        m = months.setdefault(t[:4], {})
        m[t[5:7]] = round(m.get(t[5:7], 0.0) + v, 3)
    rows = []
    for y, pnls in sorted(years.items()):
        s = trade_stats([(f"{y}-01-01T00:00:00", v) for v in pnls])
        rows.append({"year": y, **{k: s.get(k) for k in ("trades", "pnl_pct", "profit_factor", "winrate",
                                                          "rr", "max_dd_pct")}})
    return rows, months


def curve(trades: list[tuple[str, float]], points: int = CURVE_POINTS) -> list[list[Any]]:
    """Kumulatívny zisk `[čas, súčet %]`, preriedený; začína nulou pred prvým obchodom."""
    cum, out = 0.0, []
    for t, v in trades:
        cum += v
        out.append([t[:16], round(cum, 3)])
    if len(out) > points:
        out = [out[round(i * (len(out) - 1) / (points - 1))] for i in range(points)]
    return ([[trades[0][0][:16], 0.0]] if trades else []) + out


def window_trades(windows: list[dict[str, Any]], load_trades) -> list[dict[str, Any]]:
    """Obchody referenčných okien po sebe; obchod z prekryvu dvoch okien (rovnaký vstup) len raz."""
    seen, out = set(), []
    for r in windows:
        for t in (load_trades(r["id"]) if load_trades else []) or []:
            k = (t.get("open_date"), t.get("open_rate"), t.get("is_short"))
            if k not in seen:
                seen.add(k)
                out.append(t)
    return out


def performance(runs: list[dict[str, Any]], load_run: Callable[[str], dict[str, Any] | None],
                load_trades=None) -> dict[str, Any]:
    windows, checkup_id = pick_windows(runs)
    full = [load_run(r["id"]) for r in windows]
    rows = []
    for r in windows:
        m = _metrics(r)
        res = r.get("result") or {}
        m["exits"] = res.get("exits")
        m["checkup"] = ((r.get("settings") or {}).get("checkup") or {}).get("id")
        rows.append(m)
    trades = chain_trades(full)
    years, months = by_period(trades)
    head = (windows[-1].get("settings") or {}) if windows else {}
    return {
        "checkup_id": checkup_id, "windows": rows, "expected_windows": list(REFERENCE_WINDOWS),
        "positive_windows": sum(1 for r in rows if (r.get("pnl_pct") or 0) > 0),
        "pair": head.get("pair"), "timeframe": head.get("timeframe"), "engine": head.get("engine"),
        "fee": head.get("fee"), "wallet": head.get("wallet"),
        "stats": {**trade_stats(trades), **realized_r(window_trades(windows, load_trades))},
        "years": years, "months": months, "curve": curve(trades),
    }


def best_single(runs: list[dict[str, Any]], load_run, load_trades=None) -> dict[str, Any] | None:
    """Keď okná chýbajú: najnovší hotový beh profilu s krivkou a jeho číslami."""
    done = sorted((r for r in runs if r.get("status") == "done"), key=lambda r: r.get("id") or "", reverse=True)
    if not done:
        return None
    rec = load_run(done[0]["id"])
    trades = chain_trades([rec])
    years, months = by_period(trades)
    r = realized_r(load_trades(done[0]["id"])) if load_trades else {}
    return {**_metrics(done[0]), "stats": {**trade_stats(trades), **r}, "years": years, "months": months,
            "curve": curve(trades)}


# --------------------------------------------------------------------------- #
# nastavenie profilu, dokumenty
# --------------------------------------------------------------------------- #

def profile_params(key: str, name: str) -> list[dict[str, Any]]:
    """Parametre profilu, ktoré sa líšia od Pine defaultov stratégie (s popisom z `params.py`)."""
    spec = STRATEGIES[key]
    try:
        values, _inst = default_params(name, key)
    except Exception:              # noqa: BLE001 — poškodený profil nesmie zhodiť celé okno
        return []
    defaults = spec.config_cls().to_dict()
    out = []
    for k, v in values.items():
        if k.startswith("_") or defaults.get(k) == v:
            continue
        meta = spec.param_meta.get(k) or {}
        out.append({"name": k, "value": v, "default": defaults.get(k), "title": meta.get("title") or "",
                    "group": meta.get("group") or ""})
    return out


#: Texty dokumentov podľa `(mtime, veľkosť)` súboru. Okno hodnotenia hľadá kľúč stratégie vo všetkých
#: meraniach (`docs/merania/`) a čítalo ich z disku pri každom otvorení; teraz sa súbor číta znova, len
#: keď sa zmenil (zvyšok auditu M-WEB-4).
_DOC_CACHE: dict[str, tuple[tuple[int, int], str]] = {}
_DOC_LOCK = threading.Lock()


def _doc_text(path: Path) -> str:
    """Text dokumentu z cache, alebo zo súboru, keď sa zmenil. Chýbajúci súbor = `OSError` ako pri čítaní."""
    st = path.stat()
    podpis = (st.st_mtime_ns, st.st_size)
    kluc = str(path)
    with _DOC_LOCK:
        hit = _DOC_CACHE.get(kluc)
        if hit is not None and hit[0] == podpis:
            return hit[1]
    text = path.read_text(encoding="utf-8")
    with _DOC_LOCK:
        _DOC_CACHE[kluc] = (podpis, text)
    return text


def _doc_title(path: Path) -> str:
    try:
        for line in _doc_text(path).splitlines()[:5]:
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return path.stem.replace("_", " ")


def strategy_docs(key: str) -> list[dict[str, str]]:
    """Ostatné dokumenty stratégie a merania, ktoré ju menujú (`--strategy kľúč` alebo `` `kľúč` ``)."""
    spec = STRATEGIES[key]
    out = []
    folder = spec.profile_dir.parent / "docs"
    for p in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
        if p.name in (DOC_NAME, "VYSVETLIVKA.md"):
            continue
        out.append({"id": f"s/{p.relative_to(folder).as_posix()}", "title": _doc_title(p), "kind": "stratégia"})
    pat = re.compile(rf"(--strategy {re.escape(key)}\b|`{re.escape(key)}`)")
    for p in sorted(MERANIA_DIR.glob("*.md")) if MERANIA_DIR.is_dir() else []:
        try:
            if pat.search(_doc_text(p)):
                out.append({"id": f"m/{p.name}", "title": _doc_title(p), "kind": "meranie"})
        except OSError:
            continue
    return out


def read_doc(key: str, doc_id: str) -> str:
    """Text dokumentu z `strategy_docs` — iné cesty (mimo zoznamu) sa neotvoria."""
    if doc_id not in {d["id"] for d in strategy_docs(key)}:
        raise HTTPException(404, f"dokument {doc_id!r} k stratégii {key!r} nie je")
    kind, rel = doc_id.split("/", 1)
    base = (STRATEGIES[key].profile_dir.parent / "docs") if kind == "s" else MERANIA_DIR
    return (base / rel).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# celé hodnotenie
# --------------------------------------------------------------------------- #

def resolve_key(key: str) -> str:
    k = canonical_key(key) or ""
    if k not in STRATEGIES:
        raise HTTPException(404, f"neznáma stratégia {key!r}")
    return k


def report(key: str, profile: str, records: list[dict[str, Any]], load_run, load_trades=None) -> dict[str, Any]:
    """Hodnotenie stratégie `key` s profilom `profile` (prázdny = profil, na ktorom je analytika)."""
    spec = STRATEGIES[key]
    path = doc_path(key)
    analytika = parse_analytika(path.read_text(encoding="utf-8") if path.is_file() else "")
    infos = profile_info(key)
    lower = {n.lower(): n for n in infos}
    if not profile:
        profile = lower.get(analytika.get("profile") or "", "")
    name = lower.get(profile.lower(), profile)
    info = infos.get(name)
    runs = _profile_runs(records, key, name) if name else []
    perf = performance(runs, load_run, load_trades) if runs else None
    if perf and not perf["windows"]:
        perf = None
    group = profile_group(name, key) if info else ""
    all_runs = [r for r in records if strategy_of(r) == key]
    return {
        "key": key, "title": spec.title, "csharp": spec.csharp_dir is not None,
        "default_timeframe": spec.default_timeframe, "has_explainer": spec.explainer_path.is_file(),
        "lead": explainer_lead(spec.explainer()),
        "profile": {
            "name": name, "group": group, "title": info.get("title") or "", "pair": info.get("pair") or "",
            "timeframe": info.get("timeframe") or "", "created": info.get("created") or "",
            "claimed": title_metrics(info.get("title") or "") if group == "smernica" else {},
            "params": profile_params(key, name),
        } if info else None,
        "analytika": {**analytika, "matches_profile": bool(name) and analytika.get("profile") == name.lower()},
        "performance": perf,
        "single": None if perf else best_single(runs, load_run, load_trades),
        "runs": {
            "strategy_total": sum(1 for r in all_runs if r.get("status") == "done"),
            "profile_total": sum(1 for r in runs if r.get("status") == "done"),
            "recent": [{**_metrics(r), "note": r.get("note") or "", "rr": payoff_ratio(r.get("result") or {})}
                       for r in sorted(runs, key=lambda r: r.get("id") or "", reverse=True)
                       if r.get("status") == "done"][:RECENT_RUNS],
        },
        "docs": strategy_docs(key),
    }
