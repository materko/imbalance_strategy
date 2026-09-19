// Hladanie imbalance (gapu) vnutri zony + sviečkove patterny Pin Bar a Engulfing.
// Zrkadlo `tradebot/strategies/ibs/ta/imbalance.py` (Pine 1637-1665, 1712-1739)
// a `tradebot/strategies/ibs/ta/patterns.py` (Pine `f_isPinBar`, `f_isEngulfing`).
using System;
using TradeBot.Core;

namespace TradeBot.Strategies.IbsNinja.Ta
{
    /// <summary>Najdeny gap. `Offset` je Pine `midIdx` = `lb + 1`.</summary>
    public sealed class ImbalanceHit
    {
        public int Offset;
        public int BarIndex;
        public double BodyTop;
        public double BodyBot;
        public double Open;
        public double High;
        public double Low;
        public double Distance;
    }

    public static class Patterns
    {
        /// <summary>Vrati gap, ktory je zone NAJBLIZSIE, alebo null.
        /// Pozor: pri LONG zone sa hlada BEARISH gap (a naopak) - ten sa ma vyplnit.</summary>
        public static ImbalanceHit FindImbalance(BarHistory history, double zoneTop, double zoneBot, Direction direction,
                                                 IbsConfig cfg, InstrumentSpec inst, int zoneCreatedBarIndex, double atr)
        {
            double price = history.Current.Close;
            double minImb = cfg.minImbSizePoints.Resolve(inst, price, atr);
            double maxDist = cfg.imbMaxDistTicks.Resolve(inst, price, atr);

            ImbalanceHit best = null;

            for (int lb = 0; lb < cfg.imbLookback; lb++)
            {
                if (!history.Has(lb + 2)) continue;
                if (history.IndexOf(lb + 2) < zoneCreatedBarIndex) continue;

                Bar near = history[lb];
                Bar mid = history[lb + 1];
                Bar far = history[lb + 2];

                bool isBullImb = near.Low > far.High && mid.Close > far.High && (near.Low - far.High) >= minImb;
                bool isBearImb = near.High < far.Low && mid.Close < far.Low && (far.Low - near.High) >= minImb;

                double distance;
                if (direction == Direction.Long)
                {
                    if (!isBearImb) continue;
                    bool above = mid.Open > zoneTop;
                    bool through = mid.High >= zoneTop && mid.Low <= zoneBot;
                    if (!(above || through)) continue;
                    distance = Math.Max(0.0, mid.Low - zoneTop);
                }
                else
                {
                    if (!isBullImb) continue;
                    bool below = mid.Open < zoneBot;
                    bool through = mid.High >= zoneTop && mid.Low <= zoneBot;
                    if (!(below || through)) continue;
                    distance = Math.Max(0.0, zoneBot - mid.High);
                }

                if (distance > maxDist) continue;
                if (best != null && distance >= best.Distance) continue;

                best = new ImbalanceHit();
                best.Offset = lb + 1;
                best.BarIndex = history.IndexOf(lb + 1);
                best.BodyTop = mid.BodyTop;
                best.BodyBot = mid.BodyBottom;
                best.Open = mid.Open;
                best.High = mid.High;
                best.Low = mid.Low;
                best.Distance = distance;
            }

            return best;
        }

        /// <summary>Pine `f_isPinBar(dir)`: rozsah >= minimum, knot v smere vstupu >= ratio x telo,
        /// telo v okrajovej casti rozsahu. Sviecka bez tela prejde podmienkou knota automaticky.</summary>
        public static bool IsPinBar(Bar bar, Direction direction, IbsConfig cfg, InstrumentSpec inst, double atr)
        {
            double rng = bar.High - bar.Low;
            double bodyTop = bar.BodyTop;
            double bodyBot = bar.BodyBottom;
            double bodyLen = bodyTop - bodyBot;
            double upperWick = bar.High - bodyTop;
            double lowerWick = bodyBot - bar.Low;

            double minRange = cfg.pbMinRangePoints.Resolve(inst, bar.Close, atr);
            if (rng < minRange) return false;

            bool wickOk = direction == Direction.Long
                ? (bodyLen <= 0 || lowerWick >= bodyLen * cfg.pbWickToBodyRatio)
                : (bodyLen <= 0 || upperWick >= bodyLen * cfg.pbWickToBodyRatio);
            if (!wickOk) return false;

            double posLimit = rng * (cfg.pbBodyPositionPct / 100.0);
            if (direction == Direction.Long) return (bar.High - bodyTop) <= posLimit;
            return (bodyBot - bar.Low) <= posLimit;
        }

        /// <summary>Pine `f_isEngulfing(dir)` - „outlier" sviecka voci priemernemu rozsahu, nie geometricky engulfing.</summary>
        public static bool IsEngulfing(BarHistory history, Direction direction, IbsConfig cfg, InstrumentSpec inst, double atr)
        {
            Bar bar = history.Current;
            double rng = bar.High - bar.Low;

            double minRange = cfg.engMinRangePoints.Resolve(inst, bar.Close, atr);
            if (rng < minRange) return false;

            bool colorOk = direction == Direction.Long ? bar.Close > bar.Open : bar.Close < bar.Open;
            if (!colorOk) return false;

            double avgRange = history.SmaRange(cfg.engSizeAvgLen, 0);
            if (avgRange <= 0) return false;
            return rng >= cfg.engSizeMultiplier * avgRange;
        }
    }
}
