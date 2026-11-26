// `MtkEmasEngine` - MTK EMAS 1.0 s jadrom v C#. Zrkadlo `tradebot/strategies/mtkemas/engine.py`; s Python enginom sa
// porovnava bar po bare, na rovnost (ordery, kresby, koniec seansy).
//
// Na kazdom uzavretom bare: ATR a priemer(y) dostanu bar; znamienko rozdielu (price: zavretie - priemer, cross:
// rychly - pomaly); krizenie = zmena z nenuloveho na opacne nenulove. Pri krizeni: pozicia proti smeru sa zavrie
// (`exitOnSignal`), potom vstup v smere krizenia - market, stop slAtr x ATR, ciel rrTarget R (inak daleko), trailing
// trailAtr x ATR od trailFromR R a zamok na vstup pri beAtR R. Filter EMA 200 robi `EntryLayers` (trendFilter).
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.MtkEmasNet
{
    [TradeBotEngine("mtkemasnet", "MTK EMAS 1.0 (C#)")]
    public class MtkEmasEngine : IEngine, IConfigured
    {
        private const string LongColor = "#10b981";
        private const string ShortColor = "#ef4444";
        private const double NoTpR = 100.0;
        private const double NoTrail = 1e12;

        private readonly MtkEmasConfig _cfg;
        /// <summary>Config strategie - `EntryLayers.Wrap` z neho berie defaulty klucov, ktore profil nema.</summary>
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _stepMs;
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        public readonly BarHistory History;
        private readonly IMa _slow, _fast;
        private readonly EmasAtr _atr;
        private int _prevSgn;
        private readonly List<string> _boxes = new List<string>();
        private bool _wasIn;

        public MtkEmasEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(MtkEmasConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public MtkEmasEngine(MtkEmasConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _stepMs = _tf * 60000L;
            _slow = MaFactory.Make(cfg.maType, cfg.slowLen);
            _fast = cfg.signalMode == "cross" ? MaFactory.Make(cfg.maType, cfg.fastLen) : null;
            _atr = new EmasAtr(cfg.atrLen);
            History = new BarHistory(4, cfg.atrLen);
            int need = 3 * Math.Max(cfg.slowLen, cfg.fastLen) + cfg.atrLen + 10;
            _warmup = new Warmup(_tf).Add("priemer " + cfg.maType.ToUpperInvariant() + " " + cfg.slowLen.ToString(CultureInfo.InvariantCulture), need);
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

        private void Track(EngineOutput o, Bar bar, MarketContext ctx)
        {
            if (_boxes.Count == 0) return;
            foreach (string oid in _boxes)
                o.Drawings.Add(new DrawUpdate(oid, "x2_ms", bar.Time + _stepMs));
            if (ctx.PositionSize != 0.0) _wasIn = true;
            else if (_wasIn) { _boxes.Clear(); _wasIn = false; }
        }

        private void Enter(EngineOutput o, Bar bar, int idx, bool isLong, double atr)
        {
            MtkEmasConfig cfg = _cfg;
            int s = isLong ? 1 : -1;
            double c = bar.Close;
            double risk = cfg.slAtr * atr;
            if (risk < _inst.TickSize * 2) return;
            double rr = cfg.rrTarget;
            double take = c + s * (rr > 0 ? rr : NoTpR) * risk;
            TrailingPlan trailing = null;
            if (cfg.trailAtr > 0 || cfg.beAtR > 0)
            {
                double act = cfg.trailAtr > 0 ? cfg.trailFromR * risk : NoTrail;
                double off = cfg.trailAtr * atr;
                trailing = new TrailingPlan(act, off, act / _inst.TickSize, off / _inst.TickSize,
                                            cfg.beAtR > 0 ? cfg.beAtR * risk : 0.0, 0.0);
            }
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, risk);
            if (q <= 0) return;
            TradePlan plan = new TradePlan(isLong ? Direction.Long : Direction.Short, _inst.RoundPrice(c),
                                           _inst.RoundPrice(c - s * risk), _inst.RoundPrice(take), q, risk, trailing);
            OrderIntent intent = new OrderIntent(OrderAction.Entry, "mtkemas:" + idx.ToString(CultureInfo.InvariantCulture), idx,
                "MTK EMAS " + (isLong ? "long" : "short") + ": kríženie " + cfg.maType.ToUpperInvariant());
            intent.Direction = plan.Direction;
            intent.Plan = plan;
            intent.OrderType = OrderType.Market;
            o.Orders.Add(intent);
            long t = bar.Time + _stepMs;          // market sa plni na otvoreni dalsej sviecky
            long end = t + _stepMs;
            _boxes.Clear();
            _wasIn = false;
            if (rr > 0) AddBox(o, DrawKinds.TpBox, "tp", "TP ", plan.TakeProfit, plan.Entry, LongColor, t, end);
            AddBox(o, DrawKinds.SlBox, "sl", "SL ", plan.StopLoss, plan.Entry, ShortColor, t, end);
            DrawLabel label = new DrawLabel(MtkEmasKinds.Entry, t, plan.Entry, isLong ? "EMAS long" : "EMAS short", "#ffffff");
            label.Style = isLong ? LabelStyles.Up : LabelStyles.Down;
            label.Above = !isLong;
            label.BgColor = isLong ? LongColor : ShortColor;
            label.ObjId = "mtkemas.e." + t.ToString(CultureInfo.InvariantCulture);
            o.Drawings.Add(label);
        }

        private void AddBox(EngineOutput o, string kind, string tag, string prefix, double level, double entry, string color,
                            long t, long end)
        {
            string oid = "mtkemas." + tag + "." + t.ToString(CultureInfo.InvariantCulture);
            DrawBox box = new DrawBox(kind, t, Math.Max(entry, level), end, Math.Min(entry, level), color);
            box.FillColor = Palette.WithAlpha(color, 80);
            box.ObjId = oid;
            box.Text = prefix + PyMath.FormatG(level);
            o.Drawings.Add(box);
            _boxes.Add(oid);
        }

        // ------------------------------------------------------------------ //

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            MtkEmasConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            Track(o, bar, ctx);
            double pos = ctx.PositionSize;
            double atr = _atr.Push(bar.High, bar.Low, bar.Close);
            double? slow = _slow.Push(bar.Close, bar.Volume);
            double? diff;
            if (_fast != null)
            {
                double? fast = _fast.Push(bar.Close, bar.Volume);
                diff = !fast.HasValue || !slow.HasValue ? (double?)null : fast.Value - slow.Value;
            }
            else
            {
                diff = !slow.HasValue ? (double?)null : bar.Close - slow.Value;
            }
            int sgn = !diff.HasValue ? 0 : (diff.Value > 0 ? 1 : (diff.Value < 0 ? -1 : 0));
            int prev = _prevSgn;
            _prevSgn = sgn;
            if (prev == 0 || sgn == 0 || sgn == prev) return o;
            bool isLong = sgn > 0;
            bool closed = false;
            if (pos != 0.0 && (pos > 0) != isLong && cfg.exitOnSignal)
            {
                o.CloseSession = true;
                List<string> ids = new List<string>(ctx.OpenOrderIds);
                ids.Sort(StringComparer.Ordinal);
                foreach (string orderId in ids)
                    o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, idx, "opačné kríženie"));
                closed = true;
            }
            if (pos != 0.0 && !closed) return o;
            if ((isLong && !cfg.AllowLong) || (!isLong && !cfg.AllowShort) || atr <= 0) return o;
            Enter(o, bar, idx, isLong, atr);
            return o;
        }
    }
}
