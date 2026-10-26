// `FiboEngine` - Fibo 1.0 s jadrom v C#. Zrkadlo `tradebot/strategies/fibo/engine.py`; s Python enginom sa porovnava
// bar po bare, na rovnost (ordery, kresby).
//
//   1. swingy na `swingTF` (sklada sa z barov grafu): pivot so `swingLen` barmi z oboch stran, az po potvrdeni,
//   2. noha vznikne potvrdenim swingu (od posledneho opacneho swingu), aspon `legMinAtr` ATR; pri `requireBreak`
//      musi koniec prekonat predosly swing; 0 % = koniec nohy, 100 % = jej zaciatok,
//   3. navrat: extrem navratu od konca nohy; setup pada pri prerazeni 100 %, prekonani konca nohy, alebo po
//      `setupMaxBars` baroch TF swingov,
//   4. vstup: hlbka navratu v zone / pri urovni a vstupny model v smere nohy (IBS imbalance / pin bar) najviac
//      `signalMaxBars` barov po sviecke s extremom navratu,
//   5. stop za zaciatok nohy (`leg`) alebo za extrem navratu (`pullback`), ciel extenzia nohy alebo RR.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.FiboNet
{
    /// <summary>Bary TF swingov z barov grafu - zrkadlo `StructAggregator` (`tradebot/strategies/jss/engine.py`).</summary>
    internal sealed class SwingAggregator
    {
        private readonly long _ms, _step;
        private bool _has;
        private long _p;
        private double _o, _h, _l, _c, _v;

        public SwingAggregator(int minutes, int chartMinutes) { _ms = minutes * 60000L; _step = chartMinutes * 60000L; }

        private Bar Emit()
        {
            Bar b = new Bar(_p, _o, _h, _l, _c, _v);
            _has = false;
            return b;
        }

        public List<Bar> Push(Bar bar)
        {
            List<Bar> outp = new List<Bar>();
            long period = bar.Time / _ms * _ms;
            if (_has && period != _p) outp.Add(Emit());
            if (!_has)
            {
                _has = true; _p = period;
                _o = bar.Open; _h = bar.High; _l = bar.Low; _c = bar.Close; _v = bar.Volume;
            }
            else
            {
                _h = Math.Max(_h, bar.High); _l = Math.Min(_l, bar.Low); _c = bar.Close; _v += bar.Volume;
            }
            if (bar.Time + _step >= period + _ms) outp.Add(Emit());
            return outp;
        }

        public void Prime(Bar partial)
        {
            if (partial == null) return;
            _has = true; _p = partial.Time / _ms * _ms;
            _o = partial.Open; _h = partial.High; _l = partial.Low; _c = partial.Close; _v = partial.Volume;
        }
    }

    internal sealed class Pivot
    {
        public double Price; public int Idx; public long Time;
        public Pivot(double price, int idx, long time) { Price = price; Idx = idx; Time = time; }
    }

    internal sealed class Setup
    {
        public int Uid; public Direction Dir; public double Start, End; public long StartMs, EndMs;
        public int Born; public double Extreme; public int ExtremeIdx;
        public double Size { get { return Math.Abs(End - Start); } }
        public double Level(double frac) { return End - frac * (End - Start); }
        public double Depth { get { return Size > 0 ? Math.Abs(End - Extreme) / Size : 0.0; } }
    }

    [TradeBotEngine("fibomgcnet", "Fibo 1.0 MGC (C# jadro)")]
    public sealed class FiboEngine : IEngine, IConfigured
    {
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";
        private const string FibColor = "#eab308";
        private const string LegColor = "#94a3b8";
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly FiboConfig _cfg;
        /// <summary>Config strategie - `EntryLayers.Wrap` z neho berie defaulty klucov, ktore profil nema.</summary>
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly int _swingTf;
        private readonly SwingAggregator _agg;
        private readonly List<Bar> _sbars = new List<Bar>();
        private readonly int _sbarsMax;
        private int _sIdx = -1;
        private double _sAtr;
        private readonly List<double> _sSeed = new List<double>();
        private Pivot _ph, _pl, _prevPh, _prevPl;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        public readonly BarHistory History;
        // poradie setupov ako Python dict (vlozenie; prepis nemeni poradie)
        private readonly List<Setup> _setups = new List<Setup>();
        private int _uid;
        private bool _seeding;
        private readonly TimeZoneInfo _zone;
        private bool _hasDay;
        private DateTime _day;
        private int _tradesToday;
        private int _entryIdx = -1;

        public FiboEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(FiboConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public FiboEngine(FiboConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            int tf = cfg.swingTF;
            if (tf < _tf || tf % _tf != 0) tf = (Math.Max(tf, _tf) + _tf - 1) / _tf * _tf;
            _swingTf = tf;
            _agg = new SwingAggregator(tf, _tf);
            _sbarsMax = 2 * cfg.swingLen + 4;
            _warmup = new Warmup(_tf).Add("ATR " + cfg.atrLen.ToString(CultureInfo.InvariantCulture), cfg.atrLen + 8);
            _warmup.AddSeeded("swingy " + tf.ToString(CultureInfo.InvariantCulture) + "m", 2 * cfg.swingLen + cfg.atrLen + 60, tf, Seed);
            _requiredHistory = _warmup.ChartBars;
            History = new BarHistory(Math.Max(_requiredHistory, 8) + 16, cfg.atrLen);
            _zone = TimeZones.Get(cfg.tradeTZ);
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

        private static string Whole(double x)
        {
            return ((long)Math.Round(x, 0, MidpointRounding.ToEven)).ToString(CultureInfo.InvariantCulture);
        }

        private Setup Find(Direction d)
        {
            foreach (Setup s in _setups) if (s.Dir == d) return s;
            return null;
        }

        // ------------------------------------------------------------------ //
        // swingy a nohy
        // ------------------------------------------------------------------ //

        private void Seed(IList<Bar> closed, Bar partial)
        {
            _seeding = true;
            foreach (Bar b in closed) OnSwingBar(b);
            _seeding = false;
            _agg.Prime(partial);
        }

        private void OnSwingBar(Bar b)
        {
            FiboConfig cfg = _cfg;
            Bar prev = _sbars.Count > 0 ? _sbars[_sbars.Count - 1] : null;
            double tr = prev == null ? b.High - b.Low
                : Math.Max(b.High - b.Low, Math.Max(Math.Abs(b.High - prev.Close), Math.Abs(b.Low - prev.Close)));
            if (_sAtr > 0) _sAtr += (tr - _sAtr) / cfg.atrLen;
            else
            {
                _sSeed.Add(tr);
                if (_sSeed.Count >= cfg.atrLen) _sAtr = PyMath.Sum(_sSeed) / _sSeed.Count;
            }
            _sbars.Add(b);
            if (_sbars.Count > _sbarsMax) _sbars.RemoveAt(0);
            _sIdx += 1;
            int n = cfg.swingLen;
            if (_sbars.Count < 2 * n + 1) return;
            int last = _sbars.Count - 1;
            Bar c = _sbars[last - n];
            List<Bar> side = new List<Bar>();
            for (int k = 1; k <= n; k++) side.Add(_sbars[last - n - k]);
            List<Bar> right = new List<Bar>();
            for (int k = 1; k <= n; k++) right.Add(_sbars[last + 1 - k]);
            side.AddRange(right);
            int ci = _sIdx - n;
            bool isHigh = true, isLow = true;
            foreach (Bar x in side) { if (!(c.High > x.High)) isHigh = false; if (!(c.Low < x.Low)) isLow = false; }
            if (isHigh)
            {
                _prevPh = _ph; _ph = new Pivot(c.High, ci, c.Time);
                Leg(Direction.Long, right);
            }
            if (isLow)
            {
                _prevPl = _pl; _pl = new Pivot(c.Low, ci, c.Time);
                Leg(Direction.Short, right);
            }
        }

        private void Leg(Direction d, List<Bar> right)
        {
            FiboConfig cfg = _cfg;
            bool up = d == Direction.Long;
            Pivot end = up ? _ph : _pl, start = up ? _pl : _ph, prevEnd = up ? _prevPh : _prevPl;
            if (_seeding || end == null || start == null || start.Idx >= end.Idx || _sAtr <= 0) return;
            double size = up ? end.Price - start.Price : start.Price - end.Price;
            if (size <= 0 || size < cfg.legMinAtr.Value * _sAtr) return;
            if (cfg.legMaxBars > 0 && end.Idx - start.Idx > cfg.legMaxBars) return;
            if (cfg.requireBreak && (prevEnd == null || (up ? end.Price <= prevEnd.Price : end.Price >= prevEnd.Price))) return;
            double ext = up ? double.PositiveInfinity : double.NegativeInfinity;
            foreach (Bar x in right) ext = up ? Math.Min(ext, x.Low) : Math.Max(ext, x.High);
            if (up ? ext <= start.Price : ext >= start.Price) return;
            _uid += 1;
            Setup s = new Setup();
            s.Uid = _uid; s.Dir = d; s.Start = start.Price; s.End = end.Price; s.StartMs = start.Time; s.EndMs = end.Time;
            s.Born = _sIdx; s.Extreme = ext; s.ExtremeIdx = History.BarIndex;
            for (int i = 0; i < _setups.Count; i++)
                if (_setups[i].Dir == d) { _setups[i] = s; return; }   // prepis kluca v dict nemeni poradie
            _setups.Add(s);
        }

        // ------------------------------------------------------------------ //
        // kresby
        // ------------------------------------------------------------------ //

        private void Draw(EngineOutput o, Setup s, long endMs)
        {
            if (!_cfg.showFibo) return;
            endMs = Math.Max(endMs, s.EndMs);
            DrawLine leg = new DrawLine(FiboKinds.Leg, s.StartMs, s.Start, s.EndMs, s.End, LegColor);
            leg.Style = LineStyles.Dashed;
            leg.ObjId = "fib.leg." + s.Uid.ToString(CultureInfo.InvariantCulture);
            leg.Text = "noha";
            o.Drawings.Add(leg);
            List<double> fracs = new List<double>();
            fracs.Add(0.0);
            fracs.AddRange(_cfg.Levels());
            fracs.Add(1.0);
            if (_cfg.tpMode == "extension") fracs.Add(-_cfg.tpExtensionPct / 100.0);
            foreach (double f in fracs)
            {
                double y = s.Level(f);
                DrawLine l = new DrawLine(FiboKinds.Level, s.EndMs, y, endMs, y, FibColor);
                l.ObjId = "fib.lv." + s.Uid.ToString(CultureInfo.InvariantCulture) + "." + PyMath.FormatG(f);
                l.Text = PyMath.FormatG(f * 100) + " %";
                o.Drawings.Add(l);
            }
        }

        // ------------------------------------------------------------------ //
        // vstupne modely (graf)
        // ------------------------------------------------------------------ //

        private bool Imbalance(bool isLong, double atr)
        {
            if (!History.Has(3)) return false;
            Bar b0 = History[0], b1 = History[1], b2 = History[2];
            double m = _cfg.imbMinSizeAtr.Value * atr;
            if (isLong) return b0.Low > b2.High && b1.Close > b2.High && (b0.Low - b2.High) >= m;
            return b0.High < b2.Low && b1.Close < b2.Low && (b2.Low - b0.High) >= m;
        }

        private bool PinBar(Bar bar, bool isLong)
        {
            double rng = bar.High - bar.Low;
            if (rng <= 0 || Math.Abs(bar.Close - bar.Open) > _cfg.pbBodyPct / 100.0 * rng) return false;
            double wick = isLong ? Math.Min(bar.Open, bar.Close) - bar.Low : bar.High - Math.Max(bar.Open, bar.Close);
            return wick >= _cfg.pbWickPct / 100.0 * rng;
        }

        private bool Signal(Bar bar, bool isLong, double atr)
        {
            string m = _cfg.entryModel;
            if (m == "imbalance") return Imbalance(isLong, atr);
            if (m == "pinbar") return PinBar(bar, isLong);
            return Imbalance(isLong, atr) || PinBar(bar, isLong);
        }

        private bool AtLevel(Setup s, double atr)
        {
            List<double> lv = _cfg.Levels();
            double tol = s.Size > 0 ? _cfg.levelTolAtr.Value * atr / s.Size : 0.0;
            double d = s.Depth;
            if (_cfg.levelMode == "zone") return lv[0] - tol <= d && d <= lv[lv.Count - 1] + tol;
            foreach (double x in lv) if (Math.Abs(d - x) <= tol) return true;
            return false;
        }

        private TradePlan Plan(Setup s, double entry, double atr)
        {
            FiboConfig cfg = _cfg;
            bool isLong = s.Dir == Direction.Long;
            double buf = cfg.slBufferAtr.Resolve(_inst, entry, atr) + cfg.slBufferPoints.Resolve(_inst, entry, atr);
            double bas = cfg.slMode == "leg" ? s.Start : s.Extreme;
            double stop = isLong ? bas - buf : bas + buf;
            double sl = isLong ? entry - stop : stop - entry;
            if (sl < _inst.TickSize * 2) return null;
            double minSl = cfg.minSlDistance.Resolve(_inst, entry, atr);
            if (minSl > 0 && sl < minSl) return null;
            double take;
            if (cfg.tpMode == "rr") take = isLong ? entry + sl * cfg.rrRatio : entry - sl * cfg.rrRatio;
            else
            {
                take = s.Level(-cfg.tpExtensionPct / 100.0);
                if ((isLong ? take - entry : entry - take) < sl * cfg.minRR) return null;
            }
            double q = cfg.riskDollar > 0 ? cfg.PositionQty(_inst, cfg.riskDollar, sl) : 1.0;
            if (q <= 0) q = _inst.MinQty > 0 ? _inst.MinQty : 1.0;
            return new TradePlan(s.Dir, _inst.RoundPrice(entry), _inst.RoundPrice(stop), _inst.RoundPrice(take), q, sl, null);
        }

        private bool InWindow(DateTime local)
        {
            if (_cfg.weekdaysOnly && (local.DayOfWeek == DayOfWeek.Saturday || local.DayOfWeek == DayOfWeek.Sunday)) return false;
            if (!_cfg.useTradeWindow) return true;
            int m = local.Hour * 60 + local.Minute;
            return _cfg.WindowStart <= m && m < _cfg.WindowEnd;
        }

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            FiboConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            double atr = History.Atr;
            int idx = History.BarIndex;

            DateTime local = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            if (!_hasDay || local.Date != _day)
            {
                _hasDay = true;
                _day = local.Date;
                _tradesToday = 0;
            }

            if (cfg.maxHoldBars > 0 && ctx.PositionSize != 0.0 && _entryIdx >= 0 && idx - _entryIdx >= cfg.maxHoldBars)
            {
                List<string> ids = new List<string>(ctx.OpenOrderIds);
                ids.Sort(StringComparer.Ordinal);
                foreach (string oid in ids)
                    o.Orders.Add(new OrderIntent(OrderAction.Close, oid, idx,
                        "drží sa dlhšie než " + cfg.maxHoldBars.ToString(CultureInfo.InvariantCulture) + " barov"));
                _entryIdx = -1;
            }

            bool free = ctx.PositionSize == 0.0 && atr > 0;
            foreach (Setup s in new List<Setup>(_setups))
            {
                bool isLong = s.Dir == Direction.Long;
                if ((isLong ? bar.Low < s.Start : bar.High > s.Start) || (isLong ? bar.High > s.End : bar.Low < s.End)
                    || _sIdx - s.Born > cfg.setupMaxBars)
                {
                    _setups.Remove(s);
                    continue;
                }
                if (isLong ? bar.Low < s.Extreme : bar.High > s.Extreme)
                {
                    s.Extreme = isLong ? bar.Low : bar.High;
                    s.ExtremeIdx = idx;
                }
                if (!free || (isLong && !cfg.AllowLong) || (!isLong && !cfg.AllowShort)) continue;
                if (s.ExtremeIdx < 0 || (cfg.signalMaxBars > 0 && idx - s.ExtremeIdx > cfg.signalMaxBars)) continue;
                if (!AtLevel(s, atr) || !Signal(bar, isLong, atr)) continue;
                if (!InWindow(local) || _tradesToday >= cfg.maxTradesPerDay) continue;
                TradePlan plan = Plan(s, bar.Close, atr);
                if (plan == null) continue;
                string depth = Whole(s.Depth * 100);
                OrderIntent intent = new OrderIntent(OrderAction.Entry, "fib:" + idx.ToString(CultureInfo.InvariantCulture), idx,
                                                     "návrat " + depth + " % + " + cfg.entryModel);
                intent.Direction = s.Dir;
                intent.Plan = plan;
                intent.OrderType = OrderType.Market;
                o.Orders.Add(intent);
                DrawLabel label = new DrawLabel(FiboKinds.Entry, bar.Time, isLong ? bar.Low : bar.High,
                                                (isLong ? "LONG " : "SHORT ") + depth + " %", "#ffffff");
                label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
                label.Above = !isLong;
                label.BgColor = isLong ? LongColor : ShortColor;
                label.ObjId = "fib.e." + bar.Time.ToString(CultureInfo.InvariantCulture);
                o.Drawings.Add(label);
                Draw(o, s, bar.Time);
                _tradesToday += 1;
                _entryIdx = idx;
                _setups.Remove(s);
                free = false;
            }

            foreach (Bar sb in _agg.Push(bar)) OnSwingBar(sb);
            return o;
        }
    }
}
