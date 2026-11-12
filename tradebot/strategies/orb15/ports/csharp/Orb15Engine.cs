// `Orb15Engine` - ORB 15/5 1.0 s jadrom v C# (zatial pod klucom MTK ORB na zlate). Zrkadlo
// `tradebot/strategies/orb15/engine.py`; s Python enginom sa porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy).
//
// Cas = otvorenie baru v New Yorku. Na kazdom uzavretom bare:
//   1. novy den (datum NY) - vynulovat OR, bias, pocitadlo obchodov; zavretie seansy 9:30-16:00 sa posunie,
//   2. OR - bary orStart <= t < koniec OR rozsiria high / low (pri entryAtLevel posledny bar OR pokracuje dalej),
//   3. OR hotovy - sirka OR proti medianu (maxOrWidthMult),
//   4. bias predosleho obchodneho dna CME (od 18:00 NY),
//   5. koniec - t >= lastEntry: zrusit cakajuci stop order, pri closeAtEnd zavriet poziciu,
//   6b. entryAtLevel - stop order na hranici OR v smere gapu; zrusi sa, ked prerazi druha strana,
//   6. vstup - zavretie za OR (knot, gap, bias, len prvy prieraz), stop na druhej strane OR.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.Orb15Net
{
    /// <summary>MTK ORB na zlate (MGC / GC): ORB 15 len prvy prieraz v smere gapu, stop order na hranici OR.</summary>
    [TradeBotEngine("mtkorbnet", "MTK ORB MGC (C# jadro)")]
    public class Orb15Engine : IEngine, IConfigured
    {
        private const string Ny = "America/New_York";
        private const string LongColor = "#22c55e";
        private const string ShortColor = "#ef4444";
        private const string ZoneColor = "#2196f3";
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly Orb15Config _cfg;
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly TimeZoneInfo _zone;
        private readonly Warmup _warmup;
        public readonly BarHistory History;

        private bool _hasDay;
        private DateTime _day;
        private double _orHigh = double.NegativeInfinity;
        private double _orLow = double.PositiveInfinity;
        private bool _orReady;
        private long _orStartMs;
        private int _trades;
        private bool _biasDone;
        private bool _longsBlocked, _shortsBlocked;
        private bool _hasTday;
        private DateTime _tday;
        private bool _hasTdayHl;
        private double _tdayH, _tdayL;
        private bool _hasPrevHl;
        private double _prevH, _prevL;
        private readonly List<string> _boxes = new List<string>();
        private bool _wasIn;
        private double? _rthClose;
        private double? _prevRthClose;
        private int _gapDir;
        private readonly int _widthsMax;
        private readonly List<double> _widths = new List<double>();
        private bool _widthBlocked;
        private string _pendingId;      // stop order na hranici OR (entryAtLevel), kym sa nevyplni
        private bool _pendingLong;

        public Orb15Engine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(Orb15Config.FromDict(config), inst, chartTfMinutes)
        {
        }

        public Orb15Engine(Orb15Config cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _zone = TimeZones.Get(Ny);
            History = new BarHistory(4, 14);
            _warmup = new Warmup(_tf);
            _widthsMax = Math.Max(5, cfg.orWidthLookback);
        }

        public InstrumentSpec Inst { get { return _inst; } }
        public int ChartTfMinutes { get { return _tf; } }
        public int RequiredHistory { get { return 1; } }
        public Warmup Warmup { get { return _warmup; } }
        public IHtfFeeder CreateHtfFeeder() { return null; }
        public List<DrawCommand> FinalDrawings(Bar bar) { return new List<DrawCommand>(); }

        public Dictionary<string, double> Stats()
        {
            Dictionary<string, double> s = new Dictionary<string, double>();
            s["leverage"] = _cfg.leverage;
            return s;
        }

        private static int Hm(int v) { return (v / 100) * 60 + v % 100; }

        private static double Median(List<double> xs)
        {
            List<double> s = new List<double>(xs);
            s.Sort();
            int n = s.Count;
            return n % 2 == 1 ? s[n / 2] : (s[n / 2 - 1] + s[n / 2]) / 2.0;
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

        private void Enter(EngineOutput o, Bar bar, int idx, bool isLong, double entry, OrderType orderType)
        {
            Orb15Config cfg = _cfg;
            double stop = isLong ? _orLow : _orHigh;
            double risk = Math.Abs(entry - stop);
            if (risk < _inst.TickSize) return;
            double dist = cfg.targetMode == 1 ? cfg.targetPoints : risk * cfg.rr;
            double take = _inst.RoundPrice(isLong ? entry + dist : entry - dist);
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, risk);
            if (q <= 0) return;
            TradePlan plan = new TradePlan(isLong ? Direction.Long : Direction.Short, entry, stop, take, q, risk, null);
            string oid = "orb15:" + idx.ToString(CultureInfo.InvariantCulture);
            OrderIntent intent = new OrderIntent(OrderAction.Entry, oid, idx,
                "ORB 15/5 " + (isLong ? "long" : "short") + ": OR " + PyMath.FormatG(_orLow) + "–" + PyMath.FormatG(_orHigh));
            intent.Direction = plan.Direction;
            intent.Plan = plan;
            intent.OrderType = orderType;
            o.Orders.Add(intent);
            _trades += 1;
            if (orderType != OrderType.Market) { _pendingId = oid; _pendingLong = isLong; }
            else _pendingId = null;

            long end = bar.Time + _stepMs;
            _boxes.Clear();
            _wasIn = false;
            AddBox(o, bar, DrawKinds.TpBox, "tp", "TP", take, entry, end, LongColor);
            AddBox(o, bar, DrawKinds.SlBox, "sl", "SL", stop, entry, end, ShortColor);
            DrawLabel label = new DrawLabel(Orb15Kinds.Entry, bar.Time, entry, isLong ? "ORB long" : "ORB short", "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "orb15.e." + bar.Time.ToString(CultureInfo.InvariantCulture);
            o.Drawings.Add(label);
        }

        private void AddBox(EngineOutput o, Bar bar, string kind, string tag, string text, double level, double entry,
                            long end, string color)
        {
            string bid = "orb15." + tag + "." + bar.Time.ToString(CultureInfo.InvariantCulture);
            DrawBox box = new DrawBox(kind, bar.Time, Math.Max(entry, level), end, Math.Min(entry, level), color);
            box.FillColor = Palette.WithAlpha(color, 60);
            box.ObjId = bid;
            box.Text = text + " " + PyMath.FormatG(level);
            o.Drawings.Add(box);
            _boxes.Add(bid);
        }

        private void TrackDay(Bar bar, DateTime t)
        {
            DateTime tday = t.AddHours(6).Date;          // 18:00 NY = zaciatok dalsieho obchodneho dna
            if (!_hasTday || tday != _tday)
            {
                if (_hasTdayHl) { _hasPrevHl = true; _prevH = _tdayH; _prevL = _tdayL; }
                _hasTday = true;
                _tday = tday;
                _hasTdayHl = true;
                _tdayH = bar.High;
                _tdayL = bar.Low;
            }
            else
            {
                _tdayH = Math.Max(_tdayH, bar.High);
                _tdayL = Math.Min(_tdayL, bar.Low);
            }
        }

        // ------------------------------------------------------------------ //

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            Orb15Config cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            double pos = ctx.PositionSize;
            DateTime t = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            int mins = t.Hour * 60 + t.Minute;
            bool hasPrevHl = _hasPrevHl;                  // hotovy den pred tymto barom
            double prevH = _prevH, prevL = _prevL;
            TrackDay(bar, t);

            if (_boxes.Count > 0)
            {
                foreach (string oid in _boxes)
                    o.Drawings.Add(new DrawUpdate(oid, "x2_ms", bar.Time + _stepMs));
                if (pos != 0.0) _wasIn = true;
                else if (_wasIn) { _boxes.Clear(); _wasIn = false; }
            }

            // ---- 1. novy den ------------------------------------------------------ //
            if (!_hasDay || t.Date != _day)
            {
                _hasDay = true;
                _day = t.Date;
                if (_rthClose.HasValue) { _prevRthClose = _rthClose; _rthClose = null; }   // nedela (len ETH) neprepise
                _gapDir = 0;
                _widthBlocked = false;
                _orHigh = double.NegativeInfinity;
                _orLow = double.PositiveInfinity;
                _orReady = false;
                _trades = 0;
                _biasDone = false;
                _longsBlocked = _shortsBlocked = false;
            }

            int orStart = Hm(cfg.orStart);
            int orEnd = orStart + cfg.orMinutes;
            if (570 <= mins && mins < 960) _rthClose = bar.Close;

            // ---- 2. OR ---------------------------------------------------------------- //
            if (!_orReady && orStart <= mins && mins < orEnd)
            {
                if (double.IsNegativeInfinity(_orHigh))
                {
                    _orStartMs = bar.Time;
                    if (_prevRthClose.HasValue)
                    {
                        double pc = _prevRthClose.Value;
                        _gapDir = (bar.Open > pc ? 1 : 0) - (bar.Open < pc ? 1 : 0);
                    }
                }
                _orHigh = Math.Max(_orHigh, bar.High);
                _orLow = Math.Min(_orLow, bar.Low);
                if (cfg.drawRange)
                {
                    DrawBox zb = new DrawBox(Orb15Kinds.Zone, _orStartMs, _orHigh, _orStartMs + cfg.orMinutes * 60000L, _orLow, ZoneColor);
                    zb.FillColor = Palette.WithAlpha(ZoneColor, 38);
                    zb.ObjId = "orb15.z." + _orStartMs.ToString(CultureInfo.InvariantCulture);
                    zb.Text = "OR";
                    o.Drawings.Add(zb);
                }
                if (!(cfg.entryAtLevel && mins + _tf >= orEnd)) return o;
                // entryAtLevel: posledny bar OR ho uzavrel - stop order ide hned na jeho zavreti
            }

            // ---- 3. OR hotovy? ---------------------------------------------------------- //
            if (!_orReady && (mins >= orEnd || (cfg.entryAtLevel && mins + _tf >= orEnd)) && !double.IsNegativeInfinity(_orHigh))
            {
                _orReady = true;
                double width = _orHigh - _orLow;
                if (cfg.maxOrWidthMult > 0 && _widths.Count >= 20)
                    _widthBlocked = width > cfg.maxOrWidthMult * Median(_widths);
                _widths.Add(width);
                while (_widths.Count > _widthsMax) _widths.RemoveAt(0);
            }
            if (!_orReady) return o;

            // ---- 4. bias predosleho dna ------------------------------------------------- //
            if (cfg.useDailyBias && !_biasDone && mins >= Hm(cfg.biasCheck))
            {
                _biasDone = true;
                if (!hasPrevHl) return o;                // predloha: bez dennej hodnoty koniec baru
                _longsBlocked = bar.Close < prevL;
                _shortsBlocked = bar.Close > prevH;
            }

            // ---- 5. koniec -------------------------------------------------------------- //
            if (_pendingId != null && (pos != 0.0 || ctx.OpenOrderIds.Contains(_pendingId)))
                _pendingId = null;                        // stop order sa vyplnil
            if (t.Hour * 100 + t.Minute >= cfg.lastEntry)
            {
                if (_pendingId != null)
                {
                    o.Orders.Add(new OrderIntent(OrderAction.Cancel, _pendingId, idx, "koniec vstupov"));
                    _pendingId = null;
                }
                if (cfg.closeAtEnd && pos != 0.0)
                    CloseAll(o, ctx, idx, "koniec " + cfg.lastEntry.ToString("D4", CultureInfo.InvariantCulture) + " NY");
                return o;
            }
            if (_pendingId == null && (pos != 0.0 || _trades >= cfg.maxTradesPerDay || _widthBlocked))
                return o;

            // ---- 6b. vstup stop orderom na hranici OR ----------------------------------- //
            if (cfg.entryAtLevel)
            {
                if (_pendingId != null)
                {
                    bool pl = _pendingLong;
                    if (pl ? bar.Low < _orLow : bar.High > _orHigh)   // prerazila druha strana
                    {
                        o.Orders.Add(new OrderIntent(OrderAction.Cancel, _pendingId, idx, "prieraz druhou stranou OR"));
                        _pendingId = null;
                        if (cfg.firstBreakOnly) _widthBlocked = true;
                    }
                    return o;
                }
                if (pos != 0.0 || (_trades > 0 && cfg.firstBreakOnly)) return o;
                bool lng;
                int gf = cfg.gapFilter;
                if (gf != 0)
                {
                    if (_gapDir == 0) return o;
                    lng = (gf == 1 ? _gapDir : -_gapDir) > 0;
                }
                else lng = bar.Close >= (_orHigh + _orLow) / 2;
                if ((lng && (!cfg.allowLong || _longsBlocked)) || (!lng && (!cfg.allowShort || _shortsBlocked))) return o;
                if (lng ? bar.Close < _orLow : bar.Close > _orHigh)   // druha strana uz prerazena
                {
                    if (cfg.firstBreakOnly) _widthBlocked = true;
                    return o;
                }
                Enter(o, bar, idx, lng, lng ? _orHigh : _orLow, OrderType.Stop);
                return o;
            }

            // ---- 6. vstup ---------------------------------------------------------------- //
            double rng = bar.High - bar.Low;
            double upperWick = bar.High - Math.Max(bar.Open, bar.Close);
            double lowerWick = Math.Min(bar.Open, bar.Close) - bar.Low;
            bool longWickBad = cfg.useWickFilter && rng > 0 && lowerWick / rng * 100.0 > cfg.maxWickPct;
            bool shortWickBad = cfg.useWickFilter && rng > 0 && upperWick / rng * 100.0 > cfg.maxWickPct;
            int g = cfg.gapFilter;
            if (g != 0 && _gapDir != 0)
            {
                int want = g == 1 ? _gapDir : -_gapDir;
                longWickBad = longWickBad || want < 0;
                shortWickBad = shortWickBad || want > 0;
            }
            else if (g != 0)
            {
                longWickBad = shortWickBad = true;        // bez gapu filter nepusti nic
            }
            if (cfg.firstBreakOnly && _trades == 0 && (bar.Close > _orHigh || bar.Close < _orLow))
            {
                bool up = bar.Close > _orHigh;
                bool ok = up ? (cfg.allowLong && !longWickBad && !_longsBlocked)
                             : (cfg.allowShort && !shortWickBad && !_shortsBlocked);
                if (!ok)
                {
                    _widthBlocked = true;                 // prvy prieraz siel nepovolenym smerom
                    return o;
                }
            }
            if (cfg.allowLong && bar.Close > _orHigh && !longWickBad && !_longsBlocked)
                Enter(o, bar, idx, true, bar.Close, OrderType.Market);
            else if (cfg.allowShort && bar.Close < _orLow && !shortWickBad && !_shortsBlocked)
                Enter(o, bar, idx, false, bar.Close, OrderType.Market);
            return o;
        }
    }
}
