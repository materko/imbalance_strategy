"""Parita Elliott zigzagu s TradingView.

Referencia je `golden/tv_elliott_btcusdt_binance_3m.json` — body, ktoré Pine
naozaj pushol do zigzagu, odčítané cez dočasný `log.info` v `ewAddPoint`.

**Porovnávajú sa PUSH UDALOSTI, nie finálny zoznam bodov.** Pine loguje len push;
keď neskôr posunie posledný bod na extrémnejšiu hodnotu, log nevznikne. Prvý pokus
porovnával TV pushe proti našim finálnym bodom a vyšlo 32 z 41 — vyzeralo to ako
chyba v porte, hoci to bola chyba merania.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

GOLDEN = json.loads(
    (Path(__file__).parent / "golden" / "tv_elliott_btcusdt_binance_3m.json").read_text(
        encoding="utf-8"
    )
)

#: Do tohto času je odčítaná postupnosť z TradingView súvislá. Za ním sa už
#: v paneli logov nedalo spoľahlivo doskrolovať všetko, takže sa tam kontroluje
#: len to, že nám žiadny bod nechýba — nie že nemáme žiadny navyše.
CONTIGUOUS_UNTIL_MS = 1_788_472_800_000  # 2026-09-03 22:00 UTC


@pytest.fixture(scope="module")
def pushes():
    """Push udalosti nášho zigzagu — (ts_ms, cena, typ)."""
    pytest.importorskip("pandas")
    import pandas as pd

    from ibs.core import IBSEngine, MarketContext, SessionClock, load_profile
    from ibs.core.ta.elliott import ElliottWaves
    from ibs.tools.scan_zones import _load, _to_bar

    cfg, inst = load_profile("btcusdt_3m_binance_tv")
    cfg.showElliott = True
    cfg.ewSwingLen = GOLDEN["ewSwingLen"]
    cfg.ewMinWavePoints = float(GOLDEN["ewMinWavePoints"])

    try:
        chart = _load("binance", "3m")
    except SystemExit as exc:
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    chart["date"] = pd.to_datetime(chart["date"], utc=True)
    # Rozbeh 13 dní dopredu, aby mal zigzag rovnaký stav ako TradingView.
    chart = chart[chart["date"] >= "2026-08-20"]

    seen: list[tuple[int, float, int]] = []
    original = ElliottWaves._add

    def spy(self, price, ts_ms, typ, bar):
        pushed = original(self, price, ts_ms, typ, bar)
        if pushed:
            seen.append((ts_ms, round(price, 4), typ))
        return pushed

    ElliottWaves._add = spy
    try:
        clock, engine = SessionClock(cfg), IBSEngine(cfg, inst, 3)
        for row in chart.itertuples(index=False):
            bar = _to_bar(row)
            engine.on_bar(
                bar, None, MarketContext(in_trade_window=clock.state(bar.time).in_trade_window)
            )
    finally:
        ElliottWaves._add = original

    return seen, int(chart["date"].max().timestamp() * 1000)


def _expected(end_ms: int) -> list[tuple[int, float, int]]:
    return [
        (p["ms"], round(p["price"], 4), p["typ"])
        for p in GOLDEN["points"]
        if p["ms"] <= end_ms
    ]


def _fmt(p) -> str:
    import pandas as pd

    return f"{pd.Timestamp(p[0], unit='ms', tz='UTC'):%m-%d %H:%M} {p[1]} typ={p[2]}"


def test_ziadny_zigzag_bod_nechyba(pushes):
    ours, end_ms = pushes
    missing = [p for p in _expected(end_ms) if p not in set(ours)]
    assert missing == [], "chýbajúce body:\n  " + "\n  ".join(_fmt(p) for p in missing)


def test_nemame_body_navyse(pushes):
    """Len v úseku, kde je odčítaná postupnosť z TradingView súvislá."""
    ours, _ = pushes
    expected = {p for p in _expected(CONTIGUOUS_UNTIL_MS)}
    lo = min(p[0] for p in expected)
    mine = {p for p in ours if lo <= p[0] <= CONTIGUOUS_UNTIL_MS}
    extra = sorted(mine - expected)
    assert extra == [], "body navyše:\n  " + "\n  ".join(_fmt(p) for p in extra)


def test_zigzag_striedaju_smery(pushes):
    """Po pushnutí sa typ musí vždy otočiť — inak by to nebol zigzag."""
    ours, _ = pushes
    types = [p[2] for p in ours]
    assert all(a != b for a, b in zip(types, types[1:]))
