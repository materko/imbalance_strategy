"""Heslá účtov platforiem na disku agenta — DPAPI (`CryptProtectData`, rozsah používateľa).

Hub heslo nesie len dovtedy, kým ho agent neprevezme (`secret_pending`); agent ho uloží ako
`tester/live/secrets/<account>.bin` zašifrované na **tento stroj a tohto používateľa** — iný účet
Windows ani iný stroj súbor nerozšifruje. Do štartovacieho ini MT5 ide heslo len pri štarte
terminálu a driver ho z ini hneď po prihlásení zmaže.

Formát súboru: prvý riadok je značka (`TBDPAPI1` = DPAPI blob, `TBPLAIN1` = čitateľné — len mimo
Windows, kde DPAPI nie je; tam sa to loguje ako varovanie a je to určené na testy).
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from pathlib import Path

from tradebot.core.paths import LIVE_SECRETS

__all__ = ["store", "load", "delete", "secret_path", "dpapi_available"]

log = logging.getLogger(__name__)

_MARK_DPAPI = b"TBDPAPI1\n"
_MARK_PLAIN = b"TBPLAIN1\n"
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


def secret_path(account: str, root: Path | None = None) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in str(account))
    return Path(root or LIVE_SECRETS) / f"{safe}.bin"


def dpapi_available() -> bool:
    return sys.platform == "win32"


if sys.platform == "win32":
    from ctypes import wintypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    _crypt32 = ctypes.windll.crypt32
    _kernel32 = ctypes.windll.kernel32

    def _blob(data: bytes) -> _DATA_BLOB:
        buf = ctypes.create_string_buffer(data, len(data))
        return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))

    def _blob_bytes(blob: _DATA_BLOB) -> bytes:
        try:
            return ctypes.string_at(blob.pbData, blob.cbData)
        finally:
            _kernel32.LocalFree(blob.pbData)

    def _protect(data: bytes, entropy: bytes) -> bytes:
        inp, ent, out = _blob(data), _blob(entropy), _DATA_BLOB()
        if not _crypt32.CryptProtectData(ctypes.byref(inp), "TradeBot live", ctypes.byref(ent), None, None,
                                         _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out)):
            raise OSError(f"CryptProtectData zlyhalo (chyba {ctypes.GetLastError()})")
        return _blob_bytes(out)

    def _unprotect(data: bytes, entropy: bytes) -> bytes:
        inp, ent, out = _blob(data), _blob(entropy), _DATA_BLOB()
        if not _crypt32.CryptUnprotectData(ctypes.byref(inp), None, ctypes.byref(ent), None, None,
                                           _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out)):
            raise OSError(f"CryptUnprotectData zlyhalo (chyba {ctypes.GetLastError()}) — súbor je z iného "
                          "stroja alebo používateľa")
        return _blob_bytes(out)


def _entropy(account: str) -> bytes:
    """Blob je viazaný aj na id účtu — premenovaný súbor sa nerozšifruje."""
    return b"tradebot-live:" + str(account).encode("utf-8")


def store(account: str, password: str, root: Path | None = None) -> Path:
    """Zašifruje a zapíše heslo; vráti cestu. Zápis je atomický (tmp + `os.replace`)."""
    path = secret_path(account, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = str(password).encode("utf-8")
    if dpapi_available():
        data = _MARK_DPAPI + _protect(raw, _entropy(account))
    else:
        log.warning("live secrets: DPAPI nie je (nie Windows) — heslo účtu %s ide na disk čitateľne", account)
        data = _MARK_PLAIN + raw
    tmp = path.with_suffix(".bin.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return path


def load(account: str, root: Path | None = None) -> str | None:
    """Heslo, alebo `None`, keď uložené nie je. Nerozšifrovateľný súbor = `OSError`."""
    path = secret_path(account, root)
    if not path.is_file():
        return None
    data = path.read_bytes()
    if data.startswith(_MARK_DPAPI):
        if not dpapi_available():
            raise OSError(f"{path}: DPAPI blob sa dá otvoriť len na Windows")
        return _unprotect(data[len(_MARK_DPAPI):], _entropy(account)).decode("utf-8")
    if data.startswith(_MARK_PLAIN):
        return data[len(_MARK_PLAIN):].decode("utf-8")
    raise OSError(f"{path}: neznámy formát súboru s heslom")


def delete(account: str, root: Path | None = None) -> bool:
    path = secret_path(account, root)
    if not path.exists():
        return False
    path.unlink()
    return True
