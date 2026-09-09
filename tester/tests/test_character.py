"""Charakter stratégie — zaradenie musí byť odvoditeľné z čísel, nie z názvu.

Testy stavajú obchody s vlastnosťami každého typu a kontrolujú, že sa zaradia tam, kam
patria. Podstatné je, že rozhoduje **pohyb pred vstupom**: winrate aj payoff sa dajú
nastaviť aj proti charakteru (stačí posunúť TP), smer vstupu voči predchádzajúcemu pohybu
nie — a práve tie dve veci sa v praxi zamieňajú.
"""

from __future__ import annotations

import pytest

from tester import character as ch


def trade(*, profit=1.0, duration=60, minute=0, hour=10, day=4, short=False,
          exit_reason="roi", open_rate=100.0):
    """Obchod v tvare, aký ukladá Freqtrade; `profit` je v mene aj ako podiel."""
    close = open_rate + profit * (-1 if short else 1)
    return {
        "open_date": f"2025-09-{day:02d}T{hour:02d}:{minute:02d}:00+00:00",
        "close_date": f"2025-09-{day:02d}T{hour:02d}:{minute:02d}:00+00:00",
        "open_rate": open_rate, "close_rate": close, "amount": 1.0,
        "profit_abs": profit, "profit_ratio": profit / open_rate,
        "is_short": short, "exit_reason": exit_reason, "trade_duration": duration,
        "max_rate": max(open_rate, close), "min_rate": min(open_rate, close),
        "enter_tag": "x:1",
    }


def sada(*, wins, losses, win=3.0, loss=1.0, duration=60, exit_reason="roi"):
    """`wins` ziskových a `losses` stratových obchodov s danou veľkosťou."""
    return ([trade(profit=win, duration=duration, exit_reason=exit_reason, day=1 + i % 28)
             for i in range(wins)]
            + [trade(profit=-loss, duration=duration, exit_reason="stop_loss", day=1 + i % 28)
               for i in range(losses)])


def zmeraj(trades, pohyb=None, timeframe="3m"):
    """Zmeria bez sviečok; `pohyb` dodá pohyb pred vstupom priamo (ako z dát)."""
    c = ch.measure(trades, pair="", timeframe=timeframe)
    if pohyb is not None:
        c.pre_entry_atr = pohyb
        c.momentum_share = 100.0 if pohyb > 0 else 0.0
        c = ch.classify(c)
    return c


# --------------------------------------------------------------------------- #
# čísla
# --------------------------------------------------------------------------- #


def test_payoff_je_priemerny_zisk_na_priemernu_stratu():
    c = zmeraj(sada(wins=30, losses=70, win=3.0, loss=1.0))
    assert c.winrate == pytest.approx(30.0)
    assert c.payoff == pytest.approx(3.0)


def test_sikmost_odlisi_malo_velkych_od_mnoha_malych():
    """Kladná šikmosť = málo veľkých ziskov (trend), záporná = občas rana (protitrend)."""
    trend = zmeraj(sada(wins=10, losses=90, win=20.0, loss=1.0))
    protitrend = zmeraj(sada(wins=90, losses=10, win=1.0, loss=20.0))
    assert trend.skew > 1
    assert protitrend.skew < -1


def test_median_drzania_je_v_baroch_grafu_nie_v_minutach():
    """90 minút je 30 barov na 3m grafe a 6 barov na 15m — bez toho sa typy nedajú porovnať."""
    assert zmeraj(sada(wins=10, losses=10, duration=90), timeframe="3m").median_bars == 30.0
    assert zmeraj(sada(wins=10, losses=10, duration=90), timeframe="15m").median_bars == 6.0


def test_zmes_vystupov_je_v_percentach():
    c = zmeraj(sada(wins=25, losses=75))
    assert c.exits["stop_loss"] == pytest.approx(75.0)
    assert c.exits["roi"] == pytest.approx(25.0)


def test_teplo_pred_ziskom_pocita_ako_daleko_obchod_znesie_proti_sebe():
    obchod = trade(profit=1.0)
    obchod["max_rate"] = 102.0     # MFE 2
    obchod["min_rate"] = 99.0      # MAE 1
    c = ch.measure([obchod] * 30, pair="", timeframe="3m")
    assert c.heat_ratio == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# zaradenie
# --------------------------------------------------------------------------- #


def test_pohyb_pred_vstupom_rozhoduje_medzi_prerazenim_a_protitrendom():
    """To isté rozdelenie výsledkov, iný smer vstupu — a iný typ. Toto je ten test."""
    obchody = sada(wins=30, losses=70, win=3.0, loss=1.0)
    assert zmeraj(obchody, pohyb=+1.0).archetype == "breakout"

    obchody = sada(wins=70, losses=30, win=1.0, loss=2.0)
    assert zmeraj(obchody, pohyb=-1.0).archetype == "reversion"


def test_trendova_sa_odlisi_od_prerazenia_dlzkou_drzania():
    """Oboje vstupuje po pohybe; rozdiel je, či berie prvý kus, alebo sedí celý pohyb."""
    kratke = zmeraj(sada(wins=25, losses=75, win=4.0, duration=150), pohyb=+1.0)
    dlhe = zmeraj(sada(wins=25, losses=75, win=4.0, duration=3000), pohyb=+1.0)
    assert kratke.archetype == "breakout"
    assert dlhe.archetype == "trend"


def test_scalping_sa_pozna_frekvenciou_a_kratkym_drzanim():
    obchody = [trade(profit=0.1 if i % 2 else -0.1, duration=6, day=1 + i // 20)
               for i in range(200)]
    c = zmeraj(obchody, pohyb=+0.1)
    assert c.archetype == "scalp"
    assert c.trades_per_day > 5


def test_bez_jasneho_pohybu_je_to_formacia():
    """Keď vstup nie je systematicky ani po pohybe, ani proti, je to formácia."""
    c = zmeraj(sada(wins=40, losses=60), pohyb=0.0)
    assert c.archetype == "pattern"


def test_malo_obchodov_znamena_slabu_istotu_a_ziadne_tvrdenie():
    c = zmeraj(sada(wins=5, losses=5), pohyb=+2.0)
    assert c.confidence == "slabá"
    assert "20" in c.evidence[0]


def test_bez_pohybu_pred_vstupom_je_istota_slaba():
    """Bez sviečok sa prerazenie a návrat rozlíšiť nedajú — nesmie to tvrdiť opak."""
    c = zmeraj(sada(wins=30, losses=70, win=3.0))
    assert c.confidence == "slabá"
    assert any("sviečky" in d for d in c.evidence)


# --------------------------------------------------------------------------- #
# rady k typu
# --------------------------------------------------------------------------- #


def test_kazdy_typ_ma_radu_co_je_normalne_na_co_pozor_a_co_ladit():
    """Label bez toho je na nič — rada je dôvod, prečo sa typ meria."""
    for a in ch.ARCHETYPES:
        assert a.title and a.signature and a.normal and a.watch and a.tune
        assert len(a.normal) > 30 and len(a.watch) > 30


def test_zaradenie_sa_vzdy_da_previest_na_vetu_s_dokazmi():
    c = zmeraj(sada(wins=30, losses=70, win=3.0), pohyb=+1.0)
    veta = ch.describe(c)
    assert "Prerazenie" in veta and "ATR" in veta
    assert ch.table(c).encode("ascii", "replace")     # konzola na Windows
