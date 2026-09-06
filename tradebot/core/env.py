"""Premenné prostredia `TRADEBOT_*` so spätnou kompatibilitou pre staré `IBS_*`.

Balík sa volal `ibs` podľa prvej stratégie; po premenovaní na `tradebot` sa premenovali aj
premenné prostredia (`TRADEBOT_PROFILE`, `TRADEBOT_DRAW_OUT`, `TRADEBOT_USER`,
`TRADEBOT_WEB_HOST/PORT/URL`). Staré názvy ešte fungujú, ale zalogujú varovanie —
skripty a spúšťače testerov sa neaktualizujú naraz.
"""

from __future__ import annotations

import logging
import os

_log = logging.getLogger(__name__)
_warned: set[str] = set()


def getenv(name: str, default: str | None = None) -> str | None:
    """`TRADEBOT_<name>`, inak `IBS_<name>` (s varovaním), inak `default`."""
    new, old = f"TRADEBOT_{name}", f"IBS_{name}"
    value = os.environ.get(new)
    if value is not None:
        return value
    value = os.environ.get(old)
    if value is not None:
        if old not in _warned:
            _warned.add(old)
            _log.warning("%s je zastarané, použi %s", old, new)
        return value
    return default
