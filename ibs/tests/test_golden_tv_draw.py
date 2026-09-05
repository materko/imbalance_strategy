"""Parita KRESLENIA s TradingView — Market Structure a likvidita.

Referencia je `golden/tv_draw_btcusdt_binance_3m.json`: súradnice objektov,
ktoré TradingView naozaj nakreslil, odčítané cez dočasné `log.info` v Pine
(podrobnosti sú v `_comment` toho súboru).

Okno je **súvislé** — obsahuje všetky objekty, ktoré TradingView v ňom nakreslil.
Vďaka tomu test chytí nielen chýbajúce objekty, ale aj tie navyše.

SD zóny a TP/SL boxy sem nepatria; tie stráži `test_golden_tv_binance.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ibs.core import (
    DrawKind,
    DrawLabel,
    DrawLine,
    IBSEngine,
    MarketContext,
    SessionClock,
    load_profile,
)

GOLDEN = json.loads(
    (Path(__file__).parent / "golden" / "tv_draw_btcusdt_binance_3m.json").read_text(
        encoding="utf-8"
    )
)

#: Pine kreslí likviditný štítok ako „X ↓“ / „X ↑“; v logu je to bez šípky.
_LIQ_TEXT = {"X_DOWN": "X \u2193", "X_UP": "X \u2191"}


def _ms(iso: str) -> int:
    import pandas as pd

    return int(pd.Timestamp(iso, tz="UTC").timestamp() * 1000)


@pytest.fixture(scope="module")
def objects():
    """Objekty, ktoré engine nakreslil v tom istom okne ako TradingView."""
    pytest.importorskip("pandas")
    import pandas as pd

    from ibs.tools.scan_zones import _load, _to_bar

    cfg, inst = load_profile("golden_binance_btcusdt_3m")
    try:
        chart = _load("binance", "3m")
    except SystemExit as exc:
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")

    chart["date"] = pd.to_datetime(chart["date"], utc=True)
    # Rozbeh od 08-24, aby mal engine históriu (bias, posledné swingy) rovnako
    # naplnenú ako TradingView, kým sa dostane do porovnávaného okna.
    chart = chart[(chart["date"] >= "2026-08-24") & (chart["date"] <= "2026-09-04T06:00")]

    clock = SessionClock(cfg)
    engine = IBSEngine(cfg, inst, 3)
    lo, hi = (_ms(t) for t in GOLDEN["window_utc"])

    found: set[tuple] = set()
    for row in chart.itertuples(index=False):
        bar = _to_bar(row)
        out = engine.on_bar(
            bar, None, MarketContext(in_trade_window=clock.state(bar.time).in_trade_window)
        )
        if not lo <= bar.time <= hi:
            continue
        for o in out.drawings:
            if o.kind is DrawKind.SWING and isinstance(o, DrawLabel):
                found.add(("SWING", bar.time, o.x_ms, round(o.y, 4), o.text))
            elif o.kind is DrawKind.STRUCTURE and isinstance(o, DrawLine):
                found.add(("STRUCT", bar.time, o.x1_ms, round(o.y1, 4), o.text, o.x2_ms))
            elif o.kind is DrawKind.LIQ_SWEEP and isinstance(o, DrawLine):
                found.add(("LIQ", bar.time, o.x1_ms, round(o.y1, 4), o.text, o.x2_ms))
    return found, inst


def _expected(inst) -> set[tuple]:
    out = set()
    for o in GOLDEN["objects"]:
        bar = _ms(o["bar_utc"])
        if o["kind"] == "SWING":
            # Pine loguje surovú cenu pivota; štítok sa kreslí o 25 tickov vedľa.
            off = inst.tick_size * 25
            y = o["y"] + off if o["text"] in ("HH", "LH") else o["y"] - off
            out.add(("SWING", bar, o["x_ms"], round(y, 4), o["text"]))
        else:
            text = _LIQ_TEXT.get(o["text"], o["text"])
            out.add((o["kind"], bar, o["x1_ms"], round(o["y"], 4), text, o["x2_ms"]))
    return out


def _fmt(key: tuple) -> str:
    import pandas as pd

    def t(ms):
        return pd.Timestamp(ms, unit="ms", tz="UTC").strftime("%m-%d %H:%M")

    tail = f" x2={t(key[5])}" if len(key) > 5 else ""
    return f"{key[0]} na {t(key[1])}: x1={t(key[2])} y={key[3]} {key[4]}{tail}"


def test_pocty_objektov_podla_druhu(objects):
    from collections import Counter

    ours, _ = objects
    assert Counter(k[0] for k in ours) == Counter(o["kind"] for o in GOLDEN["objects"])


def test_nekreslime_nic_navyse(objects):
    """Okno je súvislé, takže čokoľvek navyše je chyba."""
    ours, inst = objects
    extra = sorted(ours - _expected(inst), key=lambda k: k[1])
    assert extra == [], "objekty navyše:\n  " + "\n  ".join(_fmt(k) for k in extra)


def test_nic_nam_nechyba(objects):
    ours, inst = objects
    missing = sorted(_expected(inst) - ours, key=lambda k: k[1])
    assert missing == [], "chýbajúce objekty:\n  " + "\n  ".join(_fmt(k) for k in missing)


@pytest.mark.parametrize("kind", ["SWING", "STRUCT", "LIQ"])
def test_kazdy_druh_sedi_uplne(objects, kind):
    """Aby bolo z výpisu hneď vidieť, ktorý modul sa rozišiel."""
    ours, inst = objects
    a = {k for k in ours if k[0] == kind}
    b = {k for k in _expected(inst) if k[0] == kind}
    assert a == b
