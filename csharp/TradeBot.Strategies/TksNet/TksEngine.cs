// `TksEngine` - TKS 1.0 (NQ Kompas) s jadrom v C#. Zrkadlo `tradebot/strategies/tks/engine.py`; s Python enginom sa
// porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy).
//
// NQ Kompas sa pocita na baroch grafu len v seanse NY 9:30-16:00 (minuta = cas ZAVRETIA baru od 9:30):
//   * unik zo sumu: (close / open dna - 1) / sigma, sigma = priemer |close / open - 1| v tej istej minute za
//     `lookbackDays` predoslych dni (aspon polovica) -> tanh(x / 2),
//   * noc: poloha close v nocnom range (prvy bar po 18:00 az 9:30) -> (pos - 0,5) x 2, orezane +-1,5, / 1,5,
//   * tlak: suma (poloha zavretia v sviecke x objem) / suma objem od 9:30, / PressScale, orezane +-1,
//   * VWAP: podiel barov od 9:30 so zavretim nad VWAP (od 9:30) -> 2 x podiel - 1,
//   * Kompas = 50 + 50 x priemer styroch.
// Signal: `nConf` barov po sebe s Kompasom pod `loLevel` (short) / nad `hiLevel` (long); spotrebuje sa (aj ked sa
// nevstupi) a znova je k dispozicii, az ked Kompas odide od hranice. Vstup market na zavreti, SL na najblizsi
// potvrdeny swing (alebo ATR / body, so stropom), TP = close +- RR x |close - SL|; vstupy len v casovom okne.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.TksNet
{
    /// <summary>NQ Kompas bar po bare - zrkadlo triedy `Kompas` v `tradebot/strategies/tks/engine.py`.</summary>
    public sealed class Kompas
    {
        /// <summary>90. percentil |tlak| na MNQ 1m 2019-06 - 2025-09 (`PRESS_SCALE`)</summary>
        public const double PressScale = 0.1293;
        private const int OpenMin = 570;     // 9:30 New York
        private const int CloseMin = 960;    // 16:00
        private const int Slots = 391;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly int _tf;
        private readonly int _lookback;
        private readonly TimeZoneInfo _zone;
        private readonly List<double?[]> _hist = new List<double?[]>();
        private double?[] _today = new double?[Slots];
        private bool _hasDay;
        public DateTime Day;
        private double? _open;
        private double? _onHi, _onLo;           // beziaci nocny range
        private double? _dayOnHi, _dayOnLo;     // nocny range pred dnesnou seansou
        private bool _prevOn;
        private double _cpv, _cv, _pn;
        private int _nb, _na;
        public bool Rth;
        public int KClose;

        public Kompas(int tfMinutes, int lookback)
        {
            _tf = Math.Max(1, tfMinutes);
            _lookback = lookback;
            _zone = TimeZones.Get("America/New_York");
        }

        public bool HasDay { get { return _hasDay; } }

        /// <summary>Hodnota 0-100, alebo null (mimo seansy / malo historie).</summary>
        public double? Push(Bar bar)
        {
            DateTime t = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            int m = t.Hour * 60 + t.Minute;                 // minuta OTVORENIA baru
            bool weekday = t.DayOfWeek != DayOfWeek.Saturday && t.DayOfWeek != DayOfWeek.Sunday;
            bool rth = OpenMin <= m && m < CloseMin && weekday;
            bool onseg = (m >= 1080 || m < OpenMin) && !rth;
            Rth = rth;
            if (onseg && !_prevOn)
            {
                _onHi = bar.High;
                _onLo = bar.Low;
            }
            else if (onseg)
            {
                _onHi = Math.Max(_onHi.Value, bar.High);
                _onLo = Math.Min(_onLo.Value, bar.Low);
            }
            _prevOn = onseg;
            if (!rth) return null;
            DateTime day = t.Date;
            if (!_hasDay || day != Day)
            {
                if (_hasDay && _open.HasValue)
                {
                    _hist.Add(_today);
                    while (_hist.Count > _lookback) _hist.RemoveAt(0);
                }
                _today = new double?[Slots];
                _hasDay = true;
                Day = day;
                _open = bar.Open;
                _dayOnHi = _onHi;
                _dayOnLo = _onLo;
                _cpv = _cv = _pn = 0.0;
                _nb = _na = 0;
            }
            int k = m + _tf - OpenMin;
            KClose = k;
            if (!(1 <= k && k < Slots)) return null;
            double c = bar.Close;
            _today[k] = Math.Abs(c / _open.Value - 1);
            _cpv += (bar.High + bar.Low + c) / 3 * bar.Volume;
            _cv += bar.Volume;
            double rng = bar.High - bar.Low;
            double clv = rng > 0 ? ((c - bar.Low) - (bar.High - c)) / rng : 0.0;
            _pn += clv * bar.Volume;
            double vw = _cv > 0 ? _cpv / _cv : c;
            _nb += 1;
            if (c > vw) _na += 1;
            List<double> vals = new List<double>();
            foreach (double?[] d in _hist) if (d[k].HasValue) vals.Add(d[k].Value);
            if (vals.Count < Math.Max(3, _lookback / 2) || PyMath.Sum(vals) <= 0) return null;
            double sig = PyMath.Sum(vals) / vals.Count;
            double ne = (c / _open.Value - 1) / sig;
            double onpos = _dayOnHi.HasValue && _dayOnLo.HasValue && _dayOnHi.Value > _dayOnLo.Value
                ? (c - _dayOnLo.Value) / (_dayOnHi.Value - _dayOnLo.Value) : 0.5;
            double c1 = Math.Tanh(ne / 2.0);
            double c2 = Math.Max(-1.5, Math.Min(1.5, (onpos - 0.5) * 2.0)) / 1.5;
            double c3 = Math.Max(-1.0, Math.Min(1.0, (_cv > 0 ? _pn / _cv : 0.0) / PressScale));
            double c4 = 2.0 * _na / _nb - 1.0;
            return 50 + 50 * (c1 + c2 + c3 + c4) / 4;
        }
    }

    [TradeBotEngine("tksnet", "TKS 1.0 (C#)")]
    public sealed class TksEngine : IEngine
    {
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";

        private readonly TksConfig _cfg;
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        public readonly BarHistory History;
        public readonly Kompas Kompas;
        public double? Value;

        private readonly List<double> _swingHi = new List<double>();
        private readonly List<double> _swingLo = new List<double>();
        private int _cntDn, _cntUp;
        private bool _armedDn = true, _armedUp = true;
        private bool _hasSessDay;
        private DateTime _sessDay;
        private int _sessTrades;
        // kresba obchodu (boxy rastu, kym obchod bezi) - `TradeHelper` v `_common.py`
        private readonly List<string> _boxes = new List<string>();
        private bool _wasIn;

        public TksEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(TksConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public TksEngine(TksConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            Kompas = new Kompas(_tf, cfg.lookbackDays);
            History = new BarHistory(2 * cfg.pivLen + 4, cfg.atrLen);
            int days = cfg.lookbackDays + 2;
            _warmup = new Warmup(_tf).Add("NQ Kompas " + cfg.lookbackDays.ToString(CultureInfo.InvariantCulture) + " dní",
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

        private static void Bounded(List<double> list, double x)
        {
            list.Add(x);
            if (list.Count > 200) list.RemoveAt(0);
        }

        /// <summary>Swing potvrdeny `pivLen` barmi na kazdej strane (Python `_pivots`).</summary>
        private void Pivots()
        {
            int p = _cfg.pivLen;
            if (!History.Has(2 * p)) return;
            Bar mid = History[p];
            double hi = double.NegativeInfinity, lo = double.PositiveInfinity;
            for (int i = 0; i < 2 * p + 1; i++)
            {
                Bar b = History[i];
                if (b.High > hi) hi = b.High;
                if (b.Low < lo) lo = b.Low;
            }
            if (mid.High == hi) Bounded(_swingHi, mid.High);
            if (mid.Low == lo) Bounded(_swingLo, mid.Low);
        }

        private void Track(EngineOutput o, Bar bar, MarketContext ctx)
        {
            if (_boxes.Count == 0) return;
            foreach (string oid in _boxes)
                o.Drawings.Add(new DrawUpdate(oid, "x2_ms", bar.Time + _stepMs));
            if (ctx.PositionSize != 0.0) _wasIn = true;
            else if (_wasIn) { _boxes.Clear(); _wasIn = false; }
        }

        private static void CloseAll(EngineOutput o, MarketContext ctx, int idx, string reason)
        {
            o.CloseSession = true;
            List<string> ids = new List<string>(ctx.OpenOrderIds);
            ids.Sort(StringComparer.Ordinal);
            foreach (string orderId in ids)
                o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx, reason));
        }

        /// <summary>Python `f"{k:.0f}"` - zaokruhlenie na parne presnej binarnej hodnoty.</summary>
        private static string Whole(double k)
        {
            return ((long)Math.Round(k, 0, MidpointRounding.ToEven)).ToString(CultureInfo.InvariantCulture);
        }

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            TksConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            Track(o, bar, ctx);
            Pivots();
            double? k = Kompas.Push(bar);
            Value = k;
            double pos = ctx.PositionSize;
            if (Kompas.Rth && (!_hasSessDay || Kompas.Day != _sessDay))
            {
                _hasSessDay = true;
                _sessDay = Kompas.Day;
                _sessTrades = 0;
            }
            if (cfg.closeAtSessionEnd && pos != 0.0 && Kompas.Rth && Kompas.KClose >= 390)
            {
                CloseAll(o, ctx, idx, "koniec seansy 16:00");
                return o;
            }
            if (!k.HasValue)
            {
                _cntDn = _cntUp = 0;
                _armedDn = _armedUp = true;
                return o;
            }
            double kv = k.Value;
            _cntDn = kv < cfg.loLevel ? _cntDn + 1 : 0;
            _cntUp = kv > cfg.hiLevel ? _cntUp + 1 : 0;
            if (kv >= cfg.loLevel) _armedDn = true;
            if (kv <= cfg.hiLevel) _armedUp = true;
            int side = 0;
            if (_cntDn >= cfg.nConf && _armedDn)
            {
                _armedDn = false;
                side = -1;
            }
            else if (_cntUp >= cfg.nConf && _armedUp)
            {
                _armedUp = false;
                side = 1;
            }
            if (side == 0 || pos != 0.0) return o;
            if (cfg.maxTradesPerSession != 0 && _sessTrades >= cfg.maxTradesPerSession) return o;
            if ((side < 0 && !cfg.AllowShort) || (side > 0 && !cfg.AllowLong)) return o;
            int kc = Kompas.KClose;                        // minuta zavretia od 9:30
            if (!(cfg.entryStartMin <= kc && kc <= cfg.entryEndMin)) return o;
            if (cfg.pauseFromMin < cfg.pauseToMin && cfg.pauseFromMin <= kc && kc < cfg.pauseToMin) return o;
            double c = bar.Close;
            double atr = History.Atr;
            double? sl = null;
            if (cfg.slMode == "swing")
            {
                List<double> swings = side < 0 ? _swingHi : _swingLo;
                for (int i = swings.Count - 1; i >= 0; i--)
                {
                    double x = swings[i];
                    if (side < 0 ? x > c : x < c) { sl = x; break; }
                }
            }
            else
            {
                double d0 = cfg.slMode == "atr" ? cfg.slAtrMult * atr : cfg.slPoints;
                if (d0 > 0) sl = c - side * d0;
            }
            if (!sl.HasValue) return o;
            double dist = Math.Abs(c - sl.Value);
            if ((cfg.maxSlPoints > 0 && dist > cfg.maxSlPoints) || (cfg.maxSlAtr > 0 && atr > 0 && dist > cfg.maxSlAtr * atr))
                return o;
            double take = c + side * cfg.rrRatio * dist;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, dist);
            TradePlan plan = Plan(side > 0, c, sl.Value, take, q > 0 ? q : 1.0);
            if (plan == null) return o;
            string ks = Whole(kv);
            Enter(o, bar, idx, plan, "Kompas " + ks + " — " + cfg.nConf.ToString(CultureInfo.InvariantCulture) + " sviečky za hranicou",
                  (side > 0 ? "LONG" : "SHORT") + " Kompas " + ks);
            _sessTrades += 1;
            return o;
        }

        // ------------------------------------------------------------------ //

        private TradePlan Plan(bool isLong, double entry, double stop, double take, double qty)
        {
            double sl = Math.Abs(entry - stop);
            if (sl < _inst.TickSize * 2) return null;
            return new TradePlan(isLong ? Direction.Long : Direction.Short, _inst.RoundPrice(entry), _inst.RoundPrice(stop),
                                 _inst.RoundPrice(take), qty, sl, null);
        }

        private void Enter(EngineOutput o, Bar bar, int idx, TradePlan plan, string reason, string text)
        {
            bool isLong = plan.Direction == Direction.Long;
            OrderIntent intent = new OrderIntent(OrderAction.Entry, "tks:" + idx.ToString(CultureInfo.InvariantCulture), idx, reason);
            intent.Direction = plan.Direction;
            intent.Plan = plan;
            intent.OrderType = OrderType.Market;
            o.Orders.Add(intent);
            long t = bar.Time + _stepMs;          // market sa plni na otvoreni dalsej sviecky
            long end = t + _stepMs;
            _boxes.Clear();
            AddBox(o, DrawKinds.TpBox, "tp", "TP ", plan.TakeProfit, plan.Entry, LongColor, t, end);
            AddBox(o, DrawKinds.SlBox, "sl", "SL ", plan.StopLoss, plan.Entry, ShortColor, t, end);
            DrawLabel label = new DrawLabel(TksKinds.Entry, t, plan.Entry, text, "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "tks.e." + t.ToString(CultureInfo.InvariantCulture);
            o.Drawings.Add(label);
        }

        private void AddBox(EngineOutput o, string kind, string tag, string prefix, double level, double entry, string color,
                            long t, long end)
        {
            string oid = "tks." + tag + "." + t.ToString(CultureInfo.InvariantCulture);
            DrawBox box = new DrawBox(kind, t, Math.Max(entry, level), end, Math.Min(entry, level), color);
            box.FillColor = Palette.WithAlpha(color, 80);
            box.ObjId = oid;
            box.Text = prefix + PyMath.FormatG(level);
            o.Drawings.Add(box);
            _boxes.Add(oid);
        }
    }
}
