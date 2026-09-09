"""Hyperopt priestor zadaný **plánom**, nie kódom v stratégii.

Freqtrade zisťuje, čo má ladiť, tak, že si po triede stratégie prejde atribúty a nájde
v nich objekty `IntParameter`/`DecimalParameter`/`CategoricalParameter`
(`freqtrade.strategy.hyper.detect_all_parameters`). Priestor je teda normálne súčasť
kódu — a tester, ktorý kód nepíše, si ho nemá ako zvoliť.

Tento modul ten krok obchádza: plán je JSON, cesta k nemu je v `TRADEBOT_HYPEROPT_PLAN`
a `TradebotStrategyBase.__init_subclass__` z neho pri importe triedy dorobí tie isté
objekty a prilepí ich na triedu. Freqtrade medzi „napísané v kóde" a „prilepené pri
importe" nerozlišuje, lebo sa pozerá až na hotovú triedu.

Plán vyzerá takto::

    {
      "strategy": "ibs",
      "goal": "winrate", "max_dd": 15.0, "min_trades": 20,
      "knobs": {
        "rrRatio":        {"low": 2, "high": 6, "step": 0.5},
        "slLookback":     {"low": 5, "high": 40},
        "minSlDistance":  {"low": 0.1, "high": 0.5, "unit": "pct"},
        "tradeDirection": {"choices": ["Long only", "Both"]}
      }
    }

Rozsah sa dá vynechať — vezme sa z `CONSTRAINTS` configu stratégie, teda z Pine, takže
`{}` znamená „celý povolený rozsah". Typ parametra sa berie z dataclass polí configu
(`int`, `float`, `bool`, `SizeSpec`, enum) — priestor si tak nedrží vlastnú tabuľku,
ktorá by sa mohla rozísť s tým, čo config naozaj prijme.

`goal`, `max_dd` a `min_trades` priestor neovplyvňujú; číta ich loss funkcia
(`deploy/freqtrade/user_data/hyperopts/TradebotPlanLoss.py`), aby bolo zadanie testera
na jednom mieste a nedalo sa rozísť.

Priestor má vlastné meno **`plan`**, nie `buy`/`sell`. Freqtrade vlastné mená priestorov
vie (`init_spaces` si ich vytiahne z `get_available_spaces`) a `--spaces plan` tak ladí
presne to, čo tester navolil — aj keby si niektorá stratégia priestor v kóde napísala,
do plánu sa nepomieša.

Čo o ladení vie **stratégia** (odporúčané parametre, pred čím varovať, väzby medzi
parametrami), je v jej vlastnej triede `hyperopt_cls`
(`tradebot/strategies/<key>/hyperopt.py`); tento modul si ju vyzdvihne z registry cez
`knowledge()` a menom žiadnu stratégiu nepozná.

**Krok znamená pri hyperopte len presnosť, nie mriežku.** Sweep skúša hodnoty, ktoré
vypíšeš; hyperopt hľadá spojito a `step` sa premietne na počet desatinných miest. Kto
chce presne dané hodnoty, patrí na sweep.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any

from tradebot.core.env import getenv
from tradebot.core.types import SizeSpec
from tradebot.strategies import StrategySpec, get_spec
from tradebot.strategies.hyperopt import StrategyHyperopt

__all__ = [
    "SPACE", "ATTR_PREFIX", "PLAN_ENV", "Knob", "Plan",
    "plan_from_env", "parameters", "install", "apply", "knob_kind", "tunable", "knowledge",
]

#: Meno hyperopt priestoru. Vlastné, aby `--spaces plan` neladil nič iné.
SPACE = "plan"

#: Predpona atribútu na triede: `rrRatio` -> `hp_rrRatio`.
ATTR_PREFIX = "hp_"

#: Premenná prostredia s cestou k plánu (`TRADEBOT_HYPEROPT_PLAN`).
PLAN_ENV = "HYPEROPT_PLAN"


# --------------------------------------------------------------------------- #
# typ a rozsah parametra — všetko z configu stratégie
# --------------------------------------------------------------------------- #


def knob_kind(name: str, spec: StrategySpec) -> tuple[str, dict[str, Any]]:
    """`("int" | "float" | "size" | "bool" | "enum", {rozsah/možnosti})` pre pole configu."""
    cls = spec.config_cls
    podla_mena = {f.name: f for f in fields(cls)}
    if name not in podla_mena:
        raise ValueError(f"stratégia {spec.key!r} parameter {name!r} nepozná")

    lo, hi = cls.CONSTRAINTS.get(name, (None, None))
    info: dict[str, Any] = {"low": lo, "high": hi}

    if name in cls.ENUM_FIELDS:
        info["choices"] = [e.value for e in cls.ENUM_FIELDS[name]]
        return "enum", info
    if name in cls.SIZE_FIELDS:
        info["unit"] = cls.SIZE_FIELDS[name]
        return "size", info

    typ = podla_mena[name].type
    meno_typu = typ if isinstance(typ, str) else getattr(typ, "__name__", str(typ))
    if "bool" in meno_typu:
        return "bool", info
    if "int" in meno_typu:
        return "int", info
    if "float" in meno_typu:
        return "float", info
    raise ValueError(f"{name}: typ {meno_typu} sa ladiť nedá (ladia sa čísla, prepínače a enumy)")


def knowledge(spec: StrategySpec) -> type[StrategyHyperopt]:
    """Trieda s vedomosťami stratégie o ladení — z registry, nie podľa mena.

    Stratégia, ktorá `hyperopt_cls` nedeklaruje, dostane základ: nič neodporúča, pred
    ničím nevaruje, žiadne väzby medzi parametrami. Ladiť sa dá aj tak.
    """
    return spec.hyperopt_cls or StrategyHyperopt


def tunable(spec: StrategySpec) -> list[str]:
    """Polia, ktoré sa dajú dať do plánu — čísla s rozsahom, prepínače a enumy.

    Parametre, ktoré rozbíjajú paritu s Pine, sa tu **neodfiltrujú**: tester ich smie
    ladiť, keď o to vyslovene stojí; označené sú v metadátach formulára.
    """
    out = []
    for f in fields(spec.config_cls):
        try:
            kind, info = knob_kind(f.name, spec)
        except ValueError:
            continue
        if kind in ("bool", "enum") or (info["low"] is not None and info["high"] is not None):
            out.append(f.name)
    return out


# --------------------------------------------------------------------------- #
# plán
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Knob:
    """Jeden ladený parameter: rozsah pre čísla, alebo zoznam možností."""

    name: str
    low: float | None = None
    high: float | None = None
    step: float | None = None
    choices: tuple[Any, ...] | None = None
    #: Jednotka veľkostného poľa (`abs`, `ticks`, `atr`, `pct`) — ladí sa číslo, nie jednotka.
    unit: str | None = None

    @property
    def attr(self) -> str:
        return ATTR_PREFIX + self.name


@dataclass(frozen=True)
class Plan:
    """Zadanie testera: čo ladiť a podľa čoho vyberať."""

    strategy: str = "ibs"
    knobs: tuple[Knob, ...] = ()
    goal: str = "break_even"
    max_dd: float | None = None
    min_trades: int | None = None
    note: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plan:
        strategy = data.get("strategy") or "ibs"
        spec = get_spec(strategy)
        raw = data.get("knobs") or {}
        if not raw:
            raise ValueError("plán nemá žiadny ladený parameter (knobs)")
        knobs = tuple(_knob(name, spec, opts or {}) for name, opts in raw.items())
        return cls(
            strategy=strategy,
            knobs=knobs,
            goal=data.get("goal") or "break_even",
            max_dd=_number(data.get("max_dd")),
            min_trades=int(data["min_trades"]) if data.get("min_trades") else None,
            note=data.get("note") or "",
            meta=data.get("meta") or {},
        )

    def to_dict(self) -> dict[str, Any]:
        knobs: dict[str, Any] = {}
        for k in self.knobs:
            if k.choices is not None:
                knobs[k.name] = {"choices": list(k.choices)}
            else:
                knobs[k.name] = {"low": k.low, "high": k.high, "step": k.step}
                if k.unit:
                    knobs[k.name]["unit"] = k.unit
        return {"strategy": self.strategy, "goal": self.goal, "max_dd": self.max_dd,
                "min_trades": self.min_trades, "note": self.note, "knobs": knobs,
                "meta": self.meta}

    @classmethod
    def load(cls, path: str | Path) -> Plan:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        return out


def _number(value: Any) -> float | None:
    return None if value is None or value == "" else float(value)


def _knob(name: str, spec: StrategySpec, opts: dict[str, Any]) -> Knob:
    kind, info = knob_kind(name, spec)

    if kind == "bool":
        zadane = opts.get("choices")
        return Knob(name, choices=tuple(zadane) if zadane else (False, True))

    if kind == "enum":
        moznosti = info["choices"]
        choices = list(opts.get("choices") or moznosti)
        nezname = [c for c in choices if c not in moznosti]
        if nezname:
            raise ValueError(f"{name}: neznáme hodnoty {nezname}; známe: {moznosti}")
        if len(choices) < 2:
            raise ValueError(f"{name}: na ladenie treba aspoň dve možnosti")
        return Knob(name, choices=tuple(choices))

    low, high = _number(opts.get("low")), _number(opts.get("high"))
    if low is None:
        low = _number(info["low"])
    if high is None:
        high = _number(info["high"])
    if low is None or high is None:
        raise ValueError(f"{name}: Pine rozsah nepoznáme, zadaj low a high")
    if low >= high:
        raise ValueError(f"{name}: dolná hranica {low:g} musí byť pod hornou {high:g}")
    if info["low"] is not None and low < float(info["low"]):
        raise ValueError(f"{name}: {low:g} je pod Pine rozsahom <{info['low']}, {info['high']}>")
    if info["high"] is not None and high > float(info["high"]):
        raise ValueError(f"{name}: {high:g} je nad Pine rozsahom <{info['low']}, {info['high']}>")

    unit = opts.get("unit") or info.get("unit")
    if kind == "size" and not unit:
        raise ValueError(f"{name}: veľkostné pole potrebuje jednotku (abs, ticks, atr, pct)")
    return Knob(name, low=low, high=high, step=_number(opts.get("step")), unit=unit)


_CACHE: dict[str, Plan] = {}


def plan_from_env() -> Plan | None:
    """Plán z `TRADEBOT_HYPEROPT_PLAN`, alebo `None`, keď premenná nie je.

    Číta sa raz — trieda sa importuje raz, ale `apply` beží každú epochu.
    """
    path = getenv(PLAN_ENV)
    if not path:
        return None
    if path not in _CACHE:
        _CACHE[path] = Plan.load(path)
    return _CACHE[path]


# --------------------------------------------------------------------------- #
# priestor pre Freqtrade
# --------------------------------------------------------------------------- #


def _decimals(step: float | None) -> int:
    """Krok testera na počet desatinných miest — `DecimalParameter` inú mriežku nevie."""
    if not step or step <= 0:
        return 2
    if step >= 1:
        return 0
    return min(6, max(1, int(math.ceil(-math.log10(step)))))


def parameters(plan: Plan) -> dict[str, Any]:
    """`{atribút: Parameter}` pre plán — presne to, čo by bolo napísané v triede."""
    from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter

    spec = get_spec(plan.strategy)
    defaults = spec.config_cls()
    out: dict[str, Any] = {}
    for knob in plan.knobs:
        kind, _ = knob_kind(knob.name, spec)
        if knob.choices is not None:
            base = getattr(defaults, knob.name, None)
            if isinstance(base, Enum):
                base = base.value
            default = base if base in knob.choices else knob.choices[0]
            out[knob.attr] = CategoricalParameter(list(knob.choices), default=default,
                                                 space=SPACE, optimize=True)
            continue

        stred = (knob.low + knob.high) / 2
        if kind == "int":
            out[knob.attr] = IntParameter(int(knob.low), int(knob.high), default=int(stred),
                                          space=SPACE, optimize=True)
        else:
            out[knob.attr] = DecimalParameter(knob.low, knob.high, default=stred,
                                              decimals=_decimals(knob.step),
                                              space=SPACE, optimize=True)
    return out


def install(cls: type, plan: Plan | None = None) -> list[str]:
    """Prilepí parametre plánu na triedu stratégie. Vráti mená atribútov.

    Volá sa z `__init_subclass__`, teda pri importe triedy — Freqtrade sa na atribúty
    pozerá až keď triedu dostane od resolvera, takže nevie, že tam neboli od začiatku.
    """
    plan = plan or plan_from_env()
    if plan is None or getattr(cls, "STRATEGY_KEY", None) != plan.strategy:
        return []
    attrs = parameters(plan)
    for attr, param in attrs.items():
        setattr(cls, attr, param)
    return list(attrs)


def apply(strategy: Any, plan: Plan) -> dict[str, Any]:
    """Hodnoty aktuálnej epochy do configu stratégie. Vráti, čo nastavila (na log)."""
    spec = get_spec(plan.strategy)
    nastavene: dict[str, Any] = {}
    for knob in plan.knobs:
        param = getattr(strategy, knob.attr, None)
        if param is None:          # plán inej stratégie, než ktorá práve beží
            continue
        hodnota = param.value
        kind, info = knob_kind(knob.name, spec)
        if kind == "int":
            hodnota = int(hodnota)
        elif kind == "size":
            hodnota = SizeSpec(value=float(hodnota), unit=knob.unit or info.get("unit") or "abs")
        elif kind == "float":
            hodnota = float(hodnota)
        setattr(strategy.tb_cfg, knob.name, hodnota)
        nastavene[knob.name] = hodnota
    # Väzby medzi parametrami vie len stratégia — hyperopt vyberá každý zvlášť.
    knowledge(spec).constrain(strategy.tb_cfg)
    return nastavene
