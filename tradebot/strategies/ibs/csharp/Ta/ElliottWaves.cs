// Elliott Waves - replika Pine riadkov 1256-1474.
// Zrkadlo `tradebot/strategies/ibs/ta/elliott.py`.
//
// Automaticke pocitanie Elliottovych vln je z principu subjektivne. Modul preto vzdy
// zobrazuje len jednu, najaktualnejsiu interpretaciu poslednej zigzag sekvencie a
// prekresluje sa zakazdym, ked sa zigzag zmeni. Je to pomocna vizualizacia, nie predikcia.
//
// Tri prisne Elliottove pravidla su tu POVINNE (na rozdiel od Fibonacci pomerov, ktore
// su len odporucania):
//  1. vlna 2 sa nesmie vratit za zaciatok vlny 1
//  2. vlna 3 nesmie byt najkratsia z vln 1, 3, 5
//  3. vlna 4 sa nesmie prekryvat s cenovym uzemim vlny 1
//
// Vzacne "diagonal" formacie, kde pravidlo 3 neplati, sa vedome nerozlisuju.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;
using TradeBot.Strategies.IbsNet;

namespace TradeBot.Strategies.IbsNet.Ta
{
    public sealed class ZigZagPoint
    {
        public double Price;
        public long TsMs;
        /// <summary>+1 pivot high, -1 pivot low.</summary>
        public int Typ;

        public ZigZagPoint(double price, long tsMs, int typ)
        {
            Price = price;
            TsMs = tsMs;
            Typ = typ;
        }
    }

    public sealed class ElliottWaves
    {
        //: Pine `ewMaxZzPoints`.
        private const int MaxPoints = 50;

        private readonly IbsConfig cfg;
        private readonly InstrumentSpec inst;
        //: Pine `ewProjExtendBars` je v BAROCH, nie v minutach.
        private readonly long stepMs;
        public List<ZigZagPoint> Points = new List<ZigZagPoint>();
        private bool _changed;

        public ElliottWaves(IbsConfig cfg, InstrumentSpec inst, long stepMs)
        {
            this.cfg = cfg;
            this.inst = inst;
            this.stepMs = stepMs;
        }

        // -- zigzag ----------------------------------------------------------- //

        public void OnBar(Bar bar, BarHistory history)
        {
            int length = cfg.ewSwingLen;
            double? pivHi = MarketStructure.Pivot(history, length, true);
            if (pivHi.HasValue) _changed = _changed | Add(pivHi.Value, history[length].Time, 1, bar);
            double? pivLo = MarketStructure.Pivot(history, length, false);
            if (pivLo.HasValue) _changed = _changed | Add(pivLo.Value, history[length].Time, -1, bar);
        }

        /// <summary>Pine `ewAddPoint`. Vrati True, ak pribudol NOVY bod (nie len posun).
        ///
        /// Rovnaky typ pivota len posunie posledny bod, ak je extremnejsi. Opacny typ
        /// zalozi novy bod, ale len ked je vlna aspon `ewMinWavePoints` velka.</summary>
        private bool Add(double price, long tsMs, int typ, Bar bar)
        {
            if (Points.Count == 0)
            {
                Points.Add(new ZigZagPoint(price, tsMs, typ));
                return true;
            }

            ZigZagPoint last = Points[Points.Count - 1];
            if (typ == last.Typ)
            {
                bool moreExtreme = typ == 1 ? price > last.Price : price < last.Price;
                if (moreExtreme)
                {
                    last.Price = price;
                    last.TsMs = tsMs;
                }
                return false;
            }

            double minWave = cfg.ewMinWavePoints.Resolve(inst, bar.Close, 0.0);
            if (Math.Abs(price - last.Price) < minWave) return false;

            Points.Add(new ZigZagPoint(price, tsMs, typ));
            if (Points.Count > MaxPoints) Points.RemoveAt(0);
            return true;
        }

        // -- kreslenie -------------------------------------------------------- //

        public List<DrawCommand> Render(Bar bar, BarHistory history)
        {
            List<DrawCommand> outCmds = new List<DrawCommand>();
            if (!cfg.showElliott || Points.Count < 2) return outCmds;

            string color = cfg.ewLineColor;

            // Kostra poslednych bodov - tenka, priesvitna.
            List<ZigZagPoint> tail = LastN(Points, 7);
            outCmds.AddRange(Lines(tail, Palette.WithAlpha(color, 60), 1, "tail"));

            double offset = LabelOffset(history);
            if (Points.Count >= 6 && ValidImpulse(LastN(Points, 6)))
            {
                List<ZigZagPoint> pts = LastN(Points, 6);
                outCmds.AddRange(Lines(pts, color, 2, "imp"));
                if (cfg.ewShowLabels) outCmds.AddRange(Labels(pts, offset, color));
                if (cfg.ewShowProjection) outCmds.AddRange(AbcTarget(pts, color));
            }
            else if (Points.Count >= 5 && ValidPartial(LastN(Points, 5)))
            {
                List<ZigZagPoint> pts = LastN(Points, 5);
                outCmds.AddRange(Lines(pts, color, 2, "par"));
                if (cfg.ewShowLabels) outCmds.AddRange(Labels(pts, offset, color));
                if (cfg.ewShowProjection) outCmds.AddRange(Wave5Target(pts, color));
            }
            return outCmds;
        }

        /// <summary>Python `list[-n:]` - poslednych `n` prvkov (alebo menej, ak ich nie je dost).</summary>
        private static List<ZigZagPoint> LastN(List<ZigZagPoint> list, int n)
        {
            int start = Math.Max(0, list.Count - n);
            List<ZigZagPoint> result = new List<ZigZagPoint>();
            for (int i = start; i < list.Count; i++) result.Add(list[i]);
            return result;
        }

        /// <summary>Pine `(highest(high,50) - lowest(low,50)) * 0.02`.</summary>
        private double LabelOffset(BarHistory history)
        {
            int n = Math.Min(50, history.Count);
            if (n == 0) return 0.0;
            double hi = double.NegativeInfinity;
            double lo = double.PositiveInfinity;
            for (int i = 0; i < n; i++)
            {
                Bar b = history[i];
                if (b.High > hi) hi = b.High;
                if (b.Low < lo) lo = b.Low;
            }
            return (hi - lo) * 0.02;
        }

        /// <summary>Impulz zacinajuci v pivot-lowe ide hore.</summary>
        private static int DirectionOf(List<ZigZagPoint> pts)
        {
            return pts[0].Typ == -1 ? 1 : -1;
        }

        /// <summary>Pine `f_ewValidImpulse` - vsetky tri prisne pravidla.</summary>
        private bool ValidImpulse(List<ZigZagPoint> pts)
        {
            int d = DirectionOf(pts);
            double p0 = pts[0].Price, p1 = pts[1].Price, p2 = pts[2].Price;
            double p3 = pts[3].Price, p4 = pts[4].Price, p5 = pts[5].Price;
            double len1 = Math.Abs(p1 - p0), len3 = Math.Abs(p3 - p2), len5 = Math.Abs(p5 - p4);
            bool rule1 = d == 1 ? (p2 > p0) : (p2 < p0);
            bool rule2 = !(len3 < len1 && len3 < len5);
            bool rule3 = d == 1 ? (p4 > p1) : (p4 < p1);
            return rule1 && rule2 && rule3;
        }

        /// <summary>Pine `f_ewValidPartial` - vlny 1-4, pravidlo 2 sa este neda overit.</summary>
        private bool ValidPartial(List<ZigZagPoint> pts)
        {
            int d = DirectionOf(pts);
            double p0 = pts[0].Price, p1 = pts[1].Price, p2 = pts[2].Price, p4 = pts[4].Price;
            bool rule1 = d == 1 ? (p2 > p0) : (p2 < p0);
            bool rule3 = d == 1 ? (p4 > p1) : (p4 < p1);
            return rule1 && rule3;
        }

        private static List<DrawCommand> Lines(List<ZigZagPoint> pts, string color, int width, string tag)
        {
            List<DrawCommand> result = new List<DrawCommand>();
            for (int i = 0; i < pts.Count - 1; i++)
            {
                ZigZagPoint a = pts[i];
                ZigZagPoint b = pts[i + 1];
                DrawLine line = new DrawLine(IbsKinds.ElliottWave, a.TsMs, a.Price, b.TsMs, b.Price, color);
                line.Width = width;
                line.ObjId = "ew." + tag + "." + i.ToString(CultureInfo.InvariantCulture);
                result.Add(line);
            }
            return result;
        }

        private static List<DrawCommand> Labels(List<ZigZagPoint> pts, double offset, string color)
        {
            List<DrawCommand> result = new List<DrawCommand>();
            for (int i = 0; i < pts.Count; i++)
            {
                ZigZagPoint p = pts[i];
                double y = p.Typ == 1 ? p.Price + offset : p.Price - offset;
                string iStr = i.ToString(CultureInfo.InvariantCulture);
                DrawLabel label = new DrawLabel(IbsKinds.ElliottWave, p.TsMs, y, iStr, color);
                label.Style = LabelStyles.None;
                label.Above = p.Typ == 1;
                label.ObjId = "ew.lbl." + iStr;
                result.Add(label);
            }
            return result;
        }

        private long ProjSpanMs()
        {
            return (long)cfg.ewProjExtendBars * stepMs;
        }

        /// <summary>Ciel celej ABC korekcie - 38,2 % az 61,8 % retracement impulzu. Po
        /// dokoncenom 5-vlnovom impulze este nevieme, kde skonci vlna A, takze sa pouziva
        /// bezne odporucana zona pre celu korekciu naraz (guideline, nie pravidlo).</summary>
        private List<DrawCommand> AbcTarget(List<ZigZagPoint> pts, string color)
        {
            int d = DirectionOf(pts);
            double p0 = pts[0].Price;
            double p5 = pts[pts.Count - 1].Price;
            double total = Math.Abs(p5 - p0);
            double a = d == 1 ? (p5 - 0.618 * total) : (p5 + 0.618 * total);
            double b = d == 1 ? (p5 - 0.382 * total) : (p5 + 0.382 * total);
            return ProjBox(pts[pts.Count - 1].TsMs, Math.Max(a, b), Math.Min(a, b), color, "ABC ciel");
        }

        /// <summary>Ciel vlny 5 - vsetky tri standardne odhady naraz ako jedna zona:
        /// 1. rovnost s vlnou 1; 2. 61,8 % celkoveho pohybu vln 1-3;
        /// 3. 123,6 % az 161,8 % dlzky vlny 4, meranej od jej konca.</summary>
        private List<DrawCommand> Wave5Target(List<ZigZagPoint> pts, string color)
        {
            int d = DirectionOf(pts);
            double p0 = pts[0].Price, p1 = pts[1].Price, p3 = pts[3].Price, p4 = pts[4].Price;
            double wave1 = Math.Abs(p1 - p0), move13 = Math.Abs(p3 - p0), wave4 = Math.Abs(p4 - p3);
            double s = d == 1 ? 1.0 : -1.0;
            double[] levels = new double[]
            {
                p4 + s * wave1,
                p4 + s * 0.618 * move13,
                p4 + s * 1.236 * wave4,
                p4 + s * 1.618 * wave4,
            };
            double maxL = levels[0], minL = levels[0];
            for (int i = 1; i < levels.Length; i++)
            {
                if (levels[i] > maxL) maxL = levels[i];
                if (levels[i] < minL) minL = levels[i];
            }
            long lastTs = pts[pts.Count - 1].TsMs;
            List<DrawCommand> outCmds = ProjBox(lastTs, maxL, minL, color, "Vlna 5 ciel");

            double eq = levels[0];
            DrawLine eqLine = new DrawLine(IbsKinds.ElliottProj, lastTs, eq, lastTs + ProjSpanMs(), eq, color);
            eqLine.Style = LineStyles.Dashed;
            eqLine.ObjId = "ew.proj.eq";
            outCmds.Add(eqLine);
            return outCmds;
        }

        private List<DrawCommand> ProjBox(long leftMs, double top, double bot, string color, string text)
        {
            long right = leftMs + ProjSpanMs();
            DrawBox box = new DrawBox(IbsKinds.ElliottProj, leftMs, top, right, bot, color);
            box.FillColor = Palette.WithAlpha(color, 85);
            box.ObjId = "ew.proj.box";

            DrawLabel label = new DrawLabel(IbsKinds.ElliottProj, right, (top + bot) / 2, text, color);
            label.Style = LabelStyles.None;
            label.ObjId = "ew.proj.label";

            return new List<DrawCommand> { box, label };
        }
    }
}
