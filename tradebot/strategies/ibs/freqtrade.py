"""IBS vo Freqtrade — čo je nad generickým adaptérom vlastné tejto stratégii.

Generická časť (engine cez DataFrame, `tb_*` stĺpce, SL/TP/veľkosť z plánu, export
kresieb) je v `tradebot.adapters.freqtrade.base`. Tu je: HTF sviečky detekčného TF,
hyperopt priestor, trailing, zavretie na konci seansy a timeout limitky.
Freqtrade resolver berie len triedu, ktorej `__module__` == názov súboru, preto
existuje shim `deploy/freqtrade/user_data/strategies/IBSImbalanceStrategy.py`.
"""

from __future__ import annotations

import logging
from datetime import datetime

from pandas import DataFrame

from tradebot.adapters.freqtrade.base import TradebotStrategyBase, _bar, _ts_ms
from tradebot.adapters.freqtrade.runner import EngineRunner
from tradebot.core.candles import timeframe_minutes
from tradebot.core import Bar, SessionClock
from tradebot.core.risk import TrailingPlan, extreme_before_stop
from tradebot.core.types import Direction, TradeDirection

logger = logging.getLogger(__name__)

#: `enter_tag` IBS obchodu je ``ibs:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibs:"

__all__ = ["IBSImbalanceStrategy", "ENTRY_TAG_PREFIX"]


class IBSImbalanceStrategy(TradebotStrategyBase):
    """Port Pine stratégie „IBS Imbalance Breakout Strategy"."""

    STRATEGY_KEY = "ibs"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"

    # Hyperopt priestor tu NIE JE. Čo sa ladí, si volí tester vo formulári a plán
    # z toho pri importe triedy dorobí Freqtrade parametre
    # (`tradebot/adapters/freqtrade/hyperplan.py`). Čo o ladení IBS vieme — odporúčané
    # parametre, pred čím varovať a väzba „koniec okna za začiatkom" — je v
    # `tradebot/strategies/ibs/hyperopt.py`, teda pri stratégii, nie v adaptéri.

    # -- IBS názvy configu a nástroja (testy a hyperopt kód ich používajú) -------

    @property
    def ibs_cfg(self):
        return self.tb_cfg

    @ibs_cfg.setter
    def ibs_cfg(self, value) -> None:
        self.tb_cfg = value

    @property
    def ibs_inst(self):
        return self.tb_inst

    @ibs_inst.setter
    def ibs_inst(self, value) -> None:
        self.tb_inst = value

    # ------------------------------------------------------------------ #

    def _after_profile(self) -> None:
        # Spot: burza nemá čo požičať, takže žiadne shorty ani páka. Freqtrade by
        # stratégiu s `can_short` v spot režime ani nespustil.
        if self.config.get("trading_mode", "spot") == "spot":
            self.can_short = False
            if self.ibs_cfg.tradeDirection is not TradeDirection.LONG_ONLY:
                logger.warning("IBS: spotový trh — tradeDirection %s sa zužuje na longy",
                               self.ibs_cfg.tradeDirection.value)
        #: Vlastne hodiny pre `custom_exit` - viď tam preco nie signal z enginu.
        self._clock = SessionClock(self.ibs_cfg)
        self._check_unfilled_timeout()

    def _entry_timeout_minutes(self) -> int:
        """Ako dlho smie limitka čakať — Pine `state5MaxBars` prevedené na minúty."""
        return int(self.ibs_cfg.state5MaxBars) * timeframe_minutes(self.timeframe)

    def _check_unfilled_timeout(self) -> None:
        """`unfilledtimeout.entry` vo Freqtrade configu nesmie byť kratší než engine.

        Freqtrade ruší nevyplnenú limitku podľa `unfilledtimeout` NEZÁVISLE od
        `check_entry_timeout` — čo príde skôr, platí. Engine (aj Pine) drží order
        `state5MaxBars` barov, teda 30 minút na 3m grafe. S kratším configom by
        Freqtrade zrušil ordery, ktoré TradingView ešte vyplnil, a engine by
        o tom nevedel (blokoval by opačné vstupy, čakal na vyplnenie...).
        """
        raw = self.config.get("unfilledtimeout") or {}
        entry = raw.get("entry")
        if entry is None:
            return
        minutes = float(entry) / (60 if raw.get("unit", "minutes") == "seconds" else 1)
        need = self._entry_timeout_minutes()
        if minutes < need:
            logger.warning(
                "IBS: unfilledtimeout.entry=%s min je kratší než state5MaxBars × timeframe "
                "= %d min. Freqtrade zruší limitky skôr než engine; nastav aspoň %d.",
                minutes, need, need,
            )

    # ------------------------------------------------------------------ #
    # HTF: sviečky detekčného TF zón
    # ------------------------------------------------------------------ #

    def _feed_informative(self, runner: EngineRunner, pair: str) -> None:
        """Naplní `runner.htf` uzavretými barmi detekčného TF a SMA objemu."""
        htf_bars: dict[int, Bar] = {}
        htf_sma: dict[int, float] = {}
        tf = self._informative_tfs[0]
        if self.dp is not None:
            # `informative_frame` súbor pre TF dopočíta z 1m, keď na disku nie je
            htf = self.informative_frame(pair, tf)
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
                    "IBS: chýbajú %s dáta pre %s a nedali sa poskladať ani z 1m - "
                    "bez nich sa nevytvorí ani jedna SD zóna", tf, pair,
                )
        runner.htf.load(htf_bars, htf_sma)

    def _log_populate(self, pair: str, dataframe: DataFrame, runner: EngineRunner) -> None:
        longs = int(dataframe["tb_enter_long"].sum())
        shorts = int(dataframe["tb_enter_short"].sum())
        book = runner.engine.book
        logger.info(
            "IBS %s: %d barov, %d HTF barov, %d zon, %d signalov (%d long / %d short)",
            pair, len(dataframe), len(runner.htf.bars), len(book), longs + shorts, longs, shorts,
        )
        # Strop `maxSdZones` je Pine dedičstvo (pamäť a boxy na grafe). Pokiaľ vyhadzuje
        # len vypršané zóny, na výsledok nemá vplyv — keď začne rezať do živého,
        # nech je to v logu vidno a nie hádanie.
        if getattr(book, "evicted_alive", 0):
            logger.warning(
                "IBS %s: strop maxSdZones=%d vyhodil %d este platnych zon (z %d celkom) "
                "- zvaz kratsi zoneValidHours alebo mensi pocet zdrojov zon",
                pair, book.max_zones, book.evicted_alive, book.evicted,
            )

    # ------------------------------------------------------------------ #
    # Trailing, koniec seansy, timeout limitky
    # ------------------------------------------------------------------ #

    def _trailing_stop(self, pair: str, trade, base_stop: float) -> float:
        """`base_stop` posunutý trailingom, ak je zapnutý a už sa aktivoval."""
        if not self.ibs_cfg.enableTrailing:
            return base_stop
        row = self._trade_signal(pair, trade)
        if row is None or row.entry != row.entry:
            return base_stop
        trail = TrailingPlan.build(self.ibs_cfg, self.ibs_inst, abs(row.entry - base_stop))
        if trail is None:
            return base_stop

        long = not trade.is_short
        direction = Direction.LONG if long else Direction.SHORT
        key = (pair, trade.open_date_utc)
        prev = self._extremes.get(key, row.entry)

        bar_open, high, low = getattr(self, "_candle", (None, None, None))
        if high is None or low is None:
            # Dry-run a live: sviečku nemáme, ostáva bežiaci extrém od Freqtrade.
            extreme = trade.min_rate if trade.is_short else trade.max_rate
            return trail.stop_price(direction, row.entry, base_stop, extreme or row.entry)

        best = high if long else low
        after = max(prev, best) if long else min(prev, best)
        self._extremes[key] = after
        before_stop = trail.stop_price(direction, row.entry, base_stop, prev)
        after_stop = trail.stop_price(direction, row.entry, base_stop, after)

        if extreme_before_stop(bar_open, high, low, long=long):
            # Cena šla najprv priaznivo — trailing sa posunul a Freqtrade ho hneď
            # otestuje proti low (resp. high), presne ako chceme.
            return after_stop

        # Nepriaznivý extrém prvý: platí ešte starý stop. Freqtrade však vie otestovať
        # len jednu hodnotu proti low, takže sa tu rozhodne za neho — spiatočná noha
        # baru sa testuje proti `close`, a keď neprejde, vráti sa starý stop, ktorý
        # low (už overené) netrafí.
        if (low <= before_stop) if long else (high >= before_stop):
            return before_stop
        close = self._detail_close(pair, self._candle_time)
        if close is None:
            return after_stop
        crossed = close <= after_stop if long else close >= after_stop
        return after_stop if crossed else before_stop

    def custom_exit(
        self, pair: str, trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ) -> str | None:
        """Pine `closeAtSessionEnd` — po poslednej seanse dna sa pozicia zavrie natvrdo.

        Zamerne sa NEpouziva signal z enginu: ten sa pocita z **uzavreteho** baru
        a Freqtrade by ho vyhodnotil uz na tom istom bare, teda o jeden bar skor,
        nez ho videl Pine. Hodiny su deterministicke, takze rovnaka odpoved bez
        akehokolvek nahliadnutia dopredu.

        Vystup cez exit-signal (a nie `custom_roi`) je tu spravne: ide o trhovy
        prikaz „zavri za akukolvek cenu", nie o odpocivajucu limitku.

        Hodiny sa pytaju na **predchadzajuci** bar grafu, nie na aktualny cas. Pine
        vyhodnocuje `barstate.isconfirmed`, teda az na zatvoreni baru T, a `immediately=true`
        plni jeho zatvaracou cenou. Freqtrade plni exit-signal otvaracou cenou sviecky,
        a otvaracia cena baru T+1 sa zatvaracej cene baru T rovna. Bez tohto posunu
        vysiel vystup o cely bar skor: 78 399,1 namiesto 78 424,1 (BTCUSDT 2026-08-26).
        """
        if not self.ibs_cfg.closeAtSessionEnd:
            return None
        from freqtrade.exchange import timeframe_to_msecs

        tf_ms = timeframe_to_msecs(self.timeframe)
        now_ms = int(current_time.timestamp() * 1000)
        state = self._clock.state(now_ms // tf_ms * tf_ms - tf_ms)
        if state.no_more_sessions_today and not state.in_trade_window:
            return "session_end"
        return None

    def check_entry_timeout(
        self, pair: str, trade, order, current_time: datetime, **kwargs
    ) -> bool:
        """Pine STATE 5: nevyplnený order sa ruší po `state5MaxBars` baroch alebo
        na konci obchodného okna — čo príde skôr.

        Engine tie CANCEL intenty vydáva, ale Freqtrade ich nevidí: do DataFrame ide
        len vstupný signál a čakajúcu limitku si ďalej spravuje sám. Bez tohto
        callbacku by o jej osude rozhodoval iba `unfilledtimeout` z configu, a ten
        s enginom nikto nezosúladil (10 minút proti 30) — Freqtrade by rušil ordery,
        ktoré TradingView ešte vyplnil.

        Počítanie barov: engine zadá order na zatvorení baru T a na zatvorení baru
        T+`state5MaxBars` ho po poslednom pokuse o vyplnenie zruší. Freqtrade order
        otvorí na sviečke T+1, takže zrušiť ho má, keď od otvorenia uplynulo aspoň
        `state5MaxBars` sviečok — sviečka T+`state5MaxBars` sa ešte plní.

        Koniec okna sa, rovnako ako v `custom_exit`, číta z PREDCHÁDZAJÚCEHO baru:
        engine ho vyhodnotil na jeho zatvorení, čo je otvorenie tejto sviečky.
        """
        from freqtrade.exchange import timeframe_to_msecs

        tf_ms = timeframe_to_msecs(self.timeframe)
        opened = trade.open_date_utc
        if opened is not None:
            elapsed_ms = int((current_time - opened).total_seconds() * 1000)
            if elapsed_ms >= self.ibs_cfg.state5MaxBars * tf_ms:
                return True

        now_ms = int(current_time.timestamp() * 1000)
        state = self._clock.state(now_ms // tf_ms * tf_ms - tf_ms)
        return not state.in_trade_window
