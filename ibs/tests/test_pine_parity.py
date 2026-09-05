"""Config sa musí zhodovať s Pine originálom — parsuje sa priamo `pine/imbalance_strategy_FULL.pine`.

Toto je prvá poistka celého portu: keby sa niekedy stratil alebo prepísal jeden z 115 vstupov,
stratégia by ticho obchodovala inak. Test to zachytí hneď, bez ohľadu na to, kto config upraví.
"""

from __future__ import annotations

import re
from dataclasses import fields
from enum import Enum
from pathlib import Path

import pytest

from ibs.core import IBSConfig
from ibs.core.config import CONSTRAINTS, PORT_ONLY_FIELDS, SIZE_FIELDS
from ibs.core.types import SizeSpec

PINE_FILE = Path(__file__).resolve().parents[2] / "pine" / "imbalance_strategy_FULL.pine"

#: Pine vstupy, ktoré sa VEDOME neportujú, aj s dôvodom.
REMOVED_INPUTS = {
    # PickMyTrade sa nebude používať (rozhodnutie 2026-09-04) - Freqtrade aj MultiCharts
    # posielajú ordre priamo, žiadny webhook medzi tým nie je.
    "pmtToken",
    "pmtAccountId",
    "pmtStratName",
    "pmtMarketOrderType",
    # Podľa vlastného Pine tooltipu použiteľné LEN pre PickMyTrade - `strategy.exit`
    # v TradingView pre neho nemá ekvivalent, takže bez PMT nemá čo robiť.
    "trailFreqPct",
}

#: Polia, kde sa vedome odchyľujeme od Pine defaultu, aj s dôvodom.
INTENTIONAL_DEFAULT_DIFFS = {
    # Pine má 0.5 (hodnota pre MNQ). Engine počíta z InstrumentSpec.point_value, takže
    # default je None a hodnota sa zadáva len v referenčných profiloch spolu
    # s legacyPineSizing — viď docs/ARCHITECTURE_port.md §3c.
    "tickDollarValue",
    # Pine color.rgb(51, 65, 85) -> hex; farby sa neporovnávajú číselne.
    "ewLineColor",
}

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


def _pine_inputs() -> dict[str, tuple[str, object, tuple[float, float] | None]]:
    out: dict[str, tuple[str, object, tuple[float, float] | None]] = {}
    for line in PINE_FILE.read_text(encoding="utf-8").splitlines():
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


@pytest.fixture(scope="module")
def pine():
    if not PINE_FILE.exists():
        pytest.skip(f"{PINE_FILE.name} nie je k dispozícii")
    parsed = _pine_inputs()
    assert len(parsed) == 115, f"z Pine sa vyparsovalo {len(parsed)} vstupov namiesto 115"
    return parsed


def test_every_pine_input_exists_in_config(pine):
    missing = sorted(set(pine) - {f.name for f in fields(IBSConfig)} - REMOVED_INPUTS)
    assert missing == [], f"v IBSConfig chýbajú Pine vstupy: {missing}"


def test_removed_inputs_are_really_gone(pine):
    """Čo je v REMOVED_INPUTS, nesmie v configu zostať - a musí to byť reálny Pine vstup."""
    still_present = sorted(REMOVED_INPUTS & {f.name for f in fields(IBSConfig)})
    assert still_present == [], f"malo byť odstránené, ale v configu je: {still_present}"

    not_in_pine = sorted(REMOVED_INPUTS - set(pine))
    assert not_in_pine == [], f"REMOVED_INPUTS odkazuje na neexistujúce Pine vstupy: {not_in_pine}"


def test_config_adds_only_documented_extras(pine):
    """Polia navyše sú povolené len tie, ktoré sú v ARCHITECTURE_port.md popísané.

    `legacyPineSizing` reprodukuje Pine sizing vrátane jeho chyby (golden test),
    `atrLen` obsluhuje parametre v jednotke `atr` — tú Pine nepozná (§3b),
    `leverage` je marža vo Freqtrade, ktorú TradingView strategy tester nerieši,
    `minSlDistance` je filter tesného SL kvôli poplatkom (defaultne vypnutý).
    """
    extra = sorted({f.name for f in fields(IBSConfig)} - set(pine))
    assert extra == sorted(PORT_ONLY_FIELDS), f"neočakávané polia navyše: {extra}"


def test_defaults_match_pine(pine):
    cfg = IBSConfig()
    mismatched: list[str] = []
    for name, (typ, pine_default, _) in pine.items():
        if name in INTENTIONAL_DEFAULT_DIFFS or name in REMOVED_INPUTS or pine_default is None:
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
    assert mismatched == [], "defaulty sa rozišli s Pine:\n  " + "\n  ".join(mismatched)


def test_constraints_match_pine_minval_maxval(pine):
    mismatched: list[str] = []
    for name, (_, _, rng) in pine.items():
        if rng is None or name in REMOVED_INPUTS:
            continue
        ours = CONSTRAINTS.get(name)
        if ours is None:
            mismatched.append(f"{name}: Pine má rozsah {rng}, CONSTRAINTS ho nemá")
        elif (float(ours[0]), float(ours[1])) != rng:
            mismatched.append(f"{name}: Pine={rng} CONSTRAINTS={ours}")
    assert mismatched == [], "rozsahy sa rozišli s Pine:\n  " + "\n  ".join(mismatched)


def test_no_stale_constraints(pine):
    stale = sorted(set(CONSTRAINTS) - set(pine) - PORT_ONLY_FIELDS)
    assert stale == [], f"CONSTRAINTS obsahuje neexistujúce vstupy: {stale}"


def test_size_fields_all_exist_in_pine(pine):
    unknown = sorted(set(SIZE_FIELDS) - set(pine) - PORT_ONLY_FIELDS)
    assert unknown == [], f"SIZE_FIELDS odkazuje na neexistujúce vstupy: {unknown}"
