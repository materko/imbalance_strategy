// `MtkZoneEngine` - MTK ZONE s jadrom v C#. Zrkadlo `tradebot/strategies/mtkzone/engine.py`; s Python enginom
// sa porovnava bar po bare, na rovnost (ordery aj kresby).
//
// 1. Zony z vyssich TF (`zoneTf1`, volitelne `zoneTf2`) - bary grafu sa skladaju `TimeframeAggregator`-om (IBS Entry
//    Zone). Na uzavretej sviecke TF zon: klasicka SD / vrchol volume profilu (odchod na [1], zakladna [2..]),
//    narast objemu (sviecka [0] s objemom >= volSpike x priemer -> zaciatok pohybu -> ticha zakladna),
//    volitelne POC / PEAK; zona vznikne pri >= minConf potvrdeniach a kvalite >= minScore.
// 2. Prvy dotyk zonu zareze; dalej ju sleduju modely IBS (stavy 0-5 ako `ibs/statemachine.py`) a pin bar.
// 3. Vstup bez pozicie: pin bar (market) -> IBS (limit) -> limit na blizsiu hranu zony; filtre VWAP, seansa NY,
//    odstup, vek a kvalita zony, max. riziko a vzdialenost. Kazda zona da najviac jeden obchod.
// Engine je CISTY: ziadne I/O, ziadny globalny stav.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;
using TradeBot.Strategies.IbsEntryNet;

namespace TradeBot.Strategies.MtkZoneNet
{
    internal sealed class HtfSeries
    {
        public readonly int Minutes;
        private readonly TimeframeAggregator _agg;
        private readonly int _atrLen, _volLen, _keep;
        public readonly List<Bar> Bars = new List<Bar>();
        public readonly List<double?> AtrS = new List<double?>();
        public readonly List<double?> VsmaS = new List<double?>();
        public int Count;
        private double? _atr;
        private readonly List<double> _trs = new List<double>();
        private readonly List<double> _vols = new List<double>();

        public HtfSeries(int minutes, int atrLen, int volLen, int keep)
        {
            Minutes = minutes;
            _agg = new TimeframeAggregator(minutes);
            _atrLen = atrLen; _volLen = volLen; _keep = keep;
        }

        public Bar Push(Bar chartBar)
        {
            Bar closed = _agg.Push(chartBar);
            if (closed == null) return null;
            Bar prev = Bars.Count > 0 ? Bars[Bars.Count - 1] : null;
            double tr = prev == null ? closed.High - closed.Low
                : Math.Max(closed.High - closed.Low, Math.Max(Math.Abs(closed.High - prev.Close), Math.Abs(closed.Low - prev.Close)));
            if (!_atr.HasValue)
            {
                _trs.Add(tr);
                if (_trs.Count >= _atrLen)
                {
                    double sum = 0.0;
                    for (int i = _trs.Count - _atrLen; i < _trs.Count; i++) sum += _trs[i];
                    _atr = sum / _atrLen;
                }
            }
            else
                _atr = (_atr.Value * (_atrLen - 1) + tr) / _atrLen;
            _vols.Add(closed.Volume);
            if (_vols.Count > _volLen) _vols.RemoveAt(0);
            Bars.Add(closed);
            AtrS.Add(_atr);
            double? vs = null;
            if (_vols.Count >= _volLen)
            {
                double s = 0.0;
                foreach (double v in _vols) s += v;
                vs = s / _volLen;
            }
            VsmaS.Add(vs);
            if (Bars.Count > _keep) { Bars.RemoveAt(0); AtrS.RemoveAt(0); VsmaS.RemoveAt(0); }
            Count += 1;
            return closed;
        }

        public bool Has(int k) { return Bars.Count > k; }
        public Bar B(int k) { return Bars[Bars.Count - 1 - k]; }
        public double? A(int k) { return AtrS[AtrS.Count - 1 - k]; }
        public double? V(int k) { return VsmaS[VsmaS.Count - 1 - k]; }
    }

    internal sealed class VProfile
    {
        public double[] Tot;
        public double Total;
        public double Lo;
        public double Step;
        public int Poc;
    }

    internal sealed class Cand
    {
        public double Top, Bot, Score, Pk, Rv;
        public int Dir;
        public string Src;
        public long LeftMs;
        public Cand(double top, double bot, int dir, double score, double pk, double rv, string src, long leftMs)
        {
            Top = top; Bot = bot; Dir = dir; Score = score; Pk = pk; Rv = rv; Src = src; LeftMs = leftMs;
        }
    }

    internal sealed class MZone
    {
        public int Uid;
        public double Top, Bot, Score, Pk, Rv;
        public int Dir, Tf, Born;
        public string Src;
        public long LeftMs;
        public bool Active = true;
        public int? TouchIdx;
        public bool Used, Dead;
        public int Ist, IstIdx;
        public double ImbOpen, ImbBt, ImbBb;
        public long ImbMs;
        public bool PinNow;
        public string BoxId = "", IboxId = "";
        public double Mid { get { return (Top + Bot) / 2; } }
        public bool IsVol { get { return Src.Contains("OBJEM"); } }
    }

    internal sealed class AnchoredVwap
    {
        private readonly string _anchor;
        private readonly TimeZoneInfo _zone;
        private long? _key;
        private double _pv, _vol;
        public double? Value;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        public AnchoredVwap(string anchor, TimeZoneInfo zone) { _anchor = anchor; _zone = zone; }

        private long Key(long tMs)
        {
            DateTime local = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(tMs), _zone);
            if (_anchor == "ny") return local.AddMinutes(-570).Date.Ticks;
            DateTime cme = local.AddHours(6).Date;           // obchodny den CME zacina 18:00 New York
            if (_anchor == "week")
            {
                int wd = ((int)cme.DayOfWeek + 6) % 7;       // pondelok = 0 (Python weekday)
                return cme.AddDays(-wd).Ticks;
            }
            if (_anchor == "month") return cme.Year * 100L + cme.Month;
            return cme.Ticks;
        }

        public void Push(Bar bar)
        {
            long k = Key(bar.Time);
            if (!_key.HasValue || k != _key.Value) { _key = k; _pv = 0.0; _vol = 0.0; }
            double v = bar.Volume;
            _pv += (bar.High + bar.Low + bar.Close) / 3 * v;
            _vol += v;
            if (_vol > 0) Value = _pv / _vol;
        }
    }

    [TradeBotEngine("mtkzonenet", "MTK ZONE (C#)")]
    public sealed class MtkZoneEngine : IEngine, IConfigured
    {
        private const string Ny = "America/New_York";
        private const string DemColor = "#1de9b6", SupColor = "#ff5252", VolColor = "#000000";
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        private static readonly string[] Kinds = { "LI", "SI", "L", "S" };

        private readonly MtkZoneConfig _cfg;
        public object Settings { get { return _cfg; } }
        private readonly InstrumentSpec _inst;
        private readonly int _tf;
        private readonly TimeZoneInfo _zone;
        private readonly List<HtfSeries> _slots = new List<HtfSeries>();
        private readonly Warmup _warmup;
        private readonly int _requiredHistory;
        public readonly BarHistory History;
        private readonly AnchoredVwap _vwap;
        private readonly List<MZone> _zones = new List<MZone>();
        private int _uid;
        // cakajuce limity: druh (L / S / LI / SI) -> order; poradie vlozenia ako Python dict
        private readonly List<string> _pendOrder = new List<string>();
        private readonly Dictionary<string, string> _pendId = new Dictionary<string, string>();
        private readonly Dictionary<string, double> _pendEntry = new Dictionary<string, double>();
        private readonly Dictionary<string, double> _pendSl = new Dictionary<string, double>();
        private readonly Dictionary<string, MZone> _pendZone = new Dictionary<string, MZone>();
        private bool _wasInPos;
        private int? _lastExit;

        public MtkZoneEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(MtkZoneConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public MtkZoneEngine(MtkZoneConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            _inst = inst;
            _tf = Math.Max(1, chartTfMinutes);
            _zone = TimeZones.Get(Ny);
            int keep = cfg.lookback + cfg.baseMax + 12;
            bool[] use = { cfg.useZ1, cfg.useZ2 };
            int[] tfs = { cfg.zoneTf1, cfg.zoneTf2 };
            for (int i = 0; i < 2; i++)
            {
                if (!use[i]) continue;
                int m = Math.Max(tfs[i], _tf);
                bool dup = false;
                foreach (HtfSeries s in _slots) if (s.Minutes == tfs[i]) dup = true;
                if (!dup) _slots.Add(new HtfSeries(m, cfg.atrLen, cfg.volLen, keep));
            }
            _warmup = new Warmup(_tf);
            foreach (HtfSeries s in _slots)
            {
                int n = s.Minutes == _tf ? keep : (keep + 1) * (int)Math.Ceiling((double)s.Minutes / _tf);
                _warmup.Add("zóny " + s.Minutes + "m (" + cfg.lookback + " sviečok)", n);
            }
            _requiredHistory = _warmup.ChartBars;
            History = new BarHistory(Math.Max(64, Math.Max(cfg.imbLookback + 4, cfg.ibsSlLookback + 2)), cfg.atrLen);
            _vwap = new AnchoredVwap(cfg.vwapAnchor, _zone);
        }

        public InstrumentSpec Inst { get { return _inst; } }
        public int ChartTfMinutes { get { return _tf; } }
        public int RequiredHistory { get { return _requiredHistory; } }
        public Warmup Warmup { get { return _warmup; } }
        public IHtfFeeder CreateHtfFeeder() { return null; }
        public List<DrawCommand> FinalDrawings(Bar bar) { return new List<DrawCommand>(); }

        public Dictionary<string, double> Stats()
        {
            Dictionary<string, double> s = new Dictionary<string, double>();
            s["leverage"] = _cfg.leverage;
            return s;
        }

        private static string F1(double v) { return v.ToString("0.0", CultureInfo.InvariantCulture); }

        // ------------------------------------------------------------------ //
        // volume profil
        // ------------------------------------------------------------------ //

        private static VProfile Profile(List<Bar> bars, int rows)
        {
            if (bars.Count == 0) return null;
            double hi = bars[0].High, lo = bars[0].Low;
            foreach (Bar b in bars) { hi = Math.Max(hi, b.High); lo = Math.Min(lo, b.Low); }
            double step = (hi - lo) / rows;
            if (step <= 0) return null;
            double[] tot = new double[rows];
            foreach (Bar b in bars)
            {
                double rng = b.High - b.Low;
                double v = b.Volume;
                if (rng <= 0)
                {
                    int r0 = Math.Min(rows - 1, Math.Max(0, (int)Math.Floor((b.Low - lo) / step)));
                    tot[r0] += v;
                    continue;
                }
                int ra = Math.Max(0, (int)Math.Floor((b.Low - lo) / step));
                int rb = Math.Min(rows - 1, (int)Math.Floor((b.High - lo) / step));
                for (int r = ra; r <= rb; r++)
                {
                    double rl = lo + r * step;
                    double sh = Math.Max(0.0, Math.Min(b.High, rl + step) - Math.Max(b.Low, rl)) / rng;
                    if (sh > 0) tot[r] += v * sh;
                }
            }
            double total = 0.0;
            foreach (double t in tot) total += t;
            int poc = 0;
            for (int r = 1; r < rows; r++) if (tot[r] > tot[poc]) poc = r;
            VProfile p = new VProfile();
            p.Tot = tot; p.Total = total; p.Lo = lo; p.Step = step; p.Poc = poc;
            return p;
        }

        private static bool[] Peaks(VProfile p, int rows, double peakMin)
        {
            bool[] o = new bool[rows];
            for (int r = 0; r < rows; r++)
            {
                double t = p.Tot[r];
                double pct = p.Total > 0 ? 100 * t / p.Total : 0.0;
                if (r == p.Poc || (pct >= peakMin && (r == 0 || t >= p.Tot[r - 1]) && (r == rows - 1 || t > p.Tot[r + 1])))
                    o[r] = true;
            }
            return o;
        }

        private static double PeakIn(VProfile p, int rows, double peakMin, double top, double bot)
        {
            if (p == null || p.Total <= 0) return 0.0;
            double pk = 0.0;
            bool[] pks = Peaks(p, rows, peakMin);
            for (int r = 0; r < rows; r++)
            {
                double mid = p.Lo + (r + 0.5) * p.Step;
                if (pks[r] && bot - 0.5 * p.Step <= mid && mid <= top + 0.5 * p.Step) pk = Math.Max(pk, p.Tot[r] / p.Total);
            }
            return pk;
        }

        // ------------------------------------------------------------------ //
        // zony
        // ------------------------------------------------------------------ //

        private static bool Ok(double? x) { return x.HasValue && x.Value != 0.0; }

        private List<Cand> Detect(HtfSeries s)
        {
            MtkZoneConfig cfg = _cfg;
            List<Cand> o = new List<Cand>();
            int rows = cfg.rows;
            double pmin = cfg.peakMin;
            VProfile prof = null;
            bool profDone = false;
            Func<VProfile> profile = delegate
            {
                if (!profDone && s.Has(0))
                {
                    int n = Math.Min(cfg.lookback, s.Bars.Count);
                    List<Bar> bs = new List<Bar>();
                    for (int k = 0; k < n; k++) bs.Add(s.B(k));
                    prof = Profile(bs, rows);
                    profDone = true;
                }
                return prof;
            };

            // --- klasicka SD / vrchol profilu: odchod na [1], zakladna [2..] ---
            if ((cfg.useClassic || cfg.usePeak) && s.Has(3))
            {
                double? aN = s.A(1);
                Bar d1 = s.B(1);
                double body = Math.Abs(d1.Close - d1.Open);
                if (Ok(aN) && aN.Value > 0 && body >= cfg.impMult * aN.Value)
                {
                    double a = aN.Value;
                    int dr = d1.Close > d1.Open ? 1 : -1;
                    int k = 0;
                    double top = 0, bot = 0;
                    for (int b = 2; b < 2 + cfg.baseMax; b++)
                    {
                        if (!s.Has(b)) break;
                        Bar x = s.B(b);
                        double ab = Ok(s.A(b)) ? s.A(b).Value : a;
                        if (Math.Abs(x.Close - x.Open) <= cfg.baseBodyMax * ab)
                        {
                            if (dr == 1)
                            {
                                top = k == 0 ? Math.Max(x.Open, x.Close) : Math.Max(top, Math.Max(x.Open, x.Close));
                                bot = k == 0 ? x.Low : Math.Min(bot, x.Low);
                            }
                            else
                            {
                                top = k == 0 ? x.High : Math.Max(top, x.High);
                                bot = k == 0 ? Math.Min(x.Open, x.Close) : Math.Min(bot, Math.Min(x.Open, x.Close));
                            }
                            k += 1;
                        }
                        else break;
                    }
                    if (k > 0 && top > bot && (dr == 1 ? d1.Close > top : d1.Close < bot))
                    {
                        double pk = PeakIn(profile(), rows, pmin, top, bot);
                        double? v2 = s.Has(2) ? s.V(2) : null;
                        double rv = Ok(v2) ? d1.Volume / v2.Value : 1.0;
                        bool peakOk = cfg.usePeak && pk > 0;
                        int conf = 1 + (peakOk ? 1 : 0) + (cfg.useVolSurge && rv >= cfg.volSpike ? 1 : 0);
                        if ((cfg.useClassic || peakOk) && conf >= cfg.minConf)
                        {
                            double bs = Math.Min(1.0, body / a / (2 * cfg.impMult));
                            double pks = peakOk ? Math.Min(1.0, pk / (2 * pmin / 100)) : 0.0;
                            double score = 35 * bs + 30 * Math.Min(1.0, rv / 2.0) + 35 * Math.Max(pks, cfg.useClassic ? bs : 0.0);
                            if (score >= cfg.minScore)
                                o.Add(new Cand(top, bot, dr, score, peakOk ? pk : 0.0, rv, peakOk ? "PROFIL" : "SD", s.B(1 + k).Time));
                        }
                    }
                }
            }

            // --- narast objemu: sviecka [0] s dobrym objemom -> zaciatok pohybu -> ticha zakladna ---
            if (cfg.useVolSurge && s.Has(2))
            {
                double? a0N = s.A(0), v1N = s.V(1);
                Bar b0 = s.B(0);
                double body0 = Math.Abs(b0.Close - b0.Open);
                if (Ok(a0N) && a0N.Value > 0 && Ok(v1N) && b0.Volume >= cfg.volSpike * v1N.Value && body0 >= cfg.impMultVol * a0N.Value)
                {
                    double a0 = a0N.Value, v1 = v1N.Value;
                    int dr = b0.Close > b0.Open ? 1 : -1;
                    int j = 1;
                    while (j <= 3 && s.Has(j))
                    {
                        Bar x = s.B(j);
                        bool same = dr == 1 ? x.Close > x.Open : x.Close < x.Open;
                        double aj = Ok(s.A(j)) ? s.A(j).Value : a0;
                        if (same && Math.Abs(x.Close - x.Open) > cfg.baseBodyMax * aj) j += 1;
                        else break;
                    }
                    int k = 0;
                    double top = 0, bot = 0;
                    for (int b = j; b < j + cfg.baseMax; b++)
                    {
                        if (!s.Has(b)) break;
                        Bar x = s.B(b);
                        double ab = Ok(s.A(b)) ? s.A(b).Value : a0;
                        bool small = Math.Abs(x.Close - x.Open) <= cfg.baseBodyMax * ab;
                        double? vb = s.Has(b + 1) ? s.V(b + 1) : null;
                        bool quiet = Ok(vb) && x.Volume <= vb.Value;
                        if (small || quiet || (k == 0 && b == j))
                        {
                            if (dr == 1)
                            {
                                top = k == 0 ? Math.Max(x.Open, x.Close) : Math.Max(top, Math.Max(x.Open, x.Close));
                                bot = k == 0 ? x.Low : Math.Min(bot, x.Low);
                            }
                            else
                            {
                                top = k == 0 ? x.High : Math.Max(top, x.High);
                                bot = k == 0 ? Math.Min(x.Open, x.Close) : Math.Min(bot, Math.Min(x.Open, x.Close));
                            }
                            k += 1;
                            if (!(small || quiet)) break;
                        }
                        else break;
                    }
                    if (k > 0 && top > bot && (dr == 1 ? b0.Close > top : b0.Close < bot))
                    {
                        double rv = b0.Volume / v1;
                        double pk = cfg.usePeak ? PeakIn(profile(), rows, pmin, top, bot) : 0.0;
                        double score = 35 * Math.Min(1.0, body0 / a0 / (2 * cfg.impMultVol)) + 30 * Math.Min(1.0, rv / 2.0)
                                       + 35 * Math.Min(1.0, rv / (2 * cfg.volSpike));
                        int conf = 1 + (pk > 0 ? 1 : 0) + (cfg.useClassic && body0 >= cfg.impMult * a0 ? 1 : 0);
                        if (score >= cfg.minScore && conf >= cfg.minConf)
                            o.Add(new Cand(top, bot, dr, score, pk, rv, pk > 0 ? "OBJEM+PROFIL" : "OBJEM", s.B(j + k - 1).Time));
                    }
                }
            }

            // --- POC a najvacsi dalsi PEAK ---
            if (cfg.usePocZone && cfg.minConf <= 1 && s.Count % cfg.pocEvery == 0 && s.Count > cfg.lookback)
            {
                VProfile p = profile();
                if (p != null && p.Total > 0)
                {
                    bool[] pks = Peaks(p, rows, pmin);
                    int best = -1;
                    for (int r = 0; r < rows; r++)
                        if (pks[r] && r != p.Poc && Math.Abs(r - p.Poc) > 1 && (best < 0 || p.Tot[r] > p.Tot[best])) best = r;
                    int[] rs = { p.Poc, best };
                    string[] names = { "POC", "PEAK" };
                    for (int i = 0; i < 2; i++)
                    {
                        int r = rs[i];
                        if (r < 0) continue;
                        double bot = p.Lo + r * p.Step;
                        double top = bot + p.Step;
                        double pct = p.Tot[r] / p.Total;
                        o.Add(new Cand(top, bot, 0, Math.Min(100.0, 100.0 * pct / (4 * pmin / 100)), pct, 0.0, names[i], s.B(0).Time));
                    }
                }
            }
            return o;
        }

        private static string Text(MZone z)
        {
            string t = (z.Dir == 1 ? "DOPYT" : "PONUKA") + " " + ((int)z.Score).ToString(CultureInfo.InvariantCulture) + " · "
                       + z.Tf.ToString(CultureInfo.InvariantCulture) + "m " + z.Src;
            if (z.Pk > 0) t += " · PEAK " + F1(Math.Floor(1000 * z.Pk) / 10) + "% VOL";
            if (z.Rv > 0) t += " · OBJEM " + F1(Math.Floor(10 * z.Rv) / 10) + "×";
            return t + (z.Active ? "" : " · otestovaná");
        }

        private void Remove(MZone z, EngineOutput o)
        {
            _zones.Remove(z);
            if (z.BoxId.Length > 0 && _cfg.showZones) o.Drawings.Add(new DrawDelete(z.BoxId));
        }

        private void AddZone(Cand c, int tf, Bar bar, int idx, EngineOutput o)
        {
            MtkZoneConfig cfg = _cfg;
            int dr = c.Dir;
            if (dr == 0)
            {
                if (c.Top < bar.Close) dr = 1;
                else if (c.Bot > bar.Close) dr = -1;
                else return;
                if (c.Score < cfg.minScore) return;
            }
            bool isVol = c.Src.Contains("OBJEM");
            List<MZone> over = new List<MZone>();
            foreach (MZone z in _zones)
                if (z.Active && z.Dir == dr && z.Tf == tf && c.Top > z.Bot && c.Bot < z.Top) over.Add(z);
            foreach (MZone oz in over)
            {
                if ((oz.Score >= c.Score && !(isVol && !oz.IsVol)) || (oz.IsVol && !isVol)) return;
                Remove(oz, o);
            }
            List<MZone> act = new List<MZone>();
            foreach (MZone z in _zones) if (z.Active && z.Dir == dr && z.Tf == tf) act.Add(z);
            if (act.Count >= cfg.maxZones)
            {
                MZone far = act[0];
                for (int i = 1; i < act.Count; i++)
                    if (Math.Abs(act[i].Mid - bar.Close) > Math.Abs(far.Mid - bar.Close)) far = act[i];
                Remove(far, o);
            }
            _uid += 1;
            MZone nz = new MZone();
            nz.Uid = _uid; nz.Top = c.Top; nz.Bot = c.Bot; nz.Dir = dr; nz.Score = c.Score; nz.Pk = c.Pk; nz.Rv = c.Rv;
            nz.Src = c.Src; nz.Tf = tf; nz.LeftMs = c.LeftMs; nz.Born = idx - 1;
            nz.BoxId = "mz." + nz.Uid.ToString(CultureInfo.InvariantCulture);
            _zones.Add(nz);
            if (cfg.showZones)
            {
                string col = isVol ? VolColor : (dr == 1 ? DemColor : SupColor);
                DrawBox box = new DrawBox(MtkZoneKinds.Zone, Math.Min(c.LeftMs, bar.Time), c.Top, bar.Time, c.Bot, col);
                box.FillColor = col + "40";
                box.ExtendRight = true;
                box.ObjId = nz.BoxId;
                box.ZoneUid = nz.Uid;
                box.Text = Text(nz);
                o.Drawings.Add(box);
            }
        }

        // ------------------------------------------------------------------ //
        // IBS gap a modely
        // ------------------------------------------------------------------ //

        private sealed class ImbHit
        {
            public double D, Open, Bt, Bb, Gt, Gb;
            public long GlMs;
        }

        private ImbHit FindImb(MZone z, int idx, double atr)
        {
            MtkZoneConfig cfg = _cfg;
            BarHistory h = History;
            double minImb = cfg.minImbSize.Resolve(_inst, h[0].Close, atr);
            double maxD = cfg.imbMaxDistTicks * _inst.TickSize;
            ImbHit best = null;
            for (int lb = 0; lb < cfg.imbLookback; lb++)
            {
                if (!h.Has(lb + 2) || idx - (lb + 2) < z.Born) continue;
                Bar near = h[lb], mid = h[lb + 1], far = h[lb + 2];
                bool bull = near.Low > far.High && mid.Close > far.High && near.Low - far.High >= minImb;
                bool bear = near.High < far.Low && mid.Close < far.Low && far.Low - near.High >= minImb;
                double? d = null;
                bool through = mid.High >= z.Top && mid.Low <= z.Bot;
                if (z.Dir == 1 && bear && (mid.Open > z.Top || through)) d = Math.Max(0.0, mid.Low - z.Top);
                if (z.Dir == -1 && bull && (mid.Open < z.Bot || through)) d = Math.Max(0.0, z.Bot - mid.High);
                if (d.HasValue && d.Value <= maxD && (best == null || d.Value < best.D))
                {
                    best = new ImbHit();
                    best.D = d.Value; best.Open = mid.Open; best.Bt = Math.Max(mid.Open, mid.Close);
                    best.Bb = Math.Min(mid.Open, mid.Close); best.GlMs = far.Time;
                    best.Gt = z.Dir == 1 ? far.Low : near.Low;
                    best.Gb = z.Dir == 1 ? near.High : far.High;
                }
            }
            return best;
        }

        private void IbsFail(MZone z, Bar bar, EngineOutput o)
        {
            z.Dead = true;
            if (_cfg.showIbsDraw && z.IboxId.Length > 0)
            {
                o.Drawings.Add(new DrawUpdate(z.IboxId, "x2_ms", bar.Time));
                o.Drawings.Add(new DrawUpdate(z.IboxId, "fill_color", "#94a3b826"));
            }
        }

        private void Models(Bar bar, int idx, double atr, EngineOutput o)
        {
            MtkZoneConfig cfg = _cfg;
            double tick = _inst.TickSize;
            bool draw = cfg.showIbsDraw;
            foreach (MZone z in _zones)
            {
                z.PinNow = false;
                if (z.Active || z.Used || z.Dead || !z.TouchIdx.HasValue) continue;
                bool isLong = z.Dir == 1;
                int age = idx - z.TouchIdx.Value;
                bool inZone = bar.High >= z.Bot && bar.Low <= z.Top;
                bool broken = isLong ? bar.Low < z.Bot : bar.High > z.Top;
                if (cfg.usePin && z.Ist == 0 && inZone)
                {
                    double rng = bar.High - bar.Low;
                    double btop = Math.Max(bar.Open, bar.Close), bbot = Math.Min(bar.Open, bar.Close);
                    double blen = btop - bbot;
                    bool wickOk = isLong ? (blen <= 0 || bbot - bar.Low >= blen * cfg.pbRatio)
                                         : (blen <= 0 || bar.High - btop >= blen * cfg.pbRatio);
                    bool posOk = isLong ? (bar.High - btop <= rng * cfg.pbBodyPos / 100)
                                        : (bbot - bar.Low <= rng * cfg.pbBodyPos / 100);
                    double minRng = cfg.pbMinRange.Resolve(_inst, bar.Close, atr);
                    z.PinNow = rng >= minRng && wickOk && posOk;
                }
                if (cfg.useIBS)
                {
                    if (z.Ist == 0)
                    {
                        ImbHit hit = FindImb(z, idx, atr);
                        if (hit != null)
                        {
                            z.ImbOpen = hit.Open; z.ImbBt = hit.Bt; z.ImbBb = hit.Bb;
                            z.Ist = 1; z.IstIdx = idx; z.ImbMs = History[1].Time;
                            z.IboxId = "mz.i." + z.Uid.ToString(CultureInfo.InvariantCulture);
                            if (draw)
                            {
                                DrawBox box = new DrawBox(MtkZoneKinds.Ifvg, hit.GlMs, Math.Max(hit.Gt, hit.Gb), bar.Time,
                                                          Math.Min(hit.Gt, hit.Gb), "#c026d3");
                                box.FillColor = "#f472b64d";
                                box.ObjId = z.IboxId;
                                box.ZoneUid = z.Uid;
                                box.Text = "iFVG";
                                o.Drawings.Add(box);
                            }
                        }
                    }
                    else if (z.Ist == 1)
                    {
                        if (idx - z.IstIdx > cfg.st1Max) IbsFail(z, bar, o);
                        else if (isLong ? (bar.High > z.Top && bar.Low <= z.Top) : (bar.Low < z.Bot && bar.High >= z.Bot))
                        {
                            z.Ist = 2; z.IstIdx = idx;
                        }
                    }
                    else if (z.Ist == 2)
                    {
                        if (idx - z.IstIdx > cfg.st2Max) IbsFail(z, bar, o);
                        else if (isLong ? bar.Close > z.ImbBt + cfg.st2ConfTicks * tick : bar.Close < z.ImbBb - cfg.st2ConfTicks * tick)
                        {
                            z.Ist = 3; z.IstIdx = idx;
                            if (draw)
                            {
                                double cb = isLong ? z.ImbBt : z.ImbBb;
                                DrawLine line = new DrawLine(MtkZoneKinds.Cb, z.ImbMs, cb, bar.Time, cb, "#94a3b8");
                                line.ObjId = "mz.cb." + z.Uid.ToString(CultureInfo.InvariantCulture);
                                line.ZoneUid = z.Uid;
                                line.Text = "CB";
                                o.Drawings.Add(line);
                                o.Drawings.Add(new DrawUpdate(z.IboxId, "x2_ms", bar.Time));
                            }
                        }
                    }
                    else if (z.Ist == 3)
                    {
                        if (idx - z.IstIdx > cfg.st3Max) IbsFail(z, bar, o);
                        else if (isLong ? bar.Low <= z.ImbOpen : bar.High >= z.ImbOpen)
                        {
                            z.Ist = 4; z.IstIdx = idx;
                            if (draw)
                            {
                                DrawLabel lab = new DrawLabel(MtkZoneKinds.Retest, bar.Time, z.ImbOpen, "●", "#2962ff");
                                lab.ObjId = "mz.r." + z.Uid.ToString(CultureInfo.InvariantCulture);
                                lab.ZoneUid = z.Uid;
                                o.Drawings.Add(lab);
                                o.Drawings.Add(new DrawUpdate(z.IboxId, "x2_ms", bar.Time));
                            }
                        }
                    }
                    else if (z.Ist == 4 && idx - z.IstIdx >= cfg.st5Max) z.Dead = true;
                }
                if (z.Ist == 0 && !z.PinNow && (broken || age > cfg.modelBars)) z.Dead = true;
            }
        }

        // ------------------------------------------------------------------ //
        // vstupy
        // ------------------------------------------------------------------ //

        private TradePlan Plan(bool isLong, double entry, double sl)
        {
            MtkZoneConfig cfg = _cfg;
            double risk = isLong ? entry - sl : sl - entry;
            if (risk < _inst.TickSize * 2) return null;
            if (cfg.maxRiskTicks > 0 && risk > cfg.maxRiskTicks * _inst.TickSize) return null;
            double tp = isLong ? entry + cfg.rrRatio * risk : entry - cfg.rrRatio * risk;
            double q = cfg.fixedQty ? cfg.qty : _inst.QtyForRisk(cfg.riskDollar, risk);
            return new TradePlan(isLong ? Direction.Long : Direction.Short, _inst.RoundPrice(entry), _inst.RoundPrice(sl),
                                 _inst.RoundPrice(tp), q > 0 ? q : 1.0, risk, null);
        }

        private bool VwapOk(bool isLong, double price)
        {
            if (_cfg.vwapMode == "off") return true;
            if (!_vwap.Value.HasValue) return false;
            double v = _vwap.Value.Value;
            bool above = price > v, below = price < v;
            if (_cfg.vwapMode == "with") return isLong ? above : below;
            return isLong ? below : above;
        }

        private bool InSess(Bar bar)
        {
            if (!_cfg.useSess) return true;
            DateTime local = TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(bar.Time), _zone);
            int hm = local.Hour * 100 + local.Minute;
            int a = _cfg.sessStart, b = _cfg.sessEnd;
            return a <= b ? (a <= hm && hm < b) : (hm >= a || hm < b);
        }

        private bool ZoneOk(MZone z, int idx)
        {
            return z.Score >= _cfg.minEntryScore && (_cfg.maxZoneAge == 0 || idx - z.Born <= _cfg.maxZoneAge);
        }

        private void PendRemove(string kind)
        {
            _pendOrder.Remove(kind);
            _pendId.Remove(kind); _pendEntry.Remove(kind); _pendSl.Remove(kind); _pendZone.Remove(kind);
        }

        private void CancelAll(EngineOutput o, int idx, string reason)
        {
            foreach (string kind in _pendOrder) o.Orders.Add(new OrderIntent(OrderAction.Cancel, _pendId[kind], idx, reason));
            _pendOrder.Clear(); _pendId.Clear(); _pendEntry.Clear(); _pendSl.Clear(); _pendZone.Clear();
        }

        public EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            MtkZoneConfig cfg = _cfg;
            EngineOutput o = new EngineOutput();
            History.Append(bar);
            int idx = History.BarIndex;
            double atr = History.Atr;
            _vwap.Push(bar);

            // 1. nove zony z uzavretych sviecok TF zon
            foreach (HtfSeries s in _slots)
                if (s.Push(bar) != null)
                    foreach (Cand c in Detect(s)) AddZone(c, s.Minutes, bar, idx, o);
            // 2. test: prvy dotyk zonu zareze
            foreach (MZone z in _zones)
            {
                if (z.Active && idx > z.Born && (z.Dir == 1 ? bar.Low <= z.Top : bar.High >= z.Bot))
                {
                    z.Active = false;
                    z.TouchIdx = idx;
                    if (cfg.showZones)
                    {
                        o.Drawings.Add(new DrawUpdate(z.BoxId, "extend_right", false));
                        o.Drawings.Add(new DrawUpdate(z.BoxId, "x2_ms", bar.Time));
                        string col = z.IsVol ? VolColor : (z.Dir == 1 ? DemColor : SupColor);
                        o.Drawings.Add(new DrawUpdate(z.BoxId, "fill_color", col + "1a"));   // otestovana = bledsia
                        o.Drawings.Add(new DrawUpdate(z.BoxId, "text", Text(z)));
                    }
                }
            }
            // 3. modely IBS a pin bar
            Models(bar, idx, atr, o);
            _zones.RemoveAll(delegate(MZone z) { return !z.Active && (z.Used || z.Dead); });

            // 4. pozicia
            foreach (string oid in ctx.DroppedEntryIds)
            {
                List<string> drop = new List<string>();
                foreach (string kind in _pendOrder) if (_pendId[kind] == oid) drop.Add(kind);
                foreach (string kind in drop) PendRemove(kind);
            }
            bool inPos = ctx.PositionSize != 0.0;
            if (inPos)
            {
                if (!_wasInPos)
                    foreach (string kind in _pendOrder)
                        if (ctx.OpenOrderIds.Contains(_pendId[kind])) _pendZone[kind].Used = true;
                CancelAll(o, idx, "pozícia otvorená (OCO)");
            }
            else if (_wasInPos) _lastExit = idx;
            _wasInPos = inPos;
            if (inPos) return o;

            bool gapOk = (!_lastExit.HasValue || idx - _lastExit.Value >= cfg.minGap) && InSess(bar);
            double buf = cfg.slBufTicks * _inst.TickSize;
            MZone dz = null, sz = null, di = null, si = null, dp = null, sp = null;
            foreach (MZone z in _zones)
            {
                if (z.Active && ZoneOk(z, idx))
                {
                    if (z.Dir == 1 && z.Top < bar.Close && (dz == null || z.Top > dz.Top)) dz = z;
                    if (z.Dir == -1 && z.Bot > bar.Close && (sz == null || z.Bot < sz.Bot)) sz = z;
                }
                if (!z.Active && !z.Used && !z.Dead && z.Score >= cfg.minEntryScore)
                {
                    if (z.Ist == 4)
                    {
                        if (z.Dir == 1 && (di == null || z.IstIdx > di.IstIdx)) di = z;
                        if (z.Dir == -1 && (si == null || z.IstIdx > si.IstIdx)) si = z;
                    }
                    if (z.PinNow)
                    {
                        if (z.Dir == 1) dp = z;
                        else sp = z;
                    }
                }
            }

            // pin bar ma prednost (market), potom IBS, potom limit na zonu
            MZone[] pz = { dp, sp };
            for (int i = 0; i < 2; i++)
            {
                MZone z = pz[i];
                bool isLong = i == 0;
                if (z == null || !cfg.usePin || !gapOk) continue;
                if ((isLong && !cfg.AllowLong) || (!isLong && !cfg.AllowShort) || !VwapOk(isLong, bar.Close)) continue;
                double sl = isLong ? bar.Low - buf : bar.High + buf;
                TradePlan plan = Plan(isLong, bar.Close, sl);
                if (plan == null) continue;
                CancelAll(o, idx, "pin bar");
                z.Used = true;
                OrderIntent intent = new OrderIntent(OrderAction.Entry, "mz:P:" + idx.ToString(CultureInfo.InvariantCulture), z.Uid,
                                                     "MTK ZONE pin bar " + z.Tf.ToString(CultureInfo.InvariantCulture) + "m " + z.Src);
                intent.Direction = plan.Direction;
                intent.Plan = plan;
                intent.OrderType = OrderType.Market;
                o.Orders.Add(intent);
                return o;
            }

            int nSw = Math.Min(cfg.ibsSlLookback, History.Count);
            double swLo = 0, swHi = 0;
            for (int k = 0; k < nSw; k++)
            {
                swLo = k == 0 ? History[k].Low : Math.Min(swLo, History[k].Low);
                swHi = k == 0 ? History[k].High : Math.Max(swHi, History[k].High);
            }
            Dictionary<string, MZone> wz = new Dictionary<string, MZone>();
            Dictionary<string, bool> wl = new Dictionary<string, bool>();
            Dictionary<string, double> we = new Dictionary<string, double>();
            Dictionary<string, double> ws = new Dictionary<string, double>();
            if (cfg.useIBS && di != null && cfg.AllowLong) { wz["LI"] = di; wl["LI"] = true; we["LI"] = di.ImbOpen; ws["LI"] = swLo - buf; }
            if (cfg.useIBS && si != null && cfg.AllowShort) { wz["SI"] = si; wl["SI"] = false; we["SI"] = si.ImbOpen; ws["SI"] = swHi + buf; }
            if (cfg.useLimit && dz != null && cfg.AllowLong) { wz["L"] = dz; wl["L"] = true; we["L"] = dz.Top; ws["L"] = dz.Bot - buf; }
            if (cfg.useLimit && sz != null && cfg.AllowShort) { wz["S"] = sz; wl["S"] = false; we["S"] = sz.Bot; ws["S"] = sz.Top + buf; }
            foreach (string kind in Kinds)
            {
                TradePlan plan = null;
                if (wz.ContainsKey(kind) && gapOk)
                {
                    double e = we[kind];
                    if (VwapOk(wl[kind], e) && (cfg.maxDist == 0 || Math.Abs(bar.Close - e) <= cfg.maxDist))
                        plan = Plan(wl[kind], e, ws[kind]);
                }
                bool has = _pendId.ContainsKey(kind);
                if (plan == null)
                {
                    if (has)
                    {
                        o.Orders.Add(new OrderIntent(OrderAction.Cancel, _pendId[kind], idx, "podmienka vstupu neplatí"));
                        PendRemove(kind);
                    }
                    continue;
                }
                MZone zz = wz[kind];
                if (has && _pendEntry[kind] == plan.Entry && _pendSl[kind] == plan.StopLoss && ReferenceEquals(_pendZone[kind], zz))
                    continue;
                if (has) o.Orders.Add(new OrderIntent(OrderAction.Cancel, _pendId[kind], idx, "nová cena limitu"));
                string oid = "mz:" + kind + ":" + idx.ToString(CultureInfo.InvariantCulture);
                if (!has) _pendOrder.Add(kind);
                _pendId[kind] = oid; _pendEntry[kind] = plan.Entry; _pendSl[kind] = plan.StopLoss; _pendZone[kind] = zz;
                OrderIntent intent = new OrderIntent(OrderAction.Entry, oid, zz.Uid,
                    "MTK ZONE " + (kind.Contains("I") ? "IBS" : "limit na zónu") + " " + zz.Tf.ToString(CultureInfo.InvariantCulture) + "m " + zz.Src);
                intent.Direction = plan.Direction;
                intent.Plan = plan;
                intent.OrderType = OrderType.Limit;
                o.Orders.Add(intent);
            }
            return o;
        }
    }
}
