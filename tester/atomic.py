"""Atomické zápisy súborov Testera — dočasný súbor vedľa cieľa a `os.replace`.

Pád procesu, Ctrl+C alebo plný disk uprostred zápisu nesmie nechať rozbitý `run.json`, profil ani
register archívu: rozbitý JSON história ticho preskočí a index ho zmaže, takže beh by zmizol (audit
25. 10. 2026, N-WEB-4). `os.replace` je na Windows aj POSIX atomický v rámci jedného disku; čitateľ
vidí buď starý, alebo celý nový súbor.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

__all__ = ["write_text_atomic", "write_json_atomic"]


def write_text_atomic(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(tmp, "w", encoding=encoding, newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def write_json_atomic(path: Path, data: Any, *, indent: int | None = 2, newline: bool = True,
                      default: Any = None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=indent, default=default)
    write_text_atomic(path, text + ("\n" if newline else ""))
