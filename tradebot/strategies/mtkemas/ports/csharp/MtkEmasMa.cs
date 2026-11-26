// Klzave priemery MTK EMAS bar po bare - zrkadlo `tradebot/strategies/mtkemas/ma.py` (tie iste vzorce a poradie
// scitania ako Python, aby obe dali tie iste bity).
using System;
using System.Collections.Generic;

namespace TradeBot.Strategies.MtkEmasNet
{
    public interface IMa
    {
        /// <summary>Hodnota po bare, alebo null, kym priemer nema dost barov.</summary>
        double? Push(double c, double v);
    }

    internal sealed class Ewm
    {
        private readonly double _a;
        private bool _has;
        private double _y;
        public Ewm(double alpha) { _a = alpha; }
        public double Push(double x)
        {
            _y = !_has ? x : (1.0 - _a) * _y + _a * x;
            _has = true;
            return _y;
        }
    }

    internal static class Win
    {
        public static double Sum(List<double> xs)
        {
            double t = 0.0;
            for (int i = 0; i < xs.Count; i++) t += xs[i];
            return t;
        }

        public static void Add(List<double> xs, double x, int max)
        {
            xs.Add(x);
            if (xs.Count > max) xs.RemoveAt(0);
        }
    }

    internal sealed class EmaMa : IMa
    {
        private readonly int _n;
        private readonly Ewm _e;
        private int _count;
        public EmaMa(int n, bool rma) { _n = n; _e = new Ewm(rma ? 1.0 / n : 2.0 / (n + 1)); }
        public double? Push(double c, double v)
        {
            _count++;
            double y = _e.Push(c);
            return _count >= _n ? y : (double?)null;
        }
    }

    internal sealed class SmaMa : IMa
    {
        private readonly int _n;
        private readonly List<double> _w = new List<double>();
        public SmaMa(int n) { _n = n; }
        public double? Push(double c, double v)
        {
            Win.Add(_w, c, _n);
            return _w.Count == _n ? Win.Sum(_w) / _n : (double?)null;
        }
    }

    internal sealed class WmaMa : IMa
    {
        private readonly int _n;
        private readonly double _den;
        private readonly List<double> _w = new List<double>();
        public WmaMa(int n) { _n = n; _den = n * (n + 1) / 2.0; }
        public double? Push(double c, double v)
        {
            Win.Add(_w, c, _n);
            if (_w.Count < _n) return null;
            double t = 0.0;
            for (int i = 0; i < _w.Count; i++) t += (i + 1) * _w[i];
            return t / _den;
        }
    }

    internal sealed class HmaMa : IMa
    {
        private readonly WmaMa _half, _full, _out;
        public HmaMa(int n)
        {
            _half = new WmaMa(Math.Max(1, n / 2));
            _full = new WmaMa(n);
            _out = new WmaMa(Math.Max(1, (int)Math.Round(Math.Sqrt(n), MidpointRounding.ToEven)));
        }
        public double? Push(double c, double v)
        {
            double? a = _half.Push(c, v);
            double? b = _full.Push(c, v);
            if (!a.HasValue || !b.HasValue) return null;
            return _out.Push(2 * a.Value - b.Value, 0.0);
        }
    }

    internal sealed class DemaMa : IMa
    {
        private readonly Ewm _e1, _e2, _e3;
        private readonly bool _triple;
        private readonly int _skip;
        private int _count;
        public DemaMa(int n, bool triple)
        {
            double a = 2.0 / (n + 1);
            _e1 = new Ewm(a); _e2 = new Ewm(a); _e3 = new Ewm(a);
            _triple = triple;
            _skip = (triple ? 3 : 2) * n;
        }
        public double? Push(double c, double v)
        {
            _count++;
            double y1 = _e1.Push(c);
            double y2 = _e2.Push(y1);
            double r = _triple ? 3 * y1 - 3 * y2 + _e3.Push(y2) : 2 * y1 - y2;
            return _count > _skip ? r : (double?)null;
        }
    }

    internal sealed class VwmaMa : IMa
    {
        private readonly int _n;
        private readonly List<double> _cv = new List<double>(), _vv = new List<double>();
        public VwmaMa(int n) { _n = n; }
        public double? Push(double c, double v)
        {
            Win.Add(_cv, c * v, _n);
            Win.Add(_vv, v, _n);
            if (_vv.Count < _n) return null;
            double den = Win.Sum(_vv);
            return den != 0 ? Win.Sum(_cv) / den : (double?)null;
        }
    }

    internal sealed class KamaMa : IMa
    {
        private const double Fast = 2.0 / 3.0;
        private const double Slow = 2.0 / 31.0;
        private readonly int _n;
        private readonly List<double> _closes = new List<double>(), _diffs = new List<double>();
        private double? _prev, _val;
        public KamaMa(int n) { _n = n; }
        public double? Push(double c, double v)
        {
            Win.Add(_diffs, _prev.HasValue ? Math.Abs(c - _prev.Value) : 0.0, _n);
            _prev = c;
            Win.Add(_closes, c, _n + 1);
            if (_closes.Count < _n + 1) return null;
            if (!_val.HasValue) { _val = c; return _val; }
            double ch = Math.Abs(c - _closes[0]);
            double vol = Win.Sum(_diffs);
            double er = vol > 0 ? ch / vol : 0.0;
            double k = er * (Fast - Slow) + Slow;
            _val = _val.Value + k * k * (c - _val.Value);
            return _val;
        }
    }

    public static class MaFactory
    {
        public static IMa Make(string kind, int n)
        {
            n = Math.Max(1, n);
            switch (kind)
            {
                case "ema": return new EmaMa(n, false);
                case "rma": return new EmaMa(n, true);
                case "sma": return new SmaMa(n);
                case "wma": return new WmaMa(n);
                case "hma": return new HmaMa(n);
                case "dema": return new DemaMa(n, false);
                case "tema": return new DemaMa(n, true);
                case "vwma": return new VwmaMa(n);
                case "kama": return new KamaMa(n);
            }
            throw new ArgumentException("MTK EMAS: neznamy typ priemeru '" + kind + "'");
        }
    }

    /// <summary>ATR = RMA(true range, n), start prvym TR - Python `ma.Atr`.</summary>
    public sealed class EmasAtr
    {
        private readonly Ewm _e;
        private double? _prevClose;
        public double Value;
        public EmasAtr(int n) { _e = new Ewm(1.0 / Math.Max(1, n)); }
        public double Push(double high, double low, double close)
        {
            double pc = _prevClose.HasValue ? _prevClose.Value : close;
            double tr = Math.Max(high - low, Math.Max(Math.Abs(high - pc), Math.Abs(low - pc)));
            _prevClose = close;
            Value = _e.Push(tr);
            return Value;
        }
    }
}
