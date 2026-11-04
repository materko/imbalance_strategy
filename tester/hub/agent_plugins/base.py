"""Kontrakt pluginu agenta (docs/HUB.md, „Pluginy agenta“): čo plugin dostane (`AgentPluginContext`) a čo dodá
(`AgentPlugin`).

Plugin nevidí agenta — len svoj kontext: meno stroja, korene spoolu platforiem, stav nasadení z reconcilera,
pohľady pluginov hubu, spätné volanie „zmenil som režim“ a udalosť `stopping` (zastavenie aj reload).
Vlákno a zachytenie výnimiek drží `AgentPluginHost`. Tento súbor a `__init__.py` sú **rozhranie**: ich
zmena (alebo zmena čohokoľvek mimo adresára pluginu) = reštart agenta; zmena len v adresári pluginu =
plugin sa načíta znova za behu (`tester.hub.pluginreload`).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

__all__ = ["AgentPlugin", "AgentPluginContext", "API"]

#: Verzia rozhrania (pre `status`); mení sa so zmenou tohto súboru.
API = 1


class AgentPluginContext:
    """Čo plugin vidí z agenta. Všetko sú funkcie — plugin sa pýta vždy čerstvo."""

    def __init__(self, name: str, *, agent_name: str = "", hub_views: Any = None,
                 spool_roots: Callable[[], list[Any]] | None = None,
                 deployments: Callable[[], list[tuple[dict[str, Any], str]]] | None = None,
                 modes_changed: Callable[[], None] | None = None,
                 clock: Callable[[], float] = time.time, stopping: threading.Event | None = None) -> None:
        self.name = name
        #: meno agenta (`agent.json` → `name`), napr. „nas-win11“
        self.agent_name = agent_name
        #: pohľady pluginov hubu (`views()`, `view(plugin, view)`) alebo `None` bez hubu
        self.hub_views = hub_views
        self._spool_roots = spool_roots or (lambda: [])
        self._deployments = deployments or (lambda: [])
        self._modes_changed = modes_changed or (lambda: None)
        self.clock = clock
        #: nastaví sa pri zastavení agenta aj pred reloadom pluginu — čakanie v pluginu ide cez `stopping.wait`
        self.stopping = stopping or threading.Event()
        self.log = logging.getLogger(f"tester.hub.agent_plugins.{name}")

    def spool_roots(self) -> list[Any]:
        """Korene spoolu platforiem na tomto stroji (`tradebot.live.spool.default_roots`)."""
        return list(self._spool_roots())

    def deployments(self) -> list[tuple[dict[str, Any], str]]:
        """Aktívne nasadenia tohto stroja a výsledok reconcilera: `[(nasadenie, chyba)]` (prázdna = v poriadku)."""
        return list(self._deployments())

    def modes_changed(self) -> None:
        """Plugin zmenil režim inštancie (control súbor) — agent hneď znova zosúladí nasadenia s prekrytím."""
        self._modes_changed()


class AgentPlugin:
    """Základ pluginu. Balík `tester/hub/agent_plugins/<meno>/` vystaví `PLUGIN = <trieda>`."""

    #: zhodné s menom balíka (doplní host)
    name = ""
    title = ""
    #: sekundy medzi tickmi; 0 = plugin čaká sám (long-poll, `ctx.stopping.wait`)
    interval = 10.0

    def setup(self, ctx: AgentPluginContext) -> None:
        self.ctx = ctx

    def tick(self) -> None:
        """Jedno kolo práce; výnimka = chyba pluginu (host ju zapíše a o chvíľu skúsi znova)."""

    def status(self) -> dict[str, Any] | None:
        """Stav pre heartbeat a webapp (`live.plugins.<meno>`); `None` = plugin nič nehlási."""
        return None

    def overrides(self) -> list[dict[str, Any]]:
        """Režimy prepnuté lokálne (`[{instance, mode, ts, by}]`), ktoré hub ešte nemá v nasadení — agent ich
        drží v požadovanom stave a posiela hubu v `live.overrides`."""
        return []

    def drop_override(self, instance: str) -> None:
        """Hub prekrytie prevzal alebo prebil novším — zabudni ho."""

    def desired(self, desired: dict[str, Any], now: float) -> None:
        """Heartbeat priniesol požadovaný stav nasadení (kto čo zmenil, nový kód)."""

    def teardown(self) -> None:
        """Pred zastavením a pred reloadom; vlákno pluginu už nebeží."""
