"""Rozdelenie príkazov na maker a taker.

Celý zmysel tohto merania stojí na jednej otázke: ležala limitka v knihe, alebo
prekročila spread? Ak sa strana pomýli, zmiešaný poplatok vyjde nižší, než aký by
burza reálne vzala, a stratégia bude vyzerať zisková bez toho, aby bola.
"""

from __future__ import annotations

import json
import zipfile

import pytest

pd = pytest.importorskip("pandas")

from tester import fees

#: Sviečka, na ktorej sa príkazy zadávajú — otvára na 100.
CHART = pd.DataFrame(
    {
        "date": pd.to_datetime(["2026-08-24 10:00", "2026-08-24 10:03"], utc=True),
        "open": [100.0, 100.0],
        "high": [101.0, 101.0],
        "low": [99.0, 99.0],
        "close": [100.5, 100.5],
        "volume": [1.0, 1.0],
    }
)


def _trade(rate, exit_reason="roi", short=False, close=None):
    return {
        "open_date": "2026-08-24 10:00:00+00:00",
        "close_date": "2026-08-24 10:03:00+00:00",
        "open_rate": rate,
        "close_rate": close if close is not None else rate + 10.0,
        "amount": 1.0,
        "profit_abs": 10.0,
        "exit_reason": exit_reason,
        "is_short": short,
        "fee_open": 0.0,
        "fee_close": 0.0,
        "funding_fees": 0.0,
    }


def _zip(tmp_path, trades):
    stats = {
        "trades": trades,
        "timeframe": "3m",
        "starting_balance": 10_000.0,
        "stake_currency": "USDT",
        "backtest_start": "2026-08-24 00:00:00",
        "backtest_end": "2026-08-25 00:00:00",
    }
    path = tmp_path / "backtest-result-2026-08-25_10-00-00.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "backtest-result-2026-08-25_10-00-00.json",
            json.dumps({"strategy": {"IBSImbalanceStrategy": stats}}),
        )
        z.writestr("backtest-result-2026-08-25_10-00-00_config.json", "{}")
    return path


@pytest.fixture(autouse=True)
def chart(monkeypatch):
    from tester.compare import scan_zones

    monkeypatch.setattr(scan_zones, "_load", lambda exchange, timeframe: CHART.copy())


def _classified(tmp_path, trades):
    stats, tr = fees.load(_zip(tmp_path, trades))
    return fees.classify(stats, tr)


def test_long_limitka_pod_trhom_je_maker(tmp_path):
    tr = _classified(tmp_path, [_trade(99.0)])
    assert bool(tr["entry_maker"].iloc[0]) is True


def test_long_limitka_nad_trhom_je_taker(tmp_path):
    """Prekročila by spread — burza ju vyplní okamžite, teda ako taker."""
    tr = _classified(tmp_path, [_trade(100.5)])
    assert bool(tr["entry_maker"].iloc[0]) is False


def test_short_ide_opacne(tmp_path):
    tr = _classified(tmp_path, [_trade(101.0, short=True), _trade(99.5, short=True)])
    assert list(tr["entry_maker"]) == [True, False]


def test_vystup_podla_dovodu(tmp_path):
    tr = _classified(
        tmp_path,
        [_trade(99.0, "roi"), _trade(99.0, "stop_loss"), _trade(99.0, "session_end")],
    )
    assert list(tr["exit_maker"]) == [True, False, False]


def test_neznamy_dovod_vystupu_je_taker(tmp_path):
    """Konzervatívne — radšej poplatok nadhodnotiť než podhodnotiť."""
    tr = _classified(tmp_path, [_trade(99.0, "force_exit")])
    assert bool(tr["exit_maker"].iloc[0]) is False


def test_poplatky_sa_pocitaju_kazdej_strane_zvlast(tmp_path):
    # vstup 99 (maker), vystup 109 (roi -> maker); pri 0,02 % je to 0,0416 USDT
    tr = _classified(tmp_path, [_trade(99.0, "roi")])
    s = fees.summarize(tr, maker=0.02, taker=0.05)
    assert s["fees"] == pytest.approx((99.0 + 109.0) * 0.0002)
    assert s["gross"] == pytest.approx(10.0)
    assert s["net"] == pytest.approx(10.0 - (99.0 + 109.0) * 0.0002)


def test_taker_vystup_stoji_viac_nez_maker(tmp_path):
    a = fees.summarize(_classified(tmp_path, [_trade(99.0, "roi")]))
    b = fees.summarize(_classified(tmp_path, [_trade(99.0, "stop_loss")]))
    assert b["fees"] > a["fees"]


def test_break_even_je_hruby_zisk_na_objem(tmp_path):
    tr = _classified(tmp_path, [_trade(99.0)])
    s = fees.summarize(tr)
    assert s["break_even"] == pytest.approx(10.0 / (99.0 + 109.0) * 100)


def test_short_zisk_ma_spravne_znamienko(tmp_path):
    """Short zarába, keď cena klesne — bez toho by hrubý zisk vyšiel opačne."""
    tr = _classified(tmp_path, [_trade(101.0, short=True, close=91.0)])
    assert fees.summarize(tr)["gross"] == pytest.approx(10.0)


# --------------------------------------------------------------------------- #
# Hĺbka prieniku za limitku
# --------------------------------------------------------------------------- #


@pytest.fixture
def m1(monkeypatch):
    """1m sviečky: prvá sa limitky 99 len dotkne, druhá cez ňu prejde."""
    from tester.compare import scan_zones

    bars = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-08-24 10:00", "2026-08-24 10:01", "2026-08-24 10:02"], utc=True
            ),
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0],
            "low": [99.0, 95.0, 95.0],
            "close": [100.0, 100.0, 100.0],
            "volume": [1.0, 1.0, 1.0],
        }
    )
    real = scan_zones._load
    monkeypatch.setattr(
        scan_zones, "_load",
        lambda exchange, timeframe: bars.copy() if timeframe == "1m" else CHART.copy(),
    )
    return real


def test_dotyk_je_pochybne_vyplnenie(tmp_path, m1):
    """Prvá sviečka klesne presne na 99 — v knihe sa taký príkaz nemusí vyplniť."""
    stats, tr = fees.load(_zip(tmp_path, [_trade(99.0)]))
    tr = fees.fill_depth(fees.classify(stats, tr), inst_tick=0.1)
    assert tr["fill_depth"].iloc[0] == pytest.approx(0.0)
    assert bool(tr["fill_doubtful"].iloc[0]) is True


def test_hlboky_prienik_nie_je_pochybny(tmp_path, m1):
    """Limitka na 96: cena šla na 95, teda o 10 tickov nižšie — vyplní sa isto."""
    stats, tr = fees.load(_zip(tmp_path, [_trade(96.0)]))
    tr = fees.fill_depth(fees.classify(stats, tr), inst_tick=0.1)
    assert tr["fill_depth"].iloc[0] == pytest.approx(1.0)
    assert bool(tr["fill_doubtful"].iloc[0]) is False


def test_taker_vstup_nie_je_pochybny_nikdy(tmp_path, m1):
    """Taker sa vyplní prekročením spreadu — hĺbka prieniku ho netrápi."""
    stats, tr = fees.load(_zip(tmp_path, [_trade(100.5)]))
    tr = fees.fill_depth(fees.classify(stats, tr), inst_tick=0.1)
    assert bool(tr["fill_doubtful"].iloc[0]) is False


# --------------------------------------------------------------------------- #
# Koľko stojí strana obchodu na TOMTO trhu
# --------------------------------------------------------------------------- #
#
# Binance taker 0,05 % na CFD neplatí ani rádovo — provízia je tam drobná a náklad je
# spread. Jeden default pre všetky trhy urobí zo ziskového CFD stratový, takže tieto
# testy strážia, že sa číslo berie z inštrumentu a že je pri ňom vidieť, odkiaľ je.


def test_krypto_ma_naklad_v_percentach_z_objemu():
    from tradebot.core.types import INSTRUMENTS

    inst = INSTRUMENTS["btcusdt_binance"]

    assert inst.cost_unit == "pct"
    assert inst.cost_pct(60_000) == inst.cost_pct(20_000) == 0.05
    assert "Binance" in inst.cost_note


def test_cfd_ma_naklad_v_tickoch_a_zavisi_od_ceny():
    """Pevný posun ceny je na drahom trhu iné percento než na lacnom."""
    from tradebot.core.types import INSTRUMENTS

    inst = INSTRUMENTS["nas100_dukascopy"]

    assert inst.cost_unit == "ticks"
    assert inst.cost_pct(20_000) == pytest.approx(inst.cost * inst.tick_size / 20_000 * 100)
    assert inst.cost_pct(10_000) == pytest.approx(2 * inst.cost_pct(20_000))


def test_bez_ceny_je_naklad_nula_a_nie_vymyslene_cislo():
    from tradebot.core.types import INSTRUMENTS

    assert INSTRUMENTS["nas100_dukascopy"].cost_pct(0) == 0.0


def test_naklad_cfd_je_o_rady_nizsi_nez_krypto_sadzba():
    """Toto je celý dôvod, prečo je to per inštrument: rozdiel nie je v percentách,
    ale v rádoch. Break-even 0,03 % je proti 0,05 % strata a proti spreadu zisk."""
    from tradebot.core.types import INSTRUMENTS

    krypto = INSTRUMENTS["btcusdt_binance"].cost_pct(60_000)
    cfd = INSTRUMENTS["nas100_dukascopy"].cost_pct(20_000)

    assert cfd * 100 < krypto


def test_kazdy_symbol_registra_povie_odkial_ma_cislo():
    from tradebot.core.types import dukascopy_specs

    for key, inst in dukascopy_specs().items():
        assert inst.cost_note, key
        assert inst.cost > 0, key


def test_symbol_si_moze_naklad_prepisat(tmp_path):
    """Keď sa zistí skutočná hodnota od brokera, je to jeden riadok v registri."""
    import json

    from tradebot.core.types import dukascopy_specs

    src = tmp_path / "reg.json"
    src.write_text(json.dumps({
        "_comment": "test",
        "vlastny": {"symbol": "X/USD", "tick_size": 0.1, "point_value": 1.0,
                    "half_spread_ticks": 12, "cost_note": "od brokera, 2026-09"},
    }), encoding="utf-8")
    inst = dukascopy_specs(src)["vlastny"]

    assert inst.cost == 12
    assert inst.cost_note == "od brokera, 2026-09"


def test_neznamy_naklad_sa_neda_zamenit_s_nulovym():
    """`None` znamená „nevieme“ — a vtedy sa break-even proti ničomu neposudzuje."""
    hodnota, note = fees.for_pair("NIECO/NEEXISTUJE")

    assert hodnota is None
    assert "NIECO/NEEXISTUJE" in note


def test_zle_jednotky_nakladu_sa_nedaju_zadat():
    from tradebot.core.types import InstrumentSpec

    with pytest.raises(ValueError, match="cost_unit"):
        InstrumentSpec(symbol="X", venue="v", tick_size=1, point_value=1, qty_step=1,
                       min_qty=1, cost_unit="atr")
