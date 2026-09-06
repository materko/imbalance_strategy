"""Tri kusy Pine, ktoré v porte chýbali — nájdené systematickým prechodom skriptu.

Spoločné majú to, že ich referenčná konfigurácia nikdy nespustila, takže parita
s TradingView sedela aj bez nich. Zoznam a spôsob hľadania je v
`docs/AUDIT_pine_2026-09-05.md`.
"""

from __future__ import annotations

import pytest

from tradebot.core import (
    MNQ,
    Bar,
    BarHistory,
    Direction,
    IBSConfig,
    IBSEngine,
    MarketContext,
    StateMachine,
    Zone,
    ZoneBook,
    ZoneState,
)
from tradebot.core.drawing import DrawKind, DrawUpdate
from tradebot.core.zones import ZoneSource

T0 = 1_756_684_800_000
MIN3 = 180_000


def bar(i: int, o: float, h: float, low: float, c: float, v: float = 100.0) -> Bar:
    return Bar(time=T0 + i * MIN3, open=o, high=h, low=low, close=c, volume=v)


# --------------------------------------------------------------------------- #
# Pine 2271-2288 — koniec seansy utne zóny v STATE 0-3
# --------------------------------------------------------------------------- #


@pytest.fixture
def machine():
    cfg = IBSConfig()
    return cfg, StateMachine(cfg, MNQ, ZoneBook(cfg, MNQ, 3))


def _zone(book: ZoneBook, state: ZoneState) -> Zone:
    z = book.create_raw(Direction.LONG, 110.0, 100.0, T0, ZoneSource.SD)
    z.state = state
    return z


@pytest.mark.parametrize(
    "state",
    [ZoneState.WAITING, ZoneState.GAP_FOUND, ZoneState.LEFT_ZONE, ZoneState.CONFIRMED],
)
def test_koniec_seansy_utne_zonu_v_stave_0_az_3(machine, state):
    """Bez toho zóna prežije medzeru medzi seansami a obchoduje sa v tej ďalšej."""
    cfg, m = machine
    z = _zone(m.book, state)
    m.cut_forming_zones(bar(1, 105, 106, 104, 105))
    assert z.state == ZoneState.INVALID
    assert z.used is True


@pytest.mark.parametrize("state", [ZoneState.READY, ZoneState.ORDER_PENDING])
def test_stavy_4_a_5_sa_nedotknu(machine, state):
    """Tie majú vlastnú kontrolu konca seansy — dvojitá by ich zrušila priskoro."""
    cfg, m = machine
    z = _zone(m.book, state)
    m.cut_forming_zones(bar(1, 105, 106, 104, 105))
    assert z.state == state


def test_rez_utne_aj_box(machine):
    cfg, m = machine
    _zone(m.book, ZoneState.WAITING)
    m.drawings = []
    m.cut_forming_zones(bar(1, 105, 106, 104, 105))
    assert any(isinstance(d, DrawUpdate) and d.field == "x2_ms" for d in m.drawings)


# --------------------------------------------------------------------------- #
# Pine 2185 — vyplnenie orderu uzavrie zónu vizuálne
# --------------------------------------------------------------------------- #


def _fill(cfg, *, pending_invalid: bool) -> list:
    book = ZoneBook(cfg, MNQ, 3)
    m = StateMachine(cfg, MNQ, book)
    z = book.create_raw(Direction.LONG, 110.0, 100.0, T0, ZoneSource.SD)
    z.state = ZoneState.ORDER_PENDING
    z.pending_invalid = pending_invalid
    z.entry_done = True
    history = BarHistory(maxlen=64)
    history.append(bar(0, 105, 106, 104, 105))
    ctx = MarketContext(in_trade_window=True, open_order_ids=frozenset({z.order_id}))
    m.drawings = []
    m._state5(z, bar(1, 105, 106, 104, 105), history, ctx)
    return m.drawings


def test_vyplnenie_uzavrie_zonu():
    resizes = _fill(IBSConfig(invalidateOnFill=True), pending_invalid=False)
    assert any(isinstance(d, DrawUpdate) and d.field == "x2_ms" for d in resizes)


def test_bez_prepinaca_sa_zona_neuzavrie():
    assert _fill(IBSConfig(invalidateOnFill=False), pending_invalid=False) == []


def test_zona_cez_ktoru_cena_presla_sa_uzavrie_aj_bez_prepinaca():
    """Pine: `invalidateOnFill or zPendingInvalid` — stačí jedno z dvoch."""
    resizes = _fill(IBSConfig(invalidateOnFill=False), pending_invalid=True)
    assert any(isinstance(d, DrawUpdate) and d.field == "x2_ms" for d in resizes)


# --------------------------------------------------------------------------- #
# Pine 682-701 — box na sviečke, ktorá vytvorila gap
# --------------------------------------------------------------------------- #


def _engine(**over):
    cfg = IBSConfig(**over)
    cfg.minImbSizePoints = 1.0
    return IBSEngine(cfg, MNQ, 3)


def _feed_gap(engine) -> list:
    """Tri sviečky s medzerou nahor: low poslednej je nad high tej prvej."""
    drawings = []
    for b in (bar(0, 100, 101, 99, 100), bar(1, 101, 106, 101, 105), bar(2, 106, 108, 104, 107)):
        out = engine.on_bar(b, None, MarketContext(in_trade_window=True))
        drawings = out.drawings
    return drawings


def test_gap_nakresli_box_na_prostrednej_sviecke():
    boxes = [d for d in _feed_gap(_engine()) if getattr(d, "kind", None) is DrawKind.IMB_BOX]
    assert len(boxes) == 1
    # telo prostrednej sviecky: open 101, close 105
    assert (boxes[0].y1, boxes[0].y2) == (105.0, 101.0)
    assert boxes[0].x1_ms == T0 + MIN3


def test_bez_medzery_sa_nekresli_nic():
    engine = _engine()
    for b in (bar(0, 100, 110, 90, 100), bar(1, 100, 110, 90, 100), bar(2, 100, 110, 90, 100)):
        out = engine.on_bar(b, None, MarketContext(in_trade_window=True))
    assert [d for d in out.drawings if getattr(d, "kind", None) is DrawKind.IMB_BOX] == []


def test_vypnuty_prepinac_nekresli():
    boxes = [
        d for d in _feed_gap(_engine(showImbalance=False))
        if getattr(d, "kind", None) is DrawKind.IMB_BOX
    ]
    assert boxes == []
