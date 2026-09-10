"""Popis stratégie pre registry — čo o nej potrebujú adaptéry, webapp a testy."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..core.config import StrategyConfig
from ..core.types import InstrumentSpec

#: Koreň repozitára (deploy/, docs/).
REPO = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ChartLayer:
    """Vrstva v grafe páru vo webapp: prepínač, ktorý zapína skupinu druhov kresieb."""

    id: str
    title: str
    kinds: tuple[str, ...]
    swatch: str
    #: druhy z `kinds`, ktoré sa nekreslia ako box, ale ako dutá sviečka (IBS imbalance)
    hollow_kinds: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "kinds": list(self.kinds), "sw": self.swatch,
                "hollow_kinds": list(self.hollow_kinds)}


@dataclass(frozen=True, eq=False)
class StrategySpec:
    """Jedna stratégia v registry.

    Povinné je meno, config a profily; ostatné polia dopĺňajú adaptéry (engine, názvy
    tried vo Freqtrade a MultiCharts, HTF feeder) a webapp (Pine súbor pre metadáta
    formulára, závislosti prepínačov, vrstvy grafu).
    """

    key: str
    title: str
    config_cls: type[StrategyConfig]
    profile_dir: Path
    default_profile: str
    #: Popisy parametrov pre formulár webapp: `pole -> {group, title, tooltip, …}`
    #: (`tradebot/strategies/<key>/params.py`). Je to **jediný** zdroj titulkov a tooltipov —
    #: Pine skript vzniká len na vyžiadanie a formulár na ňom nesmie závisieť. Rozsahy
    #: a defaulty sem nepatria: tie sú v configu a formulár si ich vyzdvihne odtiaľ.
    param_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Poradie skupín vo formulári (tak, ako ich vidí tester zhora nadol).
    param_groups: tuple[str, ...] = ()
    #: Pine zdroj — aby sa dala tá istá stratégia pozrieť na TradingView. **Voliteľný**:
    #: robí sa na vyžiadanie a keď je, `pine_input_count` stráži parser testu parity.
    pine_path: Path | None = None
    pine_input_count: int = 0
    #: Pine vstupy, ktoré sa vedome neportujú, a polia, kde sa default vedome líši.
    removed_inputs: frozenset[str] = frozenset()
    #: Pine vstupy, ktoré v configu ostávajú (parita panela), ale v porte nič nerobia — formulár ich neponúka.
    inert_inputs: frozenset[str] = frozenset()
    intentional_default_diffs: frozenset[str] = frozenset()
    #: závislosti prepínač -> podnastavenia (viď tradebot/strategies/ibs/meta.py)
    features: tuple[dict[str, Any], ...] = ()
    #: poznámky k poliam (napr. „Pine tento parameter nepoužíva")
    param_notes: dict[str, str] = field(default_factory=dict)
    #: polia, ktorých zmena rozbije paritu s Pine (sizing, časovanie prevzaté z TradingView).
    #: Formulár aj sweep na ne upozornia, ale nezakážu ich — je to rozhodnutie testera.
    parity_fields: frozenset[str] = frozenset()
    #: vrstvy grafu a ľudské názvy druhov kresieb
    layers: tuple[ChartLayer, ...] = ()
    #: Ktorý druh kresby nesie SL a TP úroveň obchodu. Analytika z nich počíta skutočnú
    #: vzdialenosť stopu a plánovaný RR — v `trades.json` je len to, čo Freqtrade nakoniec
    #: urobil, nie plán, ktorý engine vypočítal. Bez týchto mien sa tie dve vlastnosti
    #: jednoducho nepočítajú.
    sl_kind: str = ""
    tp_kind: str = ""
    #: Pole configu s dolárovým rizikom na obchod (IBS `maxLossDollar`, demo `riskDollar`).
    #: Monte Carlo z neho preškáluje obchody na iný účet — bez neho vie beh len premiešať.
    risk_field: str = ""
    #: Prepínač, ktorý sizing prepne na pevný počet kontraktov (IBS `legacyPineSizing`).
    #: Taký beh sa na iné riziko prepočítať nedá, aj keď `risk_field` v configu je.
    fixed_size_field: str = ""
    kind_titles: dict[str, str] = field(default_factory=dict)
    #: TF grafu, na ktorom stratégia bežala v TradingView
    default_timeframe: str = "3m"
    #: engine: (cfg, inst, chart_tf_minutes) -> Engine
    engine_factory: Callable[[StrategyConfig, InstrumentSpec, int], Any] | None = None
    #: názvy tried v adaptéroch (shim vo Freqtrade user_data, šablóna v MultiCharts)
    freqtrade_class: str = ""
    multicharts_class: str = ""
    #: názov šablóny študie v deploy/multicharts/ (kopíruje sa do PowerLanguage editora)
    multicharts_template: str = ""
    #: informatívne TF, ktoré adaptér musí dodať (Freqtrade informative pairs, MC Data2)
    informative_tfs: Callable[[StrategyConfig], list[str]] | None = None
    #: (cfg, chart_tf_minutes) -> feeder s `load/feed/window_for`, alebo None (engine bez HTF)
    htf_feeder: Callable[[StrategyConfig, int], Any] | None = None
    #: Čo o ladení vie stratégia: odporúčané parametre, varovania, väzby medzi
    #: parametrami (`tradebot/strategies/<key>/hyperopt.py`). Generický hyperopt si ju
    #: vyzdvihne odtiaľto, menom ju nepozná; bez nej platí základ `StrategyHyperopt`.
    hyperopt_cls: type | None = None

    def public(self) -> dict[str, Any]:
        """Čo o stratégii dostane prehliadač."""
        return {
            "key": self.key,
            "title": self.title,
            "default_timeframe": self.default_timeframe,
            "layers": [layer.to_dict() for layer in self.layers],
            "kind_titles": dict(self.kind_titles),
        }
