// Konfiguracia TKS 1.0 (C#) - zrkadlo `tradebot/strategies/tks/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.TksNet
{
    public sealed class TksConfig
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
        // ---- NQ Kompas --------------------------------------------------------
        public int lookbackDays = 14;
        // ---- pravidla ---------------------------------------------------------
        public double loLevel = 35.0;
        public double hiLevel = 65.0;
        public int nConf = 3;
        public double rrRatio = 1.0;
        public int pivLen = 3;
        // ---- casove okno (minuty po 9:30 NY podla zavretia signalnej sviecky) ---
        public int entryStartMin = 0;
        public int entryEndMin = 390;
        public int pauseFromMin = 0;
        public int pauseToMin = 0;
        // ---- stop loss --------------------------------------------------------
        /// <summary>Python `SlMode`: "swing" / "atr" / "points".</summary>
        public string slMode = "swing";
        public double slAtrMult = 2.0;
        public double slPoints = 40.0;
        public int atrLen = 14;
        public double maxSlPoints = 0.0;
        public double maxSlAtr = 0.0;
        public int maxTradesPerSession = 0;
        public bool closeAtSessionEnd = false;
        /// <summary>Python `TradeDirection`: "Both" / "Long only" / "Short only".</summary>
        public string tradeDirection = "Both";
        // ---- velkost ----------------------------------------------------------
        public bool fixedQty = true;
        public double qty = 1.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        public double riskDollar = 100.0;
        // ---- rozsirenia portu -------------------------------------------------
        public double leverage = 1.0;

        public bool AllowLong { get { return tradeDirection != "Short only"; } }
        public bool AllowShort { get { return tradeDirection != "Long only"; } }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static TksConfig FromDict(Dictionary<string, object> data)
        {
            TksConfig cfg = new TksConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(TksConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            if (cfg.slMode != "swing" && cfg.slMode != "atr" && cfg.slMode != "points")
                throw new ArgumentException("TKS: neznamy slMode '" + cfg.slMode + "' (swing / atr / points)");
            ConfigChoice.Check("tradeDirection", cfg.tradeDirection, "Both", "Long only", "Short only");
            ConfigChoice.Check("slMode", cfg.slMode, "swing", "atr", "points");
            return cfg;
        }
    }

    /// <summary>Druhy kresieb TKS - retazce zhodne s `tradebot/strategies/tks/drawing.py`.</summary>
    public static class TksKinds
    {
        public const string Entry = "tks_entry";
    }
}
