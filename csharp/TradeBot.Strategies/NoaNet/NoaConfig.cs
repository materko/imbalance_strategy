// Konfiguracia NOA 1.0 (C#) - zrkadlo `tradebot/strategies/noa/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.NoaNet
{
    public sealed class NoaConfig
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
        // ---- pasmo sumu -------------------------------------------------------
        public int lookbackDays = 14;
        public double volMult = 1.0;
        public bool gapAdjust = true;
        // ---- kontroly ---------------------------------------------------------
        public int checkEvery = 30;
        public int lastEntryMin = 360;
        public bool trailVwap = true;
        // ---- poistka, smer, pocet ---------------------------------------------
        public double hardStopPct = 1.0;
        /// <summary>Python `TradeDirection`: "Both" / "Long only" / "Short only".</summary>
        public string tradeDirection = "Both";
        public int maxTradesPerDay = 10;
        public bool weekdaysOnly = true;
        // ---- velkost ----------------------------------------------------------
        public bool fixedQty = true;
        public double qty = 1.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        public double riskDollar = 100.0;
        // ---- vizualizacia -----------------------------------------------------
        public bool showLevels = true;
        public bool showVwap = true;
        // ---- rozsirenia portu -------------------------------------------------
        public double leverage = 1.0;

        public bool AllowLong { get { return tradeDirection != "Short only"; } }
        public bool AllowShort { get { return tradeDirection != "Long only"; } }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static NoaConfig FromDict(Dictionary<string, object> data)
        {
            NoaConfig cfg = new NoaConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(NoaConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
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

    /// <summary>Druhy kresieb NOA - retazce zhodne s `tradebot/strategies/noa/drawing.py`.</summary>
    public static class NoaKinds
    {
        public const string Level = "noa_level";
        public const string Vwap = "noa_vwap";
        public const string Stop = "noa_stop";
        public const string Entry = "noa_entry";
    }
}
