"""JSS 1.0: engine na syntetických baroch.

Testuje sa mechanika: swing sa použije až po potvrdení, BOS rozhoduje zavretie, zóna je
posledná opačná sviečka pred impulzom na začiatku nohy, limitka ide na jej hranu a stop
za protiľahlú hranu (+ rezerva v bodoch), a že nový BOS nahradí zónu.
"""

from __future__ import annotations

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.jss import JssConfig, JssEngine
from tradebot.strategies.jss.engine import StructAggregator

T0 = 1_756_821_600_000          # utorok 2025-09-02 14:00 UTC
MIN5 = 300_000
OKNO = MarketContext(in_trade_window=True)
MNQ = INSTRUMENTS["mnq_databento"]


def _cfg(**kw) -> JssConfig:
    base = dict(structTF=5, swingLen=2, atrLen=3, impulseAtr=0.5, slBufferAtr=0.0, zoneMaxAtr=0.0,
                triggerMode="both", entryModel="touch", rrRatio=2.0)
    base.update(kw)
    return JssConfig(**base)


def _bar(i: int, o: float, h: float, lo: float, c: float) -> Bar:
    return Bar(time=T0 + i * MIN5, open=o, high=h, low=lo, close=c, volume=10.0)


#: dno 100 na indexe 2 (swing low), rast na vrchol 110 (index 5), impulzný pád pod 100.
#: Posledná býčia sviečka pred impulzom je index 5 (104 -> 109, high 110, low 103).
_ROWS = [
    (106, 107, 103, 104), (104, 105, 101, 102), (102, 103, 100, 101), (101, 104, 101, 103),
    (103, 106, 102, 105), (104, 110, 103, 109), (109, 109, 104, 104.5), (104.5, 105, 101, 101.5),
    (101.5, 102, 98, 98.5),
]


def _run(engine, rows, start=0, ctx=OKNO):
    return [engine.on_bar(_bar(start + i, *r), None, ctx) for i, r in enumerate(rows)]


def test_struktura_skladana_z_grafu_zavrie_bar_na_poslednej_sviecke_periody():
    agg = StructAggregator(10, 5)
    assert agg.push(_bar(0, 1, 2, 0, 1)) == []           # 14:00 — prvá polovica 10m
    out = agg.push(_bar(1, 1, 3, 0.5, 2))                 # 14:05 — posledná 5m sviečka periódy
    assert len(out) == 1 and out[0].high == 3 and out[0].low == 0 and out[0].close == 2


def test_bos_dole_da_supply_zonu_z_poslednej_byčej_sviecky_pred_impulzom():
    e = JssEngine(_cfg(), MNQ, 5)
    _run(e, _ROWS)
    z = e.zone
    assert z is not None and z.direction is Direction.SHORT
    assert (z.top, z.bot) == (110, 103)
    assert z.start_ms == T0 + 5 * MIN5, "zóna sa kreslí od svojej sviečky"


def test_limitka_na_hranu_zony_a_stop_za_zonou_s_rezervou_v_bodoch():
    e = JssEngine(_cfg(slBufferPoints=2.0), MNQ, 5)
    outs = _run(e, _ROWS)
    entries = [o for o in outs[-1].orders if o.action is OrderAction.ENTRY]
    assert entries, "po BOS ide limitka hneď na ďalší bar"
    o = entries[0]
    assert o.order_type is OrderType.LIMIT and o.direction is Direction.SHORT
    assert o.plan.entry == 103 and o.plan.stop_loss == 112
    assert abs(o.plan.take_profit - (103 - 2 * 9)) < 1e-9


def test_dotyk_zony_ju_spotrebuje():
    e = JssEngine(_cfg(), MNQ, 5)
    _run(e, _ROWS)
    _run(e, [(98.5, 103.5, 98, 102)], start=len(_ROWS))
    assert e.zone is None, "po prvom dotyku sa zóna už neobchoduje"


def test_swing_sa_nepouzije_skor_nez_je_potvrdeny():
    """Pád pod dno skôr, než má dno `swingLen` barov vpravo, nie je BOS."""
    e = JssEngine(_cfg(), MNQ, 5)
    rows = [(106, 107, 103, 104), (104, 105, 101, 102), (102, 103, 100, 101), (101, 104, 99.5, 99.6)]
    _run(e, rows)
    assert e.zone is None and e.trend == 0


def _split(rows):
    """Každý riadok ako 10m sviečka z dvoch 5m: prvá o -> stred, druhá nesie high/low aj zavretie."""
    out = []
    for o, h, lo, c in rows:
        m = (o + c) / 2
        out += [(o, max(o, m), min(o, m), m), (m, h, lo, c)]
    return out


def test_zona_tf_struktury_sa_upresni_zonou_nizsieho_tf_a_limitka_ide_na_nu():
    """Štruktúra 10m, upresnenie 5m: 10m zóna 103–110, v nej 5m zóna 104,5–110 — limitka na 104,5."""
    rows = _split(_ROWS)
    rows[10] = (104, 105, 103, 104.8)      # 10m zóna (index 5) = 5m 104->104,8 a 104,8->109
    rows[11] = (104.8, 110, 104.5, 109)
    e = JssEngine(_cfg(structTF=10, refineTF=5, impulseAtr=0.3), MNQ, 5)
    outs = _run(e, rows)
    z = e.zone
    assert z is not None and z.refined
    assert (z.htf_top, z.htf_bot) == (110, 103) and (z.top, z.bot) == (110, 104.5)
    o = [x for x in outs[-1].orders if x.action is OrderAction.ENTRY][0]
    assert o.order_type is OrderType.LIMIT and o.plan.entry == 104.5 and o.plan.stop_loss == 110


def test_bez_upresnenia_ked_refine_tf_nie_je_nizsi_nez_struktura():
    e = JssEngine(_cfg(structTF=5, refineTF=15), MNQ, 5)
    assert e.ragg is None


# --------------------------------------------------------------------------- #
# Fibonacci cez nohu BOS
# --------------------------------------------------------------------------- #


def test_fibo_zona_mimo_pasma_navratu_sa_neobchoduje_a_po_predlzeni_nohy_ano():
    """Noha BOS 110 -> 98, zóna 103–110: hrana 103 je 41,7 % návratu — pod 50 % sa nevstupuje.
    Keď noha pokračuje na 96, tá istá hrana je presne 50 % a limitka sa zadá."""
    e = JssEngine(_cfg(useFibo=True, fibMinPct=50, fibMaxPct=100), MNQ, 5)
    outs = _run(e, _ROWS)
    z = e.zone
    assert (z.leg_start, z.leg_end) == (110, 98) and abs(z.retrace(103) - 41.67) < 0.01
    assert not [o for o in outs[-1].orders if o.action is OrderAction.ENTRY]
    out = e.on_bar(_bar(len(_ROWS), 98.5, 99, 96, 97), None, OKNO)
    assert e.zone.leg_end == 96 and abs(e.zone.retrace(103) - 50.0) < 1e-9
    o = [x for x in out.orders if x.action is OrderAction.ENTRY][0]
    assert o.order_type is OrderType.LIMIT and o.plan.entry == 103


def test_fibo_vypnute_sa_sprava_ako_doteraz_a_ciel_na_extenzii():
    e = JssEngine(_cfg(), MNQ, 5)
    assert [o for o in _run(e, _ROWS)[-1].orders if o.action is OrderAction.ENTRY], "bez filtra limitka hneď po BOS"
    e = JssEngine(_cfg(useFibo=True, fibMinPct=40, tpMode="extension", tpExtensionPct=27, minRR=0.0), MNQ, 5)
    o = [x for x in _run(e, _ROWS)[-1].orders if x.action is OrderAction.ENTRY][0]
    assert abs(o.plan.take_profit - 94.75) < 0.01      # 98 − 27 % z 12, na tick
