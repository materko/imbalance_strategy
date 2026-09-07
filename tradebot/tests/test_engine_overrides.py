"""Jeden config na stratégiu + blok `_engine_overrides` pre to málo, čo sa engine týka.

Parametre stratégie sú na engine nezávislé — to je pointa portu a stráži to golden test.
Dva takmer rovnaké configy na stratégiu by sa časom potichu rozišli a nikto by si nevšimol,
že tá istá stratégia obchoduje na každom engine inak. Preto výnimky, nie kópie.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.core import list_profiles, load_profile, profile_dir
from tradebot.core.config import ConfigError


def write(tmp_path: Path, **extra) -> Path:
    data = {
        "_strategy": "ibs",
        "_instrument": "mnq",
        "rrRatio": 2.0,
        **extra,
    }
    path = tmp_path / "p.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# kde profily ležia
# --------------------------------------------------------------------------- #


def test_profily_leza_pri_strategii():
    """Balík stratégie musí byť sebestačný — dá sa presunúť jedným adresárom."""
    d = profile_dir("ibs")

    assert d.name == "configs" and d.parent.name == "ibs"
    assert d.parent.parent.name == "strategies"
    assert "golden_binance_btcusdt_3m" in list_profiles("ibs")
    assert (d / "golden_binance_btcusdt_3m.json").exists()


def test_profil_sa_nacita_menom_aj_s_prefixom_strategie():
    by_name, _ = load_profile("golden_binance_btcusdt_3m")
    with_prefix, _ = load_profile("ibs/golden_binance_btcusdt_3m")

    assert by_name.to_dict() == with_prefix.to_dict()


# --------------------------------------------------------------------------- #
# engine overrides
# --------------------------------------------------------------------------- #


def test_bez_engine_ostane_zakladna_hodnota(tmp_path: Path):
    path = write(tmp_path, _engine_overrides={"multicharts": {"rrRatio": 5.0}})

    cfg, _ = load_profile(path)
    assert cfg.rrRatio == 2.0


def test_engine_prepise_len_svoje_pole(tmp_path: Path):
    path = write(tmp_path, _engine_overrides={"multicharts": {"rrRatio": 5.0}})

    mc, _ = load_profile(path, engine="multicharts")
    ft, _ = load_profile(path, engine="freqtrade")

    assert mc.rrRatio == 5.0
    assert ft.rrRatio == 2.0  # engine bez výnimiek dostane základ


def test_overrides_nie_su_parameter_configu(tmp_path: Path):
    """`_engine_overrides` je metadáta profilu, nie pole stratégie."""
    path = write(tmp_path, _engine_overrides={"multicharts": {"rrRatio": 5.0}})

    cfg, _ = load_profile(path, engine="multicharts")
    assert "_engine_overrides" not in cfg.to_dict()


def test_aplikovanie_je_idempotentne(tmp_path: Path):
    """Dočasný profil behu z webapp už môže byť vyriešený — druhý prechod ho nesmie zmeniť."""
    path = write(tmp_path, _engine_overrides={"multicharts": {"rrRatio": 5.0}})
    once, _ = load_profile(path, engine="multicharts")

    resolved = tmp_path / "resolved.json"
    data = {**once.to_dict(), "_strategy": "ibs", "_instrument": "mnq",
            "_engine_overrides": {"multicharts": {"rrRatio": 5.0}}}
    resolved.write_text(json.dumps(data), encoding="utf-8")
    twice, _ = load_profile(resolved, engine="multicharts")

    assert twice.to_dict() == once.to_dict()


def test_pokazeny_blok_je_chyba_a_nie_ticho_ignorovany(tmp_path: Path):
    path = write(tmp_path, _engine_overrides=["multicharts"])
    with pytest.raises(ConfigError, match="_engine_overrides"):
        load_profile(path)

    path = write(tmp_path, _engine_overrides={"multicharts": 5.0})
    with pytest.raises(ConfigError, match="_engine_overrides"):
        load_profile(path, engine="multicharts")


def test_neznama_hodnota_v_bloku_spadne_ako_kdekolvek_inde(tmp_path: Path):
    path = write(tmp_path, _engine_overrides={"multicharts": {"rrRatio": -1.0}})

    with pytest.raises(ConfigError):
        load_profile(path, engine="multicharts")
