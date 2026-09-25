// Support / Resistance - zhluky opakovanych dotykov tej istej ceny.
// Zrkadlo `tradebot/strategies/ibs/ta/sr.py`. Replika Pine riadkov 822-1132.
//
// Kazdy potvrdeny swing (vlastny lookback srSwingLen) sa skusi "prilepit" k uz
// existujucej urovni, ak je od nej vzdialeny menej ako srClusterPoints - tym sa
// pocitaju opakovane dotyky. Pivot sa pocita z close, nie z knotu. Uroven nie je
// ciara, ale oblast - drzi si skutocny rozsah (min/max) dotykov.
//
// Kreslenie bezi len na poslednom bare (`Render`), lebo zlozenie zhlukov sa meni
// s cenou (triedi sa podla vzdialenosti od close). Typ urovne je dynamicky:
// support/resistance nie je vlastnost urovne, ale jej vztahu k aktualnej cene.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;
using TradeBot.Strategies.IbsNet;

namespace TradeBot.Strategies.IbsNet.Ta
{
    /// <summary>Jedna uroven - priemer dotykov + ich skutocny rozsah.</summary>
    public sealed class SrLevel
    {
        public double Price;
        public int Touches;
        /// <summary>+1 vznikla z pivot-highov, -1 z pivot-lowov. Na kreslenie sa NEPOUZIVA,
        /// typ sa prepocitava dynamicky podla polohy ceny.</summary>
        public int Typ;
        public long FirstMs;
        public double Low;
        public double High;
        public bool ZoneSpawned;

        public SrLevel(double price, int touches, int typ, long firstMs, double low, double high)
        {
            Price = price;
            Touches = touches;
            Typ = typ;
            FirstMs = firstMs;
            Low = low;
            High = high;
            ZoneSpawned = false;
        }
    }

    public sealed class SupportResistance
    {
        //: Pine `srZoneHalfWidth` - zona ma fixnu vysku 3 cenove body.
        private const double HalfWidth = 1.5;
        //: Pine `srLevelMax`.
        private const int MaxLevels = 150;

        private readonly IbsConfig cfg;
        private readonly InstrumentSpec inst;

        public List<SrLevel> Levels = new List<SrLevel>();

        public SupportResistance(IbsConfig cfg, InstrumentSpec inst)
        {
            this.cfg = cfg;
            this.inst = inst;
        }

        // -- zbieranie dotykov ------------------------------------------------ //

        /// <summary>Zaznamena dotyky z tohto baru. Vrati indexy dotknutych urovni -
        /// potrebuje ich `enableSrTrading` (z urovne, ktora prvykrat dosiahla
        /// `srMinTouches`, sa spawne obchodovatelna zona).</summary>
        public List<int> OnBar(Bar bar, BarHistory history)
        {
            int length = cfg.srSwingLen;
            List<int> touched = new List<int>();

            double? pivHi = MarketStructure.Pivot(history, length, true, "close");
            if (pivHi.HasValue) touched.Add(AddTouch(pivHi.Value, 1, history[length].Time));
            double? pivLo = MarketStructure.Pivot(history, length, false, "close");
            if (pivLo.HasValue) touched.Add(AddTouch(pivLo.Value, -1, history[length].Time));

            ForgetOld(bar);
            return touched;
        }

        /// <summary>Pine `addSrTouch` - prilepi k existujucej urovni alebo zalozi novu.</summary>
        private int AddTouch(double price, int typ, long tsMs)
        {
            double tol = cfg.srClusterPoints.Resolve(inst, price, 0.0);
            for (int i = 0; i < Levels.Count; i++)
            {
                SrLevel lvl = Levels[i];
                if (lvl.Typ == typ && Math.Abs(lvl.Price - price) <= tol)
                {
                    lvl.Touches += 1;
                    lvl.Price = (lvl.Price + price) / 2;
                    lvl.Low = Math.Min(lvl.Low, price);
                    lvl.High = Math.Max(lvl.High, price);
                    return i;
                }
            }

            Levels.Add(new SrLevel(price, 1, typ, tsMs, price, price));
            if (Levels.Count > MaxLevels) Levels.RemoveAt(0);
            return Levels.Count - 1;
        }

        /// <summary>Pine riadky 955-963 - uroven starsia nez `srLookbackDays` vypadne.</summary>
        private void ForgetOld(Bar bar)
        {
            long cutoff = (long)cfg.srLookbackDays * 86400000L;
            if (cutoff <= 0) return;
            List<SrLevel> kept = new List<SrLevel>();
            for (int i = 0; i < Levels.Count; i++)
            {
                if (bar.Time - Levels[i].FirstMs <= cutoff) kept.Add(Levels[i]);
            }
            Levels = kept;
        }

        // -- kreslenie -------------------------------------------------------- //

        /// <summary>Pine riadky 1073-1131 - vykresli sa az na poslednom bare.</summary>
        public List<DrawCommand> Render(Bar bar)
        {
            List<DrawCommand> outCmds = new List<DrawCommand>();
            if (!cfg.showSR || Levels.Count == 0) return outCmds;

            // Triedime podla VZDIALENOSTI od aktualnej ceny - zobrazi sa srMaxLevels
            // najblizsich urovni, nie tie najsilnejsie kdekolvek na grafe.
            List<SrLevel> order = StableOrderByDistance(Levels, bar.Close);

            List<SrLevel> filtered = new List<SrLevel>();
            for (int i = 0; i < order.Count; i++)
            {
                if (order[i].Touches >= cfg.srMinTouches) filtered.Add(order[i]);
            }
            List<SrLevel> shown = new List<SrLevel>();
            for (int i = 0; i < filtered.Count && shown.Count < cfg.srMaxLevels; i++) shown.Add(filtered[i]);
            if (shown.Count == 0) return outCmds;

            List<List<SrLevel>> groups = Cluster(shown, bar);
            for (int n = 0; n < groups.Count; n++) outCmds.AddRange(DrawGroup(groups[n], bar, n));
            return outCmds;
        }

        /// <summary>Stabilny insertion-sort podla |price - close| - Python `sorted` je stabilny,
        /// C# `List.Sort` nie.</summary>
        private static List<SrLevel> StableOrderByDistance(List<SrLevel> levels, double close)
        {
            List<SrLevel> result = new List<SrLevel>(levels);
            for (int i = 1; i < result.Count; i++)
            {
                SrLevel cur = result[i];
                double curKey = Math.Abs(cur.Price - close);
                int j = i - 1;
                while (j >= 0 && Math.Abs(result[j].Price - close) > curKey)
                {
                    result[j + 1] = result[j];
                    j--;
                }
                result[j + 1] = cur;
            }
            return result;
        }

        /// <summary>Zhluky blizkych urovni - retazovo a bez ohladu na support/resistance.
        /// Bez toho by blizka S a R dali dve prekryvajuce sa ciary tesne vedla seba.</summary>
        private List<List<SrLevel>> Cluster(List<SrLevel> shown, Bar bar)
        {
            double tol = cfg.srClusterPoints.Resolve(inst, bar.Close, 0.0);
            bool[] used = new bool[shown.Count];
            List<List<SrLevel>> groups = new List<List<SrLevel>>();

            for (int a = 0; a < shown.Count; a++)
            {
                if (used[a]) continue;
                used[a] = true;
                List<SrLevel> group = new List<SrLevel>();
                group.Add(shown[a]);
                bool grew = true;
                while (grew)
                {
                    grew = false;
                    for (int b = 0; b < shown.Count; b++)
                    {
                        if (used[b]) continue;
                        bool near = false;
                        for (int g = 0; g < group.Count; g++)
                        {
                            if (Math.Abs(group[g].Price - shown[b].Price) <= tol) { near = true; break; }
                        }
                        if (near)
                        {
                            used[b] = true;
                            group.Add(shown[b]);
                            grew = true;
                        }
                    }
                }
                groups.Add(group);
            }
            return groups;
        }

        private List<DrawCommand> DrawGroup(List<SrLevel> group, Bar bar, int n)
        {
            double lo = group[0].Low;
            double hi = group[0].High;
            long earliest = group[0].FirstMs;
            int touches = group[0].Touches;
            for (int i = 1; i < group.Count; i++)
            {
                if (group[i].Low < lo) lo = group[i].Low;
                if (group[i].High > hi) hi = group[i].High;
                if (group[i].FirstMs < earliest) earliest = group[i].FirstMs;
                touches += group[i].Touches;
            }
            if (lo == hi)
            {
                lo -= inst.TickSize * 2;
                hi += inst.TickSize * 2;
            }
            double mid = (lo + hi) / 2;

            string kind, color, textColor;
            if (group.Count >= 2)
            {
                kind = IbsKinds.SrGolden;
                color = Palette.Amber;
                textColor = "#000000";
            }
            else
            {
                // Cena NAD urovnou = support, POD nou = resistance.
                kind = IbsKinds.SrLevel;
                color = bar.Close > mid ? Palette.Long : Palette.Short;
                textColor = "#ffffff";
            }

            string fill = Palette.WithAlpha(color, 100 - cfg.srZoneSaturationPct);
            string nStr = n.ToString(CultureInfo.InvariantCulture);

            DrawBox box = new DrawBox(kind, earliest, mid + HalfWidth, bar.Time, mid - HalfWidth, fill);
            box.FillColor = fill;
            box.BorderWidth = 0;
            box.ExtendRight = true;
            box.ObjId = "sr." + nStr + ".box";

            DrawLabel label = new DrawLabel(kind, bar.Time, mid, touches.ToString(CultureInfo.InvariantCulture) + "x", textColor);
            label.Style = LabelStyles.Left;
            label.BgColor = color;
            label.ObjId = "sr." + nStr + ".label";

            return new List<DrawCommand> { box, label };
        }
    }
}
