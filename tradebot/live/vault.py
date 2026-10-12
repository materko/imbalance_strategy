"""Šifrovanie hesiel účtov na hube — len štandardná knižnica (image hubu nemá `cryptography`).

Hub heslo účtu drží, aby ho mohol doručiť každému stroju, ktorý dostane nasadenie s tým účtom
(účet nie je viazaný na stroj). V sqlite leží len šifrované: kľúč je v súbore `secret.key` vedľa
databázy (vznikne pri prvom použití, práva 0600), alebo v `TRADEBOT_HUB_SECRET_KEY` (hex/base64,
32 bajtov). Kto má databázu bez kľúča (záloha, kópia), heslá neprečíta; kto má oboje, áno.

Konštrukcia: HMAC-SHA256 ako PRF v režime počítadla (keystream), potom HMAC-SHA256 nad
verziou, nonce a šifrovaným textom (encrypt-then-MAC). Kľúče na šifrovanie a overenie sú
odvodené z hlavného kľúča zvlášť. Formát: `v1:` + base64(nonce 16 B ‖ šifra ‖ tag 32 B).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import secrets
from pathlib import Path

from tradebot.core.env import getenv

__all__ = ["Vault", "VaultError", "KEY_ENV"]

#: Premenná s hlavným kľúčom (bez prefixu `TRADEBOT_`, ako ostatné `getenv`).
KEY_ENV = "HUB_SECRET_KEY"

_VERSION = b"v1"
_NONCE = 16
_TAG = 32


class VaultError(ValueError):
    """Heslo sa nedá rozšifrovať — iný kľúč, poškodený záznam."""


class Vault:
    def __init__(self, key_path: Path | str | None = None, key: bytes | None = None) -> None:
        self.key_path = Path(key_path) if key_path else None
        self._key = key

    def _master(self) -> bytes:
        if self._key is not None:
            return self._key
        raw = (getenv(KEY_ENV) or "").strip()
        if raw:
            self._key = _decode_key(raw)
            return self._key
        if self.key_path is None:
            raise VaultError(f"kľúč na heslá chýba (TRADEBOT_{KEY_ENV} alebo súbor secret.key)")
        try:
            data = self.key_path.read_bytes().strip()
        except FileNotFoundError:
            data = b""
        if data:
            self._key = _decode_key(data.decode("ascii", "replace"))
            return self._key
        key = secrets.token_bytes(32)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.key_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as fh:
            fh.write(key.hex() + "\n")
        self._key = key
        return key

    def _keys(self) -> tuple[bytes, bytes]:
        m = self._master()
        return (hmac.new(m, b"tradebot-vault-enc", hashlib.sha256).digest(),
                hmac.new(m, b"tradebot-vault-mac", hashlib.sha256).digest())

    @staticmethod
    def _stream(key: bytes, nonce: bytes, n: int) -> bytes:
        out = bytearray()
        i = 0
        while len(out) < n:
            out += hmac.new(key, nonce + i.to_bytes(8, "big"), hashlib.sha256).digest()
            i += 1
        return bytes(out[:n])

    def encrypt(self, text: str) -> str:
        enc, mac = self._keys()
        nonce = secrets.token_bytes(_NONCE)
        data = text.encode("utf-8")
        ct = bytes(a ^ b for a, b in zip(data, self._stream(enc, nonce, len(data))))
        tag = hmac.new(mac, _VERSION + nonce + ct, hashlib.sha256).digest()
        return "v1:" + base64.b64encode(nonce + ct + tag).decode("ascii")

    def decrypt(self, blob: str) -> str:
        if not str(blob or "").startswith("v1:"):
            raise VaultError("neznámy formát šifrovaného hesla")
        try:
            raw = base64.b64decode(blob[3:], validate=True)
        except (binascii.Error, ValueError):
            raise VaultError("poškodené šifrované heslo") from None
        if len(raw) < _NONCE + _TAG:
            raise VaultError("poškodené šifrované heslo")
        nonce, ct, tag = raw[:_NONCE], raw[_NONCE:-_TAG], raw[-_TAG:]
        enc, mac = self._keys()
        if not hmac.compare_digest(tag, hmac.new(mac, _VERSION + nonce + ct, hashlib.sha256).digest()):
            raise VaultError("heslo sa nedá rozšifrovať týmto kľúčom (zmenil sa secret.key?)")
        return bytes(a ^ b for a, b in zip(ct, self._stream(enc, nonce, len(ct)))).decode("utf-8")


def _decode_key(raw: str) -> bytes:
    raw = raw.strip()
    try:
        key = bytes.fromhex(raw)
    except ValueError:
        try:
            key = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError):
            raise VaultError("kľúč na heslá nie je hex ani base64") from None
    if len(key) < 32:
        raise VaultError("kľúč na heslá musí mať aspoň 32 bajtov")
    return key
