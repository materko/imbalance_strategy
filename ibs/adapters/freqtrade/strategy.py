"""Freqtrade adaptér — tenká vrstva nad `ibs.core`.

Žiadna logika stratégie tu nie je. Adaptér len:
  1. dotiahne 5m sviečky pre detekciu zón,
  2. prebehne engine cez DataFrame a zapíše signály do stĺpcov,
  3. preloží ich na Freqtrade entry/exit, SL, TP a veľkosť pozície.

Nastavenia stratégie sa berú z `ibs/configs/*.json`, **nie** z Freqtrade configu.
Profil sa dá prepnúť cez `IBS_PROFILE` v prostredí.
"""

from __future__ import annotations

import logging
import os
from dataclasses import fields
from datetime import datetime

from pandas import DataFrame

from freqtrade.strategy import (
    CategoricalParameter,
    DecimalParameter,
    IStrategy,
    stoploss_from_absolute,
)

from ...core import Bar, load_profile
from ...core.types import SizeSpec
from .runner import EngineRunner, SignalRow

#: Stĺpec v DataFrame -> pole `SignalRow`.
_COLUMN_ATTRS = {
    "ibs_enter_long": "enter_long",
    "ibs_enter_short": "enter_short",
    "ibs_entry": "entry",
    "ibs_sl": "stop_loss",
    "ibs_tp": "take_profit",
    "ibs_qty": "qty",
    "ibs_zone_uid": "zone_uid",
    "ibs_in_trade_window": "in_trade_window",
}

logger = logging.getLogger(__name__)

DEFAULT_PROFILE = os.environ.get("IBS_PROFILE", "btcusdt_3m_binance")


def _ts_ms(series) -> list[int]:
    """Stĺpec `date` → ms epoch.

    Freqtrade drží `date` ako **datetime64[ms]**, takže `.astype("int64")` vráti
    milisekundy — zatiaľ čo `Timestamp.value` vracia nanosekundy vždy. Tie dve cesty
    sa líšia o 10^6 a keď sa zmiešajú, kľúče sa nikdy netrafia a stratégia ticho
    nevygeneruje ani jeden signál. Preto sa prevod robí na jednom mieste.
    """
    return (series.astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).tolist()


def _bar(row, ts: int) -> Bar:
    return Bar(
        time=ts,
        open=float(row.open),
        high=float(row.high),
        low=float(row.low),
        close=float(row.close),
        volume=float(row.volume),
    )


class IBSImbalanceStrategy(IStrategy):
    """Port Pine stratégie „IBS Imbalance Breakout Strategy"."""

    INTERFACE_VERSION = 3

    timeframe = "3m"
    #: Pozor: NIKDY neprepnúť stratégiu na 1m — všetky `*MaxBars` limity sú
    #: v BAROCH, nie v minútach (ARCHITECTURE_port.md §7). 1m je len detail fillov.
    timeframe_detail = "1m"

    can_short = True
    process_only_new_candles = True
    use_exit_signal = True
    use_custom_stoploss = True
    #: TP ide cez `custom_roi`, nie cez `custom_exit` — viď tam prečo.
    use_custom_roi = True

    #: SL aj TP riadi engine per obchod, nie tieto globálne hodnoty.
    stoploss = -0.99
    #: Nedosiahnuteľná hodnota — reálny prah dodáva `custom_roi` per obchod.
    minimal_roi = {"0": 100.0}

    startup_candle_count = 300

    # ------------------------------------------------------------------ #
    # Hyperopt priestor
    #
    # Parametre stratégie žijú v `IBSConfig`, nie vo Freqtrade. Tieto objekty sú
    # len most: `_apply_hyperopt_params()` ich pred každým výpočtom vloží do configu.
    # Optimalizujú sa výhradne prahy v jednotke `atr` (tie sú naladené na MNQ a na BTC
    # nedávajú zmysel) plus `rrRatio` a prepínače entry modelov. Session okná, STATE
    # timeouty ani sizing sa neladia - tie sú prevzaté z TradingView a menili by paritu.
    # ------------------------------------------------------------------ #

    #: `enableImbEntry` sa zámerne NEOPTIMALIZUJE - je to základný model stratégie.
    p_rr = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space="sell", optimize=True)
    p_imb_size = DecimalParameter(0.05, 1.00, default=0.25, decimals=2, space="buy")
    p_pb_range = DecimalParameter(0.05, 1.00, default=0.20, decimals=2, space="buy")
    p_eng_range = DecimalParameter(0.05, 1.00, default=0.20, decimals=2, space="buy")
    p_liq_wick = DecimalParameter(0.05, 1.00, default=0.30, decimals=2, space="buy")
    p_sr_cluster = DecimalParameter(0.10, 1.50, default=0.50, decimals=2, space="buy")
    p_pin_bar = CategoricalParameter([True, False], default=True, space="buy")
    p_engulfing = CategoricalParameter([True, False], default=True, space="buy")
    p_sr_trading = CategoricalParameter([True, False], default=True, space="buy")
    p_lq_trading = CategoricalParameter([True, False], default=True, space="buy")

    #: Ktorý parameter ide do ktorého poľa configu; hodnoty s jednotkou `atr`.
    _ATR_PARAMS = {
        "minImbSizePoints": "p_imb_size",
        "pbMinRangePoints": "p_pb_range",
        "engMinRangePoints": "p_eng_range",
        "liqSweepMinWick": "p_liq_wick",
        "srClusterPoints": "p_sr_cluster",
    }
    _FLAG_PARAMS = {
        "enablePinBarEntry": "p_pin_bar",
        "enableEngulfingEntry": "p_engulfing",
        "enableSrTrading": "p_sr_trading",
        "enableLqTrading": "p_lq_trading",
    }

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.ibs_cfg, self.ibs_inst = load_profile(DEFAULT_PROFILE)
        warnings = self.ibs_cfg.check_instrument(self.ibs_inst)
        for w in warnings:
            logger.warning("IBS config: %s", w)
        self._runners: dict[str, EngineRunner] = {}
        self._runner_fp: tuple | None = None
        self._informative_tf = f"{int(self.ibs_cfg.zoneDetectionTF)}m"

    # ------------------------------------------------------------------ #

    def informative_pairs(self):
        pairs = self.dp.current_whitelist() if self.dp else []
        return [(p, self._informative_tf) for p in pairs]

    def _apply_hyperopt_params(self) -> None:
        """Vloží hodnoty hyperopt parametrov do `ibs_cfg`.

        Volá sa na začiatku `populate_indicators`, teda EŠTE PRED `_runner()` —
        odtlačok configu tak zmenu uvidí a runner sa postaví nanovo.

        **Hyperopt sa MUSÍ spúšťať s `--analyze-per-epoch`.** Freqtrade štandardne
        počíta `populate_indicators` len raz pre celý beh a per-epochu prepočítava
        iba `populate_entry_trend` — lebo predpokladá, že parametre priestoru „buy"
        ovplyvňujú len signály. Celý náš engine ale beží v `populate_indicators`,
        takže bez toho prepínača dá každá epocha ten istý výsledok. Prejaví sa to
        tak, že všetkých N epoch má identický PnL aj počet obchodov.

        Prahy sa musia priradiť ako `SizeSpec(..., "atr")`. Holé číslo by
        `IBSConfig.__setattr__` skoercoval na predvolenú jednotku poľa (`abs`),
        čo je pri BTC rádový rozdiel — a stalo by sa to ticho.
        """
        if not self.hyperopt_active:
            return
        for field, attr in self._ATR_PARAMS.items():
            setattr(self.ibs_cfg, field, SizeSpec(float(getattr(self, attr).value), "atr"))
        for field, attr in self._FLAG_PARAMS.items():
            setattr(self.ibs_cfg, field, bool(getattr(self, attr).value))
        self.ibs_cfg.rrRatio = float(self.p_rr.value)

    @property
    def hyperopt_active(self) -> bool:
        """Pri obyčajnom backteste sa profil z JSON nesmie prepísať defaultmi."""
        from freqtrade.enums import RunMode

        return self.config.get("runmode") is RunMode.HYPEROPT

    def _config_fingerprint(self) -> tuple:
        """Odtlačok parametrov, ktoré menia výsledok.

        Runner je zámerne inkrementálny (dry/live ho volá nad rastúcim DataFrame),
        takže si medzi volaniami drží stav. Pri hyperopte sa ale parametre menia
        medzi epochami a starý runner by ticho počítal so starými — preto sa pri
        zmene odtlačku zahodí a postaví nanovo.
        """
        cfg = self.ibs_cfg
        return tuple(
            str(getattr(cfg, f.name)) for f in sorted(fields(cfg), key=lambda x: x.name)
        )

    def _runner(self, pair: str) -> EngineRunner:
        fp = self._config_fingerprint()
        if fp != self._runner_fp:
            self._runners.clear()
            self._runner_fp = fp
        runner = self._runners.get(pair)
        if runner is None:
            runner = EngineRunner(self.ibs_cfg, self.ibs_inst, int(self.timeframe.rstrip("m")))
            self._runners[pair] = runner
        return runner

    # ------------------------------------------------------------------ #

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata["pair"]
        self._apply_hyperopt_params()
        runner = self._runner(pair)

        htf_bars: dict[int, Bar] = {}
        htf_sma: dict[int, float] = {}
        if self.dp is not None:
            htf = self.dp.get_pair_dataframe(
                pair=pair,
                timeframe=self._informative_tf,
                candle_type=self.config.get("candle_type_def", ""),
            )
            if htf is not None and not htf.empty:
                htf = htf.copy()
                # Pine ta.sma(volume, volSmaLen)[1] - posun o 1 je zámerný, aby sa
                # nepoužil ešte neuzavretý bar.
                htf["vol_sma"] = htf["volume"].rolling(self.ibs_cfg.volSmaLen).mean()
                for ts, row in zip(_ts_ms(htf["date"]), htf.itertuples(index=False)):
                    htf_bars[ts] = _bar(row, ts)
                    htf_sma[ts] = float(row.vol_sma) if row.vol_sma == row.vol_sma else 0.0
            else:
                logger.warning(
                    "IBS: chýbajú %s dáta pre %s - bez nich sa nevytvorí ani jedna SD zóna",
                    self._informative_tf, pair,
                )

        ts_index = _ts_ms(dataframe["date"])
        for ts, row in zip(ts_index, dataframe.itertuples(index=False)):
            if runner.last_ts is not None and ts <= runner.last_ts:
                continue  # už spracované - runner je inkrementálny
            window = runner.htf_window_for(ts, htf_bars, htf_sma)
            runner.process(_bar(row, ts), window)

        rows = runner.rows
        empty = SignalRow()
        for col, attr in _COLUMN_ATTRS.items():
            dataframe[col] = [getattr(rows.get(ts, empty), attr) for ts in ts_index]

        logger.info(
            "IBS %s: %d barov, %d HTF barov, %d zon, %d signalov (%d long / %d short)",
            pair,
            len(ts_index),
            len(htf_bars),
            len(runner.engine.book),
            int(dataframe["ibs_enter_long"].sum() + dataframe["ibs_enter_short"].sum()),
            int(dataframe["ibs_enter_long"].sum()),
            int(dataframe["ibs_enter_short"].sum()),
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["ibs_enter_long"] == 1, ["enter_long", "enter_tag"]] = (1, "ibs")
        if self.can_short:
            dataframe.loc[dataframe["ibs_enter_short"] == 1, ["enter_short", "enter_tag"]] = (1, "ibs")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Výstupy rieši custom_roi (TP) a custom_stoploss (SL) per obchod.
        return dataframe

    # ------------------------------------------------------------------ #
    # SL / TP / veľkosť - všetko per obchod, z plánu, ktorý spočítal engine
    # ------------------------------------------------------------------ #

    def _signal(self, pair: str, when) -> SignalRow | None:
        """Signál, z ktorého tento obchod vznikol."""
        runner = self._runners.get(pair)
        if runner is None or when is None:
            return None
        return runner.signal_at_or_before(int(when.timestamp() * 1000))

    def _levels(self, pair: str, trade) -> tuple[float, float] | None:
        """(SL, TP) zo signálu, na ktorom obchod vznikol."""
        row = self._signal(pair, trade.open_date_utc)
        if row is None or row.stop_loss != row.stop_loss:  # NaN check
            return None
        return row.stop_loss, row.take_profit

    def custom_entry_price(
        self, pair: str, trade, current_time, proposed_rate: float, entry_tag, side: str, **kwargs
    ) -> float:
        """Limitka presne na cene gapu — Pine `strategy.entry(limit=entryPrice)`."""
        row = self._signal(pair, current_time)
        if row is None or row.entry != row.entry:
            return proposed_rate
        return row.entry

    def custom_stake_amount(
        self, pair: str, current_time, current_rate: float, proposed_stake: float,
        min_stake, max_stake: float, leverage: float, entry_tag, side: str, **kwargs
    ) -> float:
        """Veľkosť z `maxLossDollar / (SL vzdialenosť × point_value)`.

        Freqtrade pracuje so **stake v quote mene**, nie s počtom kontraktov, takže
        sa qty prepočíta cez aktuálnu cenu a páku.
        """
        row = self._signal(pair, current_time)
        if row is None or row.qty != row.qty or current_rate <= 0:
            return proposed_stake

        wanted = row.qty * current_rate / max(leverage, 1.0)
        stake = wanted
        if min_stake is not None:
            stake = max(stake, min_stake)
        stake = min(stake, max_stake)

        if stake < wanted * 0.999:
            # Dolezite: ked peňaženka nestaci, riziko na obchod je v skutocnosti MENSIE
            # nez maxLossDollar - a bez tohto hlasenia by to bolo ticho. Riesenie je
            # vacsi dry_run_wallet, paka, alebo nizsi maxLossDollar.
            logger.warning(
                "IBS %s: stake orezany z %.2f na %.2f (%.1f%% z chceneho). "
                "maxLossDollar=%.0f sa pri tomto SL a zostatku neuplatni cely.",
                pair, wanted, stake, stake / wanted * 100, self.ibs_cfg.maxLossDollar,
            )
        return stake

    def custom_stoploss(
        self, pair: str, trade, current_time: datetime, current_rate: float,
        current_profit: float, after_fill: bool, **kwargs
    ) -> float | None:
        """Absolútny SL z plánu. Prepočet na relatívnu hodnotu rieši `stoploss_from_absolute`,
        aby sa nemuselo ručne riešiť znamienko pre shorty ani páka."""
        levels = self._levels(pair, trade)
        if levels is None or current_rate <= 0:
            return None
        stop_price, _ = levels
        return stoploss_from_absolute(
            stop_rate=stop_price,
            current_rate=current_rate,
            is_short=trade.is_short,
            leverage=trade.leverage or 1.0,
        )

    def custom_roi(
        self, pair: str, trade, current_time: datetime, trade_duration: int,
        entry_tag: str | None, side: str, **kwargs
    ) -> float | None:
        """TP — `entry ± SL vzdialenosť × rrRatio` — ako odpočívajúci limit.

        Prečo ROI a nie `custom_exit`: exit-signál sa v backteste vyhodnocuje aj plní
        **otváracou cenou sviečky** (`row[OPEN_IDX]`), takže knôt cez TP neurobí nič
        a keď sa napokon spustí, cena je už za TP. Na golden dátach to výstupy posúvalo
        o jednu až tri sviečky neskôr a o 7-11 bodov vyššie, než ukázal TradingView.

        ROI sa naopak vyhodnocuje proti `high` (pre long) danej sviečky a plní sa cenou
        z `calc_close_rate_for_roi()` orezanou do rozsahu sviečky — teda intrabar
        a presne na TP, rovnako ako Pine `strategy.exit(limit=...)`.

        `calc_profit_ratio()` je presná inverzia `calc_close_rate_for_roi()`, takže
        poplatky ani páku netreba riešiť ručne.
        """
        levels = self._levels(pair, trade)
        if levels is None:
            return None
        _, take_profit = levels
        if take_profit != take_profit:  # NaN
            return None
        return trade.calc_profit_ratio(take_profit)

    def confirm_trade_entry(
        self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str,
        current_time: datetime, entry_tag, side: str, **kwargs
    ) -> bool:
        """Posledná poistka: mimo trade okna sa nevstupuje ani keď signál dobehol neskôr."""
        row = self._signal(pair, current_time)
        return True if row is None else row.in_trade_window

    def leverage(
        self, pair: str, current_time: datetime, current_rate: float,
        proposed_leverage: float, max_leverage: float, entry_tag, side: str, **kwargs
    ) -> float:
        """Páka z profilu, orezaná tým, čo burza dovolí.

        Pri páke 1 sa risk-based sizing na BTC nezmestí do peňaženky a `maxLossDollar`
        sa ticho neuplatní — viď `IBSConfig.leverage`.
        """
        return min(float(self.ibs_cfg.leverage), max_leverage)
