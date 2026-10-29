// Konfiguracia SPRAVY (C#) - zrkadlo `tradebot/strategies/spravy/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita
// `EntryLayers` v C# jadre priamo z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.SpravyNet
{
    public sealed class SpravyConfig
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
        public bool fixedQty = false;
        public double qty = 1.0;
        public bool skipOverRisk = false;   // strop straty - cita ho EntrySizingEngine v EntryLayers.cs
        // ---- TREND / FADE -----------------------------------------------------
        public string trendEvents = "FOMC,PCE";
        public int trendFrom = 15;
        public int trendTo = 60;
        public int trendHold = 240;
        public string fadeEvents = "CPI,PPI,JOLTS";
        public int fadeFrom = 0;
        public int fadeTo = 60;
        public int fadeHold = 60;
        // ---- stop a ciel ------------------------------------------------------
        public int atrLen = 14;
        public SizeSpec slBuffer = new SizeSpec(1.0, "atr");
        public double trendStopLeg = 0.0;
        public double fadeStopLeg = 10.0;
        public SizeSpec minLeg = new SizeSpec(0.0, "atr");
        public double tpR = 0.0;
        public bool allowLong = true;
        public bool allowShort = true;
        // ---- kalendar ---------------------------------------------------------
        public string newsAdd = "";
        public string newsSkip = "";
        // ---- velkost z rizika -------------------------------------------------
        public double riskDollar = 500.0;
        public double sizeMinRisk = 0.0;
        // ---- vizualizacia / port ---------------------------------------------
        public bool showLegs = true;
        public double leverage = 1.0;

        private static readonly Dictionary<string, string> SizeUnits = new Dictionary<string, string>
        {
            { "slBuffer", "atr" }, { "minLeg", "atr" },
        };

        public static HashSet<string> Types(string text)
        {
            HashSet<string> s = new HashSet<string>();
            foreach (string part in (text ?? "").Split(','))
            {
                string t = part.Trim().ToUpperInvariant();
                if (t.Length > 0) s.Add(t);
            }
            return s;
        }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static SpravyConfig FromDict(Dictionary<string, object> data)
        {
            SpravyConfig cfg = new SpravyConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(SpravyConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(SizeSpec)) f.SetValue(cfg, SizeSpec.Parse(raw, SizeUnits[kv.Key]));
                else if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            HashSet<string> known = new HashSet<string>();
            foreach (SpravyCalendar.Ev e in SpravyCalendar.Events) known.Add(e.Type);
            HashSet<string> trend = Types(cfg.trendEvents), fade = Types(cfg.fadeEvents);
            foreach (string t in trend)
            {
                if (!known.Contains(t)) throw new ArgumentException("SPRÁVY: neznámy typ správy " + t);
                if (fade.Contains(t)) throw new ArgumentException("SPRÁVY: typ nemôže byť naraz TREND aj FADE: " + t);
            }
            foreach (string t in fade)
                if (!known.Contains(t)) throw new ArgumentException("SPRÁVY: neznámy typ správy " + t);
            return cfg;
        }
    }

    /// <summary>Druhy kresieb - zhodne s `tradebot/strategies/spravy/drawing.py`.</summary>
    public static class SpravyKinds
    {
        public const string Leg = "sp_leg";
        public const string Entry = "sp_entry";
    }
}
