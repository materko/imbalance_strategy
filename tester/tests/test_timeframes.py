"""Odvodzovanie vyšších timeframov z 1m — `tester.timeframes`.

Dve veci, na ktorých to stojí: že sa **nič stiahnuté neprepíše** a že sa odvodené
súbory **nedostanú do archívu** — v gite majú byť len dáta z burzy a z raw exportov.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from tradebot.core.candles import resample_ohlcv
from tester import data_archive as da
from tester import timeframes as tf


def m1(n: int, start: str = "2025-01-06 00:00") -> pd.DataFrame:
    """`n` minútových sviečok od pondelka 00:00 UTC."""
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({
        "date": idx,
        "open": [100.0 + i for i in range(n)],
        "high": [101.0 + i for i in range(n)],
        "low": [99.0 + i for i in range(n)],
        "close": [100.5 + i for i in range(n)],
        "volume": [1.0] * n,
    })


@pytest.fixture
def sklad(tmp_path: Path) -> Path:
    """Sklad sviečok s jedným futures a jedným spot 1m súborom."""
    (tmp_path / "binance" / "futures").mkdir(parents=True)
    (tmp_path / "binance" / "spot").mkdir(parents=True)
    m1(600).to_feather(tmp_path / "binance" / "futures" / "BTC_USDT_USDT-1m-futures.feather")
    m1(600).to_feather(tmp_path / "binance" / "spot" / "BTC_USDT-1m.feather")
    return tmp_path


@pytest.fixture
def config(tmp_path: Path) -> Path:
    p = tmp_path / "tf.json"
    p.write_text(json.dumps({"derive": ["2m", "5m", "1h"]}), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# konfigurácia
# --------------------------------------------------------------------------- #


def test_config_je_zdrojom_zoznamu(config):
    assert tf.wanted(config) == ("2m", "5m", "1h")


def test_zdrojovy_1m_sa_neodvodzuje(tmp_path):
    p = tmp_path / "tf.json"
    p.write_text(json.dumps({"derive": ["1m", "3m"]}), encoding="utf-8")
    assert tf.wanted(p) == ("3m",)


def test_pokazeny_config_nezhodi_webapp(tmp_path):
    p = tmp_path / "tf.json"
    p.write_text("{ toto nie je JSON", encoding="utf-8")
    assert tf.wanted(p) == tf.FALLBACK
    assert tf.wanted(tmp_path / "neexistuje.json") == tf.FALLBACK


@pytest.mark.parametrize("text,mins", [("2m", 2), ("30m", 30), ("1h", 60), ("4h", 240),
                                       ("1d", 1440), ("1w", 10080)])
def test_prevod_na_minuty(text, mins):
    assert tf.minutes(text) == mins


def test_neznamy_timeframe_sa_ohlasi():
    for bad in ("15", "1y", "abc", ""):
        with pytest.raises(ValueError):
            tf.minutes(bad)


def test_realny_config_ma_vsetky_timeframy_prevoditelne():
    """Preklep v `timeframes.json` sa má ukázať tu, nie až pri štarte webapp."""
    assert tf.wanted()
    for name in tf.wanted():
        assert tf.minutes(name) > 1


# --------------------------------------------------------------------------- #
# odvodenie
# --------------------------------------------------------------------------- #


def test_najde_1m_sviecky_a_nie_funding_ani_mark(sklad):
    (sklad / "binance" / "futures" / "BTC_USDT_USDT-1h-funding_rate.feather").touch()
    (sklad / "binance" / "futures" / "BTC_USDT_USDT-1h-mark.feather").touch()
    assert [p.name for p in tf.sources(sklad)] == [
        "BTC_USDT_USDT-1m-futures.feather", "BTC_USDT-1m.feather"]


def test_prípona_futures_ostane_v_mene(sklad, config):
    made = tf.ensure(sklad, config, verbose=False, manifest=sklad / ".derived.json")
    names = sorted(p.name for p in made)
    assert names == ["BTC_USDT-1h.feather", "BTC_USDT-2m.feather", "BTC_USDT-5m.feather",
                     "BTC_USDT_USDT-1h-futures.feather", "BTC_USDT_USDT-2m-futures.feather",
                     "BTC_USDT_USDT-5m-futures.feather"]


def test_bary_su_tie_iste_ako_v_grafe_a_emulatore(sklad, config):
    """Keby sa pravidlo rozišlo, porovnanie platforiem by prestalo niečo znamenať."""
    tf.ensure(sklad, config, verbose=False, manifest=sklad / ".derived.json")
    out = pd.read_feather(sklad / "binance" / "spot" / "BTC_USDT-5m.feather")
    assert out.equals(resample_ohlcv(m1(600), 5))


def test_stiahnuty_timeframe_sa_neprepise(sklad, config):
    cudzi = sklad / "binance" / "spot" / "BTC_USDT-5m.feather"
    m1(3).to_feather(cudzi)                      # „z burzy" — iný obsah než odvodený
    made = tf.ensure(sklad, config, verbose=False, manifest=sklad / ".derived.json")

    assert cudzi not in made
    assert len(pd.read_feather(cudzi)) == 3


def test_force_prepise_aj_existujuce(sklad, config):
    cudzi = sklad / "binance" / "spot" / "BTC_USDT-5m.feather"
    m1(3).to_feather(cudzi)
    tf.ensure(sklad, config, force=True, verbose=False, manifest=sklad / ".derived.json")
    assert len(pd.read_feather(cudzi)) == 120     # 600 minút / 5


def test_druhe_spustenie_uz_nic_nerobi(sklad, config):
    manifest = sklad / ".derived.json"
    assert tf.ensure(sklad, config, verbose=False, manifest=manifest)
    assert tf.ensure(sklad, config, verbose=False, manifest=manifest) == []
    assert tf.missing(sklad, config) == []


def test_bez_1m_sa_neodvodzuje_nic(tmp_path, config):
    assert tf.ensure(tmp_path, config, verbose=False) == []
    assert tf.missing(tmp_path, config) == []


def test_denne_bary_zacinaju_o_polnoci_a_tyzdenne_v_pondelok(sklad, tmp_path):
    """Týždeň od epochy by začínal vo štvrtok — burzy aj TradingView ho majú od pondelka."""
    config = tmp_path / "tf2.json"
    config.write_text(json.dumps({"derive": ["4h", "1d", "1w"]}), encoding="utf-8")
    tyzdne = m1(3 * 7 * 24 * 60, start="2025-01-01 00:00")     # streda, tri týždne
    tyzdne.to_feather(sklad / "binance" / "spot" / "BTC_USDT-1m.feather")
    tf.ensure(sklad, config, verbose=False, manifest=sklad / ".derived.json")

    den = pd.read_feather(sklad / "binance" / "spot" / "BTC_USDT-1d.feather")["date"]
    tyzden = pd.read_feather(sklad / "binance" / "spot" / "BTC_USDT-1w.feather")["date"]
    styri = pd.read_feather(sklad / "binance" / "spot" / "BTC_USDT-4h.feather")["date"]

    assert set(den.dt.hour) == {0}
    assert set(styri.dt.hour) == {0, 4, 8, 12, 16, 20}
    assert set(tyzden.dt.day_name()) == {"Monday"}
    assert set(tyzden.dt.hour) == {0}


# --------------------------------------------------------------------------- #
# manifest a archív
# --------------------------------------------------------------------------- #


def test_manifest_drzi_vyrobene_subory(sklad, config):
    manifest = sklad / ".derived.json"
    made = tf.ensure(sklad, config, verbose=False, manifest=manifest)
    assert sorted(tf.derived(manifest)) == sorted(made)
    rows = json.loads(manifest.read_text(encoding="utf-8"))["files"]
    assert "binance/spot/BTC_USDT-2m.feather" in rows


def test_manifest_ignoruje_subory_mimo_skladu(tmp_path):
    """`dukas_import --ft-datadir` môže písať kamkoľvek; `split` sa tam aj tak nepozrie."""
    manifest = tmp_path / "sklad" / ".derived.json"
    manifest.parent.mkdir()
    tf.remember([tmp_path / "inde" / "X-3m.feather"], manifest)
    assert tf.derived(manifest) == []


def test_split_odvodene_do_archivu_nedava(sklad, config, tmp_path, monkeypatch):
    """Toto je pointa: v gite má byť 1m z burzy, nie to, čo sa z neho dopočíta."""
    manifest = sklad / ".derived.json"
    tf.ensure(sklad, config, verbose=False, manifest=manifest)
    archive = tmp_path / "archive"
    monkeypatch.setattr(da, "ROOTS", ((archive, sklad),))

    da.split(verbose=False, skip=set(tf.derived(manifest)))

    archived = sorted(p.name for p in archive.rglob("*.feather"))
    assert archived == ["BTC_USDT-1m.2025.feather", "BTC_USDT_USDT-1m-futures.2025.feather"]


def test_split_bez_manifestu_archivuje_vsetko(sklad, tmp_path, monkeypatch):
    """Stiahnuté 3m z burzy nie je odvodené a do archívu patrí."""
    m1(30).to_feather(sklad / "binance" / "spot" / "BTC_USDT-3m.feather")
    archive = tmp_path / "archive"
    monkeypatch.setattr(da, "ROOTS", ((archive, sklad),))

    da.split(verbose=False, skip=set())

    assert (archive / "binance" / "spot" / "BTC_USDT-3m.2025.feather").exists()
