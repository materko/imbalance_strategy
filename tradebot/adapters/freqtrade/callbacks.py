"""SL / TP / veľkosť — všetko per obchod, z plánu, ktorý spočítal engine
(`custom_*` a `confirm_*` callbacky Freqtradu).
"""

from __future__ import annotations

import logging
from datetime import datetime

from freqtrade.strategy import IStrategy, stoploss_from_absolute

from tradebot.core.money import point_value_for_pair

from .frames import _ts_ms
from .runner import SignalRow

logger = logging.getLogger(__name__)


#: Freqtrade si z nášho stake spätne dopočíta množstvo ako ``stake / cena * páka``
#: a výsledok **oreže** na krok kontraktu. Delenie a násobenie tou istou cenou ale
#: v plávajúcej rádovej čiarke presné nie je: 1 BTC pri 79 419,5 sa vráti ako
#: 0,9999999999999999 a z toho je po orezaní 0,999 — teda o krok menšia pozícia, než
#: plán žiada. Na piatich obchodoch golden testu to robilo rozdiel 0,26 USD oproti
#: TradingView. Zlomok promile navyše chybu prekryje a na veľkosť pozície vplyv nemá:
#: krok kontraktu je o desať rádov väčší.
_STAKE_EPS = 1e-12


class CallbacksMixin(IStrategy):
    """SL, TP, veľkosť a páka obchodu z plánu enginu (`custom_*`, `confirm_*`).
    Časť `TradebotStrategyBase`.

    Dedí z `IStrategy` kvôli hyperoptu — dôvod je pri `AIMixin` (`ai.py`)."""

    @classmethod
    def _tag_ts(cls, tag) -> int | None:
        """``<prefix><ms>`` → ms, inak `None` (force entry, starý obchod bez tagu)."""
        prefix = cls.ENTRY_TAG_PREFIX
        if not isinstance(tag, str) or not tag.startswith(prefix):
            return None
        try:
            return int(tag[len(prefix):])
        except ValueError:
            return None

    def _signal(self, pair: str, when, tag=None) -> SignalRow | None:
        """Signál, z ktorého tento obchod vznikol.

        Primárne podľa `enter_tag` (presný bar), až potom podľa času — viď
        `EngineRunner.signal_at_or_before`, prečo samotný čas nestačí.
        """
        runner = self._runners.get(pair)
        if runner is None:
            return None
        ts = self._tag_ts(tag)
        if ts is not None:
            row = runner.signal_at(ts)
            if row is not None:
                return row
        if when is None:
            return None
        return runner.signal_at_or_before(int(when.timestamp() * 1000))

    def _trade_signal(self, pair: str, trade) -> SignalRow | None:
        return self._signal(pair, trade.open_date_utc, getattr(trade, "enter_tag", None))

    def _levels(self, pair: str, trade) -> tuple[float, float] | None:
        """(SL, TP) zo signálu, na ktorom obchod vznikol — po prípadnej úprave modelom.

        Je to jediné miesto, kde sa plán mení, takže stop aj take profit vidia tú istú
        úpravu. Škáluje sa **vzdialenosť od vstupu**, nie cena: násobok 1,2 znamená
        „o pätinu ďalej", nie „o pätinu vyššie".
        """
        row = self._trade_signal(pair, trade)
        if row is None or row.stop_loss != row.stop_loss:  # NaN check
            return None
        stop_loss, take_profit = row.stop_loss, row.take_profit
        ts = self._tag_ts(getattr(trade, "enter_tag", None)) or 0
        vstup = row.entry if row.entry == row.entry and row.entry > 0 else trade.open_rate
        for kluc, uroven in (("sl", "stop_loss"), ("tp", "take_profit")):
            nasobok = self.ai_scale(pair, ts, kluc)
            hodnota = stop_loss if uroven == "stop_loss" else take_profit
            if nasobok == 1.0 or hodnota != hodnota:
                continue
            posunuta = vstup + (hodnota - vstup) * nasobok
            if uroven == "stop_loss":
                stop_loss = posunuta
            else:
                take_profit = posunuta
        return stop_loss, take_profit

    def ft_stoploss_adjust(
        self, current_rate, trade, current_time, current_profit, force_stoploss,
        low=None, high=None, *args, **kwargs
    ):
        """Zachytí OHLC práve spracúvanej sviečky — `custom_stoploss` ju inak nevidí.

        Bez nej sa nedá povedať, či cena v sviečke šla najprv hore alebo dole, a pri
        trailingu na tom závisí, či obchod v tej sviečke skončí (viď `extreme_before_stop`).
        `trade.max_rate` nestačí: Freqtrade doň zahrnie high tejto sviečky ešte pred
        volaním, takže z neho poradie už nevyčítaš.
        """
        self._candle = (current_rate, high, low)
        self._candle_time = current_time
        return super().ft_stoploss_adjust(
            current_rate, trade, current_time, current_profit, force_stoploss,
            low, high, *args, **kwargs
        )

    def _detail_close(self, pair: str, when) -> float | None:
        """Zatváracia cena sviečky, ktorú Freqtrade práve testuje.

        `custom_stoploss` dostane open, high aj low, ale nie close — a bez neho sa
        nedá dopočítať spiatočná noha baru (viď IBS `_trailing_stop`). Sviečky sa preto
        načítajú raz na pár a držia sa v dicte podľa času.
        """
        if when is None or self.dp is None:
            return None
        closes = self._closes.get(pair)
        if closes is None:
            tf = self.config.get("timeframe_detail") or self.timeframe
            try:
                df = self.dp.historic_ohlcv(pair, tf)
            except Exception:  # pragma: no cover - chýbajúce dáta, nie chyba logiky
                df = None
            closes = {} if df is None or df.empty else dict(
                zip(_ts_ms(df["date"]), df["close"].astype(float))
            )
            self._closes[pair] = closes
        return closes.get(int(when.timestamp() * 1000))

    def custom_entry_price(
        self, pair: str, trade, current_time, proposed_rate: float, entry_tag, side: str, **kwargs
    ) -> float:
        """Limitka presne na cene plánu — Pine `strategy.entry(limit=entryPrice)`."""
        row = self._signal(pair, current_time, entry_tag)
        if row is None or row.entry != row.entry:
            return proposed_rate
        return row.entry

    def custom_stake_amount(
        self, pair: str, current_time, current_rate: float, proposed_stake: float,
        min_stake, max_stake: float, leverage: float, entry_tag, side: str, **kwargs
    ) -> float:
        """Veľkosť z plánu enginu (`qty` kontraktov).

        Freqtrade pracuje so **stake v quote mene**, nie s počtom kontraktov, takže
        sa qty prepočíta cez cenu (tú z plánu, rovnakú ako dá `custom_entry_price`),
        hodnotu bodu a páku. Späť si množstvo dopočíta ako ``stake / cena * páka`` v základnej
        mene, vydelí `contractSize` (burza Tester ho má rovný hodnote bodu, viď
        `tester.ftexchange`) a výsledok **oreže** na krok kontraktu — preto ten zlomok
        promile navyše, viď `_STAKE_EPS`. Bez hodnoty bodu by 1 lot EURUSD stál 1,1 USD.
        """
        row = self._signal(pair, current_time, entry_tag)
        if row is None or row.qty != row.qty or current_rate <= 0:
            return proposed_stake

        rate = row.entry if row.entry == row.entry and row.entry > 0 else current_rate
        # Časť 2: čím si je model istejší, tým väčšia pozícia. Mantinely sú zo zadania
        # behu, takže model nemôže poslať veľkosť ani do neba, ani na nulu.
        ts = self._tag_ts(entry_tag) or 0
        # Vzdialenejší stop znamená pri tej istej veľkosti väčšiu stratu, tak sa množstvo
        # dopočíta späť: riziko na obchod ostane to, čo bolo zadané, a mení sa len to,
        # kde stop leží. Kto chce meniť aj riziko, má na to `size`.
        nasobok = self.ai_scale(pair, ts, "size") / max(self.ai_scale(pair, ts, "sl"), 1e-9)
        # hodnota bodu páru behu (register inštrumentov), inak inštrumentu profilu
        pv = point_value_for_pair(pair) or float(getattr(getattr(self, "tb_inst", None), "point_value", 1.0) or 1.0)
        wanted = row.qty * nasobok * rate * pv / max(leverage, 1.0) * (1.0 + _STAKE_EPS)
        stake = wanted
        if min_stake is not None:
            stake = max(stake, min_stake)
        stake = min(stake, max_stake)

        if stake < wanted * 0.999:
            # Dolezite: ked peňaženka nestaci, riziko na obchod je v skutocnosti MENSIE
            # nez planovane - a bez tohto hlasenia by to bolo ticho. Riesenie je
            # vacsi dry_run_wallet, paka, alebo nizsi limit rizika.
            logger.warning(
                "%s %s: stake orezany z %.2f na %.2f (%.1f%% z chceneho). "
                "Limit rizika na obchod sa pri tomto SL a zostatku neuplatni cely.",
                self.spec.key, pair, wanted, stake, stake / wanted * 100,
            )
        return stake

    def custom_stoploss(
        self, pair: str, trade, current_time: datetime, current_rate: float,
        current_profit: float, after_fill: bool, **kwargs
    ) -> float | None:
        """Absolútny SL z plánu, posunutý trailingom stratégie. Prepočet na relatívnu hodnotu rieši
        `stoploss_from_absolute`, aby sa nemuselo ručne riešiť znamienko pre shorty ani páka.

        `trade.max_rate`/`min_rate` aktualizuje Freqtrade v `should_exit()` **pred** týmto
        volaním, takže extrém už zahŕňa aktuálnu sviečku — rovnako ako offline simulácia
        v `tester.compare.scan_trades`. S `--timeframe-detail 1m` je teda trailing po minútach.
        """
        levels = self._levels(pair, trade)
        if levels is None or current_rate <= 0:
            return None
        stop_price, _ = levels
        stop_price = self._trailing_stop(pair, trade, stop_price)
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
        """TP z plánu ako odpočívajúci limit.

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

    def custom_exit(
        self, pair: str, trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ) -> str | None:
        """Engine povedal „zavri" (`close_session` na predchádzajúcom uzavretom bare) → trhový výstup.

        Číta sa PREDCHÁDZAJÚCI bar grafu: engine ho vyhodnotil na jeho zatvorení, čo je
        otvorenie sviečky, ktorú Freqtrade práve spracúva. Stratégia s vlastnou logikou
        výstupu (IBS: hodiny seáns) túto metódu prepíše.
        """
        runner = self._runners.get(pair)
        if runner is None:
            return None
        from freqtrade.exchange import timeframe_to_msecs

        tf_ms = timeframe_to_msecs(self.timeframe)
        now_ms = int(current_time.timestamp() * 1000)
        row = runner.rows.get(now_ms // tf_ms * tf_ms - tf_ms)
        return "signal_close" if row is not None and row.close_session else None

    def confirm_trade_entry(
        self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str,
        current_time: datetime, entry_tag, side: str, **kwargs
    ) -> bool:
        """Posledná poistka: mimo trade okna sa nevstupuje ani keď signál dobehol neskôr."""
        row = self._signal(pair, current_time, entry_tag)
        return True if row is None else row.in_trade_window

    def confirm_trade_exit(
        self, pair: str, trade, order_type: str, amount: float, rate: float,
        time_in_force: str, exit_reason: str, current_time: datetime, **kwargs
    ) -> bool:
        """Výstup nikdy neblokuje — len upratie stav trailingu, aby v dlhom live
        behu `_extremes` nerástol s každým obchodom."""
        self._extremes.pop((pair, trade.open_date_utc), None)
        return True

    def leverage(
        self, pair: str, current_time: datetime, current_rate: float,
        proposed_leverage: float, max_leverage: float, entry_tag, side: str, **kwargs
    ) -> float:
        """Páka z profilu (pole `leverage`, ak ho stratégia má), orezaná tým, čo burza dovolí.

        Pri páke 1 sa risk-based sizing na BTC nezmestí do peňaženky a limit rizika
        sa ticho neuplatní — viď `IBSConfig.leverage`.
        """
        return min(float(getattr(self.tb_cfg, "leverage", 1.0)), max_leverage)
