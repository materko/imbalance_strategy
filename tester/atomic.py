"""Atomické zápisy súborov Testera — implementácia je v jadre (`tradebot.core.atomic`), aby ju mohli
používať aj `tradebot.core` a `tradebot.live`; tento modul ostáva kvôli doterajším importom.
"""

from __future__ import annotations

import os  # noqa: F401 - testy cez `atomic.os` simulujú zlyhanie `os.replace`

from tradebot.core.atomic import (
    atomic_path,
    file_lock,
    read_json,
    write_bytes_atomic,
    write_json_atomic,
    write_text_atomic,
)

__all__ = ["atomic_path", "file_lock", "read_json", "write_bytes_atomic", "write_json_atomic", "write_text_atomic"]
