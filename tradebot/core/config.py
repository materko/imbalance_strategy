"""Generická báza configu stratégie a načítavanie profilov.

Každá stratégia má vlastný `@dataclass` config odvodený od `StrategyConfig`. Názvy polí
sú zhodné s Pine identifikátormi stratégie (viď `tradebot/strategies/ibs/config.py`),
tabuľky `SIZE_FIELDS`, `ENUM_FIELDS`, `CONSTRAINTS` a `PORT_ONLY_FIELDS` sú atribúty
triedy — báza podľa nich dotypuje hodnoty, kontroluje rozsahy a serializuje.

Profil = JSON s odchýlkami od Pine defaultov plus metakľúče `_strategy`, `_instrument`,
`_title`, `_comment`. Profily žijú v `tradebot/configs/<stratégia>/`; načítať sa dajú
menom (`"ibs/golden_binance_btcusdt_3m"`, alebo holé meno s argumentom `strategy`)
alebo cestou k súboru (napr. archív v `docs/profily_archiv/<stratégia>/`).
"""

from __future__ import annotations

import json
from dataclasses import fields
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Iterable

from .types import INSTRUMENTS, InstrumentSpec, SizeSpec, SizeUnit

__all__ = [
    "StrategyConfig",
    "ConfigError",
    "CONFIGS_ROOT",
    "DEFAULT_STRATEGY",
    "META_KEYS",
    "load_profile",
    "list_profiles",
    "profile_path",
]

#: Koreň profilov; každá stratégia má vlastný podpriečinok.
CONFIGS_ROOT = Path(__file__).resolve().parent.parent / "configs"

#: Stratégia, ktorá sa použije, keď meno profilu ani JSON stratégiu neuvádza.
DEFAULT_STRATEGY = "ibs"

#: Kľúče v JSON profile, ktoré nie sú parametre stratégie.
META_KEYS = frozenset({"_comment", "_instrument", "_title", "_strategy"})


class ConfigError(ValueError):
    """Config je nekonzistentný alebo mimo rozsahu, ktorý Pine povoľuje."""


class StrategyConfig:
    """Báza pre config stratégie. Podtrieda je `@dataclass` a nastaví tabuľky nižšie."""

    #: `SizeSpec` polia a ich pôvodná Pine jednotka (holé číslo v JSON = Pine správanie).
    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = {}
    #: Polia, ktoré sa držia ako enum, nie ako holý reťazec.
    ENUM_FIELDS: ClassVar[dict[str, type]] = {}
    #: Rozsahy z Pine `minval`/`maxval` — kontrolujú sa len v Pine jednotke poľa.
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {}
    #: Polia, ktoré Pine nemá (rozšírenia portu).
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = frozenset()

    # ------------------------------------------------------------------ #
    # Dotypovanie a validácia
    # ------------------------------------------------------------------ #

    def __post_init__(self) -> None:
        for name in type(self).ENUM_FIELDS:
            setattr(self, name, getattr(self, name))
        for name in type(self).SIZE_FIELDS:
            setattr(self, name, getattr(self, name))
        self.validate()

    def __setattr__(self, name: str, value: object) -> None:
        """Dotypuje enum a `SizeSpec` polia aj pri priradení po vytvorení.

        Bez toho by `cfg.imbMaxDistTicks = 4` nechalo v poli obyčajný int a spadlo
        by to až hlboko v engine na `.resolve(...)` — presne ten druh tichej chyby,
        ktorej sa v tomto porte vyhýbame.
        """
        cls = type(self)
        if name in cls.SIZE_FIELDS:
            value = SizeSpec.parse(value, default_unit=cls.SIZE_FIELDS[name])
        elif name in cls.ENUM_FIELDS:
            value = cls.ENUM_FIELDS[name](value)
        object.__setattr__(self, name, value)

    def validate(self) -> None:
        problems = [*self._generic_problems(), *self._problems()]
        if problems:
            raise ConfigError("Neplatný config:\n  - " + "\n  - ".join(problems))

    def _generic_problems(self) -> Iterable[str]:
        cls = type(self)
        for name, (lo, hi) in cls.CONSTRAINTS.items():
            raw = getattr(self, name)
            if raw is None:  # voliteľné pole (napr. tickDollarValue)
                continue
            if isinstance(raw, SizeSpec):
                if raw.unit != cls.SIZE_FIELDS[name]:
                    # iná jednotka než Pine — rozsah z Pine tu neplatí
                    if raw.value < 0:
                        yield f"{name} musí byť >= 0, je {raw.value}"
                    continue
                raw = raw.value
            if not (lo <= raw <= hi):
                yield f"{name}={raw} je mimo rozsahu Pine <{lo}, {hi}>"

    def _problems(self) -> Iterable[str]:
        """Pravidlá konkrétnej stratégie (konzistencia seáns, entry modelov…)."""
        return ()

    def check_instrument(self, inst: InstrumentSpec) -> list[str]:
        """Varovania (nie chyby) k dvojici config × inštrument."""
        warnings: list[str] = []
        if inst.venue not in ("CME", "test"):
            abs_fields = [n for n in type(self).SIZE_FIELDS if getattr(self, n).unit == "abs"]
            if abs_fields:
                warnings.append(
                    f"{', '.join(sorted(abs_fields))} sú v absolútnych cenových bodoch — tie hodnoty "
                    f"nemusia na {inst.symbol} dávať zmysel; zváž unit='atr'."
                )
        return warnings

    # ------------------------------------------------------------------ #
    # Serializácia
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        unknown = set(data) - known - META_KEYS
        if unknown:
            raise ConfigError(f"neznáme kľúče v configu: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json(cls, path: str | Path):
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        size_fields = type(self).SIZE_FIELDS
        for f in fields(self):  # type: ignore[arg-type]
            v = getattr(self, f.name)
            if isinstance(v, SizeSpec):
                out[f.name] = v.value if v.unit == size_fields[f.name] else v.to_json()
            elif isinstance(v, Enum):
                out[f.name] = v.value
            else:
                out[f.name] = v
        return out

    def to_json(self, path: str | Path, *, comment: str | None = None) -> None:
        data = self.to_dict()
        if comment:
            data = {"_comment": comment, **data}
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")


# --------------------------------------------------------------------------- #
# Profily
# --------------------------------------------------------------------------- #


def _spec(strategy: str):
    from ..strategies import STRATEGIES  # lokálny import — stratégie importujú core

    if strategy not in STRATEGIES:
        raise ConfigError(f"neznáma stratégia {strategy!r}; známe: {sorted(STRATEGIES)}")
    return STRATEGIES[strategy]


def profile_path(strategy: str, name: str) -> Path:
    return CONFIGS_ROOT / strategy / f"{name}.json"


def list_profiles(strategy: str = DEFAULT_STRATEGY) -> list[str]:
    """Mená JSON profilov stratégie v `tradebot/configs/<stratégia>/`."""
    return sorted(p.stem for p in (CONFIGS_ROOT / strategy).glob("*.json"))


def load_profile(name: str | Path, *, strategy: str | None = None):
    """Načíta profil a vráti `(config, InstrumentSpec)`.

    `name` je `"<stratégia>/<profil>"`, holé meno profilu (stratégia z argumentu,
    inak `DEFAULT_STRATEGY`) alebo cesta k JSON súboru. Kľúč `_strategy` v súbore má
    prednosť; nezhoda s argumentom je chyba, aby sa profil nenačítal do cudzej triedy.
    """
    path = Path(name)
    if path.suffix:
        pass  # cesta k súboru
    elif "/" in str(name):
        strat, _, base = str(name).partition("/")
        if strategy is not None and strategy != strat:
            raise ConfigError(f"profil {name!r} patrí stratégii {strat!r}, nie {strategy!r}")
        strategy, path = strat, profile_path(strat, base)
    else:
        path = profile_path(strategy or DEFAULT_STRATEGY, str(name))
    if not path.exists():
        raise ConfigError(
            f"profil {path} neexistuje; dostupné pre {strategy or DEFAULT_STRATEGY}: "
            f"{list_profiles(strategy or DEFAULT_STRATEGY)}"
        )

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    declared = data.get("_strategy")
    if declared is not None and strategy is not None and declared != strategy:
        raise ConfigError(f"{path.name}: _strategy={declared!r} nesedí so stratégiou {strategy!r}")
    spec = _spec(declared or strategy or DEFAULT_STRATEGY)

    inst_key = data.get("_instrument")
    if inst_key is None:
        raise ConfigError(f"{path.name}: chýba kľúč '_instrument'")
    if inst_key not in INSTRUMENTS:
        raise ConfigError(
            f"{path.name}: neznámy _instrument {inst_key!r}; známe: {sorted(INSTRUMENTS)}"
        )
    return spec.config_cls.from_dict(data), INSTRUMENTS[inst_key]
