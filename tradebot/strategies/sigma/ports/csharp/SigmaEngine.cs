// `SigmaEngine` - SIGMA BREAKOUT 1.0 s jadrom v C#. Zrkadlo `tradebot/strategies/sigma/engine.py` (a spolocnych kuskov
// `tradebot/strategies/rqport.py`); s Python enginom sa porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy).
//
// Cas = otvorenie baru v New Yorku, RTH 9:30 <= t < 16:00:
//   1. novy den - pozicia z predosleho dna sa zavrie, open RTH a VWAP od nuly,
//   2. t >= 16:00 s poziciou -> zavriet; mimo RTH nic dalsie,
//   3. pasmo = referencia (open RTH alebo VWAP k predoslemu baru) +- bandMult * priemer |zavretie - open RTH|
//      v tej istej minute za poslednych nSigmaDays dni; obchoduje sa, ked je historia nejakej minuty plna,
//   4. zavretie nad pasmom a pozicia <= 0 -> (zavriet short) long; pod pasmom a >= 0 -> short,
//   5. VWAP a historia minuty sa doplnia tymto barom az po rozhodnuti.
// Stop `slPct` % (0 = poistka 10 %), bez ciela (100 R). Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.SigmaNet
{
    [TradeBotEngine("sigmanet", "SIGMA BREAKOUT 1.0 (C# jadro)")]
    public class SigmaEngine : IEngine, IConfigured
    {
        private const string Ny = "America/New_York";
        private const string LongColor = "#22c55e";
        private const string ShortColor = "#ef4444";
        private const string RefColor = "#ffd700";
        private const string UpColor = "#26a69a";
        private const string DnColor = "#ef5350";
        private const double FarStop = 0.10;
        private const double NoTpR = 100.0;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly SigmaConfig _cfg;
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly TimeZoneInfo _zone;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        private readonly int _n;
        public readonly BarHistory History;

        private readonly Dictionary<int, List<double>> _slots = new Dictionary<int, List<double>>();
        private bool _hasDay;
        private DateTime _day;
        private double? _dayOpen;
        private double _pv, _vol;
        private double? _vwapPrev;
        private bool _enabled;
        private readonly List<string> _boxes = new List<string>();
        private bool _wasIn;

        public SigmaEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(SigmaConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public SigmaEngine(SigmaConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _zone = TimeZones.Get(Ny);
            History = new BarHistory(2, 14);
            _n = Math.Max(2, cfg.nSigmaDays);
            _warmup = new Warmup(_tf).Add("sigma " + _n.ToString(CultureInfo.InvariantCulture) + " dní",
                                          WarmupMath.OnChart(_n * 3 / 2 + 2, 1440, _tf));
            _requiredHistory = _warmup.ChartBars;
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

        // ------------------------------------------------------------------ //

        private static void CloseAll(EngineOutput o, MarketContext ctx, int idx, string reason)
        {
            o.CloseSession = true;
            List<string> ids = new List<string>(ctx.OpenOrderIds);
            ids.Sort(StringComparer.Ordinal);
            foreach (string orderId in ids)
                o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx, reason));
        }

        /// <summary>`rqport.TradeDraw.tick` - boxy rastu, kym obchod bezi.</summary>
        private void Track(EngineOutput o, Bar bar, double pos)
        {
            if (_boxes.Count == 0 || (pos == 0.0 && !_wasIn)) return;   // vstup este caka - box drzi obal
            foreach (string oid in _boxes)
                o.Drawings.Add(new DrawUpdate(oid, "x2_ms", bar.Time + _stepMs));
            if (pos != 0.0) _wasIn = true;
            else if (_wasIn) { _boxes.Clear(); _wasIn = false; }
        }

        /// <summary>`rqport.market_entry` + `TradeDraw.start(show_tp=False)`.</summary>
        private void Enter(EngineOutput o, Bar bar, int idx, bool isLong, double up, double dn)
        {
            SigmaConfig cfg = _cfg;
            double pct = cfg.slPct > 0 ? cfg.slPct / 100.0 : FarStop;
            double entry = bar.Close;
            double stop = _inst.RoundPrice(isLong ? bar.Close * (1 - pct) : bar.Close * (1 + pct));
            double risk = Math.Abs(entry - stop);
            if (risk < _inst.TickSize || (isLong && stop >= entry) || (!isLong && stop <= entry)) return;
            double take = _inst.RoundPrice(isLong ? entry + risk * NoTpR : entry - risk * NoTpR);
            if ((isLong && take <= entry) || (!isLong && take >= entry)) return;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, risk);
            if (q <= 0) return;
            TradePlan plan = new TradePlan(isLong ? Direction.Long : Direction.Short, entry, stop, take, q, risk, null);
            OrderIntent intent = new OrderIntent(OrderAction.Entry, "sigma:" + idx.ToString(CultureInfo.InvariantCulture), idx,
                "Sigma " + (isLong ? "long" : "short") + ": pásmo " + PyMath.FormatG(dn) + "–" + PyMath.FormatG(up));
            intent.Direction = plan.Direction;
            intent.Plan = plan;
            intent.OrderType = OrderType.Market;
            o.Orders.Add(intent);

            long end = bar.Time + _stepMs;
            _boxes.Clear();
            _wasIn = false;
            string bid = "sigma.sl." + bar.Time.ToString(CultureInfo.InvariantCulture);
            DrawBox box = new DrawBox(DrawKinds.SlBox, bar.Time, Math.Max(entry, stop), end, Math.Min(entry, stop), ShortColor);
            box.FillColor = Palette.WithAlpha(ShortColor, 60);
            box.ObjId = bid;
            box.Text = "SL " + PyMath.FormatG(stop);
            o.Drawings.Add(box);
            _boxes.Add(bid);
            DrawLabel label = new DrawLabel(SigmaKinds.Entry, bar.Time, entry, isLong ? "Sigma long" : "Sigma short", "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "sigma.e." + bar.Time.ToString(CultureInfo.InvariantCulture);
            o.Drawings.Add(label);
        }

        // ------------------------------------------------------------------ //

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            SigmaConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            double pos = ctx.PositionSize;
            DateTime t = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            int hhmm = t.Hour * 100 + t.Minute;
            Track(o, bar, pos);

            // ---- 1. novy den ------------------------------------------------------ //
            if (!_hasDay || t.Date != _day)
            {
                if (pos != 0.0 && cfg.useCloseAtEnd)
                {
                    CloseAll(o, ctx, idx, "zmena dňa");
                    pos = 0.0;
                }
                _hasDay = true;
                _day = t.Date;
                _dayOpen = null;
                _pv = 0.0;
                _vol = 0.0;
                _vwapPrev = null;
            }

            // ---- 2. 16:00 ------------------------------------------------------- //
            if (hhmm >= 1600 && pos != 0.0 && cfg.useCloseAtEnd)
            {
                CloseAll(o, ctx, idx, "16:00 NY");
                pos = 0.0;
            }
            if (!(930 <= hhmm && hhmm < 1600)) return o;

            // ---- 3. open RTH ---------------------------------------------------- //
            if (!_dayOpen.HasValue) _dayOpen = bar.Open;
            double rf = cfg.useVwap ? (_vwapPrev.HasValue ? _vwapPrev.Value : _dayOpen.Value) : _dayOpen.Value;

            // ---- 4. pasmo ------------------------------------------------------- //
            List<double> hist;
            if (!_slots.TryGetValue(hhmm, out hist)) { hist = new List<double>(); _slots[hhmm] = hist; }
            bool full = hist.Count == _n;
            double sigma = hist.Count > 0 ? PyMath.Sum(hist) / hist.Count : 0.0;
            double up = rf + cfg.bandMult * sigma, dn = rf - cfg.bandMult * sigma;
            if (full)
            {
                long end = bar.Time + _stepMs;
                o.Drawings.Add(BandLine(bar, up, end, UpColor, "u"));
                o.Drawings.Add(BandLine(bar, dn, end, DnColor, "d"));
                o.Drawings.Add(BandLine(bar, rf, end, RefColor, "r"));
                _enabled = true;
            }

            // ---- 5. vstup ------------------------------------------------------- //
            if (_enabled)
            {
                if (bar.Close > up && pos <= 0.0)
                {
                    if (pos < 0.0) CloseAll(o, ctx, idx, "opačný prieraz");
                    Enter(o, bar, idx, true, up, dn);
                }
                else if (bar.Close < dn && pos >= 0.0)
                {
                    if (pos > 0.0) CloseAll(o, ctx, idx, "opačný prieraz");
                    Enter(o, bar, idx, false, up, dn);
                }
            }

            // ---- 6. VWAP a historia minuty -------------------------------------- //
            double tp = (bar.High + bar.Low + bar.Close) / 3.0;
            _pv += tp * bar.Volume;
            _vol += bar.Volume;
            if (_vol > 0) _vwapPrev = _pv / _vol;
            hist.Add(Math.Abs(bar.Close - _dayOpen.Value));
            while (hist.Count > _n) hist.RemoveAt(0);
            return o;
        }

        private DrawLine BandLine(Bar bar, double y, long end, string color, string n)
        {
            DrawLine line = new DrawLine(SigmaKinds.Band, bar.Time, y, end, y, color);
            line.Width = 1;
            line.ObjId = "sigma." + n + "." + bar.Time.ToString(CultureInfo.InvariantCulture);
            return line;
        }
    }

    /// <summary>Ta ista Sigma na zlate (MGC) - vlastny kluc kvoli profilom a nasadeniu.</summary>
    [TradeBotEngine("sigmamgcnet", "SIGMA BREAKOUT 1.0 MGC (C# jadro)")]
    public sealed class SigmaMgcEngine : SigmaEngine
    {
        public SigmaMgcEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }
}
