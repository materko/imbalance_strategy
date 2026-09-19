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
from typing import ClassVar

from pandas import DataFrame, Series

from freqtrade.strategy import IStrategy

from tradebot.core import Bar, load_profile
from tradebot.core.candles import timeframe_minutes
from tradebot.core.env import getenv
from tradebot.core.risk import extreme_before_stop
from tradebot.core.types import Direction
from tradebot.strategies import StrategySpec, get_spec

from . import hyperplan
from .ai import AIMixin, settings_of as ai_settings
from .callbacks import CallbacksMixin
from .frames import _ts_ms
from .live import LiveMixin
from .runner import COLUMN_ATTRS, EngineRunner, SignalRow, export_chart
from .timeframes import TimeframesMixin

logger = logging.getLogger(__name__)

__all__ = ["TradebotStrategyBase", "_ts_ms", "_bar"]


def _decimals(step: float) -> int:
    """0.01 -> 2, 1.0 -> 0 — presnosť ako počet desatinných miest (ccxt DECIMAL_PLACES)."""
    text = f"{step:.10f}".rstrip("0")
    return len(text.partition(".")[2])


def _bar(row, ts: int) -> Bar:
    return Bar(
        time=ts,
        open=float(row.open),
        high=float(row.high),
        low=float(row.low),
        close=float(row.close),
        volume=float(row.volume),
    )


class TradebotStrategyBase(CallbacksMixin, LiveMixin, TimeframesMixin, AIMixin, IStrategy):
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
        #: (pár, prvý bar, rozsah) -> sviečky pred behom na seeding indikátorov (hyperopt
        #: stavia runner každú epochu nanovo, disk sa číta raz)
        self._seed_frames: dict[tuple, DataFrame | None] = {}
        #: dry/live: (pár, od, do) -> sviečky TF behu stiahnuté z burzy na seeding (len pri štarte runnera)
        self._seed_downloads: dict[tuple, DataFrame | None] = {}
        self._informative_tfs: list[str] = (
            list(self.spec.informative_tfs(self.tb_cfg)) if self.spec.informative_tfs else []
        )
        # Chýbajúce sviečky treba doplniť TERAZ: `Backtesting.start()` si dáta načíta skôr,
        # než zavolá čokoľvek iné zo stratégie (`bot_start` je už neskoro). Timeframe sa
        # berie z configu (`--timeframe`), nie z atribútu triedy — ten Freqtrade prepíše
        # až po vytvorení inštancie, takže tu by ešte držal východiskových 3m.
        run_tf = self.run_timeframe
        for pair in self.config.get("exchange", {}).get("pair_whitelist", []):
            for tf in (run_tf, *self._informative_tfs):
                self.ensure_timeframe(pair, tf)

        # Freqtrade potrebuje vedieť, koľko sviečok histórie stratégia chce pred prvým signálom.
        # Skúšobný engine MUSÍ mať TF behu, nie default triedy: indikátor na 5m by na 3m
        # grafe neprešiel kontrolou násobku. Indikátory na vlastnom TF (Supertrend 60m) sa
        # do `startup_candle_count` nepočítajú — dostanú svoje bary cez `_seed_runner`.
        probe = self.spec.engine_factory(self.tb_cfg, self.tb_inst, timeframe_minutes(run_tf))
        self.startup_candle_count = max(int(type(self).startup_candle_count), int(probe.required_history))
        warmup = getattr(probe, "warmup", None)
        #: TF (minúty) indikátorov s vlastnou predhistóriou — dry/live si ich pýta cez `informative_pairs`
        self._seed_tfs: list[int] = sorted({n.tf_minutes for n in warmup.seeds}) if warmup is not None else []
        logger.info("%s: startup_candle_count %d na %s (engine %d%s)", self.spec.key,
                    self.startup_candle_count, run_tf, int(probe.required_history),
                    f": {warmup.describe()}" if warmup is not None else "")
        self._after_profile()

    @property
    def run_timeframe(self) -> str:
        """TF behu. V `__init__` drží atribút triedy ešte default (Freqtrade ho z configu
        prepíše až po vytvorení inštancie), preto má prednosť `config["timeframe"]`."""
        return (getattr(self, "config", None) or {}).get("timeframe") or self.timeframe

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
        """`base_stop` posunutý trailingom z plánu obchodu (`TradePlan.trailing`).

        Spoločné pre všetky stratégie: engine trailing vloží do plánu (aktivácia a odstup
        v cenových bodoch, prípadne vlastný `stop_price` ako `TwoStageTrailing`) a tu sa
        len uplatní — žiadna stratégia ho nemusí stavať druhýkrát z configu. Plán bez
        trailingu (vypnutý prepínač) vráti `base_stop`.

        Extrém od vstupu sa vedie po sviečkach, ktoré Freqtrade testuje (s
        `--timeframe-detail 1m` po minútach), a poradie extrémov vnútri sviečky rozhoduje
        `extreme_before_stop` — pravidlo broker emulátora TradingView:

        * priaznivý extrém prvý → stop sa posunie a Freqtrade ho hneď otestuje proti low
          (resp. high) tej istej sviečky;
        * nepriaznivý extrém prvý → platí ešte starý stop; Freqtrade vie proti low otestovať
          len jednu hodnotu, takže spiatočná noha sviečky sa testuje tu proti `close` a keď
          neprejde, vráti sa starý stop (low ho už netrafil).

        Tento fill model je Freqtrade vetvy. MultiCharts runner prepočíta stop z toho istého
        plánu na close baru grafu a pošle ho na ďalší bar (`MCRunner._trailed_stop`).
        """
        row = self._trade_signal(pair, trade)
        if row is None or row.trailing is None or row.entry != row.entry:
            return base_stop
        trail = row.trailing
        if base_stop != row.stop_loss and row.stop_loss == row.stop_loss:
            # AI vrstva posunula stop (`_levels`) — trailing viazaný na riziko ide s ním
            risk = abs(row.entry - row.stop_loss)
            if risk > 0:
                trail = trail.scaled(abs(row.entry - base_stop) / risk)

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
            return after_stop
        if (low <= before_stop) if long else (high >= before_stop):
            return before_stop
        close = self._detail_close(pair, self._candle_time)
        if close is None:
            return after_stop
        crossed = close <= after_stop if long else close >= after_stop
        return after_stop if crossed else before_stop

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


    def _config_fingerprint(self) -> str:
        """Odtlačok parametrov, ktoré menia výsledok.

        Runner je zámerne inkrementálny (dry/live ho volá nad rastúcim DataFrame),
        takže si medzi volaniami drží stav. Pri hyperopte sa ale parametre menia
        medzi epochami a starý runner by ticho počítal so starými — preto sa pri
        zmene odtlačku zahodí a postaví nanovo.
        """
        return json.dumps(self.tb_cfg.to_dict(), sort_keys=True, default=str)

    def _runner(self, pair: str, fresh: bool = False) -> EngineRunner:
        fp = self._config_fingerprint()
        if fp != self._runner_fp:
            self._runners.clear()
            self._runner_fp = fp
        runner = None if fresh else self._runners.get(pair)
        if runner is None:
            runner = EngineRunner(self.tb_cfg, self.tb_inst, timeframe_minutes(self.run_timeframe),
                                  spec=self.spec, fee=float(self.config.get("fee") or 0.0))
            runner.min_history = int(self.startup_candle_count or 0)
            self._runners[pair] = runner
        return runner


    # ------------------------------------------------------------------ #

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata["pair"]
        self._apply_hyperopt_params()
        runner = self._runner(pair)
        ts_index = _ts_ms(dataframe["date"])
        if self.live_mode and self._live_gap(runner, pair, ts_index):
            runner = self._runner(pair, fresh=True)
        self._feed_informative(runner, pair)

        start = 0
        if runner.last_ts is None and ts_index:
            start = self._seed_runner(runner, pair, ts_index)
        for ts, row in zip(ts_index[start:], dataframe.iloc[start:].itertuples(index=False)):
            if runner.last_ts is not None and ts <= runner.last_ts:
                continue  # už spracované - runner je inkrementálny
            runner.process(_bar(row, ts), runner.window_for(ts))

        rows = runner.rows
        empty = SignalRow()
        for col, attr in COLUMN_ATTRS.items():
            dataframe[col] = [getattr(rows.get(ts, empty), attr) for ts in ts_index]
        if self.live_mode:
            # Predhistóriu grafu (`startup_candle_count`) backtest oreže Freqtrade sám. V dry/live
            # ju neoreže nikto: signál z baru, pred ktorým runner nemá celú predhistóriu (krátky
            # DataFrame po listingu, prvé cykly po prestavaní runnera), vstup urobiť nesmie.
            warming = [not runner.ready_at(ts) for ts in ts_index]
            if any(warming):
                dataframe.loc[warming, ["tb_enter_long", "tb_enter_short"]] = 0

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

