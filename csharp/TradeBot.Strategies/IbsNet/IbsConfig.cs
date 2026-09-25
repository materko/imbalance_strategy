// Konfiguracia IBSNet - zrkadlo `tradebot/strategies/ibs/config.py`.
// Nazvy poli su ZAMERNE zhodne s Pine identifikatormi (camelCase) a s JSON profilmi, takze ten isty
// profil nacita Python aj C#. Defaulty = Pine defaulty. Rozsahy a popisy pre formular ostavaju
// v Pythone (webapp); tu sa cita len to, co engine potrebuje.
using System;
using System.Collections.Generic;
using System.Reflection;
using TradeBot.Core;

namespace TradeBot.Strategies.IbsNet
{
    public enum TradeDirectionMode { Both, LongOnly, ShortOnly, Indicator }

    public enum IndicatorAction { Both, LongOnly, ShortOnly, NoTrade }

    public enum PriceSource { Open, High, Low, Close, Hl2, Hlc3, Ohlc4, Hlcc4 }

    public sealed class IbsConfig
    {
        // ---- entry modely ---------------------------------------------------
        public bool enableImbEntry = true;
        public bool enablePinBarEntry = false;
        public bool enableEngulfingEntry = false;
        public double pbWickToBodyRatio = 4.0;
        public double pbBodyPositionPct = 20.0;
        public SizeSpec pbMinRangePoints = new SizeSpec(2.0, "abs");
        public SizeSpec engMinRangePoints = new SizeSpec(2.0, "abs");
        public int engSizeAvgLen = 10;
        public double engSizeMultiplier = 2.0;
        public int engTouchWindowBars = 3;
        public OrderType pbEngOrderType = OrderType.Market;

        // ---- trailing ---------------------------------------------------------
        public bool enableTrailing = false;
        public double trailActivationR = 1.0;
        public double trailOffsetR = 0.5;

        // ---- zakladne nastavenia ---------------------------------------------
        public bool weekdaysOnly = true;
        public bool enableTrading = true;
        public bool enableZoneDetection = true;
        public bool enableGapDetection = true;
        public bool enableSrTrading = false;
        public bool enableLqTrading = false;
        public bool closeAtSessionEnd = true;

        // ---- seansy -----------------------------------------------------------
        public bool sess1On = false;
        public string sess1TZ = "Europe/Prague";
        public int sess1ZoneStartH = 1, sess1ZoneStartM = 0, sess1ZoneEndH = 9, sess1ZoneEndM = 0;
        public int sess1TradeStartH = 2, sess1TradeStartM = 0, sess1TradeEndH = 5, sess1TradeEndM = 0;

        public bool sess2On = true;
        public string sess2TZ = "America/New_York";
        public int sess2ZoneStartH = 10, sess2ZoneStartM = 0, sess2ZoneEndH = 11, sess2ZoneEndM = 0;
        public int sess2TradeStartH = 10, sess2TradeStartM = 0, sess2TradeEndH = 15, sess2TradeEndM = 45;

        public bool sess3On = true;
        public string sess3TZ = "Europe/London";
        public int sess3ZoneStartH = 8, sess3ZoneStartM = 0, sess3ZoneEndH = 10, sess3ZoneEndM = 0;
        public int sess3TradeStartH = 8, sess3TradeStartM = 0, sess3TradeEndH = 11, sess3TradeEndM = 0;

        // ---- SD zony ----------------------------------------------------------
        public string zoneDetectionTF = "5";
        public int zoneValidHours = 6;
        public int maxSdZones = 200;
        public SnapMode snapMode = SnapMode.Floor;
        public bool invalidateOnFill = true;
        public bool useVolumeFilter = false;
        public bool volumeFilterBlockTrading = false;
        public int volSmaLen = 20;
        public double volMultiplier = 1.5;

        // ---- Market Structure ---------------------------------------------------
        public bool showMarketStructure = true;
        public int structureSwingLen = 5;
        public bool useStructureFilter = false;

        // ---- Support / Resistance -----------------------------------------------
        public bool showSR = true;
        public int srSwingLen = 10;
        public SizeSpec srClusterPoints = new SizeSpec(15.0, "abs");
        public int srMinTouches = 2;
        public int srMaxLevels = 10;
        public int srLookbackDays = 5;
        public int srZoneSaturationPct = 30;

        // ---- likvidita (sweep) ---------------------------------------------------
        public bool showLiqSweep = true;
        public int liqSweepLen = 10;
        public SizeSpec liqSweepMinWick = new SizeSpec(5.0, "abs");
        public int liqSweepConfirmBars = 2;
        public int liqStrengthLen = 50;

        // ---- Elliott Waves -------------------------------------------------------
        public bool showElliott = true;
        public int ewSwingLen = 8;
        public SizeSpec ewMinWavePoints = new SizeSpec(20.0, "abs");
        public bool ewShowLabels = true;
        public bool ewShowProjection = true;
        public int ewProjExtendBars = 40;
        public string ewLineColor = "#334155";

        // ---- vizualizacia ----------------------------------------------------------
        public bool showImbalance = true;

        // ---- casovanie vstupu, SL ----------------------------------------------------
        public int imbLookback = 20;
        public SizeSpec imbMaxDistTicks = new SizeSpec(100.0, "ticks");
        public SizeSpec minImbSizePoints = new SizeSpec(2.5, "abs");
        public int state1MaxBars = 10;
        public int state2MaxBars = 15;
        public SizeSpec state2ConfirmTicks = new SizeSpec(1.0, "ticks");
        public int state3MaxBars = 1;
        public int state4MaxBars = 10; // Pine ho nikde nepouziva ("Rezerva")
        public int state5MaxBars = 10;

        // ---- velkost pozicie a riziko ----------------------------------------------------
        public double rrRatio = 1.0;
        public int slLookback = 10;
        public SizeSpec slBufferTicks = new SizeSpec(2.0, "ticks");
        public double maxLossDollar = 350.0;
        public int maxDailyWins = 5;
        public TradeDirectionMode tradeDirection = TradeDirectionMode.Both;

        // ---- smer podla indikatorov (`tradeDirection = Indicator`) ------------------------
        public bool indSupertrend = true;
        public string stTimeframe = "60";
        public int stAtrPeriod = 10;
        public PriceSource stSource = PriceSource.Hl2;
        public double stMultiplier = 3.0;
        public bool stChangeAtr = true;
        public bool stShowSignals = true;
        public bool stHighlighting = true;

        public bool indAdx = false;
        public string adxTimeframe = "60";
        public int adxDiLength = 14;
        public int adxSmoothing = 14;
        public double adxThreshold = 20.0;
        public bool adxShowState = true;

        public IndicatorAction ruleStUp = IndicatorAction.LongOnly;
        public IndicatorAction ruleStDown = IndicatorAction.ShortOnly;
        public IndicatorAction ruleAdxUp = IndicatorAction.LongOnly;
        public IndicatorAction ruleAdxDown = IndicatorAction.ShortOnly;
        public IndicatorAction ruleAdxSide = IndicatorAction.NoTrade;
        public IndicatorAction ruleStUpAdxUp = IndicatorAction.LongOnly;
        public IndicatorAction ruleStUpAdxSide = IndicatorAction.NoTrade;
        public IndicatorAction ruleStUpAdxDown = IndicatorAction.NoTrade;
        public IndicatorAction ruleStDownAdxUp = IndicatorAction.NoTrade;
        public IndicatorAction ruleStDownAdxSide = IndicatorAction.NoTrade;
        public IndicatorAction ruleStDownAdxDown = IndicatorAction.ShortOnly;

        /// <summary>Pine `tickDollarValue`; pouziva sa len s `legacyPineSizing`.</summary>
        public double? tickDollarValue = null;
        public bool legacyPineSizing = false;
        public int atrLen = 14;
        public SizeSpec minSlDistance = new SizeSpec(0.0, "pct");
        public double leverage = 1.0;

        // -------------------------------------------------------------------- //

        /// <summary>Povodna Pine jednotka velkostnych poli - hole cislo v JSON znamena tuto jednotku.</summary>
        private static readonly Dictionary<string, string> SizeFields = new Dictionary<string, string>
        {
            { "minImbSizePoints", "abs" }, { "pbMinRangePoints", "abs" }, { "engMinRangePoints", "abs" },
            { "srClusterPoints", "abs" }, { "liqSweepMinWick", "abs" }, { "ewMinWavePoints", "abs" },
            { "imbMaxDistTicks", "ticks" }, { "state2ConfirmTicks", "ticks" }, { "slBufferTicks", "ticks" },
            { "minSlDistance", "pct" },
        };

        /// <summary>Hodnota z ponuky TF v minutach ("D" = 1440).</summary>
        public static int TimeframeOptionMinutes(string tf)
        {
            return tf == "D" ? 1440 : int.Parse(tf, System.Globalization.CultureInfo.InvariantCulture);
        }

        public bool Allows(Direction d)
        {
            if (tradeDirection == TradeDirectionMode.LongOnly) return d == Direction.Long;
            if (tradeDirection == TradeDirectionMode.ShortOnly) return d == Direction.Short;
            return true;
        }

        public static bool Allows(IndicatorAction a, Direction d)
        {
            if (a == IndicatorAction.Both) return true;
            if (a == IndicatorAction.LongOnly) return d == Direction.Long;
            if (a == IndicatorAction.ShortOnly) return d == Direction.Short;
            return false;
        }

        /// <summary>Velkost pozicie - jedine miesto, kde sa rozhoduje medzi Pine a opravenym vzorcom.</summary>
        public double PositionQty(InstrumentSpec inst, double riskAmount, double slDistance)
        {
            if (legacyPineSizing) return inst.QtyForRiskPine(riskAmount, slDistance, tickDollarValue ?? 0.0);
            return inst.QtyForRisk(riskAmount, slDistance);
        }

        public SessionClock BuildClock()
        {
            return new SessionClock(weekdaysOnly, new[]
            {
                new SessionSpec("session1", sess1On, sess1TZ,
                    new SessionWindow(sess1ZoneStartH, sess1ZoneStartM, sess1ZoneEndH, sess1ZoneEndM),
                    new SessionWindow(sess1TradeStartH, sess1TradeStartM, sess1TradeEndH, sess1TradeEndM)),
                new SessionSpec("session2", sess2On, sess2TZ,
                    new SessionWindow(sess2ZoneStartH, sess2ZoneStartM, sess2ZoneEndH, sess2ZoneEndM),
                    new SessionWindow(sess2TradeStartH, sess2TradeStartM, sess2TradeEndH, sess2TradeEndM)),
                new SessionSpec("session3", sess3On, sess3TZ,
                    new SessionWindow(sess3ZoneStartH, sess3ZoneStartM, sess3ZoneEndH, sess3ZoneEndM),
                    new SessionWindow(sess3TradeStartH, sess3TradeStartM, sess3TradeEndH, sess3TradeEndM)),
            });
        }

        // -------------------------------------------------------------------- //

        /// <summary>Profil (len odchylky od defaultov) alebo cely config z `IBSConfig.to_dict()`.
        /// Kluce s podtrznikom su metadata profilu; neznamy kluc sa ignoruje (zrusene polia starych
        /// profilov) - validaciu robi Python strana, ktora profil pise.</summary>
        public static IbsConfig FromDict(Dictionary<string, object> data)
        {
            IbsConfig cfg = new IbsConfig();
            foreach (KeyValuePair<string, object> kv in data)
            {
                if (kv.Key.StartsWith("_", StringComparison.Ordinal)) continue;
                FieldInfo f = typeof(IbsConfig).GetField(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (f == null) continue;
                f.SetValue(cfg, Convert(kv.Key, f.FieldType, kv.Value));
            }
            return cfg;
        }

        private static object Convert(string name, Type t, object raw)
        {
            if (t == typeof(SizeSpec)) return SizeSpec.Parse(raw, SizeFields[name]);
            if (t == typeof(bool)) return (bool)raw;
            if (t == typeof(int)) return Json.ToInt(raw);
            if (t == typeof(double)) return Json.ToDouble(raw);
            if (t == typeof(double?)) return raw == null ? (double?)null : Json.ToDouble(raw);
            if (t == typeof(string))
            {
                // TF polia su retazce, ale `--set stTimeframe=60` posle cislo
                if (raw is double) return Json.ToLong(raw).ToString(System.Globalization.CultureInfo.InvariantCulture);
                return (string)raw;
            }
            string s = (string)raw;
            if (t == typeof(SnapMode)) return EnumText.Snap(s);
            if (t == typeof(OrderType)) return EnumText.Order(s);
            if (t == typeof(TradeDirectionMode))
            {
                switch (s)
                {
                    case "Both": return TradeDirectionMode.Both;
                    case "Long only": return TradeDirectionMode.LongOnly;
                    case "Short only": return TradeDirectionMode.ShortOnly;
                    case "Indicator": return TradeDirectionMode.Indicator;
                }
            }
            if (t == typeof(IndicatorAction))
            {
                switch (s)
                {
                    case "Both": return IndicatorAction.Both;
                    case "Long only": return IndicatorAction.LongOnly;
                    case "Short only": return IndicatorAction.ShortOnly;
                    case "No trade": return IndicatorAction.NoTrade;
                }
            }
            if (t == typeof(PriceSource))
            {
                switch (s)
                {
                    case "open": return PriceSource.Open;
                    case "high": return PriceSource.High;
                    case "low": return PriceSource.Low;
                    case "close": return PriceSource.Close;
                    case "hl2": return PriceSource.Hl2;
                    case "hlc3": return PriceSource.Hlc3;
                    case "ohlc4": return PriceSource.Ohlc4;
                    case "hlcc4": return PriceSource.Hlcc4;
                }
            }
            throw new ArgumentException("pole " + name + ": neznama hodnota '" + s + "'");
        }
    }

    /// <summary>Druhy kresieb IBS - retazce zhodne s `tradebot/strategies/ibs/drawing.py`.</summary>
    public static class IbsKinds
    {
        public const string SdZonePre = "sd_zone_pre";
        public const string SdZonePost = "sd_zone_post";
        public const string ImbBox = "imb_box";
        public const string PinBarBox = "pin_bar_box";
        public const string EngulfingBox = "engulfing_box";
        public const string Skip = "skip";
        public const string Counter = "counter";
        public const string State34 = "state34";
        public const string Expired = "expired";
        public const string MaxDaily = "max_daily";
        public const string ImbZero = "imb_zero";
        public const string Swing = "swing";
        public const string Structure = "structure";
        public const string SrLevel = "sr_level";
        public const string SrGolden = "sr_golden";
        public const string LiqSweep = "liq_sweep";
        public const string ElliottWave = "elliott_wave";
        public const string ElliottProj = "elliott_proj";
        public const string StLine = "st_line";
        public const string StFill = "st_fill";
        public const string StSignal = "st_signal";
        public const string AdxState = "adx_state";
    }
}
