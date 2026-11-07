// Priemerny ATR za N seans - zrkadlo `tradebot/strategies/voltbreak/avgatr.py` (Pine Volt Break / Overnight Bias ORB).
//   SessionAvgAtr - ATR zo seans polnoc-16:00 CT, seansa sa uzavrie na prvom bare o 16:00 CT alebo neskor,
//   DailyAvgAtr   - denne sviecky burzy (CME obchodny den od 17:00 CT predosleho dna), hodnota z poslednej uzavretej.
using System;
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.VoltBreakNet
{
    public sealed class SessionAvgAtr
    {
        public const int SessionEndMin = 16 * 60;
        private readonly int _atrLen, _avgLen;
        private bool _prevIn;
        private double? _sH, _sL, _sC, _prevC, _atr;
        private int _n;
        private readonly List<double> _hist = new List<double>();

        public SessionAvgAtr(int atrLen, int avgLen) { _atrLen = Math.Max(1, atrLen); _avgLen = Math.Max(1, avgLen); }

        public double? Value { get { return _hist.Count >= _avgLen ? (double?)(PyMath.Sum(_hist) / _hist.Count) : null; } }

        public void Push(Bar bar, int barMin)
        {
            bool inSess = barMin < SessionEndMin;
            bool beg = inSess && !_prevIn;
            bool done = !inSess && _prevIn;
            if (done && _sH.HasValue)
            {
                double tr = !_prevC.HasValue ? _sH.Value - _sL.Value
                    : Math.Max(_sH.Value, _prevC.Value) - Math.Min(_sL.Value, _prevC.Value);
                _n += 1;
                if (!_atr.HasValue) _atr = tr;
                else if (_n <= _atrLen) _atr = _atr.Value + (tr - _atr.Value) / _n;
                else _atr = (_atr.Value * (_atrLen - 1) + tr) / _atrLen;
                _hist.Add(_atr.Value);
                while (_hist.Count > _avgLen) _hist.RemoveAt(0);
                _prevC = _sC;
            }
            if (beg) { _sH = bar.High; _sL = bar.Low; }
            else if (inSess && _sH.HasValue) { _sH = Math.Max(_sH.Value, bar.High); _sL = Math.Min(_sL.Value, bar.Low); }
            if (inSess) _sC = bar.Close;
            _prevIn = inSess;
        }
    }

    public sealed class DailyAvgAtr
    {
        private readonly int _atrLen, _avgLen;
        private bool _hasDay;
        private DateTime _day;
        private double _h, _l, _c;
        private bool _hasOhlc;
        private double? _prevClose, _atr;
        private readonly List<double> _seed = new List<double>();
        private readonly List<double> _hist = new List<double>();
        public double? Value;

        public DailyAvgAtr(int atrLen, int avgLen) { _atrLen = Math.Max(1, atrLen); _avgLen = Math.Max(1, avgLen); }

        public void Push(Bar bar, DateTime local)
        {
            DateTime day = local.AddHours(7).Date;   // obchodny den CME od 17:00 CT
            if (!_hasDay || day != _day)
            {
                if (_hasOhlc) CloseDay();
                _hasDay = true;
                _day = day;
                _h = bar.High; _l = bar.Low; _c = bar.Close;
                _hasOhlc = true;
            }
            else
            {
                _h = Math.Max(_h, bar.High); _l = Math.Min(_l, bar.Low); _c = bar.Close;
            }
        }

        private void CloseDay()
        {
            double tr = !_prevClose.HasValue ? _h - _l : Math.Max(_h, _prevClose.Value) - Math.Min(_l, _prevClose.Value);
            _prevClose = _c;
            if (!_atr.HasValue)
            {
                _seed.Add(tr);
                if (_seed.Count == _atrLen) _atr = PyMath.Sum(_seed) / _atrLen;
            }
            else _atr = _atr.Value + (tr - _atr.Value) / _atrLen;
            if (_atr.HasValue)
            {
                _hist.Add(_atr.Value);
                while (_hist.Count > _avgLen) _hist.RemoveAt(0);
                if (_hist.Count >= _avgLen) Value = PyMath.Sum(_hist) / _avgLen;
            }
        }
    }
}
