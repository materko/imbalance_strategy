// Obaly vstupov - zrkadlo `tradebot/core/entry_filter.py`, `entry_confirm.py`, `entry_order.py`, `entry_sizing.py`
// a `entry_draw.py`.
//
// Strategia (engine) rozhodne, KEDY vstupit; obal vstup filtruje (trend EMA, volatilita), podrzi do
// potvrdzovacej sviecky alebo zmeni na limitku. V Pythone ich nasadzuju adaptery (Freqtrade, emulator
// MultiCharts); C# engine ich dostane priamo v `EngineRegistry.Create`, takze ich ma kazdy hostitel -
// most do Pythonu aj NinjaTrader a MT5 nazivo. Obal nepozna strategiu menom: zapina ho config
// (pole `trendFilter`/`volFilter`, `entryConfirm`, `entryOrderType`, `fixedQty`/`skipOverRisk`), presne ako
// `wrap_entry_*` v Pythone.
//
// Poradie je ako v adapteroch: velkost( typ orderu( potvrdenie( filter( engine )))).
using System;
using System.Collections.Generic;
using System.Globalization;

namespace TradeBot.Core
{
    /// <summary>Kresba obchodu pri obaloch vstupov - zrkadlo `tradebot/core/entry_draw.py`.</summary>
    public static class EntryDraw
    {
        private static bool IsTrade(DrawCommand o, long barTime)
        {
            DrawBox b = o as DrawBox;
            if (b != null)
                return (b.Kind == DrawKinds.TpBox || b.Kind == DrawKinds.SlBox) && b.X1Ms == barTime && !string.IsNullOrEmpty(b.ObjId);
            DrawLabel l = o as DrawLabel;
            if (l != null)
                return l.Kind != null && l.Kind.EndsWith("_entry", StringComparison.Ordinal) && l.XMs == barTime
                       && !string.IsNullOrEmpty(l.ObjId);
            return false;
        }

        /// <summary>Boxy a stitok vstupu, ktore strategia nakreslila na tomto bare.</summary>
        public static List<DrawCommand> TradeDrawings(List<DrawCommand> drawings, long barTime)
        {
            List<DrawCommand> list = new List<DrawCommand>();
            foreach (DrawCommand o in drawings) if (IsTrade(o, barTime)) list.Add(o);
            return list;
        }

        /// <summary>Python `[d for d in drawings if not any(d is x for x in objs)]` - podla identity objektu.</summary>
        public static List<DrawCommand> Without(List<DrawCommand> drawings, List<DrawCommand> objs)
        {
            List<DrawCommand> list = new List<DrawCommand>();
            foreach (DrawCommand d in drawings)
            {
                bool hit = false;
                foreach (DrawCommand x in objs) if (ReferenceEquals(d, x)) { hit = true; break; }
                if (!hit) list.Add(d);
            }
            return list;
        }

        public static bool AnyOf(List<DrawCommand> drawings, List<DrawCommand> objs)
        {
            foreach (DrawCommand d in drawings)
                foreach (DrawCommand x in objs)
                    if (ReferenceEquals(d, x)) return true;
            return false;
        }

        /// <summary>Boxy na ceny planu (vstup -> ciel, vstup -> stop); meni objekty na mieste.</summary>
        public static void Relevel(List<DrawCommand> objs, TradePlan plan)
        {
            foreach (DrawCommand o in objs)
            {
                DrawBox b = o as DrawBox;
                if (b == null) continue;
                bool tp = b.Kind == DrawKinds.TpBox;
                double level = tp ? plan.TakeProfit : plan.StopLoss;
                b.Y1 = Math.Max(plan.Entry, level);
                b.Y2 = Math.Min(plan.Entry, level);
                b.Text = (tp ? "TP " : "SL ") + PyMath.FormatG(level);
            }
        }

        private static DrawCommand CopyOf(DrawCommand o)
        {
            DrawBox b = o as DrawBox;
            if (b != null)
            {
                DrawBox n = new DrawBox(b.Kind, b.X1Ms, b.Y1, b.X2Ms, b.Y2, b.BorderColor);
                n.ObjId = b.ObjId; n.FillColor = b.FillColor; n.BorderStyle = b.BorderStyle; n.BorderWidth = b.BorderWidth;
                n.ExtendRight = b.ExtendRight; n.ZoneUid = b.ZoneUid; n.Text = b.Text;
                return n;
            }
            DrawLabel l = (DrawLabel)o;
            DrawLabel c = new DrawLabel(l.Kind, l.XMs, l.Y, l.Text, l.Color);
            c.ObjId = l.ObjId; c.Style = l.Style; c.Above = l.Above; c.BgColor = l.BgColor; c.ZoneUid = l.ZoneUid;
            return c;
        }

        /// <summary>Nove kopie kresby zacinajuce na `t` (bar skutocneho vstupu); stare sa zmazu (rovnake obj_id).</summary>
        public static List<DrawCommand> Released(List<DrawCommand> objs, long t, TradePlan plan)
        {
            List<DrawCommand> list = new List<DrawCommand>();
            foreach (DrawCommand o in objs)
            {
                DrawCommand n = CopyOf(o);
                DrawBox nb = n as DrawBox;
                if (nb != null)
                {
                    DrawBox ob = (DrawBox)o;
                    long width = Math.Max(0, ob.X2Ms - ob.X1Ms);
                    nb.X1Ms = t;
                    nb.X2Ms = Math.Max(ob.X2Ms, t + width);
                }
                else
                {
                    ((DrawLabel)n).XMs = t;
                }
                list.Add(new DrawDelete(o.ObjId));
                list.Add(n);
            }
            if (plan != null)
            {
                List<DrawCommand> boxes = new List<DrawCommand>();
                foreach (DrawCommand x in list) if (x is DrawBox) boxes.Add(x);
                Relevel(boxes, plan);
            }
            return list;
        }

        /// <summary>Posun zaciatku kresby na bar vyplnenia (ceny ostavaju).</summary>
        public static List<DrawCommand> Moved(List<DrawCommand> objs, long t)
        {
            List<DrawCommand> list = new List<DrawCommand>();
            foreach (DrawCommand o in objs) list.Add(new DrawUpdate(o.ObjId, o is DrawBox ? "x1_ms" : "x_ms", t));
            return list;
        }

        public static List<DrawCommand> Deleted(List<DrawCommand> objs)
        {
            List<DrawCommand> list = new List<DrawCommand>();
            foreach (DrawCommand o in objs) list.Add(new DrawDelete(o.ObjId));
            return list;
        }

        /// <summary>Kontext pre vnutorny engine s doplnenymi cakajucimi a zahodenymi vstupmi (kopia, ako Python).</summary>
        public static MarketContext WithIds(MarketContext ctx, ICollection<string> pending, ICollection<string> dropped)
        {
            if (ctx == null || (pending.Count == 0 && dropped.Count == 0)) return ctx;
            MarketContext c = ctx.Copy();
            foreach (string id in pending) c.PendingEntryIds.Add(id);
            foreach (string id in dropped) c.DroppedEntryIds.Add(id);
            return c;
        }

        public static OrderIntent WithPlan(OrderIntent o, TradePlan plan, OrderType orderType)
        {
            OrderIntent n = new OrderIntent(o.Action, o.OrderId, o.SourceId, o.Reason);
            n.Direction = o.Direction;
            n.Plan = plan;
            n.OrderType = orderType;
            return n;
        }

        public static TradePlan Replan(TradePlan p, double entry, double takeProfit, double qty, double slDistance)
        {
            return new TradePlan(p.Direction, entry, p.StopLoss, takeProfit, qty, slDistance, p.Trailing);
        }
    }

    /// <summary>Spolocny zaklad obalu: vsetko okrem `OnBar` ide na vnutorny engine.</summary>
    public abstract class EngineLayer : IEngine
    {
        public readonly IEngine Inner;

        protected EngineLayer(IEngine inner) { Inner = inner; }

        public InstrumentSpec Inst { get { return Inner.Inst; } }
        public int ChartTfMinutes { get { return Inner.ChartTfMinutes; } }
        public int RequiredHistory { get { return Inner.RequiredHistory; } }
        public Warmup Warmup { get { return Inner.Warmup; } }
        public List<DrawCommand> FinalDrawings(Bar bar) { return Inner.FinalDrawings(bar); }
        public IHtfFeeder CreateHtfFeeder() { return Inner.CreateHtfFeeder(); }
        public Dictionary<string, double> Stats() { return Inner.Stats(); }
        public abstract EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx);

        /// <summary>Najvnutornejsi engine strategie (pod vsetkymi obalmi).</summary>
        public static IEngine Unwrap(IEngine e)
        {
            EngineLayer l = e as EngineLayer;
            while (l != null) { e = l.Inner; l = e as EngineLayer; }
            return e;
        }

        protected double Round(double price) { return Inner.Inst != null ? Inner.Inst.RoundPrice(price) : price; }

        internal static string Text(Dictionary<string, object> cfg, string key, string dflt)
        {
            object v;
            return cfg.TryGetValue(key, out v) && v != null ? Convert.ToString(v, CultureInfo.InvariantCulture) : dflt;
        }

        internal static double Num(Dictionary<string, object> cfg, string key, double dflt)
        {
            object v;
            return cfg.TryGetValue(key, out v) && v != null ? Json.ToDouble(v) : dflt;
        }

        internal static bool Flag(Dictionary<string, object> cfg, string key, bool dflt)
        {
            object v;
            return cfg.TryGetValue(key, out v) && v is bool ? (bool)v : dflt;
        }
    }

    /// <summary>Filter trendu a volatility - zrkadlo `EntryFilterEngine` (`tradebot/core/entry_filter.py`).</summary>
    public sealed class EntryFilterEngine : EngineLayer
    {
        private const int AtrLen = 14;
        private readonly string _mode;      // off / with / against
        private readonly string _volMode;   // off / low / high
        private readonly int _volN;
        private double _atr;
        private readonly List<double> _tr = new List<double>();
        private double? _prevClose;
        private readonly Queue<double> _atrs = new Queue<double>();
        private double _atrSum;
        private readonly int _n;
        public readonly int Tf;
        private readonly long _tfMs;
        private readonly long _chartMs;
        public double? Ema;
        private int _count;
        private double _sum;
        private long? _bucket;
        private double? _lastClose;
        private HashSet<string> _dropped = new HashSet<string>();

        public EntryFilterEngine(IEngine inner, Dictionary<string, object> cfg, int chartTfMinutes) : base(inner)
        {
            _mode = Text(cfg, "trendFilter", "off");
            _volMode = Text(cfg, "volFilter", "off");
            _volN = (int)Num(cfg, "volLookback", 100);
            _n = (int)Num(cfg, "trendEmaLen", 200);
            int chart = Math.Max(1, chartTfMinutes);
            int tf = (int)Num(cfg, "trendTF", 0);
            if (tf == 0) tf = chart;
            if (tf < chart || tf % chart != 0)
            {
                int m = Math.Max(tf, chart);
                tf = (m + chart - 1) / chart * chart;
            }
            Tf = tf;
            _tfMs = tf * 60000L;
            _chartMs = chart * 60000L;
            Warmup w = inner.Warmup;
            if (w != null)
            {
                if (_mode != "off")
                    w.AddSeeded("filter trendu EMA " + _n + " na " + tf + "m", WarmupMath.EmaBars(_n), tf, Seed);
                if (_volMode != "off")
                    w.AddSeeded("filter volatility ATR " + AtrLen + " / " + _volN + " barov", _volN + 4 * AtrLen, chart, SeedVol);
            }
        }

        /// <summary>Uzavrety bar TF filtra. Start ako Pine `ta.ema`: priemer prvych `n` zavreti.</summary>
        private void CloseBar(double close)
        {
            _count += 1;
            if (!Ema.HasValue)
            {
                _sum += close;
                if (_count >= _n) Ema = _sum / _n;
            }
            else
            {
                Ema = Ema.Value + (close - Ema.Value) * 2.0 / (_n + 1);
            }
        }

        private void Seed(IList<Bar> closed, Bar partial)
        {
            foreach (Bar b in closed) CloseBar(b.Close);
            if (partial != null)
            {
                _bucket = partial.Time / _tfMs;
                _lastClose = partial.Close;
            }
        }

        private void Vol(Bar bar)
        {
            double tr = !_prevClose.HasValue
                ? bar.High - bar.Low
                : Math.Max(bar.High - bar.Low, Math.Max(Math.Abs(bar.High - _prevClose.Value), Math.Abs(bar.Low - _prevClose.Value)));
            _prevClose = bar.Close;
            if (_atr > 0)
            {
                _atr += (tr - _atr) / AtrLen;
            }
            else
            {
                _tr.Add(tr);
                if (_tr.Count < AtrLen) return;
                _atr = PyMath.Sum(_tr) / _tr.Count;
            }
            if (_atrs.Count == _volN) _atrSum -= _atrs.Dequeue();
            _atrs.Enqueue(_atr);
            _atrSum += _atr;
        }

        private void SeedVol(IList<Bar> closed, Bar partial)
        {
            foreach (Bar b in closed) Vol(b);
        }

        public bool VolAllows()
        {
            if (_volMode == "off") return true;
            if (_atrs.Count < _volN) return false;
            double mean = _atrSum / _atrs.Count;
            return _volMode == "low" ? _atr < mean : _atr > mean;
        }

        private void Push(Bar bar)
        {
            long bucket = bar.Time / _tfMs;
            if (_bucket.HasValue && bucket != _bucket.Value && _lastClose.HasValue)
            {
                CloseBar(_lastClose.Value);   // perioda sa skoncila bez toho, aby sme videli jej posledny bar
                _lastClose = null;
            }
            _bucket = bucket;
            _lastClose = bar.Close;
            if ((bar.Time + _chartMs) / _tfMs != bucket)   // posledny bar grafu v periode - bar TF je uzavrety
            {
                CloseBar(bar.Close);
                _lastClose = null;
            }
        }

        public bool Allows(Direction direction, double close)
        {
            if (!VolAllows()) return false;
            if (_mode == "off") return true;
            if (!Ema.HasValue) return false;
            bool above = close > Ema.Value;
            bool isLong = direction == Direction.Long;
            return _mode == "with" ? above == isLong : above != isLong;
        }

        public override EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (_mode != "off") Push(bar);
            if (_volMode != "off") Vol(bar);
            EngineOutput o = Inner.OnBar(bar, htf, EntryDraw.WithIds(ctx, new string[0], _dropped));
            _dropped = new HashSet<string>();
            List<OrderIntent> kept = new List<OrderIntent>();
            foreach (OrderIntent i in o.Orders)
            {
                if (i.Action == OrderAction.Entry && i.Plan != null && !Allows(i.Plan.Direction, bar.Close))
                {
                    List<DrawCommand> objs = EntryDraw.TradeDrawings(o.Drawings, bar.Time);   // zahodeny vstup - jeho kresba tiez
                    o.Drawings = EntryDraw.Without(o.Drawings, objs);
                    _dropped.Add(i.OrderId);
                    continue;
                }
                kept.Add(i);
            }
            o.Orders = kept;
            return o;
        }
    }

    /// <summary>Potvrdenie vstupu sviecou (IBS imbalance / pin bar) - zrkadlo `EntryConfirmEngine`.</summary>
    public sealed class EntryConfirmEngine : EngineLayer
    {
        private const int AtrLen = 14;
        private readonly string _mode;   // imbalance / pinbar / any
        private readonly int _confirmBars;
        private readonly double _imbMinAtr;
        private readonly double _pbWickPct;
        private readonly double _pbBodyPct;
        private readonly List<Bar> _bars = new List<Bar>();   // najviac 3, najnovsi posledny
        private double _atr;
        private readonly List<double> _tr = new List<double>();
        private OrderIntent _waitIntent;      // vstup strategie
        private int _waitAt;                  // index baru signalu
        private List<DrawCommand> _waitObjs;  // jeho kresba
        private HashSet<string> _dropped = new HashSet<string>();
        private int _idx = -1;

        public EntryConfirmEngine(IEngine inner, Dictionary<string, object> cfg) : base(inner)
        {
            _mode = Text(cfg, "entryConfirm", "none");
            _confirmBars = (int)Num(cfg, "confirmBars", 3);
            _imbMinAtr = Num(cfg, "confirmImbMinAtr", 0.05);
            _pbWickPct = Num(cfg, "confirmPbWickPct", 60);
            _pbBodyPct = Num(cfg, "confirmPbBodyPct", 30);
        }

        /// <summary>IBS imbalance: `b0` je najnovsia sviecka, `b2` prva z trojice.</summary>
        public static bool IsImbalance(Bar b0, Bar b1, Bar b2, bool isLong, double minGap)
        {
            if (isLong) return b0.Low > b2.High && b1.Close > b2.High && (b0.Low - b2.High) >= minGap;
            return b0.High < b2.Low && b1.Close < b2.Low && (b2.Low - b0.High) >= minGap;
        }

        public static bool IsPinbar(Bar bar, bool isLong, double wickPct, double bodyPct)
        {
            double rng = bar.High - bar.Low;
            if (rng <= 0 || Math.Abs(bar.Close - bar.Open) > bodyPct / 100.0 * rng) return false;
            double wick = isLong ? Math.Min(bar.Open, bar.Close) - bar.Low : bar.High - Math.Max(bar.Open, bar.Close);
            return wick >= wickPct / 100.0 * rng;
        }

        private void Push(Bar bar)
        {
            Bar prev = _bars.Count > 0 ? _bars[_bars.Count - 1] : null;
            double tr = prev == null
                ? bar.High - bar.Low
                : Math.Max(bar.High - bar.Low, Math.Max(Math.Abs(bar.High - prev.Close), Math.Abs(bar.Low - prev.Close)));
            if (_atr > 0)
            {
                _atr += (tr - _atr) / AtrLen;
            }
            else
            {
                _tr.Add(tr);
                if (_tr.Count >= AtrLen) _atr = PyMath.Sum(_tr) / _tr.Count;
            }
            _bars.Add(bar);
            if (_bars.Count > 3) _bars.RemoveAt(0);
        }

        private bool Confirmed(Bar bar, bool isLong)
        {
            bool imb = _bars.Count == 3 && IsImbalance(_bars[2], _bars[1], _bars[0], isLong, _imbMinAtr * _atr);
            bool pin = IsPinbar(bar, isLong, _pbWickPct, _pbBodyPct);
            if (_mode == "imbalance") return imb;
            if (_mode == "pinbar") return pin;
            return imb || pin;
        }

        /// <summary>Vstup na zavreti potvrdzovacej sviecky: stop ostava, RR a riziko tiez.</summary>
        private OrderIntent Entry(OrderIntent intent, Bar bar)
        {
            TradePlan plan = intent.Plan;
            bool isLong = plan.Direction == Direction.Long;
            double price = Round(bar.Close);
            double sl = isLong ? price - plan.StopLoss : plan.StopLoss - price;
            double oldSl = isLong ? plan.Entry - plan.StopLoss : plan.StopLoss - plan.Entry;
            if (sl <= 0 || oldSl <= 0 || sl < 0.25 * oldSl) return null;
            double rr = (isLong ? plan.TakeProfit - plan.Entry : plan.Entry - plan.TakeProfit) / oldSl;
            double take = Round(isLong ? price + rr * sl : price - rr * sl);
            double qty = plan.Qty != 0.0 && !double.IsNaN(plan.Qty) ? plan.Qty * oldSl / sl : plan.Qty;
            return EntryDraw.WithPlan(intent, EntryDraw.Replan(plan, price, take, qty, sl), intent.OrderType);
        }

        public override EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            _idx += 1;
            Push(bar);
            List<string> pend = new List<string>();
            if (_waitIntent != null) pend.Add(_waitIntent.OrderId);
            EngineOutput o = Inner.OnBar(bar, htf, EntryDraw.WithIds(ctx, pend, _dropped));
            _dropped = new HashSet<string>();
            double pos = ctx != null ? ctx.PositionSize : 0.0;
            if (pos != 0.0 && _waitIntent != null) Drop(o);
            List<OrderIntent> orders = new List<OrderIntent>();
            bool fresh = false;
            foreach (OrderIntent i in o.Orders)
            {
                if (i.Action == OrderAction.Entry && i.OrderType == OrderType.Market && i.Plan != null)
                {
                    List<DrawCommand> objs = EntryDraw.TradeDrawings(o.Drawings, bar.Time);
                    if (pos == 0.0)
                    {
                        if (_waitIntent != null) Drop(o);   // novy signal nahradza cakajuci
                        _waitIntent = i; _waitAt = _idx; _waitObjs = objs;
                        fresh = true;
                    }
                    else
                    {
                        o.Drawings = EntryDraw.Without(o.Drawings, objs);
                        _dropped.Add(i.OrderId);
                    }
                    continue;
                }
                if (i.Action == OrderAction.Cancel && _waitIntent != null && i.OrderId == _waitIntent.OrderId)
                    _waitIntent = null;
                orders.Add(i);
            }
            if (_waitIntent != null)
            {
                TradePlan plan = _waitIntent.Plan;
                bool isLong = plan.Direction == Direction.Long;
                if (!fresh && (isLong ? bar.Low <= plan.StopLoss : bar.High >= plan.StopLoss))
                {
                    Drop(o);   // cena presla stopom skor, nez prislo potvrdenie
                }
                else if (Confirmed(bar, isLong))
                {
                    OrderIntent entry = Entry(_waitIntent, bar);
                    if (entry != null)
                    {
                        orders.Add(entry);
                        o.Drawings = EntryDraw.Without(o.Drawings, _waitObjs);
                        o.Drawings.AddRange(EntryDraw.Released(_waitObjs, bar.Time, entry.Plan));   // kresba na potvrdzovaciu sviecku
                        _waitIntent = null;
                    }
                    else
                    {
                        Drop(o);
                    }
                }
                else if (_idx - _waitAt + 1 >= _confirmBars)
                {
                    Drop(o);
                }
            }
            o.Orders = orders;
            return o;
        }

        /// <summary>Cakajuci signal prepadol: kresba prec a strategia sa to dozvie na dalsom bare.</summary>
        private void Drop(EngineOutput o)
        {
            if (EntryDraw.AnyOf(o.Drawings, _waitObjs)) o.Drawings = EntryDraw.Without(o.Drawings, _waitObjs);
            else o.Drawings.AddRange(EntryDraw.Deleted(_waitObjs));
            _dropped.Add(_waitIntent.OrderId);
            _waitIntent = null;
        }
    }

    /// <summary>Typ vstupneho orderu (market -> limitka) - zrkadlo `EntryOrderEngine` (`entry_order.py`).</summary>
    public sealed class EntryOrderEngine : EngineLayer
    {
        private readonly double _offsetPct;
        private readonly int _validBars;
        private readonly bool _keepRR;
        private string _pendingId;   // cakajuca limitka: id, index, cena, kresba obchodu
        private int _pendingAt;
        private double _pendingPrice;
        private List<DrawCommand> _pendingObjs;
        private HashSet<string> _dropped = new HashSet<string>();
        private int _idx = -1;

        public EntryOrderEngine(IEngine inner, Dictionary<string, object> cfg) : base(inner)
        {
            _offsetPct = Num(cfg, "limitOffsetPct", 50);
            _validBars = (int)Num(cfg, "limitValidBars", 3);
            _keepRR = Flag(cfg, "limitKeepRR", true);
        }

        private OrderIntent Limit(OrderIntent intent, Bar bar)
        {
            TradePlan plan = intent.Plan;
            bool isLong = plan.Direction == Direction.Long;
            double k = _offsetPct / 100.0;
            double rng = bar.High - bar.Low;
            double price = Round(isLong ? plan.Entry - k * rng : plan.Entry + k * rng);
            double sl = isLong ? price - plan.StopLoss : plan.StopLoss - price;
            double oldSl = isLong ? plan.Entry - plan.StopLoss : plan.StopLoss - plan.Entry;
            if (sl <= 0 || oldSl <= 0 || sl < 0.25 * oldSl) return null;   // limitka za stopom alebo tesne pri nom
            double take = plan.TakeProfit;
            if (_keepRR)
            {
                double rr = (isLong ? plan.TakeProfit - plan.Entry : plan.Entry - plan.TakeProfit) / oldSl;
                take = Round(isLong ? price + rr * sl : price - rr * sl);
            }
            double qty = plan.Qty != 0.0 && !double.IsNaN(plan.Qty) ? plan.Qty * oldSl / sl : plan.Qty;
            return EntryDraw.WithPlan(intent, EntryDraw.Replan(plan, price, take, qty, sl), OrderType.Limit);
        }

        public override EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            _idx += 1;
            List<DrawCommand> gone = null;
            if (_pendingId != null && ctx != null && ctx.DroppedEntryIds.Contains(_pendingId))
            {
                // limitku zrusil obal nad nami (EOD) - obchod nebude, kresba prec
                gone = EntryDraw.Deleted(_pendingObjs);
                _pendingId = null;
            }
            List<string> pend = new List<string>();
            if (_pendingId != null) pend.Add(_pendingId);
            EngineOutput o = Inner.OnBar(bar, htf, EntryDraw.WithIds(ctx, pend, _dropped));
            _dropped = new HashSet<string>();
            if (gone != null) o.Drawings.AddRange(gone);
            double pos = ctx != null ? ctx.PositionSize : 0.0;
            List<OrderIntent> orders = new List<OrderIntent>();
            if (_pendingId != null)
            {
                if (pos != 0.0 || (bar.Low <= _pendingPrice && _pendingPrice <= bar.High))
                {
                    o.Drawings.AddRange(EntryDraw.Moved(_pendingObjs, bar.Time));   // vyplnila sa - kresba zacina na bare vyplnenia
                    _pendingId = null;
                }
                else if (_idx - _pendingAt >= _validBars)
                {
                    orders.Add(new OrderIntent(OrderAction.Cancel, _pendingId, _pendingAt, "limitka nevyplnená"));
                    o.Drawings.AddRange(EntryDraw.Deleted(_pendingObjs));   // obchod nebol - boxy a stitok prec
                    _dropped.Add(_pendingId);
                    _pendingId = null;
                }
            }
            foreach (OrderIntent i in o.Orders)
            {
                if (i.Action == OrderAction.Entry && i.OrderType == OrderType.Market && i.Plan != null)
                {
                    List<DrawCommand> objs = EntryDraw.TradeDrawings(o.Drawings, bar.Time);
                    OrderIntent lim = (_pendingId != null || pos != 0.0) ? null : Limit(i, bar);
                    if (lim == null)
                    {
                        // kym limitka caka, dalsi vstup sa neposiela; alebo by bola za stopom
                        o.Drawings = EntryDraw.Without(o.Drawings, objs);
                        _dropped.Add(i.OrderId);
                        continue;
                    }
                    EntryDraw.Relevel(objs, lim.Plan);
                    _pendingId = lim.OrderId; _pendingAt = _idx; _pendingPrice = lim.Plan.Entry; _pendingObjs = objs;
                    orders.Add(lim);
                    continue;
                }
                if (i.Action == OrderAction.Cancel && _pendingId != null && i.OrderId == _pendingId) _pendingId = null;
                orders.Add(i);
            }
            o.Orders = orders;
            return o;
        }
    }

    /// <summary>Pevny pocet kontraktov a strop straty - zrkadlo `EntrySizingEngine` (`tradebot/core/entry_sizing.py`).
    /// `fixedQty` = vzdy `qty`; `skipOverRisk` = pocet nadol na cely krok a obchod, ktoreho strata na stope
    /// by bola vacsia nez riziko na obchod (`riskDollar`, pri Pine mene `maxLossDollar`), sa vynecha.</summary>
    public sealed class EntrySizingEngine : EngineLayer
    {
        private readonly bool _fixedQty;
        private readonly double _qty;
        private readonly bool _skipOverRisk;
        private readonly double _risk;
        private HashSet<string> _dropped = new HashSet<string>();

        public EntrySizingEngine(IEngine inner, Dictionary<string, object> cfg) : base(inner)
        {
            _fixedQty = Flag(cfg, "fixedQty", false);
            _qty = Num(cfg, "qty", 1.0);
            _skipOverRisk = CapsRisk(cfg);
            _risk = RiskLimit(cfg);
        }

        /// <summary>Strop straty plati: velkost z rizika vzdy, pevny pocet (`fixedQty`, `legacyPineSizing`) len so `skipOverRisk`
        /// (`caps_risk` v `entry_sizing.py`, audit N-LIVE-20).</summary>
        public static bool CapsRisk(Dictionary<string, object> cfg)
        {
            return Flag(cfg, "skipOverRisk", false) || !(Flag(cfg, "fixedQty", false) || Flag(cfg, "legacyPineSizing", false));
        }

        /// <summary>Riziko na obchod v $ - prve z poli `riskDollar`, `maxLossDollar`, ktore config ma.</summary>
        public static double RiskLimit(Dictionary<string, object> cfg)
        {
            if (cfg.ContainsKey("riskDollar")) return Num(cfg, "riskDollar", 0.0);
            return Num(cfg, "maxLossDollar", 0.0);
        }

        /// <summary>Plan s konecnou velkostou, alebo null, ked by strata na stope prekrocila riziko.</summary>
        private TradePlan Size(TradePlan plan)
        {
            double qty = _fixedQty ? _qty : plan.Qty;
            InstrumentSpec inst = Inner.Inst;
            if (_skipOverRisk && inst != null && _risk > 0 && !double.IsNaN(qty))
            {
                qty = inst.RoundQty(qty);   // broker berie len cele kroky (NinjaTrader by 2,7 zaokruhlil na 3)
                if (qty * plan.SlDistance * inst.PointValue > _risk * (1.0 + 1e-9)) return null;
            }
            return qty == plan.Qty ? plan : EntryDraw.Replan(plan, plan.Entry, plan.TakeProfit, qty, plan.SlDistance);
        }

        public override EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            EngineOutput o = Inner.OnBar(bar, htf, EntryDraw.WithIds(ctx, new List<string>(), _dropped));
            _dropped = new HashSet<string>();
            List<OrderIntent> orders = new List<OrderIntent>();
            foreach (OrderIntent i in o.Orders)
            {
                if (i.Action == OrderAction.Entry && i.Plan != null)
                {
                    TradePlan plan = Size(i.Plan);
                    if (plan == null)
                    {
                        // obchod nebude - kresba jeho boxov prec, vnutorne obaly sa to dozvedia na dalsom bare
                        o.Drawings = EntryDraw.Without(o.Drawings, EntryDraw.TradeDrawings(o.Drawings, bar.Time));
                        _dropped.Add(i.OrderId);
                        continue;
                    }
                    orders.Add(plan == i.Plan ? i : EntryDraw.WithPlan(i, plan, i.OrderType));
                    continue;
                }
                orders.Add(i);
            }
            o.Orders = orders;
            return o;
        }
    }

    /// <summary>Nasadenie obalov podla configu - zrkadlo `wrap_entry_filter`, `wrap_entry_confirm`, `wrap_entry_order`,
    /// `wrap_entry_sizing` v tom istom poradi, v akom ich nasadzuju Python adaptery.</summary>
    public static class EntryLayers
    {
        public static IEngine Wrap(IEngine engine, Dictionary<string, object> cfg, int chartTfMinutes)
        {
            if (cfg == null) return engine;
            if (cfg.ContainsKey("trendFilter") && cfg.ContainsKey("trendTF")
                && (EngineLayer.Text(cfg, "trendFilter", "off") != "off" || EngineLayer.Text(cfg, "volFilter", "off") != "off"))
                engine = new EntryFilterEngine(engine, cfg, chartTfMinutes);
            if (cfg.ContainsKey("entryConfirm") && EngineLayer.Text(cfg, "entryConfirm", "none") != "none")
                engine = new EntryConfirmEngine(engine, cfg);
            if (cfg.ContainsKey("entryOrderType") && EngineLayer.Text(cfg, "entryOrderType", "market") != "market")
                engine = new EntryOrderEngine(engine, cfg);
            if (EngineLayer.Flag(cfg, "fixedQty", false) || (EntrySizingEngine.CapsRisk(cfg) && EntrySizingEngine.RiskLimit(cfg) > 0))
                engine = new EntrySizingEngine(engine, cfg);
            return engine;
        }
    }
}
