// Market Structure - swingy HH/HL/LH/LL a prerazenia BOS/CHoCH.
// Zrkadlo `tradebot/strategies/ibs/ta/structure.py`. Replika Pine riadkov 706-820.
//
// Swing sa potvrdi cez ta.pivothigh/ta.pivotlow, co je nutne oneskorene o
// structureSwingLen barov. Ked potom cena zavrie nad poslednym potvrdenym swing high:
//  - ak bola struktura predtym bearish -> CHoCH (zmena charakteru)
//  - ak uz bola bullish -> BOS (pokracovanie trendu)
// Zrkadlovo pre swing low. HH/HL/LH/LL je nezavisle znacenie - priradi sa hned pri
// potvrdeni swingu, kym BOS/CHoCH vznika az ked cena uroven prerazi.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;
using TradeBot.Strategies.IbsNinja;

namespace TradeBot.Strategies.IbsNinja.Ta
{
    /// <summary>Potvrdeny swing bod (Python `Swing` dataclass). Nepouziva sa priamo v tomto
    /// module (Pine si drzi len poslednu urovnu), ale je sucastou verejneho API.</summary>
    public sealed class Swing
    {
        public readonly long TsMs;
        public readonly int BarIndex;
        public readonly double Price;
        public readonly bool IsHigh;

        public Swing(long tsMs, int barIndex, double price, bool isHigh)
        {
            TsMs = tsMs;
            BarIndex = barIndex;
            Price = price;
            IsHigh = isHigh;
        }
    }

    public sealed class MarketStructure
    {
        private readonly IbsConfig cfg;
        private readonly InstrumentSpec inst;

        /// <summary>Pine `marketBias`: +1 bullish, -1 bearish, 0 neurcene.</summary>
        public int Bias;

        // posledny potvrdeny swing, ktory este nebol prerazeny
        private double? _swingHigh;
        private double? _swingLow;
        private int? _swingHighBar;
        private int? _swingLowBar;
        private long? _swingHighTs;
        private long? _swingLowTs;
        // posledny potvrdeny swing vobec - na porovnanie HH vs LH
        private double? _lastHigh;
        private double? _lastLow;
        private int _seq;

        public MarketStructure(IbsConfig cfg, InstrumentSpec inst)
        {
            this.cfg = cfg;
            this.inst = inst;
            Bias = 0;
        }

        private int Uid()
        {
            _seq += 1;
            return _seq;
        }

        /// <summary>Pine `ta.pivothigh(length, length)` / `ta.pivotlow`. Stred okna je bar
        /// vzdialeny `length` dozadu.
        ///
        /// Porovnanie je asymetricke a je to zamer. Pine na lavej strane pripusta ZHODU,
        /// vpravo vyzaduje prisne nizsie high (resp. vyssie low). `source="hl"` berie
        /// high/low (Market Structure), `source="close"` berie close (S/R aj likvidita).</summary>
        public static double? Pivot(BarHistory history, int length, bool high)
        {
            return Pivot(history, length, high, "hl");
        }

        public static double? Pivot(BarHistory history, int length, bool high, string source)
        {
            int need = 2 * length + 1;
            if (length <= 0 || history.Count < need) return null;

            double value = PivotVal(history[length], high, source);
            for (int i = 0; i < need; i++)
            {
                if (i == length) continue;
                double other = PivotVal(history[i], high, source);
                // i < length = novsie bary = vpravo od pivota -> prisne; starsie -> zhoda OK
                bool strict = i < length;
                if (high)
                {
                    if (strict ? (other >= value) : (other > value)) return null;
                }
                else
                {
                    if (strict ? (other <= value) : (other < value)) return null;
                }
            }
            return value;
        }

        private static double PivotVal(Bar b, bool high, string source)
        {
            if (source == "close") return b.Close;
            return high ? b.High : b.Low;
        }

        /// <summary>Volaj raz na kazdy uzavrety bar.</summary>
        public List<DrawCommand> OnBar(Bar bar, BarHistory history)
        {
            List<DrawCommand> outCmds = new List<DrawCommand>();
            int length = cfg.structureSwingLen;
            double tick = inst.TickSize;

            // ---- potvrdenie swingov + HH/HL/LH/LL --------------------------- //
            double? pivHi = Pivot(history, length, true);
            if (pivHi.HasValue)
            {
                Bar pivotBar = history[length];
                if (cfg.showMarketStructure && _lastHigh.HasValue)
                {
                    bool isHh = pivHi.Value > _lastHigh.Value;
                    DrawLabel lbl = new DrawLabel(IbsKinds.Swing, pivotBar.Time, pivHi.Value + tick * 25,
                        isHh ? "HH" : "LH",
                        Palette.WithAlpha(isHh ? Palette.Strong : Palette.Long, 25));
                    lbl.Style = LabelStyles.None;
                    lbl.Above = true;
                    lbl.ObjId = "swing.h." + pivotBar.Time.ToString(CultureInfo.InvariantCulture);
                    outCmds.Add(lbl);
                }
                _lastHigh = pivHi;
                _swingHigh = pivHi;
                _swingHighBar = history.IndexOf(length);
                _swingHighTs = pivotBar.Time;
            }

            double? pivLo = Pivot(history, length, false);
            if (pivLo.HasValue)
            {
                Bar pivotBar = history[length];
                if (cfg.showMarketStructure && _lastLow.HasValue)
                {
                    bool isHl = pivLo.Value > _lastLow.Value;
                    DrawLabel lbl = new DrawLabel(IbsKinds.Swing, pivotBar.Time, pivLo.Value - tick * 25,
                        isHl ? "HL" : "LL",
                        Palette.WithAlpha(isHl ? Palette.Strong : Palette.Long, 25));
                    lbl.Style = LabelStyles.None;
                    lbl.Above = false;
                    lbl.ObjId = "swing.l." + pivotBar.Time.ToString(CultureInfo.InvariantCulture);
                    outCmds.Add(lbl);
                }
                _lastLow = pivLo;
                _swingLow = pivLo;
                _swingLowBar = history.IndexOf(length);
                _swingLowTs = pivotBar.Time;
            }

            // ---- prerazenie: BOS / CHoCH ------------------------------------ //
            if (_swingHigh.HasValue && bar.Close > _swingHigh.Value)
            {
                outCmds.AddRange(Break(bar, _swingHigh.Value, _swingHighTs, true));
                Bias = 1;
                _swingHigh = null;
            }

            if (_swingLow.HasValue && bar.Close < _swingLow.Value)
            {
                outCmds.AddRange(Break(bar, _swingLow.Value, _swingLowTs, false));
                Bias = -1;
                _swingLow = null;
            }

            return outCmds;
        }

        /// <summary>Ciara od vzniku swingu po bar prerazenia + stitok v jej strede.
        ///
        /// Ciara je vzdy tlmena slate; farba ostava len na napise (BOS zelena/cervena,
        /// CHoCH jantarova). BOS ma vacsiu vizualnu vahu - hrubsiu ciaru. Stitok je
        /// mierne NAD ciarou, aby sa nebil s likviditnym "X", ktory je pod nou.</summary>
        private List<DrawCommand> Break(Bar bar, double level, long? fromTs, bool upward)
        {
            if (!cfg.showMarketStructure || !fromTs.HasValue) return new List<DrawCommand>();
            bool isChoch = Bias == (upward ? -1 : 1);
            string text = isChoch ? "CHoCH" : "BOS";
            string color = isChoch ? Palette.Amber : (upward ? Palette.Strong : Palette.Long);
            int uid = Uid();
            long from = fromTs.Value;

            DrawLine line = new DrawLine(IbsKinds.Structure, from, level, bar.Time, level,
                Palette.WithAlpha(Palette.Slate, 25));
            line.Style = LineStyles.Solid;
            line.Width = isChoch ? 1 : 2;
            line.ObjId = "struct." + uid.ToString(CultureInfo.InvariantCulture) + ".line";
            line.Text = text;

            DrawLabel label = new DrawLabel(IbsKinds.Structure, (from + bar.Time) / 2,
                level + inst.TickSize * 15, text, color);
            label.Style = LabelStyles.None;
            label.Above = true;
            label.ObjId = "struct." + uid.ToString(CultureInfo.InvariantCulture) + ".label";

            return new List<DrawCommand> { line, label };
        }
    }
}
