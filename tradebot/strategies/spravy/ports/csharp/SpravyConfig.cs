// Konfiguracia SPRAVY 3.0 (C#) - zrkadlo `tradebot/strategies/spravy/config.py`.
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
        // ---- obchodovane spravy (pravidlo plati len pre zapnutu spravu) --------
        public bool useFOMC = true;
        public bool useFOMC_MIN = false;
        public bool useCPI = true;
        public bool useNFP = false;
        public bool usePPI = true;
        public bool useJOLTS = true;
        public bool useRETAIL = false;
        public bool usePCE = true;
        public bool useGDP = false;
        public bool useISM_M = false;
        public bool useISM_S = false;
        public bool useCLAIMS = false;
        // ---- pravidlo 1 ----
        public string r1Event = "FOMC";
        public string r1Mode = "fade";
        public int r1From = -60;
        public int r1To = 0;
        public int r1Enter = 0;
        public int r1Hold = 175;
        public double r1Stop = 10.0;
        public double r1RR = 0.0;
        // ---- pravidlo 2 ----
        public string r2Event = "";
        public string r2Mode = "trend";
        public int r2From = 0;
        public int r2To = 25;
        public int r2Enter = 30;
        public int r2Hold = 145;
        public double r2Stop = 0.0;
        public double r2RR = 0.0;
        // ---- pravidlo 3 ----
        public string r3Event = "CPI";
        public string r3Mode = "fade";
        public int r3From = 0;
        public int r3To = 60;
        public int r3Enter = 60;
        public int r3Hold = 60;
        public double r3Stop = 10.0;
        public double r3RR = 0.0;
        // ---- pravidlo 4 ----
        public string r4Event = "PPI";
        public string r4Mode = "fade";
        public int r4From = 0;
        public int r4To = 15;
        public int r4Enter = 15;
        public int r4Hold = 180;
        public double r4Stop = 0.0;
        public double r4RR = 3.0;
        // ---- pravidlo 5 ----
        public string r5Event = "PCE";
        public string r5Mode = "trend";
        public int r5From = 15;
        public int r5To = 60;
        public int r5Enter = 60;
        public int r5Hold = 240;
        public double r5Stop = 0.0;
        public double r5RR = 0.0;
        // ---- pravidlo 6 ----
        public string r6Event = "JOLTS";
        public string r6Mode = "fade";
        public int r6From = 0;
        public int r6To = 60;
        public int r6Enter = 60;
        public int r6Hold = 60;
        public double r6Stop = 10.0;
        public double r6RR = 0.0;
        // ---- pravidlo 7 ----
        public string r7Event = "";
        public string r7Mode = "trend";
        public int r7From = 0;
        public int r7To = 15;
        public int r7Enter = 15;
        public int r7Hold = 60;
        public double r7Stop = 0.0;
        public double r7RR = 0.0;
        // ---- pravidlo 8 ----
        public string r8Event = "";
        public string r8Mode = "trend";
        public int r8From = 0;
        public int r8To = 15;
        public int r8Enter = 15;
        public int r8Hold = 60;
        public double r8Stop = 0.0;
        public double r8RR = 0.0;
        // ---- stop a ciel ------------------------------------------------------
        public int atrLen = 14;
        public SizeSpec slBuffer = new SizeSpec(1.0, "atr");
        public SizeSpec minLeg = new SizeSpec(0.0, "atr");
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

        public const int RuleCount = 8;

        /// <summary>Jedno pravidlo - zrkadlo `config.Rule`.</summary>
        public sealed class Rule
        {
            public int No;
            public string Event;
            public bool Trend;
            public string Mode;
            public int From, To, Enter, Hold;
            public double Stop, RR;
            /// <summary>PRED = noha cela pred spravou, inak TREND / FADE.</summary>
            public string Label { get { return To <= 0 ? "PRED" : (Trend ? "TREND" : "FADE"); } }
        }

        private static Rule Make(int no, string ev, string mode, int fr, int to, int en, int hold, double stop, double rr)
        {
            Rule r = new Rule();
            r.No = no;
            r.Event = (ev ?? "").Trim().ToUpperInvariant();
            r.Trend = (mode ?? "").Trim().ToLowerInvariant() == "trend";
            r.Mode = (mode ?? "").Trim().ToLowerInvariant();
            r.From = fr; r.To = to; r.Enter = en; r.Hold = hold; r.Stop = stop; r.RR = rr;
            return r;
        }

        /// <summary>Vsetkych 8 pravidiel aj s prazdnou spravou (na kontrolu configu).</summary>
        public List<Rule> AllRules()
        {
            List<Rule> all = new List<Rule>();
            all.Add(Make(1, r1Event, r1Mode, r1From, r1To, r1Enter, r1Hold, r1Stop, r1RR));
            all.Add(Make(2, r2Event, r2Mode, r2From, r2To, r2Enter, r2Hold, r2Stop, r2RR));
            all.Add(Make(3, r3Event, r3Mode, r3From, r3To, r3Enter, r3Hold, r3Stop, r3RR));
            all.Add(Make(4, r4Event, r4Mode, r4From, r4To, r4Enter, r4Hold, r4Stop, r4RR));
            all.Add(Make(5, r5Event, r5Mode, r5From, r5To, r5Enter, r5Hold, r5Stop, r5RR));
            all.Add(Make(6, r6Event, r6Mode, r6From, r6To, r6Enter, r6Hold, r6Stop, r6RR));
            all.Add(Make(7, r7Event, r7Mode, r7From, r7To, r7Enter, r7Hold, r7Stop, r7RR));
            all.Add(Make(8, r8Event, r8Mode, r8From, r8To, r8Enter, r8Hold, r8Stop, r8RR));
            return all;
        }

        /// <summary>Je sprava zapnuta prepinacom `use&lt;TYP&gt;`?</summary>
        public bool Uses(string ev)
        {
            switch (ev)
            {
                case "FOMC": return useFOMC;
                case "FOMC_MIN": return useFOMC_MIN;
                case "CPI": return useCPI;
                case "NFP": return useNFP;
                case "PPI": return usePPI;
                case "JOLTS": return useJOLTS;
                case "RETAIL": return useRETAIL;
                case "PCE": return usePCE;
                case "GDP": return useGDP;
                case "ISM_M": return useISM_M;
                case "ISM_S": return useISM_S;
                case "CLAIMS": return useCLAIMS;
                default: return false;
            }
        }

        /// <summary>Platne pravidla (vyplnena a zapnuta sprava `use&lt;TYP&gt;`) v poradi 1..8 - ako `SpravyConfig.rules()`.</summary>
        public List<Rule> Rules()
        {
            List<Rule> out_ = new List<Rule>();
            foreach (Rule r in AllRules())
                if (r.Event.Length > 0 && Uses(r.Event)) out_.Add(r);
            return out_;
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
            foreach (Rule r in cfg.AllRules())
            {
                if (r.Event.Length == 0) continue;
                string n = r.No.ToString(CultureInfo.InvariantCulture);
                if (!known.Contains(r.Event)) throw new ArgumentException("SPRÁVY: pravidlo " + n + ": neznámy typ správy " + r.Event);
                if (r.Mode != "trend" && r.Mode != "fade") throw new ArgumentException("SPRÁVY: pravidlo " + n + ": režim len trend alebo fade");
                if (r.From >= r.To) throw new ArgumentException("SPRÁVY: pravidlo " + n + ": noha musí mať od < do");
                if (r.Enter < r.To) throw new ArgumentException("SPRÁVY: pravidlo " + n + ": vstup nesmie byť pred koncom nohy");
                if (r.RR > 0 && r.RR < 0.5) throw new ArgumentException("SPRÁVY: pravidlo " + n + ": RRR najmenej 0,5 (alebo 0 = bez cieľa)");
            }
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
