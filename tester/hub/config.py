"""Konfigurácia agenta v tomto klone (`tester/agent.json`) a jeho perzistentný stav.

```json
{
  "name": "srv-01",                 // statické meno = identita agenta na hube
  "hub_url": "https://hub.example.com:8790",
  "token": "…",                     // ten istý ako TRADEBOT_HUB_TOKEN na hube
  "accept": true,                   // prijíma výpočty od hubu
  "send": true,                     // smie posielať výpočty (cli --remote)
  "max_parallel": 4,                // koľko behov naraz (strop; jadrá si agent zistí sám)
  "heartbeat_seconds": 10
}
```

Meno je **statické a jednoznačné** — hub podľa neho pozná agenta cez reštarty aj výpadky
siete a podľa neho vie, komu poslať hotový výsledok. Dvaja agenti s jedným menom sa
na hub nedostanú (druhého odmietne, kým prvý žije).

Premenné prostredia prebijú súbor (`TRADEBOT_HUB_URL`, `TRADEBOT_HUB_TOKEN`,
`TRADEBOT_HUB_NAME`, `TRADEBOT_HUB_ACCEPT`, `TRADEBOT_HUB_SEND`) — pre Docker a servery,
kde sa súbor nechce písať.

Stav agenta (`tester/agent_state.json`) je oddelený od konfigurácie: čo agent **poslal**
a ešte sa mu nevrátilo, a čo práve **počíta** pre hub (hub job → lokálny beh). Po reštarte
agent v oboch pokračuje: čakajúce výsledky si vyzdvihne, bežiace behy ďalej hlási.
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from tradebot.core.env import getenv
from tradebot.core.paths import AGENT_CONFIG, AGENT_STATE

__all__ = ["AgentConfig", "AgentState", "load", "save", "load_state", "save_state"]

DEFAULT_HEARTBEAT = 10


@dataclass
class AgentConfig:
    name: str
    hub_url: str
    token: str = ""
    accept: bool = True
    send: bool = True
    max_parallel: int = 0          # 0 = podľa jadier
    heartbeat_seconds: int = DEFAULT_HEARTBEAT

    def slots(self, cores: int | None = None) -> int:
        """Koľko behov naraz: strop z configu, inak jadrá stroja."""
        cores = cores or os.cpu_count() or 1
        return max(1, min(cores, self.max_parallel) if self.max_parallel else cores)

    def public(self) -> dict[str, Any]:
        """Bez tokenu — do API a na obrazovku."""
        d = asdict(self)
        d["token"] = bool(self.token)
        return d


def _env_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() in ("1", "true", "yes", "on", "ano")


def load(path: Path | None = None) -> AgentConfig | None:
    """Config zo súboru + prostredia; `None`, keď agent nie je nastavený vôbec."""
    path = Path(path or AGENT_CONFIG)
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    url = getenv("HUB_URL") or data.get("hub_url")
    if not url:
        return None
    name = getenv("HUB_NAME") or data.get("name") or socket.gethostname()
    accept = _env_bool(getenv("HUB_ACCEPT"))
    send = _env_bool(getenv("HUB_SEND"))
    return AgentConfig(
        name=str(name).strip(),
        hub_url=str(url).rstrip("/"),
        token=getenv("HUB_TOKEN") or str(data.get("token") or ""),
        accept=bool(data.get("accept", True)) if accept is None else accept,
        send=bool(data.get("send", True)) if send is None else send,
        max_parallel=int(data.get("max_parallel") or 0),
        heartbeat_seconds=int(data.get("heartbeat_seconds") or DEFAULT_HEARTBEAT),
    )


def save(cfg: AgentConfig, path: Path | None = None) -> Path:
    path = Path(path or AGENT_CONFIG)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(asdict(cfg), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


# --------------------------------------------------------------------------- #
# stav agenta
# --------------------------------------------------------------------------- #


@dataclass
class AgentState:
    """Čo agent poslal a čo počíta — prežije reštart procesu.

    `sent[job_id]`  = {"kind", "note", "created", "status", "run_ids", "error"} — výpočty,
                      ktoré tento agent zadal; `status` sa dopĺňa, keď sa vrátia.
    `computing[job_id]` = {"run_id", "kind", "epochs"} — výpočty od hubu, ktoré bežia
                      v lokálnom runneri pod `run_id`.
    """

    sent: dict[str, dict[str, Any]] = field(default_factory=dict)
    computing: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"sent": self.sent, "computing": self.computing}


def load_state(path: Path | None = None) -> AgentState:
    path = Path(path or AGENT_STATE)
    if not path.exists():
        return AgentState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AgentState()
    return AgentState(sent=dict(data.get("sent") or {}), computing=dict(data.get("computing") or {}))


def save_state(state: AgentState, path: Path | None = None) -> Path:
    path = Path(path or AGENT_STATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(state.to_dict(), fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")
    os.replace(tmp, path)
    return path
