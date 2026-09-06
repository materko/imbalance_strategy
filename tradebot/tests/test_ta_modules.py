"""Display-only moduly: Market Structure, S/R, likvidita, Elliott.

Neovplyvňujú obchody (v referenčných profiloch sú ich trading prepínače vypnuté),
ale kreslia väčšinu toho, čo je na grafe vidieť — preto sa testujú samostatne.
"""

from __future__ import annotations

import pytest

from tradebot.core import Bar, DrawKind, IBSConfig
from tradebot.core.history import BarHistory
from tradebot.strategies.ibs.ta import ElliottWaves, LiquiditySweep, MarketStructure, SupportResistance, pivot
from tradebot.core.types import BTCUSDT_BINANCE

MIN = 60_000


def bar(i: int, high: float, low: float, close: float | None = None) -> Bar:
    c = close if close is not None else (high + low) / 2
    return Bar(time=i * MIN, open=c, high=high, low=low, close=c, volume=1.0)


def history_of(bars: list[Bar]) -> BarHistory:
    h = BarHistory(maxlen=500)
    for b in bars:
        h.append(b)
    return h


# --------------------------------------------------------------------------- #
# pivot
# --------------------------------------------------------------------------- #


def test_pivot_najde_vrchol_v_strede_okna():
    h = history_of([bar(0, 10, 5), bar(1, 20, 5), bar(2, 10, 5)])
    assert pivot(h, 1, high=True) == 20


def test_pivot_pripusta_zhodu_vlavo():
    """Pine je na ľavej strane zhovievavý — rovnaké high pivot nezruší.

    Bez tejto asymetrie sa zahadzujú pivoty, ktoré TradingView nájde: na Elliott
    zigzagu to znamenalo 32 z 41 bodov namiesto 41 z 41.
    """
    h = history_of([bar(0, 20, 5), bar(1, 20, 5), bar(2, 10, 5)])
    assert pivot(h, 1, high=True) == 20


def test_pivot_je_prisny_vpravo():
    """Vpravo (novšie bary) už zhoda pivot ruší."""
    h = history_of([bar(0, 10, 5), bar(1, 20, 5), bar(2, 20, 5)])
    assert pivot(h, 1, high=True) is None


def test_pivot_potrebuje_cele_okno():
    h = history_of([bar(0, 10, 5), bar(1, 20, 5)])
    assert pivot(h, 1, high=True) is None


def test_pivot_zo_close_ignoruje_knot():
    """S/R aj likvidita počítajú pivot z close — knôt sám úroveň nezaloží."""
    bars = [bar(0, 10, 5, close=8), bar(1, 99, 5, close=8), bar(2, 10, 5, close=8)]
    h = history_of(bars)
    assert pivot(h, 1, high=True) == 99  # z high áno
    assert pivot(h, 1, high=True, source="close") is None  # z close nie


# --------------------------------------------------------------------------- #
# Market Structure
# --------------------------------------------------------------------------- #


@pytest.fixture
def cfg() -> IBSConfig:
    c = IBSConfig()
    c.structureSwingLen = 2
    c.showMarketStructure = True
    return c


def _run_structure(cfg: IBSConfig, bars: list[Bar]):
    ms = MarketStructure(cfg, BTCUSDT_BINANCE)
    h = BarHistory(maxlen=500)
    out = []
    for b in bars:
        h.append(b)
        out += ms.on_bar(b, h)
    return ms, out


def test_bos_vznikne_az_ked_cena_prerazi_swing(cfg):
    # vrchol na indexe 2, potom pokles a prerazenie
    bars = [bar(0, 10, 8), bar(1, 11, 9), bar(2, 20, 15, close=18),
            bar(3, 12, 9), bar(4, 13, 9), bar(5, 14, 10, close=12)]
    ms, out = _run_structure(cfg, bars)
    assert ms.bias == 0  # 12 < 18, swing ešte nie je prerazený
    bars.append(bar(6, 25, 20, close=24))
    ms, out = _run_structure(cfg, bars)
    assert ms.bias == 1
    texts = [o.text for o in out if o.kind is DrawKind.STRUCTURE]
    assert "BOS" in texts


def test_choch_ked_sa_smer_otoci(cfg):
    """Prerazenie proti doterajšiemu biasu je CHoCH, nie BOS."""
    ms = MarketStructure(cfg, BTCUSDT_BINANCE)
    ms.bias = -1
    h = BarHistory(maxlen=500)
    out = []
    for b in [bar(0, 10, 8), bar(1, 11, 9), bar(2, 20, 15, close=18),
              bar(3, 12, 9), bar(4, 13, 9), bar(5, 25, 20, close=24)]:
        h.append(b)
        out += ms.on_bar(b, h)
    assert ms.bias == 1
    assert "CHoCH" in [o.text for o in out if o.kind is DrawKind.STRUCTURE]


def test_swing_stitky_rozlisia_hh_od_lh(cfg):
    bars = [bar(0, 10, 8), bar(1, 11, 9), bar(2, 20, 15), bar(3, 12, 9), bar(4, 11, 9),
            bar(5, 12, 9), bar(6, 18, 14), bar(7, 11, 9), bar(8, 10, 8)]
    _, out = _run_structure(cfg, bars)
    texts = [o.text for o in out if o.kind is DrawKind.SWING]
    assert "LH" in texts  # druhý vrchol (18) je nižší než prvý (20)


# --------------------------------------------------------------------------- #
# Support / Resistance
# --------------------------------------------------------------------------- #


def test_sr_zluci_blizke_dotyky_do_jednej_urovne():
    c = IBSConfig()
    c.srClusterPoints = 5.0
    sr = SupportResistance(c, BTCUSDT_BINANCE)
    sr._add_touch(100.0, 1, 0)
    sr._add_touch(102.0, 1, MIN)
    assert len(sr.levels) == 1 and sr.levels[0].touches == 2
    assert sr.levels[0].low == 100.0 and sr.levels[0].high == 102.0


def test_sr_vzdialeny_dotyk_zalozi_novu_uroven():
    c = IBSConfig()
    c.srClusterPoints = 5.0
    sr = SupportResistance(c, BTCUSDT_BINANCE)
    sr._add_touch(100.0, 1, 0)
    sr._add_touch(200.0, 1, MIN)
    assert len(sr.levels) == 2


def test_sr_nezluci_support_s_resistance():
    """Zhlukovanie dotykov je per typ; spájajú sa až pri kreslení."""
    c = IBSConfig()
    c.srClusterPoints = 5.0
    sr = SupportResistance(c, BTCUSDT_BINANCE)
    sr._add_touch(100.0, 1, 0)
    sr._add_touch(100.0, -1, MIN)
    assert len(sr.levels) == 2


def test_sr_zabudne_stare_urovne():
    c = IBSConfig()
    c.srLookbackDays = 1
    sr = SupportResistance(c, BTCUSDT_BINANCE)
    sr._add_touch(100.0, 1, 0)
    sr._forget_old(Bar(time=2 * 86_400_000, open=1, high=1, low=1, close=1, volume=0))
    assert sr.levels == []


def test_sr_zhluk_dvoch_urovni_je_golden_zone():
    c = IBSConfig()
    c.srClusterPoints = 5.0
    c.srMinTouches = 1
    sr = SupportResistance(c, BTCUSDT_BINANCE)
    # dva rôzne typy, blízko pri sebe -> pri kreslení sa spoja
    sr._add_touch(100.0, 1, 0)
    sr._add_touch(101.0, -1, 0)
    out = sr.render(Bar(time=MIN, open=100, high=100, low=100, close=100, volume=0))
    assert {o.kind for o in out} == {DrawKind.SR_GOLDEN}


def test_sr_typ_zavisi_od_polohy_ceny():
    """Prerazená resistance sa stáva supportom — typ nie je vlastnosť úrovne."""
    c = IBSConfig()
    c.srMinTouches = 1
    sr = SupportResistance(c, BTCUSDT_BINANCE)
    sr._add_touch(100.0, 1, 0)

    above = sr.render(Bar(time=MIN, open=0, high=0, low=0, close=150, volume=0))
    below = sr.render(Bar(time=MIN, open=0, high=0, low=0, close=50, volume=0))
    assert above[0].fill_color != below[0].fill_color


# --------------------------------------------------------------------------- #
# Likvidita
# --------------------------------------------------------------------------- #


def _liq_cfg() -> IBSConfig:
    c = IBSConfig()
    c.liqSweepLen = 1
    c.liqStrengthLen = 50
    c.liqSweepMinWick = 1.0
    c.liqSweepConfirmBars = 2
    c.showLiqSweep = True
    return c


def test_sweep_vznikne_az_po_potvrdenom_navrate():
    liq = LiquiditySweep(_liq_cfg(), BTCUSDT_BINANCE)
    h = BarHistory(maxlen=500)
    out = []
    # Bar 4 musí mať vyššie high než bar 3, inak by sa z baru 3 stal nový pivot
    # a sledovaná úroveň by sa resetovala — presne ako v Pine.
    for b in [bar(0, 10, 8, close=9), bar(1, 20, 15, close=18), bar(2, 12, 9, close=10),
              bar(3, 25, 12, close=22),   # prepichnutie nad 20
              bar(4, 26, 15, close=16)]:  # zatvorenie späť pod 20
        h.append(b)
        cmds, _ = liq.on_bar(b, h)
        out += cmds
    assert any(o.kind is DrawKind.LIQ_SWEEP for o in out)


def test_bez_navratu_to_nie_je_sweep_ale_breakout():
    c = _liq_cfg()
    c.liqSweepConfirmBars = 1
    liq = LiquiditySweep(c, BTCUSDT_BINANCE)
    h = BarHistory(maxlen=500)
    out = []
    for b in [bar(0, 10, 8, close=9), bar(1, 20, 15, close=18), bar(2, 12, 9, close=10),
              bar(3, 25, 12, close=24), bar(4, 26, 22, close=25), bar(5, 27, 23, close=26)]:
        h.append(b)
        cmds, _ = liq.on_bar(b, h)
        out += cmds
    assert not any(o.kind is DrawKind.LIQ_SWEEP for o in out)


def test_sweep_zona_ide_proti_prepichnutiu():
    c = _liq_cfg()
    c.enableLqTrading = True
    liq = LiquiditySweep(c, BTCUSDT_BINANCE)
    h = BarHistory(maxlen=500)
    zones = []
    for b in [bar(0, 10, 8, close=9), bar(1, 20, 15, close=18), bar(2, 12, 9, close=10),
              bar(3, 25, 12, close=22), bar(4, 26, 15, close=16)]:
        h.append(b)
        _, z = liq.on_bar(b, h)
        zones += z
    from tradebot.core.types import Direction

    assert [z.direction for z in zones] == [Direction.SHORT]


# --------------------------------------------------------------------------- #
# Elliott
# --------------------------------------------------------------------------- #


def _ew(min_wave: float = 1.0) -> ElliottWaves:
    c = IBSConfig()
    c.ewMinWavePoints = min_wave
    c.showElliott = True
    return ElliottWaves(c, BTCUSDT_BINANCE, 3 * MIN)


def test_zigzag_posunie_bod_pri_extremnejsom_pivote():
    ew = _ew()
    b = bar(0, 1, 1)
    assert ew._add(100.0, 0, 1, b) is True
    assert ew._add(110.0, MIN, 1, b) is False  # ten istý typ, len posun
    assert len(ew.points) == 1 and ew.points[0].price == 110.0


def test_zigzag_ignoruje_prilis_malu_vlnu():
    ew = _ew(min_wave=50.0)
    b = bar(0, 1, 1)
    ew._add(100.0, 0, 1, b)
    assert ew._add(95.0, MIN, -1, b) is False
    assert len(ew.points) == 1


def test_ucebnicovy_impulz_prejde_vsetkymi_troma_pravidlami():
    """Rastúci 1-2-3-4-5: vlna 2 nad začiatkom, 3 nie je najkratšia, 4 nad vrcholom 1."""
    ew = _ew()
    b = bar(0, 1, 1)
    for i, (price, typ) in enumerate(
        [(100.0, -1), (120.0, 1), (110.0, -1), (160.0, 1), (140.0, -1), (180.0, 1)]
    ):
        ew._add(price, i * MIN, typ, b)
    assert ew._valid_impulse(ew.points) is True


def test_vlna_2_pod_zaciatkom_impulz_zrusi():
    ew = _ew()
    b = bar(0, 1, 1)
    for i, (price, typ) in enumerate(
        [(100.0, -1), (120.0, 1), (90.0, -1), (160.0, 1), (140.0, -1), (180.0, 1)]
    ):
        ew._add(price, i * MIN, typ, b)
    assert ew._valid_impulse(ew.points) is False


def test_vlna_3_ako_najkratsia_impulz_zrusi():
    ew = _ew()
    b = bar(0, 1, 1)
    # vlna1=50, vlna3=10, vlna5=60 -> 3 je najkratšia
    for i, (price, typ) in enumerate(
        [(100.0, -1), (150.0, 1), (140.0, -1), (150.0, 1), (145.0, -1), (205.0, 1)]
    ):
        ew._add(price, i * MIN, typ, b)
    assert ew._valid_impulse(ew.points) is False


def test_projekcia_vlny_5_pouzije_vsetky_tri_odhady():
    ew = _ew()
    b = bar(0, 1, 1)
    for i, (price, typ) in enumerate(
        [(100.0, -1), (120.0, 1), (110.0, -1), (160.0, 1), (140.0, -1)]
    ):
        ew._add(price, i * MIN, typ, b)
    out = ew._wave5_target(ew.points, "#334155")
    box = next(o for o in out if o.kind is DrawKind.ELLIOTT_PROJ and hasattr(o, "y1"))
    # rovnosť s vlnou 1 = 140+20 = 160; 61.8% z pohybu 1-3 (60) = 177; 1.618*20 = 172
    assert box.y2 == pytest.approx(160.0)
    assert box.y1 == pytest.approx(140 + 0.618 * 60)


def test_projekcia_ma_sirku_v_baroch_nie_v_minutach():
    """`ewProjExtendBars` je v BAROCH — na 3m grafe je to 3× dlhšie než v minútach."""
    ew = _ew()
    ew.cfg.ewProjExtendBars = 10
    assert ew._proj_span_ms() == 10 * 3 * MIN
