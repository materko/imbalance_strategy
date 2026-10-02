"""VWAP ORB: engine na syntetických baroch.

Testuje sa podmienka, ktorú stratégia pridáva k ORB: prerazenie rangu je signál až vtedy,
keď je za hranicou aj VWAP (a pri ``closeBeyondVwap`` aj cena za VWAP). Zvyšok (range,
stop na opačnej strane, cieľ RR, koniec seansy) je ORB a testuje ho `test_orb_engine.py`.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import BTCUSDT_BINANCE, Bar, MarketContext, OrderAction
from tradebot.core.types import Direction, SizeSpec
from tradebot.strategies.orb import ORBConfig, ORBEngine, SessionMode
from tradebot.strategies.vwapdrift import VwapPeriod
from tradebot.strategies.vwaporb import VwapOrbConfig, VwapOrbEngine

NY = ZoneInfo("America/New_York")
OPEN_MS = int(datetime(2025, 9, 2, 9, 30, tzinfo=NY).timestamp() * 1000)
STEP = 5 * 60_000
OKNO = MarketContext(in_trade_window=True)


def bar(i: int, c: float, v: float = 10.0, rng: float = 1.0) -> Bar:
    return Bar(time=OPEN_MS + i * STEP, open=c, high=c + rng / 2, low=c - rng / 2, close=c, volume=v)


def engine(**kw) -> VwapOrbEngine:
    return VwapOrbEngine(VwapOrbConfig(vwapPeriod=VwapPeriod.CHART, **kw), BTCUSDT_BINANCE, 5)


def warm(e) -> None:
    for i in range(-40, 0):  # pred 9:30 — ATR, do VWAP sa nepočíta
        e.on_bar(bar(i, 100.0), ctx=OKNO)


def opening_range(e) -> None:
    """9:30–9:45: range high 101, low 99, VWAP ~100."""
    for i, c in enumerate((100.0, 100.0, 100.0)):
        e.on_bar(Bar(OPEN_MS + i * STEP, c, 101.0, 99.0, c, 10.0), ctx=OKNO)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_defaulty_ny_range_bez_skrytych_filtrov():
    cfg = VwapOrbConfig()
    assert cfg.sessionMode.value == "ny" and cfg.nyStartH == 9 and cfg.nyStartM == 30
    assert cfg.slMode.value == "opposite" and cfg.entryWindowMinutes == 0
    assert cfg.minRangePct == 0.0 and cfg.minClosePosPct == 0


def test_cena_nad_rangom_ale_vwap_este_nie_a_potom_vstup_ked_je_tam_aj_vwap():
    e = engine()
    warm(e)
    opening_range(e)
    # 9:45: close 103 nad high 101, ale s malým objemom VWAP ostane v range (~100,75)
    out = e.on_bar(bar(3, 103.0, v=10.0), ctx=OKNO)
    assert not entries(out) and e._vwap_value < 101.0
    # 9:50: veľký objem nad rangom vytiahne VWAP nad high -> vstup na zavretí
    out = e.on_bar(bar(4, 103.0, v=100.0), ctx=OKNO)
    (intent,) = entries(out)
    assert e._vwap_value > 101.0
    assert intent.plan.direction is Direction.LONG
    assert intent.plan.entry == BTCUSDT_BINANCE.round_price(103.0)
    assert intent.plan.stop_loss < 99.0                     # opačná strana rangu + rezerva
    risk = intent.plan.entry - intent.plan.stop_loss
    assert abs(intent.plan.take_profit - (intent.plan.entry + 1.5 * risk)) <= 0.2


def test_orb_bez_vwap_by_vstupil_uz_na_prvej_sviecke():
    """Kontrola, že podmienku robí VWAP: holý ORB s tými istými defaultmi vstúpi o bar skôr."""
    e = ORBEngine(ORBConfig(sessionMode=SessionMode.NY, breakBufferAtr=SizeSpec(0.0, "atr"),
                            minRangePct=0.0, maxRangePct=10.0, minClosePosPct=0,
                            entryWindowMinutes=0),
                  BTCUSDT_BINANCE, 5)
    warm(e)
    opening_range(e)
    assert entries(e.on_bar(bar(3, 103.0, v=10.0), ctx=OKNO))


def test_short_ked_vwap_aj_cena_pod_rangom():
    e = engine()
    warm(e)
    opening_range(e)
    out = e.on_bar(bar(3, 97.0, v=100.0), ctx=OKNO)
    (intent,) = entries(out)
    assert intent.plan.direction is Direction.SHORT and intent.plan.stop_loss > 101.0


def test_vwap_za_rangom_ale_cena_uz_nie():
    e = engine()
    warm(e)
    opening_range(e)
    e2 = e.on_bar(bar(3, 100.5, v=10.0), ctx=OKNO)            # cena späť v range
    assert not entries(e2)
    # VWAP nad rangom, ale close v range -> ORB prerazenie nenastane, obchod nie je
    e._vwap_value = 102.0
    assert e._break_allowed(e._state["ny"], Direction.LONG, bar(4, 100.5), 1.0)
    e.vwap.push = lambda b: 102.0  # VWAP drží nad rangom
    assert not entries(e.on_bar(bar(4, 100.5), ctx=OKNO))


def test_close_beyond_vwap():
    e = engine(closeBeyondVwap=True)
    warm(e)
    opening_range(e)
    st = e._state["ny"]
    e._vwap_value = 102.0
    assert not e._break_allowed(st, Direction.LONG, bar(4, 101.5), 1.0)   # nad rangom, pod VWAP
    assert e._break_allowed(st, Direction.LONG, bar(4, 102.5), 1.0)


def test_vwap_sa_kresli():
    e = engine()
    warm(e)
    outs = []
    for i, c in enumerate((100.0, 100.0, 100.0, 102.0)):
        outs.append(e.on_bar(bar(i, c), ctx=OKNO))
    lines = [d for o in outs for d in o.drawings if d.kind.value == "vo_vwap"]
    assert len(lines) == 3


def test_direction_staci_prerazenie_cenou_a_vwap_v_smere():
    """vwapRule=direction: VWAP ostáva v range, ale stúpa — prerazenie cenou je signál hneď."""
    from tradebot.strategies.vwaporb import VwapRule

    e = engine(vwapRule=VwapRule.DIRECTION, vwapDriftBars=1)
    warm(e)
    opening_range(e)
    out = e.on_bar(bar(3, 103.0, v=10.0), ctx=OKNO)
    (intent,) = entries(out)
    assert e._vwap_value < 101.0 and intent.plan.direction is Direction.LONG


def test_direction_vwap_proti_smeru_nie():
    """VWAP klesá (veľký objem nízko v range) a cena prerazí nahor — long nie je."""
    from tradebot.strategies.vwaporb import VwapRule

    e = engine(vwapRule=VwapRule.DIRECTION, vwapDriftBars=2)
    warm(e)
    opening_range(e)
    e.on_bar(Bar(OPEN_MS + 3 * STEP, 99.2, 99.5, 99.0, 99.2, 200.0), ctx=OKNO)
    out = e.on_bar(Bar(OPEN_MS + 4 * STEP, 101.5, 101.8, 101.3, 101.5, 1.0), ctx=OKNO)
    assert e.vwap.change(2) < 0 and not entries(out)


# ---- výstup cez VWAP (1.2) --------------------------------------------------- #

from tradebot.strategies.vwaporb import ExitMode  # noqa: E402

POS = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"orb:ny:1"}))


def _long_entry(**kw):
    e = engine(**kw)
    warm(e)
    opening_range(e)
    e.on_bar(bar(3, 103.0, v=10.0), ctx=OKNO)
    out = e.on_bar(bar(4, 103.0, v=100.0), ctx=OKNO)         # vstup long, close nad VWAP
    (intent,) = entries(out)
    return e, intent


def test_exit_vwap_bez_ciela_a_zavretie_pod_vwap():
    e, intent = _long_entry(exitMode=ExitMode.VWAP)
    assert intent.plan.take_profit - intent.plan.entry > 50 * (intent.plan.entry - intent.plan.stop_loss)
    out = e.on_bar(bar(5, 104.0), ctx=POS)                    # nad VWAP — drží
    assert not out.close_session
    vwap = e._vwap_value
    out = e.on_bar(bar(6, vwap - 0.5, v=1.0), ctx=POS)       # zavrie pod VWAP — koniec
    assert out.close_session and [o.action for o in out.orders] == [OrderAction.CLOSE]


def test_exit_tp_vwapom_nezatvara():
    e, intent = _long_entry()
    assert abs(intent.plan.take_profit - intent.plan.entry
               - 1.5 * (intent.plan.entry - intent.plan.stop_loss)) <= 0.2
    vwap = e._vwap_value
    assert not e.on_bar(bar(5, vwap - 0.5, v=1.0), ctx=POS).close_session


def test_exit_len_po_prerazeni_nie_ked_bol_vstup_uz_za_vwap():
    """Pozícia, ktorá nikdy nebola na správnej strane VWAP, sa cez VWAP nezatvára (nebolo prerazenie)."""
    e = engine(exitMode=ExitMode.TP_VWAP)
    e._exit_ready = False
    e._vwap_value = None
    warm(e)
    opening_range(e)
    e.vwap.push = lambda b: 110.0                              # VWAP stále nad cenou
    out = e.on_bar(bar(3, 103.0), ctx=POS)
    assert not out.close_session


# ---- vstup na prerazovacej sviečke (1.3) ------------------------------------- #

from tradebot.strategies.vwaporb import EntryTiming, VwapRule  # noqa: E402


def _engine15(**kw) -> VwapOrbEngine:
    return VwapOrbEngine(VwapOrbConfig(vwapPeriod=VwapPeriod.M15, **kw), BTCUSDT_BINANCE, 5)


def _falling_open(e) -> None:
    """9:30–9:45 range 99–101, VWAP z 15m o 9:45; 9:45–9:55 cena klesá, stále v range."""
    for i, c in enumerate((100.5, 100.0, 99.8)):
        e.on_bar(Bar(OPEN_MS + i * STEP, c, 101.0, 99.0, c, 10.0), ctx=OKNO)
    e.on_bar(Bar(OPEN_MS + 3 * STEP, 99.5, 99.8, 99.2, 99.4, 30.0), ctx=OKNO)


def test_break_candle_vstupi_hned_aj_ked_15m_vwap_nema_2_periody():
    """Graf testera: prerazenie o 9:50, 15m VWAP má len jednu hodnotu — any čaká, break_candle nie."""
    for timing, expected in ((EntryTiming.ANY, []), (EntryTiming.BREAK_CANDLE, [Direction.SHORT])):
        e = _engine15(vwapRule=VwapRule.DIRECTION, entryTiming=timing)
        warm(e)
        _falling_open(e)
        out = e.on_bar(Bar(OPEN_MS + 4 * STEP, 99.0, 99.2, 97.5, 97.6, 60.0), ctx=OKNO)
        assert [o.plan.direction for o in entries(out)] == expected, timing


def test_break_candle_ked_vwap_nesedi_dalsia_sviecka_uz_nie():
    e = engine(vwapRule=VwapRule.BREAK, entryTiming=EntryTiming.BREAK_CANDLE)
    warm(e)
    opening_range(e)
    assert not entries(e.on_bar(bar(3, 103.0, v=10.0), ctx=OKNO))    # VWAP ešte v range
    assert not entries(e.on_bar(bar(4, 103.0, v=100.0), ctx=OKNO))   # any by tu vstúpil


# ---- SL na dotyk VWAP (1.4) --------------------------------------------------- #

from tradebot.strategies.vwaporb.trailing import VwapSeries, VwapTrailing  # noqa: E402


def test_stop_na_vwap_pri_vstupe_a_posuva_sa_s_vwap_v_case():
    e, intent = _long_entry(vwapStop=True)
    plan = intent.plan
    vwap = e._vwap_value
    assert abs(plan.stop_loss - vwap) <= 0.1                    # počiatočný stop = VWAP
    assert isinstance(plan.trailing, VwapTrailing)
    t_next = OPEN_MS + 5 * STEP                                 # sviečka po signáli
    assert plan.trailing.stop_price_at(t_next, Direction.LONG, plan.entry, plan.stop_loss,
                                       plan.entry) == vwap
    e.on_bar(bar(5, 106.0, v=200.0), ctx=POS)                   # VWAP ide hore
    newer = e._vwap_value
    assert newer > vwap
    # sviečka začínajúca po zavretí baru 5 vidí nový VWAP, sviečka pred ním ešte starý
    assert plan.trailing.stop_price_at(OPEN_MS + 6 * STEP, Direction.LONG, plan.entry,
                                       plan.stop_loss, 106.5) == newer   # high baru 5
    assert plan.trailing.stop_price_at(t_next, Direction.LONG, plan.entry, plan.stop_loss,
                                       plan.entry) == vwap


def test_vwap_na_zlej_strane_vstupu_plati_stop_orb():
    e = engine(vwapStop=True, vwapRule=VwapRule.DIRECTION, vwapDriftBars=1)
    warm(e)
    opening_range(e)
    out = e.on_bar(bar(3, 103.0, v=10.0), ctx=OKNO)            # VWAP ~100,75 pod vstupom — OK
    (intent,) = entries(out)
    assert abs(intent.plan.stop_loss - e._vwap_value) <= 0.1
    s = VwapSeries()
    s.add(1000, 104.0)                                          # VWAP nad vstupom 103 pri longu
    trail = VwapTrailing.following(s, 0.0)
    # cena ešte nebola nad VWAP -> stop ORB; keď bola (high 105), stop na VWAP
    assert trail.stop_price_at(2000, Direction.LONG, 103.0, 98.9, 103.0) == 98.9
    assert trail.stop_price_at(2000, Direction.LONG, 103.0, 98.9, 105.0) == 104.0


def test_vwap_series_at():
    s = VwapSeries()
    assert s.at(5) is None
    s.add(10, 1.0)
    s.add(20, 2.0)
    assert s.at(9) is None and s.at(10) == 1.0 and s.at(19) == 1.0 and s.at(25) == 2.0 and s.at(None) == 2.0


# ---- TP na cross VWAP (1.5) ---------------------------------------------------- #


def test_tp_na_cross_vwap_len_v_zisku():
    s = VwapSeries()
    trail = VwapTrailing.following(s, 0.0, profit_only=True)
    s.add(1000, 102.0, 105.0)              # VWAP pod vstupom 103 (long) — dotyk by bola strata
    assert trail.stop_price_at(2000, Direction.LONG, 103.0, 98.9, 106.0) == 98.9
    s.add(3000, 104.0, 105.0)              # VWAP nad vstupom, close nad VWAP — dotyk je výber zisku
    assert trail.stop_price_at(4000, Direction.LONG, 103.0, 98.9, 106.0) == 104.0
    assert trail.stop_price_at(4000, Direction.LONG, 103.0, 98.9, 103.5) == 98.9  # cena ešte nebola nad VWAP
    # MNQ 19. 3. 2026: VWAP skočil do zisku, keď už bola cena pod ním — cross už bol, TP nie
    s.add(5000, 104.5, 103.8)
    assert trail.stop_price_at(6000, Direction.LONG, 103.0, 98.9, 106.0) == 98.9
    # short zrkadlovo
    s2 = VwapSeries()
    s2.add(1000, 95.0, 93.5)
    t2 = VwapTrailing.following(s2, 0.0, profit_only=True)
    assert t2.stop_price_at(2000, Direction.SHORT, 97.0, 101.0, 94.0) == 95.0
    assert t2.stop_price_at(2000, Direction.SHORT, 94.0, 101.0, 93.0) == 101.0   # VWAP nad vstupom 94


def test_tp_na_cross_stop_a_velkost_ostava_z_rangu():
    e, intent = _long_entry(vwapTp=True)
    assert intent.plan.stop_loss < 99.0                    # stop ORB, nie VWAP
    assert isinstance(intent.plan.trailing, VwapTrailing) and intent.plan.trailing.profit_only


def test_londyn_pri_kotve_930_ny_neobchoduje_podla_vcerajsieho_vwap():
    """Deň 1: NY seansa stúpa, VWAP končí vysoko a rastie. Deň 2 ráno (Londýn 8:00) cena prerazí
    londýnsky range hore — dnešný VWAP ešte neexistuje, včerajší zamrznutý sa nesmie použiť."""
    e = engine(sessionMode="both", vwapRule="direction", vwapDriftBars=1)
    warm(e)
    for i in range(78):                                   # 9:30–16:00 NY, cena stúpa
        e.on_bar(bar(i, 100.0 + i * 0.1), ctx=OKNO)
    assert e.vwap.value is not None and e.vwap.change(1) > 0
    lon = int(datetime(2025, 9, 3, 8, 0, tzinfo=ZoneInfo("Europe/London")).timestamp() * 1000)
    outs = []
    for k in range(-6, 3):                                # pred 8:00 a londýnsky range 8:00–8:15
        outs.append(e.on_bar(Bar(lon + k * STEP, 108.0, 108.5, 107.5, 108.0, 10.0), ctx=OKNO))
    for k in range(3, 9):                                 # prerazenie rangu hore
        outs.append(e.on_bar(Bar(lon + k * STEP, 109.0 + k, 109.6 + k, 108.9 + k, 109.5 + k, 10.0), ctx=OKNO))
    assert not e.vwap.live and e._vwap_value is None
    assert not any(entries(o) for o in outs), "bez dnešného VWAP sa v Londýne nevstupuje"
