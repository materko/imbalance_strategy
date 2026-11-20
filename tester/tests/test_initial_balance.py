"""Štatistika Initial Balance na vymyslenom dni, kde sa dá každé číslo spočítať rukou."""

import numpy as np
import pandas as pd
import pytest

from tester import initial_balance as ib

#: (minúta v New Yorku, cena) — medzi bodmi lineárne, sviečky bez knôtov
PATH = [
    (9 * 60 + 30, 104), (9 * 60 + 40, 100),   # IB low 100 o 9:40 → bias lowFirst
    (10 * 60 + 10, 110), (10 * 60 + 29, 108),  # IB high 110 o 10:10, IB close 108
    (10 * 60 + 35, 105),                       # pred prierazom až 105 → before-break 0,5
    (10 * 60 + 47, 111),                       # prieraz hore v 5m sviečke 10:45
    (11 * 60, 107),                            # pullback 107 pred maximom → HOS/LOS 0,3
    (12 * 60, 116),                            # maximum seansy → extension 0,6
    (15 * 60, 104),                            # najhlbší návrat → max retracement 0,6
    (15 * 60 + 59, 106),
]


def _day(date="2026-07-15"):
    mins = np.arange(9 * 60 + 30, 16 * 60)
    xs, ys = zip(*PATH)
    price = np.interp(mins, xs, ys)
    et = pd.Timestamp(date, tz="America/New_York") + pd.to_timedelta(mins, unit="min")
    return pd.DataFrame({"date": et.tz_convert("UTC"), "open": price, "high": price,
                         "low": price, "close": price, "volume": 1.0})


def test_day_matches_hand_computation():
    (row,) = ib.compute_days(_day())
    assert row["bias"] == "lowFirst" and row["ibhT"] == "10:10" and row["iblT"] == "09:40"
    assert row["ib_high"] == 110 and row["ib_low"] == 100
    assert row["ibClose"] == pytest.approx(0.2)
    assert ib.close_band(row["ibClose"]) == 3
    assert row["outcome"] == "high" and row["dir"] == "bull" and not row["dbl"]
    assert row["slot"] == row["brkET"] == "10:45"
    assert row["brkMin"] == "10:46"   # prvá minúta s cenou nad 110
    assert row["bbScale"] == pytest.approx(0.5) and row["bbZone"] == 6 and row["bbSlot"] == "10:35"
    assert row["ext"] == pytest.approx(0.6) and row["extSlot"] == "12:00"
    assert row["scale"] == pytest.approx(0.6) and row["zone"] == 7 and row["retrSlot"] == "15:00"
    assert row["magicScale"] == pytest.approx(0.3) and row["magicZone"] == 4
    assert row["magicSlot"] == "11:00"


def test_no_break_day():
    df = _day()
    df["high"] = df["low"] = df["open"] = df["close"] = df["close"].clip(100, 110)
    (row,) = ib.compute_days(df)
    assert row["outcome"] == "none" and row["dir"] is None and row["scale"] is None


def test_zones_and_bands():
    assert ib.zone(0.0) == 1 and ib.zone(0.09) == 1 and ib.zone(0.1) == 2 and ib.zone(1.92) == 20
    assert ib.signed_zone(-0.05) == -1 and ib.signed_zone(0.3) == 4
    assert ib.ext_zone(0.6) == 7
    assert ib.close_band(1.0) == 10 and ib.close_band(1.2) is None
    assert ib.ib_pct_band(0.25) == 1 and ib.ib_pct_band(5) == 5
    assert ib.median([1, 2, 3, 4]) == 2.5 and ib.percentile([0, 10], 70) == pytest.approx(7)


def test_summary_counts_and_filters():
    days = ib.compute_days(pd.concat([_day("2026-07-14"), _day("2026-07-15")]))
    pre = ib.summary(days)
    assert pre["n"] == 2 and pre["break_high_pct"] == 100
    assert pre["break_time"]["median"] == "10:50"   # koniec 5m slotu s mediánom
    post = ib.summary(days, ib.Filter(scope="post", dir="bull"))
    assert post["n"] == 2 and post["max_ext"]["median"] == pytest.approx(0.6)
    assert ib.summary(days, ib.Filter(dow=1))["n"] == 0   # oba dni sú utorok a streda
    assert ib.summary(days, ib.Filter(dow=2))["n"] == 1


def test_webapp_api(tmp_path, monkeypatch):
    """Karta Initial Balance: symboly z archívu, súhrn s filtrom a tabuľka dní."""
    from fastapi.testclient import TestClient

    from tester.webapp.api import ib as api_ib
    from tester.webapp.app import create_app
    from tester.webapp.runner import BacktestRunner
    from tester.webapp.store import RunStore

    df = pd.concat([_day("2026-07-14"), _day("2026-07-15")], ignore_index=True)
    df.to_feather(tmp_path / "ES_USD-1m.2026.feather")
    monkeypatch.setattr(ib, "FUTURES_DIR", tmp_path)
    monkeypatch.setattr(api_ib, "_CACHE", {})
    store = RunStore(tmp_path / "runs")
    client = TestClient(create_app(store, BacktestRunner(store)))
    meta = client.get("/api/ib/meta").json()
    assert meta["symbols"] == ["ES"] and meta["sessions"]["ny"]["ib"] == ["09:30", "10:30"]
    d = client.get("/api/ib/summary", params={"symbol": "ES"}).json()
    assert d["n"] == 2 and d["total"] == 2 and d["break_high_pct"] == 100
    assert [r["date"] for r in d["days"]] == ["2026-07-15", "2026-07-14"]
    d = client.get("/api/ib/summary", params={"symbol": "ES", "scope": "post", "dow": 3}).json()
    assert d["n"] == 1 and d["max_retr"]["median"] == pytest.approx(0.6)
    assert client.get("/api/ib/summary", params={"symbol": "NQ"}).status_code == 404
    assert client.get("/api/ib/summary", params={"symbol": "ES", "scope": "x"}).status_code == 422
