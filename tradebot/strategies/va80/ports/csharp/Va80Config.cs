// Konfiguracia MTK RANGE 1.0 (C#) - zrkadlo `tradebot/strategies/va80/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.Va80Net
{
    public sealed class Va80Config
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
        // ---- value area -------------------------------------------------------
        public double vaPct = 70.0;
        public double vaBinPct = 0.03;
        public string vaMethod = "expand";
        // ---- navrat a vstup ---------------------------------------------------
        public int returnBarMin = 30;
        public double minOpenOutside = 0.0;
        public int lastEntry = 1200;
        public int exitTime = 1555;
        public bool requireOpenOutside = true;
        public int maxTradesPerDay = 1;
        public bool allowLong = true;
        public bool allowShort = true;
        // ---- stop, ciel, velkost ----------------------------------------------
        public string tpMode = "opp";
        public double rrRatio = 2.0;
        public double slBufferVa = 0.0;
        public double minRR = 0.5;
        public double maxStopAtr = 0.0;
        public bool fixedQty = true;
        public double qty = 1.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        public double riskDollar = 500.0;
        public bool showLevels = true;
        // ---- rozsirenia portu -------------------------------------------------
        public double leverage = 1.0;

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static Va80Config FromDict(Dictionary<string, object> data)
        {
            Va80Config cfg = new Va80Config();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(Va80Config).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            ConfigChoice.Check("vaMethod", cfg.vaMethod, "rank", "expand");
            ConfigChoice.Check("tpMode", cfg.tpMode, "poc", "opp", "mid", "rr");
            return cfg;
        }
    }

    /// <summary>Druhy kresieb VA NAVRAT - retazce zhodne s `tradebot/strategies/va80/drawing.py`.</summary>
    public static class Va80Kinds
    {
        public const string Level = "va80_level";
        public const string Entry = "va80_entry";
    }
}
