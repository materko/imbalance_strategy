// Klzave priemery bar po bare - zrkadlo `tradebot/core/ma.py`.
// EMA sa rozbieha z jednoducheho priemeru prvych `n` hodnot (ako talib), nie z prvej hodnoty
// (ako Pine `ta.ema`); kym nema dost barov, vracia null. Koľko barov to trva: `WarmupMath.EmaBars`.
using System;

namespace TradeBot.Core
{
    /// <summary>Exponencialny klzavy priemer, `alpha = 2/(n+1)` - Python `tradebot.core.ma.EMA`.</summary>
    public sealed class Ema
    {
        public readonly int N;
        public readonly double Alpha;
        private double? _value;
        private int _seedCount;
        private double _seedSum;

        public Ema(int n)
        {
            N = Math.Max(1, n);
            Alpha = 2.0 / (n + 1);
        }

        public double? Value { get { return _value; } }

        public double? Push(double v)
        {
            if (!_value.HasValue)
            {
                // Python SMA: sucet cyklom zlava doprava (nie `sum()`), potom delenie
                _seedSum += v;
                _seedCount++;
                if (_seedCount == N) _value = _seedSum / N;
                return _value;
            }
            _value = _value.Value + Alpha * (v - _value.Value);
            return _value;
        }
    }
}
