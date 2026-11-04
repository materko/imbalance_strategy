"""Plugin agenta `telegram` (docs/LIVE.md, „Telegram“): `TelegramService` v kontrakte `AgentPlugin`.

Config `TELEGRAM_CONFIG` sa preverí raz za minútu (súbor pribudol, zmenil sa token či chaty = nová služba);
bez configu plugin len čaká. Prekrytia režimov (`/pause` z Telegramu, kým ich hub neprevezme) drží
`TelegramState` na disku, takže reload pluginu ich nestratí.
"""

from __future__ import annotations

from typing import Any

from tradebot.core.paths import (LIVE_JOURNAL, LIVE_JOURNAL_CURSOR, LIVE_JOURNAL_STATE, TELEGRAM_CONFIG,
                                 TELEGRAM_CURSOR, TELEGRAM_STATE)
from tradebot.live.telegram import load_config

from ..base import AgentPlugin, AgentPluginContext

__all__ = ["TelegramPlugin", "RECHECK_SECONDS"]

#: Ako často sa znova pozrie config (súbor pribudol, zmenil sa token či chaty).
RECHECK_SECONDS = 60.0


class TelegramPlugin(AgentPlugin):
    title = "Telegram"
    interval = 0.0          # `TelegramService.tick` čaká sám (long-poll príkazov)

    def __init__(self, config_path: Any = None, service: Any = None) -> None:
        """`config_path` a `service` sa dajú podstrčiť (testy)."""
        self.config_path = config_path or TELEGRAM_CONFIG
        self.svc: Any = service
        self._stamp: tuple[float, float] | None = None if service is None else (float("inf"), 0.0)

    def setup(self, ctx: AgentPluginContext) -> None:
        self.ctx = ctx

    # -- služba podľa configu ---------------------------------------------- #

    def service(self) -> Any:
        if self._stamp is not None and self._stamp[0] == float("inf"):
            return self.svc      # podstrčená v teste
        now = self.ctx.clock()
        if self._stamp is not None and now - self._stamp[0] < RECHECK_SECONDS:
            return self.svc
        try:
            mtime = self.config_path.stat().st_mtime
        except OSError:
            mtime = -1.0
        if self._stamp is not None and self._stamp[1] == mtime:
            self._stamp = (now, mtime)
            return self.svc
        self._stamp = (now, mtime)
        from .service import TelegramService

        cfg = load_config(self.config_path)
        if cfg is None:
            self.svc = None
            return None
        if not cfg.label:
            cfg.label = self.ctx.agent_name
        self.svc = TelegramService(cfg, TELEGRAM_STATE, TELEGRAM_CURSOR, roots=self.ctx.spool_roots,
                                   issues=self._issues, on_change=self.ctx.modes_changed,
                                   journal_paths=(LIVE_JOURNAL, LIVE_JOURNAL_STATE, LIVE_JOURNAL_CURSOR),
                                   hub=self.ctx.hub_views)
        self.ctx.log.info("telegram zapnutý (%d chat(y), príkazy %s)", len(cfg.chats), "áno" if cfg.commands else "nie")
        return self.svc

    def _issues(self) -> dict[str, tuple[str, str]]:
        """Chyby aktívnych nasadení: `dep → (popis, chyba)` (prázdna chyba = v poriadku)."""
        from .service import _platform, _sym

        out: dict[str, tuple[str, str]] = {}
        for d, chyba in self.ctx.deployments():
            popis = f"{d.get('strategy')} {_sym(d.get('symbol'))} {_platform(d.get('platform'))}".strip()
            out[str(d.get("id"))] = (popis, chyba)
        return out

    # -- kontrakt ------------------------------------------------------------ #

    def tick(self) -> None:
        svc = self.service()
        if svc is None:
            self.ctx.stopping.wait(RECHECK_SECONDS)
            return
        svc.tick(3.0)

    def status(self) -> dict[str, Any] | None:
        return self.svc.status() if self.svc is not None else None

    def overrides(self) -> list[dict[str, Any]]:
        return list(self.svc.state.overrides()) if self.svc is not None else []

    def drop_override(self, instance: str) -> None:
        if self.svc is not None:
            self.svc.state.drop_override(instance)

    def desired(self, desired: dict[str, Any], now: float) -> None:
        if self.svc is not None:
            self.svc.state.note_desired(desired, now)
