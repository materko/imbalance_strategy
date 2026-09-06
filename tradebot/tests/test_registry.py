"""Registry stratégií: každá stratégia musí mať všetko, čo od nej adaptéry a webapp čakajú.

Toto je checklist z docs/STRATEGIE.md ako test — kto pridá stratégiu a niečo zabudne,
dozvie sa to tu, nie z výnimky vo webapp o týždeň neskôr.
"""

from __future__ import annotations

import json
from dataclasses import fields

import pytest

from tradebot.core import DrawKind, load_profile
from tradebot.strategies import STRATEGIES, get_spec
from tradebot.strategies.base import REPO

SPECS = list(STRATEGIES.values())
IDS = [s.key for s in SPECS]


def test_registry_has_ibs_and_keys_match():
    assert "ibs" in STRATEGIES
    for key, spec in STRATEGIES.items():
        assert spec.key == key
    with pytest.raises(KeyError, match="neznáma stratégia"):
        get_spec("neexistuje")


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_profiles_dir_has_titled_profiles_and_default_loads(spec):
    files = sorted(spec.profile_dir.glob("*.json"))
    assert files, f"{spec.key}: {spec.profile_dir} nemá žiadny profil"
    for p in files:
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data.get("_title"), f"{p.name}: chýba _title pre webapp"
        assert data.get("_strategy", spec.key) == spec.key, f"{p.name}: _strategy nesedí"
    cfg, inst = load_profile(f"{spec.key}/{spec.default_profile}")
    assert isinstance(cfg, spec.config_cls) and inst.tick_size > 0


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_pine_source_and_engine(spec):
    assert spec.pine_path is not None and spec.pine_path.exists(), f"{spec.key}: chýba Pine súbor"
    assert spec.pine_input_count > 0
    assert spec.engine_factory is not None
    cfg, inst = load_profile(f"{spec.key}/{spec.default_profile}")
    engine = spec.engine_factory(cfg, inst, 3)
    assert engine.required_history > 0 and callable(engine.on_bar) and callable(engine.final_drawings)


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_layers_and_features_reference_real_things(spec):
    names = {f.name for f in fields(spec.config_cls)}
    for layer in spec.layers:
        for kind in layer.kinds + layer.hollow_kinds:
            assert DrawKind(kind), f"{spec.key}: vrstva {layer.id} má neregistrovaný druh {kind!r}"
        assert set(layer.hollow_kinds) <= set(layer.kinds)
    for kind in spec.kind_titles:
        assert DrawKind(kind)
    seen: set[str] = set()
    for feat in spec.features:
        for sw in feat["switches"]:
            assert sw in names, f"{spec.key}: FEATURES prepínač {sw!r} nie je pole configu"
        for name in feat["params"]:
            assert name in names, f"{spec.key}: FEATURES pole {name!r} neexistuje"
            assert name not in seen, f"{spec.key}: {name} je v dvoch featurách"
            seen.add(name)
    for name in spec.port_only_meta:
        assert name in spec.config_cls.PORT_ONLY_FIELDS, f"{spec.key}: port_only_meta pre {name!r}, ktoré nie je port-only"


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_freqtrade_shim_exists_with_matching_class(spec):
    """Freqtrade resolver berie len triedu, ktorej __module__ == názov súboru v user_data/strategies."""
    assert spec.freqtrade_class
    shim = REPO / "platforms" / "freqtrade" / "user_data" / "strategies" / f"{spec.freqtrade_class}.py"
    assert shim.exists(), f"{spec.key}: chýba shim {shim}"
    assert f"class {spec.freqtrade_class}(" in shim.read_text(encoding="utf-8")


def test_drawkind_registry_is_open_and_stable():
    a = DrawKind.register("test_kind_x", "TEST_KIND_X")
    b = DrawKind.register("test_kind_x", "TEST_KIND_X")
    assert a is b and a == "test_kind_x" and a.value == "test_kind_x" and a.name == "TEST_KIND_X"
    assert DrawKind("test_kind_x") is a and DrawKind.TEST_KIND_X is a
    assert DrawKind.IMB_BOX.value == "imb_box"  # IBS druh dostupný aj bez explicitného importu stratégie
    with pytest.raises(ValueError):
        DrawKind("neexistuje")
