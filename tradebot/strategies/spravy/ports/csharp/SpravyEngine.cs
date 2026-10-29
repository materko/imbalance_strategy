// `SpravyEngine` - SPRAVY s jadrom v C#. Zrkadlo `tradebot/strategies/spravy/engine.py`; s Python enginom sa
// porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy).
//
// Cas: spravy su v kalendari (`SpravyCalendar`, vygenerovany z calendar.json) v case New York a prevadzaju sa na UTC
// pre kazdy den zvlast - sedi aj v tyzdnoch, ked USA a Slovensko menia cas v ine dni. Stitky ukazuju cas SK aj NY.
//
//   1. vystup v case - otvorena pozicia po `trendHold` / `fadeHold` minutach sa zavrie trhom,
//   2. noha - zaciatok (open baru v T pri od = 0, inak close baru koniaceho v T+od), high / low nohy,
//   3. vstup - na prvom bare koniacom v T+do alebo neskor: TREND v smere nohy, FADE proti nej, market.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.SpravyNet
{
    [TradeBotEngine("spravynet", "SPRÁVY (C# jadro)")]
    public sealed class SpravyEngine : IEngine, IConfigured
    {
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";
        private const string LegColor = "#f59e0b";
        private const long MinMs = 60000L;
        private const double NoTpR = 1000.0;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private sealed class Ev
        {
            public long T;
            public string Typ;
            public bool Trend;
            public long A, B, HoldMs;
            public bool HasP0;
            public double P0;
            public double Hi = double.NegativeInfinity, Lo = double.PositiveInfinity;
            public bool Done;
        }

        private readonly SpravyConfig _cfg;
        /// <summary>Config strategie - `EntryLayers.Wrap` z neho berie defaulty klucov, ktore profil nema.</summary>
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        private readonly TimeZoneInfo _ny, _sk;
        public readonly BarHistory History;
        private readonly List<Ev> _events = new List<Ev>();
        private int _nextI;
        private long? _exitMs;
        private string _pending;
        private int _pendingIdx = -1;
        private List<string> _boxes = new List<string>();
        private bool _wasIn;

        public SpravyEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(SpravyConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public SpravyEngine(SpravyConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * MinMs;
            _ny = TimeZones.Get("America/New_York");
            _sk = TimeZones.Get("Europe/Bratislava");
            History = new BarHistory(4, cfg.atrLen);
            _warmup = new Warmup(_tf).Add("ATR " + I(cfg.atrLen), WarmupMath.RmaBars(cfg.atrLen) + 1);
            _requiredHistory = Math.Max(1, _warmup.ChartBars);
            BuildEvents();
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

        private static string I(int x) { return x.ToString(CultureInfo.InvariantCulture); }
        private static string Ms(long ms) { return ms.ToString(CultureInfo.InvariantCulture); }

        // ---- kalendar ------------------------------------------------------- //

        private long ToUtcMs(int y, int m, int d, int h, int min)
        {
            DateTime local = new DateTime(y, m, d, h, min, 0, DateTimeKind.Unspecified);
            DateTime utc = TimeZoneInfo.ConvertTimeToUtc(local, _ny);
            return (long)(utc - Epoch).TotalMilliseconds;
        }

        /// <summary>„14:30 SK / 8:30 NY“ - ten isty text ako `engine.sk_time` v Pythone.</summary>
        private string SkTime(long ms)
        {
            DateTime u = Epoch.AddMilliseconds(ms);
            DateTime sk = TimeZoneInfo.ConvertTimeFromUtc(u, _sk);
            DateTime ny = TimeZoneInfo.ConvertTimeFromUtc(u, _ny);
            return sk.ToString("HH:mm", CultureInfo.InvariantCulture) + " SK / " + I(ny.Hour) + ":"
                   + ny.ToString("mm", CultureInfo.InvariantCulture) + " NY";
        }

        private void BuildEvents()
        {
            SpravyConfig cfg = _cfg;
            HashSet<string> trend = SpravyConfig.Types(cfg.trendEvents), fade = SpravyConfig.Types(cfg.fadeEvents);
            HashSet<string> skip = new HashSet<string>();
            foreach (string part in (cfg.newsSkip ?? "").Replace("\n", ";").Split(';'))
            {
                string[] bits = part.Split((char[])null, StringSplitOptions.RemoveEmptyEntries);
                if (bits.Length == 2) skip.Add(bits[0] + "|" + bits[1].ToUpperInvariant());
            }
            // (UTC ms, typ) bez duplicit, zoradene ako Python `sorted(set(...))`
            SortedSet<KeyValuePair<long, string>> all = new SortedSet<KeyValuePair<long, string>>(new PairCmp());
            foreach (SpravyCalendar.Ev e in SpravyCalendar.Events)
            {
                if (!trend.Contains(e.Type) && !fade.Contains(e.Type)) continue;
                string day = e.Y.ToString("D4", CultureInfo.InvariantCulture) + "-" + e.M.ToString("D2", CultureInfo.InvariantCulture)
                             + "-" + e.D.ToString("D2", CultureInfo.InvariantCulture);
                if (skip.Contains(day + "|" + e.Type)) continue;
                all.Add(new KeyValuePair<long, string>(ToUtcMs(e.Y, e.M, e.D, e.H, e.Min), e.Type));
            }
            foreach (string part in (cfg.newsAdd ?? "").Replace("\n", ";").Split(';'))
            {
                string[] bits = part.Split((char[])null, StringSplitOptions.RemoveEmptyEntries);
                if (bits.Length != 3) continue;
                string typ = bits[2].ToUpperInvariant();
                if (!trend.Contains(typ) && !fade.Contains(typ)) continue;
                DateTime d = DateTime.ParseExact(bits[0], "yyyy-MM-dd", CultureInfo.InvariantCulture);
                string[] hm = bits[1].Split(':');
                all.Add(new KeyValuePair<long, string>(ToUtcMs(d.Year, d.Month, d.Day, int.Parse(hm[0], CultureInfo.InvariantCulture),
                                                                int.Parse(hm[1], CultureInfo.InvariantCulture)), typ));
            }
            foreach (KeyValuePair<long, string> kv in all)
            {
                bool tr = trend.Contains(kv.Value);
                int fr = tr ? cfg.trendFrom : cfg.fadeFrom, to = tr ? cfg.trendTo : cfg.fadeTo, hold = tr ? cfg.trendHold : cfg.fadeHold;
                Ev ev = new Ev();
                ev.T = kv.Key; ev.Typ = kv.Value; ev.Trend = tr;
                ev.A = kv.Key + fr * MinMs; ev.B = kv.Key + to * MinMs; ev.HoldMs = hold * MinMs;
                _events.Add(ev);
            }
        }

        private sealed class PairCmp : IComparer<KeyValuePair<long, string>>
        {
            public int Compare(KeyValuePair<long, string> x, KeyValuePair<long, string> y)
            {
                int c = x.Key.CompareTo(y.Key);
                return c != 0 ? c : string.CompareOrdinal(x.Value, y.Value);
            }
        }

        // ---- obchod ------------------------------------------------------- //

        private TradePlan Plan(bool isLong, double close, Ev ev)
        {
            SpravyConfig cfg = _cfg;
            double atr = History.Atr;
            double stop;
            double mult = ev.Trend ? cfg.trendStopLeg : cfg.fadeStopLeg;
            if (mult > 0 && ev.HasP0)
            {
                double leg = Math.Abs(close - ev.P0);
                stop = isLong ? close - mult * leg : close + mult * leg;
            }
            else
            {
                double buf = (atr > 0 || cfg.slBuffer.Unit != "atr") ? cfg.slBuffer.Resolve(_inst, close, atr) : 0.0;
                stop = isLong ? ev.Lo - buf : ev.Hi + buf;
            }
            double risk = Math.Abs(close - stop);
            if (risk < _inst.TickSize * 2 || (isLong && stop >= close) || (!isLong && stop <= close)) return null;
            double rTp = cfg.tpR > 0 ? cfg.tpR : NoTpR;
            double take = isLong ? close + rTp * risk : close - rTp * risk;
            double sizeRisk = (cfg.sizeMinRisk > 0 && atr > 0) ? Math.Max(risk, cfg.sizeMinRisk * atr) : risk;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, sizeRisk);
            if (q <= 0) q = _inst.MinQty > 0 ? _inst.MinQty : 1.0;
            return new TradePlan(isLong ? Direction.Long : Direction.Short, _inst.RoundPrice(close), _inst.RoundPrice(stop),
                                 _inst.RoundPrice(take), q, risk, null);
        }

        private void Enter(EngineOutput o, Bar bar, Ev ev, int idx)
        {
            SpravyConfig cfg = _cfg;
            if (!ev.HasP0 || bar.Close == ev.P0) return;
            bool up = bar.Close > ev.P0;
            bool isLong = ev.Trend ? up : !up;
            if ((isLong && !cfg.allowLong) || (!isLong && !cfg.allowShort)) return;
            double atr = History.Atr;
            if (cfg.minLeg.Value > 0 && Math.Abs(bar.Close - ev.P0) < cfg.minLeg.Resolve(_inst, bar.Close, atr)) return;
            TradePlan plan = Plan(isLong, bar.Close, ev);
            if (plan == null) return;
            long end = bar.Time + _stepMs;
            string oid = "sp:" + I(idx);
            string mode = ev.Trend ? "TREND" : "FADE";
            OrderIntent intent = new OrderIntent(OrderAction.Entry, oid, idx,
                ev.Typ + " " + SkTime(ev.T) + ": " + mode + " " + (isLong ? "long" : "short") + " (noha " + (up ? "hore" : "dole") + ")");
            intent.Direction = plan.Direction;
            intent.Plan = plan;
            intent.OrderType = OrderType.Market;
            o.Orders.Add(intent);
            _pending = oid;
            _pendingIdx = idx;
            _exitMs = end + ev.HoldMs;
            long x1 = end;
            _boxes = new List<string>();
            _wasIn = false;
            if (cfg.showLegs)
            {
                DrawBox leg = new DrawBox(SpravyKinds.Leg, ev.A, ev.Hi, ev.B, ev.Lo, LegColor);
                leg.FillColor = Palette.WithAlpha(LegColor, 35);
                leg.ObjId = "sp.leg." + Ms(ev.T);
                leg.Text = ev.Typ + " " + SkTime(ev.T);
                o.Drawings.Add(leg);
            }
            DrawBox sl = new DrawBox(DrawKinds.SlBox, x1, Math.Max(plan.Entry, plan.StopLoss), x1 + _stepMs,
                                     Math.Min(plan.Entry, plan.StopLoss), ShortColor);
            sl.FillColor = Palette.WithAlpha(ShortColor, 60);
            sl.ObjId = "sp.sl." + Ms(x1);
            sl.Text = "SL " + PyMath.FormatG(plan.StopLoss);
            o.Drawings.Add(sl);
            _boxes.Add("sp.sl." + Ms(x1));
            DrawLabel label = new DrawLabel(SpravyKinds.Entry, x1, plan.Entry, ev.Typ + " " + mode + " " + (isLong ? "LONG" : "SHORT"), "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "sp.e." + Ms(x1);
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
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            long end = bar.Time + _stepMs;
            bool flat = ctx.PositionSize == 0.0;
            if (_pending != null && (!flat || ctx.OpenOrderIds.Contains(_pending))) _pending = null;
            else if (_pending != null && idx - _pendingIdx > 2) _pending = null;   // market vstup sa nevyplnil - necakat nan

            // ---- boxy beziaceho obchodu --------------------------------------
            if (_boxes.Count > 0)
            {
                foreach (string oid in _boxes) o.Drawings.Add(new DrawUpdate(oid, "x2_ms", end));
                if (!flat) _wasIn = true;
                else if (_wasIn) { _boxes = new List<string>(); _wasIn = false; }
            }

            // ---- 1. vystup v case ---------------------------------------------
            if (!flat && _exitMs.HasValue && end >= _exitMs.Value)
            {
                o.CloseSession = true;
                foreach (string oid in ctx.OpenOrderIds)
                    o.Orders.Add(new OrderIntent(OrderAction.Close, oid, idx, "koniec držania po správe"));
                _exitMs = null;
            }
            if (flat && _pending == null) _exitMs = null;

            // ---- 2.-3. noha a vstup ------------------------------------------
            while (_nextI < _events.Count && _events[_nextI].B + _stepMs <= bar.Time) _nextI += 1;
            int i = _nextI;
            while (i < _events.Count && _events[i].T <= end)
            {
                Ev ev = _events[i];
                if (!ev.Done)
                {
                    if (!ev.HasP0)
                    {
                        if (ev.A == ev.T && bar.Time == ev.A) { ev.HasP0 = true; ev.P0 = bar.Open; }
                        else if (ev.A != ev.T && end == ev.A) { ev.HasP0 = true; ev.P0 = bar.Close; }
                    }
                    if (ev.A <= bar.Time && bar.Time < ev.B)
                    {
                        ev.Hi = Math.Max(ev.Hi, bar.High);
                        ev.Lo = Math.Min(ev.Lo, bar.Low);
                    }
                    if (end >= ev.B)
                    {
                        ev.Done = true;
                        if (flat && _pending == null && !o.CloseSession) Enter(o, bar, ev, idx);
                    }
                }
                i += 1;
            }
            while (_nextI < _events.Count && _events[_nextI].Done) _nextI += 1;
            return o;
        }
    }
}
