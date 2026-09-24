// Konfiguracia ORBNinja - zrkadlo `tradebot/strategies/orb/config.py`.
// Nazvy poli su ZAMERNE zhodne s Pine identifikatormi a s JSON profilmi, takze ten isty profil
// nacita Python aj C#. Defaulty = Pine defaulty. Rozsahy, popisy a validacia ostavaju v Pythone
// (webapp); tu sa cita len to, co engine potrebuje.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.OrbNinja
{
    /// <summary>Ktore seansy sa obchoduju ("both" / "ny" / "london").</summary>
    public enum OrbSessionMode { Both, Ny, London }

    public enum OrbDirection { Both, LongOnly, ShortOnly }

    /// <summary>close = vstup na zavreti sviecky za hranicou, retest = limitka na navrat k hranici,
    /// stop = stop order priamo na hranici.</summary>
    public enum OrbEntryMode { Close, Retest, Stop }

    public enum OrbSlMode { Opposite, Mid, RangePct, Atr, BreakCandle }

    public enum OrbTpMode { Rr, Measured, Atr }

    /// <summary>Jedna obchodna seansa - Python `SessionWindow` z configu ORB. Minuty su od polnoci
    /// v PASME seansy, nie v UTC - preto si kazda nesie svoje `Tz`.</summary>
    public sealed class OrbSession
    {
        public readonly string Key;
        public readonly string Title;
        public readonly string Tz;
        public readonly int StartMinutes;
        public readonly int RangeMinutes;
        public readonly int EndMinutes;

        public OrbSession(string key, string title, string tz, int startMinutes, int rangeMinutes, int endMinutes)
        {
            Key = key; Title = title; Tz = tz;
            StartMinutes = startMinutes; RangeMinutes = rangeMinutes; EndMinutes = endMinutes;
        }

        public int RangeEndMinutes { get { return StartMinutes + RangeMinutes; } }
    }

    public sealed class OrbConfig
    {
        // ---- seansy -----------------------------------------------------------
        public OrbSessionMode sessionMode = OrbSessionMode.Both;
        public int nyStartH = 9;
        public int nyStartM = 30;
        public int nyRangeMinutes = 15;
        public int nyEndH = 15;
        public int nyEndM = 55;
        public int lonStartH = 8;
        public int lonStartM = 0;
        public int lonRangeMinutes = 15;
        public int lonEndH = 16;
        public int lonEndM = 30;

        // ---- vstup ------------------------------------------------------------
        public OrbDirection tradeDirection = OrbDirection.Both;
        public OrbEntryMode entryMode = OrbEntryMode.Close;
        public SizeSpec breakBufferAtr = new SizeSpec(0.05, "atr");
        public int retestMaxBars = 10;
        public int entryWindowMinutes = 90;
        public int maxTradesPerDay = 1;

        // ---- filtre -----------------------------------------------------------
        public double minRangePct = 0.15;
        public double maxRangePct = 1.5;
        public bool useVolumeFilter = false;
        public int volSmaLen = 20;
        public double volMultiplier = 1.5;
        public int minClosePosPct = 50;
        public bool weekdaysOnly = true;

        // ---- stop loss --------------------------------------------------------
        public OrbSlMode slMode = OrbSlMode.Opposite;
        public double slRangePct = 50.0;
        public int atrLen = 14;
        public SizeSpec slAtrMult = new SizeSpec(1.0, "atr");
        public SizeSpec slBufferAtr = new SizeSpec(0.1, "atr");

        // ---- ciel -------------------------------------------------------------
        public OrbTpMode tpMode = OrbTpMode.Rr;
        public double rrRatio = 1.5;
        public double measuredMult = 1.0;
        public SizeSpec tpAtrMult = new SizeSpec(2.0, "atr");

        // ---- riadenie pozicie -------------------------------------------------
        public bool enableTrailing = false;
        public double trailActivationR = 1.0;
        public double trailOffsetR = 0.5;
        public bool closeAtSessionEnd = true;

        // ---- riziko -----------------------------------------------------------
        public double riskDollar = 100.0;

        // ---- vizualizacia -----------------------------------------------------
        public bool showRange = true;
        public bool showLevels = true;

        // ---- rozsirenia portu -------------------------------------------------
        /// <summary>Pine `tickDollarValue`; pouziva sa len s `legacyPineSizing`.</summary>
        public double? tickDollarValue = null;
        public bool legacyPineSizing = false;
        public SizeSpec minSlDistance = new SizeSpec(0.0, "pct");
        public double leverage = 1.0;

        // -------------------------------------------------------------------- //

        /// <summary>Povodna jednotka velkostnych poli - hole cislo v JSON znamena tuto jednotku.</summary>
        private static readonly Dictionary<string, string> SizeFields = new Dictionary<string, string>
        {
            { "minSlDistance", "pct" }, { "breakBufferAtr", "atr" }, { "slAtrMult", "atr" },
            { "slBufferAtr", "atr" }, { "tpAtrMult", "atr" },
        };

        public bool AllowLong { get { return tradeDirection != OrbDirection.ShortOnly; } }
        public bool AllowShort { get { return tradeDirection != OrbDirection.LongOnly; } }

        /// <summary>Zapnute seansy podla `sessionMode`, kazda s vlastnym pasmom a oknom.</summary>
        public OrbSession[] Sessions()
        {
            OrbSession ny = new OrbSession("ny", "New York", "America/New_York",
                nyStartH * 60 + nyStartM, nyRangeMinutes, nyEndH * 60 + nyEndM);
            OrbSession london = new OrbSession("london", "Londýn", "Europe/London",
                lonStartH * 60 + lonStartM, lonRangeMinutes, lonEndH * 60 + lonEndM);
            if (sessionMode == OrbSessionMode.Ny) return new[] { ny };
            if (sessionMode == OrbSessionMode.London) return new[] { london };
            return new[] { ny, london };
        }

        /// <summary>Velkost pozicie - jedine miesto, kde sa rozhoduje medzi Pine a opravenym vzorcom.</summary>
        public double PositionQty(InstrumentSpec inst, double riskAmount, double slDistance)
        {
            if (legacyPineSizing) return inst.QtyForRiskPine(riskAmount, slDistance, tickDollarValue ?? 0.0);
            return inst.QtyForRisk(riskAmount, slDistance);
        }

        // -------------------------------------------------------------------- //

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `ORBConfig.to_dict()`.
        /// Kluce s podtrznikom su metadata profilu; neznamy kluc sa ignoruje - validaciu robi Python.</summary>
        public static OrbConfig FromDict(Dictionary<string, object> data)
        {
            OrbConfig cfg = new OrbConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(OrbConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                f.SetValue(cfg, Convert(kv.Key, f.FieldType, kv.Value));
            }
            return cfg;
        }

        private static object Convert(string name, Type t, object raw)
        {
            if (t == typeof(SizeSpec)) return SizeSpec.Parse(raw, SizeFields[name]);
            if (t == typeof(bool)) return (bool)raw;
            if (t == typeof(int))
            {
                // dlzka rangu je v Pythone enum s hodnotou "15" / "30" / "60"
                string text = raw as string;
                if (text != null) return int.Parse(text, CultureInfo.InvariantCulture);
                return Json.ToInt(raw);
            }
            if (t == typeof(double)) return Json.ToDouble(raw);
            if (t == typeof(double?)) return raw == null ? (double?)null : Json.ToDouble(raw);
            string s = (string)raw;
            if (t == typeof(OrbSessionMode))
            {
                switch (s)
                {
                    case "both": return OrbSessionMode.Both;
                    case "ny": return OrbSessionMode.Ny;
                    case "london": return OrbSessionMode.London;
                }
            }
            if (t == typeof(OrbDirection))
            {
                switch (s)
                {
                    case "Both": return OrbDirection.Both;
                    case "Long only": return OrbDirection.LongOnly;
                    case "Short only": return OrbDirection.ShortOnly;
                }
            }
            if (t == typeof(OrbEntryMode))
            {
                switch (s)
                {
                    case "close": return OrbEntryMode.Close;
                    case "retest": return OrbEntryMode.Retest;
                    case "stop": return OrbEntryMode.Stop;
                }
            }
            if (t == typeof(OrbSlMode))
            {
                switch (s)
                {
                    case "opposite": return OrbSlMode.Opposite;
                    case "mid": return OrbSlMode.Mid;
                    case "range_pct": return OrbSlMode.RangePct;
                    case "atr": return OrbSlMode.Atr;
                    case "break_candle": return OrbSlMode.BreakCandle;
                }
            }
            if (t == typeof(OrbTpMode))
            {
                switch (s)
                {
                    case "rr": return OrbTpMode.Rr;
                    case "measured": return OrbTpMode.Measured;
                    case "atr": return OrbTpMode.Atr;
                }
            }
            throw new ArgumentException("pole " + name + ": neznama hodnota '" + s + "'");
        }
    }

    /// <summary>Druhy kresieb ORB - retazce zhodne s `tradebot/strategies/orb/drawing.py`.</summary>
    public static class OrbKinds
    {
        public const string Box = "orb_box";
        public const string High = "orb_high";
        public const string Low = "orb_low";
        public const string Entry = "orb_entry";
    }
}
