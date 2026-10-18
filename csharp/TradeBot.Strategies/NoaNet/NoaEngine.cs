// `NoaEngine` - NOA 1.0 (Noise Area, Concretum) s jadrom v C#. Zrkadlo `tradebot/strategies/noa/engine.py`; s Python
// enginom sa porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy).
//
// Priebeh dna (cas New York, seansa 9:30-16:00, minuta = cas ZAVRETIA baru):
//   1. Na kazdom bare seansy sa ulozi |close / open dna - 1| pre jeho minutu od 9:30; pasmo sumu sigma pre minutu
//      je priemer z `lookbackDays` predoslych dni (dnesok sa do neho prida az na konci dna).
//   2. Hranice: horna = max(open, vcerajsie zavretie) * (1 + volMult * sigma), dolna = min(...) * (1 - volMult * sigma).
//   3. Rozhoduje sa len na kontrolach (kazdych `checkEvery` minut od 9:30). Bez pozicie: zavretie nad hornou = long,
//      pod dolnou = short (do `lastEntryMin`). S poziciou: long sa zavrie pod max(horna, VWAP) (`trailVwap`), short
//      zrkadlovo.
//   4. Bar zatvarajuci sa o 16:00 zavrie poziciu; pozicia z predosleho dna sa zavrie na prvom bare seansy.
// Pevny stop v plane je len poistka `hardStopPct`. Vstup aj vystupy su market na zavreti baru.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.NoaNet
{
    [TradeBotEngine("noanet", "NOA 1.0 (C#)")]
    public sealed class NoaEngine : IEngine
    {
        private const string Ny = "America/New_York";
        private const int OpenMin = 9 * 60 + 30;
        private const int CloseMin = 16 * 60;
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";
        private const string VwapColor = "#a855f7";
        private const string StopColor = "#f59e0b";
        private const int VwapStepMin = 5;
        private const double NoStopPct = 10.0;
        /// <summary>bez ciela: TP tak daleko, ze ho cena nedosiahne (`_common.NO_TP_R`)</summary>
        private const double NoTpR = 100.0;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly NoaConfig _cfg;
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly TimeZoneInfo _zone;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        public readonly BarHistory History;

        /// <summary>minuta od 9:30 -> pohyby |close / open - 1| z predoslych dni (najstarsi prvy)</summary>
        private readonly Dictionary<int, List<double>> _hist = new Dictionary<int, List<double>>();
        private readonly List<KeyValuePair<int, double>> _today = new List<KeyValuePair<int, double>>();
        private bool _hasDay;
        private DateTime _day;
        private double? _open;
        private double? _prevClose;
        private double? _lastClose;
        private int _nextCheck;
        private int _trades;
        // seansovy VWAP (typicka cena x objem, kazdy den od nuly)
        private bool _hasVwapDay;
        private DateTime _vwapDay;
        private double _pv, _v;
        private bool _hasVwapPt;
        private long _vwapPtMs;
        private double _vwapPtValue;
        // kresba obchodu (boxy rastu, kym obchod bezi)
        private readonly List<string> _boxes = new List<string>();
        private bool _wasIn;

        public NoaEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(NoaConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public NoaEngine(NoaConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _zone = TimeZones.Get(Ny);
            _nextCheck = cfg.checkEvery;
            History = new BarHistory(4, 14);
            int days = cfg.lookbackDays + 2;
            _warmup = new Warmup(_tf).Add("pásmo šumu " + cfg.lookbackDays.ToString(CultureInfo.InvariantCulture) + " dní",
                                          days * 1440 / _tf);
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

        /// <summary>Pasmo sumu pre minutu `mm` od 9:30 - priemer z predoslych dni (aspon polovica `lookbackDays`).</summary>
        private double? Sigma(int mm)
        {
            List<double> d;
            if (!_hist.TryGetValue(mm, out d) || d.Count == 0 || d.Count < Math.Max(3, _cfg.lookbackDays / 2)) return null;
            return PyMath.Sum(d) / d.Count;
        }

        private bool Bounds(int mm, out double ub, out double lb)
        {
            ub = lb = 0.0;
            double? sg = Sigma(mm);
            if (!sg.HasValue || !_open.HasValue || !_prevClose.HasValue) return false;
            double hiRef = _cfg.gapAdjust ? Math.Max(_open.Value, _prevClose.Value) : _open.Value;
            double loRef = _cfg.gapAdjust ? Math.Min(_open.Value, _prevClose.Value) : _open.Value;
            ub = hiRef * (1 + _cfg.volMult * sg.Value);
            lb = loRef * (1 - _cfg.volMult * sg.Value);
            return true;
        }

        private void NewDay(DateTime day, Bar bar)
        {
            if (_hasDay)
            {
                int n = _cfg.lookbackDays;
                foreach (KeyValuePair<int, double> kv in _today)
                {
                    List<double> d;
                    if (!_hist.TryGetValue(kv.Key, out d)) { d = new List<double>(); _hist[kv.Key] = d; }
                    d.Add(kv.Value);
                    while (d.Count > n) d.RemoveAt(0);
                }
                _prevClose = _lastClose;
            }
            _today.Clear();
            _hasDay = true;
            _day = day;
            _open = bar.Open;
            _trades = 0;
            _nextCheck = _cfg.checkEvery;
            _hasVwapPt = false;
        }

        private void SetToday(int mm, double v)
        {
            for (int i = 0; i < _today.Count; i++)
                if (_today[i].Key == mm) { _today[i] = new KeyValuePair<int, double>(mm, v); return; }
            _today.Add(new KeyValuePair<int, double>(mm, v));
        }

        private double? PushVwap(DateTime day, Bar bar)
        {
            if (!_hasVwapDay || day != _vwapDay)
            {
                _hasVwapDay = true;
                _vwapDay = day;
                _pv = 0.0;
                _v = 0.0;
            }
            double tp = (bar.High + bar.Low + bar.Close) / 3.0;
            _pv += tp * bar.Volume;
            _v += bar.Volume;
            return _v > 0 ? (double?)(_pv / _v) : null;
        }

        private static List<string> SortedIds(MarketContext ctx)
        {
            List<string> ids = new List<string>(ctx.OpenOrderIds);
            ids.Sort(StringComparer.Ordinal);
            return ids;
        }

        private static void CloseAll(EngineOutput o, MarketContext ctx, int idx, string reason)
        {
            o.CloseSession = true;
            foreach (string orderId in SortedIds(ctx))
                o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx, reason));
        }

        private void Track(EngineOutput o, Bar bar, MarketContext ctx)
        {
            if (_boxes.Count == 0) return;
            foreach (string oid in _boxes)
                o.Drawings.Add(new DrawUpdate(oid, "x2_ms", bar.Time + _stepMs));
            if (ctx.PositionSize != 0.0) _wasIn = true;
            else if (_wasIn) { _boxes.Clear(); _wasIn = false; }
        }

        // ------------------------------------------------------------------ //

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            NoaConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            Track(o, bar, ctx);
            DateTime t = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time + _stepMs), _zone);
            DateTime day = t.Date;
            int m = t.Hour * 60 + t.Minute;
            bool weekend = t.DayOfWeek == DayOfWeek.Saturday || t.DayOfWeek == DayOfWeek.Sunday;
            if (!(OpenMin < m && m <= CloseMin) || (cfg.weekdaysOnly && weekend)) return o;
            double pos = ctx.PositionSize;
            if (!_hasDay || day != _day)
            {
                NewDay(day, bar);
                if (pos != 0.0)
                {
                    CloseAll(o, ctx, idx, "pozícia z predošlého dňa");
                    pos = 0.0;
                }
            }
            int mm = m - OpenMin;
            double? vw = PushVwap(day, bar);
            SetToday(mm, Math.Abs(bar.Close / _open.Value - 1.0));
            _lastClose = bar.Close;
            if (cfg.showVwap && vw.HasValue) o.Drawings.AddRange(DrawVwap(bar, m, vw.Value));

            // ---- 16:00: koniec seansy ------------------------------------------- //
            if (m + _tf > CloseMin)
            {
                if (pos != 0.0) CloseAll(o, ctx, idx, "koniec seansy 16:00");
                return o;
            }

            // ---- kontrola kazdych checkEvery minut -------------------------------- //
            if (mm < _nextCheck) return o;
            _nextCheck = (mm / cfg.checkEvery + 1) * cfg.checkEvery;
            double ub, lb;
            if (!Bounds(mm, out ub, out lb) || !vw.HasValue) return o;
            long end = bar.Time + _stepMs + cfg.checkEvery * 60000L;
            if (cfg.showLevels)
            {
                o.Drawings.Add(LevelLine(bar, ub, end, LongColor, "u", "horná hranica"));
                o.Drawings.Add(LevelLine(bar, lb, end, ShortColor, "d", "dolná hranica"));
            }
            double longStop = cfg.trailVwap ? Math.Max(ub, vw.Value) : ub;
            double shortStop = cfg.trailVwap ? Math.Min(lb, vw.Value) : lb;

            if (pos > 0.0)
            {
                if (bar.Close < longStop) CloseAll(o, ctx, idx, "zavretie pod hranicou / VWAP");
                else if (cfg.showLevels) o.Drawings.Add(StopLine(bar, longStop, end));
                return o;
            }
            if (pos < 0.0)
            {
                if (bar.Close > shortStop) CloseAll(o, ctx, idx, "zavretie nad hranicou / VWAP");
                else if (cfg.showLevels) o.Drawings.Add(StopLine(bar, shortStop, end));
                return o;
            }
            if (mm > cfg.lastEntryMin || _trades >= cfg.maxTradesPerDay) return o;
            bool goLong = cfg.AllowLong && bar.Close > ub;
            bool goShort = cfg.AllowShort && bar.Close < lb;
            if (!(goLong || goShort)) return o;
            bool isLong = goLong;
            double entry = bar.Close;
            double hard = (cfg.hardStopPct != 0.0 ? cfg.hardStopPct : NoStopPct) / 100.0 * entry;
            double stop = isLong ? entry - hard : entry + hard;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, hard);
            TradePlan plan = Plan(isLong, entry, stop, q > 0 ? q : 1.0);
            if (plan == null) return o;
            Enter(o, bar, idx, plan, isLong);
            _trades += 1;
            if (cfg.showLevels) o.Drawings.Add(StopLine(bar, isLong ? longStop : shortStop, end));
            return o;
        }

        // ------------------------------------------------------------------ //

        private TradePlan Plan(bool isLong, double entry, double stop, double qty)
        {
            double sl = Math.Abs(entry - stop);
            if (sl < _inst.TickSize * 2) return null;
            double take = isLong ? entry + NoTpR * sl : entry - NoTpR * sl;
            return new TradePlan(isLong ? Direction.Long : Direction.Short, _inst.RoundPrice(entry), _inst.RoundPrice(stop),
                                 _inst.RoundPrice(take), qty, sl, null);
        }

        private void Enter(EngineOutput o, Bar bar, int idx, TradePlan plan, bool isLong)
        {
            OrderIntent intent = new OrderIntent(OrderAction.Entry, "noa:" + idx.ToString(CultureInfo.InvariantCulture), idx,
                                                 "únik z pásma šumu");
            intent.Direction = plan.Direction;
            intent.Plan = plan;
            intent.OrderType = OrderType.Market;
            o.Orders.Add(intent);
            long t = bar.Time + _stepMs;          // market sa plni na otvoreni dalsej sviecky
            long end = t + _stepMs;
            _boxes.Clear();
            string oid = "noa.sl." + t.ToString(CultureInfo.InvariantCulture);
            DrawBox box = new DrawBox(DrawKinds.SlBox, t, Math.Max(plan.Entry, plan.StopLoss), end,
                                      Math.Min(plan.Entry, plan.StopLoss), ShortColor);
            box.FillColor = Palette.WithAlpha(ShortColor, 80);
            box.ObjId = oid;
            box.Text = "SL " + PyMath.FormatG(plan.StopLoss);
            o.Drawings.Add(box);
            _boxes.Add(oid);
            DrawLabel label = new DrawLabel(NoaKinds.Entry, t, plan.Entry, (isLong ? "LONG" : "SHORT") + " šum", "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "noa.e." + t.ToString(CultureInfo.InvariantCulture);
            o.Drawings.Add(label);
        }

        private DrawLine LevelLine(Bar bar, double y, long end, string color, string n, string text)
        {
            DrawLine line = new DrawLine(NoaKinds.Level, bar.Time + _stepMs, y, end, y, color);
            line.Style = LineStyles.Dotted;
            line.ObjId = "noa." + n + "." + bar.Time.ToString(CultureInfo.InvariantCulture);
            line.Text = text;
            return line;
        }

        /// <summary>Uroven vystupu do dalsej kontroly (max(hranica, VWAP) pri longu, min pri shorte).</summary>
        private DrawLine StopLine(Bar bar, double level, long end)
        {
            DrawLine line = new DrawLine(NoaKinds.Stop, bar.Time + _stepMs, level, end, level, StopColor);
            line.Style = LineStyles.Dashed;
            line.Width = 2;
            line.ObjId = "noa.stop." + bar.Time.ToString(CultureInfo.InvariantCulture);
            line.Text = "výstup na kontrole";
            return line;
        }

        private List<DrawCommand> DrawVwap(Bar bar, int m, double vw)
        {
            List<DrawCommand> cmds = new List<DrawCommand>();
            if (m % VwapStepMin != 0 && _tf < VwapStepMin) return cmds;
            long end = bar.Time + _stepMs;
            bool had = _hasVwapPt;
            long prevMs = _vwapPtMs;
            double prevValue = _vwapPtValue;
            _hasVwapPt = true;
            _vwapPtMs = end;
            _vwapPtValue = vw;
            if (!had) return cmds;
            DrawLine line = new DrawLine(NoaKinds.Vwap, prevMs, prevValue, end, vw, VwapColor);
            line.ObjId = "noa.vwap." + end.ToString(CultureInfo.InvariantCulture);
            line.Text = "VWAP";
            cmds.Add(line);
            return cmds;
        }
    }
}
