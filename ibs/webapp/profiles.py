"""Vlastné profily testera — JSON v `user_data/profiles/`, vedľa histórie behov.

Profily v `ibs/configs/` sú kód repozitára: držia paritu s Pine, ukazujú na ne testy
a dokumenty s meraniami, takže ich tester nesmie premenovať ani zmazať. Čo si uloží
z vlastného behu, patrí k jeho dátam — ide do gitu spolu s `runs/` cez Push, dá sa
premenovať aj zmazať a nikdy neprepíše profil z repozitára.

Formát je rovnaký ako pri profiloch repozitára: **len odchýlky** od Pine defaultov
plus kľúč `_instrument`. Vďaka tomu je diff čitateľný a profil prežije aj to, keď sa
niekedy zmení Pine default (posunie sa s ním). Navyše nastavenia behu, bez ktorých
by profil povedal „ako", ale nie „na čom": `_timeframe` (limity `*MaxBars` sú v baroch,
takže TF patrí k nastaveniu), `_timerange`, `_fee`, `_wallet` a `_detail`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..core import IBSConfig
from ..core.config import CONFIG_DIR, ConfigError
from ..core.types import INSTRUMENTS

REPO = Path(__file__).resolve().parents[2]
PROFILES_DIR = REPO / "platforms" / "freqtrade" / "user_data" / "profiles"

#: Meno profilu je zároveň meno súboru — bez ciest, medzier a diakritiky.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,47}$")


class ProfileError(ValueError):
    """Neplatné meno, kolízia s profilom repozitára alebo pokus zmeniť cudzí profil."""


def _dir() -> Path:
    # PROFILES_DIR sa číta až tu, aby sa dal v testoch prepnúť
    return Path(PROFILES_DIR)


def builtin_names() -> list[str]:
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json"))


def user_names() -> list[str]:
    d = _dir()
    return sorted(p.stem for p in d.glob("*.json")) if d.exists() else []


def all_names() -> list[str]:
    return builtin_names() + user_names()


def all_paths() -> dict[str, Path]:
    """Meno profilu → súbor; profil repozitára má prednosť pred rovnako nazvaným vlastným."""
    out = {p.stem: p for p in sorted(CONFIG_DIR.glob("*.json"))}
    d = _dir()
    if d.exists():
        for p in sorted(d.glob("*.json")):
            out.setdefault(p.stem, p)
    return out


def is_user(name: str) -> bool:
    return name in user_names()


def path_for(name: str) -> Path:
    """Cesta k vlastnému profilu (nemusí existovať)."""
    check_name(name)
    return _dir() / f"{name}.json"


def resolve(name: "str | Path") -> Path:
    """Cesta k profilu podľa mena — najprv repozitár, potom vlastné profily.

    Hotová cesta (archív profilov v `docs/`) prejde nedotknutá.
    """
    if isinstance(name, Path) or "/" in str(name) or str(name).endswith(".json"):
        return Path(name)
    builtin = CONFIG_DIR / f"{name}.json"
    if builtin.exists():
        return builtin
    if NAME_RE.match(name or ""):
        own = _dir() / f"{name}.json"
        if own.exists():
            return own
    raise ConfigError(f"profil {name!r} neexistuje; dostupné: {all_names()}")


def check_name(name: str) -> str:
    name = (name or "").strip()
    if not NAME_RE.match(name):
        raise ProfileError(
            f"neplatné meno profilu {name!r}: 2–48 znakov, len písmená bez diakritiky, "
            "číslice, '.', '-' a '_'"
        )
    if name in builtin_names():
        raise ProfileError(f"{name} je profil repozitára — vyber si iné meno")
    return name


def deviations(params: dict[str, Any]) -> dict[str, Any]:
    """Len to, čo sa líši od Pine defaultov — rovnako ako profily v `ibs/configs/`."""
    defaults = IBSConfig().to_dict()
    return {k: v for k, v in params.items() if not k.startswith("_") and defaults.get(k) != v}


#: Nastavenia behu, ktoré k profilu patria — bez nich by profil povedal „ako", ale
#: nie „na čom". Ukladajú sa s podtržníkom, aby ich `IBSConfig` prešiel ako metadáta.
SETTING_KEYS = ("timeframe", "timerange", "fee", "wallet", "detail")


def settings_of(name: str) -> dict[str, Any]:
    """Nastavenia behu uložené v profile (`_timeframe`, `_timerange`, `_fee`…).

    Čo profil nemá, v slovníku nie je — formulár tú položku nechá, ako ju má tester.
    """
    path = all_paths().get(name)
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out = {k: data[f"_{k}"] for k in SETTING_KEYS if data.get(f"_{k}") is not None}
    return out


def save(name: str, params: dict[str, Any], instrument: str, *,
         comment: str | None = None, title: str | None = None,
         settings: dict[str, Any] | None = None, overwrite: bool = False) -> Path:
    """Uloží profil; `params` sú hodnoty v tvare `IBSConfig.to_dict()`,
    `settings` nastavenia behu (`timeframe`, `timerange`, `fee`, `wallet`, `detail`)."""
    name = check_name(name)
    if instrument not in INSTRUMENTS:
        raise ProfileError(f"neznámy nástroj {instrument!r}; známe: {sorted(INSTRUMENTS)}")
    IBSConfig.from_dict({k: v for k, v in params.items() if not k.startswith("_")})  # ConfigError
    path = path_for(name)
    if path.exists() and not overwrite:
        raise FileExistsError(f"profil {name} už existuje")
    data: dict[str, Any] = {"_instrument": instrument, **deviations(params)}
    for key in reversed(SETTING_KEYS):
        value = (settings or {}).get(key)
        if value is not None:
            data = {f"_{key}": value, **data}
    if comment:
        data = {"_comment": comment, **data}
    if title:
        data = {"_title": title, **data}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def rename(old: str, new: str) -> Path:
    src = _dir() / f"{old}.json"
    if not src.exists():
        if old in builtin_names():
            raise ProfileError(f"{old} je profil repozitára — premenovať sa dá len vlastný profil")
        raise FileNotFoundError(f"profil {old} neexistuje")
    dst = path_for(new)
    if dst.exists() and dst != src:
        raise FileExistsError(f"profil {new} už existuje")
    src.rename(dst)
    return dst


def delete(name: str) -> bool:
    path = _dir() / f"{name}.json"
    if not path.exists():
        if name in builtin_names():
            raise ProfileError(f"{name} je profil repozitára — zmazať sa dá len vlastný profil")
        return False
    path.unlink()
    return True
