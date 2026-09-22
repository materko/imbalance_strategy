"""ORB: dĺžka opening rangu je voľné číslo 1–60 minút, nie tri pevné voľby.

Kedysi to bol enum `RangeLength` s hodnotami 15/30/60. Testuje sa tu troje: že config
pustí celý rozsah a odmietne, čo je mimo neho; že staré profily a behy, ktoré hodnotu
nesú ako reťazec ("15"), sa stále načítajú; a že engine naozaj postaví range tej dĺžky.

Osobitne sa testuje zaokrúhlenie na sviečku grafu — range sa uzatvára na hranici baru,
takže na 30m grafe dá 1 aj 15 ten istý 30-minútový range. Nie je to chyba, ale je to
presne to miesto, kde by si používateľ myslel, že meria niečo iné.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tradebot.core import BTCUSDT_BINANCE, Bar, MarketContext
from tradebot.core.config import ConfigError
from tradebot.strategies.orb import ORBConfig, ORBEngine, SessionMode

NY = ZoneInfo("America/New_York")
#: utorok 2025-09-02, 9:30 New York — `weekdaysOnly` je default, víkend by testy vypol
OPEN_MS = int(datetime(2025, 9, 2, 9, 30, tzinfo=NY).timestamp() * 1000)
MIN = 60_000
OKNO = MarketContext(in_trade_window=True)


def bar(ts: int, o=100.0, h=100.2, low=99.8, c=100.0, v=10.0) -> Bar:
    return Bar(time=ts, open=o, high=h, low=low, close=c, volume=v)


# ---- config ----------------------------------------------------------- #


@pytest.mark.parametrize("minutes", [1, 2, 3, 5, 7, 15, 30, 45, 60])
def test_cela_skala_1_az_60_prejde(minutes):
    cfg = ORBConfig(nyRangeMinutes=minutes, lonRangeMinutes=minutes)
    ny, london = cfg.sessions
    assert ny.range_minutes == minutes
    assert london.range_minutes == minutes
    assert ny.range_end_minutes == ny.start_minutes + minutes


@pytest.mark.parametrize("minutes", [0, -5, 61, 120])
def test_mimo_rozsahu_config_odmietne(minutes):
    with pytest.raises(ConfigError, match="nyRangeMinutes"):
        ORBConfig(nyRangeMinutes=minutes)


def test_stary_profil_s_retazcom_sa_nacita():
    """Profily v `tester/profiles/` nesú "15"/"30"/"60" z čias, keď to bol enum."""
    cfg = ORBConfig.from_dict({"nyRangeMinutes": "30", "lonRangeMinutes": "60"})
    assert (cfg.nyRangeMinutes, cfg.lonRangeMinutes) == (30, 60)
    assert cfg.sessions[0].range_minutes == 30


def test_do_profilu_sa_zapise_cislo():
    assert ORBConfig(nyRangeMinutes=7).to_dict()["nyRangeMinutes"] == 7


def test_range_dlhsi_nez_seansa_je_chyba():
    """Range musí skončiť pred koncom seansy, inak by na obchodovanie nezostal čas."""
    with pytest.raises(ConfigError, match="opening range"):
        ORBConfig(nyStartH=15, nyStartM=30, nyEndH=16, nyEndM=0, nyRangeMinutes=60,
                  sessionMode=SessionMode.NY)


# ---- formulár webapp -------------------------------------------------- #


def test_formular_ponuka_cislo_od_1_do_60_nie_tri_volby():
    from tester.webapp.param_meta import param_metadata
    from tradebot.strategies import STRATEGIES

    meta = {m["name"]: m for m in param_metadata(STRATEGIES["orb"])}
    for name in ("nyRangeMinutes", "lonRangeMinutes"):
        m = meta[name]
        assert m["type"] == "int", f"{name} má byť číslo, je {m['type']}"
        assert (m["min"], m["max"]) == (1, 60)
        assert not m.get("options"), f"{name} nemá mať zoznam volieb: {m.get('options')}"


# ---- engine ----------------------------------------------------------- #


def _range_of(minutes: int, chart_tf: int) -> tuple[float, float]:
    """Postaví seansu na 1-minútových krokoch a vráti high/low rangu, ktorý engine uzavrel."""
    cfg = ORBConfig(sessionMode=SessionMode.NY, nyRangeMinutes=minutes, showRange=False,
                    showLevels=False)
    engine = ORBEngine(cfg, BTCUSDT_BINANCE, chart_tf)
    step = chart_tf * MIN
    for i in range(engine.required_history, 0, -1):
        engine.on_bar(bar(OPEN_MS - i * step), None, OKNO)
    # každý ďalší bar seansy má vyššie high a nižšie low, nech je vidieť, kde range skončil
    for n in range(0, 60 // chart_tf):
        ts = OPEN_MS + n * step
        engine.on_bar(bar(ts, h=100.0 + n + 1, low=100.0 - n - 1), None, OKNO)
    st = engine._state["ny"]
    return st.high, st.low


@pytest.mark.parametrize("minutes,bars", [(1, 1), (2, 2), (3, 3), (5, 5), (15, 15), (60, 60)])
def test_na_1m_grafe_range_zoberie_presne_tolko_barov(minutes, bars):
    hi, lo = _range_of(minutes, chart_tf=1)
    assert (hi, lo) == (100.0 + bars, 100.0 - bars)


def test_kratky_range_na_dlhom_grafe_sa_zaokruhli_na_sviecku():
    """Na 30m grafe je 1 aj 15 minút ten istý jeden 30-minútový bar — zámerne a zdokumentovane."""
    assert _range_of(1, chart_tf=30) == _range_of(15, chart_tf=30) == (101.0, 99.0)
    # na 5m grafe už tie isté hodnoty dajú iný range
    assert _range_of(1, chart_tf=5) != _range_of(15, chart_tf=5)
