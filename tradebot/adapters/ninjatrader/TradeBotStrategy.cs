// Adapter NinjaTrader 8 nad C# jadrom TradeBota - genericka NinjaScript strategia.
//
// Vie spustit KAZDU strategiu, ktorej jadro je v C# (trieda s `[TradeBotEngine("kluc")]` nad
// `TradeBot.Core.IEngine`); konkretnu strategiu nepozna menom. Strategia pre graf je tenky potomok,
// ktory povie len kluc enginu (sablony v `deploy/ninjatrader/`, napr. `IBSNet.cs`).
//
// Delba prace je rovnaka ako vo Freqtrade a MultiCharts adapteri:
//   engine  - na kazdom UZAVRETOM bare grafu povie, co chce (ENTRY / CANCEL / CLOSE, kresby),
//   adapter - povie enginu, co sa deje u brokera (pozicia, vyplnene ordery, denny limit vyhier)
//             a jeho zamery premeni na NinjaTrader ordery (managed approach).
//
// Cas: engine pracuje s casom OTVORENIA baru v ms UTC; NinjaTrader znackuje bar casom ZATVORENIA
// v pasme z Tools > Options > General. Prepocet je na jednom mieste (`BarOpenMs`).
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Media;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using TB = TradeBot.Core;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public abstract class TradeBotStrategy : Strategy
    {
        /// <summary>Kluc C# enginu - `[TradeBotEngine("...")]` na triede strategie v jadre.</summary>
        protected abstract string EngineKey { get; }

        /// <summary>Profil, ked pouzivatel ziadny nezada (nazov suboru bez .json v adresari profilov).</summary>
        protected virtual string DefaultProfile { get { return ""; } }

        private sealed class Tracked
        {
            public TB.OrderIntent Intent;
            public Order Entry;
            public bool Filled;
            public int OpenQty;
            /// <summary>najlepsia cena od vyplnenia (vstup trailingu)</summary>
            public double? Extreme;
            public double LastStop;
        }

        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private TB.IEngine _engine;
        private TB.IHtfFeeder _htf;
        private int _htfSeries = -1;
        /// <summary>Seria, na ktoru sa posielaju ordery (0 = graf, inak jemna seria na plnenie).</summary>
        private int _fillSeries;
        private int _chartTfMinutes;
        private long _stepMs;
        private int _maxDailyWins;
        private readonly Dictionary<string, Tracked> _orders = new Dictionary<string, Tracked>();
        private int _staleLogged;
        /// <summary>UTC den -> pocet obchodov zavretych v zisku (Pine `dailyWinsCount`).</summary>
        private readonly Dictionary<string, int> _dailyWins = new Dictionary<string, int>();
        /// <summary>To iste, ako to bolo na konci predosleho baru - limit plati az od DALSIEHO baru.</summary>
        private readonly Dictionary<string, int> _dailyWinsSeen = new Dictionary<string, int>();
        private readonly TB.DrawRegistry _registry = new TB.DrawRegistry();
        private readonly Dictionary<string, Brush> _brushes = new Dictionary<string, Brush>();
        private StreamWriter _export;
        // diagnostika behu: kolko barov adapter naozaj dostal (malo barov = ziadne zony, ziadne ordery)
        private int _chartBars, _htfBars;
        private long _firstBarMs, _lastBarMs;

        // ------------------------------------------------------------------ //
        // Parametre strategie v NinjaTraderi
        // ------------------------------------------------------------------ //

        [NinjaScriptProperty]
        [Display(Name = "Profil", Description = "Nazov profilu (JSON v Documents\\NinjaTrader 8\\TradeBot\\profiles) alebo cela cesta k suboru. Prazdne = predvoleny profil strategie.", GroupName = "TradeBot", Order = 1)]
        public string Profile { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Kreslit objekty", Description = "Zony, TP/SL boxy, stitky a ciary z enginu.", GroupName = "TradeBot", Order = 2)]
        public bool ShowDrawings { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Kreslit pozadie seans", Description = "Pas pozadia na kazdom bare seansy - na dlhej historii spomaluje graf.", GroupName = "TradeBot", Order = 3)]
        public bool ShowSessionBackground { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Vypisovat udalosti", Description = "Prechody stavov a ordery do okna Output.", GroupName = "TradeBot", Order = 4)]
        public bool LogEvents { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Exportovat signaly", Description = "Zamery enginu (ENTRY/CANCEL/CLOSE) a prechody stavov do CSV v Documents/NinjaTrader 8/TradeBot/logs - na porovnanie s behom v Testeri.", GroupName = "TradeBot", Order = 5)]
        public bool ExportSignals { get; set; }

        [NinjaScriptProperty]
        [Range(0, 60)]
        [Display(Name = "Detail plnenia (min)", Description = "Ordery sa plnia na barovej serii s tymto poctom minut (1 = ako --timeframe-detail 1m v Testeri). NinjaTrader volbu Order fill resolution = High pre strategie s viac seriami nepovoli, preto si jemnu seriu pridava strategia sama; v Strategy Analyzeri nechaj Standard. 0 = plnit na baroch grafu.", GroupName = "TradeBot", Order = 6)]
        public int FillDetailMinutes { get; set; }

        // ------------------------------------------------------------------ //

        public static string ProfilesDir
        {
            get { return Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "TradeBot", "profiles"); }
        }

        private string ResolveProfilePath()
        {
            string name = string.IsNullOrEmpty(Profile) ? DefaultProfile : Profile;
            if (string.IsNullOrEmpty(name)) return null;
            if (File.Exists(name)) return name;
            string path = Path.Combine(ProfilesDir, name.EndsWith(".json", StringComparison.OrdinalIgnoreCase) ? name : name + ".json");
            if (!File.Exists(path)) throw new FileNotFoundException("TradeBot: profil '" + name + "' sa nenasiel (hladal som aj " + path + ")");
            return path;
        }

        private Dictionary<string, object> LoadConfig()
        {
            string path = ResolveProfilePath();
            if (path == null) return new Dictionary<string, object>();
            return TB.Json.ParseObject(File.ReadAllText(path));
        }

        private TB.InstrumentSpec InstrumentSpec()
        {
            MasterInstrument mi = Instrument.MasterInstrument;
            return new TB.InstrumentSpec(mi.Name, "ninjatrader", mi.TickSize, mi.PointValue, 1.0, 1.0, true);
        }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "TradeBot - strategia s jadrom v C# (" + EngineKey + ")";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 10;
                EntryHandling = EntryHandling.UniqueEntries;
                IsExitOnSessionCloseStrategy = false;
                IsInstantiatedOnEachOptimizationIteration = true;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TraceOrders = false;
                BarsRequiredToTrade = 1;
                Profile = "";
                ShowDrawings = true;
                ShowSessionBackground = false;
                LogEvents = false;
                ExportSignals = false;
                FillDetailMinutes = 1;
            }
            else if (State == State.Configure)
            {
                // Informativny TF sa musi pridat uz tu, kde instrument ani TF grafu este nie su spolahlivo
                // k dispozicii - na zistenie TF staci engine nad zastupnym instrumentom a 1m grafom (kazdy
                // TF je nasobkom 1m); ostry engine vznikne v DataLoaded.
                TB.EngineRegistry.Reset();
                TB.IEngine probe = TB.EngineRegistry.Create(EngineKey, LoadConfig(),
                    new TB.InstrumentSpec("probe", "ninjatrader", 0.01, 1.0, 1.0, 1.0, true), 1);
                TB.IHtfFeeder feeder = probe.CreateHtfFeeder();
                int next = 1;
                if (feeder != null)
                {
                    AddDataSeries(BarsPeriodType.Minute, feeder.TfMinutes);
                    _htfSeries = next++;
                }
                // Jemna seria na plnenie orderov - NinjaTrader nahrada za `Order fill resolution = High`,
                // ktoru pre strategie s viac seriami nepovoli. Order poslany na tuto seriu sa plni jej barmi.
                _fillSeries = 0;
                if (FillDetailMinutes > 0)
                {
                    AddDataSeries(BarsPeriodType.Minute, FillDetailMinutes);
                    _fillSeries = next++;
                }
            }
            else if (State == State.DataLoaded)
            {
                if (BarsArray[0].BarsPeriod.BarsPeriodType != BarsPeriodType.Minute)
                    throw new InvalidOperationException("TradeBot: strategia bezi len na minutovom grafe (limity su v baroch)");
                _chartTfMinutes = BarsArray[0].BarsPeriod.Value;
                if (FillDetailMinutes >= _chartTfMinutes) _fillSeries = 0; // jemnejsie nez graf to nie je
                _stepMs = _chartTfMinutes * 60000L;
                _engine = TB.EngineRegistry.Create(EngineKey, LoadConfig(), InstrumentSpec(), _chartTfMinutes);
                _htf = _htfSeries >= 0 ? _engine.CreateHtfFeeder() : null;
                Dictionary<string, double> stats = _engine.Stats();
                double wins;
                _maxDailyWins = stats != null && stats.TryGetValue("max_daily_wins", out wins) ? (int)wins : 0;
                if (ExportSignals) OpenExport();
                Print("TradeBot " + EngineKey + ": TF " + _chartTfMinutes + "m, predhistoria " + _engine.RequiredHistory
                      + " barov (" + (_engine.Warmup != null ? _engine.Warmup.Describe() : "") + "), tick " + Instrument.MasterInstrument.TickSize
                      + ", bod " + Instrument.MasterInstrument.PointValue);
            }
            else if (State == State.Realtime)
            {
                // historicke Order objekty v realnom case neplatia - NinjaTrader da ich nastupcov
                foreach (Tracked t in _orders.Values)
                    if (t.Entry != null) t.Entry = GetRealtimeOrder(t.Entry);
            }
            else if (State == State.Terminated)
            {
                if (_engine != null)
                    Print("TradeBot " + EngineKey + ": spracovanych " + _chartBars + " barov grafu ("
                          + Epoch.AddMilliseconds(_firstBarMs).ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + " - "
                          + Epoch.AddMilliseconds(_lastBarMs).ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + " UTC), "
                          + _htfBars + " barov informativneho TF"
                          + (_chartBars < _engine.RequiredHistory * 2 ? " - PRILIS MALO DAT: skontroluj obdobie, import a Merge policy (Tools > Options > Market data)" : ""));
                CloseExport();
            }
        }

        // ------------------------------------------------------------------ //
        // Export signalov - na porovnanie s behom v Testeri (`python -m tester.ninjatrader compare`)
        // ------------------------------------------------------------------ //

        public static string LogsDir
        {
            get { return Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "TradeBot", "logs"); }
        }

        private void OpenExport()
        {
            Directory.CreateDirectory(LogsDir);
            string name = EngineKey + "_" + Instrument.FullName.Replace(' ', '_').Replace('/', '_') + "_" + _chartTfMinutes + "m_"
                        + DateTime.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture) + "_" + GetHashCode().ToString("x") + ".csv";
            _export = new StreamWriter(Path.Combine(LogsDir, name), false, new System.Text.UTF8Encoding(false));
            _export.WriteLine("kind;bar_open_ms;id;a;b;entry;sl;tp;qty;ready;text");
        }

        private void CloseExport()
        {
            if (_export == null) return;
            try
            {
                _export.WriteLine("stat;0;adapter_chart_bars;" + _chartBars + ";;;;;;;");
                _export.WriteLine("stat;0;adapter_htf_bars;" + _htfBars + ";;;;;;;");
                _export.WriteLine("stat;0;adapter_first_bar_ms;" + _firstBarMs + ";;;;;;;");
                _export.WriteLine("stat;0;adapter_last_bar_ms;" + _lastBarMs + ";;;;;;;");
                if (_engine != null)
                    foreach (KeyValuePair<string, double> kv in _engine.Stats())
                        _export.WriteLine("stat;0;" + kv.Key + ";" + Num(kv.Value) + ";;;;;;;");
                _export.Dispose();
            }
            catch (Exception) { }
            _export = null;
        }

        private static string Num(double v) { return v.ToString("R", CultureInfo.InvariantCulture); }

        private void Export(TB.Bar bar, TB.EngineOutput output, bool ready)
        {
            if (_export == null) return;
            foreach (TB.OrderIntent i in output.Orders)
            {
                TB.TradePlan p = i.Plan;
                _export.WriteLine("order;" + bar.Time + ";" + i.OrderId + ";" + i.Action + ";" + i.OrderType + ";"
                    + (p != null ? Num(p.Entry) + ";" + Num(p.StopLoss) + ";" + Num(p.TakeProfit) + ";" + Num(p.Qty) : ";;;")
                    + ";" + (ready ? "1" : "0") + ";" + i.Reason);
            }
            foreach (TB.StateEvent e in output.Events)
                _export.WriteLine("event;" + bar.Time + ";" + e.ZoneUid + ";" + e.FromState + ";" + e.ToState + ";;;;;;"
                                  + e.Reason.Replace(';', ',').Replace('\n', ' '));
        }

        // ------------------------------------------------------------------ //
        // Cas
        // ------------------------------------------------------------------ //

        private static TimeZoneInfo PlatformZone { get { return NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo; } }

        private static long ToMs(DateTime platformTime)
        {
            DateTime utc = TimeZoneInfo.ConvertTimeToUtc(DateTime.SpecifyKind(platformTime, DateTimeKind.Unspecified), PlatformZone);
            return (long)Math.Round((utc - Epoch).TotalMilliseconds);
        }

        private static DateTime FromMs(long ms)
        {
            return TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(ms), PlatformZone);
        }

        /// <summary>Cas OTVORENIA baru v ms UTC - NinjaTrader znackuje minutovy bar casom zatvorenia.</summary>
        private long BarOpenMs(int series, long tfMs)
        {
            return ToMs(Times[series][0]) - tfMs;
        }

        private static string UtcDay(long ms)
        {
            return Epoch.AddMilliseconds(ms).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        }

        // ------------------------------------------------------------------ //
        // Bar
        // ------------------------------------------------------------------ //

        protected override void OnBarUpdate()
        {
            if (_engine == null) return;

            if (BarsInProgress == _htfSeries && _htf != null)
            {
                long htfMs = _htf.TfMinutes * 60000L;
                _htfBars++;
                _htf.Feed(new TB.Bar(BarOpenMs(_htfSeries, htfMs), Opens[_htfSeries][0], Highs[_htfSeries][0],
                                     Lows[_htfSeries][0], Closes[_htfSeries][0], Volumes[_htfSeries][0]));
                return;
            }
            if (BarsInProgress != 0) return;

            TB.Bar bar = new TB.Bar(BarOpenMs(0, _stepMs), Open[0], High[0], Low[0], Close[0], Volume[0]);
            if (_chartBars++ == 0) _firstBarMs = bar.Time;
            _lastBarMs = bar.Time;

            UpdateTrailing(bar);

            TB.MarketContext ctx = new TB.MarketContext();
            ctx.PositionSize = Position.MarketPosition == MarketPosition.Long ? Position.Quantity
                             : (Position.MarketPosition == MarketPosition.Short ? -Position.Quantity : 0);
            // Market vstup, ktory uz odisiel, ale fill este neprisiel (nazivo je asynchronny; pri davke
            // oneskorenych barov pride az po nich), sa pocita ako pozicia - inak engine vidi 0, po bare
            // vstup "zrusi" a posle dalsi: 25. 9. 2026 tak ORB poslal 20 market orderov v jednej sekunde.
            foreach (KeyValuePair<string, Tracked> kv in _orders)
            {
                Tracked p = kv.Value;
                if (p.Filled || p.Intent.OrderType != TB.OrderType.Market || p.Intent.Plan == null) continue;
                if (p.Entry != null && (p.Entry.OrderState == OrderState.Cancelled || p.Entry.OrderState == OrderState.Rejected)) continue;
                ctx.PositionSize += (p.Intent.Plan.Direction == TB.Direction.Long ? 1 : -1) * Math.Max(1, Math.Round(p.Intent.Plan.Qty));
            }
            string day = UtcDay(bar.Time);
            int winsSeen;
            ctx.DailyWinLimitReached = _maxDailyWins > 0 && _dailyWinsSeen.TryGetValue(day, out winsSeen) && winsSeen >= _maxDailyWins;
            foreach (KeyValuePair<string, Tracked> kv in _orders)
                if (kv.Value.Filled && kv.Value.OpenQty > 0) ctx.OpenOrderIds.Add(kv.Key);

            TB.HtfWindow window = _htf != null ? _htf.WindowFor(bar.Time) : null;
            TB.EngineOutput output = _engine.OnBar(bar, window, ctx);

            // Signal z baru bez celej predhistorie vstup neurobi (engine si ho odpise sam timeoutom).
            bool ready = CurrentBars[0] >= _engine.RequiredHistory;
            // Nazivo: bar, ktory prisiel s velkym oneskorenim (vypadok dat, davka barov naraz), sa
            // neobchoduje - signal je stary a fill by bol uplne inde.
            if (State == State.Realtime && (NinjaTrader.Core.Globals.Now - Times[0][0]).TotalSeconds > 2 * _chartTfMinutes * 60)
            {
                ready = false;
                if (_staleLogged++ < 5) Print("TradeBot " + EngineKey + ": bar " + Times[0][0].ToString("HH:mm", CultureInfo.InvariantCulture)
                                              + " prisiel neskoro (" + (int)(NinjaTrader.Core.Globals.Now - Times[0][0]).TotalSeconds + " s) - bez vstupu");
            }
            Export(bar, output, ready);
            foreach (TB.OrderIntent intent in output.Orders) Apply(intent, ready);
            if (output.CloseSession) Flatten("tb_session_end");

            if (LogEvents)
                foreach (TB.StateEvent e in output.Events)
                    Print(Times[0][0].ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + " zona " + e.ZoneUid + ": "
                          + e.FromState + " -> " + e.ToState + " " + e.Reason);

            if (ShowDrawings && ChartControl != null)
            {
                foreach (TB.DrawCommand cmd in output.Drawings) Render(cmd);
                // Pine `barstate.islast`: co sa kresli az na poslednom bare (S/R zhluky, Elliott) -
                // na konci historie a potom na kazdom bare nazivo (objekty maju stale id, prekreslia sa)
                if (State == State.Realtime || CurrentBars[0] >= BarsArray[0].Count - 2)
                    foreach (TB.DrawCommand cmd in _engine.FinalDrawings(bar)) Render(cmd);
            }

            int winsNow;
            if (_dailyWins.TryGetValue(day, out winsNow)) _dailyWinsSeen[day] = winsNow;
        }

        // ------------------------------------------------------------------ //
        // Ordery
        // ------------------------------------------------------------------ //

        private double Tick(double price) { return Instrument.MasterInstrument.RoundToTickSize(price); }

        private void Apply(TB.OrderIntent intent, bool ready)
        {
            Tracked t;
            if (intent.Action == TB.OrderAction.Entry)
            {
                if (!ready || intent.Plan == null) return;
                // Ten isty vstup este drzi poziciu (engine po re-entry pouzije rovnake meno): Pine by druhy
                // `strategy.entry` s rovnakym id pri otvorenej pozicii ignoroval - pozicia dobehne na svojom SL/TP.
                if (_orders.TryGetValue(intent.OrderId, out t) && t.Filled && t.OpenQty > 0) return;
                TB.TradePlan plan = intent.Plan;
                int qty = (int)Math.Max(1, Math.Round(plan.Qty));
                string id = intent.OrderId;

                t = new Tracked();
                t.Intent = intent;
                t.LastStop = plan.StopLoss;
                _orders[id] = t;

                // SL a TP sa viazu na meno vstupu a musia byt nastavene PRED vstupom
                SetStopLoss(id, CalculationMode.Price, Tick(plan.StopLoss), false);
                SetProfitTarget(id, CalculationMode.Price, Tick(plan.TakeProfit));

                bool isLong = plan.Direction == TB.Direction.Long;
                if (intent.OrderType == TB.OrderType.Market)
                {
                    if (isLong) EnterLong(_fillSeries, qty, id); else EnterShort(_fillSeries, qty, id);
                }
                else if (intent.OrderType == TB.OrderType.Stop)
                {
                    if (isLong) EnterLongStopMarket(_fillSeries, true, qty, Tick(plan.Entry), id);
                    else EnterShortStopMarket(_fillSeries, true, qty, Tick(plan.Entry), id);
                }
                else
                {
                    if (isLong) EnterLongLimit(_fillSeries, true, qty, Tick(plan.Entry), id);
                    else EnterShortLimit(_fillSeries, true, qty, Tick(plan.Entry), id);
                }
                if (LogEvents)
                    Print("ENTRY " + id + " " + intent.OrderType + " @" + plan.Entry + " SL " + plan.StopLoss + " TP " + plan.TakeProfit + " qty " + qty);
                return;
            }

            if (!_orders.TryGetValue(intent.OrderId, out t)) return;

            if (intent.Action == TB.OrderAction.Cancel)
            {
                if (!t.Filled)
                {
                    if (t.Entry != null) CancelOrder(t.Entry);
                    _orders.Remove(intent.OrderId);
                }
                if (LogEvents) Print("CANCEL " + intent.OrderId + " (" + intent.Reason + ")");
            }
            else if (intent.Action == TB.OrderAction.Close)
            {
                if (t.Filled && t.OpenQty > 0)
                {
                    if (t.Intent.Plan.Direction == TB.Direction.Long) ExitLong(_fillSeries, t.OpenQty, "tb_close", intent.OrderId);
                    else ExitShort(_fillSeries, t.OpenQty, "tb_close", intent.OrderId);
                }
                if (LogEvents) Print("CLOSE " + intent.OrderId + " (" + intent.Reason + ")");
            }
        }

        /// <summary>Koniec poslednej seansy dna: zrus cakajuce vstupy a zavri, co ostalo otvorene.</summary>
        private void Flatten(string signal)
        {
            foreach (KeyValuePair<string, Tracked> kv in new List<KeyValuePair<string, Tracked>>(_orders))
            {
                Tracked t = kv.Value;
                if (!t.Filled)
                {
                    if (t.Entry != null) CancelOrder(t.Entry);
                    _orders.Remove(kv.Key);
                }
                else if (t.OpenQty > 0)
                {
                    if (t.Intent.Plan.Direction == TB.Direction.Long) ExitLong(_fillSeries, t.OpenQty, signal, kv.Key);
                    else ExitShort(_fillSeries, t.OpenQty, signal, kv.Key);
                }
            }
        }

        /// <summary>Trailing z planu obchodu (`TradePlan.Trailing`) - posuva sa na zatvoreni baru grafu.</summary>
        private void UpdateTrailing(TB.Bar bar)
        {
            foreach (KeyValuePair<string, Tracked> kv in _orders)
            {
                Tracked t = kv.Value;
                TB.TradePlan plan = t.Intent.Plan;
                if (!t.Filled || t.OpenQty <= 0 || plan == null || plan.Trailing == null) continue;
                bool isLong = plan.Direction == TB.Direction.Long;
                double prev = t.Extreme.HasValue ? t.Extreme.Value : plan.Entry;
                double best = isLong ? Math.Max(prev, bar.High) : Math.Min(prev, bar.Low);
                t.Extreme = best;
                double stop = plan.Trailing.StopPrice(plan.Direction, plan.Entry, plan.StopLoss, best);
                bool better = isLong ? stop > t.LastStop : stop < t.LastStop;
                if (!better) continue;
                t.LastStop = stop;
                SetStopLoss(kv.Key, CalculationMode.Price, Tick(stop), false);
            }
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                              double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string comment)
        {
            Tracked t;
            if (order == null || !_orders.TryGetValue(order.Name, out t)) return;
            t.Entry = order;
            if ((orderState == OrderState.Cancelled || orderState == OrderState.Rejected) && !t.Filled)
                _orders.Remove(order.Name);
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution == null || execution.Order == null) return;
            Order order = execution.Order;
            Tracked t;

            if (_orders.TryGetValue(order.Name, out t))
            {
                // vyplnenie vstupu
                t.Filled = true;
                t.OpenQty += quantity;
                return;
            }

            string entryName = order.FromEntrySignal;
            if (string.IsNullOrEmpty(entryName) || !_orders.TryGetValue(entryName, out t)) return;

            t.OpenQty -= quantity;
            if (t.OpenQty > 0) return;
            _orders.Remove(entryName);

            // Pine `dailyWinsCount`: vyhra = uzavrety obchod so ziskom > 0. Zavretie koncom seansy sa nepocita.
            if (order.Name == "tb_session_end" || order.Name == "tb_close") return;
            TB.TradePlan plan = t.Intent.Plan;
            double move = plan.Direction == TB.Direction.Long ? price - plan.Entry : plan.Entry - price;
            if (move > 0)
            {
                string day = UtcDay(ToMs(time));
                int wins;
                _dailyWins.TryGetValue(day, out wins);
                _dailyWins[day] = wins + 1;
            }
        }

        // ------------------------------------------------------------------ //
        // Kresby
        // ------------------------------------------------------------------ //

        private Brush BrushOf(string hex, out int opacity)
        {
            // "#rrggbb" alebo "#rrggbbaa" (Pine `color.new` -> alfa)
            opacity = 100;
            if (string.IsNullOrEmpty(hex)) return Brushes.Transparent;
            string rgb = hex.Length >= 7 ? hex.Substring(0, 7) : hex;
            if (hex.Length == 9)
                opacity = (int)Math.Round(int.Parse(hex.Substring(7, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture) / 255.0 * 100);
            Brush brush;
            if (_brushes.TryGetValue(rgb, out brush)) return brush;
            Color c = Color.FromRgb(byte.Parse(rgb.Substring(1, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture),
                                    byte.Parse(rgb.Substring(3, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture),
                                    byte.Parse(rgb.Substring(5, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture));
            brush = new SolidColorBrush(c);
            brush.Freeze();
            _brushes[rgb] = brush;
            return brush;
        }

        /// <summary>X suradnica: engine dava cas otvorenia baru, NinjaTrader kresli bar na case zatvorenia.</summary>
        private DateTime X(long ms) { return FromMs(ms + _stepMs); }

        private void Render(TB.DrawCommand cmd)
        {
            TB.DrawCommand target = _registry.Apply(cmd);
            if (target == null) return;
            if (cmd is TB.DrawDelete)
            {
                RemoveDrawObject(target.ObjId);
                return;
            }
            Paint(target);
        }

        private void Paint(TB.DrawCommand o)
        {
            int opacity, fillOpacity;
            TB.DrawBox box = o as TB.DrawBox;
            if (box != null)
            {
                Brush border = BrushOf(box.BorderColor, out opacity);
                Brush fill = BrushOf(box.FillColor, out fillOpacity);
                if (opacity == 0 || box.BorderWidth == 0) border = Brushes.Transparent;
                Draw.Rectangle(this, box.ObjId, false, X(box.X1Ms), box.Y1, X(box.X2Ms), box.Y2, border, fill,
                               box.FillColor == null ? 0 : fillOpacity);
                return;
            }
            TB.DrawLine line = o as TB.DrawLine;
            if (line != null)
            {
                DashStyleHelper dash = line.Style == TB.LineStyles.Dotted ? DashStyleHelper.Dot
                                     : (line.Style == TB.LineStyles.Dashed ? DashStyleHelper.Dash : DashStyleHelper.Solid);
                Draw.Line(this, line.ObjId, false, X(line.X1Ms), line.Y1, X(line.X2Ms), line.Y2, BrushOf(line.Color, out opacity), dash, line.Width);
                return;
            }
            TB.DrawLabel label = o as TB.DrawLabel;
            if (label != null)
            {
                Brush text = BrushOf(label.Color, out opacity);
                Brush bg = BrushOf(label.BgColor, out fillOpacity);
                Draw.Text(this, label.ObjId, false, label.Text, X(label.XMs), label.Y, label.Above ? 12 : -12, text,
                          new SimpleFont("Arial", 10), TextAlignment.Center, Brushes.Transparent, bg, label.BgColor == null ? 0 : fillOpacity);
                return;
            }
            TB.DrawBg band = o as TB.DrawBg;
            if (band != null)
            {
                if (band.Kind == TB.DrawKinds.Session && !ShowSessionBackground) return;
                Brush brush = BrushOf(band.Color, out opacity);
                Draw.RegionHighlightX(this, band.ObjId, X(band.X1Ms), X(band.X2Ms), Brushes.Transparent, brush, opacity);
            }
        }
    }
}
