"""Stratégie s jadrom v C# — čo musí sedieť medzi Python balíkom a C# zdrojákmi.

Config takej stratégie žije dvakrát: v Pythone (formulár, profily, validácia) a v C# (čo engine
naozaj číta). C# strana neznámy kľúč ticho preskočí, aby načítala aj staré profily — preto tu
test stráži, že **každé pole Python configu má C# náprotivok s rovnakým menom a defaultom**;
inak by sa parameter dal ladiť vo formulári a C# engine by o ňom nevedel.
"""

from __future__ import annotations

import re
from dataclasses import fields
from enum import Enum

import pytest

from tradebot.adapters.csharp.build import sources, strategy_dirs
from tradebot.core.types import SizeSpec
from tradebot.strategies import STRATEGIES

SPECS = [s for s in STRATEGIES.values() if s.csharp_dir is not None]
IDS = [s.key for s in SPECS]

_DECL = re.compile(r"^\s*public\s+(?!static|const|readonly|sealed|class|enum)([\w.<>?]+)\s+([^;()]+);", re.M)
_SIZE = re.compile(r'new SizeSpec\(([-\d.]+),\s*"(\w+)"\)')


_BASE = re.compile(r"class\s+(\w+)\s*:\s*(\w+)")
_ASSIGN = re.compile(r"^\s*(\w+)\s*=\s*([^;=]+);", re.M)


def _code(path) -> str:
    code = re.sub(r"//[^\n]*", "", path.read_text(encoding="utf-8"))
    # `new SizeSpec(2.0, "abs")` má vnútri zátvorky aj čiarku — pred delením na polia ho nahraď značkou
    return _SIZE.sub(lambda m: f"SIZE:{m.group(1)}:{m.group(2)}", code)


def _config_file(cls: str):
    """`*Config.cs` v ktorejkoľvek C# stratégii, ktorý deklaruje triedu `cls`."""
    for path in sources(strategy_dirs()):
        if not path.name.endswith("Config.cs"):
            continue
        if re.search(rf"class\s+{cls}\b", path.read_text(encoding="utf-8")):
            return path
    return None


def _csharp_fields(spec) -> dict[str, str]:
    """`meno -> text defaultu` z `*Config.cs` (aj viac polí na riadku: `public int a = 1, b = 0;`).

    Config, ktorý dedí z configu inej C# stratégie (VWAP ORB z ORB, IBS Entry Zone z IBS), má polia predka
    v jeho súbore a zmenené defaulty v konštruktore (`sessionMode = OrbSessionMode.Ny;`) — započítajú sa oboje."""
    out: dict[str, str] = {}
    for path in sorted(spec.csharp_dir.glob("*Config.cs")):
        code = _code(path)
        own: dict[str, str] = {}
        for m in _DECL.finditer(code):
            for part in m.group(2).split(","):
                name, _, default = part.partition("=")
                own[name.strip()] = default.strip()
        base = _BASE.search(code)
        base_path = _config_file(base.group(2)) if base else None
        if base_path is not None and base_path != path:
            parent = _code(base_path)
            for m in _DECL.finditer(parent):
                for part in m.group(2).split(","):
                    name, _, default = part.partition("=")
                    out.setdefault(name.strip(), default.strip())
            # zmenené defaulty predka: priradenia v tele triedy potomka (konštruktor)
            for m in _ASSIGN.finditer(code):
                if m.group(1) in out and m.group(1) not in own:
                    out[m.group(1)] = m.group(2).strip()
        out.update(own)
    return out


def test_aspon_jedna_strategia_ma_csharp_jadro():
    assert "ibsnet" in IDS


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_zdrojaky_existuju_a_engine_ma_kluc(spec):
    assert spec.csharp_dir.is_dir(), f"{spec.key}: chýba {spec.csharp_dir}"
    key = getattr(spec.engine_factory, "csharp_key", None)
    assert key, f"{spec.key}: engine_factory nie je csharp_engine_factory(...)"
    code = "".join(p.read_text(encoding="utf-8") for p in spec.csharp_dir.rglob("*.cs"))
    assert f'[TradeBotEngine("{key}"' in code, f"{spec.key}: v C# chýba trieda s kľúčom {key!r}"


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_kazde_pole_configu_ma_csharp_naprotivok_s_rovnakym_defaultom(spec):
    cs = _csharp_fields(spec)
    cfg = spec.config_cls()
    chyba, ine = [], []
    for f in fields(cfg):
        if f.name not in cs:
            chyba.append(f.name)
            continue
        value, text = getattr(cfg, f.name), cs[f.name]
        if isinstance(value, bool):
            ok = text == str(value).lower()
        elif isinstance(value, SizeSpec):
            _tag, _, rest = text.partition(":")
            number, _, unit = rest.partition(":")
            ok = _tag == "SIZE" and float(number) == value.value and unit == value.unit
        elif isinstance(value, Enum):
            # C# enum je PascalCase toho istého textu: "Long only" -> LongOnly, "hl2" -> Hl2,
            # "range_pct" -> RangePct; číselný enum ("15") je v C# obyčajné číslo
            want = "".join(w[:1].upper() + w[1:] for w in re.split(r"[\s_]+", str(value.value)) if w)
            # text v C# (Pine reťazec ako "RTH 8:30 CT", ktorý nie je platné meno enumu) je tiež v poriadku
            ok = text.split(".")[-1] == want or text == f'"{value.value}"'
        elif isinstance(value, (int, float)):
            ok = float(text) == float(value)
        elif value is None:
            ok = text == "null"
        else:
            ok = text == f'"{value}"'
        if not ok:
            ine.append(f"{f.name}: python {value!r} vs C# {text}")
    assert chyba == [], f"{spec.key}: polia configu, ktoré C# config nemá: {chyba}"
    assert ine == [], f"{spec.key}: iný default v C#: {ine}"
