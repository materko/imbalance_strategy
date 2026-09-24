// `OrbEngine` - strategia ORBNinja (Opening Range Breakout) s jadrom v C#. Zrkadlo
// `tradebot/strategies/orb/engine.py`; s Python enginom sa porovnava bar po bare, na rovnost.
//
// Priebeh jednej seansy v jeden den:
//   1. bary od otvorenia seansy po `rangeMinutes` stavaju opening range (high/low)
//   2. ked okno rangu skonci, range sa uzavrie a skontroluju sa filtre sirky
//   3. v obchodnom okne sa caka na prerazenie hranice (close za nou + buffer)
//   4. podla `entryMode` sa vstupi hned, alebo sa caka na retest hranice
//   5. SL a TP sa pocitaju podla `slMode` / `tpMode`
//   6. na konci seansy sa pozicia zatvori (`closeAtSessionEnd`)
//
// Seansy su nezavisle (New York a Londyn maju vlastny range, denny limit aj koniec) a spracuvaju
// sa v poradi; nova pozicia sa neotvori, kym je ina otvorena.
//
// Engine je CISTY: ziadne I/O, ziadny globalny stav - preto ten isty kod bezi v NinjaTraderi
// aj pod Freqtrade (cez most) a dava rovnake signaly.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.OrbNinja
{
    [TradeBotEngine("orbninja", "ORBNinja Opening Range Breakout (C#)")]
    public sealed class OrbEngine : IEngine
    {
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        /// <summary>Stav jednej seansy v jeden den.</summary>
        private sealed class SessionState
        {
            public string Day;
            public double? High;
            public double? Low;
            public long OpenMs;
            public bool Closed;
            public bool Ok;
            public int Trades;
            public Direction? BreakDir;
            public double BreakLevel;
            public int BreakBar = -1;
            public double BreakExtreme;

            public void Reset(string day, long tsMs)
            {
                Day = day;
                High = null;
                Low = null;
                OpenMs = tsMs;
                Closed = false;
                Ok = false;
                Trades = 0;
                BreakDir = null;
                BreakBar = -1;
            }
        }

        public readonly OrbConfig Cfg;
        private readonly InstrumentSpec _inst;
        private readonly int _chartTfMinutes;
        private readonly long _stepMs;
        private readonly OrbSession[] _sessions;
        private readonly TimeZoneInfo[] _zones;
        private readonly SessionState[] _state;
        public readonly BarHistory History;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;

        /// <summary>v ktorej seanse vznikla otvorena pozicia - jej koniec ju aj zatvori</summary>
        private string _openSession;
        /// <summary>nevyplneny vstup: id orderu a bar, na ktorom vznikol</summary>
        private string _pendingId;
        private int _pendingBar;

        public OrbEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(OrbConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public OrbEngine(OrbConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            Cfg = cfg;
            _inst = inst;
            _chartTfMinutes = Math.Max(1, chartTfMinutes);
            _stepMs = _chartTfMinutes * 60000L;

            _sessions = cfg.Sessions();
            _zones = new TimeZoneInfo[_sessions.Length];
            _state = new SessionState[_sessions.Length];
            for (int i = 0; i < _sessions.Length; i++)
            {
                _zones[i] = TimeZones.Get(_sessions[i].Tz);
                _state[i] = new SessionState();
            }

            // predhistoria grafu: ATR a SMA objemu (seansa sa do nej nepocita)
            _warmup = new Warmup(_chartTfMinutes).Add(
                "ATR " + cfg.atrLen + " + SMA objemu " + cfg.volSmaLen, cfg.atrLen + cfg.volSmaLen + 16);
            _requiredHistory = _warmup.ChartBars;
            History = new BarHistory(_requiredHistory + 16, cfg.atrLen);
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
            s["sessions"] = _sessions.Length;
            s["max_trades_per_day"] = Cfg.maxTradesPerDay;
            s["close_at_session_end"] = Cfg.closeAtSessionEnd ? 1 : 0;
            s["leverage"] = Cfg.leverage;
            return s;
        }

        // ------------------------------------------------------------------ //
        // plan obchodu
        // ------------------------------------------------------------------ //

        private double? StopLevel(SessionState st, Direction direction, double entry, double atr)
        {
            bool isLong = direction == Direction.Long;
            if (!st.High.HasValue || !st.Low.HasValue) return null;
            double hi = st.High.Value, lo = st.Low.Value;
            double stopBase;
            if (Cfg.slMode == OrbSlMode.Opposite)
            {
                stopBase = isLong ? lo : hi;
            }
            else if (Cfg.slMode == OrbSlMode.Mid)
            {
                stopBase = (hi + lo) / 2.0;
            }
            else if (Cfg.slMode == OrbSlMode.RangePct)
            {
                // od prerazenej hranice smerom do rangu; 100 % = opacna hrana
                double depth = (hi - lo) * (Cfg.slRangePct / 100.0);
                stopBase = isLong ? hi - depth : lo + depth;
            }
            else if (Cfg.slMode == OrbSlMode.BreakCandle)
            {
                stopBase = st.BreakExtreme;
            }
            else
            {
                double dist = Cfg.slAtrMult.Resolve(_inst, entry, atr);
                stopBase = isLong ? entry - dist : entry + dist;
            }
            double buffer = Cfg.slBufferAtr.Resolve(_inst, entry, atr);
            return isLong ? stopBase - buffer : stopBase + buffer;
        }

        /// <summary>Python `x or entry` - 0.0 aj None padaju na vstupnu cenu.</summary>
        private static double OrEntry(double? v, double entry)
        {
            return v.HasValue && v.Value != 0.0 ? v.Value : entry;
        }

        private double TargetLevel(SessionState st, Direction direction, double entry, double slDistance, double atr)
        {
            bool isLong = direction == Direction.Long;
            double hi = OrEntry(st.High, entry), lo = OrEntry(st.Low, entry);
            double dist;
            if (Cfg.tpMode == OrbTpMode.Rr) dist = slDistance * Cfg.rrRatio;
            else if (Cfg.tpMode == OrbTpMode.Measured) dist = (hi - lo) * Cfg.measuredMult;
            else dist = Cfg.tpAtrMult.Resolve(_inst, entry, atr);
            return isLong ? entry + dist : entry - dist;
        }

        private TradePlan Plan(SessionState st, Direction direction, double entry, double atr)
        {
            double? stop = StopLevel(st, direction, entry, atr);
            if (!stop.HasValue) return null;
            double slDistance = Math.Abs(entry - stop.Value);
            if (slDistance < _inst.TickSize * 2) return null;
            // Rozsirenie portu: obchod s prilis tesnym SL sa preskoci (poplatok k edge).
            double minSl = Cfg.minSlDistance.Resolve(_inst, entry, atr);
            if (minSl > 0 && slDistance < minSl) return null;
            double take = TargetLevel(st, direction, entry, slDistance, atr);
            if ((direction == Direction.Long && take <= entry) || (direction == Direction.Short && take >= entry))
                return null;

            double qty = Cfg.riskDollar > 0 ? Cfg.PositionQty(_inst, Cfg.riskDollar, slDistance) : 1.0;
            if (qty <= 0) qty = _inst.MinQty != 0.0 ? _inst.MinQty : 1.0;

            TrailingPlan trailing = null;
            if (Cfg.enableTrailing)
            {
                double act = slDistance * Cfg.trailActivationR;
                double off = slDistance * Cfg.trailOffsetR;
                double tick = _inst.TickSize != 0.0 ? _inst.TickSize : 1.0;
                trailing = new TrailingPlan(act, off, act / tick, off / tick);
            }
            return new TradePlan(direction, _inst.RoundPrice(entry), _inst.RoundPrice(stop.Value),
                                 _inst.RoundPrice(take), qty, slDistance, trailing);
        }

        // ------------------------------------------------------------------ //
        // filtre
        // ------------------------------------------------------------------ //

        private bool RangePasses(SessionState st, double price)
        {
            if (!st.High.HasValue || !st.Low.HasValue || price <= 0) return false;
            double widthPct = (st.High.Value - st.Low.Value) / price * 100.0;
            return Cfg.minRangePct <= widthPct && widthPct <= Cfg.maxRangePct;
        }

        private bool VolumeOk(Bar bar)
        {
            if (!Cfg.useVolumeFilter) return true;
            int n = Cfg.volSmaLen;
            if (!History.Has(n)) return false;
            // Python predloha tu ma `sum(...)` - kompenzovana suma, nie cyklus (PyMath.Sum)
            double[] volumes = new double[n];
            for (int i = 1; i <= n; i++) volumes[i - 1] = History[i].Volume;
            double avg = PyMath.Sum(volumes) / n;
            return avg > 0 && bar.Volume >= avg * Cfg.volMultiplier;
        }

        private bool ClosePositionOk(Bar bar, bool isLong)
        {
            double span = bar.High - bar.Low;
            if (span <= 0) return true;
            double pos = (bar.Close - bar.Low) / span * 100.0;
            return isLong ? pos >= Cfg.minClosePosPct : (100.0 - pos) >= Cfg.minClosePosPct;
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
            double atr = History.Atr;
            int idx = History.BarIndex;

            // zrusenie nevyplnenej limitky z predchadzajuceho baru
            if (_pendingId != null && ctx.PositionSize == 0.0 && idx - _pendingBar >= 1)
            {
                o.Orders.Add(new OrderIntent(OrderAction.Cancel, _pendingId, _pendingBar, "nevyplnené"));
                _pendingId = null;
            }
            if (ctx.PositionSize != 0.0) _pendingId = null;
            if (ctx.PositionSize == 0.0) _openSession = null;

            for (int i = 0; i < _sessions.Length; i++) OnSession(o, i, bar, atr, idx, ctx);
            return o;
        }

        private void OnSession(EngineOutput o, int si, Bar bar, double atr, int idx, MarketContext ctx)
        {
            OrbSession sess = _sessions[si];
            SessionState st = _state[si];
            DateTime local = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zones[si]);
            if (Cfg.weekdaysOnly && (local.DayOfWeek == DayOfWeek.Saturday || local.DayOfWeek == DayOfWeek.Sunday))
                return;
            int minutes = local.Hour * 60 + local.Minute;

            // Python tuple `(rok, mesiac, den)` - aj v obj_id kresieb, preto presne v jeho tvare
            string day = "(" + local.Year.ToString(CultureInfo.InvariantCulture) + ", "
                       + local.Month.ToString(CultureInfo.InvariantCulture) + ", "
                       + local.Day.ToString(CultureInfo.InvariantCulture) + ")";
            if (day != st.Day) st.Reset(day, bar.Time);

            // ---- 1. stavanie rangu ------------------------------------------ //
            if (sess.StartMinutes <= minutes && minutes < sess.RangeEndMinutes)
            {
                st.High = st.High.HasValue ? Math.Max(st.High.Value, bar.High) : bar.High;
                st.Low = st.Low.HasValue ? Math.Min(st.Low.Value, bar.Low) : bar.Low;
                st.OpenMs = Math.Min(st.OpenMs != 0 ? st.OpenMs : bar.Time, bar.Time);
                return;
            }

            // ---- 2. range prave uzavrety ------------------------------------ //
            if (!st.Closed && minutes >= sess.RangeEndMinutes && st.High.HasValue && st.Low.HasValue)
            {
                st.Closed = true;
                st.Ok = RangePasses(st, bar.Close);
                if (Cfg.showRange)
                {
                    DrawBox box = new DrawBox(OrbKinds.Box, st.OpenMs, st.High.Value, bar.Time, st.Low.Value,
                                              sess.Key == "london" ? "#a855f728" : "#3b82f628");
                    box.ObjId = "orb." + sess.Key + "." + day;
                    box.Text = sess.Title + " range";
                    o.Drawings.Add(box);
                }
                if (Cfg.showLevels)
                {
                    long endMs = bar.Time + _stepMs * 120;
                    string color = sess.Key == "london" ? "#a855f7b3" : "#3b82f6b3";
                    DrawLine high = new DrawLine(OrbKinds.High, bar.Time, st.High.Value, endMs, st.High.Value, color);
                    high.ObjId = "orbh." + sess.Key + "." + day;
                    high.Text = sess.Title + " high";
                    o.Drawings.Add(high);
                    DrawLine low = new DrawLine(OrbKinds.Low, bar.Time, st.Low.Value, endMs, st.Low.Value, color);
                    low.ObjId = "orbl." + sess.Key + "." + day;
                    low.Text = sess.Title + " low";
                    o.Drawings.Add(low);
                }
            }

            // ---- 6. koniec seansy - zatvara len ta, v ktorej pozicia vznikla -- //
            if (minutes >= sess.EndMinutes)
            {
                if (Cfg.closeAtSessionEnd && ctx.PositionSize != 0.0 && _openSession == sess.Key)
                {
                    o.CloseSession = true;
                    List<string> ids = new List<string>(ctx.OpenOrderIds);
                    ids.Sort(StringComparer.Ordinal);
                    foreach (string orderId in ids)
                        o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx, "koniec seansy " + sess.Title));
                    _openSession = null;
                }
                st.BreakDir = null;
                return;
            }

            // ---- mantinely obchodneho okna ----------------------------------- //
            if (!(st.Closed && st.Ok) || minutes < sess.RangeEndMinutes) return;
            if (Cfg.entryWindowMinutes > 0 && minutes > sess.StartMinutes + Cfg.entryWindowMinutes) return;
            if (st.Trades >= Cfg.maxTradesPerDay) return;
            if (ctx.PositionSize != 0.0 || _pendingId != null) return;

            double hi = st.High.Value, lo = st.Low.Value;
            double buffer = Cfg.breakBufferAtr.Resolve(_inst, bar.Close, atr);

            // ---- 3. hladanie prerazenia -------------------------------------- //
            if (!st.BreakDir.HasValue)
            {
                bool longBreak = Cfg.AllowLong && bar.Close > hi + buffer;
                bool shortBreak = Cfg.AllowShort && bar.Close < lo - buffer;
                if (!(longBreak || shortBreak)) return;
                if (!VolumeOk(bar) || !ClosePositionOk(bar, longBreak)) return;
                st.BreakDir = longBreak ? Direction.Long : Direction.Short;
                st.BreakLevel = longBreak ? hi : lo;
                st.BreakBar = idx;
                st.BreakExtreme = longBreak ? bar.Low : bar.High;

                if (Cfg.entryMode == OrbEntryMode.Retest) return; // caka sa na navrat k hranici
                double entry = Cfg.entryMode == OrbEntryMode.Close ? bar.Close : st.BreakLevel;
                OrderType orderType = Cfg.entryMode == OrbEntryMode.Close ? OrderType.Market : OrderType.Stop;
                Enter(o, sess, st, st.BreakDir.Value, entry, atr, idx, bar, orderType, "prerazenie " + sess.Title);
                return;
            }

            // ---- 4. retest --------------------------------------------------- //
            if (Cfg.entryMode == OrbEntryMode.Retest)
            {
                if (idx - st.BreakBar > Cfg.retestMaxBars)
                {
                    st.BreakDir = null;
                    return;
                }
                bool isLong = st.BreakDir.Value == Direction.Long;
                bool touched = isLong ? bar.Low <= st.BreakLevel : bar.High >= st.BreakLevel;
                if (touched)
                    Enter(o, sess, st, st.BreakDir.Value, st.BreakLevel, atr, idx, bar, OrderType.Limit,
                          "retest hranice " + sess.Title);
            }
        }

        // ------------------------------------------------------------------ //

        private void Enter(EngineOutput o, OrbSession sess, SessionState st, Direction direction, double entry,
                           double atr, int idx, Bar bar, OrderType orderType, string reason)
        {
            TradePlan plan = Plan(st, direction, entry, atr);
            if (plan == null)
            {
                st.BreakDir = null;
                return;
            }
            string orderId = "orb:" + sess.Key + ":" + idx.ToString(CultureInfo.InvariantCulture);
            OrderIntent intent = new OrderIntent(OrderAction.Entry, orderId, idx, reason);
            intent.Direction = direction;
            intent.Plan = plan;
            intent.OrderType = orderType;
            o.Orders.Add(intent);
            _pendingId = orderId;
            _pendingBar = idx;
            _openSession = sess.Key;
            st.Trades += 1;
            st.BreakDir = null;

            bool isLong = direction == Direction.Long;
            DrawLabel label = new DrawLabel(OrbKinds.Entry, bar.Time, isLong ? bar.Low : bar.High,
                                            (isLong ? "LONG " : "SHORT ") + sess.Title, "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "orb_entry." + sess.Key + "." + bar.Time.ToString(CultureInfo.InvariantCulture);
            o.Drawings.Add(label);
        }
    }
}
