// `NyVaEngine` - NY VA BREAKOUT s jadrom v C#. Zrkadlo `tradebot/strategies/nyva/engine.py`; s Python enginom sa
// porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy).
//
//   1. range - bary otvorene v rangeStart <= t < rangeEnd (New York, cas OTVORENIA baru) sa zbieraju (high, low, objem),
//   2. profil - na prvom bare po rangei: objem baru rovnomerne do `profileRows` riadkov, POC = stred najobjemnejsieho,
//      value area sa rozsiruje od POC o objemnejsieho suseda, kym nema `valueAreaPct` % (VAH / VAL); tvar P / b,
//   3. prieraz - `confirmCloses` zavreti po sebe nad VAH (pod VAL); sirka VA, VWAP dna (od 18:00 NY) a tvar ako filtre,
//   4. vstup - do entryEnd, bez pozicie, najviac `maxTradesPerDay`: market, alebo limitka na VAH / VAL (retest),
//   5. stop `slBufferTicks` za POC (strop maxSlPoints / maxSlAtr x ATR: vynechat / skratit), ciel rrRatio x riziko.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.NyVaNet
{
    /// <summary>Profil rangeu - zrkadlo `value_area` a `profile_shape` v Pythone.</summary>
    public static class NyVaProfile
    {
        public struct Area { public double Poc, Vah, Val, Hi, Lo; }

        public static Area ValueArea(List<double[]> bars, int rows, double pct, double minStep)
        {
            double hi = double.NegativeInfinity, lo = double.PositiveInfinity;
            foreach (double[] b in bars) { if (b[0] > hi) hi = b[0]; if (b[1] < lo) lo = b[1]; }
            double step = Math.Max((hi - lo) / rows, minStep);
            double[] vols = new double[rows];
            foreach (double[] b in bars)
            {
                int i0 = Math.Max(0, Math.Min(rows - 1, (int)Math.Floor((b[1] - lo) / step)));
                int i1 = Math.Max(0, Math.Min(rows - 1, (int)Math.Floor((b[0] - lo) / step)));
                double share = b[2] / (i1 - i0 + 1);
                for (int j = i0; j <= i1; j++) vols[j] += share;
            }
            int p = 0;
            for (int j = 1; j < rows; j++) if (vols[j] > vols[p]) p = j;
            double target = PyMath.Sum(vols) * pct / 100.0;
            double acc = vols[p];
            int up = p, dn = p;
            while (acc < target && (up < rows - 1 || dn > 0))
            {
                double vUp = up < rows - 1 ? vols[up + 1] : -1.0;
                double vDn = dn > 0 ? vols[dn - 1] : -1.0;
                if (vUp >= vDn) { up += 1; acc += vUp; }
                else { dn -= 1; acc += vDn; }
            }
            Area a;
            a.Poc = lo + (p + 0.5) * step; a.Vah = lo + (up + 1) * step; a.Val = lo + dn * step; a.Hi = hi; a.Lo = lo;
            return a;
        }

        /// <summary>(poc, va, low, high) - poloha POC a stredu VA (0 = low, 1 = high), podiel objemu v dolnej / hornej tretine.</summary>
        public static double[] Shape(List<double[]> bars, int rows, double pct, double minStep)
        {
            Area a = ValueArea(bars, rows, pct, minStep);
            double span = a.Hi - a.Lo;
            if (span <= 0) return new double[] { 0.5, 0.5, 1.0 / 3, 1.0 / 3 };
            double third = span / 3.0, total = 0.0, low = 0.0, high = 0.0;
            foreach (double[] b in bars)
            {
                double h = b[0], l = b[1], v = b[2];
                double rng = Math.Max(h - l, 1e-12);
                total += v;
                low += h > l ? v * Math.Max(0.0, Math.Min(h, a.Lo + third) - l) / rng : (l <= a.Lo + third ? v : 0.0);
                high += h > l ? v * Math.Max(0.0, h - Math.Max(l, a.Hi - third)) / rng : (h >= a.Hi - third ? v : 0.0);
            }
            if (total == 0.0) total = 1.0;
            return new double[] { (a.Poc - a.Lo) / span, ((a.Vah + a.Val) / 2 - a.Lo) / span, low / total, high / total };
        }
    }

    [TradeBotEngine("nyvaesnet", "NY VA BREAKOUT ES (C# jadro)")]
    public sealed class NyVaEngine : IEngine, IConfigured
    {
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";
        private const string RangeColor = "#94a3b8";
        private const string PocColor = "#facc15";
        private const string VaColor = "#22d3ee";
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly NyVaConfig _cfg;
        /// <summary>Config strategie - `EntryLayers.Wrap` z neho berie defaulty klucov, ktore profil nema.</summary>
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        private readonly TimeZoneInfo _ny;
        public readonly BarHistory History;

        private bool _hasDay;
        private DateTime _day;
        private List<double[]> _bars = new List<double[]>();
        private long? _rangeMs;
        private bool _prevIn, _built;
        private double _poc, _vah, _val;
        private int _trades;
        private int? _prevMin;
        private List<string> _boxes = new List<string>();
        private bool _wasIn;
        private double[] _shape;
        private bool _shapeP, _shapeB;
        private int _nUp, _nDn;
        private string _pendingId;
        private int _pendingAt;
        private bool _hasVwapDay;
        private DateTime _vwapDay;
        private double _pv, _vv;

        public NyVaEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(NyVaConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public NyVaEngine(NyVaConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _ny = TimeZones.Get("America/New_York");
            History = new BarHistory(4, 14);
            _warmup = new Warmup(_tf).Add("ATR 14 (max stop)", History.AtrWarmupBars);
            _requiredHistory = Math.Max(1, _warmup.ChartBars);
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

        private DateTime Ny(long ms) { return TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(ms), _ny); }

        private long NyMs(DateTime day, int h, int m)
        {
            DateTime local = new DateTime(day.Year, day.Month, day.Day, h, m, 0, DateTimeKind.Unspecified);
            return (long)(TimeZoneInfo.ConvertTimeToUtc(local, _ny) - Epoch).TotalMilliseconds;
        }

        private static string Ms(long ms) { return ms.ToString(CultureInfo.InvariantCulture); }

        // ------------------------------------------------------------------ //

        private void Build(EngineOutput o, Bar bar)
        {
            NyVaConfig cfg = _cfg;
            NyVaProfile.Area a = NyVaProfile.ValueArea(_bars, cfg.profileRows, cfg.valueAreaPct, _inst.TickSize);
            _poc = a.Poc; _vah = a.Vah; _val = a.Val;
            _built = true;
            _shape = NyVaProfile.Shape(_bars, cfg.profileRows, cfg.valueAreaPct, _inst.TickSize);
            _shapeP = _shape[0] >= cfg.shapePocPct / 100 && _shape[1] >= cfg.shapeVaPct / 100 && _shape[2] <= cfg.shapeTailPct / 100;
            _shapeB = _shape[0] <= 1 - cfg.shapePocPct / 100 && _shape[1] <= 1 - cfg.shapeVaPct / 100 && _shape[3] <= cfg.shapeTailPct / 100;
            if (!cfg.showLevels) return;
            DateTime t = Ny(bar.Time);
            long xEnd = Math.Max(NyMs(t, cfg.entryEndH, cfg.entryEndM), bar.Time);
            long x0 = _rangeMs.HasValue ? _rangeMs.Value : bar.Time;
            string kind = _shapeP ? "P" : _shapeB ? "b" : "D";
            DrawBox box = new DrawBox(NyVaKinds.Range, x0, a.Hi, bar.Time, a.Lo, RangeColor);
            box.FillColor = Palette.WithAlpha(RangeColor, 40);
            box.ObjId = "nv.r." + Ms(x0);
            box.Text = "range · profil " + kind;
            o.Drawings.Add(box);
            Line(o, NyVaKinds.Poc, x0, _poc, xEnd, PocColor, "POC", 2);
            Line(o, NyVaKinds.Va, x0, _vah, xEnd, VaColor, "VAH", 1);
            Line(o, NyVaKinds.Va, x0, _val, xEnd, VaColor, "VAL", 1);
        }

        private void Line(EngineOutput o, string kind, long x0, double y, long xEnd, string color, string name, int width)
        {
            DrawLine l = new DrawLine(kind, x0, y, xEnd, y, color);
            l.Width = width;
            l.ObjId = "nv." + name + "." + Ms(x0);
            l.Text = name + " " + PyMath.FormatG(_inst.RoundPrice(y));
            o.Drawings.Add(l);
        }

        private double MaxSl()
        {
            bool has = false;
            double m = 0.0;
            if (_cfg.maxSlPoints > 0) { m = _cfg.maxSlPoints; has = true; }
            if (_cfg.maxSlAtr > 0 && History.Atr > 0)
            {
                double x = _cfg.maxSlAtr * History.Atr;
                m = has ? Math.Min(m, x) : x;
                has = true;
            }
            return has ? m : 0.0;
        }

        private TradePlan Plan(bool isLong, double entry, double stop)
        {
            NyVaConfig cfg = _cfg;
            double risk = Math.Abs(entry - stop);
            double cap = MaxSl();
            if (cap > 0 && risk > cap)
            {
                if (!cfg.CapSl) return null;
                risk = cap;
                stop = isLong ? entry - cap : entry + cap;
            }
            if (risk < _inst.TickSize * 2) return null;
            double take = isLong ? entry + cfg.rrRatio * risk : entry - cfg.rrRatio * risk;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, risk);
            if (q <= 0) q = _inst.MinQty > 0 ? _inst.MinQty : 1.0;
            return new TradePlan(isLong ? Direction.Long : Direction.Short, _inst.RoundPrice(entry), _inst.RoundPrice(stop),
                                 _inst.RoundPrice(take), q, risk, null);
        }

        private void Enter(EngineOutput o, Bar bar, int idx, TradePlan plan, string reason, string text, bool limit)
        {
            bool isLong = plan.Direction == Direction.Long;
            string oid = "nv:" + idx.ToString(CultureInfo.InvariantCulture);
            OrderIntent intent = new OrderIntent(OrderAction.Entry, oid, idx, reason);
            intent.Direction = plan.Direction;
            intent.Plan = plan;
            intent.OrderType = limit ? OrderType.Limit : OrderType.Market;
            o.Orders.Add(intent);
            if (limit) { _pendingId = oid; _pendingAt = idx; }
            else _trades += 1;
            _boxes = new List<string>();
            _wasIn = false;
            long end = bar.Time + _stepMs;
            AddBox(o, DrawKinds.TpBox, "tp", "TP ", plan.TakeProfit, plan.Entry, LongColor, bar.Time, end);
            AddBox(o, DrawKinds.SlBox, "sl", "SL ", plan.StopLoss, plan.Entry, ShortColor, bar.Time, end);
            DrawLabel label = new DrawLabel(NyVaKinds.Entry, bar.Time, plan.Entry, text, "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "nv.e." + Ms(bar.Time);
            o.Drawings.Add(label);
        }

        private void AddBox(EngineOutput o, string kind, string tag, string prefix, double level, double entry, string color,
                            long t, long end)
        {
            string oid = "nv." + tag + "." + Ms(t);
            DrawBox box = new DrawBox(kind, t, Math.Max(entry, level), end, Math.Min(entry, level), color);
            box.FillColor = Palette.WithAlpha(color, 60);
            box.ObjId = oid;
            box.Text = prefix + PyMath.FormatG(level);
            o.Drawings.Add(box);
            _boxes.Add(oid);
        }

        private void Track(EngineOutput o, Bar bar, MarketContext ctx)
        {
            if (_boxes.Count == 0) return;
            foreach (string oid in _boxes) o.Drawings.Add(new DrawUpdate(oid, "x2_ms", bar.Time + _stepMs));
            if (ctx.PositionSize != 0.0) _wasIn = true;
            else if (_wasIn) { _boxes = new List<string>(); _wasIn = false; }
        }

        // ------------------------------------------------------------------ //

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            NyVaConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            Track(o, bar, ctx);
            DateTime t = Ny(bar.Time);
            int cur = t.Hour * 60 + t.Minute;
            DateTime vday = Ny(bar.Time + 6 * 3600 * 1000L).Date;   // obchodny den od 18:00 NY
            if (!_hasVwapDay || vday != _vwapDay) { _hasVwapDay = true; _vwapDay = vday; _pv = 0.0; _vv = 0.0; }
            _pv += (bar.High + bar.Low + bar.Close) / 3.0 * bar.Volume;
            _vv += bar.Volume;
            bool hasVwap = _vv > 0;
            double vwap = hasVwap ? _pv / _vv : 0.0;
            if (!_hasDay || t.Date != _day)
            {
                _hasDay = true;
                _day = t.Date;
                _nUp = _nDn = 0;
                _trades = 0;
                _built = false;
                _bars = new List<double[]>();
                _prevIn = false;
                _prevMin = null;
            }

            // ---- range a profil ----------------------------------------------
            bool inRange = cfg.RangeStart <= cur && cur < cfg.RangeEnd;
            if (inRange)
            {
                if (!_prevIn) { _bars = new List<double[]>(); _rangeMs = bar.Time; _built = false; }
                _bars.Add(new double[] { bar.High, bar.Low, bar.Volume });
            }
            else if (_prevIn && _bars.Count > 0 && !_built)
            {
                Build(o, bar);
            }
            _prevIn = inRange;

            // ---- zavretie v case ---------------------------------------------
            double pos = ctx.PositionSize;
            if (cfg.useCloseTime && pos != 0.0 && cur >= cfg.CloseTime && (!_prevMin.HasValue || _prevMin.Value < cfg.CloseTime))
            {
                o.CloseSession = true;
                foreach (string oid in ctx.OpenOrderIds)
                    o.Orders.Add(new OrderIntent(OrderAction.Close, oid, idx, "zavretie v čase"));
            }

            // ---- retest: vyplnenie / zrusenie limitky ------------------------
            if (_pendingId != null)
            {
                if (pos != 0.0)
                {
                    _pendingId = null;
                    _trades += 1;
                }
                else if (idx - _pendingAt >= cfg.retestBars || cur >= cfg.EntryEnd || o.CloseSession)
                {
                    o.Orders.Add(new OrderIntent(OrderAction.Cancel, _pendingId, _pendingAt, "retest nevyplnený"));
                    _pendingId = null;
                }
            }

            // ---- prieraz a vstup ----------------------------------------------
            if (_built && !inRange)
            {
                double c = bar.Close;
                _nUp = c > _vah ? _nUp + 1 : 0;
                _nDn = c < _val ? _nDn + 1 : 0;
                double width = _vah - _val;
                bool widthOk = (cfg.vaMinPoints <= 0 || width >= cfg.vaMinPoints) && (cfg.vaMaxPoints <= 0 || width <= cfg.vaMaxPoints);
                if (widthOk && cfg.RangeEnd <= cur && cur < cfg.EntryEnd && pos == 0.0 && _pendingId == null
                    && _trades < cfg.maxTradesPerDay && !o.CloseSession)
                {
                    int need = cfg.confirmCloses;
                    double buf = cfg.slBufferTicks * _inst.TickSize;
                    bool retest = cfg.Retest;
                    bool goLong = cfg.allowLong && _nUp == need && (!cfg.useShape || _shapeP) && (!cfg.useVwap || (hasVwap && c > vwap));
                    bool goShort = cfg.allowShort && _nDn == need && (!cfg.useShape || _shapeB) && (!cfg.useVwap || (hasVwap && c < vwap));
                    string tail = retest ? " — retest" : "";
                    string n = need.ToString(CultureInfo.InvariantCulture);
                    if (goLong)
                    {
                        double e = retest ? _vah : c, sl = _poc - buf;
                        TradePlan plan = e > sl ? Plan(true, e, sl) : null;
                        if (plan != null)
                            Enter(o, bar, idx, plan, n + "× zavretie nad VAH " + PyMath.FormatG(_inst.RoundPrice(_vah)) + tail, "nad VAH", retest);
                    }
                    else if (goShort)
                    {
                        double e = retest ? _val : c, sl = _poc + buf;
                        TradePlan plan = e < sl ? Plan(false, e, sl) : null;
                        if (plan != null)
                            Enter(o, bar, idx, plan, n + "× zavretie pod VAL " + PyMath.FormatG(_inst.RoundPrice(_val)) + tail, "pod VAL", retest);
                    }
                }
            }
            _prevMin = cur;
            return o;
        }
    }
}
