"""IBSZones — detekcia zón nezávisí od TF grafu.

Celý rozdiel oproti `ibs` je v tom, KEDY sa okno detekčného TF vydá. Test to meria
priamo: pre rovnaké dáta a rovnaký detekčný TF musí `ZoneSyncHTFFeeder` vydať tú istú
postupnosť okien na 1m, 2m, 3m aj 4m grafe. `HTFFeeder` z `ibs` to nerobí — a je to
zámer, nie chyba, lebo kopíruje Pine predlohu kvôli golden testom proti TradingView.
"""

from __future__ import annotations

import pytest

from tradebot.core.types import Bar
from tradebot.strategies.ibs.htf import HTFFeeder
from tradebot.strategies.ibs.config import IBSConfig
from tradebot.strategies.ibszones.htf import ZoneSyncHTFFeeder

MIN = 60_000
HTF_MIN = 5  #: detekčný TF, na ktorom sa hľadá pattern
CHART_TFS = (1, 2, 3, 4)
DAY = 24 * 60


def _cfg() -> IBSConfig:
    cfg = IBSConfig()
    cfg.zoneDetectionTF = str(HTF_MIN)
    return cfg


def _htf_bars(count: int) -> dict[int, Bar]:
    """`count` uzavretých barov detekčného TF od času 0, s rastúcou cenou."""
    out: dict[int, Bar] = {}
    for i in range(count):
        t = i * HTF_MIN * MIN
        base = 100.0 + i
        out[t] = Bar(time=t, open=base, high=base + 0.5, low=base - 0.5, close=base + 0.2, volume=10.0)
    return out


def _windows_seen(feeder_cls, chart_tf_minutes: int, htf_bars: dict[int, Bar]) -> list[tuple[int, ...]]:
    """Otváracie časy barov každého okna, ktoré feeder vydá pri prehratí celého dňa."""
    feeder = feeder_cls(_cfg(), chart_tf_minutes)
    feeder.load(htf_bars, {t: 10.0 for t in htf_bars})
    seen: list[tuple[int, ...]] = []
    for step in range(DAY // chart_tf_minutes):
        window = feeder.window_for(step * chart_tf_minutes * MIN)
        if window is not None:
            seen.append(tuple(b.time for b in window.bars))
    return seen


@pytest.fixture(scope="module")
def htf_bars() -> dict[int, Bar]:
    return _htf_bars(DAY // HTF_MIN + 4)


def test_zonesync_vydava_rovnake_okna_na_kazdom_tf_grafu(htf_bars):
    """Jadro veci: 5m zóny musia vyjsť rovnako na 1m, 2m, 3m aj 4m grafe."""
    per_tf = {tf: _windows_seen(ZoneSyncHTFFeeder, tf, htf_bars) for tf in CHART_TFS}
    reference = per_tf[CHART_TFS[0]]
    assert reference, "feeder nevydal ani jedno okno - test by nemeral nic"
    for tf in CHART_TFS[1:]:
        assert per_tf[tf] == reference, (
            f"{tf}m graf vydal ine okna ako {CHART_TFS[0]}m graf: "
            f"{len(per_tf[tf])} vs {len(reference)} okien"
        )


def test_zonesync_vyda_kazdy_htf_bar_prave_raz(htf_bars):
    """Žiadna perióda detekčného TF sa nepreskočí ani nezopakuje."""
    for tf in CHART_TFS:
        newest = [w[0] for w in _windows_seen(ZoneSyncHTFFeeder, tf, htf_bars)]
        assert newest == sorted(newest), f"{tf}m: okna nejdu v case"
        assert len(newest) == len(set(newest)), f"{tf}m: to iste okno vydane viackrat"
        step = {b - a for a, b in zip(newest, newest[1:])}
        assert step == {HTF_MIN * MIN}, f"{tf}m: diery alebo preskoky v oknach - kroky {step}"


def test_ibs_feeder_sa_medzi_tf_rozchadza(htf_bars):
    """Kontrolný test: `ibs` sa naozaj správa inak — preto je IBSZones samostatná stratégia.

    Keby tento test raz začal padať, znamená to, že `ibs` zmenil správanie (a golden testy
    proti TradingView to musia potvrdiť) — nie že IBSZones prestal byť potrebný.
    """
    per_tf = {tf: _windows_seen(HTFFeeder, tf, htf_bars) for tf in CHART_TFS}
    assert any(per_tf[tf] != per_tf[CHART_TFS[0]] for tf in CHART_TFS[1:]), (
        "HTFFeeder z ibs dava na vsetkych TF to iste - rozdiel, kvoli ktoremu IBSZones "
        "vznikol, zmizol a tuto stratégiu treba prehodnotiť"
    )
