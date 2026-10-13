// Velke imbalance (fair value gap) z vyssich TF - zrkadlo `tradebot/strategies/ibsentry/fvg.py`.
//
// Vrstva nic neobchoduje a nic nefiltruje: len najde medzery a engine z nich spravi obycajne zony v tej istej
// knihe ako SD zony. Vyssie TF sa skladaju z barov grafu rovnakym pravidlom ako `tradebot/core/candles.py`:
// bucket = floor(time / tf) * tf (od epochy), perioda bez barov sa nevypchava.
using System;
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.IbsEntryNet
{
    /// <summary>Najdena medzera medzi 1. a 3. svieckou trojice na danom TF.</summary>
    public sealed class FvgHit
    {
        public readonly double Top;
        public readonly double Bot;
        /// <summary>+1 = bullish (medzera pod cenou, dopyt), -1 = bearish (ponuka)</summary>
        public readonly int Direction;
        public readonly int TfMinutes;

        public FvgHit(double top, double bot, int direction, int tfMinutes)
        {
            Top = top; Bot = bot; Direction = direction; TfMinutes = tfMinutes;
        }
    }

    /// <summary>Sklada bary grafu na vyssi TF a vracia ich, az ked sa sviecka UZAVRELA.</summary>
    public sealed class TimeframeAggregator
    {
        private readonly long _tfMs;
        private long? _open;
        private Bar _acc;

        public TimeframeAggregator(int minutes) { _tfMs = minutes * 60000L; }

        /// <summary>Prida bar grafu; vrati uzavrety bar vyssieho TF, ak sa prave uzavrel (inak null).</summary>
        public Bar Push(Bar bar)
        {
            long bucket = bar.Time / _tfMs * _tfMs;
            Bar done = null;
            if (_open.HasValue && bucket != _open.Value)
            {
                done = _acc;
                _acc = null;
            }
            _open = bucket;
            if (_acc == null)
                _acc = new Bar(bucket, bar.Open, bar.High, bar.Low, bar.Close, bar.Volume);
            else
                _acc = new Bar(_acc.Time, _acc.Open, Math.Max(_acc.High, bar.High), Math.Min(_acc.Low, bar.Low),
                               bar.Close, _acc.Volume + bar.Volume);
            return done;
        }
    }

    /// <summary>Na kazdom bare grafu povie, ktore nove FVG sa na zapnutych TF prave uzavreli; v `Inverted` su
    /// medzery, ktore prave prerazila uzavreta sviecka toho isteho TF (IFVG, smer uz otoceny).</summary>
    public sealed class FvgDetector
    {
        /// <summary>Kolko neprerazenych medzier na TF sa sleduje kvoli inverzii - strop proti rastu pamate.</summary>
        public const int MaxOpenGaps = 200;

        private sealed class OpenGap
        {
            public FvgHit Hit;
            public long Born;
        }

        private readonly int[] _tfs;
        private readonly Dictionary<int, TimeframeAggregator> _aggs = new Dictionary<int, TimeframeAggregator>();
        private readonly Dictionary<int, List<Bar>> _recent = new Dictionary<int, List<Bar>>();
        private readonly Dictionary<int, List<OpenGap>> _open = new Dictionary<int, List<OpenGap>>();
        public List<FvgHit> Inverted = new List<FvgHit>();

        public FvgDetector(int[] tfMinutes)
        {
            _tfs = tfMinutes;
            foreach (int m in tfMinutes)
            {
                _aggs[m] = new TimeframeAggregator(m);
                _recent[m] = new List<Bar>();
                _open[m] = new List<OpenGap>();
            }
        }

        public List<FvgHit> OnBar(Bar bar, double minSize, long? maxAgeMs)
        {
            List<FvgHit> found = new List<FvgHit>();
            Inverted = new List<FvgHit>();
            foreach (int minutes in _tfs)
            {
                Bar closed = _aggs[minutes].Push(bar);
                if (closed == null) continue;
                CheckInversions(minutes, closed, bar.Time, maxAgeMs);
                List<Bar> recent = _recent[minutes];
                recent.Add(closed);
                if (recent.Count > 3) recent.RemoveRange(0, recent.Count - 3);
                if (recent.Count == 3)
                {
                    FvgHit hit = Detect(recent, minutes, minSize);
                    if (hit != null)
                    {
                        found.Add(hit);
                        List<OpenGap> gaps = _open[minutes];
                        OpenGap g = new OpenGap();
                        g.Hit = hit;
                        g.Born = bar.Time;
                        gaps.Add(g);
                        if (gaps.Count > MaxOpenGaps) gaps.RemoveRange(0, gaps.Count - MaxOpenGaps);
                    }
                }
            }
            return found;
        }

        /// <summary>Uzavreta sviecka TF prerazila zatvorenim niektoru zo sledovanych medzier?</summary>
        private void CheckInversions(int minutes, Bar closed, long nowMs, long? maxAgeMs)
        {
            List<OpenGap> keep = new List<OpenGap>();
            foreach (OpenGap g in _open[minutes])
            {
                if (maxAgeMs.HasValue && nowMs - g.Born > maxAgeMs.Value) continue;
                if (g.Hit.Direction == 1 && closed.Close < g.Hit.Bot)
                    Inverted.Add(new FvgHit(g.Hit.Top, g.Hit.Bot, -1, minutes));
                else if (g.Hit.Direction == -1 && closed.Close > g.Hit.Top)
                    Inverted.Add(new FvgHit(g.Hit.Top, g.Hit.Bot, 1, minutes));
                else
                    keep.Add(g);
            }
            _open[minutes] = keep;
        }

        /// <summary>Trojica sviecok: medzera medzi 1. a 3. je fair value gap (stredna je impulz, telo sa nekontroluje).</summary>
        private static FvgHit Detect(List<Bar> trio, int minutes, double minSize)
        {
            Bar far = trio[0], near = trio[2];
            if (near.Low > far.High && (near.Low - far.High) >= minSize) return new FvgHit(near.Low, far.High, 1, minutes);
            if (near.High < far.Low && (far.Low - near.High) >= minSize) return new FvgHit(far.Low, near.High, -1, minutes);
            return null;
        }
    }
}
