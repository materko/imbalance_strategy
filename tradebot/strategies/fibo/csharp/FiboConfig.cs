// Konfiguracia Fibo 1.0 (C#) - zrkadlo `tradebot/strategies/fibo/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryOrderType...) a velkosti pozicie
// (fixedQty, qty, skipOverRisk) cita `EntryLayers` v C# jadre priamo z configu - tu su kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.FiboNet
{
    public sealed class FiboConfig
    {
        // ---- obaly vstupov a velkost pozicie (C# `EntryLayers`) ---------------
        public string trendFilter = "off";
        public int trendEmaLen = 200;
        public int trendTF = 0;
        public string volFilter = "off";
        public int volLookback = 100;
        public string entryOrderType = "market";
        public int limitOffsetPct = 50;
        public int limitValidBars = 3;
        public bool limitKeepRR = true;
        public bool fixedQty = false;
        public double qty = 1.0;
        public bool skipOverRisk = false;
        // ---- noha (impulz) ----------------------------------------------------
        public int swingTF = 15;
        public int swingLen = 3;
        public SizeSpec legMinAtr = new SizeSpec(3.0, "atr");
        public bool requireBreak = true;
        public int legMaxBars = 0;
        public int atrLen = 14;
        // ---- urovne navratu ---------------------------------------------------
        public bool use382 = true;
        public bool use50 = true;
        public bool use618 = true;
        public bool use786 = true;
        /// <summary>Python `LevelMode`: "zone" / "levels".</summary>
        public string levelMode = "zone";
        public SizeSpec levelTolAtr = new SizeSpec(0.25, "atr");
        public int setupMaxBars = 60;
        // ---- vstup ------------------------------------------------------------
        /// <summary>Python `EntryModel`: "imbalance" / "pinbar" / "any".</summary>
        public string entryModel = "any";
        public int signalMaxBars = 3;
        public SizeSpec imbMinSizeAtr = new SizeSpec(0.05, "atr");
        public int pbWickPct = 60;
        public int pbBodyPct = 30;
        /// <summary>Python `TradeDirection`: "Both" / "Long only" / "Short only".</summary>
        public string tradeDirection = "Both";
        public int maxTradesPerDay = 3;
        // ---- filtre -----------------------------------------------------------
        public bool weekdaysOnly = true;
        public bool useTradeWindow = false;
        public string tradeTZ = "America/New_York";
        public int tradeStartH = 3;
        public int tradeStartM = 0;
        public int tradeEndH = 16;
        public int tradeEndM = 0;
        // ---- stop a ciel ------------------------------------------------------
        /// <summary>Python `SlMode`: "leg" / "pullback".</summary>
        public string slMode = "leg";
        public SizeSpec slBufferAtr = new SizeSpec(0.1, "atr");
        public SizeSpec slBufferPoints = new SizeSpec(0.0, "abs");
        /// <summary>Python `TpMode`: "extension" / "rr".</summary>
        public string tpMode = "extension";
        public double tpExtensionPct = 27.0;
        public double rrRatio = 2.0;
        public double minRR = 0.5;
        public int maxHoldBars = 0;
        // ---- riziko -----------------------------------------------------------
        public double riskDollar = 100.0;
        // ---- vizualizacia / port ---------------------------------------------
        public bool showFibo = true;
        public double? tickDollarValue = null;
        public bool legacyPineSizing = false;
        public SizeSpec minSlDistance = new SizeSpec(0.0, "pct");
        public double leverage = 1.0;

        private static readonly Dictionary<string, string> SizeUnits = new Dictionary<string, string>
        {
            { "legMinAtr", "atr" }, { "levelTolAtr", "atr" }, { "imbMinSizeAtr", "atr" },
            { "slBufferAtr", "atr" }, { "slBufferPoints", "abs" }, { "minSlDistance", "pct" },
        };

        public bool AllowLong { get { return tradeDirection != "Short only"; } }
        public bool AllowShort { get { return tradeDirection != "Long only"; } }
        public int WindowStart { get { return tradeStartH * 60 + tradeStartM; } }
        public int WindowEnd { get { return tradeEndH * 60 + tradeEndM; } }

        /// <summary>Zapnute urovne navratu (podiel nohy), vzostupne - Python `levels()`.</summary>
        public List<double> Levels()
        {
            List<double> l = new List<double>();
            if (use382) l.Add(0.382);
            if (use50) l.Add(0.5);
            if (use618) l.Add(0.618);
            if (use786) l.Add(0.786);
            return l;
        }

        /// <summary>Python `position_qty`.</summary>
        public double PositionQty(InstrumentSpec inst, double risk, double sl)
        {
            if (legacyPineSizing) return inst.QtyForRiskPine(risk, sl, tickDollarValue.HasValue ? tickDollarValue.Value : 0.0);
            return inst.QtyForRisk(risk, sl);
        }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static FiboConfig FromDict(Dictionary<string, object> data)
        {
            FiboConfig cfg = new FiboConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(FiboConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(SizeSpec)) f.SetValue(cfg, SizeSpec.Parse(raw, SizeUnits[kv.Key]));
                else if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else if (f.FieldType == typeof(double?)) f.SetValue(cfg, raw == null ? (double?)null : Json.ToDouble(raw));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            ConfigChoice.Check("levelMode", cfg.levelMode, "zone", "levels");
            ConfigChoice.Check("entryModel", cfg.entryModel, "imbalance", "pinbar", "any");
            ConfigChoice.Check("slMode", cfg.slMode, "leg", "pullback");
            ConfigChoice.Check("tpMode", cfg.tpMode, "extension", "rr");
            ConfigChoice.Check("tradeDirection", cfg.tradeDirection, "Both", "Long only", "Short only");
            return cfg;
        }
    }

    /// <summary>Druhy kresieb - zhodne s `tradebot/strategies/fibo/drawing.py`.</summary>
    public static class FiboKinds
    {
        public const string Leg = "fib_leg";
        public const string Level = "fib_level";
        public const string Entry = "fib_entry";
    }
}
