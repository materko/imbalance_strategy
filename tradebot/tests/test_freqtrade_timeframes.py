"""Chýbajúci timeframe si stratégia dopočíta z 1m — `TradebotStrategyBase.ensure_timeframe`.

Freqtrade si vyšší TF nedopočíta: pre základný TF behu skončí na „No history … found",
informatívny ticho vráti prázdny DataFrame a stratégia potom nevytvorí ani jednu zónu.
Adaptér ho preto poskladá z 1m — cez dátový handler Freqtradu, takže pomenovanie aj formát
súboru sú jeho.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("freqtrade")

from freqtrade.data.history import get_datahandler
from freqtrade.enums import CandleType, RunMode

from tradebot.core import derived as derived_mod
from tradebot.core.candles import resample_ohlcv

strategy_mod = pytest.importorskip("tradebot.adapters.freqtrade.strategy")
IBSImbalanceStrategy = strategy_mod.IBSImbalanceStrategy

PAIR = "BTC/USDT:USDT"


def m1(n: int, start: str = "2025-01-06 00:00", freq: str = "1min") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({
        "date": idx,
        "open": [100.0 + i for i in range(n)],
        "high": [101.0 + i for i in range(n)],
        "low": [99.0 + i for i in range(n)],
        "close": [100.5 + i for i in range(n)],
        "volume": [1.0] * n,
    })


@pytest.fixture
def strategy(tmp_path: Path, monkeypatch):
    """Stratégia bez behu Freqtradu: len config, spec a prázdny datadir."""
    from tradebot.strategies import get_spec

    s = IBSImbalanceStrategy.__new__(IBSImbalanceStrategy)
    s.spec = get_spec("ibs")
    s.config = {
        "datadir": tmp_path,
        "dataformat_ohlcv": "feather",
        "candle_type_def": CandleType.FUTURES,
        "runmode": RunMode.BACKTEST,
        "exchange": {"pair_whitelist": [PAIR]},
    }
    s.dp = None
    monkeypatch.setattr(derived_mod, "MANIFEST", tmp_path / ".derived.json")
    return s


def handler(tmp_path: Path):
    return get_datahandler(tmp_path, "feather")


def test_chybajuci_tf_sa_poskladá_z_1m(strategy, tmp_path):
    handler(tmp_path).ohlcv_store(PAIR, "1m", data=m1(600), candle_type=CandleType.FUTURES)

    assert strategy.ensure_timeframe(PAIR, "5m") is True

    made = handler(tmp_path).ohlcv_load(PAIR, "5m", candle_type=CandleType.FUTURES)
    ref = resample_ohlcv(m1(600), 5)
    assert len(made) == len(ref)
    assert list(made["close"]) == list(ref["close"])


def test_existujuci_tf_sa_neprepise(strategy, tmp_path):
    h = handler(tmp_path)
    h.ohlcv_store(PAIR, "1m", data=m1(600), candle_type=CandleType.FUTURES)
    h.ohlcv_store(PAIR, "5m", data=m1(3, freq="5min"), candle_type=CandleType.FUTURES)  # „z burzy"

    assert strategy.ensure_timeframe(PAIR, "5m") is True
    # ostali tri bary z burzy, nie 120 dopočítaných zo 600 minút
    assert len(h.ohlcv_load(PAIR, "5m", candle_type=CandleType.FUTURES)) == 3


def test_vyrobeny_subor_je_evidovany_ako_odvodeny(strategy, tmp_path):
    handler(tmp_path).ohlcv_store(PAIR, "1m", data=m1(600), candle_type=CandleType.FUTURES)
    strategy.ensure_timeframe(PAIR, "15m")

    evidencia = derived_mod.derived(tmp_path / ".derived.json")
    assert [p.name for p in evidencia] == ["BTC_USDT_USDT-15m-futures.feather"]


def test_bez_1m_sa_neda_nic(strategy, tmp_path):
    assert strategy.ensure_timeframe(PAIR, "5m") is False
    assert not list(tmp_path.rglob("*.feather"))


def test_1m_sa_nikdy_nevyraba(strategy, tmp_path):
    """1m je zdroj — keď chýba ono, nie je z čoho skladať a nesmie sa nič vymyslieť."""
    assert strategy.ensure_timeframe(PAIR, "1m") is False


@pytest.mark.parametrize("mode", [RunMode.DRY_RUN, RunMode.LIVE])
def test_v_zivom_behu_sa_nedopocitava(strategy, tmp_path, mode):
    """Tam prichádzajú sviečky z burzy a vymyslený bar by bol chyba, nie pomoc."""
    handler(tmp_path).ohlcv_store(PAIR, "1m", data=m1(600), candle_type=CandleType.FUTURES)
    strategy.config["runmode"] = mode

    assert strategy.ensure_timeframe(PAIR, "5m") is True     # netvrdíme, že dáta nie sú
    assert not (tmp_path / "futures" / "BTC_USDT_USDT-5m-futures.feather").exists()


def test_neznamy_timeframe_beh_nezhodi(strategy, tmp_path):
    handler(tmp_path).ohlcv_store(PAIR, "1m", data=m1(60), candle_type=CandleType.FUTURES)
    assert strategy.ensure_timeframe(PAIR, "7x") is False
