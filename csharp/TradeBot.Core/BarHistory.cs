// Kruhova historia barov s Pine semantikou indexovania - zrkadlo `tradebot/core/history.py`.
// `history[0]` je aktualny bar, `history[1]` predchadzajuci atd.
using System;

namespace TradeBot.Core
{
    public sealed class BarHistory
    {
        private readonly Bar[] _ring;
        private int _count;
        private int _head = -1; // index posledneho vlozeneho baru
        private readonly int _atrLen;
        private double _atr;
        private double _trSum;

        /// <summary>Pine `bar_index` - rastie donekonecna, aj ked stare bary z pamate vypadnu.</summary>
        public int BarIndex = -1;

        public BarHistory(int maxlen, int atrLen)
        {
            _ring = new Bar[Math.Max(1, maxlen)];
            _atrLen = Math.Max(1, atrLen);
        }

        public void Append(Bar bar)
        {
            bool hasPrev = _count > 0;
            double prevClose = hasPrev ? _ring[_head].Close : 0.0;
            _head = (_head + 1) % _ring.Length;
            _ring[_head] = bar;
            if (_count < _ring.Length) _count++;
            BarIndex++;
            UpdateAtr(bar, hasPrev, prevClose);
        }

        public int Count { get { return _count; } }

        /// <summary>Pine `bar[offset]` - 0 je aktualny bar.</summary>
        public Bar this[int offset]
        {
            get
            {
                if (offset < 0) throw new IndexOutOfRangeException("offset musi byt >= 0 (Pine indexuje dozadu)");
                if (offset >= _count) throw new IndexOutOfRangeException("bar[" + offset + "] nie je v historii (" + _count + " barov)");
                int i = _head - offset;
                if (i < 0) i += _ring.Length;
                return _ring[i];
            }
        }

        public bool Has(int offset) { return offset >= 0 && offset < _count; }

        public Bar Current { get { return _ring[_head]; } }

        /// <summary>`bar_index` baru vzdialeneho `offset` barov dozadu.</summary>
        public int IndexOf(int offset) { return BarIndex - offset; }

        public int AtrWarmupBars { get { return WarmupMath.RmaBars(_atrLen); } }

        /// <summary>Wilderov ATR (Pine `ta.atr(atrLen)`). 0.0, kym nie je dost barov.</summary>
        public double Atr { get { return _atr; } }

        private void UpdateAtr(Bar bar, bool hasPrev, double prevClose)
        {
            double tr = bar.High - bar.Low;
            if (hasPrev)
                tr = Math.Max(tr, Math.Max(Math.Abs(bar.High - prevClose), Math.Abs(bar.Low - prevClose)));

            int n = _atrLen;
            if (BarIndex < n)
            {
                _trSum += tr;
                _atr = BarIndex == n - 1 ? _trSum / n : 0.0;
                return;
            }
            _atr = (_atr * (n - 1) + tr) / n;
        }

        /// <summary>Pine `ta.sma(volume, length)[offset]`. Vrati 0.0, kym nie je dost barov.</summary>
        public double SmaVolume(int length, int offset)
        {
            if (length <= 0 || _count < length + offset) return 0.0;
            double total = 0.0;
            for (int i = offset; i < offset + length; i++) total += this[i].Volume;
            return total / length;
        }

        /// <summary>Pine `ta.sma(high - low, length)[offset]`.</summary>
        public double SmaRange(int length, int offset)
        {
            if (length <= 0 || _count < length + offset) return 0.0;
            double total = 0.0;
            for (int i = offset; i < offset + length; i++)
            {
                Bar b = this[i];
                total += b.High - b.Low;
            }
            return total / length;
        }
    }
}
