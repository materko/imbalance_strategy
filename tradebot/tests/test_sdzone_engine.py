"""SD Zones: engine na syntetických baroch.

Testuje sa mechanika: či zóna vznikne len pri dosť silnom impulze, ako sa klasifikujú
štyri formácie, či sa obchoduje až návrat do zóny, a či čerstvosť naozaj drží.
"""

from __future__ import annotations

import pytest

from tradebot.core import BTCUSDT_BINANCE, Bar, DrawKind, MarketContext, OrderAction
from tradebot.core.types import Direction, OrderType
from tradebot.strategies.sdzone import EntryMode, PatternSet, SDZoneConfig, SDZoneEngine, ZoneMode

#: utorok 2025-09-02 14:00 UTC = 10:00 New York — pracovný deň, inak by `weekdaysOnly` bránil
T0 = 1_756_821_600_000
MIN15 = 900_000
OKNO = MarketContext(in_trade_window=True)


def bar(i: int, o=100.0, h=100.6, low=99.4, c=100.0, v=10.0) -> Bar:
    return Bar(time=T0 + i * MIN15, open=o, high=h, low=low, close=c, volume=v)


def _engine(**kw) -> SDZoneEngine:
    return SDZoneEngine(SDZoneConfig(**kw), BTCUSDT_BINANCE, 15)


def rozbeh(e: SDZoneEngine, n: int = 30) -> None:
    """Pokojné bary, aby sa naplnil ATR — striedavé závery, nenulový rozsah."""
    for i in range(n):
        c = 100.3 if i % 2 else 99.7
        e.on_bar(bar(i, o=100.0, h=100.6, low=99.4, c=c), None, OKNO)


def demand_formacia(e: SDZoneEngine, i0: int = 30) -> int:
    """Príchod hore, krátka báza s malými telami, silný impulz hore = RBR demand."""
    e.on_bar(bar(i0, o=99.5, h=100.7, low=99.4, c=100.6), None, OKNO)          # rally
    e.on_bar(bar(i0 + 1, o=100.52, h=100.8, low=100.4, c=100.62), None, OKNO)  # báza
    e.on_bar(bar(i0 + 2, o=100.6, h=103.5, low=100.5, c=103.4), None, OKNO)    # impulz
    return i0 + 2


def test_defaults_a_required_history():
    cfg = SDZoneConfig()
    assert cfg.zoneMode is ZoneMode.WFZ and cfg.rrRatio == 3.0
    e = SDZoneEngine(cfg, BTCUSDT_BINANCE, 15)
    assert e.required_history >= cfg.atrLen + cfg.baseMaxBars


def test_slaby_impulz_zonu_nevytvori():
    e = _engine(impulseMinBodyAtr=3.0)     # nереálne prísny prah
    rozbeh(e)
    demand_formacia(e)
    assert not e._zones


def test_silny_impulz_vytvori_demand_zonu():
    e = _engine()
    rozbeh(e)
    demand_formacia(e)
    assert len(e._zones) == 1
    z = e._zones[0]
    assert z.direction is Direction.LONG and z.pattern == "RBR" and z.continuation
    assert z.bottom < z.top


def test_vstup_az_pri_navrate_do_zony():
    e = _engine()
    rozbeh(e)
    i = demand_formacia(e)
    z = e._zones[0]
    out = e.on_bar(bar(i + 1, o=103.4, h=104.0, low=103.0, c=103.8), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY], "bez návratu sa nevstupuje"
    out = e.on_bar(bar(i + 2, o=103.0, h=103.2, low=z.top - 0.1, c=101.5), None, OKNO)
    vst = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(vst) == 1
    intent = vst[0]
    assert intent.direction is Direction.LONG and intent.order_type is OrderType.LIMIT
    plan = intent.plan
    assert plan.stop_loss < z.bottom <= plan.entry < plan.take_profit
    assert plan.take_profit - plan.entry == pytest.approx(
        plan.sl_distance * SDZoneConfig().rrRatio, abs=4 * BTCUSDT_BINANCE.tick_size)


def test_zona_sa_po_pouziti_znova_neobchoduje():
    e = _engine()
    rozbeh(e)
    i = demand_formacia(e)
    z = e._zones[0]
    e.on_bar(bar(i + 1, o=103.0, h=103.2, low=z.top - 0.1, c=101.5), None, OKNO)
    e._pending = None
    e._trades_today = 0
    out = e.on_bar(bar(i + 2, o=101.5, h=101.8, low=z.top - 0.1, c=101.6), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_short_zo_supply_zony():
    e = _engine()
    rozbeh(e)
    e.on_bar(bar(30, o=100.5, h=100.6, low=99.3, c=99.4), None, OKNO)          # drop
    e.on_bar(bar(31, o=99.4, h=99.6, low=99.2, c=99.4), None, OKNO)           # báza
    e.on_bar(bar(32, o=99.4, h=99.5, low=96.5, c=96.6), None, OKNO)           # impulz dole
    assert len(e._zones) == 1 and e._zones[0].direction is Direction.SHORT
    assert e._zones[0].pattern == "DBD"
    z = e._zones[0]
    out = e.on_bar(bar(33, o=97.0, h=z.bottom + 0.1, low=96.8, c=98.0), None, OKNO)
    vst = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(vst) == 1 and vst[0].direction is Direction.SHORT
    assert vst[0].plan.take_profit < vst[0].plan.entry < vst[0].plan.stop_loss


def test_long_only_supply_zonu_nevytvori():
    e = _engine(tradeDirection="Long only")
    rozbeh(e)
    e.on_bar(bar(30, o=100.5, h=100.6, low=99.3, c=99.4), None, OKNO)
    e.on_bar(bar(31, o=99.4, h=99.6, low=99.2, c=99.4), None, OKNO)
    e.on_bar(bar(32, o=99.4, h=99.5, low=96.5, c=96.6), None, OKNO)
    assert not e._zones


def test_len_obratove_formacie_odmietnu_RBR():
    e = _engine(patterns=PatternSet.REVERSAL)
    rozbeh(e)
    demand_formacia(e)          # RBR je pokračovacia
    assert not e._zones


def test_pfz_je_uzsia_nez_wfz():
    """Porovnáva sa POSLEDNÁ zóna — tá z testovanej formácie.

    Zahrievacie bary sú tiež platná konsolidácia, takže pri prvej impulznej sviečke
    vznikne zóna aj z nich; `_zones[0]` by teda porovnával niečo iné.
    """
    def rbr(e):
        e2 = [z for z in e._zones if z.pattern == "RBR"]
        assert e2, "formácia RBR mala vytvoriť zónu"
        return e2[-1]

    e1 = _engine(zoneMode=ZoneMode.WFZ); rozbeh(e1); demand_formacia(e1)
    e2 = _engine(zoneMode=ZoneMode.PFZ); rozbeh(e2); demand_formacia(e2)
    assert rbr(e2).height < rbr(e1).height


def test_vstup_close_potrebuje_zaver_v_zone():
    e = _engine(entryMode=EntryMode.CLOSE)
    rozbeh(e)
    i = demand_formacia(e)
    z = e._zones[0]
    out = e.on_bar(bar(i + 1, o=103.0, h=103.2, low=z.top - 0.1, c=101.5), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY], "záver mimo zóny nestačí"
    out = e.on_bar(bar(i + 2, o=101.0, h=101.2, low=z.bottom, c=(z.top + z.bottom) / 2), None, OKNO)
    assert [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_kresby_su_registrovane_druhy():
    e = _engine()
    rozbeh(e)
    i = demand_formacia(e)
    z = e._zones[0]
    out = e.on_bar(bar(i + 1, o=103.0, h=103.2, low=z.top - 0.1, c=101.5), None, OKNO)
    kinds = {o.kind for o in out.drawings}
    assert kinds
    for k in kinds:
        assert DrawKind(k.value) is k
