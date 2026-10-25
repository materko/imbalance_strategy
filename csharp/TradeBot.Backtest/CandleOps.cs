// Vyber a skladanie sviecok - zrkadlo `tradebot/core/candles.py` (resample_ohlcv). Pravidlo musi
// sediet do bitu, inak by natvny backtest videl ine bary nez Python emulator:
//
// * bary sa zarovnavaju na nasobky TF od epochy (label/closed left), tyzden na pondelok 5. 1. 1970;
// * open = prvy, high = max, low = min, close = posledny, volume = sucet (Kahan) - NaN sa preskakuje (pandas);
// * perioda bez jedineho 1m baru (alebo s open len NaN) sa zahodi, nedoplna sa.
using System;
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Backtest
{
    public static class CandleOps
    {
        public const long MinuteMs = 60000;
        public const int WeekMinutes = 7 * 24 * 60;
        /// <summary>Pondelok 5. 1. 1970 - zaciatok tyzdna (1. 1. 1970 bol stvrtok).</summary>
        public const long WeekOriginMs = 4L * 86400000L;

        public static long FloorDiv(long a, long b)
        {
            long q = a / b;
            return (a % b != 0 && ((a < 0) != (b < 0))) ? q - 1 : q;
        }

        /// <summary>Riadky s fromMs &lt;= cas &lt; toMs; long.MinValue / long.MaxValue = bez hranice.</summary>
        public static Candles Slice(Candles c, long fromMs, long toMs)
        {
            int lo = Lower(c.Time, fromMs), hi = Lower(c.Time, toMs);
            if (fromMs == long.MinValue) lo = 0;
            if (toMs == long.MaxValue) hi = c.Count;
            return Range(c, lo, Math.Max(lo, hi));
        }

        /// <summary>Prvy index s casom &gt;= t (casy su vzostupne).</summary>
        public static int Lower(long[] times, long t)
        {
            int lo = 0, hi = times.Length;
            while (lo < hi)
            {
                int mid = (lo + hi) >> 1;
                if (times[mid] < t) lo = mid + 1; else hi = mid;
            }
            return lo;
        }

        public static Candles Range(Candles c, int start, int end)
        {
            int n = end - start;
            Candles r = new Candles();
            r.Time = new long[n]; r.Open = new double[n]; r.High = new double[n];
            r.Low = new double[n]; r.Close = new double[n]; r.Volume = new double[n];
            Array.Copy(c.Time, start, r.Time, 0, n);
            Array.Copy(c.Open, start, r.Open, 0, n);
            Array.Copy(c.High, start, r.High, 0, n);
            Array.Copy(c.Low, start, r.Low, 0, n);
            Array.Copy(c.Close, start, r.Close, 0, n);
            Array.Copy(c.Volume, start, r.Volume, 0, n);
            return r;
        }

        /// <summary>Zaciatok periody `minutes`, do ktorej patri cas `t` (ako pandas resample).</summary>
        public static long PeriodStart(long t, int minutes)
        {
            long step = minutes * MinuteMs;
            long origin = minutes % WeekMinutes == 0 ? WeekOriginMs : 0;
            return FloorDiv(t - origin, step) * step + origin;
        }

        /// <summary>1m (alebo jemnejsie zoradene) sviecky -> `minutes`; `minutes` &lt;= 1 vrati vstup.</summary>
        public static Candles Resample(Candles c, int minutes)
        {
            if (minutes <= 1) return c;
            List<long> t = new List<long>();
            List<double> o = new List<double>(), h = new List<double>(), l = new List<double>(),
                cl = new List<double>(), v = new List<double>();
            int i = 0, n = c.Count;
            while (i < n)
            {
                long p = PeriodStart(c.Time[i], minutes);
                double fo = double.NaN, fh = double.NaN, fl = double.NaN, fc = double.NaN, fv = 0.0, comp = 0.0;
                for (; i < n && PeriodStart(c.Time[i], minutes) == p; i++)
                {
                    double x = c.Open[i];
                    if (double.IsNaN(fo) && !double.IsNaN(x)) fo = x;
                    x = c.High[i];
                    if (!double.IsNaN(x) && (double.IsNaN(fh) || x > fh)) fh = x;
                    x = c.Low[i];
                    if (!double.IsNaN(x) && (double.IsNaN(fl) || x < fl)) fl = x;
                    x = c.Close[i];
                    if (!double.IsNaN(x)) fc = x;
                    x = c.Volume[i];
                    if (!double.IsNaN(x))
                    {
                        // Kahanov sucet ako pandas `group_sum` - naivny `+=` by sa lisil v poslednom bite
                        double y = x - comp;
                        double s = fv + y;
                        comp = s - fv - y;
                        if (double.IsNaN(comp)) comp = 0.0;
                        fv = s;
                    }
                }
                if (double.IsNaN(fo)) continue;
                t.Add(p); o.Add(fo); h.Add(fh); l.Add(fl); cl.Add(fc); v.Add(fv);
            }
            Candles r = new Candles();
            r.Time = t.ToArray(); r.Open = o.ToArray(); r.High = h.ToArray();
            r.Low = l.ToArray(); r.Close = cl.ToArray(); r.Volume = v.ToArray();
            return r;
        }

        public static Bar[] Bars(Candles c)
        {
            Bar[] b = new Bar[c.Count];
            for (int i = 0; i < b.Length; i++) b[i] = new Bar(c.Time[i], c.Open[i], c.High[i], c.Low[i], c.Close[i], c.Volume[i]);
            return b;
        }
    }
}
