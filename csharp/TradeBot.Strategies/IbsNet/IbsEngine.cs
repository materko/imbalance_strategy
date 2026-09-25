// `IbsEngine` - jeden vstupny bod strategie IBSNet: spaja hodiny, detekciu zon a stavovy automat
// do jedineho volania `OnBar`. Zrkadlo `tradebot/strategies/ibs/engine.py`; logika je prepis IBS
// (Pine `imbalance_strategy_FULL.pine`) a s Python enginom sa porovnava bar po bare.
//
// Engine je CISTY: ziadne I/O, ziadny globalny stav - preto ten isty kod bezi v NinjaTraderi
// aj pod Freqtrade (cez most) a dava rovnake signaly.
using System;
using System.Collections.Generic;
using TradeBot.Core;
using TradeBot.Strategies.IbsNet.Ta;

namespace TradeBot.Strategies.IbsNet
{
    [TradeBotEngine("ibsnet", "IBSNet Imbalance Breakout (C#)")]
    public sealed class IbsEngine : IEngine
    {
        public readonly IbsConfig Cfg;
        private readonly InstrumentSpec _inst;
        private readonly int _chartTfMinutes;
        private readonly long _stepMs;

        public readonly SessionClock Clock;
        public readonly ZoneBook Book;
        public readonly StateMachine Machine;
        public readonly MarketStructure Structure;
        public readonly SupportResistance Sr;
        public readonly LiquiditySweep Liquidity;
        public readonly ElliottWaves Elliott;
        public readonly DirectionGate Gate;
        public readonly BarHistory History;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;

        /// <summary>Pine `inTradeWindow[1]` - na detekciu konca seansy.</summary>
        private bool _wasInTradeWindow;

        public IbsEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(IbsConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public IbsEngine(IbsConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            Cfg = cfg;
            _inst = inst;
            _chartTfMinutes = chartTfMinutes;
            _stepMs = chartTfMinutes * 60000L;

            Clock = cfg.BuildClock();
            Book = new ZoneBook(cfg, inst, chartTfMinutes);
            Machine = new StateMachine(cfg, inst, Book);
            Structure = new MarketStructure(cfg, inst);
            Sr = new SupportResistance(cfg, inst);
            Liquidity = new LiquiditySweep(cfg, inst);
            Elliott = new ElliottWaves(cfg, inst, _stepMs);
            Gate = new DirectionGate(cfg, chartTfMinutes);
            Machine.DirectionGate = Gate;

            int lookback = Math.Max(Math.Max(cfg.imbLookback, cfg.slLookback), Math.Max(cfg.volSmaLen, cfg.engSizeAvgLen)) + 64;
            History = new BarHistory(lookback, cfg.atrLen);
            // Predhistoria grafu = okno historie; smerove indikatory maju vlastnu (seeding).
            _warmup = Gate.AddWarmup(new Warmup(chartTfMinutes).Add("okno historie", lookback));
            _requiredHistory = _warmup.ChartBars;
        }

        public InstrumentSpec Inst { get { return _inst; } }
        public int ChartTfMinutes { get { return _chartTfMinutes; } }
        public int RequiredHistory { get { return _requiredHistory; } }
        public Warmup Warmup { get { return _warmup; } }

        public IHtfFeeder CreateHtfFeeder() { return new HtfFeeder(Cfg, _chartTfMinutes); }

        public Dictionary<string, double> Stats()
        {
            Dictionary<string, double> s = new Dictionary<string, double>();
            s["zones"] = Book.Count;
            s["max_zones"] = Book.MaxZones;
            s["evicted"] = Book.Evicted;
            s["evicted_alive"] = Book.EvictedAlive;
            s["max_daily_wins"] = Cfg.maxDailyWins;
            s["state5_max_bars"] = Cfg.state5MaxBars;
            s["close_at_session_end"] = Cfg.closeAtSessionEnd ? 1 : 0;
            s["leverage"] = Cfg.leverage;
            return s;
        }

        // ------------------------------------------------------------------ //

        /// <summary>Pine `f_maybeSpawnSrZone` (riadok 911): ked uroven PRVYKRAT dosiahne `srMinTouches`,
        /// vznikne z nej obchodovatelna zona. Smer je dynamicky: cena nad urovnou = support = LONG.</summary>
        private void SpawnSrZones(List<int> touched, Bar bar, EngineOutput o)
        {
            foreach (int idx in touched)
            {
                if (idx < 0 || idx >= Sr.Levels.Count) continue;
                SrLevel lvl = Sr.Levels[idx];
                if (lvl.ZoneSpawned || lvl.Touches < Cfg.srMinTouches) continue;
                double lo = lvl.Low, hi = lvl.High;
                if (lo == hi)
                {
                    lo -= _inst.TickSize * 2;
                    hi += _inst.TickSize * 2;
                }
                Direction direction = bar.Close > (lo + hi) / 2 ? Direction.Long : Direction.Short;
                Zone zone = Book.CreateRaw(direction, hi, lo, bar.Time, ZoneSource.Sr);
                zone.CreatedBarIndex = History.BarIndex;
                lvl.ZoneSpawned = true;
                o.Drawings.AddRange(zone.Boxes(_stepMs));
            }
        }

        /// <summary>Pine 682-701 - box na sviecke, ktora vytvorila gap. NEZAVISLE od zon; kresli sa na telo
        /// PROSTREDNEJ sviecky (doji sa rozsiri o pol ticku).</summary>
        private void DrawImbalanceCandle(EngineOutput o, double atr)
        {
            if (!Cfg.showImbalance || !History.Has(2)) return;
            Bar near = History[0], mid = History[1], far = History[2];
            double minImb = Cfg.minImbSizePoints.Resolve(_inst, near.Close, atr);
            bool bull = near.Low > far.High && mid.Close > far.High && (near.Low - far.High) >= minImb;
            bool bear = near.High < far.Low && mid.Close < far.Low && (far.Low - near.High) >= minImb;
            if (!(bull || bear)) return;

            double top = Math.Max(mid.Open, mid.Close), bot = Math.Min(mid.Open, mid.Close);
            if (top == bot)
            {
                double t = top;
                top = t + _inst.TickSize * 0.5;
                bot = t - _inst.TickSize * 0.5;
            }
            DrawBox box = new DrawBox(IbsKinds.ImbBox, mid.Time, top, mid.Time + _stepMs, bot, bull ? Palette.Strong : Palette.Long);
            box.ObjId = "imb." + mid.Time;
            o.Drawings.Add(box);
        }

        /// <summary>Pine 1198-1247 - fade po sweepe, obchod ide PROTI prepichnutiu.</summary>
        private void SpawnSweepZones(List<Sweep> sweeps, Bar bar, EngineOutput o)
        {
            foreach (Sweep sw in sweeps)
            {
                Zone zone = Book.CreateRaw(sw.Direction, sw.Top, sw.Bot, bar.Time, ZoneSource.Liquidity);
                zone.CreatedBarIndex = History.BarIndex;
                o.Drawings.AddRange(zone.Boxes(_stepMs));
            }
        }

        public List<DrawCommand> FinalDrawings(Bar bar)
        {
            List<DrawCommand> list = new List<DrawCommand>();
            list.AddRange(Sr.Render(bar));
            list.AddRange(Elliott.Render(bar, History));
            return list;
        }

        /// <summary>Spracuje jeden uzavrety bar. `htf` sa odovzdava LEN na bare, kde sa prave uzavrela nova
        /// perioda detekcneho TF - vtedy Pine hlada pattern (`first5mTick`). Inokedy null.</summary>
        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            History.Append(bar);
            ClockState state = Clock.State(bar.Time);
            // Parametre v jednotke `atr` sa prepocitavaju z ATR grafoveho TF.
            double atr = History.Atr;
            bool wasInWindow = _wasInTradeWindow;

            if (ctx == null) ctx = new MarketContext();
            ctx.InTradeWindow = state.InTradeWindow;

            EngineOutput o = new EngineOutput();
            o.Clock = state;
            o.Drawings.AddRange(state.Backgrounds(bar.Time, _stepMs));
            DrawImbalanceCandle(o, atr);
            // Market Structure bezi vzdy - `marketBias` z neho cita filter `useStructureFilter`.
            o.Drawings.AddRange(Structure.OnBar(bar, History));
            ctx.MarketBias = Structure.Bias;

            // S/R zbiera dotyky priebezne, ale kresli sa az vo `FinalDrawings()`.
            List<int> touched = Sr.OnBar(bar, History);
            if (Cfg.enableSrTrading && state.InZoneWindow) SpawnSrZones(touched, bar, o);

            LiquidityResult liq = Liquidity.OnBar(bar, History);
            o.Drawings.AddRange(liq.Drawings);
            if (state.InZoneWindow) SpawnSweepZones(liq.Sweeps, bar, o);

            Elliott.OnBar(bar, History);
            o.Drawings.AddRange(Gate.OnBar(bar));

            if (htf != null && state.InZoneWindow)
            {
                SdPattern pattern = ZoneDetection.DetectSdPattern(htf, Cfg, _inst, atr);
                if (pattern != null)
                {
                    Zone zone = Book.CreateFromPattern(pattern, bar.Time);
                    if (zone != null)
                    {
                        zone.CreatedBarIndex = History.BarIndex;
                        o.Drawings.AddRange(zone.Boxes(_stepMs));
                    }
                }
            }

            o.Orders = Machine.OnBar(bar, History, ctx, atr);
            if (wasInWindow && !state.InTradeWindow) Machine.CutFormingZones(bar);
            if (Cfg.closeAtSessionEnd && state.NoMoreSessionsToday && !state.InTradeWindow)
            {
                o.Orders.AddRange(Machine.CloseSession(bar, ctx));
                o.CloseSession = true;
            }
            // Pine `box.set_*` z tohto baru (zmensenie pri invalidacii, prefarbenie).
            o.Drawings.AddRange(Machine.Drawings);
            o.Events = new List<StateEvent>(Machine.Events);

            _wasInTradeWindow = state.InTradeWindow;
            return o;
        }
    }
}
