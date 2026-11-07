// `VoltBreakEngine` - Volt Break s jadrom v C#. Zrkadlo `tradebot/strategies/voltbreak/engine.py`; s Python enginom sa
// porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy). Casy CT (America/Chicago):
//   1. novy den (polnoc CT): Noise Up = open + noisePct % priemerneho ATR (avgLen seans), VWAP od polnoci,
//   2. signal: bar sa zatvara v okne startHHMM-endHHMM, plocha pozicia, menej nez maxTrades obchodov dna,
//      zavretie nad Noise Up aj nad VWAP -> long market; TP / SL v $ na kontrakt (prepocet usdPerPoint),
//   3. casovy exit na zavreti baru, ktory sa zatvara v endHHMM alebo neskor (pred 16:00 CT).
// Priemer ATR dostane predhistoriu z dat pred behom (prehraju sa bary grafu bez obchodov). Engine je CISTY.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.VoltBreakNet
{
    [TradeBotEngine("voltbreaknet", "Volt Break (C# jadro)")]
    public sealed class VoltBreakEngine : IEngine, IConfigured
    {
        private const string Ct = "America/Chicago";
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";
        private const int BoxBars = 6;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly VoltBreakConfig _cfg;
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly TimeZoneInfo _zone;
        private readonly int _start, _end;
        private readonly SessionVwap _vwap;
        private readonly SessionAvgAtr _sessAtr;
        private readonly DailyAvgAtr _dailyAtr;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        public readonly BarHistory History;
        private bool _hasPrevDay;
        private DateTime _prevDay;
        private double? _noiseUp;
        private int _tradesToday;
        private bool _hasLastVwap;
        private long _lastVwapMs;
        private double _lastVwapValue;

        public VoltBreakEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(VoltBreakConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public VoltBreakEngine(VoltBreakConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _zone = TimeZones.Get(Ct);
            _start = VoltBreakConfig.HhmmMinutes(cfg.startHHMM);
            _end = VoltBreakConfig.HhmmMinutes(cfg.endHHMM);
            _vwap = new SessionVwap(_tf, 0, 24 * 60, Ct, null, 64);
            _sessAtr = new SessionAvgAtr(cfg.atrLen, cfg.avgLen);
            _dailyAtr = new DailyAvgAtr(cfg.atrLen, cfg.avgLen);
            _warmup = new Warmup(_tf).Add("bez predhistórie", 2);
            _warmup.AddSeeded("ATR " + cfg.atrLen.ToString(CultureInfo.InvariantCulture) + " za " +
                              cfg.avgLen.ToString(CultureInfo.InvariantCulture) + " seáns",
                              SeedSessions(cfg) * 1380 / _tf, _tf, Seed);
            _requiredHistory = _warmup.ChartBars;
            History = new BarHistory(8, 14);
        }

        /// <summary>Rozbeh RMA, kym vaha startu neklesne pod 0,01 %, + okno priemeru + rezerva (`_seed_sessions`).</summary>
        private static int SeedSessions(VoltBreakConfig cfg)
        {
            int n = Math.Max(1, cfg.atrLen);
            double alpha = 1.0 / n;
            int decay = alpha >= 1.0 ? 0 : (int)Math.Ceiling(Math.Log(0.0001) / Math.Log(1.0 - alpha));
            return n + decay + cfg.avgLen + 2;
        }

        public InstrumentSpec Inst { get { return _inst; } }
        public int ChartTfMinutes { get { return _tf; } }
        public int RequiredHistory { get { return _requiredHistory; } }
        public Warmup Warmup { get { return _warmup; } }
        public IHtfFeeder CreateHtfFeeder() { return null; }
        public List<DrawCommand> FinalDrawings(Bar bar) { return new List<DrawCommand>(); }

        public Dictionary<string, double> Stats()
        {
            Dictionary<string, double> s = new Dictionary<string, double>();
            s["leverage"] = _cfg.leverage;
            return s;
        }

        private double? AvgAtr { get { return _cfg.atrSource == VoltBreakConfig.AtrDaily ? _dailyAtr.Value : _sessAtr.Value; } }

        private void Seed(IList<Bar> closed, Bar partial)
        {
            foreach (Bar b in closed)
            {
                MarketContext ctx = new MarketContext();
                ctx.InTradeWindow = true;
                OnBar(b, null, ctx);
            }
        }

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            VoltBreakConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            DateTime local = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            DateTime closeLocal = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time + _stepMs), _zone);
            int barMin = local.Hour * 60 + local.Minute;
            int closeMin = closeLocal.Hour * 60 + closeLocal.Minute;
            DateTime day = local.Date;

            _sessAtr.Push(bar, barMin);
            _dailyAtr.Push(bar, local);
            double? vw = _vwap.Push(bar);

            if (!_hasPrevDay || day != _prevDay)
            {
                double? avg = AvgAtr;
                _noiseUp = avg.HasValue ? (double?)(bar.Open + cfg.noisePct / 100.0 * avg.Value) : null;
                _tradesToday = 0;
                _hasLastVwap = false;
                if (cfg.showLevels && _noiseUp.HasValue)
                {
                    long right = bar.Time + Math.Max(_end - barMin, _tf) * 60000L;
                    DrawLine line = new DrawLine(VoltBreakKinds.Noise, bar.Time, _noiseUp.Value, right, _noiseUp.Value, "#f59e0b");
                    line.ObjId = "vb_noise." + bar.Time.ToString(CultureInfo.InvariantCulture);
                    line.Text = "Noise Up";
                    o.Drawings.Add(line);
                }
            }
            _hasPrevDay = true;
            _prevDay = day;

            if (cfg.showLevels && vw.HasValue && barMin < SessionAvgAtr.SessionEndMin)
            {
                long endMs = bar.Time + _stepMs;
                bool had = _hasLastVwap;
                long pMs = _lastVwapMs;
                double pV = _lastVwapValue;
                _hasLastVwap = true;
                _lastVwapMs = endMs;
                _lastVwapValue = vw.Value;
                if (had)
                {
                    DrawLine line = new DrawLine(VoltBreakKinds.Vwap, pMs, pV, endMs, vw.Value, "#3b82f6");
                    line.ObjId = "vb_vwap." + endMs.ToString(CultureInfo.InvariantCulture);
                    line.Text = "VWAP";
                    o.Drawings.Add(line);
                }
            }

            bool flat = ctx.PositionSize == 0.0;
            bool inWindow = _start <= closeMin && closeMin < _end;
            if (inWindow && flat && _tradesToday < cfg.maxTrades && _noiseUp.HasValue
                && bar.Close > _noiseUp.Value && vw.HasValue && bar.Close > vw.Value)
            {
                TradePlan plan = Plan(bar);
                if (plan != null)
                {
                    _tradesToday += 1;
                    OrderIntent intent = new OrderIntent(OrderAction.Entry, "vb:" + idx.ToString(CultureInfo.InvariantCulture), idx,
                                                         "zavretie nad Noise Up aj VWAP");
                    intent.Direction = Direction.Long;
                    intent.Plan = plan;
                    intent.OrderType = OrderType.Market;
                    o.Orders.Add(intent);
                    DrawLabel label = new DrawLabel(VoltBreakKinds.Entry, bar.Time, bar.Low, "LONG", "#ffffff");
                    label.Style = LabelStyles.Up;
                    label.Above = false;
                    label.BgColor = LongColor;
                    label.ObjId = "vb_entry." + bar.Time.ToString(CultureInfo.InvariantCulture);
                    o.Drawings.Add(label);
                    o.Drawings.Add(Box(bar, DrawKinds.TpBox, plan.TakeProfit, plan.Entry, LongColor));
                    o.Drawings.Add(Box(bar, DrawKinds.SlBox, plan.StopLoss, plan.Entry, ShortColor));
                }
            }

            if (cfg.useTimeExit && !flat && closeMin >= _end && barMin < SessionAvgAtr.SessionEndMin)
            {
                o.CloseSession = true;
                List<string> ids = new List<string>(ctx.OpenOrderIds);
                ids.Sort(StringComparer.Ordinal);
                foreach (string orderId in ids)
                    o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx, "časový exit"));
            }
            return o;
        }

        private TradePlan Plan(Bar bar)
        {
            VoltBreakConfig cfg = _cfg;
            double sl = cfg.SlPoints;
            if (sl <= 0) return null;
            double entry = bar.Close;
            double q = cfg.riskDollar > 0 ? (cfg.legacyPineSizing ? 1.0 : _inst.QtyForRisk(cfg.riskDollar, sl)) : 1.0;
            if (q <= 0) q = _inst.MinQty != 0 ? _inst.MinQty : 1.0;
            return new TradePlan(Direction.Long, _inst.RoundPrice(entry), _inst.RoundPrice(entry - sl),
                                 _inst.RoundPrice(entry + cfg.TpPoints), q, sl, null);
        }

        private DrawBox Box(Bar bar, string kind, double price, double entry, string color)
        {
            DrawBox box = new DrawBox(kind, bar.Time, Math.Max(entry, price), bar.Time + BoxBars * _stepMs, Math.Min(entry, price), color);
            box.FillColor = color + "40";
            box.BorderWidth = 0;
            box.ObjId = "vb" + bar.Time.ToString(CultureInfo.InvariantCulture) + "." + kind;
            return box;
        }
    }
}
