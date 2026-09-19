"""Tokeny hubu: hlavný (správcovský) a tokeny agentov, ktoré ich zároveň identifikujú."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any


#: Identita správcu (hlavný token, alebo hub bez tokenov).
ADMIN = "*"


class TokensMixin:
    """Tokeny agentov (`tokens.json`) a kto volá — časť `HubState`."""

    @property
    def tokens_file(self) -> Path:
        return self.root / "tokens.json"

    def _tokens_signature(self) -> tuple[int, int] | None:
        try:
            st = self.tokens_file.stat()
        except OSError:
            return None
        return (st.st_mtime_ns, st.st_size)

    def _load_tokens(self) -> None:
        podpis = self._tokens_signature()
        if podpis == self._tokens_stamp:
            return
        self._tokens_stamp = podpis
        if podpis is None:
            self.tokens = {}
            return
        try:
            data = json.loads(self.tokens_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self.tokens = {str(k): str(v) for k, v in (data or {}).items() if v}

    def _save_tokens(self) -> None:
        tmp = self.tokens_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(self.tokens, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self.tokens_file)
        try:
            os.chmod(self.tokens_file, 0o600)
        except OSError:
            pass
        self._tokens_stamp = self._tokens_signature()

    def identity(self, token: str | None) -> str | None:
        """Kto volá: `ADMIN` (hlavný token, alebo hub bez tokenov), meno agenta, alebo
        `None` = neplatný token."""
        with self._lock:
            self._load_tokens()
            if not self.token and not self.tokens:
                return ADMIN
            if not token:
                return None
            if self.token and secrets.compare_digest(token, self.token):
                return ADMIN
            for name, t in self.tokens.items():
                if secrets.compare_digest(token, t):
                    return name
            return None

    def add_token(self, name: str, token: str | None = None, by: str = ADMIN) -> str:
        """Vydá (alebo prepíše) token agenta. Vracia ho — inde sa už nedá prečítať celý."""
        name = (name or "").strip()
        if not name:
            raise ValueError("agent musí mať meno")
        with self._lock:
            self._load_tokens()
            token = token or secrets.token_urlsafe(24)
            self.tokens[name] = token
            self._save_tokens()
            self.log("token_added", agent=name, by=by)
            return token

    def remove_token(self, name: str, by: str = ADMIN) -> bool:
        with self._lock:
            self._load_tokens()
            if name not in self.tokens:
                return False
            del self.tokens[name]
            self._save_tokens()
            self.log("token_removed", agent=name, by=by)
            return True

    def token_names(self) -> list[dict[str, Any]]:
        with self._lock:
            self._load_tokens()
            return [{"name": n, "token_hint": t[:4] + "…", "registered": n in self.agents}
                    for n, t in sorted(self.tokens.items())]
