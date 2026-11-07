// Konfiguracia Volt Break (C#) - zrkadlo `tradebot/strategies/voltbreak/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.VoltBreakNet
{
    public sealed class VoltBreakConfig
    {
        public const string AtrSession = "Seansa 0:00–16:00 CT (ako vo videu)";
        public const string AtrDaily = "Denné sviečky burzy";

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
        // ---- velkost (obal EntrySizingEngine) ---------------------------------
        public bool fixedQty = false;
        public double qty = 1.0;
        public bool skipOverRisk = false;
        // ---- noise a ATR ------------------------------------------------------
        public double noisePct = 30.0;
        public int atrLen = 14;
        public int avgLen = 15;
        public string atrSource = "Seansa 0:00–16:00 CT (ako vo videu)";
        // ---- ciel, stop, okno -------------------------------------------------
        public double tpUsd = 800.0;
        public double slUsd = 1500.0;
        public int maxTrades = 3;
        public int startHHMM = 1000;
        public int endHHMM = 1430;
        public bool useTimeExit = true;
        public double usdPerPoint = 20.0;
        public double riskDollar = 150.0;
        public bool legacyPineSizing = false;
        // ---- rozsirenia portu a vizualizacia ----------------------------------
        public double leverage = 1.0;
        public bool showLevels = true;

        public double TpPoints { get { return tpUsd / usdPerPoint; } }
        public double SlPoints { get { return slUsd / usdPerPoint; } }

        public static int HhmmMinutes(int hhmm) { return hhmm / 100 * 60 + hhmm % 100; }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static VoltBreakConfig FromDict(Dictionary<string, object> data)
        {
            VoltBreakConfig cfg = new VoltBreakConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(VoltBreakConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            ConfigChoice.Check("atrSource", cfg.atrSource, AtrSession, AtrDaily);
            return cfg;
        }
    }

    /// <summary>Druhy kresieb Volt Break - retazce zhodne s `tradebot/strategies/voltbreak/drawing.py`.</summary>
    public static class VoltBreakKinds
    {
        public const string Noise = "vb_noise";
        public const string Vwap = "vb_vwap";
        public const string Entry = "vb_entry";
    }
}
