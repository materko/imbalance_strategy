// Konfiguracia MTK ZONE (C#) - zrkadlo `tradebot/strategies/mtkzone/config.py`.
// Nazvy poli su zhodne s JSON profilmi. Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...)
// cita `EntryLayers` v C# jadre priamo z configu - tu su kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.MtkZoneNet
{
    public sealed class MtkZoneConfig
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
        // ---- 1 zony - odkial ----------------------------------------------------
        public bool useZ1 = true;
        public int zoneTf1 = 5;
        public bool useZ2 = false;
        public int zoneTf2 = 15;
        public bool useClassic = true;
        public bool usePeak = true;
        public bool useVolSurge = true;
        public bool usePocZone = false;
        public int pocEvery = 10;
        // ---- 2 zony - pravidla --------------------------------------------------
        public int minConf = 2;
        public double impMult = 1.5;
        public double volSpike = 2.0;
        public double impMultVol = 0.5;
        public int baseMax = 3;
        public double baseBodyMax = 0.6;
        public double minScore = 40.0;
        public int maxZones = 3;
        public int atrLen = 14;
        public int volLen = 20;
        // ---- 3 volume profil ----------------------------------------------------
        public int lookback = 50;
        public int rows = 40;
        public double peakMin = 3.0;
        // ---- 4 modely -----------------------------------------------------------
        public bool useLimit = true;
        public bool useIBS = false;
        public bool usePin = false;
        public int modelBars = 30;
        public int imbLookback = 20;
        public SizeSpec minImbSize = new SizeSpec(8.0, "abs");
        public int imbMaxDistTicks = 40;
        public int st1Max = 1;
        public int st2Max = 10;
        public int st2ConfTicks = 6;
        public int st3Max = 4;
        public int st5Max = 4;
        public int ibsSlLookback = 10;
        public double pbRatio = 4.0;
        public double pbBodyPos = 20.0;
        public SizeSpec pbMinRange = new SizeSpec(4.0, "abs");
        // ---- 5 obchod -----------------------------------------------------------
        public string tradeDirection = "Both";
        public double rrRatio = 1.0;
        public int slBufTicks = 0;
        public bool fixedQty = true;
        public double qty = 1.0;
        public double riskDollar = 400.0;
        public bool skipOverRisk = false;
        public int maxRiskTicks = 0;
        public int minGap = 0;
        public double maxDist = 0.0;
        // ---- 6 filtre -----------------------------------------------------------
        public string vwapMode = "off";
        public string vwapAnchor = "day";
        public bool useSess = false;
        public int sessStart = 930;
        public int sessEnd = 1600;
        public int maxZoneAge = 0;
        public double minEntryScore = 0.0;
        // ---- 7 zobrazenie -------------------------------------------------------
        public bool showZones = true;
        public bool showIbsDraw = true;
        public double leverage = 1.0;

        public bool AllowLong { get { return tradeDirection != "Short only"; } }
        public bool AllowShort { get { return tradeDirection != "Long only"; } }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static MtkZoneConfig FromDict(Dictionary<string, object> data)
        {
            MtkZoneConfig cfg = new MtkZoneConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(MtkZoneConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                object raw = kv.Value;
                if (f.FieldType == typeof(bool)) f.SetValue(cfg, (bool)raw);
                else if (f.FieldType == typeof(int)) f.SetValue(cfg, Json.ToInt(raw));
                else if (f.FieldType == typeof(double)) f.SetValue(cfg, Json.ToDouble(raw));
                else if (f.FieldType == typeof(SizeSpec)) f.SetValue(cfg, SizeSpec.Parse(raw, "abs"));
                else f.SetValue(cfg, Convert.ToString(raw, CultureInfo.InvariantCulture));
            }
            ConfigChoice.Check("tradeDirection", cfg.tradeDirection, "Both", "Long only", "Short only");
            ConfigChoice.Check("vwapMode", cfg.vwapMode, "off", "with", "against");
            ConfigChoice.Check("vwapAnchor", cfg.vwapAnchor, "day", "ny", "week", "month");
            return cfg;
        }
    }

    /// <summary>Druhy kresieb MTK ZONE - retazce zhodne s `tradebot/strategies/mtkzone/drawing.py`.</summary>
    public static class MtkZoneKinds
    {
        public const string Zone = "mz_zone";
        public const string Ifvg = "mz_ifvg";
        public const string Cb = "mz_cb";
        public const string Retest = "mz_retest";
    }
}
