// Konfiguracia IB RETRACE 1.0 (C#) - zrkadlo `tradebot/strategies/ibret/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.IbRetNet
{
    public sealed class IbRetConfig
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
        // ---- Initial Balance a prieraz (New York, HHMM) -------------------------
        public int ibStart = 930;
        public int ibMinutes = 60;
        public int breakFrom = 1030;
        public int breakTo = 1125;
        public bool tradeMon = true;
        public bool tradeTue = true;
        public bool tradeWed = true;
        public bool tradeThu = true;
        public bool tradeFri = true;
        public double minIbPoints = 0.0;
        public double maxIbPoints = 0.0;
        /// <summary>Python `TradeDirection`: "Both" / "Long only" / "Short only".</summary>
        public string tradeDirection = "Both";
        // ---- vstup a urovne (zlomok sirky IB od prerazenej hrany) ----------------
        /// <summary>Python `EntryMode`: "pullback" / "breakout".</summary>
        public string entryMode = "pullback";
        public double entryRetr = 0.25;
        public double slRetr = 0.8;
        public int slBufferTicks = 0;
        public int lastEntry = 1330;
        // ---- ciel a koniec ------------------------------------------------------
        /// <summary>Python `TpMode`: "ext" / "rr".</summary>
        public string tpMode = "ext";
        public double tpExt = 0.5;
        public double rr = 1.0;
        public double minRR = 0.5;
        public bool closeAtEnd = true;
        public int exitTime = 1600;
        // ---- velkost ----------------------------------------------------------
        public bool fixedQty = false;
        public double qty = 1.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        public double riskDollar = 250.0;
        // ---- vizualizacia a rozsirenia portu -------------------------------------
        public bool drawRange = true;
        public double leverage = 1.0;

        public bool AllowLong { get { return tradeDirection != "Short only"; } }
        public bool AllowShort { get { return tradeDirection != "Long only"; } }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static IbRetConfig FromDict(Dictionary<string, object> data)
        {
            IbRetConfig cfg = new IbRetConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(IbRetConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            ConfigChoice.Check("tradeDirection", cfg.tradeDirection, "Both", "Long only", "Short only");
            ConfigChoice.Check("entryMode", cfg.entryMode, "pullback", "breakout");
            ConfigChoice.Check("tpMode", cfg.tpMode, "ext", "rr");
            if (cfg.slRetr <= cfg.entryRetr)
                throw new ArgumentException("IB RETRACE: slRetr musi byt hlbsie nez entryRetr");
            return cfg;
        }
    }

    /// <summary>Druhy kresieb IB RETRACE - retazce zhodne s `tradebot/strategies/ibret/drawing.py`.</summary>
    public static class IbRetKinds
    {
        public const string Zone = "ibret_zone";
        public const string Entry = "ibret_entry";
    }
}
