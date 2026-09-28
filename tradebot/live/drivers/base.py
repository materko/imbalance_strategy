"""Driver platformy na strane agenta (docs/LIVE.md, fáza 2b) — jediné miesto, ktoré pozná platformu.

Hub a reconciler (`tradebot.live.apply`) pracujú s **účtami** a **nasadeniami** ako s dátami;
čo z nich urobiť na disku a v procese platformy (profil, control súbor, terminál s grafmi), vie
len driver. Jedna trieda na platformu, `load_drivers()` vráti tie, ktorých platforma na stroji je.

Účet a nasadenie prichádzajú z heartbeatu ako JSON; `Account.from_dict` / `Deployment.from_dict`
ich prevedú na dataclassy s doplnenými predvolenými hodnotami (chýbajúce pole nie je chyba).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..schema import CONTROL_MODES, instance_id, instance_symbol

__all__ = ["Account", "Deployment", "Driver", "load_drivers", "DRIVER_MODULES"]

log = logging.getLogger(__name__)

#: Moduly driverov — každý má `DRIVER` (inštancia `Driver`). Pridanie platformy = riadok sem.
DRIVER_MODULES = ("tradebot.live.drivers.mt5", "tradebot.live.drivers.ninjatrader")


@dataclass
class Account:
    id: str
    platform: str
    label: str = ""
    login: str = ""
    server: str = ""
    terminal: str = ""
    portable: bool = False
    #: Heslo, ktoré hub nesie, kým ho agent neprevezme (`secret_pending`); po `store_secret` sa acknu.
    secret: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Account":
        return cls(id=str(d.get("id") or ""), platform=str(d.get("platform") or ""),
                   label=str(d.get("label") or ""), login=str(d.get("login") or ""),
                   server=str(d.get("server") or ""), terminal=str(d.get("terminal") or ""),
                   portable=bool(d.get("portable")), secret=(str(d["secret"]) if d.get("secret") else None),
                   raw=dict(d))


@dataclass
class Deployment:
    id: str
    account: str
    strategy: str
    symbol: str
    tf: int
    profile: str
    config: dict[str, Any] = field(default_factory=dict, repr=False)
    config_hash: str = ""
    mode: str = "enabled"
    active: bool = True
    #: Id inštancie (adresár spoolu) — hub ho odvodí; keď chýba, dopočíta ho driver (`instance_of`).
    instance: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Deployment":
        try:
            tf = int(d.get("tf") or 0)
        except (TypeError, ValueError):
            tf = 0
        mode = str(d.get("mode") or "enabled")
        return cls(id=str(d.get("id") or ""), account=str(d.get("account") or ""),
                   strategy=str(d.get("strategy") or ""), symbol=str(d.get("symbol") or ""), tf=tf,
                   profile=str(d.get("profile") or ""), config=dict(d.get("config") or {}),
                   config_hash=str(d.get("config_hash") or ""), mode=mode if mode in CONTROL_MODES else "enabled",
                   active=bool(d.get("active", True)), instance=str(d.get("instance") or ""), raw=dict(d))

    def validate(self) -> None:
        """Bez stratégie, symbolu, TF a profilu sa nasadenie nedá zapísať — chyba k nasadeniu, nie pád."""
        chyby = []
        if not self.strategy:
            chyby.append("stratégia")
        if not self.symbol:
            chyby.append("symbol")
        if self.tf <= 0:
            chyby.append("tf")
        if not self.profile:
            chyby.append("profil")
        if any(ch in self.profile for ch in "/\\") or self.profile in (".", ".."):
            chyby.append(f"profil {self.profile!r} nesmie byť cesta")
        if chyby:
            raise ValueError("nasadenie nemá: " + ", ".join(chyby))


class Driver(ABC):
    """Jedna platforma. Každá metóda smie vyhodiť výnimku — reconciler ju premení na `status: error`
    k danému nasadeniu (alebo účtu) a ostatné nasadenia idú ďalej."""

    platform: str = ""

    @abstractmethod
    def available(self) -> bool:
        """Je platforma na tomto stroji? Len dostupné drivery sa hlásia hubu (`drivers` v heartbeate)."""

    @abstractmethod
    def store_secret(self, account: Account, password: str) -> None:
        """Heslo účtu na disk agenta (DPAPI); platforma bez hesla (NinjaTrader) = no-op."""

    @abstractmethod
    def ensure_profile(self, deployment: Deployment) -> Path:
        """Snímka configu z nasadenia → profil na disku platformy pod názvom `deployment.profile`.
        Idempotentné: rovnaký obsah sa neprepisuje."""

    @abstractmethod
    def write_control(self, deployment: Deployment) -> Path:
        """`control/<instance>.json` s režimom a profilom nasadenia; nezmenený obsah sa neprepisuje
        (adaptér číta podľa mtime, každý zápis by bol pre neho nová správa)."""

    @abstractmethod
    def ensure_instance(self, account: Account, deployments: list[Deployment]) -> None:
        """Platforma beží a má presne tieto (aktívne) inštancie účtu — nič navyše, nič nechýba.
        Volá sa každé kolo; keď sedí, nesmie nič reštartovať."""

    @abstractmethod
    def remove_instance(self, account: Account, deployment: Deployment) -> None:
        """Nasadenie sa ruší (`active: false`, zmizlo z hubu, alebo zmenilo id inštancie): control súbor
        sa **nemaže hneď** (adaptér berie chýbajúci ako `enabled`), prepne sa na `paused` a odloží;
        graf/inštanciu odoberie nasledujúci `ensure_instance` bez neho a až po jej zastavení control zmaže."""

    @abstractmethod
    def status(self, account: Account) -> dict[str, Any]:
        """Beží proces? Ktoré inštancie má? — pre `live_status` agenta a webapp."""

    # -- kód platformy (docs/LIVE.md, fáza 2c) --------------------------------- #

    def installed_version(self) -> str | None:
        """Z akého commitu je kód TradeBotu na platforme nainštalovaný (`installed.json` vedľa kódu,
        píše ho `install`); `None` = marker nie je (ručná inštalácia spred fázy 2c, alebo nikdy)."""
        return None

    def install_code(self, version: str, accounts: list[Account]) -> dict[str, Any]:
        """Nasadí kód TradeBotu z tohto klonu na platformu (jadro, adaptér, šablóny, profily), preloží,
        čo platforma prekladať potrebuje, a zapíše `installed.json` s `version`. Bežiace inštancie
        účtov `accounts` smie zavrieť (MT5 drží DLL); ich opätovný štart je vec `ensure_instance`
        v ďalšom kole reconcilera. Vráti, čo urobil (`dict`, ide do heartbeatu); chyba = výnimka."""
        raise NotImplementedError(f"driver {self.platform!r} nevie nasadiť kód")

    def instance_of(self, account: Account, deployment: Deployment) -> str:
        """Id inštancie tak, ako ho počíta platforma (`LiveSpool.InstanceId`); hub ho posiela hotové,
        toto je záloha pre starý hub alebo ručné volanie."""
        return deployment.instance or instance_id(self.platform, self.spool_account(account),
                                                  instance_symbol(self.platform, deployment.symbol),
                                                  deployment.tf, deployment.strategy)

    def spool_account(self, account: Account) -> str:
        """Ako sa účet volá v spoole (MT5 `<login>-<server>`, NT meno účtu) — prebíja driver."""
        return account.login


def load_drivers(modules: tuple[str, ...] = DRIVER_MODULES) -> dict[str, Driver]:
    """Drivery, ktorých platforma je na stroji (`available()`), podľa kľúča platformy. Modul, ktorý sa
    nedá naimportovať alebo padne v `available()`, sa preskočí s varovaním — jedna platforma nesmie
    zhodiť agenta kvôli druhej."""
    import importlib

    out: dict[str, Driver] = {}
    for name in modules:
        try:
            mod = importlib.import_module(name)
            driver: Driver = getattr(mod, "DRIVER")
            if driver.available():
                out[driver.platform] = driver
        except Exception as exc:  # noqa: BLE001 - chýbajúca platforma nie je chyba agenta
            log.warning("live drivers: %s sa nedá použiť: %s: %s", name, type(exc).__name__, exc)
    return out
