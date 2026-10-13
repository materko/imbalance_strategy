// Konfiguracia VWAP ORB (C#) - zrkadlo `tradebot/strategies/vwaporb/config.py`.
// ORB (vsetky polia `OrbConfig`) + VWAP; defaulty ORB zmenene tam, kde by branili zadaniu - rovnako
// ako v Pythone (len New York, bez filtrov sirky rangu a polohy close, bez 90-minutoveho okna).
using System;
using System.Collections.Generic;
using TradeBot.Core;
using TradeBot.Strategies.OrbNet;

namespace TradeBot.Strategies.VwapOrbNet
{
    /// <summary>Odkial sa VWAP pocita: od 9:30 NY, seansovy CME (18:00 NY) alebo den od 00:00 UTC.</summary>
    public enum VwapAnchor { NyOpen, Session, UtcDay }

    /// <summary>break = VWAP za rangom; direction = staci prerazenie cenou, VWAP len smeruje rovnako.</summary>
    public enum VwapRule { Break, Direction }

    /// <summary>any = prva sviecka, kde plati oboje; break_candle = len prerazovacia sviecka.</summary>
    public enum VwapEntryTiming { Any, BreakCandle }

    /// <summary>tp = ciel ORB; vwap = bez ciela, do prerazenia VWAP proti obchodu; tp_vwap = co pride skor.</summary>
    public enum VwapExitMode { Tp, Vwap, TpVwap }

    public sealed class VwapOrbConfig : OrbConfig
    {
        // ---- VWAP -------------------------------------------------------------
        public VwapAnchor vwapAnchor = VwapAnchor.NyOpen;
        /// <summary>Python `VwapPeriod`: 15 = z 15m sviecok, 0 = "chart" (z barov grafu).</summary>
        public int vwapPeriod = 15;
        public VwapRule vwapRule = VwapRule.Break;
        public VwapEntryTiming entryTiming = VwapEntryTiming.Any;
        public SizeSpec vwapBreakAtr = new SizeSpec(0.0, "atr");
        public bool closeBeyondVwap = false;
        public int vwapDriftBars = 2;
        public SizeSpec vwapDriftMinAtr = new SizeSpec(0.0, "atr");
        // ---- vystup cez VWAP --------------------------------------------------
        public VwapExitMode exitMode = VwapExitMode.Tp;
        public SizeSpec vwapExitAtr = new SizeSpec(0.0, "atr");
        /// <summary>Stop posuvany s VWAP - v C# porte nie je (pozri `VwapOrbEngine`), engine ho odmietne.</summary>
        public bool vwapStop = false;
        public SizeSpec vwapStopAtr = new SizeSpec(0.0, "atr");
        /// <summary>TP na cross VWAP - v C# porte nie je, engine ho odmietne.</summary>
        public bool vwapTp = false;
        public SizeSpec vwapTpAtr = new SizeSpec(0.0, "atr");
        public bool showVwap = true;

        /// <summary>Zmenene defaulty ORB (Python `VwapOrbConfig`).</summary>
        public VwapOrbConfig()
        {
            sessionMode = OrbSessionMode.Ny;
            breakBufferAtr = new SizeSpec(0.0, "atr");
            entryWindowMinutes = 0;
            minRangePct = 0.0;
            maxRangePct = 10.0;
            minClosePosPct = 0;
        }

        public bool VwapExit { get { return exitMode != VwapExitMode.Tp; } }

        /// <summary>Python `VwapAnchor.window`: (zaciatok, koniec v minutach od polnoci, pasmo).</summary>
        public void Window(int startMinutes, out int start, out int end, out string tz)
        {
            if (vwapAnchor == VwapAnchor.Session) { start = 18 * 60; end = 17 * 60; tz = "America/New_York"; return; }
            if (vwapAnchor == VwapAnchor.UtcDay) { start = 0; end = 24 * 60; tz = "UTC"; return; }
            start = startMinutes; end = 16 * 60; tz = "America/New_York";
        }

        public static new VwapOrbConfig FromDict(Dictionary<string, object> data)
        {
            return Fill(new VwapOrbConfig(), data);
        }

        protected override string SizeUnit(string name)
        {
            switch (name)
            {
                case "vwapBreakAtr":
                case "vwapDriftMinAtr":
                case "vwapExitAtr":
                case "vwapStopAtr":
                case "vwapTpAtr":
                    return "atr";
            }
            return base.SizeUnit(name);
        }

        protected override object ConvertField(string name, Type t, object raw)
        {
            if (name == "vwapPeriod")
            {
                string p = raw as string;
                if (p == "chart") return 0;
                return p != null ? int.Parse(p, System.Globalization.CultureInfo.InvariantCulture) : Json.ToInt(raw);
            }
            string s = raw as string;
            if (t == typeof(VwapAnchor))
            {
                if (s == "ny_open") return VwapAnchor.NyOpen;
                if (s == "session") return VwapAnchor.Session;
                if (s == "utc_day") return VwapAnchor.UtcDay;
            }
            else if (t == typeof(VwapRule))
            {
                if (s == "break") return VwapRule.Break;
                if (s == "direction") return VwapRule.Direction;
            }
            else if (t == typeof(VwapEntryTiming))
            {
                if (s == "any") return VwapEntryTiming.Any;
                if (s == "break_candle") return VwapEntryTiming.BreakCandle;
            }
            else if (t == typeof(VwapExitMode))
            {
                if (s == "tp") return VwapExitMode.Tp;
                if (s == "vwap") return VwapExitMode.Vwap;
                if (s == "tp_vwap") return VwapExitMode.TpVwap;
            }
            else
            {
                return base.ConvertField(name, t, raw);
            }
            throw new ArgumentException("pole " + name + ": neznama hodnota '" + s + "'");
        }
    }

    /// <summary>Druhy kresieb VWAP ORB - retazce zhodne s `tradebot/strategies/vwaporb/drawing.py`.</summary>
    public static class VwapOrbKinds
    {
        public const string Vwap = "vo_vwap";
    }
}
