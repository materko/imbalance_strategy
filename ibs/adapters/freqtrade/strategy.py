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

from pandas import DataFrame, Series

from freqtrade.strategy import (
    DecimalParameter,
    IntParameter,
    IStrategy,
    stoploss_from_absolute,
)

from ...core import Bar, SessionClock, load_profile
from ...core.risk import TrailingPlan, extreme_before_stop
from ...core.types import Direction, SizeSpec
from .runner import EngineRunner, SignalRow, export_chart

#: `enter_tag` obchodu je ``ibs:<čas baru signálu v ms>``. Vďaka tomu každý
#: `custom_*` callback vie PRESNE, z ktorého signálu obchod vznikol — hľadať
#: „posledný signál pred otvorením" zlyhá, keď engine vygeneruje ďalší signál
#: na sviečke, na ktorej Freqtrade obchod otvára (viď `EngineRunner.signal_at`).
ENTRY_TAG_PREFIX = "ibs:"

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

#: Kam po backteste uložiť kresby enginu (zóny, boxy, štítky) pre graf vo webapp.
#: Prázdne = neukladať. `{pair}` v ceste sa nahradí párom (viac párov v jednom behu).
DRAW_OUT_ENV = "IBS_DRAW_OUT"


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
    #
    # POZOR - priestor je zámerne MALÝ a obsahuje len parametre, ktoré menia
    # **štruktúru** obchodu, nie citlivosť filtra.
    #
    # Prvá verzia ladila desať prahov v jednotke `atr` plus prepínače entry modelov
    # a dopadla presne tak, ako sa to pri desiatich stupňoch voľnosti a ~150 obchodoch
    # za rok dá čakať: víťazná epocha bola na ladenom roku +34,8 %, ale **všetky štyri**
    # out-of-sample roky boli stratové (−11 % až −65 %), viď docs/HYPEROPT_btcusdt_2026-09-04.md.
    #
    # Čo naopak prežilo naprieč piatimi rokmi, boli zmeny s jedným stupňom voľnosti:
    # `rrRatio`, `slLookback` a zapnutie štruktúrneho filtra. Preto sa ladia práve
    # tie tri - a `structureSwingLen`, ktorý sa nikdy neladil, hoci filter, ktorý ho
    # používa, je najsilnejšia páka, akú sme našli.
    #
    # STATE timeouty ani sizing sa neladia - tie su prevzate z TradingView
    # a menili by paritu. Obchodne okno seansy 2 je vynimka, viz nizsie.
    # ------------------------------------------------------------------ #

    p_rr = DecimalParameter(1.0, 8.0, default=5.0, decimals=1, space="sell", optimize=True)
    p_sl_lookback = IntParameter(5, 40, default=20, space="sell", optimize=True)
    p_struct_len = IntParameter(3, 25, default=5, space="buy", optimize=True)

    #: Obchodne okno seansy 2 (New York) - jediny casovy parameter, ktory sa ladi.
    #: Duvod: rozdelenie po seansach ukazalo, ze cely edge je v NY seanse (break-even
    #: 0,0944 % a kladny vo vsetkych piatich rokoch), kym londynska seansa ma -0,0007 %
    #: a len riedi vysledok. Ked jedno okno rozhoduje o vsetkom, oplati sa vediet, ci
    #: je nastavene spravne. Ladia sa len CELE hodiny a len obchodne okno - okno vzniku
    #: zon ostava, aby zony vznikali rovnako. Zije v priestore "protection", takze sa
    #: zapina samostatne cez --spaces protection a nemiesa sa do ostatnych behov.
    p_s2_start = IntParameter(6, 15, default=10, space="protection", optimize=True)
    p_s2_end = IntParameter(11, 23, default=15, space="protection", optimize=True)

    #: Ktorý hyperopt parameter ide do ktorého poľa configu (celé čísla).
    _INT_PARAMS = {
        "slLookback": "p_sl_lookback",
        "structureSwingLen": "p_struct_len",
    }

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.ibs_cfg, self.ibs_inst = load_profile(DEFAULT_PROFILE)
        warnings = self.ibs_cfg.check_instrument(self.ibs_inst)
        for w in warnings:
            logger.warning("IBS config: %s", w)
        self._runners: dict[str, EngineRunner] = {}
        self._runner_fp: tuple | None = None
        #: (pár, čas vstupu) -> najlepšia dosiahnutá cena, vstup do trailingu.
        self._extremes: dict[tuple, float] = {}
        #: OHLC práve spracúvanej sviečky, zachytené v `ft_stoploss_adjust`.
        self._candle: tuple = (None, None, None)
        self._candle_time = None
        #: pár -> {čas sviečky v ms: close}; dopĺňa sa lenivo.
        self._closes: dict[str, dict[int, float]] = {}
        self._informative_tf = f"{int(self.ibs_cfg.zoneDetectionTF)}m"
        #: Vlastne hodiny pre `custom_exit` - viď tam preco nie signal z enginu.
        self._clock = SessionClock(self.ibs_cfg)
        self._check_unfilled_timeout()

    def _entry_timeout_minutes(self) -> int:
        """Ako dlho smie limitka čakať — Pine `state5MaxBars` prevedené na minúty."""
        return int(self.ibs_cfg.state5MaxBars) * int(self.timeframe.rstrip("m"))

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
        """
        if not self.hyperopt_active:
            return
        for field, attr in self._INT_PARAMS.items():
            setattr(self.ibs_cfg, field, int(getattr(self, attr).value))
        self.ibs_cfg.rrRatio = float(self.p_rr.value)

        # Okno musi mat kladnu dlzku. Hyperopt obmedzenia medzi parametrami nevie
        # vyjadrit, takze sa koniec posunie za zaciatok tu - inak by cela vetva
        # priestoru davala nula obchodov a optimalizator by v nej blúdil naslepo.
        start, end = int(self.p_s2_start.value), int(self.p_s2_end.value)
        self.ibs_cfg.sess2TradeStartH = start
        self.ibs_cfg.sess2TradeEndH = max(end, start + 1)

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
        self._export_chart(pair, runner)
        return dataframe

    def _export_chart(self, pair: str, runner: EngineRunner) -> None:
        """Uloží kresby behu, ak o to okolie požiadalo cez `IBS_DRAW_OUT`.

        Len v backteste: dry/live volá `populate_indicators` každú sviečku a hyperopt
        stokrát za sebou s inými parametrami — tam by súbor nemal zmysel.
        """
        out = os.environ.get(DRAW_OUT_ENV)
        if not out:
            return
        from freqtrade.enums import RunMode

        if self.config.get("runmode") not in (RunMode.BACKTEST, RunMode.PLOT):
            return
        path = out.replace("{pair}", pair.replace("/", "_").replace(":", "_"))
        try:
            head = export_chart(runner, pair, self.timeframe, path)
        except OSError as exc:  # pragma: no cover - plný disk, zlá cesta
            logger.warning("IBS %s: kresby sa nepodarilo uložiť do %s: %s", pair, path, exc)
            return
        logger.info(
            "IBS %s: kresby ulozene do %s (%d objektov)",
            pair, path, sum(head["counts"].values()),
        )

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Tag nesie čas baru signálu — jediný spoľahlivý kľúč späť na `SignalRow`.
        tags = Series(
            [f"{ENTRY_TAG_PREFIX}{ts}" for ts in _ts_ms(dataframe["date"])],
            index=dataframe.index,
        )
        long = dataframe["ibs_enter_long"] == 1
        dataframe.loc[long, "enter_long"] = 1
        dataframe.loc[long, "enter_tag"] = tags[long]
        if self.can_short:
            short = dataframe["ibs_enter_short"] == 1
            dataframe.loc[short, "enter_short"] = 1
            dataframe.loc[short, "enter_tag"] = tags[short]
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Výstupy rieši custom_roi (TP) a custom_stoploss (SL) per obchod.
        return dataframe

    # ------------------------------------------------------------------ #
    # SL / TP / veľkosť - všetko per obchod, z plánu, ktorý spočítal engine
    # ------------------------------------------------------------------ #

    @staticmethod
    def _tag_ts(tag) -> int | None:
        """``ibs:<ms>`` → ms, inak `None` (force entry, starý obchod bez tagu)."""
        if not isinstance(tag, str) or not tag.startswith(ENTRY_TAG_PREFIX):
            return None
        try:
            return int(tag[len(ENTRY_TAG_PREFIX):])
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
        """(SL, TP) zo signálu, na ktorom obchod vznikol."""
        row = self._trade_signal(pair, trade)
        if row is None or row.stop_loss != row.stop_loss:  # NaN check
            return None
        return row.stop_loss, row.take_profit

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

    def _detail_close(self, pair: str, when) -> float | None:
        """Zatváracia cena sviečky, ktorú Freqtrade práve testuje.

        `custom_stoploss` dostane open, high aj low, ale nie close — a bez neho sa
        nedá dopočítať spiatočná noha baru (viď `_trailing_stop`). Sviečky sa preto
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
        """Limitka presne na cene gapu — Pine `strategy.entry(limit=entryPrice)`."""
        row = self._signal(pair, current_time, entry_tag)
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
        row = self._signal(pair, current_time, entry_tag)
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
        """Absolútny SL z plánu, posunutý trailingom. Prepočet na relatívnu hodnotu rieši
        `stoploss_from_absolute`, aby sa nemuselo ručne riešiť znamienko pre shorty ani páka.

        `trade.max_rate`/`min_rate` aktualizuje Freqtrade v `should_exit()` **pred** týmto
        volaním, takže extrém už zahŕňa aktuálnu sviečku — rovnako ako offline simulácia
        v `ibs.tools.scan_trades`. S `--timeframe-detail 1m` je teda trailing po minútach.
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
        row = self._signal(pair, current_time, entry_tag)
        return True if row is None else row.in_trade_window

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
        """Páka z profilu, orezaná tým, čo burza dovolí.

        Pri páke 1 sa risk-based sizing na BTC nezmestí do peňaženky a `maxLossDollar`
        sa ticho neuplatní — viď `IBSConfig.leverage`.
        """
        return min(float(self.ibs_cfg.leverage), max_leverage)
