// Konfiguracia SIGMA BREAKOUT 1.0 (C#) - zrkadlo `tradebot/strategies/sigma/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.SigmaNet
{
    public sealed class SigmaConfig
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
        // ---- pasmo ------------------------------------------------------------
        public int nSigmaDays = 14;
        public double bandMult = 1.0;
        public bool useVwap = false;
        // ---- stop a velkost ---------------------------------------------------
        public double slPct = 0.0;
        public bool useCloseAtEnd = true;
        public bool fixedQty = true;
        public double qty = 1.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        public double riskDollar = 500.0;
        // ---- rozsirenia portu -------------------------------------------------
        public double leverage = 1.0;

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static SigmaConfig FromDict(Dictionary<string, object> data)
        {
            SigmaConfig cfg = new SigmaConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(SigmaConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
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

    /// <summary>Druhy kresieb Sigma - retazce zhodne s `tradebot/strategies/sigma/drawing.py`.</summary>
    public static class SigmaKinds
    {
        public const string Band = "sigma_band";
        public const string Entry = "sigma_entry";
    }
}
