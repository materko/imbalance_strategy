// Konfiguracia SD ZONY EURUSD (C#) - zrkadlo `tradebot/strategies/sdeur/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.SdEurNet
{
    public sealed class SdEurConfig
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
        // ---- zona (vyssi TF) --------------------------------------------------
        public int zoneTF = 60;
        public int atrLen = 14;
        public int baseMaxBars = 4;
        public SizeSpec baseMax = new SizeSpec(3.0, "atr");
        public int extremeBars = 4;
        public SizeSpec depMin = new SizeSpec(1.0, "atr");
        public int depMaxBars = 8;
        public SizeSpec minZoneHeight = new SizeSpec(0.0, "atr");
        public SizeSpec maxZoneHeight = new SizeSpec(0.0, "atr");
        public int zoneMaxHours = 120;
        public bool useFormWindow = true;
        public int formStartH = 18;
        public int formEndH = 2;
        // ---- vstup ------------------------------------------------------------
        public bool allowLong = true;
        public bool allowShort = true;
        public int entryStartH = 2;
        public int entryStartM = 0;
        public int entryEndH = 11;
        public int entryEndM = 0;
        public double entryDepthPct = 0.0;
        public int maxTradesPerDay = 0;
        // ---- stop a ciel ------------------------------------------------------
        public SizeSpec slBuffer = new SizeSpec(0.25, "atr");
        public double rrRatio = 1.5;
        public int maxHoldHours = 48;
        // ---- velkost ----------------------------------------------------------
        public bool fixedQty = false;
        public double qty = 1.0;
        public double riskDollar = 500.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        // ---- vizualizacia / port ---------------------------------------------
        public bool showZones = true;
        public double leverage = 1.0;

        private static readonly Dictionary<string, string> SizeUnits = new Dictionary<string, string>
        {
            { "baseMax", "atr" }, { "depMin", "atr" }, { "minZoneHeight", "atr" }, { "maxZoneHeight", "atr" },
            { "slBuffer", "atr" },
        };

        public int EntryStart { get { return entryStartH * 60 + entryStartM; } }
        public int EntryEnd { get { return entryEndH * 60 + entryEndM; } }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static SdEurConfig FromDict(Dictionary<string, object> data)
        {
            SdEurConfig cfg = new SdEurConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(SdEurConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(SizeSpec)) f.SetValue(cfg, SizeSpec.Parse(raw, SizeUnits[kv.Key]));
                else if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            return cfg;
        }
    }

    /// <summary>Druhy kresieb - zhodne s `tradebot/strategies/sdeur/drawing.py`.</summary>
    public static class SdEurKinds
    {
        public const string Supply = "se_supply";
        public const string Demand = "se_demand";
        public const string Entry = "se_entry";
    }
}
