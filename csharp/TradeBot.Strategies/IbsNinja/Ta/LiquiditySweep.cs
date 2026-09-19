// Likvidita (sweep / stop hunt) - replika Pine riadkov 1135-1252.
// Zrkadlo `tradebot/strategies/ibs/ta/liquidity.py`.
//
// Sweep je situacia, ked cena kratko prepichne swing high/low (tym "vyberie" stopy
// nahromadene za urovnou), ale hned sa potvrdene zatvori spat na povodnu stranu.
// Na rozdiel od BOS, ktory sa udrzi, je to signal mozneho obratu.
//
// Sleduju sa len "silne" pivoty - musia byt najvyssim/najnizsim bodom za poslednych
// liqStrengthLen barov. Postupnost: pivot -> prepichnutie o aspon liqSweepMinWick ->
// navrat zavretim spat do liqSweepConfirmBars barov. Ak sa navrat nestihne, bol to
// realny breakout a uroven sa zahodi.
//
// Modul vracia aj zony na obchodovanie (enableLqTrading); sweep je z definicie
// fade signal, takze obchod ide vzdy PROTI nemu.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;
using TradeBot.Strategies.IbsNinja;

namespace TradeBot.Strategies.IbsNinja.Ta
{
    /// <summary>Obchodovatelna zona, ktora vznikla z potvrdeneho sweepu.</summary>
    public sealed class Sweep
    {
        public readonly Direction Direction;
        public readonly double Top;
        public readonly double Bot;

        public Sweep(Direction direction, double top, double bot)
        {
            Direction = direction;
            Top = top;
            Bot = bot;
        }
    }

    /// <summary>Vysledok `OnBar` - Python vracia tuple (kresby, zony).</summary>
    public sealed class LiquidityResult
    {
        public readonly List<DrawCommand> Drawings;
        public readonly List<Sweep> Sweeps;

        public LiquidityResult(List<DrawCommand> drawings, List<Sweep> sweeps)
        {
            Drawings = drawings;
            Sweeps = sweeps;
        }
    }

    public sealed class LiquiditySweep
    {
        /// <summary>Stav prave sledovaneho pivota - Python drzi ako dict
        /// (uroven, ts vzniku, prepichnute?, ts prepichnutia, bar_index prepichnutia, extrem).</summary>
        private sealed class SweepState
        {
            public double Level;
            public long Ts;
            public bool Pierced;
            public long PierceTs;
            public int PierceIdx;
            public double Extreme;
        }

        private readonly IbsConfig cfg;
        private readonly InstrumentSpec inst;
        private SweepState _hi;
        private SweepState _lo;
        private int _seq;

        public LiquiditySweep(IbsConfig cfg, InstrumentSpec inst)
        {
            this.cfg = cfg;
            this.inst = inst;
        }

        /// <summary>Volaj raz na kazdy uzavrety bar.</summary>
        public LiquidityResult OnBar(Bar bar, BarHistory history)
        {
            List<DrawCommand> outCmds = new List<DrawCommand>();
            List<Sweep> zones = new List<Sweep>();
            int length = cfg.liqSweepLen;

            // ---- nove "silne" pivoty --------------------------------------- //
            double? pivHi = MarketStructure.Pivot(history, length, true);
            if (pivHi.HasValue && pivHi.Value >= Extreme(history, true))
            {
                SweepState st = new SweepState();
                st.Level = pivHi.Value;
                st.Ts = history[length].Time;
                st.Pierced = false;
                _hi = st;
            }
            double? pivLo = MarketStructure.Pivot(history, length, false);
            if (pivLo.HasValue && pivLo.Value <= Extreme(history, false))
            {
                SweepState st = new SweepState();
                st.Level = pivLo.Value;
                st.Ts = history[length].Time;
                st.Pierced = false;
                _lo = st;
            }

            double minWick = cfg.liqSweepMinWick.Resolve(inst, bar.Close, 0.0);

            // ---- sell-side: nad swing high ---------------------------------- //
            if (_hi != null)
            {
                SweepState st = _hi;
                if (!st.Pierced)
                {
                    if (bar.High - st.Level >= minWick)
                    {
                        st.Pierced = true;
                        st.PierceTs = bar.Time;
                        st.PierceIdx = history.BarIndex;
                        st.Extreme = bar.High;
                    }
                }
                else
                {
                    st.Extreme = Math.Max(st.Extreme, bar.High);
                    int since = history.BarIndex - st.PierceIdx;
                    if (bar.Close < st.Level && since <= cfg.liqSweepConfirmBars)
                    {
                        outCmds.AddRange(Draw(st, "X ↓"));
                        if (cfg.enableLqTrading)
                        {
                            double top, bot;
                            Span(st.Extreme, st.Level, out top, out bot);
                            zones.Add(new Sweep(Direction.Short, top, bot));
                        }
                        _hi = null;
                    }
                    else if (since > cfg.liqSweepConfirmBars)
                    {
                        _hi = null; // navrat neprisiel -> bol to breakout, nie sweep
                    }
                }
            }

            // ---- buy-side: pod swing low ------------------------------------ //
            if (_lo != null)
            {
                SweepState st = _lo;
                if (!st.Pierced)
                {
                    if (st.Level - bar.Low >= minWick)
                    {
                        st.Pierced = true;
                        st.PierceTs = bar.Time;
                        st.PierceIdx = history.BarIndex;
                        st.Extreme = bar.Low;
                    }
                }
                else
                {
                    st.Extreme = Math.Min(st.Extreme, bar.Low);
                    int since = history.BarIndex - st.PierceIdx;
                    if (bar.Close > st.Level && since <= cfg.liqSweepConfirmBars)
                    {
                        outCmds.AddRange(Draw(st, "X ↑"));
                        if (cfg.enableLqTrading)
                        {
                            double top, bot;
                            Span(st.Level, st.Extreme, out top, out bot);
                            zones.Add(new Sweep(Direction.Long, top, bot));
                        }
                        _lo = null;
                    }
                    else if (since > cfg.liqSweepConfirmBars)
                    {
                        _lo = null;
                    }
                }
            }

            return new LiquidityResult(outCmds, zones);
        }

        // ------------------------------------------------------------------ //

        /// <summary>Pine `ta.highest(high, liqStrengthLen)` / `ta.lowest(low, ...)`.</summary>
        private double Extreme(BarHistory history, bool high)
        {
            int n = Math.Min(cfg.liqStrengthLen, history.Count);
            double result = high ? double.NegativeInfinity : double.PositiveInfinity;
            for (int i = 0; i < n; i++)
            {
                Bar b = history[i];
                double v = high ? b.High : b.Low;
                if (high) { if (v > result) result = v; }
                else { if (v < result) result = v; }
            }
            return result;
        }

        /// <summary>Zona musi mat nenulovu vysku, aj ked prepichnutie bolo presne.</summary>
        private void Span(double top, double bot, out double outTop, out double outBot)
        {
            if (top == bot)
            {
                outTop = top + inst.TickSize * 2;
                outBot = bot - inst.TickSize * 2;
                return;
            }
            outTop = top;
            outBot = bot;
        }

        /// <summary>Bodkovana ciara od vzniku swingu po bar prepichnutia + "X" v jej strede.
        /// "X" je vzdy mierne POD ciarou - BOS/CHoCH je vzdy nad svojou, takze ked sa stretnu
        /// na tom istom mieste, napisy sa neprekryju.</summary>
        private List<DrawCommand> Draw(SweepState st, string text)
        {
            if (!cfg.showLiqSweep) return new List<DrawCommand>();
            _seq += 1;
            int uid = _seq;
            double level = st.Level;
            long x1 = st.Ts;
            long x2 = st.PierceTs;
            string uidStr = uid.ToString(CultureInfo.InvariantCulture);

            DrawLine line = new DrawLine(IbsKinds.LiqSweep, x1, level, x2, level, Palette.WithAlpha(Palette.Long, 20));
            line.Style = LineStyles.Dotted;
            line.Width = 1;
            line.ObjId = "liq." + uidStr + ".line";
            line.Text = text;

            DrawLabel label = new DrawLabel(IbsKinds.LiqSweep, (x1 + x2) / 2, level - inst.TickSize * 15, text, Palette.Long);
            label.Style = LabelStyles.None;
            label.Above = false;
            label.ObjId = "liq." + uidStr + ".label";

            return new List<DrawCommand> { line, label };
        }
    }
}
