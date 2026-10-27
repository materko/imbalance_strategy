// Seansovy VWAP bar po bare - zrkadlo `tradebot/core/vwap.py` (`SessionVwap`).
//
// VWAP = Σ(typicka cena × objem) / Σ objem od kotvy seansy, typicka cena = (high + low + close) / 3.
// Seansa sa zadava v minutach od polnoci v pasme; cez polnoc (Globex 18:00-17:00) ako start > end a patri
// k dnu, v ktorom konci. Pri `periodMinutes` sa bary grafu najprv zlozia do period (od kotvy) a VWAP sa
// pocita z uzavretych period - hodnota sa meni len pri zatvoreni periody, nic nerepaintuje.
using System;
using System.Collections.Generic;

namespace TradeBot.Core
{
    public sealed class SessionVwap
    {
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly int _tf;
        private readonly int _start;
        private readonly int _end;
        private readonly TimeZoneInfo _zone;
        private readonly int? _period;
        private readonly int _keep;

        /// <summary>posledna publikovana hodnota (null pred prvym barom seansy)</summary>
        public double? Value;
        /// <summary>zmenila sa hodnota na poslednom bare (pri periode len na jej zatvoreni)</summary>
        public bool Updated;
        /// <summary>posledny bar bol v seanse - mimo nej `Value` ostava zamrznuta na konci predoslej seansy</summary>
        public bool Live;
        /// <summary>den seansy (rok * 10000 + mesiac * 100 + den), null pred prvym barom seansy</summary>
        public int? Day;
        /// <summary>poslednych `keep` publikovanych hodnot dnesnej seansy, najnovsia posledna</summary>
        public readonly List<double> History = new List<double>();

        private double _pv;
        private double _vol;
        // rozpracovana perioda
        private bool _hasBucket;
        private int _bIdx;
        private double _bHigh, _bLow, _bClose, _bVol;

        public SessionVwap(int chartTfMinutes, int startMinutes, int endMinutes, string tz, int? periodMinutes, int keep)
        {
            _tf = Math.Max(1, chartTfMinutes);
            _start = startMinutes;
            _end = endMinutes;
            _zone = TimeZones.Get(tz);
            _period = periodMinutes.HasValue && periodMinutes.Value != 0 ? periodMinutes : null;
            _keep = Math.Max(2, keep);
        }

        private static int DayKey(DateTime d) { return d.Year * 10000 + d.Month * 100 + d.Day; }

        /// <summary>Den seansy a minuta od kotvy, alebo false mimo seansy.</summary>
        private bool SessionMinute(DateTime local, out int day, out int minute)
        {
            int m = local.Hour * 60 + local.Minute;
            day = DayKey(local);
            minute = 0;
            if (_start < _end)
            {
                if (_start <= m && m < _end) { minute = m - _start; return true; }
                return false;
            }
            // seansa cez polnoc: vecerna cast patri k nasledujucemu dnu
            if (m >= _start)
            {
                day = DayKey(local.Date.AddDays(1));
                minute = m - _start;
                return true;
            }
            if (m < _end)
            {
                minute = m + 1440 - _start;
                return true;
            }
            return false;
        }

        private void Reset(int day)
        {
            Day = day;
            Value = null;
            History.Clear();
            _pv = _vol = 0.0;
            _hasBucket = false;
        }

        private void Add(double high, double low, double close, double volume)
        {
            if (volume <= 0) return;
            _pv += (high + low + close) / 3.0 * volume;
            _vol += volume;
            Value = _pv / _vol;
            History.Add(Value.Value);
            if (History.Count > _keep) History.RemoveAt(0);
            Updated = true;
        }

        public double? Push(Bar bar)
        {
            Updated = false;
            DateTime local = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            int day, minute;
            bool inSession = SessionMinute(local, out day, out minute);
            Live = inSession;
            if (!inSession) return Value;
            if (!Day.HasValue || day != Day.Value) Reset(day);

            if (!_period.HasValue)
            {
                Add(bar.High, bar.Low, bar.Close, bar.Volume);
                return Value;
            }

            int period = _period.Value;
            int idx = minute / period;
            if (_hasBucket && _bIdx != idx)   // diera v datach: stara perioda sa uz nedoplni
            {
                Add(_bHigh, _bLow, _bClose, _bVol);
                _hasBucket = false;
            }
            if (!_hasBucket)
            {
                _hasBucket = true;
                _bIdx = idx; _bHigh = bar.High; _bLow = bar.Low; _bClose = bar.Close; _bVol = bar.Volume;
            }
            else
            {
                _bHigh = Math.Max(_bHigh, bar.High);
                _bLow = Math.Min(_bLow, bar.Low);
                _bClose = bar.Close;
                _bVol += bar.Volume;
            }
            // perioda sa zatvara na bare, za ktorym by dalsi bar zacal v novej periode alebo po seanse
            int span = ((_end - _start) % 1440 + 1440) % 1440;
            if (span == 0) span = 1440;
            int nxt = minute + _tf;
            if (nxt / period != idx || nxt >= span)
            {
                Add(_bHigh, _bLow, _bClose, _bVol);
                _hasBucket = false;
            }
            return Value;
        }

        /// <summary>O kolko sa VWAP zmenil za poslednych `barsBack` publikovanych hodnot.</summary>
        public double? Change(int barsBack)
        {
            int n = barsBack;
            if (n < 1 || History.Count <= n) return null;
            return History[History.Count - 1] - History[History.Count - 1 - n];
        }
    }
}
