"""Testy configu a inštrumentov.

Ťažisko je na tom, aby sa nezopakovali tiché chyby popísané v
docs/ARCHITECTURE_port.md §3b/§3c — hlavne MNQ hodnota `tickDollarValue` na krypte.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.core import (
    BTCUSD_COINBASE,
    BTCUSDT_BINANCE,
    MNQ,
    ConfigError,
    IBSConfig,
    SizeSpec,
    TradeDirection,
    list_profiles,
    load_profile,
)
from tradebot.core.config import CONFIG_DIR, PORT_ONLY_FIELDS, SIZE_FIELDS


# --------------------------------------------------------------------------- #
# Defaulty a validácia
# --------------------------------------------------------------------------- #


def test_defaults_are_valid():
    cfg = IBSConfig()
    assert cfg.enableImbEntry is True
    assert cfg.tradeDirection is TradeDirection.BOTH
    assert cfg.zoneDetectionTF == "5"


def test_size_fields_parsed_from_bare_numbers():
    """Holé číslo = pôvodná Pine jednotka, teda bit-identické správanie."""
    cfg = IBSConfig(minImbSizePoints=2.5, slBufferTicks=2)
    assert cfg.minImbSizePoints == SizeSpec(2.5, "abs")
    assert cfg.slBufferTicks == SizeSpec(2.0, "ticks")


def test_size_field_accepts_explicit_unit():
    cfg = IBSConfig(minImbSizePoints={"value": 0.25, "unit": "atr"})
    assert cfg.minImbSizePoints == SizeSpec(0.25, "atr")


def test_out_of_range_is_rejected():
    with pytest.raises(ConfigError, match="rrRatio"):
        IBSConfig(rrRatio=99.0)


def test_range_not_applied_to_converted_unit():
    """minImbSizePoints má Pine rozsah <1, 30>, ale 0.25 ATR je legitímne."""
    cfg = IBSConfig(minImbSizePoints={"value": 0.25, "unit": "atr"})
    assert cfg.minImbSizePoints.value == 0.25


def test_unknown_detection_tf_rejected():
    with pytest.raises(ConfigError, match="zoneDetectionTF"):
        IBSConfig(zoneDetectionTF="7")


def test_no_entry_model_rejected():
    with pytest.raises(ConfigError, match="entry model"):
        IBSConfig(enableImbEntry=False, enablePinBarEntry=False, enableEngulfingEntry=False)


def test_no_session_rejected():
    with pytest.raises(ConfigError, match="session"):
        IBSConfig(sess1On=False, sess2On=False, sess3On=False)


def test_trailing_offset_above_activation_rejected():
    with pytest.raises(ConfigError, match="trailOffsetR"):
        IBSConfig(trailActivationR=0.5, trailOffsetR=2.0)


def test_unknown_key_rejected():
    with pytest.raises(ConfigError, match="neznáme kľúče"):
        IBSConfig.from_dict({"totalneNeexistujuce": 1})


def test_roundtrip_to_dict():
    cfg = IBSConfig(tradeDirection="Long only", minImbSizePoints={"value": 0.3, "unit": "atr"})
    again = IBSConfig.from_dict(cfg.to_dict())
    assert again.to_dict() == cfg.to_dict()
    assert again.tradeDirection is TradeDirection.LONG_ONLY


# --------------------------------------------------------------------------- #
# InstrumentSpec
# --------------------------------------------------------------------------- #


def test_mnq_reproduces_pine_tick_dollar_value():
    """`tickDollarValue = 0.5` v Pine == MNQ tick 0.25 × $2/bod."""
    assert MNQ.tick_dollar_value == pytest.approx(0.5)


def test_qty_for_risk_matches_pine_formula_on_mnq():
    # SL 20 bodov, riziko $350 -> 350 / (20 x 2) = 8.75 -> 8 kontraktov (celé číslo)
    assert MNQ.qty_for_risk(350.0, 20.0) == 8.0


def test_qty_for_risk_is_fractional_on_crypto():
    # SL $150, riziko $350, point_value 1 -> 2.333 BTC (nie floor na 0 -> max(1,0) ako Pine)
    qty = BTCUSDT_BINANCE.qty_for_risk(350.0, 150.0)
    assert qty == pytest.approx(2.333, abs=1e-3)
    assert qty > BTCUSDT_BINANCE.min_qty


def test_qty_never_below_min_qty():
    assert MNQ.qty_for_risk(1.0, 10_000.0) == MNQ.min_qty


def test_round_qty_steps_down():
    assert BTCUSDT_BINANCE.round_qty(0.0019) == pytest.approx(0.001)


# --------------------------------------------------------------------------- #
# Krížová kontrola config × inštrument
# --------------------------------------------------------------------------- #


def test_mnq_config_has_no_tick_value_warning():
    cfg, inst = load_profile("multicharts_mnq_3m")
    warnings = cfg.check_instrument(inst)
    assert not [w for w in warnings if "tickDollarValue" in w]


def test_mnq_tick_value_on_crypto_is_flagged():
    """Presne tá tichá chyba, ktorá na BTCUSD vypla limit $350."""
    cfg = IBSConfig(tickDollarValue=0.5)
    warnings = cfg.check_instrument(BTCUSDT_BINANCE)
    assert any("tickDollarValue" in w for w in warnings)


def test_risk_limit_that_never_binds_is_flagged():
    """Coinbase profil s MNQ tickDollarValue - TradingView reálne obchodoval qty=1."""
    cfg, inst = load_profile("golden_coinbase_btcusd_3m")
    warnings = cfg.check_instrument(inst)
    assert any("tickDollarValue" in w for w in warnings)


def test_legacy_sizing_reproduces_tradingview_qty_one_on_btc():
    """Referenčný BTC profil musí dať qty=1 — inak sa golden test s TV nikdy nestretne.

    Pine: slDistTicks = 150/0.01 = 15 000; × 0.5 = $7 500; floor(350/7500) = 0 → max(1,0) = 1.
    """
    cfg, inst = load_profile("golden_coinbase_btcusd_3m")
    assert cfg.legacyPineSizing is True
    assert cfg.position_qty(inst, cfg.maxLossDollar, 150.0) == 1.0


def test_fixed_sizing_actually_respects_the_risk_limit():
    """To isté zadanie bez legacy vzorca (Pine default): $350 / $150 SL = 2.333 BTC."""
    cfg = IBSConfig()
    assert cfg.legacyPineSizing is False
    assert cfg.position_qty(BTCUSDT_BINANCE, 350.0, 150.0) == pytest.approx(2.333, abs=1e-3)


def test_legacy_and_fixed_agree_on_mnq():
    """Na MNQ dávajú oba vzorce to isté — rozdiel vzniká až pri qty < 1."""
    cfg, inst = load_profile("multicharts_mnq_3m")
    assert cfg.position_qty(inst, 350.0, 20.0) == inst.qty_for_risk(350.0, 20.0) == 8.0


def test_legacy_sizing_requires_tick_dollar_value():
    with pytest.raises(ConfigError, match="legacyPineSizing"):
        IBSConfig(legacyPineSizing=True, tickDollarValue=None)


def test_legacy_sizing_reports_breakeven_sl_distance():
    """Na Coinbase padne qty na 1 už pri SL nad $7 — reálne SL sú rádovo $100+."""
    cfg, inst = load_profile("golden_coinbase_btcusd_3m")
    warning = next(w for w in cfg.check_instrument(inst) if "vyjde qty=1" in w)
    assert "nad 7 " in warning


def test_legacy_sizing_breakeven_is_harmless_on_mnq():
    """Na MNQ je hranica 175 bodov, teda ďaleko nad reálnymi SL — limit tam funguje."""
    cfg, inst = load_profile("multicharts_mnq_3m")
    warning = next(w for w in cfg.check_instrument(inst) if "vyjde qty=1" in w)
    assert "nad 175 " in warning


def test_volume_filter_flagged_without_real_volume():
    from dataclasses import replace

    forex = replace(BTCUSDT_BINANCE, symbol="EURUSD", has_real_volume=False)
    warnings = IBSConfig(useVolumeFilter=True).check_instrument(forex)
    assert any("volume" in w for w in warnings)


# --------------------------------------------------------------------------- #
# Profily
# --------------------------------------------------------------------------- #


def test_all_profiles_exist():
    """V tradebot/configs/ibs sú len referenčné profily; experimenty a medzikroky sú v docs/profily_archiv/."""
    assert set(list_profiles()) == {"multicharts_mnq_3m", "golden_coinbase_btcusd_3m", "golden_binance_btcusdt_3m"}
    for p in CONFIG_DIR.glob("*.json"):
        assert json.loads(p.read_text(encoding="utf-8")).get("_title"), f"{p.name}: chýba _title pre webapp"


def test_archived_profiles_still_load_by_path():
    """Staré docs sa na ne odkazujú; cesta k súboru musí fungovať všade, kde názov."""
    path = Path("docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json")
    cfg, inst = load_profile(path)
    assert cfg.rrRatio == 5.0 and inst.symbol == "BTC/USDT:USDT"


@pytest.mark.parametrize("name", ["multicharts_mnq_3m", "golden_coinbase_btcusd_3m", "golden_binance_btcusdt_3m"])
def test_profile_loads_and_validates(name):
    cfg, inst = load_profile(name)
    assert isinstance(cfg, IBSConfig)
    assert inst.tick_size > 0


@pytest.mark.parametrize("name", ["multicharts_mnq_3m", "golden_coinbase_btcusd_3m", "golden_binance_btcusdt_3m"])
def test_profiles_apply_the_five_chart_overrides(name):
    """Všetky profily vychádzajú z rovnakých nastavení grafu (docs/tv_settings_2026-09-03.md)."""
    cfg, _ = load_profile(name)
    assert cfg.enablePinBarEntry is True
    assert cfg.enableTrailing is True
    assert cfg.tradeDirection is TradeDirection.LONG_ONLY
    assert cfg.sess2ZoneStartH == 8
    assert cfg.showElliott is False


def test_tv_reference_profile_keeps_pine_units():
    """Referenčný profil pre golden test musí byť bit-identický s tým, čo bežalo v TradingView."""
    cfg, _ = load_profile("golden_binance_btcusdt_3m")
    assert cfg.legacyPineSizing is True
    assert cfg.tickDollarValue == 0.5
    for name, unit in SIZE_FIELDS.items():
        assert getattr(cfg, name).unit == unit, name


def test_coinbase_profile_keeps_pine_units():
    """Referenčný profil musí zostať bit-identický s TradingView."""
    cfg, _ = load_profile("golden_coinbase_btcusd_3m")
    for name, unit in SIZE_FIELDS.items():
        assert getattr(cfg, name).unit == unit, name


def test_profiles_only_contain_overrides():
    """Profil má byť čitateľný diff proti Pine defaultom, nie výpis všetkých 115 polí."""
    defaults = IBSConfig().to_dict()
    for path in CONFIG_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, value in data.items():
            if key.startswith("_"):
                continue
            assert defaults[key] != value, f"{path.name}: {key} je zhodné s defaultom, netreba ho tam"


def test_unknown_profile_lists_available():
    with pytest.raises(ConfigError, match="multicharts_mnq_3m"):
        load_profile("neexistuje")
