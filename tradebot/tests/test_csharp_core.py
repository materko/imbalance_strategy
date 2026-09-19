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

from tradebot.core.types import SizeSpec
from tradebot.strategies import STRATEGIES

SPECS = [s for s in STRATEGIES.values() if s.csharp_dir is not None]
IDS = [s.key for s in SPECS]

_DECL = re.compile(r"^\s*public\s+(?!static|const|readonly|sealed|class|enum)([\w.<>?]+)\s+([^;()]+);", re.M)
_SIZE = re.compile(r'new SizeSpec\(([-\d.]+),\s*"(\w+)"\)')


def _csharp_fields(spec) -> dict[str, str]:
    """`meno -> text defaultu` z `*Config.cs` (aj viac polí na riadku: `public int a = 1, b = 0;`)."""
    out: dict[str, str] = {}
    for path in sorted(spec.csharp_dir.glob("*Config.cs")):
        code = re.sub(r"//[^\n]*", "", path.read_text(encoding="utf-8"))
        # `new SizeSpec(2.0, "abs")` má vnútri zátvorky aj čiarku — pred delením na polia ho nahraď značkou
        code = _SIZE.sub(lambda m: f"SIZE:{m.group(1)}:{m.group(2)}", code)
        for m in _DECL.finditer(code):
            for part in m.group(2).split(","):
                name, _, default = part.partition("=")
                out[name.strip()] = default.strip()
    return out


def test_aspon_jedna_strategia_ma_csharp_jadro():
    assert "ibsninja" in IDS


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
            # C# enum je PascalCase toho istého textu: "Long only" -> LongOnly, "hl2" -> Hl2
            want = "".join(w[:1].upper() + w[1:] for w in str(value.value).split())
            ok = text.split(".")[-1] == want
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
