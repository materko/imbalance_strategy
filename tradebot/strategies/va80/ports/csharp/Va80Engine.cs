// `Va80Engine` - MTK RANGE 1.0 (pravidlo 80 %) s jadrom v C#. Zrkadlo `tradebot/strategies/va80/engine.py`; s Python
// enginom sa porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy). Cas New York, RTH 9:30-16:00:
//   1. novy den - value area z barov predosleho dna (zavretie a objem v kosoch vaBinPct % otvorenia), otvorenie
//      nad VAH / pod VAL aspon o minOpenOutside sirky VA,
//   2. profil dna a extrem dna od otvorenia,
//   3. vystup v case o exitTime,
//   4. prve zavretie sviecky returnBarMin (od 9:30) spat vo VA do lastEntry = jeden pokus za den: stop za extremom
//      dna + slBufferVa * sirka VA, ciel POC / opacny okraj / stred.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.Va80Net
{
    [TradeBotEngine("va80net", "MTK RANGE 1.0 (C# jadro)")]
    public sealed class Va80Engine : IEngine, IConfigured
    {
        private const string Ny = "America/New_York";
        private const int OpenMin = 570, CloseMin = 960;
        private const string LongColor = "#22c55e", ShortColor = "#ef4444";
        private const string VahColor = "#089981", ValColor = "#f23645", PocColor = "#5b9cf6";
        private const double NoTpR = 100.0;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly Va80Config _cfg;
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly TimeZoneInfo _zone;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        public readonly BarHistory History;

        private bool _hasDay;
        private DateTime _day;
        private readonly Dictionary<double, double> _bins = new Dictionary<double, double>();
        private double _binStep;
        private bool _hasVa;
        private double _vah, _val, _poc;
        private int _side;
        private int _trades;
        private bool _done;
        private double _extH, _extL;
        // denne ATR z RTH dni (true range voci predoslemu zavretiu, priemer 14 hotovych dni)
        private bool _hasD;
        private double _dH, _dL, _dC;
        private bool _hasPrevC;
        private double _prevC;
        private readonly List<double> _trs = new List<double>();
        private readonly List<string> _boxes = new List<string>();
        private bool _wasIn;

        public Va80Engine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(Va80Config.FromDict(config), inst, chartTfMinutes)
        {
        }

        public Va80Engine(Va80Config cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _zone = TimeZones.Get(Ny);
            History = new BarHistory(2, 14);
            _warmup = new Warmup(_tf).Add("profil predošlého dňa a ATR 14 dní", 24 * 1440 / _tf);
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

        /// <summary>`value_area` - (VAH, VAL, POC) z objemov kosov; false, ked sa neda spocitat.</summary>
        public static bool ValueArea(Dictionary<double, double> bins, double pct, string method,
                                     out double vah, out double val, out double poc)
        {
            vah = val = poc = 0.0;
            if (bins.Count == 0) return false;
            List<double> prices = new List<double>(bins.Keys);
            prices.Sort();
            List<double> vols = new List<double>();
            foreach (double p in prices) vols.Add(bins[p]);
            double tot = PyMath.Sum(vols);
            if (tot <= 0) return false;
            int pi = 0;
            for (int k = 1; k < prices.Count; k++) if (bins[prices[k]] > bins[prices[pi]]) pi = k;
            poc = prices[pi];
            double limit = pct / 100.0 * tot;
            if (method == "expand")
            {
                int i = pi, j = pi;
                double acc = bins[poc];
                while (acc < limit && (i > 0 || j < prices.Count - 1))
                {
                    double up = j < prices.Count - 1 ? bins[prices[j + 1]] : -1.0;
                    double dn = i > 0 ? bins[prices[i - 1]] : -1.0;
                    if (up >= dn) { j += 1; acc += up; }
                    else { i -= 1; acc += dn; }
                }
                vah = prices[j]; val = prices[i];
                return true;
            }
            List<double> order = new List<double>(prices);
            order.Sort(delegate (double a, double b)
            {
                int c = bins[b].CompareTo(bins[a]);
                return c != 0 ? c : a.CompareTo(b);
            });
            double s = 0.0, hi = double.MinValue, lo = double.MaxValue;
            double pocP = poc;
            foreach (double p in order)
            {
                s += bins[p];
                if (s <= limit || p == pocP) { if (p > hi) hi = p; if (p < lo) lo = p; }
            }
            vah = hi; val = lo;
            return true;
        }

        private double Bin(double price)
        {
            return _inst.RoundPrice(Math.Round(price / _binStep, MidpointRounding.ToEven) * _binStep);
        }

        private static void CloseAll(EngineOutput o, MarketContext ctx, int idx, string reason)
        {
            o.CloseSession = true;
            List<string> ids = new List<string>(ctx.OpenOrderIds);
            ids.Sort(StringComparer.Ordinal);
            foreach (string orderId in ids) o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx, reason));
        }

        private void Track(EngineOutput o, Bar bar, double pos)
        {
            if (_boxes.Count == 0 || (pos == 0.0 && !_wasIn)) return;   // vstup este caka - box drzi obal
            foreach (string oid in _boxes) o.Drawings.Add(new DrawUpdate(oid, "x2_ms", bar.Time + _stepMs));
            if (pos != 0.0) _wasIn = true;
            else if (_wasIn) { _boxes.Clear(); _wasIn = false; }
        }

        private void NewDay(EngineOutput o, Bar bar, DateTime day)
        {
            Va80Config cfg = _cfg;
            if (_bins.Count > 0)
            {
                double h, l, p;
                _hasVa = ValueArea(_bins, cfg.vaPct, cfg.vaMethod, out h, out l, out p);
                if (_hasVa) { _vah = h; _val = l; _poc = p; }
            }
            if (_hasD)
            {
                double tr = !_hasPrevC ? _dH - _dL : Math.Max(_dH, _prevC) - Math.Min(_dL, _prevC);
                _trs.Add(tr);
                while (_trs.Count > 14) _trs.RemoveAt(0);
                _prevC = _dC;
                _hasPrevC = true;
            }
            _hasD = true;
            _dH = bar.High; _dL = bar.Low;
            _hasDay = true;
            _day = day;
            _bins.Clear();
            double tick = _inst.TickSize;
            _binStep = Math.Max(tick, Math.Round(bar.Open * cfg.vaBinPct / 100.0 / tick, MidpointRounding.ToEven) * tick);
            _done = false;
            _side = 0;
            _trades = 0;
            _extH = bar.High; _extL = bar.Low;
            if (!_hasVa) return;
            double width = _vah - _val;
            if (width <= 0) return;
            if (bar.Open > _vah + cfg.minOpenOutside * width) _side = -1;
            else if (bar.Open < _val - cfg.minOpenOutside * width) _side = 1;
            if (cfg.showLevels)
            {
                long end = bar.Time + (CloseMin - OpenMin) * 60000L;
                o.Drawings.Add(Level(bar, _vah, end, VahColor, "h", "VAH včera"));
                o.Drawings.Add(Level(bar, _val, end, ValColor, "l", "VAL včera"));
                o.Drawings.Add(Level(bar, _poc, end, PocColor, "p", "POC včera"));
            }
        }

        private static DrawLine Level(Bar bar, double y, long end, string color, string n, string text)
        {
            DrawLine line = new DrawLine(Va80Kinds.Level, bar.Time, y, end, y, color);
            line.Style = LineStyles.Dashed;
            line.ObjId = "va80." + n + "." + bar.Time.ToString(CultureInfo.InvariantCulture);
            line.Text = text;
            return line;
        }

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            Va80Config cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            double pos = ctx.PositionSize;
            Track(o, bar, pos);
            DateTime t = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            int m = t.Hour * 60 + t.Minute;
            if (t.DayOfWeek == DayOfWeek.Saturday || t.DayOfWeek == DayOfWeek.Sunday || m < OpenMin || m >= CloseMin) return o;
            int endM = m + _tf;
            int endHm = endM / 60 * 100 + endM % 60;

            if (!_hasDay || t.Date != _day) NewDay(o, bar, t.Date);
            double b = Bin(bar.Close);
            double v;
            _bins.TryGetValue(b, out v);
            _bins[b] = v + bar.Volume;
            _extH = Math.Max(_extH, bar.High);
            _extL = Math.Min(_extL, bar.Low);
            _dH = Math.Max(_dH, bar.High); _dL = Math.Min(_dL, bar.Low); _dC = bar.Close;

            if (pos != 0.0 && endHm >= cfg.exitTime)
            {
                CloseAll(o, ctx, idx, "výstup v čase " + cfg.exitTime.ToString("0000", CultureInfo.InvariantCulture));
                return o;
            }
            if (_done || !_hasVa || pos != 0.0 || (endM - OpenMin) % cfg.returnBarMin != 0) return o;
            if (endHm > cfg.lastEntry) { _done = true; return o; }
            if (!(_val <= bar.Close && bar.Close <= _vah))
            {
                if (!cfg.requireOpenOutside || _trades > 0) _side = bar.Close > _vah ? -1 : 1;
                return o;
            }
            if (_side == 0 || _trades >= cfg.maxTradesPerDay) return o;
            _trades += 1;
            bool isLong = _side > 0;
            _side = 0;
            double stopH = _extH, stopL = _extL;
            _extH = bar.High; _extL = bar.Low;     // extrem dalsieho vybehu sa pocita od tohto pokusu
            if ((isLong && !cfg.allowLong) || (!isLong && !cfg.allowShort)) return o;
            double width = _vah - _val;
            double stop = isLong ? stopL - cfg.slBufferVa * width : stopH + cfg.slBufferVa * width;
            double entry = bar.Close;
            double take = cfg.tpMode == "rr" ? entry + cfg.rrRatio * (entry - stop)
                : cfg.tpMode == "poc" ? _poc : cfg.tpMode == "opp" ? (isLong ? _vah : _val) : (_vah + _val) / 2;
            if (cfg.minRR > 0 && Math.Abs(take - entry) < cfg.minRR * Math.Abs(entry - stop)) return o;
            if (cfg.maxStopAtr > 0 && (_trs.Count < 14 || Math.Abs(entry - stop) > cfg.maxStopAtr * (PyMath.Sum(_trs) / _trs.Count))) return o;
            Enter(o, bar, idx, isLong, stop, take);
            return o;
        }

        /// <summary>`rqport.market_entry` + `TradeDraw.start`.</summary>
        private void Enter(EngineOutput o, Bar bar, int idx, bool isLong, double stopRaw, double takeRaw)
        {
            Va80Config cfg = _cfg;
            double entry = bar.Close;
            double stop = _inst.RoundPrice(stopRaw);
            double risk = Math.Abs(entry - stop);
            if (risk < _inst.TickSize || (isLong && stop >= entry) || (!isLong && stop <= entry)) return;
            double take = _inst.RoundPrice(takeRaw);
            if ((isLong && take <= entry) || (!isLong && take >= entry)) return;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, risk);
            if (q <= 0) return;
            TradePlan plan = new TradePlan(isLong ? Direction.Long : Direction.Short, entry, stop, take, q, risk, null);
            OrderIntent intent = new OrderIntent(OrderAction.Entry, "va80:" + idx.ToString(CultureInfo.InvariantCulture), idx,
                                                 "návrat do včerajšej VA (" + (isLong ? "long" : "short") + ")");
            intent.Direction = plan.Direction;
            intent.Plan = plan;
            intent.OrderType = OrderType.Market;
            o.Orders.Add(intent);
            long end = bar.Time + _stepMs;
            _boxes.Clear();
            _wasIn = false;
            foreach (bool tp in new bool[] { true, false })
            {
                double level = tp ? take : stop;
                string color = tp ? LongColor : ShortColor;
                string kind = tp ? DrawKinds.TpBox : DrawKinds.SlBox;
                string bid = "va80." + (tp ? "tp" : "sl") + "." + bar.Time.ToString(CultureInfo.InvariantCulture);
                DrawBox box = new DrawBox(kind, bar.Time, Math.Max(entry, level), end, Math.Min(entry, level), color);
                box.FillColor = Palette.WithAlpha(color, 60);
                box.ObjId = bid;
                box.Text = (tp ? "TP " : "SL ") + PyMath.FormatG(level);
                o.Drawings.Add(box);
                _boxes.Add(bid);
            }
            DrawLabel label = new DrawLabel(Va80Kinds.Entry, bar.Time, entry, isLong ? "VA long" : "VA short", "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "va80.e." + bar.Time.ToString(CultureInfo.InvariantCulture);
            o.Drawings.Add(label);
        }
    }
}
