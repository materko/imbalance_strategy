// `WprEngine` - WILLIAMS %R LONG 1.0 s jadrom v C#. Zrkadlo `tradebot/strategies/wpr/engine.py` (a spolocnych kuskov
// `tradebot/strategies/rqport.py`); s Python enginom sa porovnava bar po bare, na rovnost. Len long:
//   1. %R(wprLen) este nie je -> zapamatat high a nic,
//   2. cakanie na novy prepad - v pozicii sa zapne, vypne sa, ked %R vystupi aspon na entryLevel,
//   3. vstup - bez pozicie, bez cakania, %R < entryLevel: long trhom,
//   4. vystup - zavretie nad high predoslej sviecky (exitMode 0 / 2) alebo %R >= exitLevel (1 / 2).
// Stop `stopPct` % (0 = poistka 10 %), bez ciela (100 R). Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.WprNet
{
    [TradeBotEngine("wprnet", "WILLIAMS %R LONG 1.0 (C# jadro)")]
    public class WprEngine : IEngine, IConfigured
    {
        private const string LongColor = "#22c55e";
        private const string ShortColor = "#ef4444";
        private const double FarStop = 0.10;
        private const double NoTpR = 100.0;

        private readonly WprConfig _cfg;
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        private readonly int _n;
        public readonly BarHistory History;
        private readonly List<Bar> _win = new List<Bar>();
        private double? _prevHigh;
        private bool _wait;
        private readonly List<string> _boxes = new List<string>();
        private bool _wasIn;

        public WprEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(WprConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public WprEngine(WprConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _n = Math.Max(1, cfg.wprLen);
            History = new BarHistory(2, 14);
            _warmup = new Warmup(_tf).Add("%R " + _n.ToString(CultureInfo.InvariantCulture), _n);
            _requiredHistory = _n;
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

        private void Track(EngineOutput o, Bar bar, double pos)
        {
            if (_boxes.Count == 0 || (pos == 0.0 && !_wasIn)) return;   // vstup este caka - box drzi obal
            foreach (string oid in _boxes)
                o.Drawings.Add(new DrawUpdate(oid, "x2_ms", bar.Time + _stepMs));
            if (pos != 0.0) _wasIn = true;
            else if (_wasIn) { _boxes.Clear(); _wasIn = false; }
        }

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            WprConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            double pos = ctx.PositionSize;
            Track(o, bar, pos);
            _win.Add(bar);
            while (_win.Count > _n) _win.RemoveAt(0);

            // ---- 1. %R --------------------------------------------------------- //
            if (_win.Count < _n)
            {
                _prevHigh = bar.High;
                return o;
            }
            double hh = double.MinValue, ll = double.MaxValue;
            foreach (Bar b in _win) { if (b.High > hh) hh = b.High; if (b.Low < ll) ll = b.Low; }
            double wpr = hh > ll ? -100.0 * (hh - bar.Close) / (hh - ll) : -50.0;

            bool inLong = pos > 0;
            // ---- 2. cakanie na novy prepad ------------------------------------- //
            if (inLong) _wait = true;
            if (_wait && wpr >= cfg.entryLevel) _wait = false;

            // ---- 3. vstup ------------------------------------------------------- //
            if (pos == 0.0 && !_wait && wpr < cfg.entryLevel)
            {
                Enter(o, bar, idx);
                _wait = true;
            }

            // ---- 4. vystup ------------------------------------------------------ //
            int mode = cfg.exitMode;
            bool exPrior = inLong && (mode == 0 || mode == 2) && _prevHigh.HasValue && bar.Close > _prevHigh.Value;
            bool exWpr = inLong && (mode == 1 || mode == 2) && wpr >= cfg.exitLevel;
            if (exPrior || exWpr)
            {
                o.CloseSession = true;
                List<string> ids = new List<string>(ctx.OpenOrderIds);
                ids.Sort(StringComparer.Ordinal);
                foreach (string orderId in ids)
                    o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx,
                                                 exPrior ? "nad high predošlej sviečky" : "%R nad úrovňou výstupu"));
                _wait = true;
            }
            _prevHigh = bar.High;
            return o;
        }

        /// <summary>`rqport.market_entry` (long) + `TradeDraw.start(show_tp=False)`.</summary>
        private void Enter(EngineOutput o, Bar bar, int idx)
        {
            WprConfig cfg = _cfg;
            double pct = cfg.stopPct > 0 ? cfg.stopPct / 100.0 : FarStop;
            double entry = bar.Close;
            double stop = _inst.RoundPrice(bar.Close * (1 - pct));
            double risk = Math.Abs(entry - stop);
            if (risk < _inst.TickSize || stop >= entry) return;
            double take = _inst.RoundPrice(entry + risk * NoTpR);
            if (take <= entry) return;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, risk);
            if (q <= 0) return;
            TradePlan plan = new TradePlan(Direction.Long, entry, stop, take, q, risk, null);
            OrderIntent intent = new OrderIntent(OrderAction.Entry, "wpr:" + idx.ToString(CultureInfo.InvariantCulture), idx,
                                                 "%R long (prepad pod úroveň vstupu)");
            intent.Direction = Direction.Long;
            intent.Plan = plan;
            intent.OrderType = OrderType.Market;
            o.Orders.Add(intent);

            long end = bar.Time + _stepMs;
            _boxes.Clear();
            _wasIn = false;
            string bid = "wpr.sl." + bar.Time.ToString(CultureInfo.InvariantCulture);
            DrawBox box = new DrawBox(DrawKinds.SlBox, bar.Time, Math.Max(entry, stop), end, Math.Min(entry, stop), ShortColor);
            box.FillColor = Palette.WithAlpha(ShortColor, 60);
            box.ObjId = bid;
            box.Text = "SL " + PyMath.FormatG(stop);
            o.Drawings.Add(box);
            _boxes.Add(bid);
            DrawLabel label = new DrawLabel(WprKinds.Entry, bar.Time, entry, "%R", "#ffffff");
            label.Style = LabelStyles.Up;
            label.Above = false;
            label.BgColor = LongColor;
            label.ObjId = "wpr.e." + bar.Time.ToString(CultureInfo.InvariantCulture);
            o.Drawings.Add(label);
        }
    }

    /// <summary>Ten isty Williams %R na Micro Dow (MYM) - vlastny kluc kvoli profilom a nasadeniu (12. 11. 2026).</summary>
    [TradeBotEngine("wprmymnet", "WILLIAMS %R LONG 1.0 MYM (C# jadro)")]
    public sealed class WprMymEngine : WprEngine
    {
        public WprMymEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }
}
