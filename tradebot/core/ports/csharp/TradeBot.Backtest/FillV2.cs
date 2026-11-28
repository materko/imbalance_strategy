// Plnenie prikazov fill v2 (SMERNICA V2 §3, zadanie U4) - riadok po riadku zrkadlo `tradebot/core/fill.py`
// (FillModel). Vzorce, poradie operacii aj okna CFD v case New York musia sediet do bitu, inak by sa natvny backtest
// rozisiel s Python emulatorom (`tester/tests/test_csharp_backtest.py`, parita na v2).
//
// Jazyk je zamerne C# 5 a len BCL.
using System;
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Backtest
{
    public sealed class FillV2
    {
        public const string Reject = "reject";
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        private static readonly TimeZoneInfo Ny = TimeZones.Get("America/New_York");
        private const int RthFrom = 9 * 60 + 30, RthTo = 16 * 60, OpenFrom = 9 * 60 + 30, OpenTo = 9 * 60 + 40;
        private const int RollHourUtc = 21;

        public string Kind = "futures";
        public string Instrument = "";
        public double Tick, CostTicks, SlipTicks, PassTicks, CostPctMaker, CostPctTaker, SlipPct;
        public double Spread, OffMult = 2, PassSell, SlipSl, SlipMkt, OpenMult = 2, OpenSlip, NewsMult = 4, NewsSlip;
        public double Commission, Swap;
        public int NewsMin = 5;
        public long[] News = new long[0];

        public bool Cfd { get { return Kind == "cfd"; } }

        /// <summary>`FillModel.to_dict` z Pythonu (kluc `fill` v JSON instrumentu); null = v1.</summary>
        public static FillV2 FromJson(Dictionary<string, object> d)
        {
            if (d == null) return null;
            FillV2 f = new FillV2();
            f.Kind = Json.GetString(d, "kind", "futures");
            f.Instrument = Json.GetString(d, "instrument", "");
            f.Tick = Json.GetDouble(d, "tick", 0); f.CostTicks = Json.GetDouble(d, "cost_ticks", 0);
            f.SlipTicks = Json.GetDouble(d, "slip_ticks", 0); f.PassTicks = Json.GetDouble(d, "pass_ticks", 0);
            f.CostPctMaker = Json.GetDouble(d, "cost_pct_maker", 0); f.CostPctTaker = Json.GetDouble(d, "cost_pct_taker", 0);
            f.SlipPct = Json.GetDouble(d, "slip_pct", 0);
            f.Spread = Json.GetDouble(d, "spread", 0); f.OffMult = Json.GetDouble(d, "off_mult", 2);
            f.PassSell = Json.GetDouble(d, "pass_sell", 0); f.SlipSl = Json.GetDouble(d, "slip_sl", 0);
            f.SlipMkt = Json.GetDouble(d, "slip_mkt", 0); f.OpenMult = Json.GetDouble(d, "open_mult", 2);
            f.OpenSlip = Json.GetDouble(d, "open_slip", 0); f.NewsMult = Json.GetDouble(d, "news_mult", 4);
            f.NewsSlip = Json.GetDouble(d, "news_slip", 0); f.Commission = Json.GetDouble(d, "commission", 0);
            f.Swap = Json.GetDouble(d, "swap", 0); f.NewsMin = (int)Json.GetDouble(d, "news_min", 5);
            List<object> news = Json.Get(d, "news") as List<object>;
            if (news != null)
            {
                f.News = new long[news.Count];
                for (int i = 0; i < news.Count; i++) f.News[i] = Convert.ToInt64(news[i]);
                Array.Sort(f.News);
            }
            return f;
        }

        private double Slip(double price) { return SlipTicks * Tick + SlipPct * price; }
        private double Pass() { return PassTicks * Tick; }

        /// <summary>(S, sklz navyse) v minute `ms` (CFD): spravy &gt; otvorenie NY &gt; hlavna seansa &gt; mimo seansy.</summary>
        public void Window(long ms, out double s, out double extra)
        {
            s = Spread; extra = 0;
            if (News.Length > 0)
            {
                int i = Array.BinarySearch(News, ms);
                if (i < 0) i = ~i;
                else while (i > 0 && News[i - 1] == ms) i--;   // bisect_left
                long best = long.MaxValue;
                for (int j = i - 1; j <= i; j++)
                    if (j >= 0 && j < News.Length) best = Math.Min(best, Math.Abs(ms - News[j]));
                if (best != long.MaxValue && best <= NewsMin * 60000L) { s = Spread * NewsMult; extra = NewsSlip; return; }
            }
            DateTime t = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(ms), Ny);
            int m = t.Hour * 60 + t.Minute;
            bool weekday = t.DayOfWeek != DayOfWeek.Saturday && t.DayOfWeek != DayOfWeek.Sunday;
            if (weekday && m >= OpenFrom && m < OpenTo) { s = Spread * OpenMult; extra = OpenSlip; return; }
            if (weekday && m >= RthFrom && m < RthTo) { s = Spread; extra = 0; return; }
            s = Spread * OffMult; extra = 0;
        }

        /// <summary>Vstup: true + cena a `atOpen`, false = nevyplnene, `rejected` = CFD limit za trhom pri odoslani.
        /// `kind` = market / stop / limit.</summary>
        public bool Entry(long ms, double o, double h, double l, bool isLong, string kind, double price, bool firstMinute,
                          out double px, out bool atOpen, out bool rejected)
        {
            px = 0; atOpen = false; rejected = false;
            if (kind == "market")
            {
                if (!firstMinute) return false;
                px = Market(ms, o, isLong); atOpen = true;
                return true;
            }
            if (Cfd)
            {
                double s, extra;
                Window(ms, out s, out extra);
                if (kind == "stop")
                {
                    if (isLong)
                    {
                        if (h + s >= price) { px = Math.Max(price, o + s) + SlipSl + extra; atOpen = o + s >= price; return true; }
                        return false;
                    }
                    if (l <= price) { px = Math.Min(price, o) - SlipSl - extra; atOpen = o <= price; return true; }
                    return false;
                }
                if (firstMinute && ((isLong && price >= o + s) || (!isLong && price <= o))) { rejected = true; return false; }
                if (isLong) { if (l <= price - s) { px = price; return true; } return false; }
                if (h >= price + PassSell) { px = price; return true; }
                return false;
            }
            if (kind == "stop")
            {
                double sl = Slip(price);
                if (isLong) { if (h >= price) { px = Math.Max(price, o) + sl; atOpen = o >= price; return true; } return false; }
                if (l <= price) { px = Math.Min(price, o) - sl; atOpen = o <= price; return true; }
                return false;
            }
            double p = Pass();
            if (isLong) { if (l <= price - p) { px = price; return true; } return false; }
            if (h >= price + p) { px = price; return true; }
            return false;
        }

        /// <summary>Vystup: true + cena, je to SL, nerozhodnutelne. SL aj TP v jednej minute -&gt; SL.</summary>
        public bool Exit(long ms, double o, double h, double l, bool isLong, double stop, double tp,
                         out double px, out bool isSl, out bool amb)
        {
            bool hitSl, hitTp;
            double slPx;
            if (Cfd)
            {
                double s, extra;
                Window(ms, out s, out extra);
                if (isLong) { hitSl = l <= stop; hitTp = h >= tp + PassSell; slPx = Math.Min(stop, o) - SlipSl - extra; }
                else { hitSl = h + s >= stop; hitTp = l <= tp - s; slPx = Math.Max(stop, o + s) + SlipSl + extra; }
            }
            else
            {
                double p = Pass();
                if (isLong) { hitSl = l <= stop; hitTp = h >= tp + p; slPx = Math.Min(stop, o) - Slip(stop); }
                else { hitSl = h >= stop; hitTp = l <= tp - p; slPx = Math.Max(stop, o) + Slip(stop); }
            }
            px = 0; isSl = false; amb = false;
            if (hitSl) { px = slPx; isSl = true; amb = hitTp; return true; }
            if (hitTp) { px = tp; return true; }
            return false;
        }

        /// <summary>Trhovy prikaz (aj vystup v case) na cene `price` (bid pri CFD).</summary>
        public double Market(long ms, double price, bool buy)
        {
            if (Cfd)
            {
                double s, extra;
                Window(ms, out s, out extra);
                return buy ? price + s + SlipMkt + extra : price - SlipMkt - extra;
            }
            double sl = Slip(price);
            return buy ? price + sl : price - sl;
        }

        /// <summary>Naklad strany ako podiel nominalu (`trade_money`): futures cost_ticks·T/cena, BTC maker/taker %,
        /// CFD provizia/cena.</summary>
        public double SideFee(double price, bool maker)
        {
            if (price <= 0) return 0.0;
            if (Cfd) return Commission / price;
            if (CostPctMaker != 0 || CostPctTaker != 0) return maker ? CostPctMaker : CostPctTaker;
            return CostTicks * Tick / price;
        }

        /// <summary>Pocet rolloverov (21:00 UTC) medzi otvorenim a zatvorenim - swap CFD.</summary>
        public int Nights(long openMs, long closeMs)
        {
            long day = 86400000L, roll = RollHourUtc * 3600000L;
            long first = CandleOps.FloorDiv(openMs - roll, day) + 1;
            long last = CandleOps.FloorDiv(closeMs - roll, day);
            return (int)Math.Max(0, last - first + 1);
        }
    }
}
