// Nativny backtest C# strategie s emulovanym brokerom MultiCharts - riadok po riadku zrkadlo
// `tradebot/adapters/multicharts/runner.py` (MCRunner) a `emulator.py` (emulate). Engine sa vola
// priamo (bez mosta cez pythonnet a JSON), inak je cesta ta ista:
//
// * order zadany na close baru plati na dalsi bar; market sa plni na otvoreni jeho prvej minuty,
//   limitka pri dotyku (alebo na otvoreni, ak je cena uz za limitom), stop vstup pri prerazeni;
// * naraz jedna pozicia; SL a TP sa rozhoduju po 1m sviecikach, SL aj TP v tej istej minute = SL;
// * koniec seansy zavrie poziciu na close baru; trailing stop sa prepocita na close kazdeho baru;
// * indikatory s vlastnou predhistoriou sa seeduju z 1m dat pred prvym barom (`seed_engine`).
//
// Zhodu s Python emulatorom (obchod po obchode) strazi `tester/tests/test_csharp_backtest.py`.
using System;
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Backtest
{
    public sealed class EmuTrade
    {
        public string OrderId;
        public Direction Direction;
        public double Qty;
        public double Entry;
        public long OpenMs;
        public double StopInitial;
        public double TakeProfit;
        public bool Market;
        public double StopLast;
        public double Exit = double.NaN;
        public long CloseMs;
        public string Reason = "";
        public double MaxPrice;
        public double MinPrice;

        public bool IsLong { get { return Direction == Direction.Long; } }
        public bool Closed { get { return !double.IsNaN(Exit); } }
    }

    public sealed class EmuResult
    {
        public List<EmuTrade> Trades = new List<EmuTrade>();
        public int Bars;
        public long FirstMs, LastMs;
        public double FirstClose = double.NaN, LastClose = double.NaN;
        public int Ambiguous;
        public string Log = "";
        /// <summary>Close posledneho baru kazdeho dna UTC (zaciatok dna v ms) - krivka trhu v suhrne behu.</summary>
        public SortedDictionary<long, double> Daily = new SortedDictionary<long, double>();
    }

    /// <summary>Order, ktory ma tento bar lezat na trhu (Python `LiveOrder`).</summary>
    internal sealed class LiveOrder
    {
        public string OrderId;
        public Direction Direction;
        public TradePlan Plan;
        public bool Market;
        public bool Stop;
    }

    /// <summary>Python `dict` zivych orderov: prepis existujuceho kluca drzi jeho poradie, novy ide na koniec.</summary>
    internal sealed class LiveBook
    {
        private readonly List<string> _order = new List<string>();
        private readonly Dictionary<string, LiveOrder> _map = new Dictionary<string, LiveOrder>();

        public int Count { get { return _map.Count; } }

        public void Set(LiveOrder o)
        {
            if (!_map.ContainsKey(o.OrderId)) _order.Add(o.OrderId);
            _map[o.OrderId] = o;
        }

        public bool Remove(string id)
        {
            if (id == null || !_map.Remove(id)) return false;
            _order.Remove(id);
            return true;
        }

        public LiveOrder Last { get { return _order.Count == 0 ? null : _map[_order[_order.Count - 1]]; } }

        public List<LiveOrder> Values()
        {
            List<LiveOrder> v = new List<LiveOrder>(_order.Count);
            foreach (string id in _order) v.Add(_map[id]);
            return v;
        }
    }

    internal sealed class BarOutput
    {
        public List<LiveOrder> Entries = new List<LiveOrder>();
        public TradePlan ExitPlan;
        public double? ExitStop;
        public bool CloseSession;
    }

    /// <summary>Python `MCRunner` - jeden graf, `OnBar` presne raz za uzavrety bar.</summary>
    internal sealed class McRunner
    {
        public readonly IEngine Engine;
        public readonly IHtfFeeder Htf;
        private readonly long _stepMs;
        private readonly int? _maxDailyWins;
        private readonly LiveBook _live = new LiveBook();
        private TradePlan _openPlan;
        private string _openId;
        private double? _openExtreme;
        private long? _lastTs;
        private int? _closedTrades;
        private long? _winDay;
        private int _winsToday;
        private bool _sessionCloseSent;

        public McRunner(IEngine engine, Dictionary<string, object> config, int chartTfMinutes)
        {
            Engine = engine;
            Htf = engine.CreateHtfFeeder();
            _stepMs = chartTfMinutes * CandleOps.MinuteMs;
            object mdw;
            if (config.TryGetValue("maxDailyWins", out mdw) && mdw != null) _maxDailyWins = Json.ToInt(mdw);
        }

        public void FeedHtf(Bar b) { if (Htf != null) Htf.Feed(b); }

        public BarOutput OnBar(Bar bar, double positionSize, int closedTrades, List<double> closedTradePnls)
        {
            if (_lastTs.HasValue && bar.Time <= _lastTs.Value) return new BarOutput();
            _lastTs = bar.Time;
            bool dailyLimit = DailyWinLimit(bar, closedTradePnls);

            string roundTripId = null;
            if (_closedTrades.HasValue && closedTrades > _closedTrades.Value && positionSize == 0.0
                && _openPlan == null && _live.Count > 0)
            {
                LiveOrder last = _live.Last;
                roundTripId = last.OrderId;
                _live.Remove(roundTripId);
            }
            _closedTrades = closedTrades;

            if (positionSize != 0.0 && _openPlan == null)
            {
                LiveOrder last = _live.Last;
                _openPlan = last != null ? last.Plan : null;
                _openId = last != null ? last.OrderId : null;
                _openExtreme = null;
                if (_openId != null) _live.Remove(_openId);
            }

            // ako `EngineHost.OnBar`: InTradeWindow ostava false (most ho do C# neposiela)
            MarketContext ctx = new MarketContext();
            ctx.PositionSize = positionSize;
            ctx.DailyWinLimitReached = dailyLimit;
            if (positionSize != 0.0 && _openId != null) ctx.OpenOrderIds.Add(_openId);
            if (roundTripId != null) { ctx.OpenOrderIds.Clear(); ctx.OpenOrderIds.Add(roundTripId); }
            HtfWindow htf = Htf != null ? Htf.WindowFor(bar.Time) : null;
            EngineOutput o = Engine.OnBar(bar, htf, ctx);

            BarOutput result = new BarOutput();
            result.CloseSession = o.CloseSession;
            foreach (OrderIntent intent in o.Orders)
            {
                if (intent.Action == OrderAction.Cancel)
                {
                    _live.Remove(intent.OrderId);
                    if (intent.OrderId == _openId && positionSize == 0.0)
                    {
                        _openPlan = null;
                        _openId = null;
                        _openExtreme = null;
                    }
                }
                else if (intent.Plan != null)
                {
                    LiveOrder live = new LiveOrder();
                    live.OrderId = intent.OrderId;
                    live.Direction = intent.Direction.HasValue ? intent.Direction.Value : intent.Plan.Direction;
                    live.Plan = intent.Plan;
                    live.Market = intent.OrderType == OrderType.Market;
                    live.Stop = intent.OrderType == OrderType.Stop;
                    _live.Set(live);
                }
            }

            if (positionSize != 0.0)
            {
                result.ExitPlan = _openPlan;
                result.ExitStop = TrailedStop(bar);
            }
            else
            {
                _openPlan = null;
                _openId = null;
                _openExtreme = null;
                result.Entries = _live.Values();
            }
            _sessionCloseSent = o.CloseSession && positionSize != 0.0;
            return result;
        }

        private bool DailyWinLimit(Bar bar, List<double> pnls)
        {
            long day = CandleOps.FloorDiv(bar.Time, 86400000L);
            if (!_winDay.HasValue || day != _winDay.Value)
            {
                _winDay = day;
                _winsToday = 0;
            }
            bool limit = _maxDailyWins.HasValue && _winsToday >= _maxDailyWins.Value;
            if (pnls != null)
            {
                int start = _sessionCloseSent && pnls.Count > 0 ? 1 : 0;   // SESSION_END sa v Pine nepocita
                for (int i = start; i < pnls.Count; i++) if (pnls[i] > 0) _winsToday++;
            }
            return limit;
        }

        private double? TrailedStop(Bar bar)
        {
            TradePlan plan = _openPlan;
            if (plan == null) return null;
            if (plan.Trailing == null) return plan.StopLoss;
            bool isLong = plan.Direction == Direction.Long;
            double best = isLong ? bar.High : bar.Low;
            if (!_openExtreme.HasValue) _openExtreme = plan.Entry;
            _openExtreme = isLong ? Math.Max(_openExtreme.Value, best) : Math.Min(_openExtreme.Value, best);
            return plan.Trailing.StopPrice(plan.Direction, plan.Entry, plan.StopLoss, _openExtreme.Value);
        }
    }

    /// <summary>Bary pre jeden graf a okno: graf, 1m detail rozdeleny po baroch grafu a vyssie TF (lenivo).
    /// Po `Prepare` sa uz len cita, takze ho smie zdielat viac vlakien naraz.</summary>
    public sealed class EmuData
    {
        public readonly Candles M1;
        public readonly int ChartTf;
        public readonly Bar[] Chart;
        public readonly Bar[] Detail;
        internal readonly Dictionary<long, int[]> ByBar = new Dictionary<long, int[]>();
        private readonly Candles _inRange;
        private readonly Dictionary<int, Bar[]> _htf = new Dictionary<int, Bar[]>();
        private readonly Dictionary<int, long[]> _htfCloses = new Dictionary<int, long[]>();

        private EmuData(Candles m1, int chartTf, long fromMs, long toMs)
        {
            M1 = m1;
            ChartTf = chartTf;
            _inRange = CandleOps.Slice(m1, fromMs, toMs);
            Chart = CandleOps.Bars(CandleOps.Resample(_inRange, chartTf));
            Detail = CandleOps.Bars(_inRange);
            long step = chartTf * CandleOps.MinuteMs;
            // 1m bary podla baru grafu (kluc od epochy, ako `b.time // step * step` v Pythone); su zoradene
            for (int i = 0; i < Detail.Length;)
            {
                long key = CandleOps.FloorDiv(Detail[i].Time, step) * step;
                int j = i;
                while (j < Detail.Length && CandleOps.FloorDiv(Detail[j].Time, step) * step == key) j++;
                if (!ByBar.ContainsKey(key)) ByBar[key] = new int[] { i, j - i };
                i = j;
            }
        }

        /// <summary>`fromMs`/`toMs`: long.MinValue / long.MaxValue = bez hranice.</summary>
        public static EmuData Prepare(Candles m1, int chartTf, long fromMs, long toMs)
        {
            return new EmuData(m1, chartTf, fromMs, toMs);
        }

        public Bar[] HtfBars(int minutes)
        {
            lock (_htf)
            {
                Bar[] b;
                if (!_htf.TryGetValue(minutes, out b))
                {
                    b = CandleOps.Bars(CandleOps.Resample(_inRange, minutes));
                    long[] closes = new long[b.Length];
                    for (int i = 0; i < b.Length; i++) closes[i] = b[i].Time + minutes * CandleOps.MinuteMs;
                    _htf[minutes] = b;
                    _htfCloses[minutes] = closes;
                }
                return b;
            }
        }

        public long[] HtfCloses(int minutes)
        {
            HtfBars(minutes);
            lock (_htf) { return _htfCloses[minutes]; }
        }
    }

    public static class McEmulator
    {
        private static double? EntryFill(Bar sub, LiveOrder live, bool firstMinute)
        {
            double price = live.Plan.Entry;
            bool isLong = live.Direction == Direction.Long;
            if (live.Market) return firstMinute ? sub.Open : (double?)null;
            if (live.Stop)
            {
                if (isLong)
                {
                    if (sub.Open >= price) return sub.Open;
                    return sub.High >= price ? price : (double?)null;
                }
                if (sub.Open <= price) return sub.Open;
                return sub.Low <= price ? price : (double?)null;
            }
            if (isLong)
            {
                if (sub.Open <= price) return sub.Open;
                return sub.Low <= price ? price : (double?)null;
            }
            if (sub.Open >= price) return sub.Open;
            return sub.High >= price ? price : (double?)null;
        }

        /// <summary>Zisk uzavreteho obchodu po poplatku - `tradebot.core.money.trade_money(...).net`.</summary>
        public static double NetPnl(EmuTrade t, InstrumentSpec inst, double fee)
        {
            if (!t.Closed) return 0.0;
            double pv = inst.PointValue;
            double smer = t.IsLong ? 1.0 : -1.0;
            double nOpen = t.Entry * t.Qty * pv;
            double nClose = t.Exit * t.Qty * pv;
            double gross = (t.Exit - t.Entry) * smer * t.Qty * pv;
            return gross - (nOpen * fee + nClose * fee);
        }

        /// <summary>(cena, dovod, nerozhodnutelne) alebo false. Pri SL aj TP v jednej minute berie SL.</summary>
        private static bool ExitFill(Bar sub, EmuTrade trade, double stop, double tp, out double px, out string reason, out bool amb)
        {
            bool hitSl, hitTp;
            double slPx, tpPx;
            if (trade.IsLong)
            {
                hitSl = sub.Low <= stop;
                hitTp = sub.High >= tp;
                slPx = Math.Min(stop, sub.Open);
                tpPx = Math.Max(tp, sub.Open);
            }
            else
            {
                hitSl = sub.High >= stop;
                hitTp = sub.Low <= tp;
                slPx = Math.Max(stop, sub.Open);
                tpPx = Math.Min(tp, sub.Open);
            }
            px = 0; reason = ""; amb = false;
            if (!(hitSl || hitTp)) return false;
            if (hitSl)
            {
                px = slPx;
                reason = stop != trade.StopInitial ? "trailing_stop" : "stop_loss";
                amb = hitTp;
                return true;
            }
            px = tpPx;
            reason = "take_profit";
            return true;
        }

        /// <summary>Python `_seed_before` + `seed_engine`: seeded indikatory z 1m dat pred prvym barom grafu.</summary>
        private static string SeedBefore(IEngine engine, Candles m1, long firstMs)
        {
            Warmup w = engine.Warmup;
            if (w == null) return "";
            long span = 0;
            bool any = false;
            foreach (WarmupNeed n in w.Needs)
                if (n.Seeded) { any = true; span = Math.Max(span, SpanMs(n)); }
            if (!any) return "";
            Candles before = CandleOps.Slice(m1, firstMs - span, firstMs);
            List<string> parts = new List<string>();
            foreach (WarmupNeed n in w.Needs)
            {
                if (!n.Seeded) continue;
                int got = 0;
                if (before.Count > 0)
                {
                    long ms = n.TfMinutes * CandleOps.MinuteMs;
                    long period = CandleOps.FloorDiv(firstMs, ms) * ms;
                    Candles part = CandleOps.Slice(before, period - SpanMs(n), firstMs);
                    Candles htf = CandleOps.Resample(part, n.TfMinutes);
                    List<Bar> closed = new List<Bar>();
                    Bar partial = null;
                    for (int i = 0; i < htf.Count; i++)
                    {
                        Bar b = new Bar(htf.Time[i], htf.Open[i], htf.High[i], htf.Low[i], htf.Close[i], htf.Volume[i]);
                        if (b.Time < period) closed.Add(b);
                        else if (b.Time == period) partial = b;
                    }
                    if (n.Bars <= 0) closed.Clear();
                    else if (closed.Count > n.Bars) closed.RemoveRange(0, closed.Count - n.Bars);
                    n.Seed(closed, partial);
                    got = closed.Count;
                }
                parts.Add(n.Name + " @" + n.TfMinutes + "m " + got + "/" + n.Bars);
            }
            return "predhistoria indikatorov z dat pred behom: " + string.Join(", ", parts.ToArray());
        }

        private static long SpanMs(WarmupNeed n)
        {
            return 2L * (n.Bars + 1) * n.TfMinutes * CandleOps.MinuteMs + WarmupMath.SeedSlackDays * 1440L * CandleOps.MinuteMs;
        }

        /// <summary>Prehra engine cez emulovaneho brokera MultiCharts. `fromMs`/`toMs`: long.MinValue/MaxValue = bez hranice.
        /// `fee` je poplatok na stranu - tu len na zisk obchodu pre denny limit vyhier.</summary>
        public static EmuResult Run(IEngine engine, Dictionary<string, object> config, Candles m1, int chartTf,
                                    long fromMs, long toMs, double fee)
        {
            return Run(engine, config, EmuData.Prepare(m1, chartTf, fromMs, toMs), fee);
        }

        /// <summary>Beh nad pripravenymi datami - hyperopt ich pripravi raz a zdiela medzi vlaknami (len citanie).</summary>
        public static EmuResult Run(IEngine engine, Dictionary<string, object> config, EmuData data, double fee)
        {
            if (engine.ChartTfMinutes != data.ChartTf)
                throw new ArgumentException("engine je na " + engine.ChartTfMinutes + "m, data na " + data.ChartTf + "m");
            EmuResult res = new EmuResult();
            Bar[] chart = data.Chart;
            Bar[] detail = data.Detail;
            Dictionary<long, int[]> byBar = data.ByBar;
            long step = data.ChartTf * CandleOps.MinuteMs;

            McRunner runner = new McRunner(engine, config, data.ChartTf);
            List<string> log = new List<string>();
            if (chart.Length > 0)
            {
                string s = SeedBefore(engine, data.M1, chart[0].Time);
                if (s.Length > 0) log.Add(s);
            }
            Bar[] htfBars = new Bar[0];
            long[] htfCloses = new long[0];
            if (runner.Htf != null)
            {
                htfBars = data.HtfBars(runner.Htf.TfMinutes);
                htfCloses = data.HtfCloses(runner.Htf.TfMinutes);
            }
            int htfPos = 0;

            List<EmuTrade> trades = res.Trades;
            EmuTrade open = null;
            double activeStop = 0, activeTp = 0;
            List<LiveOrder> pending = new List<LiveOrder>();
            int reported = 0;
            Bar[] single = new Bar[1];

            for (int bi = 0; bi < chart.Length; bi++)
            {
                Bar bar = chart[bi];
                int[] range;
                Bar[] subs;
                int subStart, subCount;
                if (byBar.TryGetValue(bar.Time, out range)) { subs = detail; subStart = range[0]; subCount = range[1]; }
                else { single[0] = bar; subs = single; subStart = 0; subCount = 1; }

                // -- broker: vyplnenie orderov zadanych na predoslom bare
                for (int k = 0; k < subCount; k++)
                {
                    Bar sub = subs[subStart + k];
                    bool filledNow = false;
                    if (open == null && pending.Count > 0)
                    {
                        foreach (LiveOrder live in pending)
                        {
                            double? px = EntryFill(sub, live, k == 0);
                            if (!px.HasValue) continue;
                            open = new EmuTrade();
                            open.OrderId = live.OrderId; open.Direction = live.Direction; open.Qty = live.Plan.Qty;
                            open.Entry = px.Value; open.OpenMs = sub.Time; open.StopInitial = live.Plan.StopLoss;
                            open.TakeProfit = live.Plan.TakeProfit; open.Market = live.Market;
                            open.StopLast = live.Plan.StopLoss; open.MaxPrice = px.Value; open.MinPrice = px.Value;
                            activeStop = live.Plan.StopLoss;
                            activeTp = live.Plan.TakeProfit;
                            filledNow = px.Value == sub.Open;   // limitka uprostred minuty: vystup az od dalsej
                            pending = new List<LiveOrder>();
                            break;
                        }
                    }
                    if (open == null) continue;
                    open.MaxPrice = Math.Max(open.MaxPrice, sub.High);
                    open.MinPrice = Math.Min(open.MinPrice, sub.Low);
                    if (open.OpenMs == sub.Time && !filledNow) continue;
                    double xp; string reason; bool amb;
                    if (!ExitFill(sub, open, activeStop, activeTp, out xp, out reason, out amb)) continue;
                    if (amb) res.Ambiguous++;
                    open.Exit = xp; open.CloseMs = sub.Time; open.Reason = reason; open.StopLast = activeStop;
                    trades.Add(open);
                    open = null;
                }

                // -- strategia na close baru; HTF bary uzavrete najneskor s tymto barom idu pred `OnBar`
                if (htfBars.Length > 0)
                {
                    int end = UpperBound(htfCloses, bar.Time + step);
                    for (int h = htfPos; h < end; h++) runner.FeedHtf(htfBars[h]);
                    htfPos = Math.Max(htfPos, end);
                }
                double position = open != null ? open.Qty * (open.IsLong ? 1.0 : -1.0) : 0.0;
                List<double> pnls = new List<double>();
                for (int t = reported; t < trades.Count; t++) pnls.Add(NetPnl(trades[t], engine.Inst, fee));
                BarOutput o = runner.OnBar(bar, position, trades.Count, pnls);
                reported = trades.Count;

                if (o.CloseSession && open != null)
                {
                    open.Exit = bar.Close; open.CloseMs = bar.Time; open.Reason = "session_end"; open.StopLast = activeStop;
                    trades.Add(open);
                    open = null;
                }
                if (open != null && o.ExitPlan != null)
                {
                    activeStop = o.ExitStop.HasValue ? o.ExitStop.Value : o.ExitPlan.StopLoss;
                    activeTp = o.ExitPlan.TakeProfit;
                }
                pending = open == null ? new List<LiveOrder>(o.Entries) : new List<LiveOrder>();

                if (double.IsNaN(res.FirstClose)) res.FirstClose = bar.Close;
                res.LastClose = bar.Close;
                res.Daily[CandleOps.FloorDiv(bar.Time, 86400000L) * 86400000L] = bar.Close;
            }

            if (open != null)   // koniec dat s otvorenou poziciou -> zavriet na poslednom close
            {
                open.Exit = res.LastClose; open.CloseMs = chart[chart.Length - 1].Time; open.Reason = "force_exit";
                open.StopLast = activeStop;
                trades.Add(open);
            }
            res.Bars = chart.Length;
            if (chart.Length > 0) { res.FirstMs = chart[0].Time; res.LastMs = chart[chart.Length - 1].Time; }
            log.Add("hotovo: " + trades.Count + " obchodov, nerozhodnutelnych minut " + res.Ambiguous);
            res.Log = string.Join("\n", log.ToArray());
            return res;
        }

        /// <summary>Python `bisect_right`: prvy index s hodnotou &gt; x.</summary>
        private static int UpperBound(long[] a, long x)
        {
            int lo = 0, hi = a.Length;
            while (lo < hi)
            {
                int mid = (lo + hi) >> 1;
                if (a[mid] <= x) lo = mid + 1; else hi = mid;
            }
            return lo;
        }
    }
}
