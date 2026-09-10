"""AI vrstva (FreqAI) — nálepka, filter a zmena parametrov podľa istoty.

Model sa tu netrénuje; testuje sa **to, čo okolo neho stojí**: či je nálepka správna, či
filter zahodí presne to, čo má, a či sa vypnutá vrstva neprejaví vôbec. Práve to posledné
je podstatné — parita s Pine platí len vtedy, keď vypnutá AI nemení nič.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")

from tradebot.adapters.freqtrade import ai


class Falosna(ai.AIMixin):
    """Stratégia len s tým, čo mixin potrebuje."""

    def __init__(self, config=None, runners=None):
        self.config = config or {}
        self._runners = runners or {}
        self.spec = type("S", (), {"key": "test"})()


def bary(n=40, cena=100.0):
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="3min", tz="UTC"),
        "open": cena, "high": cena + 1, "low": cena - 1, "close": cena,
        "volume": 1.0,
        "tb_enter_long": 0, "tb_enter_short": 0,
        "tb_entry": np.nan, "tb_sl": np.nan, "tb_tp": np.nan,
    })


# --------------------------------------------------------------------------- #
# nálepka
# --------------------------------------------------------------------------- #


def test_signal_ktory_dosiahol_tp_dostane_win():
    df = bary()
    df.loc[0, ["tb_enter_long", "tb_entry", "tb_sl", "tb_tp"]] = [1, 100.0, 95.0, 105.0]
    df.loc[5, "high"] = 106.0                      # TP prišiel na 5. bare

    out = Falosna().set_freqai_targets(df, {"pair": "X"})

    assert out[ai.TARGET][0] == ai.WIN


def test_signal_ktory_dosiahol_sl_dostane_loss():
    df = bary()
    df.loc[0, ["tb_enter_long", "tb_entry", "tb_sl", "tb_tp"]] = [1, 100.0, 95.0, 105.0]
    df.loc[3, "low"] = 94.0

    assert Falosna().set_freqai_targets(df, {"pair": "X"})[ai.TARGET][0] == ai.LOSS


def test_ked_pride_oboje_v_jednom_bare_rata_sa_stop():
    """V jednom bare nevieme, čo prišlo skôr. Optimistický odhad by model naučil, že
    sporné obchody vychádzajú — a to je presne tá chyba, ktorú robí každý zlý backtest."""
    df = bary()
    df.loc[0, ["tb_enter_long", "tb_entry", "tb_sl", "tb_tp"]] = [1, 100.0, 95.0, 105.0]
    df.loc[4, ["high", "low"]] = [106.0, 94.0]

    assert Falosna().set_freqai_targets(df, {"pair": "X"})[ai.TARGET][0] == ai.LOSS


def test_bar_bez_signalu_nema_nalepku():
    """FreqAI taký riadok z tréningu vyhodí — model sa učí len na tom, čo engine ponúkol."""
    out = Falosna().set_freqai_targets(bary(), {"pair": "X"})

    assert out[ai.TARGET].isna().all()


def test_signal_ktory_do_konca_okna_neskoncil_nema_nalepku():
    df = bary()
    df.loc[0, ["tb_enter_long", "tb_entry", "tb_sl", "tb_tp"]] = [1, 100.0, 95.0, 105.0]

    assert pd.isna(Falosna().set_freqai_targets(df, {"pair": "X"})[ai.TARGET][0])


def test_short_ma_nalepku_naopak():
    df = bary()
    df.loc[0, ["tb_enter_short", "tb_entry", "tb_sl", "tb_tp"]] = [1, 100.0, 105.0, 95.0]
    df.loc[6, "low"] = 94.0                        # short TP je dole

    assert Falosna().set_freqai_targets(df, {"pair": "X"})[ai.TARGET][0] == ai.WIN


# --------------------------------------------------------------------------- #
# filter
# --------------------------------------------------------------------------- #


def so_signalmi(pravdepodobnosti, do_predict=1):
    df = bary(len(pravdepodobnosti))
    df["tb_enter_long"] = 1
    df[ai.PREDICTION_COL] = pravdepodobnosti
    df["do_predict"] = do_predict
    return df


def test_vypnuta_vrstva_nemeni_nic():
    """Toto je podmienka parity s Pine: bez zapnutej AI musí byť beh presne ten istý."""
    df = so_signalmi([0.1, 0.2, 0.9])
    out, pocet = Falosna(config={}).ai_gate(df, "X")

    assert pocet == 0
    assert (out["tb_enter_long"] == 1).all()


def test_signaly_pod_prahom_sa_zahodia():
    df = so_signalmi([0.10, 0.60, 0.54, 0.99])
    s = Falosna(config={"tradebot_ai": {"min_probability": 0.55}})
    out, pocet = s.ai_gate(df, "X")

    assert pocet == 2
    assert list(out["tb_enter_long"]) == [0, 1, 0, 1]


def test_model_ktory_nevie_nevetuje():
    """`do_predict = 0` znamená, že model si nie je istý dátami — nie že signál je zlý."""
    df = so_signalmi([0.1, 0.1, 0.1], do_predict=0)
    out, pocet = Falosna(config={"tradebot_ai": {"min_probability": 0.55}}).ai_gate(df, "X")

    assert pocet == 0


def test_bez_predikcie_sa_nefiltruje():
    df = bary(5)
    df["tb_enter_long"] = 1
    out, pocet = Falosna(config={"tradebot_ai": {"min_probability": 0.55}}).ai_gate(df, "X")

    assert pocet == 0


# --------------------------------------------------------------------------- #
# zmena parametrov podľa istoty
# --------------------------------------------------------------------------- #


def test_bez_nastaveneho_rozsahu_sa_nic_neskaluje():
    s = Falosna(config={"tradebot_ai": {"min_probability": 0.5}})
    s._ai_predictions = {"X": {1: 0.9}}

    assert s.ai_scale("X", 1, "size") == 1.0


def test_istota_na_prahu_da_dolny_koniec_a_jednotka_horny():
    s = Falosna(config={"tradebot_ai": {"min_probability": 0.5,
                                        "adjust": {"size": [0.5, 1.5]}}})
    s._ai_predictions = {"X": {1: 0.5, 2: 1.0, 3: 0.75}}

    assert s.ai_scale("X", 1, "size") == pytest.approx(0.5)
    assert s.ai_scale("X", 2, "size") == pytest.approx(1.5)
    assert s.ai_scale("X", 3, "size") == pytest.approx(1.0)   # v polovici pásma


def test_bez_predikcie_pre_ten_bar_sa_nemeni_nic():
    s = Falosna(config={"tradebot_ai": {"min_probability": 0.5,
                                        "adjust": {"size": [0.5, 1.5]}}})
    s._ai_predictions = {"X": {}}

    assert s.ai_scale("X", 999, "size") == 1.0


def test_konfiguracia_behu_sa_cita_zo_spravneho_kluca():
    assert ai.settings_of({"tradebot_ai": {"min_probability": 0.6}})["min_probability"] == 0.6
    assert ai.settings_of({}) == {}
