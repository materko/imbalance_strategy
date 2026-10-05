"""FPC 1.0 (férová cena): engine na syntetických baroch.

Testuje sa mechanika, nie edge: odkiaľ je férová cena (open okna, cena pred správou), kedy vznikne
návrat (signál, pásmo bez vstupu), pokračovanie prvej sviečky s biasom a veľkou sviečkou, straty po sebe
a zatvorenie po okne.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction
from tradebot.strategies.fpc import FpcConfig, FpcEngine, NewsMode

NY = ZoneInfo("America/New_York")
MIN = 60_000
MNQ = INSTRUMENTS["mnq_databento"]


def t(h: int, m: int) -> int:
    """Utorok 2. 9. 2025, čas New York → ms."""
    return int(datetime(2025, 9, 2, h, m, tzinfo=NY).timestamp() * 1000)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


class Sim:
    """Najjednoduchší broker: market vstup na otvorení ďalšieho baru, stop / cieľ vnútri baru."""

    def __init__(self, **kw) -> None:
        base = dict(newsMode=NewsMode.OFF, useS2=False)
        base.update(kw)
        self.e = FpcEngine(FpcConfig(**base), MNQ, 1)
        self.pos = 0
        self.plan = None
        self.pending = None
        self.outs: list = []

    def step(self, ts: int, o: float, h: float, l: float, c: float, v: float = 10.0):
        if self.pending is not None:
            self.plan, self.pending = self.pending, None
            self.pos = 1 if self.plan.direction is Direction.LONG else -1
        if self.pos:
            p = self.plan
            hit = (l <= p.stop_loss or h >= p.take_profit) if self.pos > 0 else (h >= p.stop_loss or l <= p.take_profit)
            if hit:
                self.pos, self.plan = 0, None
        ids = frozenset({"fpc"}) if self.pos else frozenset()
        out = self.e.on_bar(Bar(ts, o, h, l, c, v), ctx=MarketContext(True, position_size=float(self.pos),
                                                                       open_order_ids=ids))
        for oi in entries(out):
            self.pending = oi.plan
        if out.close_session:
            self.pos, self.plan = 0, None
        self.outs.append(out)
        return out


def warm(s: Sim, start: float = 20100.0, end: float = 20000.0) -> None:
    """Bary 1:00–9:26 lineárne zo `start` na `end` (rozsah 2) — bias = opak tohto pohybu."""
    t0, t1 = t(1, 0), t(9, 26)
    n = (t1 - t0) // MIN
    for i in range(n + 1):
        c = start + (end - start) * i / n
        s.step(t0 + i * MIN, c, c + 1, c - 1, c)


def pre_open(s: Sim) -> None:
    """9:27–9:29: knôt 9:28 (high 20006) je swing high potvrdený na 9:29."""
    s.step(t(9, 27), 20000, 20003, 19998, 20000)
    s.step(t(9, 28), 20000, 20006, 19998, 20001)
    s.step(t(9, 29), 20001, 20004, 19999, 20000)


#: 9:31–9:39: rast od férovej ceny 20000, pullback 9:36 (swing low 20036), prieraz dole 9:39 na 20032
RISE = [
    (20000, 20012, 19999, 20010),
    (20010, 20022, 20009, 20020),
    (20020, 20032, 20019, 20030),
    (20030, 20042, 20029, 20040),
    (20040, 20052, 20039, 20050),
    (20050, 20051, 20036, 20046),
    (20046, 20058, 20045, 20056),
    (20056, 20060, 20050, 20055),
    (20055, 20056, 20030, 20032),
]


def morning(s: Sim, first=(20000, 20004, 19996, 20000), rise=RISE):
    """Otvorenie 9:30 (doji = bez pokračovania) a rast; vráti výstupy 9:30–9:39."""
    outs = [s.step(t(9, 30), *first)]
    for i, b in enumerate(rise, start=1):
        outs.append(s.step(t(9, 30 + i), *b))
    return outs


# ---------------------------------------------------------------------------- #

def test_ferova_cena_je_open_okna_a_kresli_sa():
    s = Sim()
    warm(s)
    pre_open(s)
    outs = morning(s)
    assert s.e.fair == 20000
    kinds = {d.kind for d in outs[0].drawings if hasattr(d, "kind")}
    assert {"fpc_fair", "fpc_window", "fpc_zone"} <= {str(k) for k in kinds}


def test_navrat_short_na_prieraz_struktury_nad_ferovou_cenou():
    s = Sim()
    warm(s)
    pre_open(s)
    outs = morning(s)
    vstupy = [(i, oi) for i, o in enumerate(outs) for oi in entries(o)]
    assert len(vstupy) == 1
    i, oi = vstupy[0]
    assert i == 9   # 9:39, zavretie 20032 pod swing low 20036
    p = oi.plan
    assert p.direction is Direction.SHORT
    assert (p.entry, p.stop_loss, p.take_profit) == (20032, 20057, 19994)
    assert p.qty == MNQ.qty_for_risk(100.0, 25.0)


def test_v_pasme_bez_vstupu_sa_nevracia():
    s = Sim(minPct=200.0)   # pásmo 76 bodov, cena je len 32 nad férovou
    warm(s)
    pre_open(s)
    assert not any(entries(o) for o in morning(s))


def test_ciel_na_ferovej_cene():
    s = Sim(tpMode="fair")
    warm(s)
    pre_open(s)
    p = entries(morning(s)[9])[0].plan
    assert p.take_profit == 20000 and p.stop_loss == 20057


def test_pokracovanie_v_smere_prvej_sviecky_s_biasom():
    s = Sim()
    warm(s)                 # za 8 h trh klesol → bias long
    pre_open(s)
    out = s.step(t(9, 30), 20000, 20010, 19995, 20008)   # zelená, zavrie nad swing high 20006
    assert s.e.bias == 1
    p = entries(out)[0].plan
    assert p.direction is Direction.LONG
    assert (p.entry, p.take_profit, p.stop_loss) == (20008, 20046, 19983)


def test_pokracovanie_proti_biasu_sa_nerobi():
    s = Sim()
    warm(s, start=19900.0)  # za 8 h trh stúpol → bias short
    pre_open(s)
    out = s.step(t(9, 30), 20000, 20010, 19995, 20008)
    assert s.e.bias == -1 and not entries(out)
    s2 = Sim(useBias=False)
    warm(s2, start=19900.0)
    pre_open(s2)
    assert entries(s2.step(t(9, 30), 20000, 20010, 19995, 20008))


def test_velka_otvaracia_sviecka_zdvojnasobi_tp_aj_sl():
    s = Sim()
    warm(s)
    pre_open(s)
    p = entries(s.step(t(9, 30), 19990, 20020, 19988, 20010))[0].plan   # rozsah 32 > 25
    assert (p.take_profit - p.entry, p.entry - p.stop_loss) == (76, 50)


def test_v_den_spravy_je_ferova_cena_pred_spravou():
    s = Sim(newsMode=NewsMode.AUTO)
    t0 = t(6, 0)
    for i in range(150):   # 6:00–8:29 pokojne
        s.step(t0 + i * MIN, 20000, 20001, 19999, 20000)
    s.step(t(8, 30), 20000, 20062, 19999, 20060)   # skok o 8:30, cena pred správou 20000
    for i in range(1, 60):  # 8:31–9:29 hore
        s.step(t(8, 30) + i * MIN, 20060, 20061, 20059, 20060)
    assert s.e._sid == 5 and s.e.fair == 20000
    s.step(t(9, 30), 20060, 20064, 20058, 20060)
    assert s.e.fair == 20000          # NY ráno: nie open 9:30 (20060), ale cena pred správou


def test_bez_skoku_je_ferova_cena_open_930():
    s = Sim(newsMode=NewsMode.AUTO)
    t0 = t(6, 0)
    for i in range(210):   # 6:00–9:29 pokojne, aj 8:30
        s.step(t0 + i * MIN, 20000, 20001, 19999, 20000)
    s.step(t(9, 30), 20010, 20012, 20008, 20010)
    assert s.e.fair == 20010


def _loss_then_signal(max_loss_row: int):
    """Short 9:39 dostane stop, potom znova prieraz dole nad férovou cenou."""
    s = Sim(maxLossRow=max_loss_row)
    warm(s)
    pre_open(s)
    morning(s)
    s.step(t(9, 40), 20032, 20060, 20031, 20058)   # stop 20057
    assert s.e.loss_row == 1
    return [s.step(t(9, 41), 20058, 20066, 20057, 20064),
            s.step(t(9, 42), 20064, 20065, 20050, 20052)]   # displacement dole 52 nad férovou cenou


def test_po_n_stratach_po_sebe_okno_konci():
    assert not any(entries(o) for o in _loss_then_signal(1))
    assert any(entries(o) for o in _loss_then_signal(3))


def test_zatvorenie_po_konci_okna():
    s = Sim(s1Len=12, closeAfter=5)   # okno 9:30–9:41
    warm(s)
    pre_open(s)
    morning(s)                          # short 9:39
    closed = None
    for m in range(40, 60):
        out = s.step(t(9, m), 20030, 20031, 20029, 20030)   # ani stop, ani cieľ
        if out.close_session:
            closed = m
            break
    assert closed == 47                 # koniec okna 9:42 + 5 min
