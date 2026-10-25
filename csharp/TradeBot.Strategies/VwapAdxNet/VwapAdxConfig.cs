// Konfiguracia VWAP ADX Pullback (C#) - zrkadlo `tradebot/strategies/vwapadx/config.py`.
// Nazvy poli su zhodne s Pine identifikatormi a JSON profilmi; casy su HHMM v pasme America/Chicago.
// Polia obalov vstupov (trendFilter, entryConfirm, entryOrderType...) cita `EntryLayers` v C# jadre priamo
// z configu - tu su ako text kvoli zhode configu s Pythonom.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.VwapAdxNet
{
    public sealed class VwapAdxConfig
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
        // ---- opening range a cas ----------------------------------------------
        public int orStartHHMM = 830;
        public int orEndHHMM = 900;
        public int exitHHMM = 1555;
        /// <summary>casovy vystup (ako vo videu); vypnuty = drzi do SL / TP</summary>
        public bool useTimeExit = true;
        // ---- VWAP a ADX -------------------------------------------------------
        /// <summary>Python `VwapAnchor`: "RTH 8:30 CT" (od zaciatku rangu) alebo "Polnoc CT".</summary>
        public string vwapAnchor = "RTH 8:30 CT";
        public int adxLen = 14;
        public double adxMin = 20.0;
        // ---- TP / SL a obchody ------------------------------------------------
        public int tpBars = 5;
        public int slBars = 20;
        public int maxTrades = 1;
        // ---- rozsirenia portu -------------------------------------------------
        public double riskDollar = 100.0;
        // obal velkosti pozicie a strop straty (EntrySizingEngine v EntryLayers.cs) - cita ich z configu sam
        public bool fixedQty = false;
        public double qty = 1.0;
        public bool skipOverRisk = false;
        /// <summary>Doslovny Pine sizing: vzdy 1 kontrakt bez ohladu na riziko.</summary>
        public bool legacyPineSizing = false;
        public double leverage = 1.0;
        public bool showVwap = true;
        public bool showRange = true;

        public bool AnchorMidnight { get { return vwapAnchor == "Polnoc CT"; } }

        /// <summary>Pine `toMin`: 830 -> 510 minut od polnoci.</summary>
        public static int HhmmMinutes(int hhmm) { return hhmm / 100 * 60 + hhmm % 100; }

        public double PositionQty(InstrumentSpec inst, double riskAmount, double slDistance)
        {
            if (legacyPineSizing) return 1.0;
            return inst.QtyForRisk(riskAmount, slDistance);
        }

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `to_dict()`; kluce s podtrznikom su metadata.</summary>
        public static VwapAdxConfig FromDict(Dictionary<string, object> data)
        {
            VwapAdxConfig cfg = new VwapAdxConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(VwapAdxConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
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

    /// <summary>Druhy kresieb VWAP ADX - retazce zhodne s `tradebot/strategies/vwapadx/drawing.py`.</summary>
    public static class VwapAdxKinds
    {
        public const string Vwap = "va_vwap";
        public const string Range = "va_range";
        public const string Entry = "va_entry";
    }
}
