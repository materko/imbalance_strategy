"""Metadáta parametrov pre formulár — z balíka stratégie, nie z Pine.

Formulár skladá každé pole z dvoch zdrojov a ani jeden z nich nie je Pine:

* **popis** (skupina, titulok, tooltip, krok, `inline`) — `tradebot/strategies/<key>/params.py`,
  vyzdvihnuté cez `StrategySpec.param_meta` a `param_groups`;
* **typ, default, rozsah a hodnoty enumu** — priamo z configu stratégie (typy polí
  dataclass, `CONSTRAINTS`, `SIZE_FIELDS`, `ENUM_FIELDS`), takže sa formulár nemá ako
  rozísť s tým, čo config prijme.

Pine skript sa pre stratégiu vyrába **len na vyžiadanie** (aby sa dala pozrieť na
TradingView), takže formulár na ňom závisieť nesmie — stratégia bez Pine musí mať
plnohodnotný formulár. Že config sedí s Pine tam, kde Pine je, stráži test parity
(`tester/tests/test_pine_parity.py`), ktorý má vlastný parser.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from tradebot.core.types import SizeSpec
from tradebot.strategies import STRATEGIES, StrategySpec, get_spec
from tradebot.strategies.ibs import SPEC as IBS_SPEC

REPO = Path(__file__).resolve().parents[2]
#: Spätná kompatibilita — metadáta IBS bez argumentu.
REMOVED_INPUTS = IBS_SPEC.removed_inputs
FEATURES = IBS_SPEC.features
INERT_INPUTS = IBS_SPEC.inert_inputs

#: Pine vstupy, ktoré v configu ostali kvôli parite panela, ale v porte nerobia nič,
#: takže vo formulári len zavadzajú. V `IBSConfig` ostávajú, aby profil sedel s TV
#: panelom, a do uloženého profilu sa zapíšu s Pine defaultom.
#:
#: `alert*` posielali notifikáciu TradingView — vo Freqtrade notifikácie rieši sám
#: Freqtrade (Telegram) v live režime, v backteste nemajú význam.
#:
#: `showDashboard`, `showTradeLog`, `showDebugTable` a ich pozície/počty riadkov kreslili
#: tabuľky **na graf v TradingView**. Port ich nekreslí a ani nemá kam — históriu behov,
#: zoznam obchodov aj dôvody výstupu ukazuje webapp vo vlastných tabuľkách. Kresliaci
#: prepínač `showImbalance` medzi ne nepatrí: ten engine číta (`engine.py`) a rozhoduje,
#: či sa do kresieb behu dostanú imbalance boxy.
INERT_INPUTS = {
    "alertOnState2", "alertOnState3", "alertOnState4",
    "showDashboard", "dashPos", "dashboardRows",
    "showTradeLog", "tradeLogRows",
    "showDebugTable", "debugTableRows", "debugPos",
}

PORT_GROUP = "🧩 Rozšírenia portu (nie sú v Pine)"
OTHER_GROUP = "⚙️ Ostatné"


@dataclass
class ParamMeta:
    name: str
    type: str  # bool | int | float | string | color | size
    title: str
    group: str
    tooltip: str = ""
    default: Any = None
    options: list[str] | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    #: pre `size` polia: základná jednotka poľa z `config_cls.SIZE_FIELDS` — holé číslo
    #: v profile znamená práve ju (`abs`/`ticks`/`atr`/`pct`)
    base_unit: str | None = None
    inline: str | None = None
    #: pole, ktoré Pine skript sám nepoužíva (napr. state4MaxBars) alebo je len vizuálne
    note: str = ""
    #: prepínače, z ktorých aspoň jeden musí byť zapnutý, aby malo pole zmysel (viď FEATURES)
    depends_on: list[str] | None = None
    #: kresliaci prepínač feature, ktorú toto pole zapína (zrkadlí sa vedľa neho)
    show_param: str | None = None
    #: zmena tohto poľa rozbije paritu s Pine (sizing, STATE timeouty). Ladiť sa dá,
    #: ale výsledok sa už nedá porovnať s TradingView — formulár aj sweep to povedia.
    breaks_parity: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _declared(spec: StrategySpec) -> dict[str, ParamMeta]:
    """Popisy, ktoré o sebe stratégia povedala (`params.py`), ako `ParamMeta`."""
    out: dict[str, ParamMeta] = {}
    for name, row in (spec.param_meta or {}).items():
        out[name] = ParamMeta(
            name=name,
            type=row.get("type", "string"),
            title=row.get("title", name),
            group=row.get("group") or OTHER_GROUP,
            tooltip=row.get("tooltip", ""),
            options=list(row["options"]) if row.get("options") else None,
            min=row.get("min"),
            max=row.get("max"),
            step=row.get("step"),
            inline=row.get("inline"),
        )
    return out


def _group_order(spec: StrategySpec) -> list[str]:
    """Skupiny v poradí, v akom ich stratégia deklarovala; zvyšné na koniec."""
    order = [g for g in spec.param_groups]
    order.append(OTHER_GROUP)
    order.append(PORT_GROUP)
    return order


def param_metadata(spec: StrategySpec | str | None = None) -> list[dict[str, Any]]:
    """Jeden záznam na každé pole configu stratégie, v poradí skupín stratégie.

    Default je default configu (= `config_cls()`), nie hodnota z profilu — profil sa
    do formulára načíta zvlášť a formulár zvýrazní odchýlky. Bez argumentu IBS.

    Pole bez popisu v `params.py` dostane holý názov ako titulok a skončí v „Ostatné".
    Nie je to výnimka, ktorá by sa mala využívať — stráži to `test_registry.py`.
    """
    if spec is None:
        spec = IBS_SPEC
    elif isinstance(spec, str):
        spec = get_spec(spec)
    cls = spec.config_cls
    declared = _declared(spec)
    defaults = cls()
    cfg_fields = {f.name: f for f in fields(cls)}
    order = {g: i for i, g in enumerate(_group_order(spec))}

    metas: list[ParamMeta] = []
    for name in cfg_fields:
        if name in spec.removed_inputs or name in spec.inert_inputs:
            continue
        default = getattr(defaults, name)
        meta = declared.get(name) or ParamMeta(name=name, type="string", title=name, group=OTHER_GROUP)
        # typ podľa configu, nie podľa popisu — SizeSpec a enumy sú iné
        if isinstance(default, SizeSpec):
            meta.type = "size"
            meta.base_unit = cls.SIZE_FIELDS[name]
            meta.default = default.value if default.unit == meta.base_unit else default.to_json()
        elif isinstance(default, bool):
            meta.type = "bool"
            meta.default = default
        elif isinstance(default, int):
            meta.type = "int"
            meta.default = default
        elif isinstance(default, float):
            meta.type = "float"
            meta.default = default
        elif default is None:
            # voliteľné pole (napr. tickDollarValue): typ deklaruje `params.py`, inak text
            meta.type = meta.type if meta.type in ("int", "float", "bool", "string") else "string"
            meta.default = None
        else:
            v = getattr(default, "value", default)
            meta.type = "color" if meta.type == "color" else "string"
            meta.default = v
        if name in cls.CONSTRAINTS and meta.min is None:
            meta.min, meta.max = cls.CONSTRAINTS[name]
        # Hodnoty enumu sú v samotnom enume; opakovať ich v popise by znamenalo dve
        # pravdy o tom, čo config prijme.
        if not meta.options and name in cls.ENUM_FIELDS:
            meta.options = [e.value for e in cls.ENUM_FIELDS[name]]
        if name in spec.param_notes:
            meta.note = spec.param_notes[name]
        if name in cls.PORT_ONLY_FIELDS:
            meta.group = PORT_GROUP
        if name in spec.parity_fields:
            meta.breaks_parity = True
        metas.append(meta)

    by_name = {m.name: m for m in metas}
    for feat in spec.features:
        for name in feat["params"]:
            by_name[name].depends_on = list(feat["switches"])
        if feat.get("show"):
            by_name[feat["switches"][0]].show_param = feat["show"]

    metas.sort(key=lambda m: (order.get(m.group, 999), 0))
    return [m.to_dict() for m in metas]


def strategy_meta(spec: StrategySpec) -> dict[str, Any]:
    """Balík pre prehliadač: metadáta polí a Pine defaulty jednej stratégie."""
    return {"params": param_metadata(spec), "defaults": spec.config_cls().to_dict()}


def groups(spec: StrategySpec | str | None = None) -> list[str]:
    seen: list[str] = []
    for m in param_metadata(spec):
        if m["group"] not in seen:
            seen.append(m["group"])
    return seen
