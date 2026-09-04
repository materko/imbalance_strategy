"""Trailing stop — Pine `strategy.exit(trail_points=, trail_offset=)`.

Dlho tu nič nebolo, lebo pri `rrRatio = 1` sa trailing **nikdy neprejaví**: aktivuje
sa presne na úrovni, kde je už TP, takže obchod skončí skôr. Referenčný golden beh
bol práve taký, a tak vyzeralo všetko v poriadku aj bez implementácie. Pri RR 2,5 je
TP ďaleko, trailing rozhoduje o väčšine výstupov a rozdiel je okamžite vidieť.

Najchúlostivejšia je časť o poradí pohybu vnútri sviečky — viď `extreme_before_stop`.
"""

from __future__ import annotations

import pytest

from ibs.core import IBSConfig
from ibs.core.risk import TrailingPlan, extreme_before_stop
from ibs.core.types import Direction, InstrumentSpec

INST = InstrumentSpec(
    symbol="TEST", venue="test", tick_size=0.1, point_value=1.0, qty_step=0.001, min_qty=0.001
)


@pytest.fixture
def plan() -> TrailingPlan:
    """Aktivácia na 1R, odstup 0,5R, riziko 100 bodov."""
    cfg = IBSConfig()
    cfg.enableTrailing = True
    cfg.trailActivationR = 1.0
    cfg.trailOffsetR = 0.5
    return TrailingPlan.build(cfg, INST, 100.0)


def test_vypnuty_trailing_nedava_plan():
    cfg = IBSConfig()
    cfg.enableTrailing = False
    assert TrailingPlan.build(cfg, INST, 100.0) is None


def test_pred_aktivaciou_plati_povodny_stop(plan):
    # +99 bodov, aktivácia je až na +100
    assert plan.stop_price(Direction.LONG, 1000.0, 900.0, 1099.0) == 900.0


def test_po_aktivacii_sleduje_extrem(plan):
    assert plan.stop_price(Direction.LONG, 1000.0, 900.0, 1100.0) == pytest.approx(1050.0)
    assert plan.stop_price(Direction.LONG, 1000.0, 900.0, 1200.0) == pytest.approx(1150.0)


def test_stop_sa_nikdy_nevracia(plan):
    """Tesne po aktivácii je trailing ešte POD pôvodným SL — vtedy platí SL."""
    tight = TrailingPlan.build(_cfg(activation=1.0, offset=3.0), INST, 100.0)
    assert tight.stop_price(Direction.LONG, 1000.0, 900.0, 1100.0) == 900.0


def test_short_ide_opacne(plan):
    assert plan.stop_price(Direction.SHORT, 1000.0, 1100.0, 901.0) == 1100.0
    assert plan.stop_price(Direction.SHORT, 1000.0, 1100.0, 900.0) == pytest.approx(950.0)
    assert plan.stop_price(Direction.SHORT, 1000.0, 1100.0, 800.0) == pytest.approx(850.0)


def _cfg(*, activation: float, offset: float) -> IBSConfig:
    cfg = IBSConfig()
    cfg.enableTrailing = True
    cfg.trailActivationR = activation
    cfg.trailOffsetR = offset
    return cfg


# --------------------------------------------------------------------------- #
# Poradie pohybu vnútri sviečky
# --------------------------------------------------------------------------- #


def test_bliszsi_extrem_k_openu_nastane_skor():
    # LONG: high blízko openu -> priaznivý extrém prvý
    assert extreme_before_stop(100.0, 101.0, 90.0, long=True) is True
    # LONG: low blízko openu -> najprv sa ide proti nám
    assert extreme_before_stop(100.0, 110.0, 99.0, long=True) is False


def test_pre_short_je_priaznivy_extrem_low():
    assert extreme_before_stop(100.0, 110.0, 99.0, long=False) is True
    assert extreme_before_stop(100.0, 101.0, 90.0, long=False) is False


def test_realny_bar_z_tradingview():
    """BTCUSDT 3m, 2026-08-28 16:51 — bar, na ktorom sa port rozišiel s TradingView.

    Low je od openu 4,3 bodu, high 240,6. Cena teda šla najprv dole; trailing sa
    aktivoval až na konci baru a obchod pokračoval ďalších 6 minút.
    """
    assert extreme_before_stop(79250.0, 79490.6, 79245.7, long=True) is False


# --------------------------------------------------------------------------- #
# Celý výstup cez simulátor
# --------------------------------------------------------------------------- #


@pytest.fixture
def sim_trade():
    from ibs.core.risk import TradePlan
    from ibs.tools.scan_trades import SimTrade

    plan = TradePlan(
        direction=Direction.LONG,
        entry=1000.0,
        stop_loss=900.0,
        take_profit=1250.0,
        qty=1.0,
        sl_distance=100.0,
        trailing=TrailingPlan.build(_cfg(activation=1.0, offset=0.5), INST, 100.0),
    )
    return SimTrade(order_id="x", direction=Direction.LONG, plan=plan, placed_ms=0,
                    outcome="FILLED", extreme=1000.0)


def _bar(o, h, l, c):
    from ibs.core import Bar

    return Bar(time=0, open=o, high=h, low=l, close=c, volume=1.0)


def test_priaznivy_extrem_prvy_moze_vyhodit_v_tej_istej_sviecke(sim_trade):
    from ibs.tools.scan_trades import FillSimulator

    # open 1000 -> high 1200 (blizsie k openu nez low) -> low 1100 -> close
    stop, hit = FillSimulator._trailing(sim_trade, _bar(1190.0, 1200.0, 1100.0, 1150.0), True)
    assert stop == pytest.approx(1150.0)
    assert hit is True


def test_nepriaznivy_extrem_prvy_testuje_este_stary_stop(sim_trade):
    from ibs.tools.scan_trades import FillSimulator

    # Cena najprv spadne na povodny SL - trailing to uz nezachrani.
    stop, hit = FillSimulator._trailing(sim_trade, _bar(999.0, 1200.0, 899.0, 1150.0), True)
    assert stop == pytest.approx(900.0)
    assert hit is True


def test_navrat_k_zatvoreniu_sa_tiez_testuje(sim_trade):
    """Bar išiel najprv dole, potom na extrém a vrátil sa pod trailing do close."""
    from ibs.tools.scan_trades import FillSimulator

    stop, hit = FillSimulator._trailing(sim_trade, _bar(1001.0, 1200.0, 1000.0, 1120.0), True)
    assert stop == pytest.approx(1150.0)
    assert hit is True


def test_ked_sa_close_udrzi_nad_trailingom_obchod_zije(sim_trade):
    """Ten istý tvar baru, len close ostal nad trailingom — presne prípad z TradingView."""
    from ibs.tools.scan_trades import FillSimulator

    stop, hit = FillSimulator._trailing(sim_trade, _bar(1001.0, 1200.0, 1000.0, 1180.0), True)
    assert hit is False
    assert sim_trade.extreme == pytest.approx(1200.0)
