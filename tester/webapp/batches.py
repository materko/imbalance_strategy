"""Výsledky hromadných behov — mriežka, matica, overenie víťaza hyperoptu, okolie víťaza.

    sweeps/sweep-<id>.json          body mriežky (`cli sweep`, karta Hľadanie)
    sweeps/matrix-<id>.json         bunky matice trhov a timeframov
    sweeps/hyperopt_run-<id>.json   víťaz hyperoptu na referenčných oknách (`id` = beh hyperoptu)
    sweeps/plateau-<id>.json        susedia víťaza (`id` = beh hyperoptu)

### Prečo nie obyčajné behy
Každý bod mriežky bol kedysi celý beh v `runs/` — s obchodmi, logom a megabajtovými
kresbami. Mriežky a matice ich vyrobili tisíce, repozitár narástol na jedenásť gigabajtov
a GitHub push odmietol. Z bodu sa pritom číta len riadok tabuľky: hodnoty parametrov,
výsledok (break-even, PnL, drawdown, počet obchodov) a stav. Presne to sa ukladá.

Bod nesie **celý efektívny config** (parametre aj nastavenia behu), len úsporne: spoločný
základ je raz v hlavičke a bod má iba to, čím sa od neho líši. Z toho sa dá bod kedykoľvek
prehrať ako obyčajný beh (`cli replay <id>`, tlačidlo v tabuľke) — a ten už do histórie ide.

### Tvar záznamu
`records()` vracia body v tvare záznamu behu (`id`, `status`, `settings` so značkou,
`params`, `result`), takže poradie mriežky (`tester.sweep.rank`), tabuľka matice, verdikt
overenia aj test okolia nad nimi pracujú bez zmeny — rovnako ako kedysi nad históriou.
Navyše majú `batch: {kind, id}`, podľa čoho stránka vie, že bod v histórii nie je.

Súbor zapisuje len runner (jedno pracovné vlákno) a atomicky (dočasný súbor + premenovanie),
takže čítanie z webapp nikdy nevidí rozpísaný JSON. Každý celok je nový súbor, git merge
nemá o čo bojovať.
"""

from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Iterable

from tradebot.core.paths import SWEEPS_DIR

__all__ = ["KINDS", "BatchStore", "batch_tag", "strip_tag", "new_batch", "add_to"]

#: Značky v `settings`, podľa ktorých beh patrí do celku a nie do histórie. Kľúč je zároveň
#: druh celku a predpona súboru.
KINDS = ("sweep", "matrix", "hyperopt_run", "plateau")

#: Pole značky, ktoré sa neukladá: podpis mriežky je JSON celého zadania (pri veľkej
#: mriežke desiatky kB na bod) a slúži len na odmietnutie tej istej mriežky vo fronte.
_TAG_SKIP = ("signature",)

_ID_RE = re.compile(r"^[0-9A-Za-z_-]{1,64}$")
_RUN_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")


def batch_tag(settings: dict[str, Any] | None) -> tuple[str, dict[str, Any]] | None:
    """`(druh, značka)` behu, ktorý patrí do celku — alebo `None` pre obyčajný beh."""
    for kind in KINDS:
        tag = (settings or {}).get(kind)
        if isinstance(tag, dict) and tag.get("id"):
            return kind, tag
    return None


def strip_tag(settings: dict[str, Any]) -> dict[str, Any]:
    """Nastavenia behu bez značiek celkov — s tým sa bod prehrá ako obyčajný beh."""
    return {k: v for k, v in settings.items() if k not in KINDS}


def _diff(full: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """Čím sa `full` líši od `base`. Kľúč, ktorý v `full` chýba, sa zapíše ako `null`."""
    out = {k: v for k, v in full.items() if k not in base or base[k] != v}
    out.update({k: None for k in base if k not in full and base[k] is not None})
    return out


def _write_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, default=str)
        fh.write("\n")
    os.replace(tmp, path)


def _kind_id(record: dict[str, Any]) -> tuple[str, str]:
    found = batch_tag(record.get("settings"))
    if found is None:
        raise ValueError("záznam nemá značku celku (sweep/matrix/hyperopt_run/plateau)")
    return found[0], str(found[1]["id"])


def new_batch(record: dict[str, Any]) -> dict[str, Any]:
    """Prázdny celok, ktorého základ (spoločný config) je config tohto behu."""
    kind, batch_id = _kind_id(record)
    settings = strip_tag(dict(record.get("settings") or {}))
    return {
        "version": 1, "kind": kind, "id": batch_id,
        "strategy": settings.get("strategy") or "ibs",
        "created": record.get("created"), "user": record.get("user") or "",
        "base": {"params": dict(record.get("params") or {}), "settings": settings},
        "points": [],
    }


def add_to(data: dict[str, Any], record: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
    """Zapíše bod do celku v pamäti — len rozdiel oproti základu, bez podpisu mriežky."""
    kind, _ = _kind_id(record)
    tag = record["settings"][kind]
    base = data["base"]
    settings = strip_tag(dict(record.get("settings") or {}))
    point = {
        "run": record["id"],
        "status": record.get("status"),
        "created": record.get("created"),
        "started": record.get("started"),
        "finished": record.get("finished"),
        "user": record.get("user") or "",
        "note": record.get("note") or "",
        "tag": {k: v for k, v in tag.items() if k not in _TAG_SKIP and k != "id"},
        "params": _diff(dict(record.get("params") or {}), base.get("params") or {}),
        "settings": _diff(settings, base.get("settings") or {}),
        "result": record.get("result"),
        "error": record.get("error"),
        **(extra or {}),
    }
    data["points"] = [p for p in data["points"] if p.get("run") != record["id"]] + [point]
    data["points"].sort(key=lambda p: str(p.get("run")))
    data["updated"] = max(str(data.get("updated") or ""), str(record.get("finished") or record.get("created") or ""))


class BatchStore:
    """Súbory celkov v `sweeps/` — zápis bodov a ich čítanie v tvare záznamu behu."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root or SWEEPS_DIR)
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[tuple[int, int], dict[str, Any]]] = {}

    # -- cesty ---------------------------------------------------------------- #

    def path(self, kind: str, batch_id: str) -> Path:
        if kind not in KINDS or not _ID_RE.match(str(batch_id)):
            raise ValueError(f"neplatný celok: {kind!r}/{batch_id!r}")
        return self.root / f"{kind}-{batch_id}.json"

    # -- zápis ---------------------------------------------------------------- #

    def add_point(self, record: dict[str, Any], extra: dict[str, Any] | None = None) -> Path:
        """Pridá (alebo prepíše, keď už je) bod celku zo záznamu behu.

        `record` je presne to, čo by sa inak uložilo do `runs/<id>/run.json`; celok a druh
        sa berú zo značky v `settings`. `extra` sú polia navyše k bodu (interval víťaza).
        """
        with self._lock:
            kind, batch_id = _kind_id(record)
            path = self.path(kind, batch_id)
            data = self._load(path) or new_batch(record)
            add_to(data, record, extra)
            _write_atomic(path, data)
            self._cache.pop(str(path), None)
            return path

    def write(self, data: dict[str, Any]) -> Path:
        """Zapíše celý celok naraz (migrácia starých behov, `cli prune`)."""
        path = self.path(data["kind"], data["id"])
        with self._lock:
            _write_atomic(path, data)
            self._cache.pop(str(path), None)
        return path

    # -- čítanie -------------------------------------------------------------- #

    def _load(self, path: Path) -> dict[str, Any] | None:
        try:
            st = path.stat()
        except OSError:
            self._cache.pop(str(path), None)
            return None
        podpis = (st.st_mtime_ns, st.st_size)
        hit = self._cache.get(str(path))
        if hit is not None and hit[0] == podpis:
            return hit[1]
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None
        self._cache[str(path)] = (podpis, data)
        return data

    def get(self, kind: str, batch_id: str) -> dict[str, Any] | None:
        """Surový súbor celku, alebo `None`."""
        try:
            return self._load(self.path(kind, batch_id))
        except ValueError:
            return None

    def files(self, kind: str | None = None) -> list[dict[str, Any]]:
        """Všetky celky (daného druhu), od najnovšieho."""
        out = []
        try:
            polozky = sorted(os.scandir(self.root), key=lambda e: e.name, reverse=True)
        except OSError:
            return []
        for e in polozky:
            if not e.name.endswith(".json") or e.name.startswith("."):
                continue
            druh, _, _ = e.name[:-5].partition("-")
            if druh not in KINDS or (kind is not None and druh != kind):
                continue
            data = self._load(Path(e.path))
            if data is not None:
                out.append(data)
        return out

    @staticmethod
    def expand(data: dict[str, Any], point: dict[str, Any]) -> dict[str, Any]:
        """Bod celku ako záznam behu — so značkou v `settings` a s celým configom."""
        base = data.get("base") or {}
        # Kľúč, ktorý bod nemal, je v rozdiele `null` — pre čitateľov (`.get`) je to to isté.
        params = {**(base.get("params") or {}), **(point.get("params") or {})}
        settings = {**(base.get("settings") or {}), **(point.get("settings") or {})}
        settings[data["kind"]] = {"id": data["id"], **(point.get("tag") or {})}
        rec = {
            "id": point.get("run"),
            "status": point.get("status"),
            "created": point.get("created"),
            "started": point.get("started"),
            "finished": point.get("finished"),
            "user": point.get("user") or "",
            "note": point.get("note") or "",
            "settings": settings,
            "params": params,
            "result": point.get("result"),
            "error": point.get("error"),
            "series": None,
            "batch": {"kind": data["kind"], "id": data["id"]},
        }
        for k, v in point.items():
            if k not in rec and k not in ("run", "tag"):
                rec[k] = v
        return rec

    def records(self, kind: str, batch_id: str | None = None) -> list[dict[str, Any]]:
        """Body celku (alebo všetkých celkov druhu) ako záznamy behov."""
        celky = ([self.get(kind, batch_id)] if batch_id is not None else self.files(kind))
        out = []
        for data in celky:
            if not data:
                continue
            out.extend(self.expand(data, p) for p in data.get("points") or [])
        return out

    def find(self, run_id: str) -> dict[str, Any] | None:
        """Bod podľa id behu, v ktoromkoľvek celku — alebo `None`."""
        if not _RUN_ID_RE.match(str(run_id)):
            return None
        for data in self.files():
            for p in data.get("points") or []:
                if p.get("run") == run_id:
                    return self.expand(data, p)
        return None

    def ids(self) -> Iterable[str]:
        for data in self.files():
            for p in data.get("points") or []:
                if p.get("run"):
                    yield p["run"]
