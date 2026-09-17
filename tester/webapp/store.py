"""Ukladanie behov — jeden adresár na beh, všetko čitateľný JSON.

    runs/<run_id>/run.json        parametre (celý efektívny config), nastavenia behu, výsledok
    runs/<run_id>/trades.json     zoznam obchodov
    runs/<run_id>/plan.json       SL/TP plán obchodov z kresieb (analytika bez grafu)
    runs/<run_id>/log.txt         skrátený log Freqtradu / emulátora
    runs/.charts/<run_id>.json.gz kresby enginu pre graf páru — lokálna cache, nie v gite

Kresby (zóny, boxy, štítky) sa k behu **neukladajú**: mali megabajt na beh, história ich
mala tisíce a repozitár narástol na jedenásť gigabajtov. Beh nesie celý config, takže graf
sa dá kedykoľvek prepočítať (`tester.webapp.replay`) — robí sa to, až keď ho niekto otvorí,
a výsledok ostane v cache. Čerstvý beh si svoje kresby do cache odloží hneď. Starý beh so
`chart.json.gz` v adresári ho používa ďalej, kým ho `cli prune` neodprace.

Z kresieb potrebuje aj analytika jednu vec — plánovaný stop a cieľ obchodu (Freqtrade ich
v riadku obchodu nemá). Tie boxy sa preto pri uložení vyberú do malého `plan.json`
a `chart()` ich vráti, keď plné kresby lokálne nie sú.

Body mriežok, matíc a overení hyperoptu sem nejdú vôbec — tie sú v `sweeps/`
(`tester.webapp.batches`), dostupné cez `tagged()` a `find()`.

Prečo súbory a nie databáza: história má ísť do gitu, aby sa dala pushovať a pullovať
medzi testermi. JSON per beh sa mergeuje bez konfliktov (každý beh je nový adresár),
diff je čitateľný a nič sa nestratí. Pri stovkách behov je prehľadanie všetkých
`run.json` otázka desiatok milisekúnd, index netreba.

`run_id` = čas + odtlačok parametrov, takže dvaja testeri s rovnakým nastavením
v rovnakej sekunde nekolidujú a z názvu adresára vidno, kedy beh vznikol.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from tradebot.core.paths import CHART_CACHE, REPO, RUNS_DIR, SWEEPS_DIR  # noqa: F401  (REPO sa reexportuje)

_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")

#: Kresby enginu — gzip, lebo ročný beh má desaťtisíce objektov (~MB v JSON) a súbor
#: sa po zápise už nikdy nemení, takže čitateľný diff nikto nepotrebuje.
CHART_FILE = "chart.json.gz"
#: Plánovaný SL/TP obchodov behu — výťah z kresieb pre analytiku (`plan_objects`).
PLAN_FILE = "plan.json"


def make_run_id(params: dict[str, Any], settings: dict[str, Any], when: datetime | None = None) -> str:
    when = when or datetime.now(timezone.utc)
    blob = json.dumps({"p": params, "s": settings}, sort_keys=True, default=str).encode()
    return f"{when:%Y%m%d-%H%M%S}-{hashlib.sha1(blob).hexdigest()[:6]}"


def _read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


#: Stratégia behov spred registry stratégií (záznamy bez `settings.strategy`).
LEGACY_STRATEGY = "ibs"


def _with_strategy(record: dict[str, Any]) -> dict[str, Any]:
    """Staré `run.json` nemajú `settings.strategy` — doplní sa len pri čítaní, disk sa nemení."""
    settings = record.get("settings")
    if isinstance(settings, dict) and not settings.get("strategy"):
        settings["strategy"] = LEGACY_STRATEGY
    return record


def strategy_of(record: dict[str, Any]) -> str:
    return ((record.get("settings") or {}).get("strategy")) or LEGACY_STRATEGY


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def plan_objects(chart: dict[str, Any] | None, trades: Iterable[dict[str, Any]],
                 strategy: str = "ibs", engine: str = "") -> list[dict[str, Any]]:
    """SL/TP boxy, ktoré analytika spáruje s obchodmi behu — nič viac z kresieb.

    Párovanie je to isté ako v `tester.analytics.enrich` (čas signálu z `enter_tag`, pri
    MultiCharts úroveň stopu), takže `enrich` nad výťahom dá presne to, čo nad celými
    kresbami. Box, ku ktorému nepatrí žiadny obchod, sa nevyberie.
    """
    from tradebot.strategies import get_spec

    from .. import analytics as an

    try:
        spec = get_spec(strategy)
    except KeyError:
        return []
    sl_kind, tp_kind = getattr(spec, "sl_kind", ""), getattr(spec, "tp_kind", "")
    if not chart or not sl_kind:
        return []
    sl_boxes = an._boxes(chart, sl_kind)
    tp_boxes = an._boxes(chart, tp_kind) if tp_kind else {}
    keep: set[int] = set()
    for t in trades:
        x = an.signal_time_ms(t.get("enter_tag"))
        if x is not None and x in sl_boxes:
            keep.add(x)
            continue
        stop, _ = an.plan_from_record(t, engine)
        if stop is None:
            continue
        otvorenie = an._dt(t.get("open_date"))
        x = an._box_by_stop(sl_boxes, int(otvorenie.timestamp() * 1000) if otvorenie else None,
                            stop, bool(t.get("is_short")))
        if x is not None:
            keep.add(x)
    out: list[dict[str, Any]] = []
    for x in sorted(keep):
        out.append({"t": "box", "k": sl_kind, "x1": x, "y1": sl_boxes[x][0], "y2": sl_boxes[x][1]})
        if x in tp_boxes:
            out.append({"t": "box", "k": tp_kind, "x1": x, "y1": tp_boxes[x][0], "y2": tp_boxes[x][1]})
    return out


def read_chart_file(path: Path) -> dict[str, Any] | None:
    """Kresby z `.json.gz` (alebo `None`, keď súbor nie je / je rozbitý)."""
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, EOFError, json.JSONDecodeError):
        return None


def write_plan(path: Path, objects: list[dict[str, Any]]) -> None:
    """`plan.json` kompaktne — riadok na obchod by bol v gite zbytočne dlhý."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"version": 1, "objects": objects}, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")


class RunStore:
    def __init__(self, root: Path | None = None, chart_cache: Path | None = None,
                 batches: Any = None) -> None:
        # RUNS_DIR sa čita az tu, aby sa dal v testoch a nastrojoch prepnut
        self.root = Path(root or RUNS_DIR)
        self.root.mkdir(parents=True, exist_ok=True)
        # Cache kresieb a celky mriežok patria k tomu istému skladu: v teste s dočasným
        # adresárom nesmú siahnuť na skutočnú históriu repozitára.
        # Porovnáva sa so skutočnou cestou z `paths`, nie s touto globálnou: test, ktorý si
        # `RUNS_DIR` modulu prepne na dočasný adresár, nesmie písať do `tester/sweeps/`.
        from tradebot.core import paths as _paths

        default = self.root.resolve() == Path(_paths.RUNS_DIR).resolve()
        self.chart_cache = Path(chart_cache) if chart_cache else (
            Path(CHART_CACHE) if default else self.root / Path(CHART_CACHE).name)
        if batches is None:
            from .batches import BatchStore

            batches = BatchStore(Path(SWEEPS_DIR) if default else self.root / ".sweeps")
        self.batches = batches
        # Načítané `run.json` podľa (mtime, veľkosť): pri tisíckach behov trvá čítanie
        # všetkých súborov sekundy a robilo sa pri KAŽDOM dopyte (história, ponuky
        # mriežok, nastavení…). Disk je stále pravda - čo sa zmenilo alebo pribudlo
        # (aj cez git pull), sa prečíta nanovo, čo zmizlo, vypadne.
        self._cache: dict[str, tuple[tuple[int, int], dict[str, Any]]] = {}

    def _cached(self, run_id: str, path: Path) -> dict[str, Any] | None:
        """Záznam behu z cache, alebo zo súboru, keď sa zmenil. `None` = niet/rozbitý."""
        try:
            st = path.stat()
        except OSError:
            self._cache.pop(run_id, None)
            return None
        podpis = (st.st_mtime_ns, st.st_size)
        hit = self._cache.get(run_id)
        if hit is not None and hit[0] == podpis:
            return hit[1]
        try:
            rec = _with_strategy(_read_json(path))
        except (OSError, json.JSONDecodeError):
            self._cache.pop(run_id, None)
            return None  # rozbitý súbor nemá zhodiť celý zoznam
        self._cache[run_id] = (podpis, rec)
        return rec

    # -- zápis -------------------------------------------------------------- #

    def save(self, record: dict[str, Any], trades: list[dict[str, Any]] | None = None,
             log: str | None = None, chart_path: Path | str | None = None) -> Path:
        """`chart_path` je hotový súbor kresieb od stratégie. Do adresára behu (a teda do
        gitu) nejde: vyberie sa z neho `plan.json` a súbor sa presunie do lokálnej cache
        grafov — tam je, kým ho niekto neotvorí, a nabudúce sa dá prepočítať."""
        run_id = record["id"]
        if not _ID_RE.match(run_id):
            raise ValueError(f"neplatné run_id: {run_id!r}")
        d = self.root / run_id
        _write_json(d / "run.json", record)
        if trades is not None:
            _write_json(d / "trades.json", trades)
        if log is not None:
            (d / "log.txt").write_text(log, encoding="utf-8", newline="\n")
        if chart_path is not None and Path(chart_path).exists():
            nastavenia = record.get("settings") or {}
            if trades:
                write_plan(d / PLAN_FILE, plan_objects(read_chart_file(Path(chart_path)), trades,
                                                       strategy_of(record), nastavenia.get("engine") or ""))
            self.put_chart(run_id, chart_path, {"source": "run", "match": True,
                                                "created": record.get("finished")})
        return d

    def put_chart(self, run_id: str, chart_path: Path | str, check: dict[str, Any]) -> Path:
        """Presunie hotové kresby do cache grafov a zapíše k nim výsledok kontroly."""
        self.chart_cache.mkdir(parents=True, exist_ok=True)
        ciel = self.chart_cache / f"{run_id}.json.gz"
        shutil.move(str(chart_path), str(ciel))
        _write_json(self.chart_cache / f"{run_id}.check.json", check)
        return ciel

    def save_extra(self, run_id: str, name: str, data: Any) -> Path:
        """Ďalší JSON k behu (`epochs.json` hyperoptu) — do zoznamu histórie by nesadol."""
        if not _ID_RE.match(run_id) or "/" in name or "\\" in name:
            raise ValueError(f"neplatné run_id/meno: {run_id!r}/{name!r}")
        cesta = self.root / run_id / name
        _write_json(cesta, data)
        return cesta

    def extra(self, run_id: str, name: str) -> Any | None:
        """Prečíta `save_extra`, alebo `None`, keď taký súbor nie je."""
        if not _ID_RE.match(run_id) or "/" in name or "\\" in name:
            return None
        cesta = self.root / run_id / name
        return _read_json(cesta) if cesta.exists() else None

    def delete(self, run_id: str) -> bool:
        d = self.root / run_id
        if not _ID_RE.match(run_id) or not d.is_dir():
            return False
        shutil.rmtree(d)
        for p in (self.chart_cache / f"{run_id}.json.gz", self.chart_cache / f"{run_id}.check.json"):
            p.unlink(missing_ok=True)
        return True

    # -- čítanie ------------------------------------------------------------ #

    def get(self, run_id: str) -> dict[str, Any] | None:
        # Plytká kópia: detail behu si do záznamu dopisuje polia (`overrides`, `has_chart`)
        # a tie do cache nepatria.
        rec = self._cached(run_id, self.root / run_id / "run.json")
        return dict(rec) if rec is not None else None

    def trades(self, run_id: str) -> list[dict[str, Any]]:
        p = self.root / run_id / "trades.json"
        if not p.exists():
            return []
        rows = _read_json(p)
        # Behy spred `point_value` v zázname: chýbajúca hodnota nie je 1, doplní sa
        # z inštrumentu páru (tradebot.core.money), inak by MNQ/forex vyšli v bodoch.
        if rows and any("point_value" not in r for r in rows):
            from tradebot.core.money import fill_point_value

            fill_point_value(rows, ((self.get(run_id) or {}).get("settings") or {}).get("pair"))
        return rows

    def log(self, run_id: str) -> str:
        p = self.root / run_id / "log.txt"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def chart_file(self, run_id: str) -> Path | None:
        """Súbor plných kresieb behu: starý `chart.json.gz` v adresári, inak cache grafov."""
        if not _ID_RE.match(str(run_id)):
            return None
        for p in (self.root / run_id / CHART_FILE, self.chart_cache / f"{run_id}.json.gz"):
            if p.exists():
                return p
        return None

    def has_chart(self, run_id: str) -> bool:
        """Sú plné kresby lokálne (bez prepočtu)?"""
        return self.chart_file(run_id) is not None

    def chart_check(self, run_id: str) -> dict[str, Any] | None:
        """Výsledok kontroly prepočítaných kresieb (`replay`), alebo `None` pri starom súbore."""
        p = self.chart_cache / f"{run_id}.check.json"
        if not _ID_RE.match(str(run_id)) or not p.exists():
            return None
        try:
            return _read_json(p)
        except (OSError, json.JSONDecodeError):
            return None

    def drawings(self, run_id: str) -> dict[str, Any] | None:
        """Plné kresby behu pre graf (viď `export_chart`), alebo `None`, keď lokálne nie sú."""
        p = self.chart_file(run_id)
        return read_chart_file(p) if p is not None else None

    def plan(self, run_id: str) -> list[dict[str, Any]] | None:
        p = self.root / run_id / PLAN_FILE
        if not _ID_RE.match(str(run_id)) or not p.exists():
            return None
        try:
            return list((_read_json(p) or {}).get("objects") or [])
        except (OSError, json.JSONDecodeError):
            return None

    def chart(self, run_id: str) -> dict[str, Any] | None:
        """Kresby pre analytiku: plné, keď sú lokálne, inak výťah plánu obchodov
        (`plan.json`, `plan_only`). Graf páru volá `drawings`, nie toto."""
        full = self.drawings(run_id)
        if full is not None:
            return full
        plan = self.plan(run_id)
        return {"objects": plan, "plan_only": True} if plan is not None else None

    # -- celky (mriežky, matice, overenia) ------------------------------------ #

    def tagged(self, kind: str, batch_id: str | None = None) -> list[dict[str, Any]]:
        """Body celku zo `sweeps/` a staré behy s tou istou značkou, ktoré ešte ležia
        v histórii (pred `cli prune`). Starý beh má prednosť — má aj obchody."""
        stare = [r for r in self.all()
                 if ((r.get("settings") or {}).get(kind) or {}).get("id")
                 and (batch_id is None or r["settings"][kind]["id"] == batch_id)]
        videne = {r["id"] for r in stare}
        nove = [r for r in self.batches.records(kind, batch_id) if r.get("id") not in videne]
        return stare + nove

    def find(self, run_id: str) -> dict[str, Any] | None:
        """Beh z histórie, alebo bod celku (so značkou `batch`) — alebo `None`."""
        return self.get(run_id) or self.batches.find(run_id)

    def all(self) -> list[dict[str, Any]]:
        out = []
        zive: set[str] = set()
        try:
            polozky = list(os.scandir(self.root))
        except OSError:
            polozky = []
        for e in polozky:
            if not e.is_dir():
                continue
            rec = self._cached(e.name, Path(e.path) / "run.json")
            if rec is not None:
                zive.add(e.name)
                out.append(dict(rec))
        for run_id in [k for k in self._cache if k not in zive]:
            self._cache.pop(run_id, None)
        out.sort(key=lambda r: r.get("id", ""), reverse=True)
        return out

    def search(self, query: str) -> list[dict[str, Any]]:
        conds = parse_query(query)
        return [r for r in self.all() if all(_match(r, c) for c in conds)]


# --------------------------------------------------------------------------- #
# Vyhľadávanie
#
#   rrRatio>=5 useStructureFilter=true pair=ETH pnl>0 note~seansa
#
# Token bez operátora sa hľadá ako text v poznámke, páre, profile a id.
# --------------------------------------------------------------------------- #

_TOKEN_RE = re.compile(r'(\w[\w.]*)\s*(>=|<=|!=|=|>|<|~)\s*("[^"]*"|\S+)|(\S+)')

#: Skratky pre výsledkové polia, aby sa nemuselo písať `result.profit_total`.
ALIASES = {
    "pnl": "result.pnl_pct",
    "pnl_pct": "result.pnl_pct",
    "pnl_abs": "result.pnl_abs",
    "trades": "result.trades",
    "n": "result.trades",
    "pf": "result.profit_factor",
    "wr": "result.winrate",
    "winrate": "result.winrate",
    "dd": "result.max_drawdown_pct",
    "maxdd": "result.max_drawdown_pct",
    "breakeven": "result.break_even_pct",
    "be": "result.break_even_pct",
    "pair": "settings.pair",
    "strategy": "settings.strategy",
    "strat": "settings.strategy",
    "tf": "settings.timeframe",
    "timeframe": "settings.timeframe",
    "timerange": "settings.timerange",
    "fee": "settings.fee",
    "wallet": "settings.wallet",
    "profile": "settings.profile",
    "sweep": "settings.sweep.id",
    "engine": "settings.engine",
    "exchange": "settings.exchange",
    "status": "status",
    "note": "note",
    "id": "id",
    "user": "user",
}


def parse_query(query: str) -> list[tuple[str, str, str]]:
    conds: list[tuple[str, str, str]] = []
    for m in _TOKEN_RE.finditer(query or ""):
        if m.group(4):
            conds.append(("*", "~", m.group(4)))
            continue
        key, op, val = m.group(1), m.group(2), m.group(3).strip('"')
        conds.append((key, op, val))
    return conds


def _lookup(record: dict[str, Any], key: str) -> Any:
    key = ALIASES.get(key, key)
    if "." in key:
        cur: Any = record
        for part in key.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur
    params = record.get("params") or {}
    if key in params:
        v = params[key]
        return v.get("value") if isinstance(v, dict) and "value" in v else v
    return record.get(key)


def _coerce(val: str) -> Any:
    low = val.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return float(val)
    except ValueError:
        return val


def _match(record: dict[str, Any], cond: tuple[str, str, str]) -> bool:
    key, op, raw = cond
    if key == "*":
        hay = " ".join(
            str(x) for x in (
                record.get("id"), record.get("note"), record.get("user"),
                (record.get("settings") or {}).get("pair"),
                (record.get("settings") or {}).get("profile"),
                (record.get("settings") or {}).get("strategy"),
            ) if x
        ).lower()
        return raw.lower() in hay
    actual = _lookup(record, key)
    if actual is None:
        return False
    if op == "~":
        return raw.lower() in str(actual).lower()
    want = _coerce(raw)
    if isinstance(want, bool) or isinstance(actual, bool):
        return (bool(actual) == bool(want)) if op == "=" else (bool(actual) != bool(want)) if op == "!=" else False
    if isinstance(want, float):
        try:
            a = float(actual)
        except (TypeError, ValueError):
            return False
        return {
            "=": a == want, "!=": a != want, ">": a > want, "<": a < want, ">=": a >= want, "<=": a <= want,
        }[op]
    s = str(actual).lower()
    if op == "=":
        return s == raw.lower()
    if op == "!=":
        return s != raw.lower()
    return False


def diff_from_defaults(params: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Len odchýlky — to je to, čo tester chce v histórii vidieť na prvý pohľad."""
    out = {}
    for k, v in params.items():
        if k.startswith("_"):
            continue
        if defaults.get(k) != v:
            out[k] = v
    return out


def summarize_for_list(record: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Riadok do tabuľky histórie — bez sérií a bez celého configu."""
    r = record.get("result") or {}
    return {
        "id": record.get("id"),
        "status": record.get("status"),
        "created": record.get("created"),
        "user": record.get("user"),
        "note": record.get("note", ""),
        "settings": record.get("settings"),
        "overrides": diff_from_defaults(record.get("params") or {}, defaults),
        "result": {k: r.get(k) for k in (
            "trades", "wins", "losses", "winrate", "pnl_abs", "pnl_pct", "profit_factor",
            "max_drawdown_pct", "break_even_pct", "duration_s",
        )},
        "error": record.get("error"),
    }


def iter_ids(root: Path = RUNS_DIR) -> Iterable[str]:
    for p in Path(root).glob("*/run.json"):
        yield p.parent.name
