"""IBS Entry Zone — zóny z veľkých imbalance (FVG) na vyšších TF.

Najdôležitejší je prvý test: vyššie TF sa musia skladať **rovnako** ako
`tradebot/core/candles.py`. Keby sa to pravidlo rozišlo, Freqtrade a MultiCharts by
videli iné sviečky a porovnanie platforiem by prestalo niečo znamenať.
"""

from __future__ import annotations

import pytest

from tradebot.core.candles import resample_ohlcv
from tradebot.core.types import Bar, Direction
from tradebot.strategies.ibsentry.config import IBSEntryZoneConfig
from tradebot.strategies.ibsentry.fvg import FvgDetector, FvgHit, TimeframeAggregator

MIN = 60_000


def _bars(n: int, tf_minutes: int = 1) -> list[Bar]:
    """`n` barov s mierne kolísajúcou cenou — na skladanie TF stačí, nech nie sú ploché."""
    out = []
    for i in range(n):
        base = 100.0 + (i % 7) * 0.3
        out.append(
            Bar(
                time=i * tf_minutes * MIN,
                open=base,
                high=base + 0.4,
                low=base - 0.4,
                close=base + 0.1,
                volume=float(i % 5 + 1),
            )
        )
    return out


@pytest.mark.parametrize("tf", [5, 15, 30, 60])
def test_skladanie_tf_sedi_s_core_candles(tf):
    """`TimeframeAggregator` musí dať tie isté sviečky ako `resample_ohlcv`."""
    pd = pytest.importorskip("pandas")
    bars = _bars(60 * 4)

    agg = TimeframeAggregator(tf)
    mine = [b for b in (agg.push(bar) for bar in bars) if b is not None]

    df = pd.DataFrame(
        {
            "date": pd.to_datetime([b.time for b in bars], unit="ms", utc=True),
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
        }
    )
    ref = resample_ohlcv(df, tf)
    # Posledná sviečka agregátora je ešte otvorená, referenciu skrátime rovnako.
    ref = ref.iloc[: len(mine)]

    assert len(mine) == len(ref), f"{tf}m: iny pocet sviecok"
    for got, (_, want) in zip(mine, ref.iterrows()):
        assert got.time == int(want["date"].timestamp() * 1000), f"{tf}m: iny cas sviecky"
        assert got.open == pytest.approx(want["open"])
        assert got.high == pytest.approx(want["high"])
        assert got.low == pytest.approx(want["low"])
        assert got.close == pytest.approx(want["close"])
        assert got.volume == pytest.approx(want["volume"])


def _detector() -> FvgDetector:
    return FvgDetector((5,))


def _push_5m(det: FvgDetector, highs_lows: list[tuple[float, float]], min_size: float = 1.0) -> list[FvgHit]:
    """Nakŕmi detektor 1m barmi tak, aby vznikli 5m sviečky s daným high/low."""
    found: list[FvgHit] = []
    t = 0
    for high, low in highs_lows:
        for _ in range(5):
            found += det.on_bar(Bar(time=t, open=low, high=high, low=low, close=high, volume=1.0), min_size)
            t += MIN
    found += det.on_bar(Bar(time=t, open=low, high=high, low=low, close=high, volume=1.0), min_size)
    return found


def test_najde_bullish_fvg():
    """Trojica, kde low tretej je nad high prvej, je bullish FVG (dopyt -> LONG zóna)."""
    found = _push_5m(_detector(), [(100.0, 99.0), (104.0, 101.0), (108.0, 105.0)])
    assert len(found) == 1, f"cakal som jednu medzeru, dostal {len(found)}"
    hit = found[0]
    assert hit.direction == 1
    assert hit.bot == pytest.approx(100.0)  # high prvej sviečky
    assert hit.top == pytest.approx(105.0)  # low tretej
    assert hit.tf_minutes == 5


def test_najde_bearish_fvg():
    found = _push_5m(_detector(), [(108.0, 105.0), (104.0, 101.0), (100.0, 99.0)])
    assert len(found) == 1
    assert found[0].direction == -1
    assert found[0].top == pytest.approx(105.0)
    assert found[0].bot == pytest.approx(100.0)


def test_mala_medzera_sa_nepocita():
    """Gap pod `min_size` sa nesmie stať zónou."""
    assert _push_5m(_detector(), [(100.0, 99.0), (104.0, 101.0), (108.0, 100.2)], min_size=5.0) == []


def test_zony_z_fvg_idu_do_tej_istej_knihy_ako_sd():
    """Jadro veci: zóna z FVG je obyčajná zóna v `ZoneBook`, nie filter.

    Kontroluje sa zdroj, smer aj to, že ju automat dostane rovnako ako SD zónu.
    """
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies.ibs.zones import ZoneSource
    from tradebot.strategies.ibsentry.engine import IBSEntryZoneEngine

    cfg = IBSEntryZoneConfig()
    cfg.fvgUse15m = cfg.fvgUse30m = cfg.fvgUse60m = False  # len 5m, nech je vzorka čistá
    cfg.fvgMinSize = type(cfg).SIZE_FIELDS and cfg.fvgMinSize
    inst = INSTRUMENTS["mnq_databento"]
    eng = IBSEntryZoneEngine(cfg, inst, 1)

    out = type("O", (), {"drawings": []})()
    t = 0
    for high, low in [(100.0, 99.0), (104.0, 101.0), (108.0, 105.0)]:
        for _ in range(5):
            eng.history.append(Bar(time=t, open=low, high=high, low=low, close=high, volume=1.0))
            eng._spawn_extra_zones(eng.history.current, out)
            t += MIN
    eng.history.append(Bar(time=t, open=105.0, high=108.0, low=105.0, close=108.0, volume=1.0))
    eng._spawn_extra_zones(eng.history.current, out)

    fvg_zones = [z for z in eng.book.zones if z.source is ZoneSource.FVG]
    assert len(fvg_zones) == 1, f"cakal som jednu zonu z FVG, kniha ma {len(eng.book.zones)} zon"
    z = fvg_zones[0]
    assert z.direction is Direction.LONG, "bullish FVG je dopyt, teda LONG zona"
    assert z.variant == "FVG5m"
    assert eng.fvg_zones_created == 1
    assert out.drawings, "zona sa musi aj nakreslit, rovnako ako SD zona"


def test_vypnuty_zdroj_nevyrobi_nic():
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies.ibsentry.engine import IBSEntryZoneEngine

    cfg = IBSEntryZoneConfig()
    cfg.enableFvgTrading = False
    eng = IBSEntryZoneEngine(cfg, INSTRUMENTS["mnq_databento"], 1)
    out = type("O", (), {"drawings": []})()
    t = 0
    for high, low in [(100.0, 99.0), (104.0, 101.0), (108.0, 105.0), (108.0, 105.0)]:
        for _ in range(5):
            eng.history.append(Bar(time=t, open=low, high=high, low=low, close=high, volume=1.0))
            eng._spawn_extra_zones(eng.history.current, out)
            t += MIN
    assert eng.fvg_zones_created == 0
    assert eng.book.zones == []
