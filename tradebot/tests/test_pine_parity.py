"""Config každej stratégie sa musí zhodovať s jej Pine originálom — parsuje sa priamo Pine súbor.

Toto je prvá poistka celého portu: keby sa niekedy stratil alebo prepísal jeden z Pine
vstupov, stratégia by ticho obchodovala inak. Test to zachytí hneď, bez ohľadu na to,
kto config upraví. Beží pre každú stratégiu v registry (`STRATEGIES`).
"""

from __future__ import annotations

import re
from dataclasses import fields
from enum import Enum

import pytest

from tradebot.core.types import SizeSpec
from tradebot.strategies import STRATEGIES

_INPUT_RE = re.compile(r"^\s*(\w+)\s*=\s*input\.(\w+)\((.*)$")


def _split_args(rest: str) -> list[str]:
    args: list[str] = []
    depth = 0
    cur = ""
    in_str = False
    for ch in rest:
        if in_str:
            cur += ch
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            cur += ch
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            if depth == 0:
                break
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
            continue
        cur += ch
    args.append(cur.strip())
    return args


def _parse_default(typ: str, raw: str):
    if typ == "bool":
        return raw == "true"
    if typ == "int":
        return int(raw)
    if typ == "float":
        return float(raw)
    if typ == "string":
        return raw.strip('"')
    return None  # color a pod.


def _pine_inputs(path) -> dict[str, tuple[str, object, tuple[float, float] | None]]:
    out: dict[str, tuple[str, object, tuple[float, float] | None]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _INPUT_RE.match(line)
        if not m:
            continue
        name, typ, rest = m.groups()
        args = _split_args(rest)
        mn = re.search(r"minval\s*=\s*(-?[\d.]+)", rest)
        mx = re.search(r"maxval\s*=\s*(-?[\d.]+)", rest)
        rng = (float(mn.group(1)), float(mx.group(1))) if mn and mx else None
        out[name] = (typ, _parse_default(typ, args[0]) if args else None, rng)
    return out


@pytest.fixture(scope="module", params=list(STRATEGIES.values()), ids=lambda s: s.key)
def strat(request):
    """(spec, vyparsované Pine vstupy) pre každú stratégiu."""
    spec = request.param
    if spec.pine_path is None or not spec.pine_path.exists():
        pytest.skip(f"{spec.key}: Pine súbor nie je k dispozícii")
    parsed = _pine_inputs(spec.pine_path)
    assert len(parsed) == spec.pine_input_count, (
        f"{spec.key}: z Pine sa vyparsovalo {len(parsed)} vstupov namiesto {spec.pine_input_count}"
    )
    return spec, parsed


def _field_names(spec) -> set[str]:
    return {f.name for f in fields(spec.config_cls)}


def test_every_pine_input_exists_in_config(strat):
    spec, pine = strat
    missing = sorted(set(pine) - _field_names(spec) - spec.removed_inputs)
    assert missing == [], f"{spec.key}: v configu chýbajú Pine vstupy: {missing}"


def test_removed_inputs_are_really_gone(strat):
    """Čo je v removed_inputs, nesmie v configu zostať - a musí to byť reálny Pine vstup."""
    spec, pine = strat
    still_present = sorted(spec.removed_inputs & _field_names(spec))
    assert still_present == [], f"malo byť odstránené, ale v configu je: {still_present}"
    not_in_pine = sorted(spec.removed_inputs - set(pine))
    assert not_in_pine == [], f"removed_inputs odkazuje na neexistujúce Pine vstupy: {not_in_pine}"


def test_config_adds_only_documented_extras(strat):
    """Polia navyše sú povolené len tie, ktoré stratégia deklaruje v PORT_ONLY_FIELDS
    (IBS: `legacyPineSizing`, `atrLen`, `leverage`, `minSlDistance` — viď ARCHITECTURE_port.md)."""
    spec, pine = strat
    extra = sorted(_field_names(spec) - set(pine))
    assert extra == sorted(spec.config_cls.PORT_ONLY_FIELDS), f"{spec.key}: neočakávané polia navyše: {extra}"


def test_defaults_match_pine(strat):
    spec, pine = strat
    cfg = spec.config_cls()
    mismatched: list[str] = []
    for name, (typ, pine_default, _) in pine.items():
        if name in spec.intentional_default_diffs or name in spec.removed_inputs or pine_default is None:
            continue
        ours = getattr(cfg, name)
        if isinstance(ours, SizeSpec):
            ours = ours.value
        elif isinstance(ours, Enum):  # str-Enum je aj str, takže musí ísť pred str vetvu
            ours = ours.value
        if isinstance(ours, str) or isinstance(pine_default, str):
            same = str(ours) == str(pine_default)
        else:
            same = float(ours) == pytest.approx(float(pine_default))
        if not same:
            mismatched.append(f"{name}: Pine={pine_default!r} config={ours!r}")
    assert mismatched == [], f"{spec.key}: defaulty sa rozišli s Pine:\n  " + "\n  ".join(mismatched)


def test_constraints_match_pine_minval_maxval(strat):
    spec, pine = strat
    constraints = spec.config_cls.CONSTRAINTS
    mismatched: list[str] = []
    for name, (_, _, rng) in pine.items():
        if rng is None or name in spec.removed_inputs:
            continue
        ours = constraints.get(name)
        if ours is None:
            mismatched.append(f"{name}: Pine má rozsah {rng}, CONSTRAINTS ho nemá")
        elif (float(ours[0]), float(ours[1])) != rng:
            mismatched.append(f"{name}: Pine={rng} CONSTRAINTS={ours}")
    assert mismatched == [], f"{spec.key}: rozsahy sa rozišli s Pine:\n  " + "\n  ".join(mismatched)


def test_no_stale_constraints(strat):
    spec, pine = strat
    stale = sorted(set(spec.config_cls.CONSTRAINTS) - set(pine) - spec.config_cls.PORT_ONLY_FIELDS)
    assert stale == [], f"{spec.key}: CONSTRAINTS obsahuje neexistujúce vstupy: {stale}"


def test_size_fields_all_exist_in_pine(strat):
    spec, pine = strat
    unknown = sorted(set(spec.config_cls.SIZE_FIELDS) - set(pine) - spec.config_cls.PORT_ONLY_FIELDS)
    assert unknown == [], f"{spec.key}: SIZE_FIELDS odkazuje na neexistujúce vstupy: {unknown}"
