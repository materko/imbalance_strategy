// Okno detekcneho TF (`zoneDetectionTF`) - zrkadlo `tradebot/strategies/ibs/htf.py`.
// Drzi uzavrete bary detekcneho TF a na bare grafu, kde sa prave uzavrela nova perioda, vrati
// `HtfWindow` - presne Pine `first5mTick`. Ktore styri bary to su, sa pocita z CASU UZAVRETIA baru grafu.
using System;
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.IbsNinja
{
    public sealed class HtfFeeder : IHtfFeeder
    {
        public readonly long HtfMs;
        public readonly long StepMs;
        private readonly int _volSmaLen;
        private readonly int _tfMinutes;
        private readonly Dictionary<long, Bar> _bars = new Dictionary<long, Bar>();
        private readonly Dictionary<long, double> _volSma = new Dictionary<long, double>();
        private readonly List<double> _volumes = new List<double>();
        private readonly Queue<long> _order = new Queue<long>();
        private long? _prevOpen;
        private readonly int _keep;

        public HtfFeeder(IbsConfig cfg, int chartTfMinutes)
        {
            _tfMinutes = IbsConfig.TimeframeOptionMinutes(cfg.zoneDetectionTF);
            HtfMs = _tfMinutes * 60000L;
            StepMs = chartTfMinutes * 60000L;
            _volSmaLen = cfg.volSmaLen;
            // inkrementalne krmenie: drzat len tolko barov, kolko treba na okno + SMA
            _keep = _volSmaLen + HtfWindow.RequiredBars + 8;
        }

        public int TfMinutes { get { return _tfMinutes; } }

        public int Count { get { return _bars.Count; } }

        /// <summary>Otvaracie casy HTF barov, ktore Pine `request.security` vidi na danom bare grafu
        /// (`lookahead_off` + offset [1]): najnovsi je o DVA HTF bary pred periodou, v ktorej sa bar grafu zavrel.</summary>
        public static long[] WindowOpens(long tsMs, long chartTfMs, long htfMs, int count)
        {
            long closeMs = tsMs + chartTfMs;
            long newest = (closeMs / htfMs) * htfMs - 2 * htfMs;
            long[] opens = new long[count];
            for (int i = 0; i < count; i++) opens[i] = newest - i * htfMs;
            return opens;
        }

        /// <summary>Zaeviduje UZAVRETY bar detekcneho TF (NinjaTrader: sekundarna seria).</summary>
        public void Feed(Bar bar)
        {
            if (_bars.ContainsKey(bar.Time)) return;
            _bars[bar.Time] = bar;
            _order.Enqueue(bar.Time);
            _volumes.Add(bar.Volume);
            int n = _volSmaLen;
            if (_volumes.Count >= n)
            {
                double sum = 0.0;
                for (int i = _volumes.Count - n; i < _volumes.Count; i++) sum += _volumes[i];
                _volSma[bar.Time] = sum / n;
            }
            else
            {
                _volSma[bar.Time] = 0.0;
            }
            if (_volumes.Count > _keep) _volumes.RemoveRange(0, _volumes.Count - _keep);
            while (_order.Count > _keep)
            {
                long old = _order.Dequeue();
                _bars.Remove(old);
                _volSma.Remove(old);
            }
        }

        /// <summary>Okno styroch uzavretych HTF barov - ale len na bare, kde zacala nova perioda.</summary>
        public HtfWindow WindowFor(long tsMs)
        {
            long htfOpen = tsMs / HtfMs * HtfMs;
            bool isNewPeriod = _prevOpen.HasValue && htfOpen != _prevOpen.Value;
            _prevOpen = htfOpen;
            if (!isNewPeriod) return null;
            long[] opens = WindowOpens(tsMs, StepMs, HtfMs, HtfWindow.RequiredBars);
            Bar[] bars = new Bar[opens.Length];
            for (int i = 0; i < opens.Length; i++)
            {
                Bar b;
                if (!_bars.TryGetValue(opens[i], out b)) return null;
                bars[i] = b;
            }
            double sma;
            if (!_volSma.TryGetValue(opens[0], out sma)) sma = 0.0;
            return new HtfWindow(bars, sma);
        }
    }
}
