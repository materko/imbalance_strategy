"""Parita parametrov: formulár ponúka presne to, čo stratégia naozaj číta.

Tri pravdy o parametroch stratégie sa nesmú rozísť:

1. **config** (`config.py`) — čo profil a beh nesú,
2. **popis** (`params.py`) — čo formulár ukáže a `cli params` vypíše,
3. **kód** — engine stratégie, jej moduly, `tradebot/core` a adaptéry.

Pole, ktoré formulár ponúka, ale kód ho nečíta, je horšie než žiadne: tester ho ladí,
výsledok sa nemení a záver z mriežky je šum. Pole, ktoré kód číta, ale formulár ho
nemá, sa zas nedá nastaviť ani uložiť do profilu. Pine vstupy, ktoré port vedome
neportuje, v configu vôbec nie sú (`removed_inputs`, pri zrušenom poli aj `RETIRED_FIELDS`);
výnimočne ponechané v configu (`inert_inputs`) formulár skryje a test stráži, aby tam
neostalo nič, čo kód medzičasom začal čítať.

„Číta" sa overuje staticky (AST), nie behom: pole je použité, keď sa v kóde objaví
ako atribút (`cfg.rrRatio`), ako meno v `getattr` (aj f-string `f"sess{n}On"`), alebo
ako reťazec v tabuľke (dict/list/tuple/set) mimo deklaračných tabuliek configu.
Validácia v `_problems` sa za použitie nepočíta — pole, ktoré sa len kontroluje, nič
nerobí. Je to sito, nie dôkaz (vetvu, ktorá sa nikdy nevykoná, neodhalí), ale mŕtve
pole, ktoré nikto nikde nečíta, zachytí spoľahlivo.
"""

from __future__ import annotations

import ast
import re
from dataclasses import fields
from functools import lru_cache
from pathlib import Path

import pytest

from tradebot.strategies import STRATEGIES
from tradebot.strategies.base import REPO

SPECS = list(STRATEGIES.values())
IDS = [s.key for s in SPECS]

#: Súbory balíka stratégie, ktoré parametre len **popisujú** (formulár, ladenie, registry).
DECLARATIVE = {"params.py", "meta.py", "hyperopt.py"}
#: Tabuľky configu, v ktorých je meno poľa deklarácia, nie použitie.
CONFIG_TABLES = {"SIZE_FIELDS", "ENUM_FIELDS", "CONSTRAINTS", "PORT_ONLY_FIELDS", "RETIRED_FIELDS",
                 "PINE_DISPLAY_INPUTS", "__all__"}
#: Metódy configu, ktoré pole len kontrolujú.
VALIDATION = {"_problems", "_generic_problems", "validate", "check_instrument", "__post_init__"}
#: Generický kód, ktorý číta polia stratégie (hodiny seáns, riziko, adaptéry).
SHARED = ("tradebot/core", "tradebot/adapters")


class _Refs:
    """Mená, ktoré kód číta: atribúty, `getattr` mená a reťazce v tabuľkách."""

    def __init__(self) -> None:
        self.attrs: set[str] = set()
        self.strings: set[str] = set()
        self.patterns: list[re.Pattern[str]] = []

    def visit(self, node: ast.AST, strings: bool = True) -> None:
        for n in ast.walk(node):
            if isinstance(n, ast.Attribute):
                self.attrs.add(n.attr)
            if not strings:
                continue
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id in ("getattr", "setattr", "hasattr") and len(n.args) >= 2):
                self._name(n.args[1])
            elif isinstance(n, ast.Dict):
                for e in [*n.keys, *n.values]:
                    if e is not None:
                        self._name(e)
            elif isinstance(n, (ast.List, ast.Tuple, ast.Set)):
                for e in n.elts:
                    self._name(e)

    def _name(self, e: ast.AST) -> None:
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            self.strings.add(e.value)
        elif isinstance(e, ast.JoinedStr):
            parts, literal = [], 0
            for v in e.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(re.escape(v.value))
                    literal += len(v.value)
                else:
                    parts.append(r"\w+")
            if literal >= 3:  # f"{x}" by zodpovedalo všetkému
                self.patterns.append(re.compile("^" + "".join(parts) + "$"))

    def reads(self, name: str) -> bool:
        return name in self.attrs or name in self.strings or any(p.match(name) for p in self.patterns)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _visit_config(path: Path, refs: _Refs) -> None:
    for node in _parse(path).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(isinstance(t, ast.Name) and t.id in CONFIG_TABLES for t in targets):
                refs.visit(node)  # napr. IBS INDICATOR_RULES, divergence mapa pole -> indikátor
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name not in VALIDATION:
                    refs.visit(item)
        elif isinstance(node, ast.FunctionDef):
            refs.visit(node)


@lru_cache(maxsize=None)
def _shared_refs() -> _Refs:
    refs = _Refs()
    for base in SHARED:
        for path in sorted((REPO / base).rglob("*.py")):
            refs.visit(_parse(path))
    return refs


_CS_NOISE = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"', re.S)
_CS_CFG_READ = re.compile(r"\b_?[cC]fg\.(\w+)")
_CS_WORD = re.compile(r"\b[A-Za-z_]\w*\b")


def _csharp_reads(csharp_dir: Path) -> set[str]:
    """Polia configu, ktoré číta C# jadro stratégie: `cfg.pole` / `Cfg.pole` / `_cfg.pole` kdekoľvek
    a v triede configu (`*Config.cs`) meno použité aj mimo svojej deklarácie. Komentáre a reťazce
    sa nepočítajú — tabuľka jednotiek je deklarácia, nie čítanie."""
    reads: set[str] = set()
    for path in sorted(csharp_dir.rglob("*.cs")):
        code = _CS_NOISE.sub(" ", path.read_text(encoding="utf-8"))
        reads.update(_CS_CFG_READ.findall(code))
        if path.name.endswith("Config.cs"):
            seen: dict[str, int] = {}
            for word in _CS_WORD.findall(code):
                seen[word] = seen.get(word, 0) + 1
            reads.update(w for w, n in seen.items() if n >= 2)
    return reads


def _strategy_refs(key: str) -> _Refs:
    refs = _Refs()
    pkg = REPO / "tradebot" / "strategies" / key
    csharp_dir = STRATEGIES[key].csharp_dir
    if csharp_dir is not None:  # jadro v C#: polia číta ono, Python balík je len popis
        refs.attrs |= _csharp_reads(csharp_dir)
    for path in sorted(pkg.rglob("*.py")):
        if path.parent == pkg and path.name in DECLARATIVE:
            continue
        if path.parent == pkg and path.name == "config.py":
            _visit_config(path, refs)
        elif path.parent == pkg and path.name == "__init__.py":
            # SPEC nesie mená polí ako reťazce (`risk_field="riskDollar"`) — to je popis
            refs.visit(_parse(path), strings=False)
        else:
            refs.visit(_parse(path))
    shared = _shared_refs()
    refs.attrs |= shared.attrs
    refs.strings |= shared.strings
    refs.patterns += shared.patterns
    return refs


def _field_names(spec) -> list[str]:
    return [f.name for f in fields(spec.config_cls)]


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_kazde_pole_configu_nieco_cita(spec):
    """Pole, ktoré formulár ponúka, musí kód stratégie alebo adaptér naozaj čítať.

    Keď test padne: pole buď zruš (config + `params.py` + `RETIRED_FIELDS`, aby staré
    profily ďalej prešli; Pine vstup aj do `REMOVED_INPUTS` v `meta.py`), alebo ho výnimočne
    nechaj v configu ako `inert_inputs` v `meta.py` a napíš prečo.
    """
    refs = _strategy_refs(spec.key)
    mrtve = sorted(n for n in _field_names(spec) if n not in spec.inert_inputs and not refs.reads(n))
    assert mrtve == [], f"{spec.key}: polia vo formulári, ktoré nič nečíta: {mrtve}"


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_inert_vstupy_su_naozaj_inertne(spec):
    """`inert_inputs` formulár skrýva — keď ich kód začne čítať, tester ich musí vidieť."""
    refs = _strategy_refs(spec.key)
    assert set(spec.inert_inputs) <= set(_field_names(spec)), f"{spec.key}: inert pole mimo configu"
    citane = sorted(n for n in spec.inert_inputs if refs.reads(n))
    assert citane == [], f"{spec.key}: inert_inputs, ktoré kód číta (patria do formulára): {citane}"


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_popisy_a_formular_sedia_s_configom(spec):
    """`params.py` popisuje presne polia configu a formulár ponúka presne tie, čo nie sú inertné."""
    from tester.webapp.param_meta import param_metadata

    names = set(_field_names(spec))
    assert set(spec.param_meta) <= names, f"{spec.key}: params.py mimo configu: {sorted(set(spec.param_meta) - names)}"
    chyba = sorted(names - spec.inert_inputs - set(spec.param_meta))
    assert chyba == [], f"{spec.key}: polia bez popisu v params.py: {chyba}"
    formular = {m["name"] for m in param_metadata(spec)}
    assert formular == names - spec.inert_inputs - spec.removed_inputs


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_zrusene_polia_su_zrusene_vsade(spec):
    """Zrušené pole (`RETIRED_FIELDS`) nesmie ostať v configu ani v popisoch, a starý profil
    s ním sa musí ďalej načítať."""
    retired = set(spec.config_cls.RETIRED_FIELDS)
    if not retired:
        return
    assert not retired & set(_field_names(spec)), f"{spec.key}: zrušené pole je stále v configu"
    assert not retired & set(spec.param_meta), f"{spec.key}: zrušené pole je stále v params.py"
    stary = {**spec.config_cls().to_dict(), **{k: 1 for k in retired}}
    assert spec.config_cls.from_dict(stary).to_dict() == spec.config_cls().to_dict()


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_ladenie_odkazuje_na_polia_formulara(spec):
    """Hyperopt odporúčania a „preladiť tento parameter" musia mieriť na pole, ktoré tester vidí."""
    if spec.hyperopt_cls is None:
        return
    viditelne = set(_field_names(spec)) - spec.inert_inputs
    tabulky = {"SUGGESTED": set(spec.hyperopt_cls.SUGGESTED), "WARN": set(spec.hyperopt_cls.WARN),
               # vlastnosť obchodu -> parameter; overuje sa parameter
               "FEATURE_PARAMS": {v for v in spec.hyperopt_cls.FEATURE_PARAMS.values() if v}}
    for tabulka, mena in tabulky.items():
        cudzie = sorted(mena - viditelne)
        assert cudzie == [], f"{spec.key}: {tabulka} odkazuje na polia mimo formulára: {cudzie}"
