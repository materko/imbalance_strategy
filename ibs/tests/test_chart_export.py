"""Graf páru vo webapp: export kresieb z behu, ich serializácia a API nad nimi.

Reťazec je: engine kreslí → `EngineRunner.registry` drží finálny stav →
`export_chart` zapíše `chart.json.gz` → webapp ho presunie k behu → stránka si
pýta okno sviečok (`/api/candles`) a okno kresieb (`/api/runs/<id>/chart`).
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from ibs.adapters.freqtrade import EngineRunner
from ibs.adapters.freqtrade.runner import export_chart
from ibs.core import MNQ, Bar, DrawBg, DrawBox, DrawKind, DrawLabel, DrawLine, IBSConfig, LabelStyle, LineStyle
from ibs.core.drawing import merge_backgrounds, object_to_dict, objects_to_dicts
from ibs.webapp import chart as chart_mod
from ibs.webapp.store import CHART_FILE, RunStore

T0 = 1_756_684_800_000  # 2025-09-01 00:00 UTC
MIN3 = 180_000


# --------------------------------------------------------------------------- #
# serializácia
# --------------------------------------------------------------------------- #


def test_box_to_dict_keeps_only_non_default_fields():
    box = DrawBox(kind=DrawKind.SD_ZONE_POST, x1_ms=0, y1=110.0, x2_ms=1000, y2=100.0, border_color="#fff",
                  fill_color="#10b98126", border_style=LineStyle.DOTTED, obj_id="z0.post", zone_uid=7, text="zona")
    assert object_to_dict(box) == {
        "k": "sd_zone_post", "t": "box", "x1": 0, "y1": 110.0, "x2": 1000, "y2": 100.0,
        "bc": "#fff", "fc": "#10b98126", "bs": "dotted", "tx": "zona", "z": 7,
    }
    plain = DrawBox(kind=DrawKind.TP_BOX, x1_ms=0, y1=1.0, x2_ms=1, y2=0.0, border_color="#000", obj_id="a", border_width=0,
                    extend_right=True)
    d = object_to_dict(plain)
    assert d["bw"] == 0 and d["er"] is True and "fc" not in d and "bs" not in d and "z" not in d and "id" not in d


def test_line_label_and_bg_to_dict():
    line = DrawLine(kind=DrawKind.STRUCTURE, x1_ms=1, y1=2.0, x2_ms=3, y2=4.0, color="#abc", style=LineStyle.DASHED,
                    width=2, obj_id="l1", text="BOS")
    assert object_to_dict(line) == {"k": "structure", "t": "line", "x1": 1, "y1": 2.0, "x2": 3, "y2": 4.0,
                                    "c": "#abc", "s": "dashed", "w": 2, "tx": "BOS"}
    label = DrawLabel(kind=DrawKind.SKIP, x_ms=5, y=6.0, text="SKIP", color="#fff", style=LabelStyle.UP, above=False,
                      bg_color="#111", obj_id="s1", zone_uid=3)
    assert object_to_dict(label) == {"k": "skip", "t": "label", "x": 5, "y": 6.0, "tx": "SKIP", "c": "#fff",
                                     "ab": False, "s": "up", "bg": "#111", "z": 3}
    bg = DrawBg(kind=DrawKind.SESSION, x1_ms=0, x2_ms=10, color="#eee", obj_id="bg1.0", text="Session 1")
    assert object_to_dict(bg) == {"k": "session", "t": "bg", "x1": 0, "x2": 10, "c": "#eee", "tx": "Session 1"}


def test_merge_backgrounds_joins_adjacent_bands_of_same_colour_only():
    bands = [
        DrawBg(DrawKind.SESSION, 0, 100, "#aaa", "bg1.0", "Session 1"),
        DrawBg(DrawKind.SESSION, 100, 200, "#aaa", "bg1.100", "Session 1"),
        DrawBg(DrawKind.SESSION, 100, 200, "#bbb", "bg2.100", "Session 2"),  # iná seansa, prekrýva sa
        DrawBg(DrawKind.SESSION, 200, 300, "#aaa", "bg1.200", "Session 1"),
        DrawBg(DrawKind.SESSION, 500, 600, "#aaa", "bg1.500", "Session 1"),  # medzera → nový pás
    ]
    box = DrawBox(kind=DrawKind.TP_BOX, x1_ms=0, y1=1.0, x2_ms=1, y2=0.0, border_color="#000", obj_id="a")
    out = merge_backgrounds([bands[0], box, *bands[1:]])
    assert [(o.x1_ms, o.x2_ms, o.color) for o in out if isinstance(o, DrawBg)] == [
        (0, 300, "#aaa"), (100, 200, "#bbb"), (500, 600, "#aaa"),
    ]
    assert out[1] is box  # ostatné objekty prechádzajú nezmenené a v poradí
    assert len(objects_to_dicts(bands)) == 3


# --------------------------------------------------------------------------- #
# EngineRunner → export
# --------------------------------------------------------------------------- #


def _runner() -> EngineRunner:
    cfg = IBSConfig(sess1On=True, sess1TZ="UTC", weekdaysOnly=False,
                    sess1ZoneStartH=0, sess1ZoneEndH=23, sess1TradeStartH=0, sess1TradeEndH=23)
    return EngineRunner(cfg, MNQ, chart_tf_minutes=3)


def test_runner_collects_drawings_and_export_writes_gzip(tmp_path: Path):
    runner = _runner()
    for i in range(30):
        runner.process(Bar(time=T0 + i * MIN3, open=100.0, high=101.0, low=99.0, close=100.5, volume=100.0), None)
    assert len(runner.registry) > 0  # seansa beží celý deň → pás pozadia na každom bare

    out = tmp_path / "c.json.gz"
    head = export_chart(runner, "BTC/USDT:USDT", "3m", out)
    with gzip.open(out, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["pair"] == "BTC/USDT:USDT" and data["timeframe"] == "3m"
    assert data["from_ms"] == T0 and data["to_ms"] == T0 + 29 * MIN3 and data["bars"] == 30
    bands = [o for o in data["objects"] if o["t"] == "bg"]
    assert len(bands) == 1 and bands[0]["x1"] == T0 and bands[0]["x2"] == T0 + 30 * MIN3
    assert head["counts"]["session"] == 1 and "objects" not in head


def test_export_without_gz_suffix_writes_plain_json(tmp_path: Path):
    runner = _runner()
    runner.process(Bar(time=T0, open=100.0, high=101.0, low=99.0, close=100.5, volume=100.0), None)
    out = tmp_path / "c.json"
    export_chart(runner, "X", "3m", out)
    assert json.loads(out.read_text(encoding="utf-8"))["bars"] == 1


# --------------------------------------------------------------------------- #
# webapp.chart
# --------------------------------------------------------------------------- #


def test_window_keeps_objects_touching_the_range():
    chart = {"objects": [
        {"t": "box", "k": "sd_zone_post", "x1": 0, "x2": 100},
        {"t": "box", "k": "sd_zone_post", "x1": 150, "x2": 160},
        {"t": "box", "k": "sr_level", "x1": 0, "x2": 10, "er": True},  # extend.right → siaha až po koniec okna
        {"t": "label", "k": "skip", "x": 120},
        {"t": "label", "k": "skip", "x": 300},
        {"t": "line", "k": "structure", "x1": 90, "x2": 250},
    ]}
    got = chart_mod.window(chart, 110, 200)
    assert [o.get("x", o.get("x1")) for o in got] == [150, 0, 120, 90]
    assert chart_mod.summary({"pair": "X", "objects": [1, 2]}) == {"pair": "X"}


def test_pair_file_uses_freqtrade_naming():
    assert chart_mod.pair_file("BTC/USDT:USDT", "3m").name == "BTC_USDT_USDT-3m-futures.feather"
    with pytest.raises(ValueError):
        chart_mod.pair_file("BTC/USDT:USDT", "2m")


@pytest.fixture
def fake_data(tmp_path: Path, monkeypatch):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    n = 20
    df = pd.DataFrame({
        "date": pd.to_datetime([T0 + i * MIN3 for i in range(n)], unit="ms", utc=True),
        "open": [100.0 + i for i in range(n)], "high": [101.0 + i for i in range(n)],
        "low": [99.0 + i for i in range(n)], "close": [100.5 + i for i in range(n)], "volume": [1.0] * n,
    })
    df.to_feather(tmp_path / "BTC_USDT_USDT-3m-futures.feather")
    monkeypatch.setattr(chart_mod, "DATA_DIR", tmp_path)
    chart_mod._frame.cache_clear()
    return tmp_path


def test_candles_window_and_truncation(fake_data):
    c = chart_mod.candles("BTC/USDT:USDT", "3m", T0 + 2 * MIN3, T0 + 6 * MIN3)
    assert c["t"] == [T0 + 2 * MIN3, T0 + 3 * MIN3, T0 + 4 * MIN3, T0 + 5 * MIN3]
    assert c["o"] == [102.0, 103.0, 104.0, 105.0] and c["truncated"] is False
    assert c["from_ms"] == T0 + 2 * MIN3 and c["to_ms"] == T0 + 5 * MIN3

    t = chart_mod.candles("BTC/USDT:USDT", "3m", T0, T0 + 20 * MIN3, limit=3)
    assert t["truncated"] is True and t["t"] == [T0, T0 + MIN3, T0 + 2 * MIN3]

    empty = chart_mod.candles("BTC/USDT:USDT", "3m", T0 + 100 * MIN3, T0 + 101 * MIN3)
    assert empty["t"] == [] and empty["truncated"] is False
    assert chart_mod.available_timeframes("BTC/USDT:USDT") == ["3m"]
    with pytest.raises(FileNotFoundError):
        chart_mod.candles("ETH/USDT:USDT", "3m", T0, T0 + MIN3)


# --------------------------------------------------------------------------- #
# store + API
# --------------------------------------------------------------------------- #


def _record(run_id: str) -> dict:
    return {
        "id": run_id, "status": "done", "created": "2026-09-05T10:00:00+00:00", "user": "t", "note": "",
        "settings": {"pair": "BTC/USDT:USDT", "timerange": "20250901-20250902", "fee": 0.0005, "wallet": 10000, "profile": None},
        "params": IBSConfig().to_dict(), "result": {"trades": 0}, "series": {"equity": [], "market": []},
    }


def _write_chart(path: Path, objects: list[dict]) -> Path:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"version": 1, "pair": "BTC/USDT:USDT", "timeframe": "3m", "from_ms": 0, "to_ms": 1000,
                   "bars": 5, "counts": {"sd_zone_post": len(objects)}, "objects": objects}, fh)
    return path


def test_store_moves_chart_file_into_run_dir(tmp_path: Path):
    store = RunStore(tmp_path / "runs")
    tmp = _write_chart(tmp_path / "tmp.chart.json.gz", [{"t": "box", "k": "sd_zone_post", "x1": 0, "x2": 10}])
    d = store.save(_record("20260905-120000-aaaaaa"), trades=[], log="", chart_path=tmp)
    assert (d / CHART_FILE).exists() and not tmp.exists()
    assert store.has_chart("20260905-120000-aaaaaa")
    assert store.chart("20260905-120000-aaaaaa")["counts"] == {"sd_zone_post": 1}
    # chýbajúci súbor (staršia stratégia) nie je chyba
    store.save(_record("20260905-120001-bbbbbb"), chart_path=tmp_path / "nie.gz")
    assert not store.has_chart("20260905-120001-bbbbbb") and store.chart("20260905-120001-bbbbbb") is None


@pytest.fixture
def client(tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from ibs.webapp.app import create_app
    from ibs.webapp.runner import BacktestRunner

    store = RunStore(tmp_path / "runs")
    runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
    return TestClient(create_app(store, runner)), store, tmp_path


def test_chart_endpoint_filters_by_window(client):
    c, store, tmp_path = client
    objs = [
        {"t": "box", "k": "sd_zone_post", "x1": 0, "y1": 2.0, "x2": 100, "y2": 1.0, "bc": "#000"},
        {"t": "label", "k": "skip", "x": 500, "y": 1.0, "tx": "SKIP", "c": "#000", "ab": True},
    ]
    store.save(_record("20260905-120000-aaaaaa"), trades=[], log="", chart_path=_write_chart(tmp_path / "c.gz", objs))
    store.save(_record("20260905-120001-bbbbbb"), trades=[], log="")

    det = c.get("/api/runs/20260905-120000-aaaaaa").json()
    assert det["record"]["has_chart"] is True
    assert c.get("/api/runs/20260905-120001-bbbbbb").json()["record"]["has_chart"] is False

    r = c.get("/api/runs/20260905-120000-aaaaaa/chart", params={"from": 400, "to": 600}).json()
    assert [o["k"] for o in r["objects"]] == ["skip"] and r["meta"]["counts"] == {"sd_zone_post": 2}
    assert len(c.get("/api/runs/20260905-120000-aaaaaa/chart").json()["objects"]) == 2
    assert c.get("/api/runs/20260905-120001-bbbbbb/chart").status_code == 404
    assert c.get("/api/runs/20260905-120002-cccccc/chart").status_code == 404


def test_candles_endpoint(client, fake_data):
    c, _, _ = client
    r = c.get("/api/candles", params={"pair": "BTC/USDT:USDT", "tf": "3m", "from": T0, "to": T0 + 3 * MIN3})
    assert r.status_code == 200 and r.json()["c"] == [100.5, 101.5, 102.5]
    assert c.get("/api/candles", params={"pair": "BTC/USDT:USDT", "tf": "3m", "from": T0, "to": T0}).status_code == 422
    assert c.get("/api/candles", params={"pair": "BTC/USDT:USDT", "tf": "2m", "from": T0, "to": T0 + 1}).status_code == 422
    assert c.get("/api/candles", params={"pair": "ETH/USDT:USDT", "tf": "3m", "from": T0, "to": T0 + 1}).status_code == 404
