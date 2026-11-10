"""Atomické zápisy, zámok medzi procesmi a čítanie JSON-u, ktoré pokazený súbor nezahodí potichu.

Jedno miesto pre všetko, čo si drží stav v súbore (história behov, profily, stav hubu a agenta, kurzory,
manifest odvodených timeframov):

* **zápis** ide do dočasného súboru vedľa cieľa a `os.replace` — pád procesu, Ctrl+C alebo plný disk
  uprostred zápisu nechá pôvodný súbor celý; čitateľ vidí buď starý, alebo celý nový (audit 25. 10. 2026,
  N-WEB-4, N-HUB-8; 9. 11. 2026, M-CORE-4);
* **`file_lock`** stráži „prečítaj – uprav – zapíš" medzi procesmi (webapp a podproces Freqtrade píšu ten
  istý manifest);
* **`read_json`** pokazený súbor odloží ako `<meno>.corrupt-<čas>` a nahlas to zaloguje, namiesto aby sa
  ticho tváril ako prázdny (N-HUB-9: pokazený `state.json` = hub bez výpočtov a nikto nevie prečo).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

__all__ = ["atomic_path", "file_lock", "read_json", "write_bytes_atomic", "write_json_atomic", "write_text_atomic"]

log = logging.getLogger(__name__)

#: Windows: cieľ má na okamih otvorený čitateľ (EA, antivírus, iné vlákno) a `os.replace` vráti
#: PermissionError — pár krátkych pokusov to prekryje. Iná chyba (plný disk) ide von hneď.
_REPLACE_TRIES = 5
_REPLACE_WAIT = 0.05


def _replace(tmp: Path, path: Path) -> None:
    for attempt in range(_REPLACE_TRIES):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == _REPLACE_TRIES - 1:
                raise
            time.sleep(_REPLACE_WAIT * (attempt + 1))


@contextmanager
def atomic_path(path: Path | str) -> Iterator[Path]:
    """Dočasná cesta vedľa cieľa pre zapisovače, ktoré chcú meno súboru (feather, zip): po úspešnom bloku
    sa presunie na cieľ, pri výnimke sa zmaže a cieľ ostáva nedotknutý."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        yield tmp
        _replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def write_bytes_atomic(path: Path | str, data: bytes) -> None:
    with atomic_path(path) as tmp:
        tmp.write_bytes(data)


def write_text_atomic(path: Path | str, text: str, *, encoding: str = "utf-8") -> None:
    with atomic_path(path) as tmp:
        with open(tmp, "w", encoding=encoding, newline="\n") as fh:
            fh.write(text)


def write_json_atomic(path: Path | str, data: Any, *, indent: int | None = 2, newline: bool = True,
                      default: Any = None, sort_keys: bool = False, separators: tuple[str, str] | None = None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=indent, default=default, sort_keys=sort_keys,
                      separators=separators)
    write_text_atomic(path, text + ("\n" if newline else ""))


@contextmanager
def file_lock(path: Path | str, *, timeout: float = 10.0, stale: float = 60.0) -> Iterator[None]:
    """Zámok medzi procesmi pre súbor `path` (zámkový súbor `<meno>.lock` vedľa neho, `O_EXCL`).

    Zámok starší než `stale` sekúnd patrí procesu, ktorý spadol, a prevezme sa. Keď sa zámok nepodarí
    získať do `timeout`, ide sa ďalej bez neho — zaseknutý zámok nesmie zastaviť backtest; horší prípad
    je stratená aktualizácia, ktorú by sme bez zámku mali vždy."""
    lock = Path(path).with_name(Path(path).name + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    held = False
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            held = True
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > stale:
                    lock.unlink()
                    continue
            except OSError:
                continue   # medzitým zmizol - skúsiť znova
        except OSError:
            break          # adresár len na čítanie a pod. - bez zámku
        if time.monotonic() >= deadline:
            log.warning("zámok %s sa nepodarilo získať do %.0f s - pokračujem bez neho", lock, timeout)
            break
        time.sleep(0.02)
    try:
        yield
    finally:
        if held:
            try:
                lock.unlink()
            except OSError:
                pass


def read_json(path: Path | str, default: Any = None, *, what: str = "") -> Any:
    """JSON zo súboru. Chýbajúci súbor = `default` bez hluku. Súbor, ktorý sa nedá prečítať alebo nie je
    JSON, sa odloží ako `<meno>.corrupt-<čas>` (dá sa ručne obnoviť), zaloguje sa chyba a vráti sa `default`."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default
    except OSError as exc:
        log.error("%s %s sa nedá prečítať (%s) - pokračujem s prázdnym", what or "súbor", path, exc)
        return default
    try:
        return json.loads(text)
    except ValueError as exc:
        kept = path.with_name(f"{path.name}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}")
        try:
            os.replace(path, kept)
        except OSError:
            kept = path
        log.error("%s %s je pokazený (%s) - odložený ako %s, pokračujem s prázdnym", what or "súbor", path, exc, kept.name)
        return default
