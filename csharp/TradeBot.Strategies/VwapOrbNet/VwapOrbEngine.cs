// `VwapOrbEngine` - VWAP ORB s jadrom v C#. Zrkadlo `tradebot/strategies/vwaporb/engine.py`; s Python
// enginom sa porovnava bar po bare, na rovnost.
//
// Cely ORB (stavanie rangu, stop, ciel, koniec seansy, kresby) je `OrbEngine`; tento engine k nemu pridava
// seansovy VWAP (`SessionVwap` z jadra) a podmienku cez hacik `BreakAllowed`:
//   long  - close nad high rangu (kontroluje ORB) a podla `vwapRule`: break = VWAP nad high rangu
//           (o `vwapBreakAtr` × ATR), direction = VWAP stupa (zmena za `vwapDriftBars` period aspon
//           `vwapDriftMinAtr` × ATR); pri `closeBeyondVwap` navyse close nad VWAP
//   short - zrkadlovo pod low
// Vystup (`exitMode`): tp = ciel ORB; vwap = bez pevneho ciela (100R), drzi sa, kym cena od vstupu neprerazi
// VWAP proti obchodu; tp_vwap = co pride skor.
//
// Stop posuvany s VWAP (`vwapStop`, `vwapTp`) v C# porte NIE JE: potrebuje stop, ktory sa meni v case podla
// VWAP (Python `VwapTrailing.stop_price_at`), a ten C# `TrailingPlan` ani zive adaptery nepoznaju. Engine ho
// preto odmietne hned pri vytvoreni - radsej chyba nez ticho iny obchod nez v testoch.
using System;
using System.Collections.Generic;
using System.Globalization;
using TradeBot.Core;
using TradeBot.Strategies.OrbNet;

namespace TradeBot.Strategies.VwapOrbNet
{
    [TradeBotEngine("vwaporbnet", "VWAP ORB 1.5 (C#)")]
    public sealed class VwapOrbEngine : OrbEngine
    {
        private const string VwapColor = "#a855f7";
        /// <summary>Ciel pri `exitMode=vwap` - daleko, aby ho cena prakticky nedosiahla (adaptery TP potrebuju).</summary>
        private const double NoTpR = 100.0;

        private readonly VwapOrbConfig _cfg;
        public readonly SessionVwap Vwap;
        /// <summary>VWAP z barov grafu - smer pri `break_candle`, ked 15m VWAP este nema ani jednu periodu</summary>
        public readonly SessionVwap VwapFast;
        private readonly int _fastBars;
        /// <summary>smery, v ktorych uz dnes prerazovacia sviecka bola: den + smer</summary>
        private readonly HashSet<string> _broke = new HashSet<string>();
        private double? _vwapValue;
        /// <summary>pozicia uz bola na spravnej strane VWAP - dalsie zavretie za nim proti obchodu ju zatvori</summary>
        private bool _exitReady;
        /// <summary>posledny nakresleny bod ciary VWAP</summary>
        private bool _hasPoint;
        private long _pointMs;
        private double _pointValue;
        private int? _pointDay;

        public VwapOrbEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(VwapOrbConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public VwapOrbEngine(VwapOrbConfig cfg, InstrumentSpec inst, int chartTfMinutes)
            : base(cfg, inst, chartTfMinutes)
        {
            if (cfg.vwapStop || cfg.vwapTp)
                throw new NotSupportedException(
                    "VWAP ORB (C#): 'SL na dotyk VWAP' (vwapStop) a 'TP na cross VWAP' (vwapTp) C# port nema - "
                    + "stop posuvany s VWAP nepoznaju ani zive adaptery. Vypni ich, alebo pouzi Python 'vwaporb'.");
            _cfg = cfg;
            int start, end;
            string tz;
            cfg.Window(cfg.nyStartH * 60 + cfg.nyStartM, out start, out end, out tz);
            int? per = cfg.vwapPeriod != 0 ? (int?)cfg.vwapPeriod : null;
            Vwap = new SessionVwap(ChartTfMinutes, start, end, tz, per, cfg.vwapDriftBars + 2);
            _fastBars = Math.Max(1, cfg.vwapDriftBars * (per.HasValue ? per.Value / ChartTfMinutes : 1));
            VwapFast = new SessionVwap(ChartTfMinutes, start, end, tz, null, _fastBars + 2);
        }

        public override EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            // VWAP pred ORB: podmienka prerazenia sa pyta na hodnotu po zavreti tohto baru
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            // Mimo seansy VWAP by `Push` vratil vcerajsiu zamrznutu hodnotu - podla nej sa nevstupuje ani nevystupuje.
            double? value = Vwap.Push(bar);
            _vwapValue = Vwap.Live ? value : null;
            VwapFast.Push(bar);
            EngineOutput o = base.OnBar(bar, htf, ctx);
            if (_cfg.showVwap && Vwap.Updated && _vwapValue.HasValue) o.Drawings.AddRange(VwapDrawing(bar, _vwapValue.Value));
            if (_cfg.VwapExit) VwapExit(o, bar, ctx);
            return o;
        }

        /// <summary>Zavrie poziciu, ked cena od vstupu prerazi VWAP proti obchodu (Python `_vwap_exit`).</summary>
        private void VwapExit(EngineOutput o, Bar bar, MarketContext ctx)
        {
            double? vwap = _vwapValue;
            double pos = ctx.PositionSize;
            OrderIntent entry = null;
            foreach (OrderIntent i in o.Orders)
                if (i.Action == OrderAction.Entry) { entry = i; break; }
            if (pos == 0.0)
            {
                // nova pozicia z tohto baru: pripravena, ak signalny bar zavrel na spravnej strane
                bool l = entry != null && entry.Direction.HasValue && entry.Direction.Value == Direction.Long;
                _exitReady = entry != null && vwap.HasValue && (l ? bar.Close > vwap.Value : bar.Close < vwap.Value);
                return;
            }
            if (!vwap.HasValue || o.CloseSession) return;
            bool isLong = pos > 0.0;
            double buffer = _cfg.vwapExitAtr.Resolve(Inst, bar.Close, History.Atr);
            if (isLong ? bar.Close > vwap.Value : bar.Close < vwap.Value)
            {
                _exitReady = true;
                return;
            }
            bool wrong = isLong ? bar.Close < vwap.Value - buffer : bar.Close > vwap.Value + buffer;
            if (_exitReady && wrong)
            {
                o.CloseSession = true;
                foreach (string orderId in SortedIds(ctx))
                    o.Orders.Add(new OrderIntent(OrderAction.Close, orderId, History.BarIndex, "prerazenie VWAP proti obchodu"));
                _openSession = null;
                _exitReady = false;
            }
        }

        /// <summary>Pri `exitMode=vwap` bez pevneho ciela - ciel 100R, inak ciel ORB.</summary>
        protected override double TargetLevel(SessionState st, Direction direction, double entry, double slDistance, double atr)
        {
            if (_cfg.exitMode == VwapExitMode.Vwap)
            {
                double dist = slDistance * NoTpR;
                if (direction == Direction.Long) return entry + dist;
                return Math.Max(entry - dist, entry * 0.01);
            }
            return base.TargetLevel(st, direction, entry, slDistance, atr);
        }

        /// <summary>VWAP podla `vwapRule` v smere prerazenia (a pri `closeBeyondVwap` aj cena za VWAP).</summary>
        protected override bool BreakAllowed(SessionState st, Direction direction, Bar bar, double atr)
        {
            double? vwap = _vwapValue;
            if (!vwap.HasValue || !st.High.HasValue || !st.Low.HasValue) return false;
            bool isLong = direction == Direction.Long;
            bool candleOnly = _cfg.entryTiming == VwapEntryTiming.BreakCandle;
            if (candleOnly)
            {
                // ORB sa pyta len pri close za rangom - prve opytanie v smere je prerazovacia sviecka
                string key = st.Day + "|" + (isLong ? "L" : "S");
                if (_broke.Contains(key)) return false;
                _broke.Add(key);
            }
            if (_cfg.closeBeyondVwap && !(isLong ? bar.Close > vwap.Value : bar.Close < vwap.Value)) return false;
            if (_cfg.vwapRule == VwapRule.Direction)
            {
                double? change = VwapChange(_cfg.vwapDriftBars, candleOnly);
                if (!change.HasValue) return false;
                double need = _cfg.vwapDriftMinAtr.Resolve(Inst, vwap.Value, atr);
                return isLong ? change.Value > 0 && change.Value >= need : change.Value < 0 && -change.Value >= need;
            }
            double needBreak = _cfg.vwapBreakAtr.Resolve(Inst, bar.Close, atr);
            return isLong ? vwap.Value > st.High.Value + needBreak : vwap.Value < st.Low.Value - needBreak;
        }

        /// <summary>Zmena VWAP za `bars` period; pri `fallback` aj za menej period, alebo z barov grafu.</summary>
        private double? VwapChange(int bars, bool fallback)
        {
            double? change = Vwap.Change(bars);
            if (change.HasValue || !fallback) return change;
            for (int n = bars - 1; n > 0; n--)
            {
                change = Vwap.Change(n);
                if (change.HasValue) return change;
            }
            for (int n = _fastBars; n > 0; n--)
            {
                change = VwapFast.Change(n);
                if (change.HasValue) return change;
            }
            return null;
        }

        /// <summary>Usecka VWAP od posledneho bodu; bod je na konci baru, ked je hodnota znama.</summary>
        private List<DrawCommand> VwapDrawing(Bar bar, double vwap)
        {
            List<DrawCommand> list = new List<DrawCommand>();
            long endMs = bar.Time + _stepMs;
            bool had = _hasPoint;
            long prevMs = _pointMs;
            double prevValue = _pointValue;
            int? prevDay = _pointDay;
            _hasPoint = true;
            _pointMs = endMs;
            _pointValue = vwap;
            _pointDay = Vwap.Day;
            if (!had || prevDay != Vwap.Day) return list;
            DrawLine line = new DrawLine(VwapOrbKinds.Vwap, prevMs, prevValue, endMs, vwap, VwapColor);
            line.ObjId = "vo_vwap." + endMs.ToString(CultureInfo.InvariantCulture);
            line.Text = "VWAP";
            list.Add(line);
            return list;
        }
    }
}
