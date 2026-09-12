"""Prenos behov medzi históriami: adresáre `tester/runs/<id>/` ako jeden zip.

Zip nesie celé adresáre behov (`run.json`, `trades.json`, `log.txt`, `chart.json.gz`,
`epochs.json`…), takže sa po rozbalení u zadávateľa beh ničím nelíši od lokálneho —
história webapp ho číta z tých istých súborov.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Iterable

from ..webapp.store import _ID_RE

__all__ = ["pack_runs", "unpack_runs"]


def pack_runs(root: Path, run_ids: Iterable[str]) -> bytes:
    """Adresáre behov ako zip v pamäti. Beh, ktorý na disku nie je, sa preskočí."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for run_id in run_ids:
            d = Path(root) / run_id
            if not _ID_RE.match(run_id) or not d.is_dir():
                continue
            for p in sorted(d.rglob("*")):
                if p.is_file():
                    z.write(p, f"{run_id}/{p.relative_to(d).as_posix()}")
    return buf.getvalue()


def unpack_runs(data: bytes, root: Path) -> list[str]:
    """Rozbalí zip do histórie a vráti id behov. Cudzie cesty (mimo `<id>/…`) ignoruje."""
    root = Path(root)
    out: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            parts = Path(info.filename).parts
            if info.is_dir() or len(parts) < 2 or not _ID_RE.match(parts[0]):
                continue
            if any(p in ("..", "") for p in parts):
                continue
            cieľ = root.joinpath(*parts)
            cieľ.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(cieľ, "wb") as dst:
                dst.write(src.read())
            if parts[0] not in out:
                out.append(parts[0])
    return out
