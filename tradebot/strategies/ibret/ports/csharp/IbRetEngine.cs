// `IbRetEngine` - IB RETRACE 1.0 s jadrom v C#. Zrkadlo `tradebot/strategies/ibret/engine.py`; s Python enginom sa
// porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy).
//
// Cas = otvorenie baru v New Yorku. Na kazdom uzavretom bare:
//   1. novy den (datum NY) - zrusit cakajucu limitku, vynulovat IB a stav dna,
//   2. IB - bary ibStart <= t < koniec IB rozsiria high / low a nic dalsie,
//   3. IB hotovy - den v tyzdni a sirka IB rozhodnu, ci sa v ten den obchoduje,
//   4. limitka sa vyplnila? - pozicia alebo id v otvorenych obchodoch,
//   5. koniec - closeAtEnd a zavretie baru o exitTime a neskor: poziciu zavriet,
//   6. cakajuca limitka - zrusit pri lastEntry, pri prieraze druhej strany IB a ked cena dosla do ciela bez navratu,
//   7. prieraz - prvy knot (breakOn wick, IB Lab) alebo prve zavretie za IB rozhodne o dni: v okne breakFrom-breakTo a povolenom smere vstup.
// Uroven x (zlomok sirky IB) lezi pri longu na IB high - x * IB, pri shorte na IB low + x * IB.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.IbRetNet
{
    [TradeBotEngine("ibretnet", "IB RETRACE 1.0 (C#)")]
    public class IbRetEngine : IEngine, IConfigured
    {
        private const string Ny = "America/New_York";
        private const string LongColor = "#22c55e";
        private const string ShortColor = "#ef4444";
        private const string ZoneColor = "#2196f3";
        private const int Wait = 0, Done = 1;   // stav dna: caka na prieraz / o dni je rozhodnute
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly IbRetConfig _cfg;
        /// <summary>Config strategie - `EntryLayers.Wrap` z neho berie defaulty klucov, ktore profil nema.</summary>
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly TimeZoneInfo _zone;
        private readonly Warmup _warmup;
        public readonly BarHistory History;

        private bool _hasDay;
        private DateTime _day;
        private double _ibHigh = double.NegativeInfinity;
        private double _ibLow = double.PositiveInfinity;
        private long _ibStartMs;
        private long _ibHighMs;
        private long _ibLowMs;
        private readonly List<double> _ibHist = new List<double>();   // sirky IB predoslych dni (minIbRel / maxIbRel)
        private bool _ibReady;
        private int _state = Wait;
        private string _pendingId;      // id limitky, kym sa nevyplni
        private bool _pendLong = true;
        private double _pendTake;
        private readonly List<string> _boxes = new List<string>();
        private bool _wasIn;

        public IbRetEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(IbRetConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public IbRetEngine(IbRetConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _zone = TimeZones.Get(Ny);
            History = new BarHistory(4, 14);
            _warmup = new Warmup(_tf);
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

        // ------------------------------------------------------------------ //

        private void Cancel(EngineOutput o, int idx, string reason)
        {
            o.Orders.Add(new OrderIntent(OrderAction.Cancel, _pendingId, idx, reason));
            _pendingId = null;
            _boxes.Clear();
            _wasIn = false;
        }

        private void Enter(EngineOutput o, Bar bar, int idx, bool isLong)
        {
            IbRetConfig cfg = _cfg;
            double rng = _ibHigh - _ibLow;
            double edge = isLong ? _ibHigh : _ibLow;
            int s = isLong ? 1 : -1;
            double[] lv = cfg.Levels(isLong);
            double stop = _inst.RoundPrice(edge - s * lv[1] * rng - s * cfg.slBufferTicks * _inst.TickSize);
            double entry;
            OrderType orderType;
            if (cfg.entryMode == "breakout")
            {
                entry = bar.Close;
                orderType = OrderType.Market;
            }
            else
            {
                entry = _inst.RoundPrice(edge - s * lv[0] * rng);
                orderType = OrderType.Limit;
            }
            double risk = Math.Abs(entry - stop);
            if (risk < _inst.TickSize * 2) return;
            double take = cfg.tpMode == "ext"
                ? _inst.RoundPrice(edge + s * lv[2] * rng)
                : _inst.RoundPrice(entry + s * lv[3] * risk);
            double reward = s * (take - entry);
            if (reward <= 0 || reward < cfg.minRR * risk - 1e-9) return;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, risk);
            if (q <= 0) return;
            TradePlan plan = new TradePlan(isLong ? Direction.Long : Direction.Short, entry, stop, take, q, risk, null);
            string oid = "ibret:" + idx.ToString(CultureInfo.InvariantCulture);
            OrderIntent intent = new OrderIntent(OrderAction.Entry, oid, idx,
                "IB RETRACE " + (isLong ? "long" : "short") + ": IB " + PyMath.FormatG(_ibLow) + "–" + PyMath.FormatG(_ibHigh));
            intent.Direction = plan.Direction;
            intent.Plan = plan;
            intent.OrderType = orderType;
            o.Orders.Add(intent);
            if (orderType == OrderType.Limit)
            {
                _pendingId = oid;
                _pendLong = isLong;
                _pendTake = take;
            }

            long t = bar.Time + _stepMs;          // order plati od otvorenia dalsej sviecky
            long end = t + _stepMs;
            _boxes.Clear();
            _wasIn = false;
            AddBox(o, t, DrawKinds.TpBox, "tp", "TP", take, entry, end, LongColor);
            AddBox(o, t, DrawKinds.SlBox, "sl", "SL", stop, entry, end, ShortColor);
            DrawLabel label = new DrawLabel(IbRetKinds.Entry, t, entry, isLong ? "IB long" : "IB short", "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "ibret.e." + t.ToString(CultureInfo.InvariantCulture);
            o.Drawings.Add(label);
        }

        private void AddBox(EngineOutput o, long t, string kind, string tag, string text, double level, double entry,
                            long end, string color)
        {
            string bid = "ibret." + tag + "." + t.ToString(CultureInfo.InvariantCulture);
            DrawBox box = new DrawBox(kind, t, Math.Max(entry, level), end, Math.Min(entry, level), color);
            box.FillColor = Palette.WithAlpha(color, 60);
            box.ObjId = bid;
            box.Text = text + " " + PyMath.FormatG(level);
            o.Drawings.Add(box);
            _boxes.Add(bid);
        }

        // ------------------------------------------------------------------ //

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            IbRetConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            double pos = ctx.PositionSize;
            DateTime t = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            int mins = t.Hour * 60 + t.Minute;
            DateTime tc = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time + _stepMs), _zone);
            int closeMins = tc.Hour * 60 + tc.Minute;

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
                if (_pendingId != null) Cancel(o, idx, "nový deň");
                else if (pos == 0.0) { _boxes.Clear(); _wasIn = false; }   // obchod otvoreny aj zavrety v jednej sviecke
                _ibHigh = double.NegativeInfinity;
                _ibLow = double.PositiveInfinity;
                _ibReady = false;
                _state = Wait;
            }

            int ibStart = Hm(cfg.ibStart);
            int ibEnd = ibStart + cfg.ibMinutes;

            // ---- 2. IB ---------------------------------------------------------------- //
            if (!_ibReady && ibStart <= mins && mins < ibEnd)
            {
                if (double.IsNegativeInfinity(_ibHigh)) _ibStartMs = bar.Time;
                if (bar.High > _ibHigh) { _ibHigh = bar.High; _ibHighMs = bar.Time; }
                if (bar.Low < _ibLow) { _ibLow = bar.Low; _ibLowMs = bar.Time; }
                if (cfg.drawRange)
                {
                    DrawBox zb = new DrawBox(IbRetKinds.Zone, _ibStartMs, _ibHigh, _ibStartMs + cfg.ibMinutes * 60000L, _ibLow, ZoneColor);
                    zb.FillColor = Palette.WithAlpha(ZoneColor, 38);
                    zb.ObjId = "ibret.z." + _ibStartMs.ToString(CultureInfo.InvariantCulture);
                    zb.Text = "IB";
                    o.Drawings.Add(zb);
                }
                return o;
            }

            // ---- 3. IB hotovy ------------------------------------------------------------ //
            if (!_ibReady && mins >= ibEnd && !double.IsNegativeInfinity(_ibHigh))
            {
                _ibReady = true;
                double rng = _ibHigh - _ibLow;
                int wd = ((int)t.DayOfWeek + 6) % 7;          // Python weekday(): pondelok 0
                bool[] days = { cfg.tradeMon, cfg.tradeTue, cfg.tradeWed, cfg.tradeThu, cfg.tradeFri };
                double pct = rng > 0 ? rng / ((_ibHigh + _ibLow) / 2.0) * 100.0 : 0.0;
                int maxLen = Math.Max(1, cfg.ibAvgDays);
                double sum = 0.0;
                foreach (double h in _ibHist) sum += h;
                bool hasRel = _ibHist.Count == maxLen && sum > 0;
                double rel = hasRel ? rng / (sum / _ibHist.Count) : 0.0;
                bool useRel = cfg.minIbRel > 0 || cfg.maxIbRel > 0;
                if (rng <= 0 || wd > 4 || !days[wd]
                    || (cfg.minIbPoints > 0 && rng < cfg.minIbPoints)
                    || (cfg.maxIbPoints > 0 && rng > cfg.maxIbPoints)
                    || (cfg.minIbPct > 0 && pct < cfg.minIbPct)
                    || (cfg.maxIbPct > 0 && pct > cfg.maxIbPct)
                    || (useRel && (!hasRel || (cfg.minIbRel > 0 && rel < cfg.minIbRel)
                                   || (cfg.maxIbRel > 0 && rel > cfg.maxIbRel))))
                    _state = Done;
                if (rng > 0)
                {
                    _ibHist.Add(rng);
                    if (_ibHist.Count > maxLen) _ibHist.RemoveAt(0);
                }
            }
            if (!_ibReady) return o;

            // ---- 4. limitka sa vyplnila? ------------------------------------------------- //
            if (_pendingId != null && (pos != 0.0 || ctx.OpenOrderIds.Contains(_pendingId)))
                _pendingId = null;

            // ---- 5. koniec -------------------------------------------------------------- //
            if (cfg.closeAtEnd && pos != 0.0 && closeMins >= Hm(cfg.exitTime))
            {
                o.CloseSession = true;
                List<string> ids = new List<string>(ctx.OpenOrderIds);
                ids.Sort(StringComparer.Ordinal);
                foreach (string orderId in ids)
                    o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx,
                        "koniec " + cfg.exitTime.ToString("0000", CultureInfo.InvariantCulture) + " NY"));
                return o;
            }

            // ---- 6. cakajuca limitka ------------------------------------------------------- //
            if (_pendingId != null)
            {
                bool lng = _pendLong;
                string reason = null;
                if (closeMins >= Hm(cfg.lastEntry)) reason = "koniec vstupov";
                else if (lng ? bar.Low < _ibLow : bar.High > _ibHigh) reason = "prieraz druhej strany IB";
                else if (lng ? bar.High >= _pendTake : bar.Low <= _pendTake) reason = "cieľ bez návratu";
                if (reason != null) Cancel(o, idx, reason);
                return o;
            }
            if (_state != Wait) return o;

            // ---- 7. prieraz ---------------------------------------------------------------- //
            bool up, down;
            if (cfg.breakOn == "wick")
            {
                down = bar.Low < _ibLow;                      // oba okraje v jednom bare = medvedi (IB Lab)
                up = bar.High > _ibHigh && !down;
            }
            else if (cfg.breakOn == "body")
            {
                up = Math.Min(bar.Open, bar.Close) > _ibHigh;
                down = Math.Max(bar.Open, bar.Close) < _ibLow;
            }
            else
            {
                up = bar.Close > _ibHigh;
                down = bar.Close < _ibLow;
            }
            if (!(up || down)) return o;
            _state = Done;                                    // o dni rozhoduje prvy prieraz
            if (pos != 0.0) return o;                         // pozicia z predosleho dna (bez konca dna) - dnes bez vstupu
            int hhmm = t.Hour * 100 + t.Minute;
            if (!(cfg.breakFrom <= hhmm && hhmm <= cfg.breakTo)) return o;
            if ((up && !cfg.AllowLong) || (down && !cfg.AllowShort)) return o;
            if (cfg.biasFilter != "off")
            {
                bool bull = _ibLowMs < _ibHighMs;            // lowFirst (IB Lab), inak highFirst
                if ((up == bull) != (cfg.biasFilter == "with")) return o;
            }
            Enter(o, bar, idx, up);
            return o;
        }
    }
}
