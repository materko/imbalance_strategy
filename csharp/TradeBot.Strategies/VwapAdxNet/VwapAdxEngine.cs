// `VwapAdxEngine` - VWAP ADX Pullback s jadrom v C#. Zrkadlo `tradebot/strategies/vwapadx/engine.py`; s Python
// enginom sa porovnava bar po bare, na rovnost.
//
// Priebeh dna (casy CT), len long:
//   1. `rthStart` = prvy bar dna o `orStartHHMM` alebo neskor - novy opening range, vynuluju sa stavy.
//   2. VWAP (hlc3) ukotveny na `rthStart` alebo na polnoc CT (`SessionVwap` z jadra).
//   3. Po konci rangu, kym sa bar nezatvori v `exitHHMM`: zavretie nad high rangu = nabita; potom low <= VWAP = dotyk.
//   4. Signal: nabita + dotyk + zavretie nad VWAP + ADX > `adxMin` a ADX <= ADX predosleho baru, pozicia plocha,
//      menej nez `maxTrades` obchodov od `rthStart`. Po signali sa dotyk vynuluje.
//   5. Vstup market, TP = najvyssi high poslednych `tpBars` barov, SL = najnizsi low poslednych `slBars` barov.
//   6. Casovy exit na zavreti baru, ktory sa zatvara v `exitHHMM` alebo neskor (len pred 17:00 CT).
// ADX je Pine `ta.dmi(adxLen, adxLen)` - ta ista implementacia ako v IBSNet (`Dmi`).
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;
using TradeBot.Strategies.IbsNet;

namespace TradeBot.Strategies.VwapAdxNet
{
    [TradeBotEngine("vwapadxnet", "VWAP ADX Pullback (C#)")]
    public sealed class VwapAdxEngine : IEngine, IConfigured
    {
        private const string Ct = "America/Chicago";
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";
        private const string VwapColor = "#3b82f6";
        private const string RangeColor = "#f59e0b";
        private const int BoxBars = 30;
        /// <summary>VWAP sa kresli raz za tolko minut</summary>
        private const int VwapStepMin = 5;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly VwapAdxConfig _cfg;
        /// <summary>Config strategie - `EntryLayers.Wrap` z neho berie defaulty klucov, ktore profil nema.</summary>
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _chartTfMinutes;
        private readonly long _stepMs;
        private readonly TimeZoneInfo _zone;
        private readonly int _orS, _orE, _ex;
        public readonly SessionVwap Vwap;
        public readonly Dmi Dmi;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        public readonly BarHistory History;

        private int? _prevMin;
        private DateTime? _prevDay;
        private double? _prevAdx;
        private double? _orH, _orL;
        private long? _orStartMs;
        private bool _rangeDrawn;
        public bool Armed;
        public bool Touched;
        public int TradesToday;
        private bool _hasLastVwap;
        private long _lastVwapMs;
        private double _lastVwapValue;

        public VwapAdxEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(VwapAdxConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public VwapAdxEngine(VwapAdxConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _chartTfMinutes = Math.Max(1, chartTfMinutes);
            _stepMs = _chartTfMinutes * 60000L;
            _zone = TimeZones.Get(Ct);
            _orS = VwapAdxConfig.HhmmMinutes(cfg.orStartHHMM);
            _orE = VwapAdxConfig.HhmmMinutes(cfg.orEndHHMM);
            _ex = VwapAdxConfig.HhmmMinutes(cfg.exitHHMM);
            if (cfg.AnchorMidnight)
                Vwap = new SessionVwap(_chartTfMinutes, 0, 24 * 60, Ct, null, 64);
            else
                // zaciatok = koniec: cely den je jedna seansa, ktora sa nuluje na prvom bare o orStart alebo neskor
                Vwap = new SessionVwap(_chartTfMinutes, _orS, _orS, Ct, null, 64);
            Dmi = new Dmi(cfg.adxLen, cfg.adxLen);

            int n = Math.Max(cfg.tpBars, cfg.slBars);
            _warmup = new Warmup(_chartTfMinutes)
                .Add("ADX " + cfg.adxLen, Dmi.WarmupBars)
                .Add("TP/SL " + n + " barov", n);
            _requiredHistory = _warmup.ChartBars;
            History = new BarHistory(n + 16, 14);
        }

        public InstrumentSpec Inst { get { return _inst; } }
        public int ChartTfMinutes { get { return _chartTfMinutes; } }
        public int RequiredHistory { get { return _requiredHistory; } }
        public Warmup Warmup { get { return _warmup; } }
        public IHtfFeeder CreateHtfFeeder() { return null; }
        public List<DrawCommand> FinalDrawings(Bar bar) { return new List<DrawCommand>(); }

        public Dictionary<string, double> Stats()
        {
            Dictionary<string, double> s = new Dictionary<string, double>();
            s["max_trades"] = _cfg.maxTrades;
            s["leverage"] = _cfg.leverage;
            return s;
        }

        // ------------------------------------------------------------------ //

        private TradePlan Plan(Bar bar)
        {
            int nTp = Math.Min(_cfg.tpBars, History.Count), nSl = Math.Min(_cfg.slBars, History.Count);
            double tp = History[0].High;
            for (int i = 1; i < nTp; i++) tp = Math.Max(tp, History[i].High);
            double sl = History[0].Low;
            for (int i = 1; i < nSl; i++) sl = Math.Min(sl, History[i].Low);
            double entry = bar.Close;
            double slDistance = entry - sl;
            if (slDistance <= 0) return null;
            double qty = _cfg.riskDollar > 0 ? _cfg.PositionQty(_inst, _cfg.riskDollar, slDistance) : 1.0;
            if (qty <= 0) qty = _inst.MinQty != 0.0 ? _inst.MinQty : 1.0;
            return new TradePlan(Direction.Long, _inst.RoundPrice(entry), _inst.RoundPrice(sl), _inst.RoundPrice(tp),
                                 qty, slDistance, null);
        }

        private static List<string> SortedIds(MarketContext ctx)
        {
            List<string> ids = new List<string>(ctx.OpenOrderIds);
            ids.Sort(StringComparer.Ordinal);
            return ids;
        }

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            EngineOutput o = new EngineOutput();

            History.Append(bar);
            int idx = History.BarIndex;
            double? adx = Dmi.Push(bar);
            double? vw = Vwap.Push(bar);

            DateTime local = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            DateTime closeLocal = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time + _stepMs), _zone);
            int barMin = local.Hour * 60 + local.Minute;
            int closeMin = closeLocal.Hour * 60 + closeLocal.Minute;
            DateTime day = local.Date;
            bool newDay = !_prevDay.HasValue || day != _prevDay.Value;
            bool rthStart = barMin >= _orS && (newDay || (_prevMin.HasValue && _prevMin.Value < _orS));

            // ---- opening range ---------------------------------------------- //
            if (rthStart)
            {
                _orH = bar.High;
                _orL = bar.Low;
                Armed = Touched = false;
                TradesToday = 0;
                _orStartMs = bar.Time;
                _rangeDrawn = false;
                _hasLastVwap = false;
            }
            else if (_orS <= barMin && barMin < _orE && _orH.HasValue)
            {
                _orH = Math.Max(_orH.Value, bar.High);
                _orL = Math.Min(_orL.Value, bar.Low);
            }

            bool afterOr = barMin >= _orE && closeMin < _ex;
            bool adxOk = adx.HasValue && _prevAdx.HasValue && adx.Value > _cfg.adxMin && adx.Value <= _prevAdx.Value;

            if (afterOr && _orH.HasValue)
            {
                if (!Armed && bar.Close > _orH.Value) Armed = true;
                if (Armed && vw.HasValue && bar.Low <= vw.Value) Touched = true;
            }

            o.Drawings.AddRange(Draw(bar, barMin, vw));

            // ---- casovy exit -------------------------------------------------- //
            bool flat = ctx.PositionSize == 0.0;
            if (_cfg.useTimeExit && !flat && closeMin >= _ex && barMin < 17 * 60)
            {
                o.CloseSession = true;
                foreach (string orderId in SortedIds(ctx))
                    o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx, "časový exit"));
            }

            // ---- signal -------------------------------------------------------- //
            if (afterOr && Armed && Touched && vw.HasValue && bar.Close > vw.Value && adxOk
                && flat && TradesToday < _cfg.maxTrades)
            {
                Touched = false;   // dalsi obchod (ak je povoleny) potrebuje novy pullback
                TradePlan plan = Plan(bar);
                if (plan != null)
                {
                    TradesToday += 1;
                    OrderIntent intent = new OrderIntent(OrderAction.Entry, "va:" + idx.ToString(CultureInfo.InvariantCulture), idx,
                                                         "pullback k VWAP po prerazení rangu, ADX prestal rásť");
                    intent.Direction = Direction.Long;
                    intent.Plan = plan;
                    intent.OrderType = OrderType.Market;
                    o.Orders.Add(intent);
                    DrawLabel label = new DrawLabel(VwapAdxKinds.Entry, bar.Time, bar.Low, "LONG", "#ffffff");
                    label.Style = LabelStyles.Up;
                    label.Above = false;
                    label.BgColor = LongColor;
                    label.ObjId = "va_entry." + bar.Time.ToString(CultureInfo.InvariantCulture);
                    o.Drawings.Add(label);
                    o.Drawings.AddRange(TradeBoxes(bar, plan));
                }
            }

            _prevMin = barMin;
            _prevDay = day;
            _prevAdx = adx;
            return o;
        }

        // ------------------------------------------------------------------ //

        private List<DrawCommand> Draw(Bar bar, int barMin, double? vw)
        {
            List<DrawCommand> cmds = new List<DrawCommand>();
            bool inDay = _orS <= barMin && barMin < _ex;
            if (_cfg.showRange && !_rangeDrawn && barMin >= _orE && _orH.HasValue && _orStartMs.HasValue)
            {
                long right = _orStartMs.Value + (_ex - _orS) * 60000L;
                DrawBox box = new DrawBox(VwapAdxKinds.Range, _orStartMs.Value, _orH.Value, right, _orL.Value, RangeColor);
                box.FillColor = RangeColor + "18";
                box.BorderWidth = 1;
                box.ObjId = "va_range." + _orStartMs.Value.ToString(CultureInfo.InvariantCulture);
                cmds.Add(box);
                _rangeDrawn = true;
            }
            if (_cfg.showVwap && vw.HasValue && inDay && barMin % VwapStepMin == 0)
            {
                long end = bar.Time + _stepMs;
                bool had = _hasLastVwap;
                long prevMs = _lastVwapMs;
                double prevValue = _lastVwapValue;
                _hasLastVwap = true;
                _lastVwapMs = end;
                _lastVwapValue = vw.Value;
                if (had)
                {
                    DrawLine line = new DrawLine(VwapAdxKinds.Vwap, prevMs, prevValue, end, vw.Value, VwapColor);
                    line.ObjId = "va_vwap." + end.ToString(CultureInfo.InvariantCulture);
                    line.Text = "VWAP";
                    cmds.Add(line);
                }
            }
            return cmds;
        }

        private List<DrawCommand> TradeBoxes(Bar bar, TradePlan plan)
        {
            long right = bar.Time + BoxBars * _stepMs;
            List<DrawCommand> list = new List<DrawCommand>();
            string[] kinds = { DrawKinds.TpBox, DrawKinds.SlBox };
            double[] prices = { plan.TakeProfit, plan.StopLoss };
            string[] colors = { LongColor, ShortColor };
            for (int i = 0; i < 2; i++)
            {
                DrawBox box = new DrawBox(kinds[i], bar.Time, Math.Max(plan.Entry, prices[i]), right,
                                          Math.Min(plan.Entry, prices[i]), colors[i]);
                box.FillColor = colors[i] + "40";
                box.BorderWidth = 0;
                box.ObjId = "va" + bar.Time.ToString(CultureInfo.InvariantCulture) + "." + kinds[i];
                list.Add(box);
            }
            return list;
        }
    }
}
