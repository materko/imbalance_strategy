// Konfiguracia ORB 15/5 1.0 (C#) - zrkadlo `tradebot/strategies/orb15/config.py` (aj rozsirenia MTK ORB: gapFilter,
// maxOrWidthMult, orWidthLookback, firstBreakOnly, entryAtLevel). Nazvy poli su zhodne s JSON profilmi. Polia obalov
// vstupov (trendFilter, entryConfirm, entryOrderType...) cita `EntryLayers` v C# jadre priamo z configu.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.Orb15Net
{
    public sealed class Orb15Config
    {
        // ---- obaly vstupov (C# `EntryLayers`) ---------------------------------
        public string trendFilter = "off";
        public int trendEmaLen = 200;
        public int trendTF = 0;
        public string volFilter = "off";
        public int volLookback = 100;
        public string entryConfirm = "none";
        public int confirmBars = 3;
        public double confirmImbMinAtr = 0.05;
        public int confirmPbWickPct = 60;
        public int confirmPbBodyPct = 30;
        public string entryOrderType = "market";
        public int limitOffsetPct = 50;
        public int limitValidBars = 3;
        public bool limitKeepRR = true;
        // ---- opening range ----------------------------------------------------
        public int orStart = 930;
        public int orMinutes = 15;
        public int lastEntry = 1600;
        // ---- vstup ------------------------------------------------------------
        public bool allowLong = true;
        public bool allowShort = true;
        public int maxTradesPerDay = 1;
        public bool useWickFilter = false;
        public double maxWickPct = 50.0;
        public bool useDailyBias = true;
        public int biasCheck = 915;
        public int gapFilter = 0;
        public double maxOrWidthMult = 0.0;
        public int orWidthLookback = 60;
        public bool firstBreakOnly = false;
        public bool entryAtLevel = false;
        // ---- ciel a koniec ----------------------------------------------------
        public int targetMode = 0;
        public double rr = 2.0;
        public double targetPoints = 40.0;
        public bool closeAtEnd = true;
        // ---- velkost ----------------------------------------------------------
        public bool fixedQty = false;
        public double qty = 1.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        public double riskDollar = 500.0;
        // ---- vizualizacia a rozsirenia portu -----------------------------------
        public bool drawRange = true;
        public double leverage = 1.0;

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static Orb15Config FromDict(Dictionary<string, object> data)
        {
            Orb15Config cfg = new Orb15Config();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(Orb15Config).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            return cfg;
        }
    }

    /// <summary>Druhy kresieb ORB 15/5 - retazce zhodne s `tradebot/strategies/orb15/drawing.py`.</summary>
    public static class Orb15Kinds
    {
        public const string Zone = "orb15_zone";
        public const string Entry = "orb15_entry";
    }
}
