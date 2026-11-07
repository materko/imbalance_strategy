// Konfiguracia WILLIAMS %R LONG 1.0 (C#) - zrkadlo `tradebot/strategies/wpr/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.WprNet
{
    public sealed class WprConfig
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
        // ---- velkost ----------------------------------------------------------
        public bool fixedQty = true;
        public double qty = 1.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        // ---- Williams %R ------------------------------------------------------
        public int wprLen = 14;
        public double entryLevel = -90.0;
        public double exitLevel = -30.0;
        /// <summary>0 = nad high predoslej sviecky, 1 = %R, 2 = oboje</summary>
        public int exitMode = 2;
        public double stopPct = 0.0;
        public double riskDollar = 500.0;
        // ---- rozsirenia portu -------------------------------------------------
        public double leverage = 1.0;

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static WprConfig FromDict(Dictionary<string, object> data)
        {
            WprConfig cfg = new WprConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(WprConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
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

    /// <summary>Druhy kresieb Williams %R - retazce zhodne s `tradebot/strategies/wpr/drawing.py`.</summary>
    public static class WprKinds
    {
        public const string Entry = "wpr_entry";
    }
}
