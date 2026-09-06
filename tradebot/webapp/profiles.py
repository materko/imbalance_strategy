"""Vlastné profily testera — JSON v `user_data/profiles/`, vedľa histórie behov.

Profily v `tradebot/configs/<stratégia>/` sú kód repozitára: držia paritu s Pine, ukazujú
na ne testy a dokumenty s meraniami, takže ich tester nesmie premenovať ani zmazať. Čo si
uloží z vlastného behu, patrí k jeho dátam — ide do gitu spolu s `runs/` cez Push, dá sa
premenovať aj zmazať a nikdy neprepíše profil z repozitára.

Na rozdiel od profilov repozitára (tie držia len odchýlky od Pine defaultov) sa sem
zapisuje **každé pole configu**. Profil tak stojí sám na sebe: nezáleží, či sa medzitým
zmenil profil, z ktorého tester vychádzal, ani či sa posunul niektorý Pine default —
beh spustený o rok neskôr má presne tie hodnoty, s ktorými sa profil ukladal.

Každý vlastný profil nesie `_strategy` (bez kľúča = `ibs`, profily spred registry stratégií);
ponuka vo formulári ukazuje len profily aktívnej stratégie. K tomu nastavenia behu, bez
ktorých by profil povedal „ako", ale nie „na čom": `_timeframe` (limity `*MaxBars` sú
v baroch, takže TF patrí k nastaveniu), `_timerange`, `_fee`, `_wallet` a `_detail`.
`_base` hovorí, z ktorého profilu tester vychádzal — je to len záznam pôvodu.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..core.config import ConfigError
from ..core.types import INSTRUMENTS
from ..strategies import get_spec

REPO = Path(__file__).resolve().parents[2]
PROFILES_DIR = REPO / "platforms" / "freqtrade" / "user_data" / "profiles"

#: Stratégia vlastných profilov bez `_strategy` (spred registry stratégií).
LEGACY_STRATEGY = "ibs"

#: Meno profilu je zároveň meno súboru — bez ciest, medzier a diakritiky.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,47}$")


class ProfileError(ValueError):
    """Neplatné meno, kolízia s profilom repozitára alebo pokus zmeniť cudzí profil."""


def _dir() -> Path:
    # PROFILES_DIR sa číta až tu, aby sa dal v testoch prepnúť
    return Path(PROFILES_DIR)


def _strategy_of_file(path: Path) -> str:
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("_strategy") or LEGACY_STRATEGY)
    except (OSError, json.JSONDecodeError):
        return LEGACY_STRATEGY


def builtin_names(strategy: str = LEGACY_STRATEGY) -> list[str]:
    return sorted(p.stem for p in get_spec(strategy).profile_dir.glob("*.json"))


def user_names(strategy: str = LEGACY_STRATEGY) -> list[str]:
    d = _dir()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json") if _strategy_of_file(p) == strategy)


def all_names(strategy: str = LEGACY_STRATEGY) -> list[str]:
    return builtin_names(strategy) + user_names(strategy)


def all_paths(strategy: str = LEGACY_STRATEGY) -> dict[str, Path]:
    """Meno profilu → súbor; profil repozitára má prednosť pred rovnako nazvaným vlastným."""
    out = {p.stem: p for p in sorted(get_spec(strategy).profile_dir.glob("*.json"))}
    d = _dir()
    if d.exists():
        for p in sorted(d.glob("*.json")):
            if _strategy_of_file(p) == strategy:
                out.setdefault(p.stem, p)
    return out


def is_user(name: str, strategy: str = LEGACY_STRATEGY) -> bool:
    return name in user_names(strategy)


def path_for(name: str) -> Path:
    """Cesta k vlastnému profilu (nemusí existovať)."""
    check_name(name)
    return _dir() / f"{name}.json"


def resolve(name: "str | Path", strategy: str = LEGACY_STRATEGY) -> "str | Path":
    """Čo dať `load_profile`: profil repozitára menom, vlastný profil cestou, hotová cesta nedotknutá."""
    if isinstance(name, Path) or "/" in str(name) or str(name).endswith(".json"):
        return name
    builtin = get_spec(strategy).profile_dir / f"{name}.json"
    if builtin.exists():
        return name
    if NAME_RE.match(name or ""):
        own = _dir() / f"{name}.json"
        if own.exists():
            return own
    raise ConfigError(f"profil {name!r} neexistuje; dostupné pre {strategy}: {all_names(strategy)}")


def check_name(name: str, strategy: str | None = None) -> str:
    name = (name or "").strip()
    if not NAME_RE.match(name):
        raise ProfileError(
            f"neplatné meno profilu {name!r}: 2–48 znakov, len písmená bez diakritiky, "
            "číslice, '.', '-' a '_'"
        )
    from ..strategies import STRATEGIES

    for key in ([strategy] if strategy else STRATEGIES):
        if name in builtin_names(key):
            raise ProfileError(f"{name} je profil repozitára — vyber si iné meno")
    return name


def config_values(params: dict[str, Any], strategy: str = LEGACY_STRATEGY) -> dict[str, Any]:
    """Všetky polia configu — profil má byť úplný, nie diff.

    Odchýlkový zápis (ako v `tradebot/configs/`) by znamenal, že profil závisí na tom, čo je
    práve default: keby sa Pine default posunul, posunul by sa aj rok starý profil
    a beh by sa už nedal zopakovať. Preto sa zapíše celý config, aj keď je súbor dlhší.

    Čo formulár neposiela (polia skryté ako neúčinné) sa doplní z defaultov — aj tak by
    ich config doplnil, ale v súbore majú byť vidno.
    """
    defaults = get_spec(strategy).config_cls().to_dict()
    return {k: params.get(k, v) for k, v in defaults.items()}


#: Nastavenia behu, ktoré k profilu patria — bez nich by profil povedal „ako", ale
#: nie „na čom". Ukladajú sa s podtržníkom, aby ich config prešiel ako metadáta.
SETTING_KEYS = ("timeframe", "timerange", "fee", "wallet", "detail")


def _data_of(name: str, strategy: str) -> dict[str, Any]:
    path = all_paths(strategy).get(name)
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def settings_of(name: str, strategy: str = LEGACY_STRATEGY) -> dict[str, Any]:
    """Nastavenia behu uložené v profile (`_timeframe`, `_timerange`, `_fee`…).

    Čo profil nemá, v slovníku nie je — formulár tú položku nechá, ako ju má tester.
    """
    data = _data_of(name, strategy)
    return {k: data[f"_{k}"] for k in SETTING_KEYS if data.get(f"_{k}") is not None}


def base_of(name: str, strategy: str = LEGACY_STRATEGY) -> str | None:
    """Profil, z ktorého tento vznikol (`_base`) — len záznam, hodnoty sú vlastné."""
    return _data_of(name, strategy).get("_base") or None


def save(name: str, params: dict[str, Any], instrument: str, *,
         comment: str | None = None, title: str | None = None, base: str | None = None,
         settings: dict[str, Any] | None = None, overwrite: bool = False,
         strategy: str = LEGACY_STRATEGY) -> Path:
    """Uloží profil; `params` sú hodnoty v tvare `config.to_dict()`,
    `settings` nastavenia behu (`timeframe`, `timerange`, `fee`, `wallet`, `detail`),
    `base` meno profilu, z ktorého sa vychádzalo, `strategy` kľúč stratégie."""
    name = check_name(name)
    if instrument not in INSTRUMENTS:
        raise ProfileError(f"neznámy nástroj {instrument!r}; známe: {sorted(INSTRUMENTS)}")
    spec = get_spec(strategy)
    spec.config_cls.from_dict({k: v for k, v in params.items() if not k.startswith("_")})  # ConfigError
    path = path_for(name)
    if path.exists() and not overwrite:
        raise FileExistsError(f"profil {name} už existuje")
    data: dict[str, Any] = {"_strategy": strategy, "_instrument": instrument, **config_values(params, strategy)}
    for key in reversed(SETTING_KEYS):
        value = (settings or {}).get(key)
        if value is not None:
            data = {f"_{key}": value, **data}
    if base:
        data = {"_base": base, **data}
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
        from ..strategies import STRATEGIES

        if any(old in builtin_names(k) for k in STRATEGIES):
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
        from ..strategies import STRATEGIES

        if any(name in builtin_names(k) for k in STRATEGIES):
            raise ProfileError(f"{name} je profil repozitára — zmazať sa dá len vlastný profil")
        return False
    path.unlink()
    return True
