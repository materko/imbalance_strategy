"""Syntetický trh — čo sa má zachovať a čo má zmiznúť.

Celý zmysel je, že sa zachová **rozdelenie výnosov a tvar barov**, ale zmizne **poradie**.
Keby sa nezachovalo prvé, dalo by sa namietnuť, že to nevyzerá ako trh; keby nezmizlo
druhé, nebola by to kontrola ničoho. A trh musí byť **pevný** — inak sa dva výsledky
nedajú porovnať.
"""

from __future__ import annotations

import json

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

from tester import synthetic as sy


def bary(n: int = 600, seed: int = 1):
    """Bary s trendom a zhlukmi volatility — teda so štruktúrou, ktorá má zmiznúť."""
    rng = np.random.default_rng(seed)
    vol = np.repeat(rng.choice([0.0005, 0.004], size=-(-n // 20)), 20)[:n]
    r = rng.normal(0.00002, 1.0, size=n) * vol
    close = 100.0 * np.exp(np.cumsum(r))
    telo = np.abs(rng.normal(0, 0.0006, size=n)) * close
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC"),
        "open": close * (1 + rng.normal(0, 0.0002, size=n)),
        "high": close + telo,
        "low": close - telo,
        "close": close,
        "volume": rng.random(n),
    })


# --------------------------------------------------------------------------- #
# čo sa zachová
# --------------------------------------------------------------------------- #


def test_rozdelenie_vynosov_ostane_presne_rovnake():
    """Toto je odpoveď na „tvoja náhodná prechádzka nevyzerá ako trh“."""
    zdroj = bary()
    novy = sy.shuffle_bars(zdroj, block=20, seed=7)

    a = np.diff(np.log(zdroj["close"].to_numpy()))
    b = np.diff(np.log(novy["close"].to_numpy()))
    assert np.allclose(np.sort(a), np.sort(b))


def test_celkovy_drift_je_z_konstrukcie_ten_isty():
    """Súčet výnosov sa premiešaním nemení, takže trh končí na tej istej cene.

    Je to dôležité pre férovosť: stratégia s dlhým biasom nie je na syntetickom trhu
    trestaná tým, že by tam trh nerástol.
    """
    zdroj = bary()
    novy = sy.shuffle_bars(zdroj, block=20, seed=7)

    assert novy["close"].iloc[-1] == pytest.approx(zdroj["close"].iloc[-1], rel=1e-6)


def test_bary_ostanu_koherentne():
    """Bar, kde high nie je najvyššie, by rozbil každý fill model."""
    novy = sy.shuffle_bars(bary(), block=20, seed=7)

    assert (novy["high"] >= novy[["open", "close"]].max(axis=1)).all()
    assert (novy["low"] <= novy[["open", "close"]].min(axis=1)).all()


def test_casova_os_a_pocet_barov_ostanu():
    zdroj = bary()
    novy = sy.shuffle_bars(zdroj, block=20, seed=7)

    assert len(novy) == len(zdroj)
    assert (novy["date"].to_numpy() == zdroj["date"].to_numpy()).all()


# --------------------------------------------------------------------------- #
# čo zmizne
# --------------------------------------------------------------------------- #


def test_poradie_zmizne():
    zdroj = bary()
    novy = sy.shuffle_bars(zdroj, block=20, seed=7)

    assert not np.allclose(zdroj["close"].to_numpy(), novy["close"].to_numpy())


def test_blok_drzi_zhluky_volatility_pokope():
    """Bez blokov by trh vyzeral neprirodzene hladko — volatilita by sa rozpustila."""
    zdroj = bary()
    zhluk = lambda df: pd.Series(np.abs(np.diff(np.log(df["close"].to_numpy())))).autocorr(1)

    velky = zhluk(sy.shuffle_bars(zdroj, block=60, seed=7))
    ziadny = zhluk(sy.shuffle_bars(zdroj, block=1, seed=7))

    assert velky > ziadny


# --------------------------------------------------------------------------- #
# pevnosť
# --------------------------------------------------------------------------- #


def test_ten_isty_seed_da_ten_isty_trh():
    zdroj = bary()
    a = sy.shuffle_bars(zdroj, block=20, seed=7)
    b = sy.shuffle_bars(zdroj, block=20, seed=7)

    assert np.array_equal(a["close"].to_numpy(), b["close"].to_numpy())


def test_iny_seed_da_iny_trh():
    zdroj = bary()
    a = sy.shuffle_bars(zdroj, block=20, seed=7)
    b = sy.shuffle_bars(zdroj, block=20, seed=8)

    assert not np.array_equal(a["close"].to_numpy(), b["close"].to_numpy())


def test_kratky_rad_sa_premiesat_neda():
    with pytest.raises(ValueError, match="aspoň"):
        sy.shuffle_bars(bary(30), block=20)


# --------------------------------------------------------------------------- #
# register a data
# --------------------------------------------------------------------------- #


def test_recept_sa_ulozi_a_precita(tmp_path, monkeypatch):
    reg = tmp_path / "reg.json"
    zdroj = bary(2000)
    monkeypatch.setattr(sy, "_source_frame", lambda *a, **k: zdroj)
    monkeypatch.setattr(sy, "_write_recipe", sy._write_recipe)

    r = sy.build("t", like="btcusdt_binance", block=20, seed=3, registry=reg)

    assert r.seed == 3 and r.block == 20
    assert sy.recipes(reg)["t"].sha256 == r.sha256
    assert json.loads(reg.read_text(encoding="utf-8"))["t"]["like"] == "btcusdt_binance"


def test_existujuci_trh_sa_neprepise_bez_force(tmp_path, monkeypatch):
    """Prepísanie znamená, že skoršie behy na ňom prestanú byť porovnateľné."""
    reg = tmp_path / "reg.json"
    monkeypatch.setattr(sy, "_source_frame", lambda *a, **k: bary(2000))
    sy.build("t", like="btcusdt_binance", block=20, registry=reg)

    with pytest.raises(ValueError, match="--force"):
        sy.build("t", like="btcusdt_binance", block=20, registry=reg)

    sy.build("t", like="btcusdt_binance", block=20, seed=99, registry=reg, force=True)
    assert sy.recipes(reg)["t"].seed == 99


def test_ten_isty_recept_da_bit_po_bite_ten_isty_trh(tmp_path, monkeypatch):
    """Toto je dôvod, prečo sa dáta necommitujú — recept stačí."""
    monkeypatch.setattr(sy, "_source_frame", lambda *a, **k: bary(2000))
    prvy = sy.build("t", like="btcusdt_binance", block=20, seed=5,
                    registry=tmp_path / "a.json")
    druhy = sy.build("t", like="btcusdt_binance", block=20, seed=5,
                     registry=tmp_path / "b.json", force=True)

    assert prvy.sha256 == druhy.sha256


def test_instrument_dedi_mierku_zo_zdroja():
    """Prahy v bodoch platia na syntetickom trhu rovnako ako na zdroji — inak by bolo
    varovanie „profil je pre iný nástroj“ falošné."""
    from tradebot.core.types import INSTRUMENTS

    synth = INSTRUMENTS.get("synth")
    if synth is None:
        pytest.skip("syntetický trh nie je vygenerovaný")
    vzor = INSTRUMENTS[synth.scale_of]

    assert synth.scale_of == "btcusdt_binance"
    assert (synth.tick_size, synth.point_value) == (vzor.tick_size, vzor.point_value)
    assert not synth.has_real_volume        # objem je premiesany, nie obchodovany


def test_synteticke_data_do_archivu_nejdu():
    """Deterministické a veľké — z receptu vzniknú znova, tak ich netreba niesť v gite."""
    from tester import data_archive

    assert data_archive.SYNTHETIC_SOURCE == "synthetic"
