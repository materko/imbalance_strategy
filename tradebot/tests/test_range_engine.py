"""Range Breakout: engine na syntetických baroch.

Testuje sa mechanika, nie edge: či sa range nájde len keď je dosť tesný, či prerazenie
dá order so správnym SL/TP, ako sa správajú tri režimy vstupu a či zlyhané prerazenie
setup zahodí.
"""

from __future__ import annotations

import pytest

from tradebot.core import BTCUSDT_BINANCE, Bar, DrawKind, MarketContext, OrderAction
from tradebot.core.types import Direction, OrderType
from tradebot.strategies.range import BoundaryMode, EntryMode, RangeConfig, RangeEngine, SlMode

#: utorok 2025-09-02 14:00 UTC = 10:00 New York — vnútri pracovného týždňa,
#: inak by `weekdaysOnly` obchody odmietol a testy by merali nesprávnu vec.
T0 = 1_756_821_600_000
MIN3 = 180_000
OKNO = MarketContext(in_trade_window=True)


def bar(i: int, o=100.0, h=100.6, low=99.4, c=100.0, v=10.0) -> Bar:
    return Bar(time=T0 + i * MIN3, open=o, high=h, low=low, close=c, volume=v)


def _engine(**kw) -> RangeEngine:
    cfg = RangeConfig(**kw)
    return RangeEngine(cfg, BTCUSDT_BINANCE, 3)


def warm(engine: RangeEngine, n: int = 40) -> None:
    """Bary v úzkom pásme — závery striedavo 99,7 a 100,4, takže range má nenulovú šírku."""
    for i in range(n):
        c = 100.4 if i % 2 else 99.7
        engine.on_bar(bar(i, o=100.0, h=100.6, low=99.4, c=c), None, OKNO)


def test_defaults_validate_and_required_history():
    cfg = RangeConfig()
    assert cfg.maxWidthAtr.unit == "atr" and cfg.minWidthAtr.unit == "atr"
    engine = RangeEngine(cfg, BTCUSDT_BINANCE, 3)
    assert engine.required_history == cfg.atrLen + cfg.lookbackBars + 8


def test_prilis_siroke_okno_nie_je_range():
    """Keď sa cena hýbe naprieč širokým pásmom, žiadny range nevznikne."""
    engine = _engine(minWidthAtr=0.05, maxWidthAtr=0.5)   # veľmi prísny strop
    for i in range(40):
        # striedavo hore-dole o veľa -> okno je široké
        c = 100.0 + (8.0 if i % 2 else -8.0)
        engine.on_bar(bar(i, o=c, h=c + 1, low=c - 1, c=c), None, OKNO)
    assert engine._rng is None


def test_prerazenie_hore_da_market_order_so_stopom_pod_rangom():
    engine = _engine()
    warm(engine)
    assert engine._rng is not None, "z úzkych barov mal vzniknúť range"
    hranica = engine._rng.high
    out = engine.on_bar(bar(40, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    entries = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1
    intent = entries[0]
    assert intent.direction is Direction.LONG and intent.order_type is OrderType.MARKET
    plan = intent.plan
    assert plan.stop_loss < hranica <= plan.entry < plan.take_profit
    # entry aj stop sú zaokrúhlené na tick, takže sa porovnáva s toleranciou pár tickov
    assert plan.take_profit - plan.entry == pytest.approx(
        plan.sl_distance * RangeConfig().rrRatio, abs=4 * BTCUSDT_BINANCE.tick_size)
    assert plan.qty > 0


def test_prerazenie_dole_da_short():
    engine = _engine()
    warm(engine)
    out = engine.on_bar(bar(40, o=100.0, h=100.1, low=97.0, c=97.2), None, OKNO)
    entries = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1
    plan = entries[0].plan
    assert entries[0].direction is Direction.SHORT
    assert plan.take_profit < plan.entry < plan.stop_loss


def test_long_only_nevstupi_do_shortu():
    engine = _engine(tradeDirection="Long only")
    warm(engine)
    out = engine.on_bar(bar(40, o=100.0, h=100.1, low=97.0, c=97.2), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_retest_vstupi_az_pri_navrate_na_hranicu():
    engine = _engine(entryMode=EntryMode.RETEST)
    warm(engine)
    hranica = engine._rng.high
    out = engine.on_bar(bar(40, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY], "retest nevstupuje hneď"
    # cena sa vráti na hranicu, ale nezavrie pod ňou (inak by to bolo zlyhané prerazenie)
    out = engine.on_bar(bar(41, o=102.5, h=103.0, low=hranica - 0.2, c=102.6), None, OKNO)
    entries = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1
    assert entries[0].order_type is OrderType.LIMIT
    assert entries[0].plan.entry == pytest.approx(hranica, abs=0.5)


def test_continuation_caka_na_potvrdzujuci_zaver_po_retestte():
    engine = _engine(entryMode=EntryMode.CONTINUATION)
    warm(engine)
    hranica = engine._rng.high
    engine.on_bar(bar(40, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    out = engine.on_bar(bar(41, o=102.5, h=103.0, low=hranica - 0.2, c=102.6), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY], "po retestte sa ešte čaká"
    out = engine.on_bar(bar(42, o=102.6, h=104.0, low=102.5, c=103.9), None, OKNO)
    entries = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1 and entries[0].order_type is OrderType.MARKET


def test_zlyhane_prerazenie_zahodi_setup():
    engine = _engine(entryMode=EntryMode.RETEST)
    warm(engine)
    engine.on_bar(bar(40, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    assert engine._rng is not None
    # zaver spat vnutri rangu -> prerazenie zlyhalo
    engine.on_bar(bar(41, o=102.0, h=102.1, low=99.8, c=100.0), None, OKNO)
    assert engine._rng is None


def test_druhy_zaver_je_vyzadovany_ked_je_zapnuty():
    engine = _engine(requireSecondClose=True)
    warm(engine)
    out = engine.on_bar(bar(40, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY], "prvý záver nestačí"
    out = engine.on_bar(bar(41, o=102.8, h=103.5, low=102.5, c=103.2), None, OKNO)
    assert [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_sl_mid_je_blizsie_nez_opposite():
    e1 = _engine(slMode=SlMode.OPPOSITE); warm(e1)
    o1 = e1.on_bar(bar(40, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    e2 = _engine(slMode=SlMode.MID); warm(e2)
    o2 = e2.on_bar(bar(40, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    p1 = [o for o in o1.orders if o.action is OrderAction.ENTRY][0].plan
    p2 = [o for o in o2.orders if o.action is OrderAction.ENTRY][0].plan
    assert p2.stop_loss > p1.stop_loss and p2.sl_distance < p1.sl_distance


def test_hranice_zo_zaverov_su_uzsie_nez_z_extremov():
    e1 = _engine(boundaryMode=BoundaryMode.CLOSE); warm(e1)
    e2 = _engine(boundaryMode=BoundaryMode.EXTREME); warm(e2)
    assert e1._rng.height < e2._rng.height


def test_kresby_su_registrovane_druhy():
    engine = _engine()
    warm(engine)
    out = engine.on_bar(bar(40, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    kinds = {o.kind for o in out.drawings}
    assert kinds, "engine má pri vstupe niečo nakresliť"
    for k in kinds:
        assert DrawKind(k.value) is k


def test_max_obchodov_za_den_drzi():
    engine = _engine(maxTradesPerDay=1, cooldownBars=0)
    warm(engine)
    out = engine.on_bar(bar(40, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    assert [o for o in out.orders if o.action is OrderAction.ENTRY]
    engine._pending = None            # ako keby order dobehol a pozícia sa zavrela
    for i in range(41, 70):
        engine.on_bar(bar(i), None, OKNO)
    out = engine.on_bar(bar(70, o=100.0, h=103.0, low=99.9, c=102.8), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY], "druhý obchod v ten istý deň"
