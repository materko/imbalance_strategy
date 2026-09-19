"""Profily stratégie z repozitára a ich popisy pre formulár (vlastné profily
testera sú v `profiles.py`).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.strategies import get_spec

from . import profiles


def default_params(profile: "str | Path | None" = None, strategy: str = "ibs",
                   engine: str | None = None) -> tuple[dict[str, Any], str | None]:
    """Parametre formulára: Pine defaulty stratégie, profil z jej priečinka, vlastný profil testera
    alebo cesta k JSON v repozitári (archív profilov).

    `engine` doplní hodnoty z bloku `_engine_overrides` profilu, aby tester videl vo
    formulári presne to, s čím sa beh spustí."""
    if profile:
        cfg, inst = load_profile(profiles.resolve(profile, strategy), strategy=strategy, engine=engine)
        key = next(k for k, v in INSTRUMENTS.items() if v is inst)
        return cfg.to_dict(), key
    return get_spec(strategy).config_cls().to_dict(), None


def list_profiles(strategy: str = "ibs") -> list[str]:
    """Profily repozitára stratégie a za nimi vlastné profily testera tej istej stratégie."""
    return profiles.all_names(strategy)


def _profile_key(strategy: str, key: str) -> dict[str, str]:
    """Hodnota kľúča z každého profilu (repozitár aj vlastné); bez neho ostane prázdno."""
    out = {}
    for name, path in profiles.all_paths(strategy).items():
        try:
            out[name] = str(json.loads(path.read_text(encoding="utf-8")).get(key) or "")
        except (OSError, json.JSONDecodeError):
            out[name] = ""
    return out


def profile_instruments(strategy: str = "ibs") -> dict[str, str]:
    """`_instrument` z profilu — aby stránka vedela, ktorý profil sedí na ktorý pár."""
    return _profile_key(strategy, "_instrument")


def profile_titles(strategy: str = "ibs") -> dict[str, str]:
    """`_title` z profilu — ľudský popis do dropdownu (bez neho ostane názov súboru)."""
    return {name: title or name for name, title in _profile_key(strategy, "_title").items()}


def profile_info(strategy: str = "ibs") -> dict[str, dict[str, str]]:
    """Ku každému profilu: kedy vznikol, pár, TF a popis — stránka z toho skladá názov
    „dátum · pár TF · popis". Vlastný profil bez `_created` (starší) dostane čas súboru;
    profil repozitára dátum nemá (čas súboru je čas checkoutu, nie vzniku)."""
    vlastne = set(profiles.user_names(strategy))
    out: dict[str, dict[str, str]] = {}
    for name, path in profiles.all_paths(strategy).items():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        created = str(data.get("_created") or "")
        if not created and name in vlastne:
            created = datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        inst = INSTRUMENTS.get(str(data.get("_instrument") or ""))
        out[name] = {"created": created, "pair": inst.symbol if inst else "",
                     "timeframe": str(data.get("_timeframe") or ""),
                     "title": str(data.get("_title") or "")}
    return out
