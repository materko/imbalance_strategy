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


def zona(e: SDZoneEngine, pattern: str) -> "object":
    """Posledná zóna danej formácie.

    Zahrievacie bary sú tiež platná konsolidácia a rally bar pred bázou je sám impulzom
    (DBR) — s meraním odchodu jeho zóna dobehne na tom istom bare ako testovaná formácia,
    takže `_zones[0]` by bol niečo iné.
    """
    zony = [z for z in e._zones if z.pattern == pattern]
    assert zony, f"formácia {pattern} mala vytvoriť zónu"
    return zony[-1]


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
    z = zona(e, "RBR")
    assert z.direction is Direction.LONG and z.pattern == "RBR" and z.continuation
    assert z.bottom < z.top


def test_vstup_az_pri_navrate_do_zony():
    e = _engine()
    rozbeh(e)
    i = demand_formacia(e)
    z = zona(e, "RBR")
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
    z = zona(e, "RBR")
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
    z = zona(e, "DBD")
    assert z.direction is Direction.SHORT
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
    assert not [z for z in e._zones if z.pattern == "RBR"]


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
    z = zona(e, "RBR")
    out = e.on_bar(bar(i + 1, o=103.0, h=103.2, low=z.top - 0.1, c=101.5), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY], "záver mimo zóny nestačí"
    out = e.on_bar(bar(i + 2, o=101.0, h=101.2, low=z.bottom, c=(z.top + z.bottom) / 2), None, OKNO)
    assert [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_kresby_su_registrovane_druhy():
    e = _engine()
    rozbeh(e)
    i = demand_formacia(e)
    z = zona(e, "RBR")
    out = e.on_bar(bar(i + 1, o=103.0, h=103.2, low=z.top - 0.1, c=101.5), None, OKNO)
    kinds = {o.kind for o in out.drawings}
    assert kinds
    for k in kinds:
        assert DrawKind(k.value) is k


# ---------------------------------------------------------------------- #
# odchod (leg-out): záver za bázou o legOutMinAtr do legOutMaxBars barov
# ---------------------------------------------------------------------- #
# Po `rozbeh` je ATR baru pred impulzom ~1,15, horná hrana bázy (knôt) 100,8.
# legOutMinAtr=2.5 -> cieľ ~103,67: impulz so záverom 103,4 sám nestačí.

def _rbr(e: SDZoneEngine) -> list:
    return [z for z in e._zones if z.pattern == "RBR"]


def _baza_a_impulz(e: SDZoneEngine, i0: int = 30) -> int:
    rozbeh(e)
    return demand_formacia(e, i0)


def test_nula_vypne_odchod_zona_vznika_na_impulze():
    e = _engine(legOutMinAtr=0)
    i = _baza_a_impulz(e)
    z = zona(e, "RBR")
    assert z.born_bar == e.history.bar_index and z.fresh and not e._candidates


def test_dostatocny_odchod_uz_na_impulze():
    e = _engine(legOutMinAtr=1.0)        # cieľ ~101,95, impulz zavrel 103,4
    _baza_a_impulz(e)
    assert zona(e, "RBR").born_bar == e.history.bar_index


def test_nedostatocny_odchod_zonu_nevytvori():
    e = _engine(legOutMinAtr=5.0, legOutMaxBars=3)   # cieľ ~106,5
    i = _baza_a_impulz(e)
    assert not _rbr(e) and e._candidates, "kandidát čaká na odchod"
    e.on_bar(bar(i + 1, o=103.4, h=103.8, low=103.2, c=103.5), None, OKNO)
    e.on_bar(bar(i + 2, o=103.5, h=103.9, low=103.3, c=103.6), None, OKNO)
    assert not _rbr(e) and not e._candidates, "po legOutMaxBars kandidát zaniká"
    e.on_bar(bar(i + 3, o=103.6, h=107.5, low=103.5, c=107.2), None, OKNO)
    assert not _rbr(e), "neskorý odchod sa už nepočíta"


def test_odchod_rozlozeny_do_viacerych_barov():
    e = _engine(legOutMinAtr=2.5, legOutMaxBars=3)
    i = _baza_a_impulz(e)
    assert not _rbr(e), "impulz sám cieľ nedosiahol — zóna ešte nesmie existovať"
    e.on_bar(bar(i + 1, o=103.4, h=104.2, low=103.3, c=104.0), None, OKNO)
    z = zona(e, "RBR")
    assert z.born_bar == i + 1 and z.fresh


@pytest.mark.parametrize("max_bars,vznikne", [(2, False), (3, True)])
def test_odchod_po_legOutMaxBars_sa_zamietne(max_bars, vznikne):
    e = _engine(legOutMinAtr=2.5, legOutMaxBars=max_bars)
    i = _baza_a_impulz(e)
    e.on_bar(bar(i + 1, o=103.4, h=103.7, low=103.3, c=103.5), None, OKNO)
    e.on_bar(bar(i + 2, o=103.5, h=104.3, low=103.4, c=104.1), None, OKNO)   # tretí bar odchodu
    assert bool(_rbr(e)) is vznikne


def test_zaver_spat_pod_bazou_kandidata_zrusi():
    e = _engine(legOutMinAtr=2.5, legOutMaxBars=3)
    i = _baza_a_impulz(e)
    e.on_bar(bar(i + 1, o=103.4, h=103.5, low=100.2, c=100.3), None, OKNO)   # pod 100,4
    e.on_bar(bar(i + 2, o=100.3, h=104.3, low=100.2, c=104.1), None, OKNO)
    assert not _rbr(e)


def test_navrat_pocas_odchodu_zona_nie_je_cerstva():
    e = _engine(legOutMinAtr=2.5, legOutMaxBars=3)
    i = _baza_a_impulz(e)
    e.on_bar(bar(i + 1, o=103.4, h=103.5, low=100.7, c=101.0), None, OKNO)   # dotkne sa zóny
    e.on_bar(bar(i + 2, o=101.0, h=104.3, low=100.9, c=104.1), None, OKNO)
    z = zona(e, "RBR")
    assert not z.fresh
    out = e.on_bar(bar(i + 3, o=104.0, h=104.1, low=z.top - 0.1, c=101.5), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY], "prvý návrat už prebehol"


def test_ziadny_pohlad_dopredu_zona_obchodovatelna_az_po_dokonceni():
    """Pred barom, ktorý odchod dokončí, zóna neexistuje a nedá sa z nej vstúpiť;
    výstupy engine-u na prefixe barov nezávisia od barov, ktoré prídu potom."""
    def prehraj(n_po_impulze: int):
        e = _engine(legOutMinAtr=2.5, legOutMaxBars=3)
        i = _baza_a_impulz(e)
        dalsie = [bar(i + 1, o=103.4, h=103.7, low=103.3, c=103.5),
                  bar(i + 2, o=103.5, h=104.3, low=103.4, c=104.1),   # dokončí odchod
                  bar(i + 3, o=104.0, h=104.1, low=100.7, c=101.5)]   # návrat do zóny
        outs = [e.on_bar(b, None, OKNO) for b in dalsie[:n_po_impulze]]
        return e, i, outs

    e1, i, outs1 = prehraj(1)
    assert not _rbr(e1)
    assert not [o for o in outs1[0].orders if o.action is OrderAction.ENTRY]
    e3, _, outs3 = prehraj(3)
    assert [len(o.orders) for o in outs3[:1]] == [len(o.orders) for o in outs1]
    z = zona(e3, "RBR")
    assert z.born_bar == i + 2
    vst = [o for o in outs3[2].orders if o.action is OrderAction.ENTRY]
    assert len(vst) == 1 and vst[0].direction is Direction.LONG


def test_predhistoria_pokryva_odchod():
    kratky = SDZoneEngine(SDZoneConfig(legOutMaxBars=1, maxZoneAgeBars=5), BTCUSDT_BINANCE, 15)
    dlhy = SDZoneEngine(SDZoneConfig(legOutMaxBars=10, maxZoneAgeBars=5), BTCUSDT_BINANCE, 15)
    assert dlhy.required_history - kratky.required_history == 9
    assert dlhy.required_history == max(SDZoneConfig().atrLen, SDZoneConfig().trendMaLen
                                        if SDZoneConfig().useTrendFilter else 0)         + SDZoneConfig().baseMaxBars + 10 + 8


def test_stary_profil_so_zrusenymi_polami_sa_nacita():
    stary = {**SDZoneConfig().to_dict(), "impulseMinMoveAtr": 1.5, "impulseMaxBars": 3}
    del stary["legOutMinAtr"], stary["legOutMaxBars"]
    cfg = SDZoneConfig.from_dict(stary)
    assert cfg.legOutMinAtr == SDZoneConfig().legOutMinAtr
    assert cfg.legOutMaxBars == SDZoneConfig().legOutMaxBars
    assert SDZoneConfig.from_dict({"legOutMinAtr": 0}).legOutMinAtr.value == 0
    from tradebot.strategies.sdzone.config import CONFIG_DIR
    for path in CONFIG_DIR.glob("*.json"):
        SDZoneConfig.from_json(path).validate()
