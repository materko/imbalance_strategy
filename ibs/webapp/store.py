"""Ukladanie behov — jeden adresár na beh, všetko čitateľný JSON.

    runs/<run_id>/run.json        parametre, nastavenia behu, výsledok (súhrn), séria pre graf
    runs/<run_id>/trades.json     zoznam obchodov
    runs/<run_id>/log.txt         skrátený log Freqtradu
    runs/<run_id>/chart.json.gz   kresby enginu (zóny, boxy, štítky) pre graf páru

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
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO / "platforms" / "freqtrade" / "user_data" / "runs"

_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")

#: Kresby enginu — gzip, lebo ročný beh má desaťtisíce objektov (~MB v JSON) a súbor
#: sa po zápise už nikdy nemení, takže čitateľný diff nikto nepotrebuje.
CHART_FILE = "chart.json.gz"


def make_run_id(params: dict[str, Any], settings: dict[str, Any], when: datetime | None = None) -> str:
    when = when or datetime.now(timezone.utc)
    blob = json.dumps({"p": params, "s": settings}, sort_keys=True, default=str).encode()
    return f"{when:%Y%m%d-%H%M%S}-{hashlib.sha1(blob).hexdigest()[:6]}"


def _read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


class RunStore:
    def __init__(self, root: Path | None = None) -> None:
        # RUNS_DIR sa čita az tu, aby sa dal v testoch a nastrojoch prepnut
        self.root = Path(root or RUNS_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    # -- zápis -------------------------------------------------------------- #

    def save(self, record: dict[str, Any], trades: list[dict[str, Any]] | None = None,
             log: str | None = None, chart_path: Path | str | None = None) -> Path:
        """`chart_path` je hotový súbor kresieb od stratégie — presunie sa do adresára
        behu (nie kopíruje: má megabajty a dočasný adresár by ho inak držal navždy)."""
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
            shutil.move(str(chart_path), str(d / CHART_FILE))
        return d

    def delete(self, run_id: str) -> bool:
        d = self.root / run_id
        if not _ID_RE.match(run_id) or not d.is_dir():
            return False
        shutil.rmtree(d)
        return True

    # -- čítanie ------------------------------------------------------------ #

    def get(self, run_id: str) -> dict[str, Any] | None:
        p = self.root / run_id / "run.json"
        return _read_json(p) if p.exists() else None

    def trades(self, run_id: str) -> list[dict[str, Any]]:
        p = self.root / run_id / "trades.json"
        return _read_json(p) if p.exists() else []

    def log(self, run_id: str) -> str:
        p = self.root / run_id / "log.txt"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def has_chart(self, run_id: str) -> bool:
        return (self.root / run_id / CHART_FILE).exists()

    def chart(self, run_id: str) -> dict[str, Any] | None:
        """Kresby behu (viď `ibs.adapters.freqtrade.runner.export_chart`), alebo `None`."""
        p = self.root / run_id / CHART_FILE
        if not p.exists():
            return None
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            return json.load(fh)

    def all(self) -> list[dict[str, Any]]:
        out = []
        for p in self.root.glob("*/run.json"):
            try:
                out.append(_read_json(p))
            except (OSError, json.JSONDecodeError):
                continue  # rozbitý súbor nemá zhodiť celý zoznam
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
    "timerange": "settings.timerange",
    "fee": "settings.fee",
    "wallet": "settings.wallet",
    "profile": "settings.profile",
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
