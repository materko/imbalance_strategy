// Smer obchodov podla indikatorov na vlastnom TF (`tradeDirection = Indicator`) - zrkadlo
// `tradebot/strategies/ibs/ta/trend.py`. Supertrend je doslovny prepis TradingView skriptu
// (Pine v4, KivancOzbilgic), ADX/DMI je TradingView „Directional Movement Index".
//
// Vyssi TF sa sklada z barov grafu (zarovnanie od epochy, perioda bez baru neexistuje), preto musi
// byt nasobkom TF grafu. HTF bar sa pouzije na bare grafu, ktory ho UZATVARA - filter nerepaintuje.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;

namespace TradeBot.Strategies.IbsNet
{
    /// <summary>Bary vyssieho TF z barov grafu; HTF bar sa uzavrie na bare grafu, ktory konci periodu.</summary>
    public sealed class BoundaryAggregator
    {
        public readonly long Ms;
        public readonly long StepMs;
        private long? _openTs;
        private double _o, _h, _l, _c, _v;

        public BoundaryAggregator(int minutes, int chartTfMinutes)
        {
            Ms = minutes * 60000L;
            StepMs = chartTfMinutes * 60000L;
        }

        private Bar CloseBar()
        {
            Bar closed = new Bar(_openTs.Value, _o, _h, _l, _c, _v);
            _openTs = null;
            return closed;
        }

        /// <summary>Prida bar grafu a vrati HTF bary, ktore sa nim uzavreli (0, 1 alebo 2).</summary>
        public List<Bar> Push(Bar bar)
        {
            List<Bar> closed = new List<Bar>();
            long period = bar.Time / Ms * Ms;
            if (_openTs.HasValue && period != _openTs.Value) closed.Add(CloseBar());
            if (!_openTs.HasValue)
            {
                _openTs = period;
                _o = bar.Open; _h = bar.High; _l = bar.Low; _c = bar.Close; _v = bar.Volume;
            }
            else
            {
                _h = Math.Max(_h, bar.High);
                _l = Math.Min(_l, bar.Low);
                _c = bar.Close;
                _v += bar.Volume;
            }
            if ((bar.Time + StepMs) % Ms == 0) closed.Add(CloseBar());
            return closed;
        }

        public bool Started { get { return _openTs.HasValue; } }

        /// <summary>Seeding: rozpracovana perioda z barov pred behom.</summary>
        public void Prime(Bar partial)
        {
            if (partial == null) return;
            _openTs = partial.Time / Ms * Ms;
            _o = partial.Open; _h = partial.High; _l = partial.Low; _c = partial.Close; _v = partial.Volume;
        }
    }

    /// <summary>Pine `ta.rma`: rozbeh z SMA prvych `n` hodnot, potom Wilderova rekurzia.</summary>
    internal sealed class Rma
    {
        private readonly int _n;
        private readonly List<double> _seed = new List<double>();
        public double? Value;

        public Rma(int n) { _n = n; }

        public double? Push(double v)
        {
            if (Value.HasValue)
            {
                Value = Value.Value + (v - Value.Value) / _n;
            }
            else
            {
                _seed.Add(v);
                if (_seed.Count == _n)
                {
                    double sum = 0.0;
                    foreach (double x in _seed) sum += x;
                    Value = sum / _n;
                }
            }
            return Value;
        }
    }

    /// <summary>TradingView „Supertrend" (Pine v4) bar po bare. `Trend` je +1/-1 (v Pine zacina na 1).</summary>
    public sealed class Supertrend
    {
        public readonly int Period;
        public readonly double Mult;
        public readonly PriceSource Source;
        public readonly bool ChangeAtr;
        private double? _rma;
        private readonly Queue<double> _trWindow = new Queue<double>();
        private double? _prevClose;
        public double? Up;
        public double? Dn;
        public int Trend = 1;
        public bool Flipped;
        public bool Ready;
        /// <summary>kolko barov vlastneho TF preslo vypoctom (aj zo seedingu)</summary>
        public int Bars;

        public Supertrend(int period, double multiplier, PriceSource source, bool changeAtr)
        {
            Period = Math.Max(1, period);
            Mult = multiplier;
            Source = source;
            ChangeAtr = changeAtr;
        }

        public bool Warmed { get { return Ready && Bars >= WarmupBars; } }

        public double? Line { get { return Trend == 1 ? Up : Dn; } }

        public int WarmupBars
        {
            get { return (ChangeAtr ? WarmupMath.RmaBars(Period) : WarmupMath.SmaBars(Period)) + 1; }
        }

        public static double PriceOf(Bar bar, PriceSource source)
        {
            double o = bar.Open, h = bar.High, lo = bar.Low, c = bar.Close;
            switch (source)
            {
                case PriceSource.Open: return o;
                case PriceSource.High: return h;
                case PriceSource.Low: return lo;
                case PriceSource.Close: return c;
                case PriceSource.Hlc3: return (h + lo + c) / 3.0;
                case PriceSource.Ohlc4: return (o + h + lo + c) / 4.0;
                case PriceSource.Hlcc4: return (h + lo + 2.0 * c) / 4.0;
            }
            return (h + lo) / 2.0;
        }

        private void WindowAppend(double tr)
        {
            _trWindow.Enqueue(tr);
            while (_trWindow.Count > Period) _trWindow.Dequeue();
        }

        private double WindowSum()
        {
            double sum = 0.0;
            foreach (double x in _trWindow) sum += x;
            return sum;
        }

        private double? Atr(Bar bar)
        {
            if (!_prevClose.HasValue)
            {
                // Pine v4: `atr()` berie `tr(true)` = high-low, `sma(tr, n)` ma na prvom bare na
                if (ChangeAtr) WindowAppend(bar.High - bar.Low);
                return RmaStep(null);
            }
            double prev = _prevClose.Value;
            double tr = Math.Max(bar.High - bar.Low, Math.Max(Math.Abs(bar.High - prev), Math.Abs(bar.Low - prev)));
            WindowAppend(tr);
            if (ChangeAtr) return RmaStep(tr);
            return _trWindow.Count == Period ? WindowSum() / Period : (double?)null;
        }

        private double? RmaStep(double? tr)
        {
            if (_rma.HasValue) _rma = _rma.Value + (tr.Value - _rma.Value) / Period;
            else if (_trWindow.Count == Period) _rma = WindowSum() / Period;
            return _rma;
        }

        public int Push(Bar bar)
        {
            Bars++;
            double? atr = Atr(bar);
            double? prevClose = _prevClose, prevUp = Up, prevDn = Dn;
            _prevClose = bar.Close;
            Flipped = false;
            if (!atr.HasValue)
            {
                Up = null; Dn = null;
                return Trend;
            }
            double src = PriceOf(bar, Source);
            double up = src - Mult * atr.Value;
            double up1 = prevUp.HasValue ? prevUp.Value : up;
            if (prevClose.HasValue && prevClose.Value > up1) up = Math.Max(up, up1);
            double dn = src + Mult * atr.Value;
            double dn1 = prevDn.HasValue ? prevDn.Value : dn;
            if (prevClose.HasValue && prevClose.Value < dn1) dn = Math.Min(dn, dn1);
            int before = Trend;
            if (Trend == -1 && bar.Close > dn1) Trend = 1;
            else if (Trend == 1 && bar.Close < up1) Trend = -1;
            Flipped = Ready && Trend != before;
            Up = up; Dn = dn;
            Ready = true;
            return Trend;
        }
    }

    /// <summary>TradingView „Directional Movement Index" (ADX a +-DI) bar po bare.</summary>
    public sealed class Dmi
    {
        public readonly int DiLen;
        public readonly int Smoothing;
        private Bar _prev;
        private readonly Rma _tr, _plusDm, _minusDm, _dx;
        public double? Plus;
        public double? Minus;
        public double? Adx;
        public int Bars;

        public Dmi(int diLength, int adxSmoothing)
        {
            DiLen = Math.Max(1, diLength);
            Smoothing = Math.Max(1, adxSmoothing);
            _tr = new Rma(DiLen);
            _plusDm = new Rma(DiLen);
            _minusDm = new Rma(DiLen);
            _dx = new Rma(Smoothing);
        }

        public bool Ready { get { return Adx.HasValue; } }
        public bool Warmed { get { return Ready && Bars >= WarmupBars; } }
        public int WarmupBars { get { return 1 + WarmupMath.RmaBars(DiLen) + WarmupMath.RmaBars(Smoothing); } }

        public double? Push(Bar bar)
        {
            Bars++;
            Bar prev = _prev;
            _prev = bar;
            if (prev == null) return null;
            double up = bar.High - prev.High;
            double down = prev.Low - bar.Low;
            double tr = Math.Max(bar.High - bar.Low, Math.Max(Math.Abs(bar.High - prev.Close), Math.Abs(bar.Low - prev.Close)));
            double? trur = _tr.Push(tr);
            double? plusDm = _plusDm.Push(up > down && up > 0 ? up : 0.0);
            double? minusDm = _minusDm.Push(down > up && down > 0 ? down : 0.0);
            if (!trur.HasValue) return null;
            if (trur.Value != 0)
            {
                // Pine: delenie nulou je `na` a `fixnan` podrzi predoslu hodnotu
                Plus = 100.0 * plusDm.Value / trur.Value;
                Minus = 100.0 * minusDm.Value / trur.Value;
            }
            if (!Plus.HasValue) return null;
            double total = Plus.Value + Minus.Value;
            double? dx = _dx.Push(Math.Abs(Plus.Value - Minus.Value) / (total != 0 ? total : 1.0));
            Adx = dx.HasValue ? 100.0 * dx.Value : (double?)null;
            return Adx;
        }

        /// <summary>`up` / `down` / `side` (ADX pod prahom alebo +DI = -DI), null kym sa nerozbehne.</summary>
        public string State(double threshold)
        {
            if (!Adx.HasValue) return null;
            if (Adx.Value < threshold || Plus.Value == Minus.Value) return "side";
            return Plus.Value > Minus.Value ? "up" : "down";
        }
    }

    /// <summary>`tradeDirection = Indicator` pre stavovy automat: aktualizuje sa kazdym barom grafu a povie,
    /// ci smie zona daneho smeru polozit order. Kym sa niektory indikator nerozbehne, neobchoduje sa.</summary>
    public sealed class DirectionGate
    {
        private const string UpColor = "#16a34a";
        private const string DownColor = "#dc2626";
        private const string SideColor = "#94a3b8";

        private sealed class IndicatorSource
        {
            public readonly string Tf;
            public readonly int Minutes;
            public readonly BoundaryAggregator Agg;

            public IndicatorSource(string name, string tf, int chartTfMinutes)
            {
                int minutes = IbsConfig.TimeframeOptionMinutes(tf);
                if (minutes < chartTfMinutes || minutes % chartTfMinutes != 0)
                    throw new ArgumentException(name + ": TF " + tf + " (" + minutes + "m) nie je nasobkom TF grafu "
                                                + chartTfMinutes + "m - indikator sa sklada z barov grafu, takze musi byt");
                Tf = tf;
                Minutes = minutes;
                Agg = new BoundaryAggregator(minutes, chartTfMinutes);
            }
        }

        private readonly IbsConfig _cfg;
        public readonly bool Enabled;
        public readonly Supertrend St;
        public readonly Dmi DmiInd;
        private readonly IndicatorSource _stSrc;
        private readonly IndicatorSource _dmiSrc;

        public DirectionGate(IbsConfig cfg, int chartTfMinutes)
        {
            _cfg = cfg;
            Enabled = cfg.tradeDirection == TradeDirectionMode.Indicator;
            if (!Enabled) return;
            if (cfg.indSupertrend)
            {
                _stSrc = new IndicatorSource("Supertrend", cfg.stTimeframe, chartTfMinutes);
                St = new Supertrend(cfg.stAtrPeriod, cfg.stMultiplier, cfg.stSource, cfg.stChangeAtr);
            }
            if (cfg.indAdx)
            {
                _dmiSrc = new IndicatorSource("ADX/DMI", cfg.adxTimeframe, chartTfMinutes);
                DmiInd = new Dmi(cfg.adxDiLength, cfg.adxSmoothing);
            }
        }

        /// <summary>Zaskrtnute indikatory s VLASTNOU predhistoriou - `WarmupBars` barov ich TF.</summary>
        public Warmup AddWarmup(Warmup warmup)
        {
            if (St != null)
                warmup.AddSeeded("Supertrend " + St.Period, St.WarmupBars, _stSrc.Minutes, SeedSt);
            if (DmiInd != null)
                warmup.AddSeeded("ADX/DMI " + DmiInd.DiLen + "/" + DmiInd.Smoothing, DmiInd.WarmupBars, _dmiSrc.Minutes, SeedDmi);
            return warmup;
        }

        private void SeedSt(IList<Bar> bars, Bar partial)
        {
            if (St.Bars != 0 || _stSrc.Agg.Started)
                throw new InvalidOperationException(_stSrc.Tf + ": seeding indikatora smie ist len pred prvym barom grafu");
            foreach (Bar b in bars) St.Push(b);
            _stSrc.Agg.Prime(partial);
        }

        private void SeedDmi(IList<Bar> bars, Bar partial)
        {
            if (DmiInd.Bars != 0 || _dmiSrc.Agg.Started)
                throw new InvalidOperationException(_dmiSrc.Tf + ": seeding indikatora smie ist len pred prvym barom grafu");
            foreach (Bar b in bars) DmiInd.Push(b);
            _dmiSrc.Agg.Prime(partial);
        }

        /// <summary>Bar grafu; vrati kresby indikatorov, ktorych HTF bar sa nim uzavrel.</summary>
        public List<DrawCommand> OnBar(Bar bar)
        {
            List<DrawCommand> list = new List<DrawCommand>();
            if (!Enabled) return list;
            if (St != null)
            {
                foreach (Bar htf in _stSrc.Agg.Push(bar))
                {
                    St.Push(htf);
                    if (St.Ready) list.AddRange(DrawSt(htf));
                }
            }
            if (DmiInd != null)
            {
                foreach (Bar htf in _dmiSrc.Agg.Push(bar))
                {
                    DmiInd.Push(htf);
                    if (DmiInd.Ready && _cfg.adxShowState) list.Add(DrawDmi(htf));
                }
            }
            return list;
        }

        /// <summary>Stavy (Supertrend, ADX); `false` = este sa nerozbehli. Nezaskrtnuty indikator ma null.</summary>
        private bool States(out string st, out string dmi)
        {
            st = null; dmi = null;
            if (St != null)
            {
                if (!St.Warmed) return false;
                st = St.Trend == 1 ? "up" : "down";
            }
            if (DmiInd != null)
            {
                if (!DmiInd.Warmed) return false;
                dmi = DmiInd.State(_cfg.adxThreshold);
                if (dmi == null) return false;
            }
            return true;
        }

        private IndicatorAction? Action()
        {
            string st, dmi;
            if (!States(out st, out dmi)) return null;
            if (st == "up" && dmi == null) return _cfg.ruleStUp;
            if (st == "down" && dmi == null) return _cfg.ruleStDown;
            if (st == null && dmi == "up") return _cfg.ruleAdxUp;
            if (st == null && dmi == "down") return _cfg.ruleAdxDown;
            if (st == null && dmi == "side") return _cfg.ruleAdxSide;
            if (st == "up" && dmi == "up") return _cfg.ruleStUpAdxUp;
            if (st == "up" && dmi == "side") return _cfg.ruleStUpAdxSide;
            if (st == "up" && dmi == "down") return _cfg.ruleStUpAdxDown;
            if (st == "down" && dmi == "up") return _cfg.ruleStDownAdxUp;
            if (st == "down" && dmi == "side") return _cfg.ruleStDownAdxSide;
            if (st == "down" && dmi == "down") return _cfg.ruleStDownAdxDown;
            throw new InvalidOperationException("kombinacia stavov indikatorov bez pravidla");
        }

        public bool Allowed(Direction direction)
        {
            if (!Enabled) return true;
            IndicatorAction? action = Action();
            return action.HasValue && IbsConfig.Allows(action.Value, direction);
        }

        private static string StateText(string state)
        {
            if (state == "up") return "HORE";
            if (state == "down") return "DOLE";
            if (state == "side") return "STRANA";
            return "SA ROZBIEHA";
        }

        /// <summary>Stav do SKIP stitku, napr. `ST60 HORE + ADX60 STRANA`.</summary>
        public string Describe()
        {
            string st, dmi;
            if (!States(out st, out dmi)) { st = null; dmi = null; }
            List<string> parts = new List<string>();
            if (St != null) parts.Add("ST" + _cfg.stTimeframe + " " + StateText(st));
            if (DmiInd != null) parts.Add("ADX" + _cfg.adxTimeframe + " " + StateText(dmi));
            return string.Join(" + ", parts.ToArray());
        }

        public string BlockReason(Direction direction)
        {
            if (Allowed(direction)) return null;
            IndicatorAction? action = Action();
            string text = "CAKA";
            if (action.HasValue)
            {
                switch (action.Value)
                {
                    case IndicatorAction.Both: text = "OBA SMERY"; break;
                    case IndicatorAction.LongOnly: text = "LEN LONG"; break;
                    case IndicatorAction.ShortOnly: text = "LEN SHORT"; break;
                    default: text = "NEOBCHODOVAT"; break;
                }
            }
            return Describe() + ": " + text;
        }

        // ------------------------------------------------------------------ //

        /// <summary>Ciara plati od uzavretia HTF baru po uzavretie dalsieho - tam ju brana pouziva.</summary>
        private List<DrawCommand> DrawSt(Bar htf)
        {
            long ms = _stSrc.Agg.Ms;
            bool up = St.Trend == 1;
            string color = up ? UpColor : DownColor;
            long start = htf.Time + ms, end = htf.Time + 2 * ms;
            double lineY = St.Line.Value;

            List<DrawCommand> draws = new List<DrawCommand>();
            DrawLine line = new DrawLine(IbsKinds.StLine, start, lineY, end, lineY, color);
            line.Width = 2;
            line.ObjId = "st." + htf.Time;
            line.Text = "Supertrend " + _cfg.stTimeframe + " " + (up ? "hore" : "dole");
            draws.Add(line);

            if (_cfg.stHighlighting)
            {
                // Pine `fill(ohlc4, ciara)`; box nema sikme hrany, tak ide po ohlc4 HTF baru
                double mid = (htf.Open + htf.High + htf.Low + htf.Close) / 4.0;
                DrawBox fill = new DrawBox(IbsKinds.StFill, start, Math.Max(mid, lineY), end, Math.Min(mid, lineY),
                                           Palette.WithAlpha(color, 100));
                fill.FillColor = Palette.WithAlpha(color, 85);
                fill.BorderWidth = 0;
                fill.ObjId = "stf." + htf.Time;
                draws.Add(fill);
            }
            if (St.Flipped && _cfg.stShowSignals)
            {
                DrawLabel label = new DrawLabel(IbsKinds.StSignal, start, lineY, up ? "Buy" : "Sell", "#ffffff");
                label.Style = up ? LabelStyles.Up : LabelStyles.Down;
                label.Above = !up;
                label.BgColor = color;
                label.ObjId = "sts." + htf.Time;
                draws.Add(label);
            }
            return draws;
        }

        private DrawCommand DrawDmi(Bar htf)
        {
            long ms = _dmiSrc.Agg.Ms;
            string state = DmiInd.State(_cfg.adxThreshold);
            string color = state == "up" ? UpColor : (state == "down" ? DownColor : SideColor);
            DrawBg bg = new DrawBg(IbsKinds.AdxState, htf.Time + ms, htf.Time + 2 * ms, Palette.WithAlpha(color, 90));
            bg.ObjId = "adx." + htf.Time;
            bg.Text = string.Format(CultureInfo.InvariantCulture, "ADX {0} {1}: ADX {2}, +DI {3}, −DI {4}",
                                    _cfg.adxTimeframe, StateText(state).ToLowerInvariant(),
                                    PyFormat.Fixed(DmiInd.Adx.Value, 1), PyFormat.Fixed(DmiInd.Plus.Value, 1),
                                    PyFormat.Fixed(DmiInd.Minus.Value, 1));
            return bg;
        }
    }

    /// <summary>Formatovanie cisel ako Python f-string `{x:.Nf}`: spravne zaokruhlenie PRESNEJ binarnej hodnoty
    /// (half-even na presnej hodnote). .NET Framework `ToString("F1")` zaokruhluje z 15 cifier, co sa na hrane lisi.</summary>
    public static class PyFormat
    {
        public static string Fixed(double value, int decimals)
        {
            if (double.IsNaN(value)) return "nan";
            if (double.IsInfinity(value)) return value > 0 ? "inf" : "-inf";
            // decimal drzi 28 cifier; double -> decimal cez G17 je pre bezne ceny presnejsie nez (decimal)x
            decimal d;
            if (!decimal.TryParse(value.ToString("G17", CultureInfo.InvariantCulture),
                                  NumberStyles.Float, CultureInfo.InvariantCulture, out d))
                return value.ToString("F" + decimals, CultureInfo.InvariantCulture);
            d = Math.Round(d, decimals, MidpointRounding.ToEven);
            return d.ToString("F" + decimals, CultureInfo.InvariantCulture);
        }
    }
}
