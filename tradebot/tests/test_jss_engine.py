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
