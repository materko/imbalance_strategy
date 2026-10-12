"""Prenos behov medzi históriami: adresáre `tester/runs/<id>/` ako jeden zip.

Zip nesie celé adresáre behov (`run.json`, `trades.json`, `log.txt`, `chart.json.gz`,
`epochs.json`…), takže sa po rozbalení u zadávateľa beh ničím nelíši od lokálneho —
história webapp ho číta z tých istých súborov.

Bod mriežky, bunka matice, overenie víťaza hyperoptu a sused víťaza do histórie nejdú
(`tester.webapp.batches`) — agent ho má len ako riadok v `sweeps/`. Do zipu ide ako
`points/<id>.json` (záznam behu v tvare `BatchStore.find`) a u zadávateľa sa zapíše do
jeho `sweeps/` rovnako, ako keby bod spočítal sám.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any, Iterable

from ..webapp.store import _ID_RE

__all__ = ["pack_runs", "unpack_runs"]

#: Adresár bodov celkov v zipe. Staré `unpack_runs` ho preskočia (nie je to id behu).
POINTS = "points"

#: Polia záznamu bodu, ktoré `BatchStore.expand` skladá sám — všetko ostatné sú polia
#: navyše (`break_even_ci`, `log_tail`), ktoré treba pri zápise odovzdať ako `extra`.
_RECORD_KEYS = ("id", "status", "created", "started", "finished", "user", "note",
                "settings", "params", "result", "error", "series", "batch")


def pack_runs(root: Path, run_ids: Iterable[str], batches: Any = None) -> bytes:
    """Adresáre behov (a body celkov z `batches`) ako zip v pamäti. Beh, ktorý na disku
    nie je ani ako adresár, ani ako bod celku, sa preskočí."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for run_id in run_ids:
            if not _ID_RE.match(run_id):
                continue
            d = Path(root) / run_id
            if d.is_dir():
                for p in sorted(d.rglob("*")):
                    if p.is_file():
                        z.write(p, f"{run_id}/{p.relative_to(d).as_posix()}")
                continue
            bod = batches.find(run_id) if batches is not None else None
            if bod is not None:
                z.writestr(f"{POINTS}/{run_id}.json",
                           json.dumps(bod, ensure_ascii=False, default=str))
    return buf.getvalue()


def unpack_runs(data: bytes, root: Path, batches: Any = None) -> list[str]:
    """Rozbalí zip do histórie (body celkov do `batches`) a vráti id behov.
    Cudzie cesty (mimo `<id>/…` a `points/<id>.json`) ignoruje."""
    root = Path(root)
    out: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            parts = Path(info.filename).parts
            if info.is_dir() or len(parts) < 2 or any(p in ("..", "") for p in parts):
                continue
            if parts[0] == POINTS:
                run_id = parts[1][:-5] if parts[1].endswith(".json") else ""
                if batches is None or len(parts) != 2 or not _ID_RE.match(run_id):
                    continue
                rec = json.loads(z.read(info).decode("utf-8"))
                if not isinstance(rec, dict) or rec.get("id") != run_id:
                    continue
                extra = {k: v for k, v in rec.items() if k not in _RECORD_KEYS}
                batches.add_point({k: v for k, v in rec.items() if k in _RECORD_KEYS}, extra)
                if run_id not in out:
                    out.append(run_id)
                continue
            if not _ID_RE.match(parts[0]):
                continue
            cieľ = root.joinpath(*parts)
            cieľ.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(cieľ, "wb") as dst:
                dst.write(src.read())
            if parts[0] not in out:
                out.append(parts[0])
    return out
