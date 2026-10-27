// Konfiguracia NY VA BREAKOUT (C#) - zrkadlo `tradebot/strategies/nyva/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.NyVaNet
{
    public sealed class NyVaConfig
    {
        // ---- obaly vstupov (C# `EntryLayers`) ---------------------------------
        public string trendFilter = "off";
        public int trendEmaLen = 100;
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
        // ---- fixed range (cas New York) ---------------------------------------
        public int rangeStartH = 9;
        public int rangeStartM = 30;
        public int rangeEndH = 10;
        public int rangeEndM = 30;
        public int profileRows = 60;
        public double valueAreaPct = 70.0;
        // ---- vstup ------------------------------------------------------------
        public bool allowLong = true;
        public bool allowShort = true;
        public int entryEndH = 16;
        public int entryEndM = 0;
        public int maxTradesPerDay = 1;
        public int confirmCloses = 1;
        /// <summary>Python `EntryMode`: "close" (market po prieraze) / "retest" (limitka na VAH / VAL).</summary>
        public string entryMode = "close";
        public int retestBars = 10;
        // ---- filtre -----------------------------------------------------------
        public bool useVwap = false;
        public double vaMinPoints = 0.0;
        public double vaMaxPoints = 0.0;
        public bool useShape = false;
        public double shapePocPct = 60.0;
        public double shapeVaPct = 55.0;
        public double shapeTailPct = 25.0;
        // ---- stop a ciel ------------------------------------------------------
        public double rrRatio = 1.0;
        public int slBufferTicks = 4;
        public double maxSlPoints = 0.0;
        public double maxSlAtr = 0.0;
        /// <summary>Python `SlCap`: "skip" / "cap".</summary>
        public string slCapMode = "skip";
        public bool useCloseTime = false;
        public int closeH = 15;
        public int closeM = 59;
        // ---- velkost ----------------------------------------------------------
        public bool fixedQty = false;
        public double qty = 1.0;
        public double riskDollar = 500.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        // ---- vizualizacia / port ---------------------------------------------
        public bool showLevels = true;
        public double leverage = 1.0;

        public int RangeStart { get { return rangeStartH * 60 + rangeStartM; } }
        public int RangeEnd { get { return rangeEndH * 60 + rangeEndM; } }
        public int EntryEnd { get { return entryEndH * 60 + entryEndM; } }
        public int CloseTime { get { return closeH * 60 + closeM; } }
        public bool Retest { get { return entryMode == "retest"; } }
        public bool CapSl { get { return slCapMode == "cap"; } }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static NyVaConfig FromDict(Dictionary<string, object> data)
        {
            NyVaConfig cfg = new NyVaConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(NyVaConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            if (cfg.entryMode != "close" && cfg.entryMode != "retest")
                throw new ArgumentException("NY VA: neznamy entryMode '" + cfg.entryMode + "' (close / retest)");
            if (cfg.slCapMode != "skip" && cfg.slCapMode != "cap")
                throw new ArgumentException("NY VA: neznamy slCapMode '" + cfg.slCapMode + "' (skip / cap)");
            return cfg;
        }
    }

    /// <summary>Druhy kresieb - zhodne s `tradebot/strategies/nyva/drawing.py`.</summary>
    public static class NyVaKinds
    {
        public const string Range = "nv_range";
        public const string Poc = "nv_poc";
        public const string Va = "nv_va";
        public const string Entry = "nv_entry";
    }
}
