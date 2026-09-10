"""Freqtrade adaptér — generická vrstva nad enginom ľubovoľnej stratégie z registry.

Žiadna logika stratégie tu nie je. Adaptér len:
  1. dotiahne informatívne sviečky, ktoré stratégia potrebuje (IBS: detekčný TF zón),
  2. prebehne engine cez DataFrame a zapíše signály do stĺpcov `tb_*`,
  3. preloží ich na Freqtrade entry/exit, SL, TP a veľkosť pozície.

Konkrétna stratégia je podtrieda so `STRATEGY_KEY` (viď `tradebot/strategies/ibs/freqtrade.py`)
a prepíše len to, čo je jej vlastné: hyperopt priestor, plnenie HTF, trailing, výstup na
konci seansy. Freqtrade resolver navyše vyžaduje shim vo `user_data/strategies/<Trieda>.py`.

Nastavenia stratégie sa berú z profilu (`tradebot/strategies/<stratégia>/configs/*.json` alebo cesta),
**nie** z Freqtrade configu. Profil sa volí cez `TRADEBOT_PROFILE` v prostredí.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from pandas import DataFrame, Series

from freqtrade.strategy import IStrategy, stoploss_from_absolute

from tradebot.core import Bar, load_profile
from tradebot.core.candles import resample_ohlcv, timeframe_minutes
from tradebot.core.derived import remember
from tradebot.core.env import getenv
from tradebot.strategies import StrategySpec, get_spec

from . import hyperplan
from .ai import AIMixin, settings_of as ai_settings
from .runner import COLUMN_ATTRS, EngineRunner, SignalRow, export_chart

logger = logging.getLogger(__name__)

__all__ = ["TradebotStrategyBase", "_ts_ms", "_bar"]


#: Freqtrade si z nášho stake spätne dopočíta množstvo ako ``stake / cena * páka``
#: a výsledok **oreže** na krok kontraktu. Delenie a násobenie tou istou cenou ale
#: v plávajúcej rádovej čiarke presné nie je: 1 BTC pri 79 419,5 sa vráti ako
#: 0,9999999999999999 a z toho je po orezaní 0,999 — teda o krok menšia pozícia, než
#: plán žiada. Na piatich obchodoch golden testu to robilo rozdiel 0,26 USD oproti
#: TradingView. Zlomok promile navyše chybu prekryje a na veľkosť pozície vplyv nemá:
#: krok kontraktu je o desať rádov väčší.
_STAKE_EPS = 1e-12


def _decimals(step: float) -> int:
    """0.01 -> 2, 1.0 -> 0 — presnosť ako počet desatinných miest (ccxt DECIMAL_PLACES)."""
    text = f"{step:.10f}".rstrip("0")
    return len(text.partition(".")[2])


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


class TradebotStrategyBase(AIMixin, IStrategy):
    """Spoločné správanie pre všetky stratégie TradeBotu vo Freqtrade."""

    #: kľúč v `tradebot.strategies.STRATEGIES`
    STRATEGY_KEY: ClassVar[str] = ""
    #: `enter_tag` obchodu je ``<prefix><čas baru signálu v ms>``. Vďaka tomu každý
    #: `custom_*` callback vie PRESNE, z ktorého signálu obchod vznikol — hľadať
    #: „posledný signál pred otvorením" zlyhá, keď engine vygeneruje ďalší signál
    #: na sviečke, na ktorej Freqtrade obchod otvára (viď `EngineRunner.signal_at`).
    ENTRY_TAG_PREFIX: ClassVar[str] = "tb:"

    INTERFACE_VERSION = 3

    timeframe = "3m"
    #: Pozor: limity `*MaxBars` sú v BAROCH, nie v minútach (ARCHITECTURE_port.md §7).
    #: 1m je len detail fillov.
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

    def __init_subclass__(cls, **kwargs) -> None:
        """Doplní na triedu hyperopt parametre z plánu (`TRADEBOT_HYPEROPT_PLAN`).

        Musí to byť tu, pri vzniku triedy: Freqtrade hľadá parametre v atribútoch až
        keď triedu dostane od resolvera, ale robí to na hotovej triede — takže parameter
        prilepený pri importe je preň nerozoznateľný od napísaného v tele triedy.
        Bez plánu sa nedeje nič a ladí sa priestor napísaný v stratégii.
        """
        super().__init_subclass__(**kwargs)
        installed = hyperplan.install(cls)
        if installed:
            logger.info("hyperopt plan: %s -> priestor %r", ", ".join(installed), hyperplan.SPACE)

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.spec: StrategySpec = get_spec(self.STRATEGY_KEY)
        profile = getenv("PROFILE", self.spec.default_profile) or self.spec.default_profile
        self.tb_cfg, self.tb_inst = load_profile(profile, strategy=self.spec.key, engine="freqtrade")
        for w in self.tb_cfg.check_instrument(self.tb_inst):
            logger.warning("%s config: %s", self.spec.key, w)
        self._runners: dict[str, EngineRunner] = {}
        self._runner_fp: str | None = None
        #: (pár, čas vstupu) -> najlepšia dosiahnutá cena, vstup do trailingu.
        self._extremes: dict[tuple, float] = {}
        #: OHLC práve spracúvanej sviečky, zachytené v `ft_stoploss_adjust`.
        self._candle: tuple = (None, None, None)
        self._candle_time = None
        #: pár -> {čas sviečky v ms: close}; dopĺňa sa lenivo.
        self._closes: dict[str, dict[int, float]] = {}
        self._informative_tfs: list[str] = (
            list(self.spec.informative_tfs(self.tb_cfg)) if self.spec.informative_tfs else []
        )
        # Chýbajúce sviečky treba doplniť TERAZ: `Backtesting.start()` si dáta načíta skôr,
        # než zavolá čokoľvek iné zo stratégie (`bot_start` je už neskoro). Timeframe sa
        # berie z configu (`--timeframe`), nie z atribútu triedy — ten Freqtrade prepíše
        # až po vytvorení inštancie, takže tu by ešte držal východiskových 3m.
        run_tf = self.config.get("timeframe") or self.timeframe
        for pair in self.config.get("exchange", {}).get("pair_whitelist", []):
            for tf in (run_tf, *self._informative_tfs):
                self.ensure_timeframe(pair, tf)

        # Freqtrade potrebuje vedieť, koľko sviečok histórie stratégia chce pred prvým signálom.
        probe = self.spec.engine_factory(self.tb_cfg, self.tb_inst, timeframe_minutes(self.timeframe))
        self.startup_candle_count = max(int(type(self).startup_candle_count), int(probe.required_history))
        self._after_profile()

    # ------------------------------------------------------------------ #
    # Inštrument, ktorý na burze neexistuje (Dukascopy CFD)
    # ------------------------------------------------------------------ #

    def bot_start(self, **kwargs) -> None:
        """Doplní Freqtradu market info pre pár, ktorý nosná burza nepozná.

        Dukascopy CFD (NAS100, forex, komodity) nie sú burza v ccxt, takže sa beh vezie
        na burze, od ktorej potrebujeme len quote menu a timeframe (`config.dukascopy.json`).
        Pri vstupe do obchodu si však Freqtrade pýta `exchange.markets[pair]` — presnosť
        ceny, krok množstva a limity — a bez neho padne na „Can't get market information
        for symbol …". Tie čísla máme v `InstrumentSpec` a sú **presnejšie**, než keby sme
        ich požičali od cudzieho páru.

        Robí sa to len pre inštrument mimo burzy (`venue="multicharts"`) a len pre pár,
        ktorý na nosnej burze naozaj nie je — skutočný trh sa nikdy neprepisuje.
        """
        exchange = getattr(self.dp, "_exchange", None) if self.dp else None
        if exchange is None or self.tb_inst.venue != "multicharts":
            return
        markets = getattr(exchange, "_markets", None)
        if markets is None:
            return
        for pair in self.config.get("exchange", {}).get("pair_whitelist", []):
            if pair in markets:
                continue
            markets[pair] = self._synthetic_market(pair, exchange)
            logger.warning(
                "%s nie je na burze %s - market info doplnene z instrumentu %s "
                "(tick %g, krok mnozstva %g, min %g). Poplatok musis zadat sam (--fee), "
                "z burzy sa nema odkial vziat.",
                pair, self.config.get("exchange", {}).get("name"), self.tb_inst.symbol,
                self.tb_inst.tick_size, self.tb_inst.qty_step, self.tb_inst.min_qty,
            )

    def _synthetic_market(self, pair: str, exchange) -> dict:
        """Market podľa `InstrumentSpec` v tvare, aký čaká ccxt/Freqtrade."""
        base, _, quote = pair.partition("/")
        inst = self.tb_inst
        # ccxt: TICK_SIZE (4) berie presnosť ako krok, ostatné režimy ako počet desatinných miest
        tick_size_mode = getattr(exchange, "precisionMode", None) == 4
        price_prec = inst.tick_size if tick_size_mode else _decimals(inst.tick_size)
        amount_prec = inst.qty_step if tick_size_mode else _decimals(inst.qty_step)
        return {
            "id": pair.replace("/", ""), "symbol": pair, "base": base, "quote": quote,
            "type": "spot", "spot": True, "margin": False, "swap": False, "future": False,
            "option": False, "contract": False, "contractSize": None, "active": True,
            "precision": {"price": price_prec, "amount": amount_prec},
            "limits": {
                "amount": {"min": inst.min_qty, "max": None},
                "price": {"min": None, "max": None},
                "cost": {"min": None, "max": None},
                "leverage": {"min": 1.0, "max": 1.0},
            },
            # Poplatok CFD brokera nemá s nosnou burzou nič spoločné - zadáva sa cez
            # `--fee`; nula tu je len preto, aby `get_fee()` nespadlo, keď sa zabudne.
            "taker": 0.0, "maker": 0.0,
            "info": {"tradebot": "synteticky market z InstrumentSpec, nie z burzy"},
        }

    # ------------------------------------------------------------------ #
    # Háky pre stratégiu
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    # Chýbajúci timeframe si stratégia dopočíta z 1m
    # ------------------------------------------------------------------ #

    def ensure_timeframe(self, pair: str, timeframe: str) -> bool:
        """Postará sa, aby pre `pair` a `timeframe` boli sviečky na disku. Vráti, či sú.

        Freqtrade si vyšší TF **nedopočíta**: pre základný TF behu skončí na „No history …
        found", informatívny TF ticho vráti prázdny DataFrame (a stratégia potom nevytvorí
        ani jednu zónu). Chýbajúci TF sa preto poskladá z 1m — z toho istého zdroja a tým
        istým pravidlom (`tradebot.core.candles.resample_ohlcv`), aké používa graf webapp
        aj emulátor MultiCharts, takže bary sú všade rovnaké.

        Číta aj zapisuje **cez dátový handler Freqtradu**, takže pomenovanie súboru,
        formát aj `futures/` podadresár sú jeho (nič sa tu o cestách nehádže).

        Volá sa v `__init__`, teda **pred** tým, než si Freqtrade načíta dáta backtestu
        (`Backtesting.start` → `load_bt_data`), a ešte raz lenivo pri informatívnom TF.
        """
        if not self._may_derive():
            return True
        source_tf = "1m"
        try:
            from freqtrade.data.history import get_datahandler

            handler = get_datahandler(
                Path(self.config["datadir"]), self.config.get("dataformat_ohlcv", "feather")
            )
            candle_type = self.config.get("candle_type_def", "")
            have = handler.ohlcv_load(pair, timeframe, candle_type=candle_type, warn_no_data=False)
            if not have.empty:
                return True
            if timeframe == source_tf:
                return False
            minutes = timeframe_minutes(timeframe)
            base = handler.ohlcv_load(pair, source_tf, candle_type=candle_type, warn_no_data=False)
            if base.empty:
                logger.warning(
                    "%s %s: chyba %s aj %s - dopocitat sa nema z coho", self.spec.key, pair,
                    timeframe, source_tf,
                )
                return False
            out = resample_ohlcv(base[["date", "open", "high", "low", "close", "volume"]], minutes)
            handler.ohlcv_store(pair, timeframe, data=out, candle_type=candle_type)
            path = handler._pair_data_filename(
                Path(self.config["datadir"]), pair, timeframe, candle_type
            )
            remember([path])
            logger.warning(
                "%s %s: %s sviecky na disku neboli, poskladal som ich z %s (%d barov, %s). "
                "Su odvodene - do archivu nejdu.",
                self.spec.key, pair, timeframe, source_tf, len(out), path.name,
            )
            return True
        except Exception as exc:  # noqa: BLE001  (dopocet je pomoc, nie podmienka behu)
            logger.warning("%s %s: %s sa dopocitat nepodarilo (%s)", self.spec.key, pair,
                           timeframe, exc)
            return False

    def _may_derive(self) -> bool:
        """Dopočítavať sa smie len tam, kde sa počíta z histórie.

        V dry/live behu prichádzajú sviečky z burzy a vymyslený bar by bol chyba, nie pomoc.
        """
        from freqtrade.enums import RunMode

        return self.config.get("runmode") in (
            RunMode.BACKTEST, RunMode.HYPEROPT, RunMode.PLOT, RunMode.UTIL_NO_EXCHANGE,
            RunMode.UTIL_EXCHANGE, RunMode.OTHER,
        )

    def informative_frame(self, pair: str, timeframe: str) -> DataFrame:
        """Sviečky informatívneho TF; keď súbor nie je, dopočítajú sa z 1m."""
        if self.dp is None:
            return DataFrame()
        frame = self.dp.get_pair_dataframe(
            pair=pair, timeframe=timeframe, candle_type=self.config.get("candle_type_def", ""),
        )
        if frame is not None and not frame.empty:
            return frame
        if not self.ensure_timeframe(pair, timeframe):
            return DataFrame()
        frame = self.dp.get_pair_dataframe(
            pair=pair, timeframe=timeframe, candle_type=self.config.get("candle_type_def", ""),
        )
        return frame if frame is not None else DataFrame()

    def _after_profile(self) -> None:
        """Volá sa po načítaní profilu (IBS: hodiny seáns, kontrola unfilledtimeout)."""

    def _apply_hyperopt_params(self) -> None:
        """Hodnoty aktuálnej epochy do configu.

        Čo sa ladí, hovorí plán testera (`TRADEBOT_HYPEROPT_PLAN`) — priestor sa v kóde
        stratégie nepíše. Bez plánu sa nedeje nič a hyperopt skončí na tom, že nemá čo
        ladiť; to je správna odpoveď, nie tichý beh s cudzími parametrami.
        """
        if not self.hyperopt_active:
            return
        plan = hyperplan.plan_from_env()
        if plan is not None and plan.strategy == self.spec.key:
            hyperplan.apply(self, plan)

    def _feed_informative(self, runner: EngineRunner, pair: str) -> None:
        """Dodá runneru informatívne sviečky (IBS: bary detekčného TF do `runner.htf`)."""

    def _trailing_stop(self, pair: str, trade, base_stop: float) -> float:
        """`base_stop` posunutý trailingom — stratégia bez trailingu vráti `base_stop`."""
        return base_stop

    def _log_populate(self, pair: str, dataframe: DataFrame, runner: EngineRunner) -> None:
        longs = int(dataframe["tb_enter_long"].sum())
        shorts = int(dataframe["tb_enter_short"].sum())
        logger.info("%s %s: %d barov, %d signalov (%d long / %d short)",
                    self.spec.key, pair, len(dataframe), longs + shorts, longs, shorts)

    # ------------------------------------------------------------------ #

    @property
    def hyperopt_active(self) -> bool:
        """Pri obyčajnom backteste sa profil z JSON nesmie prepísať defaultmi."""
        from freqtrade.enums import RunMode

        return self.config.get("runmode") is RunMode.HYPEROPT

    def informative_pairs(self):
        pairs = self.dp.current_whitelist() if self.dp else []
        return [(p, tf) for p in pairs for tf in self._informative_tfs]

    def _config_fingerprint(self) -> str:
        """Odtlačok parametrov, ktoré menia výsledok.

        Runner je zámerne inkrementálny (dry/live ho volá nad rastúcim DataFrame),
        takže si medzi volaniami drží stav. Pri hyperopte sa ale parametre menia
        medzi epochami a starý runner by ticho počítal so starými — preto sa pri
        zmene odtlačku zahodí a postaví nanovo.
        """
        return json.dumps(self.tb_cfg.to_dict(), sort_keys=True, default=str)

    def _runner(self, pair: str) -> EngineRunner:
        fp = self._config_fingerprint()
        if fp != self._runner_fp:
            self._runners.clear()
            self._runner_fp = fp
        runner = self._runners.get(pair)
        if runner is None:
            runner = EngineRunner(self.tb_cfg, self.tb_inst, timeframe_minutes(self.timeframe), spec=self.spec)
            self._runners[pair] = runner
        return runner

    # ------------------------------------------------------------------ #

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata["pair"]
        self._apply_hyperopt_params()
        runner = self._runner(pair)
        self._feed_informative(runner, pair)

        ts_index = _ts_ms(dataframe["date"])
        for ts, row in zip(ts_index, dataframe.itertuples(index=False)):
            if runner.last_ts is not None and ts <= runner.last_ts:
                continue  # už spracované - runner je inkrementálny
            runner.process(_bar(row, ts), runner.window_for(ts))

        rows = runner.rows
        empty = SignalRow()
        for col, attr in COLUMN_ATTRS.items():
            dataframe[col] = [getattr(rows.get(ts, empty), attr) for ts in ts_index]

        # AI vrstva ide AŽ TERAZ: príznaky aj nálepka stoja na tom, čo engine vypočítal
        # (signál a plán obchodu), takže bez `tb_*` stĺpcov by nemala z čoho vychádzať.
        dataframe = self._ai_step(dataframe, metadata, pair)

        self._log_populate(pair, dataframe, runner)
        self._export_chart(pair, runner)
        return dataframe

    def _ai_step(self, dataframe: DataFrame, metadata: dict, pair: str) -> DataFrame:
        """Model nad hotovými signálmi. Bez zapnutej AI vrstvy nerobí nič."""
        if not ai_settings(self.config):
            return dataframe
        freqai = getattr(self, "freqai", None)
        if freqai is None:      # pragma: no cover - config bez sekcie `freqai`
            logger.warning("%s: AI vrstva je zapnuta, ale Freqtrade nema `freqai` config",
                           self.spec.key)
            return dataframe
        # Keď sa model nenatrénuje (v okne bola len jedna trieda, málo nálepiek), FreqAI
        # to zahlási a predikcia v dataframe nie je. Vtedy sa NEFILTRUJE — model, ktorý
        # nevie, nemá právo vetovať, a beh má dobehnúť ako obyčajný.
        try:
            dataframe = freqai.start(dataframe, metadata, self)
        except (KeyError, ValueError) as exc:
            logger.warning("%s %s: AI vrstva sa nenatrenovala (%s) - bezi sa bez filtra",
                           self.spec.key, pair, exc)
            return dataframe
        self.ai_remember(pair, dataframe)
        dataframe, _ = self.ai_gate(dataframe, pair)
        return dataframe

    def _export_chart(self, pair: str, runner: EngineRunner) -> None:
        """Uloží kresby behu, ak o to okolie požiadalo cez `TRADEBOT_DRAW_OUT`.

        Len v backteste: dry/live volá `populate_indicators` každú sviečku a hyperopt
        stokrát za sebou s inými parametrami — tam by súbor nemal zmysel.
        `{pair}` v ceste sa nahradí párom (viac párov v jednom behu).
        """
        out = getenv("DRAW_OUT")
        if not out:
            return
        from freqtrade.enums import RunMode

        if self.config.get("runmode") not in (RunMode.BACKTEST, RunMode.PLOT):
            return
        path = out.replace("{pair}", pair.replace("/", "_").replace(":", "_"))
        try:
            head = export_chart(runner, pair, self.timeframe, path)
        except OSError as exc:  # pragma: no cover - plný disk, zlá cesta
            logger.warning("%s %s: kresby sa nepodarilo uložiť do %s: %s", self.spec.key, pair, path, exc)
            return
        logger.info("%s %s: kresby ulozene do %s (%d objektov)",
                    self.spec.key, pair, path, sum(head["counts"].values()))

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Tag nesie čas baru signálu — jediný spoľahlivý kľúč späť na `SignalRow`.
        prefix = self.ENTRY_TAG_PREFIX
        tags = Series([f"{prefix}{ts}" for ts in _ts_ms(dataframe["date"])], index=dataframe.index)
        long = dataframe["tb_enter_long"] == 1
        dataframe.loc[long, "enter_long"] = 1
        dataframe.loc[long, "enter_tag"] = tags[long]
        if self.can_short:
            short = dataframe["tb_enter_short"] == 1
            dataframe.loc[short, "enter_short"] = 1
            dataframe.loc[short, "enter_tag"] = tags[short]
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Výstupy rieši custom_roi (TP) a custom_stoploss (SL) per obchod.
        return dataframe

    # ------------------------------------------------------------------ #
    # SL / TP / veľkosť - všetko per obchod, z plánu, ktorý spočítal engine
    # ------------------------------------------------------------------ #

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
        sa qty prepočíta cez cenu (tú z plánu, rovnakú ako dá `custom_entry_price`)
        a páku. Späť si qty dopočíta ako ``stake / cena * páka`` a výsledok **oreže**
        na krok kontraktu — preto ten zlomok promile navyše, viď `_STAKE_EPS`.
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
        wanted = row.qty * nasobok * rate / max(leverage, 1.0) * (1.0 + _STAKE_EPS)
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
