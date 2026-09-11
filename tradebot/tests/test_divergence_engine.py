"""Divergenčná stratégia: detektor, skladanie HTF, indikátory a engine na syntetických baroch.

Testuje sa mechanika, nie edge: či detektor nájde divergenciu presne podľa definície
(a nie skôr, než je pivot potvrdený), či sa HTF bar skladá a sprístupní až na prvom
bare novej periódy, ako rozhoduje signál, potvrdenie vstupu, výstup podľa trendu
a dvojstupňový trailing.
"""

from __future__ import annotations

import pytest

from tradebot.adapters.freqtrade import EngineRunner
from tradebot.core import BTCUSDT_BINANCE, Bar, DrawKind, MarketContext, OrderAction
from tradebot.core.types import Direction, OrderType, TradeDirection
from tradebot.strategies.divergence import DivergenceConfig, DivergenceEngine, EntryMode
from tradebot.strategies.divergence.divergence import DivHits, DivergenceDetector
from tradebot.strategies.divergence.htf import TFAggregator
from tradebot.strategies.divergence.ta import HeikinAshi, Pivots, Supertrend
from tradebot.strategies.divergence.trailing import TwoStageTrailing

T0 = 1_756_684_800_000  # 2025-09-01 00:00 UTC — násobok hodiny aj štyroch hodín
MIN15 = 900_000
INST = BTCUSDT_BINANCE
OKNO = MarketContext(in_trade_window=True)


def bar(i: int, o=100.0, h=101.0, low=99.0, c=100.5, v=10.0, step=MIN15) -> Bar:
    return Bar(time=T0 + i * step, open=o, high=h, low=low, close=c, volume=v)


# --------------------------------------------------------------------------- #
# detektor divergencií
# --------------------------------------------------------------------------- #

#: close: pivot low 100 na indexe 2 (potvrdený na 4 pri prd=2), potom nižšie low 95 na
#: indexe 8 — cena nižšie low. Vlastný indikátor „ind" robí vyššie low (10 → 20) a nikde
#: nepretne spojnicu 10→20: regulárna býčia divergencia dĺžky 6.
CLOSES = [110, 105, 100, 104, 108, 106, 104, 99, 95]
INDS = [30, 20, 10, 12, 15, 17, 19, 19.5, 20]


def _detector(**kw) -> DivergenceDetector:
    base = dict(prd=2, source_close=True, regular=True, hidden=True, max_pp=10, max_bars=50,
                dont_confirm=True, buy_inds={"ind"}, sell_inds={"ind"})
    base.update(kw)
    vals = iter(INDS)
    return DivergenceDetector(extra={"ind": lambda b: next(vals)}, **base)


def test_detektor_najde_regularnu_bycu_divergenciu_na_vlastnom_indikatore():
    det = _detector()
    hits = [det.on_bar(bar(i, o=c, h=c + 1, low=c - 1, c=c)) for i, c in enumerate(CLOSES)]
    posledny = hits[-1]
    assert posledny.buy_count == 1 and posledny.sell_count == 0
    hit = posledny.buy[0]
    assert hit.indicator == "ind" and not hit.hidden
    assert hit.length == 6 and hit.pivot_index == 2 and hit.pivot_price == 100
    assert hit.pivot_time == T0 + 2 * MIN15
    # skôr než na poslednom bare nič: pivot je príliš blízko (len <= 5) alebo cena nie je nižšie
    assert all(h.buy_count == 0 for h in hits[:-1])


def test_pivot_sa_pouzije_az_po_potvrdeni():
    """Pivot na indexe 2 s prd=2 je známy až na bare 4 — dovtedy ho detektor nemá."""
    det = _detector()
    for i, c in enumerate(CLOSES[:4]):
        det.on_bar(bar(i, o=c, h=c + 1, low=c - 1, c=c))
    assert det.pl == []
    det.on_bar(bar(4, o=108, h=109, low=107, c=108))
    assert det.pl and det.pl[0][0] == 2 and det.pl[0][1] == 100


def test_regular_vypnuty_nic_nenajde_a_hidden_je_ina_definicia():
    det = _detector(regular=False, hidden=True)
    hits = [det.on_bar(bar(i, o=c, h=c + 1, low=c - 1, c=c)) for i, c in enumerate(CLOSES)]
    assert hits[-1].buy_count == 0  # cena nižšie low = regulárna, nie skrytá


def test_prerusena_spojnica_divergenciu_zrusi():
    """Keď close medzi pivotom a teraz klesne pod spojnicu, divergencia nie je („arrived")."""
    closes = list(CLOSES)
    closes[5] = 90  # hlboko pod spojnicou 100 → 95
    vals = iter(INDS)
    det = DivergenceDetector(prd=2, source_close=True, regular=True, hidden=False, max_pp=10,
                             max_bars=50, dont_confirm=True, buy_inds={"ind"}, sell_inds=set(),
                             extra={"ind": lambda b: next(vals)})
    hits = [det.on_bar(bar(i, o=c, h=c + 1, low=c - 1, c=c)) for i, c in enumerate(closes)]
    assert hits[-1].buy_count == 0


def test_dont_confirm_vypnute_caka_na_pohyb_a_porovnava_predchadzajuci_bar():
    """S potvrdením sa hľadá až keď indikátor alebo close stúpne a berie sa bar [1]."""
    closes = CLOSES + [96]           # close stúpol o bar neskôr
    inds = INDS[:-1] + [19.4, 20.5]  # na bare 8 klesol aj indikátor, inak by sa hľadalo už tam
    vals = iter(inds)
    det = DivergenceDetector(prd=2, source_close=True, regular=True, hidden=False, max_pp=10,
                             max_bars=50, dont_confirm=False, buy_inds={"ind"}, sell_inds=set(),
                             extra={"ind": lambda b: next(vals)})
    hits = [det.on_bar(bar(i, o=c, h=c + 1, low=c - 1, c=c)) for i, c in enumerate(closes)]
    assert hits[-2].buy_count == 0          # na bare 8 close klesol -> nehľadá sa
    assert hits[-1].buy_count == 1          # na bare 9 close stúpol, porovnáva sa bar 8
    assert hits[-1].buy[0].length == 7      # dĺžka od pivotu (idx 2) po aktuálny bar (idx 9)


# --------------------------------------------------------------------------- #
# skladanie vyššieho TF a indikátory
# --------------------------------------------------------------------------- #

def test_htf_aggregator_sklada_hodinu_zo_stvrthodin_a_sprístupni_ju_na_prvom_bare_novej_periody():
    agg = TFAggregator(60)
    closed = []
    for i in range(9):
        b = bar(i, o=100 + i, h=110 + i, low=90 - i, c=101 + i, v=1.0)
        out = agg.push(b)
        closed.append(out)
    # bary 0..3 = 00:00-01:00; uzavretý bar príde s barom 4 (otvorenie 01:00)
    assert closed[:4] == [None] * 4 and closed[4] is not None
    h = closed[4]
    assert h.time == T0 and h.open == 100 and h.high == 113 and h.low == 87 and h.close == 104 and h.volume == 4.0
    assert closed[5:8] == [None] * 3 and closed[8] is not None and closed[8].time == T0 + 3_600_000


def test_htf_aggregator_preskoci_prazdnu_periodu_bez_vypchavky():
    agg = TFAggregator(60)
    agg.push(bar(0))
    out = agg.push(bar(8))  # skok cez celú hodinu 01:00–02:00
    assert out is not None and out.time == T0
    assert agg.closed_count == 1


def test_engine_odmietne_tf_grafu_ktory_nedeli_htf():
    with pytest.raises(ValueError, match="násobkom"):
        DivergenceEngine(DivergenceConfig(), INST, 7)


def test_supertrend_v_raste_je_hore_a_ciara_pod_cenou():
    st = Supertrend(5, 3.0)
    ha = HeikinAshi()
    for i in range(40):
        c = 100 + i
        trend = st.push(ha.push(bar(i, o=c - 0.5, h=c + 0.7, low=c - 0.7, c=c + 0.5)))
    assert trend == 1 and st.line is not None and st.line < 140
    for i in range(40, 80):
        c = 140 - (i - 40) * 3
        trend = st.push(ha.push(bar(i, o=c + 0.5, h=c + 0.7, low=c - 0.7, c=c - 0.5)))
    assert trend == -1 and st.line > c


def test_pivots_su_prisne_a_hlasia_sa_s_indexom_povodneho_baru():
    p = Pivots(2)
    seq = [1, 2, 5, 2, 1, 1, 1]
    out = [p.push(v, v, i) for i, v in enumerate(seq)]
    assert out[4][0] == (2, 5, 2)          # pivot high na indexe 2, potvrdený na 4
    assert out[6][0] is None and out[6][1] is None  # plató 1,1,1 nie je pivot


def test_dvojstupnovy_trailing_zamok_potom_sledovanie():
    t = TwoStageTrailing(activation_price_distance=4.0, offset_price_distance=1.0,
                         activation_ticks=40, offset_ticks=10,
                         lock_activation_distance=1.5, lock_level_distance=0.35)
    entry, base = 100.0, 97.0
    assert t.stop_price(Direction.LONG, entry, base, 101.0) == base            # pod aktiváciou
    assert t.stop_price(Direction.LONG, entry, base, 101.6) == pytest.approx(100.35)  # zámok
    assert t.stop_price(Direction.LONG, entry, base, 103.9) == pytest.approx(100.35)  # stále zámok
    assert t.stop_price(Direction.LONG, entry, base, 105.0) == pytest.approx(104.0)   # sledovanie
    assert t.stop_price(Direction.SHORT, entry, 103.0, 98.4) == pytest.approx(99.65)
    assert t.stop_price(Direction.SHORT, entry, 103.0, 95.0) == pytest.approx(96.0)


def test_trailing_z_configu_je_v_percentach_ceny_vstupu():
    cfg = DivergenceConfig()
    t = TwoStageTrailing.from_config(cfg, INST, 50_000.0)
    assert t.activation_price_distance == pytest.approx(2_000.0)
    assert t.offset_price_distance == pytest.approx(500.0)
    assert t.lock_activation_distance == pytest.approx(750.0)
    assert t.lock_level_distance == pytest.approx(175.0)
    assert TwoStageTrailing.from_config(DivergenceConfig(enableTrailing=False), INST, 50_000.0) is None


# --------------------------------------------------------------------------- #
# engine — rozhodovanie s podstrčeným stavom indikátorov
# --------------------------------------------------------------------------- #

class _Stav:
    """Čo engine vidí z indikátorov na jednom bare — testy to nastavia priamo."""

    def __init__(self, *, buy=0, sell=0, rsi=50.0, t1=1, t2=1, line2=90.0, tchart=-1,
                 bull1=0, bear1=0, bull2=0, bear2=0):
        self.buy, self.sell, self.rsi, self.t1, self.t2, self.line2, self.tchart = buy, sell, rsi, t1, t2, line2, tchart
        self.bull1, self.bear1, self.bull2, self.bear2 = bull1, bear1, bull2, bear2


def _engine(stavy: list[_Stav], **kw) -> DivergenceEngine:
    """Engine, ktorého `_update` neráta indikátory, ale berie stav zo zoznamu (posledný sa opakuje)."""
    cfg = DivergenceConfig(**kw)
    engine = DivergenceEngine(cfg, INST, 15)
    it = list(stavy)

    def fake_update(b: Bar, out) -> DivHits:
        engine.history.append(b)
        s = it.pop(0) if len(it) > 1 else it[0]
        hits = DivHits(buy=[None] * s.buy, sell=[None] * s.sell)  # type: ignore[list-item]
        engine.recent.append(hits)
        engine.rsi_value = s.rsi
        engine.htf1.st.trend, engine.htf2.st.trend = s.t1, s.t2
        engine.htf2.st.line = s.line2
        engine.st_chart.trend = s.tchart
        engine.htf1.bull, engine.htf1.bear = s.bull1, s.bear1
        engine.htf2.bull, engine.htf2.bear = s.bull2, s.bear2
        return hits

    engine._update = fake_update  # type: ignore[method-assign]
    return engine


def _warm(engine: DivergenceEngine, n: int = 20) -> None:
    for i in range(n):
        engine.on_bar(bar(i), None, OKNO)


def test_defaults_validate_and_required_history():
    cfg = DivergenceConfig()
    assert cfg.long_indicators >= {"macd", "rsi", "stoch"} and cfg.short_indicators == {"macd", "rsi"}
    engine = DivergenceEngine(cfg, INST, 15)
    assert engine.required_history >= (cfg.zoneMaxBars + cfg.zonePrd2) * (cfg.htf2Minutes // 15)


def test_config_odmietne_prazdnu_sadu_indikatorov_a_zly_zamok():
    with pytest.raises(ValueError, match="long divergencie"):
        DivergenceConfig(**{f: False for f in ("divMacdLong", "divRsiLong", "divStochLong", "divObvLong",
                                                 "divMomLong", "divVwmacdLong", "divCmfLong", "divMfiLong",
                                                 "divCdvLong")})
    with pytest.raises(ValueError, match="beLockPct"):
        DivergenceConfig(beLockPct=2.0, beActivationPct=1.5)
    with pytest.raises(ValueError, match="htf2Minutes"):
        DivergenceConfig(htfMinutes=240, htf2Minutes=60)


def test_immediate_long_signal_da_market_order_so_stopom_pod_vstupom_a_bez_tp_boxu():
    engine = _engine([_Stav(buy=0), _Stav(buy=1)], entryMode="immediate", rrRatio=0.0)
    _warm(engine)
    out = engine.on_bar(bar(20, c=100.5), None, OKNO)
    entries = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1
    intent = entries[0]
    assert intent.direction is Direction.LONG and intent.order_type is OrderType.MARKET
    plan = intent.plan
    assert plan.entry == 100.5 and plan.stop_loss < plan.entry
    assert plan.sl_distance == pytest.approx(plan.entry - plan.stop_loss)
    assert plan.take_profit > plan.entry + 10 * plan.sl_distance   # poistka, nie cieľ
    assert plan.qty > 0 and plan.trailing is not None
    kinds = {o.kind for o in out.drawings}
    assert DrawKind.SL_BOX in kinds and DrawKind.DV_ENTRY in kinds and DrawKind.TP_BOX not in kinds
    box = [o for o in out.drawings if o.kind is DrawKind.SL_BOX][0]
    assert box.x1_ms == bar(20).time and box.y2 == plan.stop_loss


def test_rr_kladne_kresli_tp_box_na_urovni_planu():
    engine = _engine([_Stav(buy=0), _Stav(buy=1)], entryMode="immediate", rrRatio=2.0)
    _warm(engine)
    out = engine.on_bar(bar(20, c=100.5), None, OKNO)
    plan = [o for o in out.orders if o.action is OrderAction.ENTRY][0].plan
    assert plan.take_profit - plan.entry == pytest.approx(2.0 * plan.sl_distance, abs=INST.tick_size)
    tp = [o for o in out.drawings if o.kind is DrawKind.TP_BOX]
    assert tp and tp[0].y1 == plan.take_profit


@pytest.mark.parametrize("stav", [
    _Stav(buy=1, rsi=65.0),                 # RSI nad stropom
    _Stav(buy=1, t1=-1),                    # 1h supertrend dole
    _Stav(buy=1, t2=-1),                    # 4h supertrend dole
    _Stav(buy=1, tchart=1),                 # bez pullbacku na grafe
    _Stav(buy=1, bear2=1),                  # medvedia zóna 4h
    _Stav(buy=1, bear1=1),                  # medvedia zóna 1h
    _Stav(buy=1, sell=1),                   # medvedia divergencia v okne
], ids=["rsi", "st1", "st2", "pullback", "zone4h", "zone1h", "oppdiv"])
def test_kazdy_filter_povodneho_populate_entry_trend_blokuje_long(stav):
    engine = _engine([_Stav(buy=0), stav], entryMode="immediate")
    _warm(engine)
    out = engine.on_bar(bar(20), None, OKNO)
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_vypnute_filtre_long_pustia():
    engine = _engine([_Stav(buy=0), _Stav(buy=1, tchart=1, bear2=3)], entryMode="immediate",
                     pullbackFilter=False, zoneFilter=False)
    _warm(engine)
    out = engine.on_bar(bar(20), None, OKNO)
    assert [o.direction for o in out.orders if o.action is OrderAction.ENTRY] == [Direction.LONG]


def test_short_zrkadlovo_a_long_only_ho_odmietne():
    stav = _Stav(sell=2, rsi=45.0, t1=-1, t2=-1, line2=110.0, tchart=1)
    engine = _engine([_Stav(), stav], entryMode="immediate")
    _warm(engine)
    out = engine.on_bar(bar(20), None, OKNO)
    assert [o.direction for o in out.orders if o.action is OrderAction.ENTRY] == [Direction.SHORT]
    engine2 = _engine([_Stav(), stav], entryMode="immediate", tradeDirection="Long only")
    _warm(engine2)
    assert not [o for o in engine2.on_bar(bar(20), None, OKNO).orders if o.action is OrderAction.ENTRY]
    # short potrebuje minDivsShort (2) — jedna medvedia nestačí
    engine3 = _engine([_Stav(), _Stav(sell=1, rsi=45.0, t1=-1, t2=-1, tchart=1)], entryMode="immediate")
    _warm(engine3)
    assert not [o for o in engine3.on_bar(bar(20), None, OKNO).orders if o.action is OrderAction.ENTRY]


def test_signal_plati_signalbars_barov_dozadu():
    """Divergencia na bare N dá signál ešte na N+2 (signalBars=3), nie na N+3."""
    engine = _engine([_Stav(buy=0)] * 20 + [_Stav(buy=1)] + [_Stav(buy=0)] * 10, entryMode="immediate")
    # 20 barov bez, bar 20 s divergenciou — vstup hneď na 20; potom vyplnené -> ďalší nie
    outs = [engine.on_bar(bar(i), None, OKNO) for i in range(21)]
    assert any(o.action is OrderAction.ENTRY for o in outs[20].orders)
    # nový engine: divergencia na bare 20, ale pozícia „obsadená" do baru 22 -> vstup na 22? nie,
    # can_enter je false len kým je pending; skúsime, že na bare 23 už signál nie je
    engine2 = _engine([_Stav(buy=0)] * 20 + [_Stav(buy=1)] + [_Stav(buy=0)] * 10, entryMode="immediate")
    for i in range(20):
        engine2.on_bar(bar(i), None, OKNO)
    otvorene = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"x"}))
    engine2.on_bar(bar(20), None, otvorene)   # divergencia, ale pozícia je -> bez vstupu
    engine2.on_bar(bar(21), None, otvorene)
    out22 = engine2.on_bar(bar(22), None, OKNO)   # pozícia skončila, divergencia z baru 20 ešte platí
    assert any(o.action is OrderAction.ENTRY for o in out22.orders)
    engine3 = _engine([_Stav(buy=0)] * 20 + [_Stav(buy=1)] + [_Stav(buy=0)] * 10, entryMode="immediate")
    for i in range(20):
        engine3.on_bar(bar(i), None, OKNO)
    for i in range(20, 23):
        engine3.on_bar(bar(i), None, otvorene)
    out23 = engine3.on_bar(bar(23), None, OKNO)   # bar 20 už vypadol z okna 3 barov
    assert not any(o.action is OrderAction.ENTRY for o in out23.orders)


def test_confirm_vstupi_az_na_bare_ktory_zavrie_nad_referenciou():
    engine = _engine([_Stav(buy=0)] * 20 + [_Stav(buy=1)] + [_Stav(buy=0)] * 10, entryMode="confirm")
    for i in range(20):
        engine.on_bar(bar(i), None, OKNO)
    out20 = engine.on_bar(bar(20, c=100.0), None, OKNO)          # signál -> vyzbrojenie, bez orderu
    assert not out20.orders and any(o.kind is DrawKind.DV_ARMED for o in out20.drawings)
    out21 = engine.on_bar(bar(21, c=99.5), None, OKNO)            # nižší close: referencia klesne, čaká
    assert not out21.orders
    out22 = engine.on_bar(bar(22, c=99.8), None, OKNO)            # nad 99,5 -> vstup
    entries = [o for o in out22.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1 and entries[0].plan.entry == 99.8
    assert entries[0].reason.startswith("divergencia, potvrdené")


def test_confirm_konci_ked_signal_zmizne():
    """Divergencia z baru 20 žije 3 bary (20–22); na bare 23 signál nie je, takže ani
    vyšší close nevstupuje — čakanie skončilo so signálom, ako v origináli."""
    engine = _engine([_Stav(buy=0)] * 20 + [_Stav(buy=1)] + [_Stav(buy=0)] * 10, entryMode="confirm")
    for i in range(20):
        engine.on_bar(bar(i), None, OKNO)
    engine.on_bar(bar(20, c=100.0), None, OKNO)
    engine.on_bar(bar(21, c=99.5), None, OKNO)
    engine.on_bar(bar(22, c=99.0), None, OKNO)                    # posledný bar so signálom
    assert engine._armed is not None
    out = engine.on_bar(bar(23, c=99.9), None, OKNO)              # už vyšší close, ale bez signálu
    assert not out.orders and engine._armed is None


def test_confirm_skonci_aj_ked_filter_prestane_platit():
    """Signál nie je len divergencia: keď medzitým padne 4h supertrend, čakanie sa zruší."""
    engine = _engine([_Stav(buy=0)] * 20 + [_Stav(buy=1)] + [_Stav(buy=1, t2=-1)] * 10, entryMode="confirm")
    for i in range(20):
        engine.on_bar(bar(i), None, OKNO)
    engine.on_bar(bar(20, c=100.0), None, OKNO)
    out = engine.on_bar(bar(21, c=101.0), None, OKNO)
    assert not out.orders and engine._armed is None


def test_neprijaty_vstup_sa_zrusi_na_dalsom_bare():
    engine = _engine([_Stav(buy=0), _Stav(buy=1)], entryMode="immediate")
    _warm(engine)
    out = engine.on_bar(bar(20), None, OKNO)
    order_id = [o for o in out.orders if o.action is OrderAction.ENTRY][0].order_id
    out2 = engine.on_bar(bar(21), None, OKNO)
    cancels = [o for o in out2.orders if o.action is OrderAction.CANCEL]
    assert cancels and cancels[0].order_id == order_id


def test_vystup_podla_trendu_len_pre_stratovy_obchod():
    def run(close_after: float, t2: int, line2: float, trend_exit=True) -> bool:
        engine = _engine([_Stav(buy=0)] * 20 + [_Stav(buy=1)] + [_Stav(buy=0, t2=t2, line2=line2)],
                         entryMode="immediate", trendExit=trend_exit)
        _warm(engine)
        out = engine.on_bar(bar(20, c=100.0), None, OKNO)
        oid = [o for o in out.orders if o.action is OrderAction.ENTRY][0].order_id
        otvorene = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({oid}))
        out2 = engine.on_bar(bar(21, c=close_after), None, otvorene)
        return out2.close_session and any(o.action is OrderAction.CLOSE for o in out2.orders)

    assert run(99.0, -1, 90.0) is True            # v strate, 4h supertrend otočil dole
    assert run(99.0, 1, 99.5) is True             # v strate, close pod čiarou 4h
    assert run(99.0, 1, 90.0) is False            # v strate, ale trend drží
    assert run(102.0, -1, 90.0) is False          # v zisku — nechá sa trailingu
    assert run(99.0, -1, 90.0, trend_exit=False) is False


def test_casovy_limit_zavrie_obchod():
    engine = _engine([_Stav(buy=0)] * 20 + [_Stav(buy=1)] + [_Stav(buy=0)], entryMode="immediate", maxHoldBars=3)
    _warm(engine)
    out = engine.on_bar(bar(20), None, OKNO)
    oid = [o for o in out.orders if o.action is OrderAction.ENTRY][0].order_id
    otvorene = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({oid}))
    flags = [engine.on_bar(bar(21 + k, c=101.0), None, otvorene).close_session for k in range(3)]
    assert flags == [False, False, True]


def test_generic_runner_runs_divergence_without_htf_feeder():
    runner = EngineRunner(DivergenceConfig(), INST, 15)
    assert runner.spec.key == "divergence" and runner.htf is None
    for i in range(60):
        c = 100 + (i % 7) * 0.3
        runner.process(bar(i, o=c - 0.1, h=c + 0.5, low=c - 0.5, c=c), runner.window_for(T0 + i * MIN15))
    assert runner.engine.htf1.bars >= 14 and runner.engine.htf2.bars >= 3
    assert runner.engine.st_chart.trend in (1, -1)


def test_realne_indikatory_daju_na_ciste_vlne_bycie_aj_medvedie_divergencie():
    """Bez podstrčeného stavu: sínusoida s klesajúcou amplitúdou dáva RSI divergencie."""
    import math

    cfg = DivergenceConfig(prd=3, maxBars=120, dontConfirm=True, zoneFilter=False)
    engine = DivergenceEngine(cfg, INST, 15)
    buy = sell = 0
    for i in range(400):
        # cena klesá po vlnách, vlny sa skracujú -> nižšie low pri slabšom RSI
        c = 100 - i * 0.05 + 3.0 * math.sin(i / 6.0) * (1 + i / 400)
        b = bar(i, o=c - 0.2, h=c + 0.6, low=c - 0.6, c=c, v=10 + (i % 5))
        engine.on_bar(b, None, OKNO)
        buy += engine.recent[-1].buy_count
        sell += engine.recent[-1].sell_count
    assert buy > 0 and sell > 0
