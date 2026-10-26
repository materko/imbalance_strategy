// `SdEurEngine` - SD ZONY EURUSD s jadrom v C#. Zrkadlo `tradebot/strategies/sdeur/engine.py`; s Python enginom sa
// porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy).
//
//   1. vyplnenie - cakajuca limitka sa vyplnila (pozicia alebo OpenOrderIds) -> obchod, TP / SL box,
//   2. drzanie - pozicia otvorena dlhsie nez `maxHoldHours` sa zavrie trhom,
//   3. dotyk - zona, ktorej blizsiu hranu bar dosiahol, je minuta (prvy navrat); zavretie za vzdialenejsou hranou
//      alebo vek nad `zoneMaxHours` ju zrusi,
//   4. zony - bary grafu sa skladaju do sviecok `zoneTF` (zarovnane na epochu); na uzavretej sviecke sa posunu
//      kandidati (prerazenie bazy -> von, odchod >= depMin -> zona) a vzniknu novi kandidati z bazy,
//   5. limitka - bez pozicie, ked sa dalsi bar otvara v okne vstupu: na najblizsiu nedotknutu zonu.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.SdEurNet
{
    [TradeBotEngine("sdeurnet", "SD ZÓNY EURUSD (C# jadro)")]
    public sealed class SdEurEngine : IEngine
    {
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";
        private const long HourMs = 3600000L;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private sealed class Zone
        {
            public int Side;            // 1 = supply (short), -1 = demand (long)
            public double Top, Bottom, Atr;
            public int BaseEnd;
            public long X1Ms, ReadyMs;
            public string ObjId = "";
            public bool Dead, Touched;
            public double Proximal { get { return Side == 1 ? Bottom : Top; } }
            public double Distal { get { return Side == 1 ? Top : Bottom; } }
        }

        private sealed class Cand
        {
            public Zone Zone;
            public int Q;
        }

        private readonly SdEurConfig _cfg;
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs, _zoneMs;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        private readonly TimeZoneInfo _ny;
        public readonly BarHistory History;

        // sviecky zoneTF: open_ms, high, low, close
        private readonly List<long> _zbT = new List<long>();
        private readonly List<double> _zbH = new List<double>(), _zbL = new List<double>(), _zbC = new List<double>();
        private int _zidx = -1;
        private bool _hasCur;
        private long _curT;
        private double _curH, _curL, _curC;
        private double _zatr;
        private bool _hasPrevClose;
        private double _prevClose;
        private List<Cand> _cands = new List<Cand>();
        private List<Zone> _zones = new List<Zone>();
        private string _pendingId;
        private int _pendingAt;
        private Zone _pendingZone;
        private TradePlan _pendingPlan;
        private long _pendingMs;
        private long? _fillMs;
        private List<string> _boxes = new List<string>();
        private bool _wasIn;
        private bool _hasDay;
        private DateTime _day;
        private int _trades;

        public SdEurEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(SdEurConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public SdEurEngine(SdEurConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _zoneMs = Math.Max(cfg.zoneTF, _tf) * 60000L;
            long ratio = Math.Max(1L, _zoneMs / _stepMs);
            _ny = TimeZones.Get("America/New_York");
            History = new BarHistory(4, 14);
            int need = cfg.atrLen * 3 + cfg.extremeBars + cfg.baseMaxBars + 2;
            _warmup = new Warmup(_tf).Add("zóny " + I(cfg.zoneTF) + "m (ATR " + I(cfg.atrLen) + " + báza)", (int)(need * ratio));
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

        private static string I(int x) { return x.ToString(CultureInfo.InvariantCulture); }
        private static string Ms(long ms) { return ms.ToString(CultureInfo.InvariantCulture); }
        private DateTime Ny(long ms) { return TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(ms), _ny); }

        private int NyMinutes(long ms)
        {
            DateTime t = Ny(ms);
            return t.Hour * 60 + t.Minute;
        }

        private static bool In(int m, int a, int b) { return a < b ? (a <= m && m < b) : (m >= a || m < b); }

        private static long FloorDiv(long a, long b)
        {
            long q = a / b;
            if ((a % b != 0) && ((a < 0) != (b < 0))) q -= 1;
            return q;
        }

        private void CloseZone(EngineOutput o, Zone z, Bar bar)
        {
            z.Dead = true;
            if (z.ObjId.Length > 0) o.Drawings.Add(new DrawUpdate(z.ObjId, "x2_ms", bar.Time + _stepMs));
        }

        // ---- sviecky zoneTF ---------------------------------------------------- //

        private bool FeedZoneBar(Bar bar)
        {
            long bucket = FloorDiv(bar.Time, _zoneMs) * _zoneMs;
            bool closed = false;
            if (_hasCur && _curT != bucket)
            {
                PushZoneBar();                 // diera v datach: predosla sviecka sa uzavrie az teraz
                closed = true;
            }
            if (!_hasCur)
            {
                _hasCur = true;
                _curT = bucket; _curH = bar.High; _curL = bar.Low; _curC = bar.Close;
            }
            else
            {
                _curH = Math.Max(_curH, bar.High);
                _curL = Math.Min(_curL, bar.Low);
                _curC = bar.Close;
            }
            if (bar.Time + _stepMs >= bucket + _zoneMs)
            {
                PushZoneBar();
                closed = true;
            }
            return closed;
        }

        private void PushZoneBar()
        {
            double h = _curH, l = _curL, c = _curC;
            double pc = _hasPrevClose ? _prevClose : c;
            double tr = Math.Max(h - l, Math.Max(Math.Abs(h - pc), Math.Abs(l - pc)));
            if (_zidx < 0) _zatr = h - l;
            else _zatr += (tr - _zatr) / _cfg.atrLen;
            _prevClose = c;
            _hasPrevClose = true;
            _zbT.Add(_curT); _zbH.Add(h); _zbL.Add(l); _zbC.Add(c);
            int keep = _cfg.extremeBars + _cfg.baseMaxBars + 4;
            if (_zbT.Count > keep)
            {
                int cut = _zbT.Count - keep;
                _zbT.RemoveRange(0, cut); _zbH.RemoveRange(0, cut); _zbL.RemoveRange(0, cut); _zbC.RemoveRange(0, cut);
            }
            _zidx += 1;
            _hasCur = false;
        }

        private void ZoneEvents(EngineOutput o, Bar bar)
        {
            SdEurConfig cfg = _cfg;
            int last = _zbT.Count - 1;
            double h = _zbH[last], l = _zbL[last];
            List<Cand> alive = new List<Cand>();
            HashSet<string> confirmed = new HashSet<string>();
            foreach (Cand c in _cands)
            {
                Zone z = c.Zone;
                c.Q += 1;
                if (z.Side == 1 ? h > z.Top : l < z.Bottom) continue;        // baza prerazena skor, nez cena odisla
                double dep = cfg.depMin.Resolve(_inst, bar.Close, z.Atr);
                if ((z.Side == 1 ? (z.Bottom - l) : (h - z.Top)) >= dep)
                {
                    string key = I(z.BaseEnd) + "/" + I(z.Side);
                    if (!confirmed.Contains(key))                             // z jednej bazy jedna zona na stranu
                    {
                        confirmed.Add(key);
                        Confirm(o, z, bar);
                    }
                    continue;
                }
                if (c.Q < cfg.depMaxBars) alive.Add(c);
            }
            _cands = alive;
            NewCandidates(bar);
        }

        private void Confirm(EngineOutput o, Zone z, Bar bar)
        {
            z.ReadyMs = bar.Time + _stepMs;
            _zones.Add(z);
            if (!_cfg.showZones) return;
            string color = z.Side == 1 ? ShortColor : LongColor;
            z.ObjId = "se.z." + Ms(z.X1Ms) + "." + I(z.Side) + "." + PyMath.FormatG(z.Top);
            long x2 = z.ReadyMs + _cfg.zoneMaxHours * HourMs;
            DrawBox box = new DrawBox(z.Side == 1 ? SdEurKinds.Supply : SdEurKinds.Demand, z.X1Ms, z.Top, x2, z.Bottom, color);
            box.FillColor = Palette.WithAlpha(color, 40);
            box.ObjId = z.ObjId;
            box.Text = (z.Side == 1 ? "supply " : "demand ") + I(_cfg.zoneTF) + "m";
            o.Drawings.Add(box);
        }

        private void NewCandidates(Bar bar)
        {
            SdEurConfig cfg = _cfg;
            int n = _zbT.Count;
            double a = _zatr;
            if (a <= 0) return;
            if (cfg.useFormWindow)
            {
                int hour = NyMinutes(_zbT[n - 1]) / 60;
                if (!In(hour, cfg.formStartH, cfg.formEndH)) return;
            }
            double maxH = cfg.baseMax.Resolve(_inst, bar.Close, a);
            double minZh = cfg.minZoneHeight.Resolve(_inst, bar.Close, a);
            double maxZh = cfg.maxZoneHeight.Resolve(_inst, bar.Close, a);
            int ext = cfg.extremeBars;
            for (int k = 1; k <= cfg.baseMaxBars; k++)
            {
                if (n < k + Math.Max(ext, 1) || _zidx + 1 < k + ext) break;
                double bh = double.NegativeInfinity, bl = double.PositiveInfinity;
                for (int j = n - k; j < n; j++)
                {
                    if (_zbH[j] > bh) bh = _zbH[j];
                    if (_zbL[j] < bl) bl = _zbL[j];
                }
                double height = bh - bl;
                if (height < 2 * _inst.TickSize || height > maxH) continue;
                if ((minZh > 0 && height < minZh) || (maxZh > 0 && height > maxZh)) continue;
                double prevMax = double.NegativeInfinity, prevMin = double.PositiveInfinity;
                for (int j = n - k - ext; j < n - k; j++)
                {
                    if (_zbH[j] > prevMax) prevMax = _zbH[j];
                    if (_zbL[j] < prevMin) prevMin = _zbL[j];
                }
                for (int side = 1; side >= -1; side -= 2)
                {
                    if ((side == 1 && !cfg.allowShort) || (side == -1 && !cfg.allowLong)) continue;
                    if (ext > 0 && (side == 1 ? bh < prevMax : bl > prevMin)) continue;
                    Zone z = new Zone();
                    z.Side = side; z.Top = bh; z.Bottom = bl; z.Atr = a; z.BaseEnd = _zidx; z.X1Ms = _zbT[n - k];
                    Cand c = new Cand();
                    c.Zone = z;
                    _cands.Add(c);
                }
            }
        }

        // ---- obchod ------------------------------------------------------------- //

        private TradePlan Plan(Zone z, double close)
        {
            SdEurConfig cfg = _cfg;
            bool isLong = z.Side == -1;
            double height = z.Top - z.Bottom;
            double depth = height * cfg.entryDepthPct / 100.0;
            double entry = z.Side == 1 ? z.Proximal + depth : z.Proximal - depth;
            double buf = cfg.slBuffer.Resolve(_inst, close, z.Atr) + _inst.TickSize;
            double stop = z.Side == 1 ? z.Distal + buf : z.Distal - buf;
            double risk = Math.Abs(entry - stop);
            if (risk < _inst.TickSize * 2) return null;
            double take = isLong ? entry + cfg.rrRatio * risk : entry - cfg.rrRatio * risk;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, risk);
            if (q <= 0) q = _inst.MinQty > 0 ? _inst.MinQty : 1.0;
            return new TradePlan(isLong ? Direction.Long : Direction.Short, _inst.RoundPrice(entry), _inst.RoundPrice(stop),
                                 _inst.RoundPrice(take), q, risk, null);
        }

        private void Filled(EngineOutput o, Bar bar)
        {
            Zone z = _pendingZone;
            TradePlan plan = _pendingPlan;
            _pendingId = null;
            _pendingZone = null;
            _pendingPlan = null;
            _trades += 1;
            _fillMs = bar.Time;
            bool isLong = plan.Direction == Direction.Long;
            _boxes = new List<string>();
            _wasIn = false;
            long x1 = _pendingMs, end = bar.Time + _stepMs;
            AddBox(o, DrawKinds.TpBox, "tp", "TP ", plan.TakeProfit, plan.Entry, LongColor, x1, end);
            AddBox(o, DrawKinds.SlBox, "sl", "SL ", plan.StopLoss, plan.Entry, ShortColor, x1, end);
            DrawLabel label = new DrawLabel(SdEurKinds.Entry, x1, plan.Entry, isLong ? "LONG zóna" : "SHORT zóna", "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "se.e." + Ms(x1);
            o.Drawings.Add(label);
            if (!z.Dead) CloseZone(o, z, bar);
        }

        private void AddBox(EngineOutput o, string kind, string tag, string prefix, double level, double entry, string color,
                            long t, long end)
        {
            string oid = "se." + tag + "." + Ms(t);
            DrawBox box = new DrawBox(kind, t, Math.Max(entry, level), end, Math.Min(entry, level), color);
            box.FillColor = Palette.WithAlpha(color, 60);
            box.ObjId = oid;
            box.Text = prefix + PyMath.FormatG(level);
            o.Drawings.Add(box);
            _boxes.Add(oid);
        }

        private void Cancel(EngineOutput o, string reason)
        {
            o.Orders.Add(new OrderIntent(OrderAction.Cancel, _pendingId, _pendingAt, reason));
            _pendingId = null;
            _pendingZone = null;
            _pendingPlan = null;
        }

        // ------------------------------------------------------------------ //

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            SdEurConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            double pos = ctx.PositionSize;
            DateTime day = Ny(bar.Time).Date;
            if (!_hasDay || day != _day) { _hasDay = true; _day = day; _trades = 0; }

            // ---- TP / SL boxy beziaceho obchodu ----------------------------------
            if (_boxes.Count > 0)
            {
                foreach (string oid in _boxes) o.Drawings.Add(new DrawUpdate(oid, "x2_ms", bar.Time + _stepMs));
                if (pos != 0.0) _wasIn = true;
                else if (_wasIn) { _boxes = new List<string>(); _wasIn = false; }
            }

            // ---- 1. vyplnenie limitky ----------------------------------------------
            if (_pendingId != null && (pos != 0.0 || ctx.OpenOrderIds.Contains(_pendingId))) Filled(o, bar);
            if (pos == 0.0) _fillMs = null;

            // ---- 2. najdlhsie drzanie ----------------------------------------------
            if (pos != 0.0 && cfg.maxHoldHours > 0 && _fillMs.HasValue
                && bar.Time + _stepMs - _fillMs.Value >= cfg.maxHoldHours * HourMs)
            {
                o.CloseSession = true;
                foreach (string oid in ctx.OpenOrderIds)
                    o.Orders.Add(new OrderIntent(OrderAction.Close, oid, idx, "drží sa " + I(cfg.maxHoldHours) + " h"));
                _fillMs = null;
            }

            // ---- 3. dotyk, zanik a vek zon -----------------------------------------
            List<Zone> live = new List<Zone>();
            foreach (Zone z in _zones)
            {
                if (z.Dead) continue;
                bool touched = z.Side == 1 ? bar.High >= z.Proximal : bar.Low <= z.Proximal;
                bool through = z.Side == 1 ? bar.Close > z.Top : bar.Close < z.Bottom;
                bool old = bar.Time + _stepMs - z.ReadyMs > cfg.zoneMaxHours * HourMs;
                bool mine = _pendingId != null && ReferenceEquals(_pendingZone, z);
                if (touched && mine) z.Touched = true;
                if (through || old || (touched && !mine))
                {
                    CloseZone(o, z, bar);
                    if (mine) Cancel(o, through ? "zóna prerazená" : "zóna vypršala");
                    continue;
                }
                live.Add(z);
            }
            _zones = live;

            // ---- 4. nove zony ------------------------------------------------------
            if (FeedZoneBar(bar)) ZoneEvents(o, bar);

            // ---- 5. limitka na najblizsiu zonu -------------------------------------
            if (pos == 0.0 && !o.CloseSession)
            {
                int nxt = NyMinutes(bar.Time + _stepMs);
                bool inWin = In(nxt, cfg.EntryStart, cfg.EntryEnd);
                bool limitOk = cfg.maxTradesPerDay <= 0 || _trades < cfg.maxTradesPerDay;
                Zone best = null;
                if (inWin && limitOk)
                {
                    List<Zone> cands = new List<Zone>();
                    foreach (Zone z in _zones)
                        if (!z.Dead && !z.Touched && z.ReadyMs <= bar.Time + _stepMs) cands.Add(z);
                    if (_pendingId != null && !_pendingZone.Dead && _pendingZone.Touched)
                    {
                        cands = new List<Zone>();
                        cands.Add(_pendingZone);
                    }
                    foreach (Zone z in cands)
                    {
                        if (best == null) { best = z; continue; }
                        double d = Math.Abs(z.Proximal - bar.Close), db = Math.Abs(best.Proximal - bar.Close);
                        if (d < db || (d == db && z.ReadyMs < best.ReadyMs)) best = z;
                    }
                }
                if (_pendingId != null && !ReferenceEquals(_pendingZone, best))
                    Cancel(o, !inWin ? "mimo okna vstupu" : "bližšia zóna");
                if (best != null && _pendingId == null)
                {
                    TradePlan plan = Plan(best, bar.Close);
                    if (plan == null)
                    {
                        CloseZone(o, best, bar);
                        _zones.Remove(best);
                    }
                    else
                    {
                        string oid = "se:" + I(idx);
                        OrderIntent intent = new OrderIntent(OrderAction.Entry, oid, idx,
                            (best.Side == 1 ? "supply" : "demand") + " zóna " + I(cfg.zoneTF) + "m");
                        intent.Direction = plan.Direction;
                        intent.Plan = plan;
                        intent.OrderType = OrderType.Limit;
                        o.Orders.Add(intent);
                        _pendingId = oid;
                        _pendingAt = idx;
                        _pendingZone = best;
                        _pendingPlan = plan;
                        _pendingMs = bar.Time;
                    }
                }
            }
            else if (_pendingId != null && pos != 0.0)
            {
                _pendingId = null;
                _pendingZone = null;
                _pendingPlan = null;
            }
            return o;
        }
    }
}
