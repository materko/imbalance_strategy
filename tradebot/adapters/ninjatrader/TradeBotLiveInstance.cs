// TradeBot Live AddOn - jedna instancia enginu bez cloveka v NinjaTraderi 8 (docs/NINJATRADER.md, "Beh bez cloveka").
//
// Zrkadlo adaptera `TradeBotStrategy.cs` (NinjaScript Strategy), ale bez grafu a bez managed orderov:
// bary daju dva `BarsRequest` (graf + informativny TF), ordery idu cez `Account.CreateOrder/Submit`,
// SL a TP su samostatne OCO ordery, fily chodia z `Account.ExecutionUpdate`. Semantika je ta ista:
// engine dostane kazdy UZAVRETY bar grafu presne raz, jedna pozicia naraz (odlozene vstupy), trailing
// na zatvoreni baru, denny limit vyhier, koniec seansy zavrie vsetko, control subor (pauza, flatten,
// profil). Navyse vie, co Strategy nevie: pri zmene profilu postavi novy engine a PREHRA historiu
// z BarsRequest znova, takze novy engine ma plnu predhistoriu.
//
// Vlakna: NinjaTrader vola callbacky (BarsRequest.Update, OrderUpdate, ExecutionUpdate) zo svojich
// vlakien - tie len skopiruju data / zaradia akciu do fronty a zobudia vlakno instancie. Vsetka logika
// (engine, ordery, spool, control) bezi v jednom vlastnom vlakne, takze nic nepotrebuje zamky a UI
// vlakno NinjaTradera sa nikdy neblokuje. Kazdy callback je v try/catch - vynimka ide do logu.
//
// Uzavretie baru: NinjaTrader znackuje bar casom ZATVORENIA v pasme z Options > General. Bar je
// uzavrety, ked za nim v serii uz je dalsi, alebo ked jeho cas zatvorenia + 1 s uz preslo (tichy trh
// bez tickov by inak bar nikdy nezavrel). Informativny TF sa krmi pred barom grafu, s ktorym sa uzavrel.
#region Using declarations
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Threading;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using TB = TradeBot.Core;
#endregion

namespace NinjaTrader.NinjaScript.AddOns
{
    /// <summary>Jeden riadok `instances[]` z `TradeBot\deploy.json`.</summary>
    public sealed class LiveDeployment
    {
        public string Id = "";
        public string Connection = "";
        public string Account = "";
        public string Instrument = "";
        public int Tf = 1;
        public string Strategy = "";
        public string Profile = "";

        /// <summary>Kluc na porovnanie medzi dvoma citaniami deploy.json.</summary>
        public string Key
        {
            get { return Id.Length > 0 ? Id : Account + "|" + Instrument + "|" + Tf + "|" + Strategy; }
        }

        public bool SameAs(LiveDeployment o)
        {
            return o != null && Id == o.Id && Connection == o.Connection && Account == o.Account && Instrument == o.Instrument
                && Tf == o.Tf && Strategy == o.Strategy && Profile == o.Profile;
        }

        public string Describe()
        {
            return (Id.Length > 0 ? Id + ": " : "") + Strategy + " " + Instrument + " " + Tf + "m na " + Account
                 + " (" + Connection + ", profil '" + Profile + "')";
        }

        public static LiveDeployment FromJson(Dictionary<string, object> d)
        {
            LiveDeployment dep = new LiveDeployment();
            dep.Id = TB.Json.GetString(d, "deployment", "");
            dep.Connection = TB.Json.GetString(d, "connection", "");
            dep.Account = TB.Json.GetString(d, "account", "");
            dep.Instrument = TB.Json.GetString(d, "instrument", "");
            dep.Tf = (int)TB.Json.GetDouble(d, "tf", 1);
            dep.Strategy = TB.Json.GetString(d, "strategy", "");
            dep.Profile = TB.Json.GetString(d, "profile", "");
            return dep;
        }
    }

    public sealed class LiveInstance
    {
        /// <summary>Kopia baru zo serie NinjaTradera (cas = cas ZATVORENIA v pasme platformy).</summary>
        private sealed class Candle
        {
            public readonly DateTime Time;
            public readonly double Open, High, Low, Close, Volume;
            public Candle(DateTime time, double o, double h, double l, double c, double v)
            {
                Time = time; Open = o; High = h; Low = l; Close = c; Volume = v;
            }
        }

        /// <summary>Jedna barova seria (graf alebo informativny TF): BarsRequest + vlastna kopia barov.</summary>
        private sealed class Series
        {
            public readonly int Tf;
            public BarsRequest Request;
            public EventHandler<BarsUpdateEventArgs> Handler;
            /// <summary>Kopia barov - pise ju callback NT pod `Gate`, cita vlakno instancie.</summary>
            public readonly List<Candle> Bars = new List<Candle>();
            public readonly object Gate = new object();
            /// <summary>Kolko barov (od indexu 0) uz dostal engine.</summary>
            public int Fed;
            public readonly ManualResetEvent Loaded = new ManualResetEvent(false);
            public string Error;
            public int Updates;
            public Series(int tf) { Tf = tf; }
        }

        private sealed class Tracked
        {
            public TB.OrderIntent Intent;
            public Order Entry;
            public bool Filled;
            public int OpenQty;
            /// <summary>najlepsia cena od vyplnenia (vstup trailingu)</summary>
            public double? Extreme;
            public double LastStop;
            /// <summary>Odlozeny vstup: engine ho chce, ale bezi pozicia, takze u brokera nie je (Pine `pyramiding=0`).</summary>
            public bool Parked;
            /// <summary>OCO vystupy po vyplneni vstupu.</summary>
            public Order Sl, Tp;
            /// <summary>Meno vystupu (tb_close / tb_session_end / tb_flatten), ked sa pozicia zatvara trhovym orderom.</summary>
            public string Closing;
            public DateTime ClosingSince;
            public bool CloseSent;
            /// <summary>Kedy prisiel prvy fill vstupu (UTC) - pozicia uctu sa obnovi o chvilu neskor.</summary>
            public DateTime FilledAt;
            /// <summary>Cas prveho fillu vstupu a odoslania vstupu (ms UTC) - po restarte od nich hlada exekucie uctu.</summary>
            public long FilledMs, SentMs;
            /// <summary>Strazca SL (GuardExits): od kedy pozicia nema zivy SL, kolko pokusov ho polozit znova zlyhalo.</summary>
            public DateTime NoStopSince;
            public int ExitFails;
            /// <summary>Odmietnute trhove zatvorenie: pocet, dalsi pokus najskor o, a ci medzitym stoja SL/TP znova.</summary>
            public int CloseFails;
            public DateTime CloseRetryAt;
            public bool Protect;
        }

        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        /// <summary>Bar je uzavrety, ked jeho cas zatvorenia + tato rezerva uz presiel.</summary>
        private const int CloseGraceSeconds = 1;
        private const int ControlPeriodSeconds = 2;
        /// <summary>Kym sa pri zatvarani pozicie nepotvrdi zrusenie SL/TP, trhovy vystup pocka najviac tolko.</summary>
        private const int CloseCancelTimeoutSeconds = 10;
        /// <summary>Pozicia bez ziveho SL: po tolkych sekundach sa polozi znova (OCO, fill druheho vystupu ma prednost).</summary>
        private const int NoStopGraceSeconds = 2;
        /// <summary>Tolko pokusov polozit SL znova - potom sa pozicia zavrie trhom (bez stopu nesmie ostat).</summary>
        private const int MaxExitAttempts = 3;
        /// <summary>Po tolkych odmietnutych trhovych zatvoreniach sa SL/TP polozia spat, kym ide dalsi pokus.</summary>
        private const int MaxCloseAttempts = 3;

        public readonly LiveDeployment Deployment;
        private readonly Queue<Action> _queue = new Queue<Action>();
        private readonly AutoResetEvent _wake = new AutoResetEvent(false);
        private Thread _thread;
        private volatile bool _stopRequested;
        private string _stopReason = "terminated";

        public bool Failed { get; private set; }
        public bool Finished { get; private set; }
        public string Status { get; private set; }
        public DateTime FinishedAt { get; private set; }

        private Account _account;
        private Instrument _inst;
        private string _instrumentName = "";
        private string _instance = "";
        private Dictionary<string, object> _config;
        private TB.IEngine _engine;
        private TB.IHtfFeeder _htf;
        private Series _chart;
        private Series _htfSeries;
        /// <summary>1m bary symbolu do telemetrie (`m1`); pri 1m grafe je to `_chart`.</summary>
        private Series _m1Series;
        /// <summary>Kolko 1m barov (od indexu 0) uz je v spoole - vlastny pocitadlo, `Fed` patri engine-u.</summary>
        private int _m1Spooled;
        private int _maxDailyWins;
        private long _stepMs;
        private readonly Dictionary<string, Tracked> _orders = new Dictionary<string, Tracked>();
        private readonly Dictionary<string, int> _dailyWins = new Dictionary<string, int>();
        private readonly Dictionary<string, int> _dailyWinsSeen = new Dictionary<string, int>();
        private TB.LiveSpool _spool;
        private bool _spoolErrorPrinted;
        /// <summary>Predhistoria je prehrata, dalsie bary su nazivo (ready, stale guard, control kazde 2 s).</summary>
        private bool _live;
        private int _chartBars, _htfBars, _engineBars;
        private long _firstBarMs, _lastBarMs;
        private int _staleLogged;
        /// <summary>Rastie pri kazdom prehrati historie - bar, pocas ktoreho sa vymenil engine, sa nesmie podat dvakrat.</summary>
        private int _replays;
        private EventHandler<OrderEventArgs> _orderHandler;
        private EventHandler<ExecutionEventArgs> _executionHandler;
        private int _ocoSeq;
        /// <summary>Posledny fill cudzieho orderu na instrumente (napr. Chart Trader Close) - cena pre vystup mimo strategie.</summary>
        private double _foreignPrice;
        private long _foreignMs;
        private DateTime _extFlatSince = DateTime.MinValue;
        /// <summary>Od kedy je ucet nepretrzite Connected - ReconcileExternal po reconnecte pocka, kym sa pozicie
        /// uctu zosynchronizuju (audit N-LIVE-12).</summary>
        private DateTime _connectedSince = DateTime.MinValue;
        /// <summary>Strazca feedu (FeedWatch): bary pocas seansy neprichadzaju; kedy sa to naposledy hlasilo.</summary>
        private bool _feedStale;
        private DateTime _feedNoted = DateTime.MinValue;
        private NinjaTrader.Data.SessionIterator _sessions;
        /// <summary>Den (NY), v ktorom sa uz zatvaralo podla hodin (EodByClock) - hlasi sa raz.</summary>
        private string _eodClockDay;
        private double _lastClose;

        // control subor (docs/LIVE.md, faza 2)
        private string _controlPath;
        private DateTime _controlMtime = DateTime.MinValue;
        private bool _controlSeen;
        private string _controlMode = "enabled";
        private string _controlProfile;
        private string _pendingProfile;
        private bool _pendingLogged;
        private int _controlEvents;
        private DateTime _controlChecked = DateTime.MinValue;

        // pamat obchodov cez restart (docs/NINJATRADER.md, "Restart s otvorenymi obchodmi")
        private string _statePath;
        private string _stateText;
        private bool _stateWarned;

        public LiveInstance(LiveDeployment deployment)
        {
            Deployment = deployment;
            Status = "new";
        }

        public string Instance { get { return _instance; } }

        // ------------------------------------------------------------------ //
        // Zivotny cyklus
        // ------------------------------------------------------------------ //

        public void Start()
        {
            if (_thread != null) return;
            _thread = new Thread(Run);
            _thread.IsBackground = true;
            _thread.Name = "TradeBotLive " + Deployment.Key;
            _thread.Start();
        }

        /// <summary>Poziada o koniec (zrusi cakajuce vstupy, poziciu necha - jej SL/TP su GTC ordery na ucte).</summary>
        public void Stop(string reason)
        {
            _stopReason = reason ?? "terminated";
            _stopRequested = true;
            _wake.Set();
        }

        public bool Join(int ms)
        {
            Thread t = _thread;
            if (t == null) return true;
            try { return t.Join(ms); } catch (Exception) { return true; }
        }

        private void Log(string text) { TradeBotLiveAddOn.Say("[" + (_instance.Length > 0 ? _instance : Deployment.Key) + "] " + text); }

        private void Note(string level, string text)
        {
            Log((level == "info" ? "" : level.ToUpperInvariant() + ": ") + text);
            if (_spool != null) { _spool.Note(level, text); SpoolCheck(); }
        }

        private void SpoolCheck()
        {
            if (_spool == null) return;
            if (!_spool.Broken)
            {
                if (_spoolErrorPrinted) { _spoolErrorPrinted = false; Log("live telemetria znova bezi"); }
                return;
            }
            if (_spoolErrorPrinted) return;
            _spoolErrorPrinted = true;
            Log("live telemetria prerusena - " + _spool.LastError + " (skusi sa znova o " + TB.LiveSpool.ReopenSeconds + " s)");
        }

        /// <summary>Callback NinjaTradera: praca sa zaradi do fronty vlakna instancie.</summary>
        private void Post(Action action)
        {
            lock (_queue) _queue.Enqueue(action);
            _wake.Set();
        }

        private void Run()
        {
            try
            {
                Status = "starting";
                if (!Setup())
                {
                    Failed = true;
                    Status = "failed";
                    Teardown("failed");
                    return;
                }
                Status = "running";
                DateTime lastControl = DateTime.UtcNow;
                while (!_stopRequested)
                {
                    _wake.WaitOne(1000);
                    Drain();
                    if (_stopRequested) break;
                    try { ProcessBars(); }
                    catch (Exception e) { Note("error", "spracovanie barov zlyhalo - " + e); }
                    try { if (_live) ReconcileExternal(); }
                    catch (Exception e) { Note("error", "kontrola pozicie uctu - " + e.Message); }
                    try { if (_live) ReleaseParked(); }   // pozicia uctu sa vynuluje o chvilu po fille vystupu
                    catch (Exception e) { Note("error", "odlozene vstupy - " + e.Message); }
                    try { if (_live) GuardExits(); }
                    catch (Exception e) { Note("error", "strazca SL - " + e.Message); }
                    try { if (_live) { EodByClock(); FeedWatch(); } }
                    catch (Exception e) { Note("error", "strazca feedu / EOD - " + e.Message); }
                    try { if (_live) OldContractCheck(); }
                    catch (Exception e) { Log("kontrola stareho kontraktu - " + e.Message); }
                    SaveState();
                    try { if (_live) SpoolBroker(); }
                    catch (Exception e) { Log("pozicia uctu do telemetrie - " + e.Message); }
                    if ((DateTime.UtcNow - lastControl).TotalSeconds >= ControlPeriodSeconds)
                    {
                        lastControl = DateTime.UtcNow;
                        try { ControlCheck(); } catch (Exception e) { Note("error", "control zlyhal - " + e.Message); }
                        try { CloseTimeouts(); } catch (Exception e) { Note("error", "close timeout - " + e.Message); }
                    }
                }
                Teardown(_stopReason);
            }
            catch (Exception e)
            {
                Log("vlakno instancie spadlo: " + e);
                Failed = true;
                try { Teardown("crashed"); } catch (Exception) { }
            }
            finally
            {
                Finished = true;
                FinishedAt = DateTime.UtcNow;
                if (Status != "failed") Status = "stopped";
            }
        }

        private void Drain()
        {
            while (true)
            {
                Action a;
                lock (_queue)
                {
                    if (_queue.Count == 0) return;
                    a = _queue.Dequeue();
                }
                try { a(); }
                catch (Exception e) { Note("error", "udalost zlyhala - " + e); }
            }
        }

        // ------------------------------------------------------------------ //
        // Start: pripojenie, ucet, instrument, engine, bary, predhistoria
        // ------------------------------------------------------------------ //

        private bool Setup()
        {
            LiveDeployment d = Deployment;
            Log("start " + d.Describe());
            if (d.Strategy.Length == 0 || d.Instrument.Length == 0 || d.Account.Length == 0 || d.Tf < 1)
            {
                Log("neuplny zaznam v deploy.json (strategy, instrument, account, tf) - preskakujem");
                return false;
            }
            string profilePath = ResolveProfilePath(d.Strategy, d.Profile);
            if (profilePath == null)
            {
                Log("profil '" + d.Profile + "' sa nenasiel v " + TradeBotLiveAddOn.ProfilesDir + " - preskakujem");
                return false;
            }

            if (d.Connection.Length > 0 && !TradeBotLiveAddOn.EnsureConnected(d.Connection, 60))
            {
                Log("pripojenie '" + d.Connection + "' nie je Connected - skusim znova neskor");
                return false;
            }
            _account = WaitAccount(d.Account, 60);
            if (_account == null) return false;
            try { _inst = Instrument.GetInstrument(d.Instrument); }
            catch (Exception e) { Log("GetInstrument: " + e.Message); }
            if (_inst == null) { Log("instrument '" + d.Instrument + "' NinjaTrader nepozna"); return false; }
            _instrumentName = _inst.MasterInstrument.Name;
            _stepMs = d.Tf * 60000L;
            _instance = TB.LiveSpool.InstanceId("ninjatrader", _account.Name, _instrumentName, d.Tf, d.Strategy);
            _statePath = Path.Combine(TradeBotLiveAddOn.StateDir, _instance + ".json");

            try
            {
                _config = TB.Json.ParseObject(File.ReadAllText(profilePath));
                TB.EngineRegistry.Reset();
                _engine = TB.EngineRegistry.Create(d.Strategy, _config, InstrumentSpec(), d.Tf);
            }
            catch (Exception e) { Log("engine '" + d.Strategy + "' z profilu '" + d.Profile + "' sa nepostavil - " + e.Message); return false; }
            _htf = _engine.CreateHtfFeeder();
            ReadStats();
            _controlProfile = d.Profile;
            Log("instrument " + _inst.FullName + " tick " + _inst.MasterInstrument.TickSize + " bod " + _inst.MasterInstrument.PointValue
                + ", TF " + d.Tf + "m, predhistoria " + _engine.RequiredHistory + " barov (" + (_engine.Warmup != null ? _engine.Warmup.Describe() : "")
                + ")" + (_htf != null ? ", informativny TF " + _htf.TfMinutes + "m" : ""));

            OpenSpool(d.Profile);
            Log("instancia " + _instance + (_spool != null && !_spool.Broken ? ", spool " + _spool.Path : ""));

            // control subor pred prvym barom: iny profil sa vymeni zadarmo (nic sa este neprehralo)
            ControlInit();

            // indikatory na vlastnom TF (filter trendu na 60m, ADX) AddOn nesieje - rozbehnu sa na tejto predhistorii
            _chart = RequestSeries(d.Tf, Math.Max(50, Math.Max(_engine.RequiredHistory * 2, LiveHistory(_engine)) + 5));
            if (_chart == null) return false;
            if (_htf != null)
            {
                _htfSeries = RequestSeries(_htf.TfMinutes, HtfBarsBack(_chart.Tf, _htf.TfMinutes, _engine.RequiredHistory * 2 + 5));
                if (_htfSeries == null) return false;
            }
            // 1m bary do telemetrie (sklad zivych sviecok, docs/LIVE.md) - bez nich obchoduje dalej
            _m1Series = d.Tf == 1 ? _chart : RequestSeries(1, TB.LiveSpool.MinuteBackfill);
            if (_m1Series == null) Log("1m bary do telemetrie nebudu (BarsRequest 1m zlyhal)");

            _orderHandler = OnOrderUpdate;
            _executionHandler = OnExecutionUpdate;
            _account.OrderUpdate += _orderHandler;
            _account.ExecutionUpdate += _executionHandler;

            Replay();
            try { RestoreState(); }
            catch (Exception e) { Note("error", "prevzatie obchodov spred restartu zlyhalo - " + e); }
            // rezim flatten z control suboru: ControlInit bezal pred prevzatim, ked este nebolo co zatvorit (audit N-LIVE-9)
            if (_controlMode == "flatten" && _orders.Count > 0) { Flatten("tb_flatten"); Log("FLATTEN (control, po prevzati obchodov)"); }
            SaveState();
            return true;
        }

        private static int HtfBarsBack(int chartTf, int htfTf, int chartBars)
        {
            return (int)Math.Ceiling((double)chartBars * chartTf / Math.Max(1, htfTf)) + 8;
        }

        /// <summary>Bary grafu na prehratie: `RequiredHistory` a indikatory na vlastnom TF (`Warmup.LiveChartBars`).</summary>
        private static int LiveHistory(TB.IEngine engine)
        {
            return engine.Warmup != null ? Math.Max(engine.RequiredHistory, engine.Warmup.LiveChartBars) : engine.RequiredHistory;
        }

        private void ReadStats()
        {
            Dictionary<string, double> stats = _engine.Stats();
            double wins;
            _maxDailyWins = stats != null && stats.TryGetValue("max_daily_wins", out wins) ? (int)wins : 0;
        }

        private TB.InstrumentSpec InstrumentSpec()
        {
            MasterInstrument mi = _inst.MasterInstrument;
            return new TB.InstrumentSpec(mi.Name, "ninjatrader", mi.TickSize, mi.PointValue, 1.0, 1.0, true);
        }

        /// <summary>`TradeBot\profiles\&lt;strategia&gt;\&lt;profil&gt;.json`, potom `TradeBot\profiles\&lt;profil&gt;.json`, potom cela cesta.</summary>
        public static string ResolveProfilePath(string strategy, string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            string file = name.EndsWith(".json", StringComparison.OrdinalIgnoreCase) ? name : name + ".json";
            string[] candidates = new string[]
            {
                Path.Combine(Path.Combine(TradeBotLiveAddOn.ProfilesDir, strategy ?? ""), file),
                Path.Combine(TradeBotLiveAddOn.ProfilesDir, file),
                name
            };
            foreach (string c in candidates)
                if (File.Exists(c)) return c;
            return null;
        }

        private Account WaitAccount(string name, int seconds)
        {
            for (int i = 0; i < seconds && !_stopRequested; i++)
            {
                try
                {
                    lock (Account.All)
                        foreach (Account a in Account.All)
                            if (a.Name == name && a.ConnectionStatus == ConnectionStatus.Connected)
                            {
                                Log("ucet " + name + " je Connected (" + (a.Connection != null && a.Connection.Options != null ? a.Connection.Options.Name : "-") + ")");
                                return a;
                            }
                }
                catch (Exception e) { Log("WaitAccount: " + e.Message); }
                Thread.Sleep(1000);
            }
            Log("ucet " + name + " sa do " + seconds + " s nepripojil");
            return null;
        }

        private void OpenSpool(string profile)
        {
            _spoolErrorPrinted = false;
            _spool = new TB.LiveSpool(TradeBotLiveAddOn.SpoolDir, "ninjatrader", _account.Name, _instrumentName, Deployment.Tf,
                                      Deployment.Strategy, profile, false, _config, InstrumentSpec());
            SpoolCheck();
            _m1Spooled = 0;   // novy beh dostane predhistoriu 1m znova
        }

        // ------------------------------------------------------------------ //
        // Bary: BarsRequest -> vlastna kopia; uzavrete bary -> engine
        // ------------------------------------------------------------------ //

        private Series RequestSeries(int tf, int barsBack)
        {
            Series s = new Series(tf);
            try
            {
                BarsRequest req = new BarsRequest(_inst, barsBack);
                BarsPeriod period = new BarsPeriod();
                period.BarsPeriodType = BarsPeriodType.Minute;
                period.Value = tf;
                req.BarsPeriod = period;
                req.TradingHours = _inst.MasterInstrument.TradingHours;
                req.MergePolicy = MergePolicy.DoNotMerge;
                s.Request = req;
                s.Handler = delegate(object sender, BarsUpdateEventArgs e)
                {
                    try
                    {
                        BarsSeries bs = e.BarsSeries;
                        lock (s.Gate)
                        {
                            for (int i = Math.Max(0, e.MinIndex); i <= e.MaxIndex && i < bs.Count; i++)
                                Put(s.Bars, i, new Candle(bs.GetTime(i), bs.GetOpen(i), bs.GetHigh(i), bs.GetLow(i), bs.GetClose(i), bs.GetVolume(i)));
                            s.Updates++;
                        }
                        _wake.Set();
                    }
                    catch (Exception ex) { Log("bar update " + tf + "m: " + ex.Message); }
                };
                req.Update += s.Handler;
                req.Request(new Action<BarsRequest, ErrorCode, string>(delegate(BarsRequest r, ErrorCode code, string msg)
                {
                    try
                    {
                        if (code != ErrorCode.NoError || r.Bars == null)
                            s.Error = code + " " + msg;
                        else
                        {
                            Bars b = r.Bars;
                            lock (s.Gate)
                            {
                                for (int i = 0; i < b.Count; i++)
                                    Put(s.Bars, i, new Candle(b.GetTime(i), b.GetOpen(i), b.GetHigh(i), b.GetLow(i), b.GetClose(i), b.GetVolume(i)));
                            }
                        }
                    }
                    catch (Exception ex) { s.Error = ex.Message; }
                    finally { s.Loaded.Set(); }
                }));
                if (!s.Loaded.WaitOne(120000)) { Log("BarsRequest " + tf + "m bez odpovede 120 s"); DisposeSeries(s); return null; }
                if (s.Error != null) { Log("BarsRequest " + tf + "m chyba " + s.Error); DisposeSeries(s); return null; }
                int n;
                Candle last = null;
                lock (s.Gate) { n = s.Bars.Count; if (n > 0) last = s.Bars[n - 1]; }
                Log("BarsRequest " + _inst.FullName + " " + tf + "m: " + n + " barov (chcel " + barsBack + ")"
                    + (last != null ? ", posledny " + last.Time.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + " c=" + last.Close : ""));
                return s;
            }
            catch (Exception e) { Log("BarsRequest " + tf + "m: " + e); DisposeSeries(s); return null; }
        }

        private static void Put(List<Candle> list, int index, Candle c)
        {
            if (index < list.Count) list[index] = c;
            else if (index == list.Count) list.Add(c);
            // diera v indexoch (nemalo by nastat) - bar sa doplni, ked NT posle jeho update
        }

        private void DisposeSeries(Series s)
        {
            if (s == null || s.Request == null) return;
            try { if (s.Handler != null) s.Request.Update -= s.Handler; } catch (Exception) { }
            try { s.Request.Dispose(); } catch (Exception) { }
            s.Request = null;
        }

        /// <summary>Bar s indexom `i` je uzavrety: je za nim dalsi, alebo jeho cas zatvorenia (+ rezerva) uz presiel.</summary>
        private static Candle ClosedAt(Series s, int i, DateTime now)
        {
            lock (s.Gate)
            {
                if (i >= s.Bars.Count) return null;
                Candle c = s.Bars[i];
                if (i < s.Bars.Count - 1 || c.Time.AddSeconds(CloseGraceSeconds) <= now) return c;
                return null;
            }
        }

        /// <summary>Prehra predhistoriu (ready=false, bez orderov) a prepne na zivy rezim.</summary>
        private void Replay()
        {
            if (_chart == null) return;
            _replays++;
            _live = false;
            _chart.Fed = 0;
            if (_htfSeries != null) _htfSeries.Fed = 0;
            _engineBars = 0;
            _chartBars = 0; _htfBars = 0;
            _staleLogged = 0;
            ProcessBars();
            int count;
            lock (_chart.Gate) count = _chart.Bars.Count;
            Log("predhistoria prehrata: " + _chartBars + " barov grafu" + (_htfSeries != null ? ", " + _htfBars + " barov " + _htfSeries.Tf + "m" : "")
                + (_chartBars < _engine.RequiredHistory ? " - PRILIS MALO DAT (treba " + _engine.RequiredHistory + "), obchoduje az po dalsich baroch nazivo" : "")
                + (_firstBarMs > 0 ? " (" + Epoch.AddMilliseconds(_firstBarMs).ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + " - "
                   + Epoch.AddMilliseconds(_lastBarMs).ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + " UTC)" : ""));
            _live = true;
            if (_spool != null) { _spool.Realtime = true; SpoolCheck(); }
        }

        /// <summary>Vsetky uzavrete, este nepodane bary: informativny TF pred barom grafu, s ktorym sa uzavrel.</summary>
        private void ProcessBars()
        {
            if (_engine == null || _chart == null) return;
            DateTime now = NinjaTrader.Core.Globals.Now;
            while (!_stopRequested)
            {
                Candle c = ClosedAt(_chart, _chart.Fed, now);
                if (c == null) break;
                FeedHtfUpTo(c.Time, now);
                _chart.Fed++;
                OnChartBar(c, _chart.Fed - 1, now);
            }
            SpoolMinutes(now);
        }

        /// <summary>Uzavrete 1m bary, ktore v spoole este nie su (`m1`); predhistoria najviac `MinuteBackfill` minut.</summary>
        private void SpoolMinutes(DateTime now)
        {
            if (_m1Series == null || _spool == null) return;
            while (!_stopRequested)
            {
                Candle c = ClosedAt(_m1Series, _m1Spooled, now);
                if (c == null) break;
                _m1Spooled++;
                if ((now - c.Time).TotalMinutes > TB.LiveSpool.MinuteBackfill) continue;   // 1m graf ma historie viac
                _spool.Minute(ToMs(c.Time) - 60000L, c.Open, c.High, c.Low, c.Close, c.Volume);
            }
            SpoolCheck();
        }

        private void FeedHtfUpTo(DateTime chartClose, DateTime now)
        {
            if (_htfSeries == null || _htf == null) return;
            long htfMs = _htfSeries.Tf * 60000L;
            while (true)
            {
                Candle h = ClosedAt(_htfSeries, _htfSeries.Fed, now);
                if (h == null || h.Time > chartClose) break;
                _htfSeries.Fed++;
                _htfBars++;
                _htf.Feed(new TB.Bar(ToMs(h.Time) - htfMs, h.Open, h.High, h.Low, h.Close, h.Volume));
            }
        }

        private void OnChartBar(Candle c, int index, DateTime now)
        {
            TB.Bar bar = new TB.Bar(ToMs(c.Time) - _stepMs, c.Open, c.High, c.Low, c.Close, c.Volume);
            if (_chartBars++ == 0) _firstBarMs = bar.Time;
            _lastBarMs = bar.Time;
            _lastClose = c.Close;
            int replays = _replays;
            if (_live) ControlCheck();   // moze vymenit engine (profil) - vtedy sa historia prehra znova a tento bar uz je v nej
            if (_engine == null || replays != _replays) return;
            _engineBars++;

            UpdateTrailing(bar);

            TB.MarketContext ctx = new TB.MarketContext();
            int tracked = 0;
            foreach (KeyValuePair<string, Tracked> kv in _orders)
                if (kv.Value.Filled && kv.Value.OpenQty > 0)
                    tracked += (kv.Value.Intent.Plan.Direction == TB.Direction.Long ? 1 : -1) * kv.Value.OpenQty;
            // vlastna pozicia hned (PositionUpdate uctu chodi o chvilu neskor), inak pozicia uctu (cudzia / z predosleho behu)
            ctx.PositionSize = tracked != 0 ? tracked : AccountPosition();
            // Market vstup, ktory uz odisiel, ale fill este neprisiel, sa pocita ako pozicia (inak engine
            // posle dalsi a dalsi - 25. 9. 2026 ORB 20 market orderov v jednej sekunde).
            foreach (KeyValuePair<string, Tracked> kv in _orders)
            {
                Tracked p = kv.Value;
                if (p.Filled || p.Parked || p.Intent.OrderType != TB.OrderType.Market || p.Intent.Plan == null) continue;
                if (p.Entry == null || !Alive(p.Entry)) continue;
                ctx.PositionSize += (p.Intent.Plan.Direction == TB.Direction.Long ? 1 : -1) * Math.Max(1, Math.Round(p.Intent.Plan.Qty));
            }
            string day = UtcDay(bar.Time);
            int winsSeen;
            ctx.DailyWinLimitReached = _maxDailyWins > 0 && _dailyWinsSeen.TryGetValue(day, out winsSeen) && winsSeen >= _maxDailyWins;
            foreach (KeyValuePair<string, Tracked> kv in _orders)
                if (kv.Value.Filled && kv.Value.OpenQty > 0) ctx.OpenOrderIds.Add(kv.Key);

            TB.HtfWindow window = _htf != null ? _htf.WindowFor(bar.Time) : null;
            TB.EngineOutput output = _engine.OnBar(bar, window, ctx);

            // Predhistoria sa neobchoduje (ready=false); nazivo az po plnej predhistorii enginu.
            bool ready = _live && index >= _engine.RequiredHistory && _engineBars > _engine.RequiredHistory;
            if (_live && (now - c.Time).TotalSeconds > 2 * Deployment.Tf * 60)
            {
                ready = false;
                if (_staleLogged++ < 5)
                    Note("warn", "bar " + c.Time.ToString("HH:mm", CultureInfo.InvariantCulture) + " prisiel neskoro ("
                         + (int)(now - c.Time).TotalSeconds + " s) - bez vstupu");
            }
            if (_spool != null) { _spool.Bar(bar, output, ready, ctx.MarketBias); SpoolCheck(); }
            foreach (TB.OrderIntent intent in output.Orders) Apply(intent, ready);
            if (output.CloseSession) Flatten("tb_session_end");

            int total;
            lock (_chart.Gate) total = _chart.Bars.Count;
            if (_spool != null && (_live || index >= total - 2))
            {
                List<TB.DrawCommand> finals = _engine.FinalDrawings(bar);
                _spool.FinalDrawings(bar, finals);
                SpoolCheck();
            }

            int winsNow;
            if (_dailyWins.TryGetValue(day, out winsNow)) _dailyWinsSeen[day] = winsNow;
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

        private static string UtcDay(long ms)
        {
            return Epoch.AddMilliseconds(ms).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        }

        // ------------------------------------------------------------------ //
        // Ordery (Account API): vstup = order s menom id, vystupy `<id>:sl`, `<id>:tp` (OCO), `<id>:tb_*` trhovo
        // ------------------------------------------------------------------ //

        private double Tick(double price) { return _inst.MasterInstrument.RoundToTickSize(price); }

        private static bool Alive(Order o)
        {
            if (o == null) return false;
            OrderState s = o.OrderState;
            return s != OrderState.Cancelled && s != OrderState.Rejected && s != OrderState.Filled && s != OrderState.Unknown;
        }

        /// <summary>Pozicia uctu na instrumente (aj cudzia - napr. z predosleho behu alebo z grafu).</summary>
        private int AccountPosition()
        {
            double price;
            return AccountPosition(out price);
        }

        private int AccountPosition(out double avgPrice)
        {
            avgPrice = 0;
            try
            {
                lock (_account.Positions)
                    foreach (Position p in _account.Positions)
                        if (p.Instrument != null && p.Instrument.FullName == _inst.FullName)
                        {
                            avgPrice = p.AveragePrice;
                            return p.MarketPosition == MarketPosition.Long ? p.Quantity : (p.MarketPosition == MarketPosition.Short ? -p.Quantity : 0);
                        }
            }
            catch (Exception e) { Log("Positions: " + e.Message); }
            return 0;
        }

        /// <summary>Pozicia uctu na instrumente do pingu `hb` - webapp z nej vidi, ci pozicia u brokera naozaj je
        /// (`account`: cely ucet, aj ine instancie na tom istom instrumente). Spool zapise len zmenu.</summary>
        private void SpoolBroker()
        {
            if (_spool == null || _account == null || _inst == null) return;
            double price;
            int qty = AccountPosition(out price);
            _spool.Broker(qty, qty != 0 ? price : 0.0, "account");
            SpoolCheck();
        }

        private static string ExitName(string suffix)
        {
            if (suffix == "sl") return "Stop loss";
            if (suffix == "tp") return "Profit target";
            return suffix;
        }

        private void Apply(TB.OrderIntent intent, bool ready)
        {
            Tracked t;
            if (intent.Action == TB.OrderAction.Entry)
            {
                if (!ready || intent.Plan == null) return;
                if (_controlMode != "enabled")
                {
                    Log("ENTRY " + intent.OrderId + " zahodeny - rezim " + _controlMode);
                    return;
                }
                if (_orders.TryGetValue(intent.OrderId, out t) && t.Filled && t.OpenQty > 0) return;
                Tracked previous = t;
                t = new Tracked();
                t.Intent = intent;
                t.LastStop = intent.Plan.StopLoss;
                _orders[intent.OrderId] = t;
                if (HasOpenPosition())
                {
                    t.Parked = true;
                    if (previous != null && !previous.Filled && previous.Entry != null) CancelOrder(previous.Entry);
                    Log("ENTRY " + intent.OrderId + " odlozeny - bezi pozicia");
                    return;
                }
                SubmitEntry(intent.OrderId, t);
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
                Log("CANCEL " + intent.OrderId + " (" + intent.Reason + ")");
            }
            else if (intent.Action == TB.OrderAction.Close)
            {
                if (t.Filled && t.OpenQty > 0) RequestClose(intent.OrderId, t, "tb_close");
                Log("CLOSE " + intent.OrderId + " (" + intent.Reason + ")");
            }
        }

        private Order Create(OrderAction action, OrderType type, int qty, double limit, double stop, string oco, string name)
        {
            return _account.CreateOrder(_inst, action, type, OrderEntry.Automated, TimeInForce.Gtc, qty, limit, stop, oco, name,
                                        NinjaTrader.Core.Globals.MaxDate, null);
        }

        private void SubmitEntry(string id, Tracked t)
        {
            TB.OrderIntent intent = t.Intent;
            TB.TradePlan plan = intent.Plan;
            int qty = (int)Math.Max(1, Math.Round(plan.Qty));
            bool isLong = plan.Direction == TB.Direction.Long;
            OrderAction action = isLong ? OrderAction.Buy : OrderAction.SellShort;
            try
            {
                Order order;
                if (intent.OrderType == TB.OrderType.Market) order = Create(action, OrderType.Market, qty, 0, 0, "", id);
                else if (intent.OrderType == TB.OrderType.Stop) order = Create(action, OrderType.StopMarket, qty, 0, Tick(plan.Entry), "", id);
                else order = Create(action, OrderType.Limit, qty, Tick(plan.Entry), 0, "", id);
                t.Entry = order;
                t.SentMs = (long)Math.Round((DateTime.UtcNow - Epoch).TotalMilliseconds);
                _account.Submit(new Order[] { order });
                Log("ENTRY " + id + " " + intent.OrderType + " @" + plan.Entry + " SL " + plan.StopLoss + " TP " + plan.TakeProfit + " qty " + qty);
            }
            catch (Exception e)
            {
                Note("error", "vstup " + id + " sa neposlal - " + e.Message);
                _orders.Remove(id);
            }
        }

        /// <summary>Po vyplneni vstupu: SL (stop-market) + TP (limit) ako OCO dvojica na otvoreny objem.</summary>
        private void EnsureExits(string id, Tracked t)
        {
            TB.TradePlan plan = t.Intent.Plan;
            bool isLong = plan.Direction == TB.Direction.Long;
            OrderAction action = isLong ? OrderAction.Sell : OrderAction.BuyToCover;
            if (t.Sl == null)
            {
                try
                {
                    string oco = "tb" + (++_ocoSeq).ToString(CultureInfo.InvariantCulture) + "-" + Guid.NewGuid().ToString("N").Substring(0, 8);
                    t.Sl = Create(action, OrderType.StopMarket, t.OpenQty, 0, Tick(t.LastStop), oco, id + ":sl");
                    t.Tp = Create(action, OrderType.Limit, t.OpenQty, Tick(plan.TakeProfit), 0, oco, id + ":tp");
                    _account.Submit(new Order[] { t.Sl, t.Tp });
                    Log("EXITS " + id + " SL " + Tick(t.LastStop) + " TP " + Tick(plan.TakeProfit) + " qty " + t.OpenQty + " oco " + oco);
                }
                catch (Exception e)
                {
                    // neodoslane - GuardExits ich polozi znova, po MaxExitAttempts pozicia ide von trhom
                    t.Sl = null;
                    t.Tp = null;
                    Note("error", "vystupy " + id + " sa neposlali - " + e.Message);
                }
                return;
            }
            try
            {
                // dalsi ciastocny fill: navys objem vystupov
                List<Order> change = new List<Order>();
                if (Alive(t.Sl)) { t.Sl.QuantityChanged = t.OpenQty; change.Add(t.Sl); }
                if (Alive(t.Tp)) { t.Tp.QuantityChanged = t.OpenQty; change.Add(t.Tp); }
                if (change.Count > 0) _account.Change(change);
            }
            catch (Exception e) { Note("error", "objem vystupov " + id + " sa nezmenil - " + e.Message); }
        }

        /// <summary>
        /// Pozicia nesmie ostat bez stopu (audit N-LIVE-1, N-LIVE-11): vyplneny vstup, ktory nema zivy SL (neodoslany,
        /// odmietnuty, zruseny zvonka), dostane SL/TP znova; po `MaxExitAttempts` neuspechoch sa zavrie trhom. Pocas
        /// zatvarania trhom plati to iste, ked uz trhovy vystup `MaxCloseAttempts` krat nepresiel (`Protect`).
        /// </summary>
        private void GuardExits()
        {
            DateTime now = DateTime.UtcNow;
            foreach (KeyValuePair<string, Tracked> kv in new List<KeyValuePair<string, Tracked>>(_orders))
            {
                Tracked t = kv.Value;
                if (!t.Filled || t.OpenQty <= 0 || (t.Closing != null && !t.Protect)) { t.NoStopSince = DateTime.MinValue; continue; }
                if (Alive(t.Sl))
                {
                    t.NoStopSince = DateTime.MinValue;
                    if (t.Sl.OrderState == OrderState.Accepted || t.Sl.OrderState == OrderState.Working) t.ExitFails = 0;   // broker ho prijal
                    continue;
                }
                // vystup sa prave vyplnil - pozicia sa zavrie sama (HandleExecution)
                if ((t.Sl != null && t.Sl.OrderState == OrderState.Filled) || (t.Tp != null && t.Tp.OrderState == OrderState.Filled)) continue;
                if (t.NoStopSince == DateTime.MinValue) { t.NoStopSince = now; if (!t.Protect) continue; }
                if (!t.Protect && (now - t.NoStopSince).TotalSeconds < NoStopGraceSeconds) continue;
                // TP z neuplnej dvojice najprv prec (inak by po novej dvojici stali dva TP)
                if (Alive(t.Tp)) { CancelOrder(t.Tp); continue; }
                if (AccountPosition() == 0) continue;   // ucet flat - pozicia sa zavrela inde (ReconcileExternal)
                if (t.ExitFails >= MaxExitAttempts)
                {
                    if (t.Closing != null) continue;    // trhovy vystup uz bezi (CloseTimeouts)
                    Note("error", "pozicia " + kv.Key + " je bez SL a polozit ho " + t.ExitFails + "x zlyhalo - zatvaram trhom");
                    RequestClose(kv.Key, t, "tb_close");
                    continue;
                }
                Note("warn", "pozicia " + kv.Key + " nema SL - pokladam SL/TP znova (pokus " + (t.ExitFails + 1) + ")");
                t.Sl = null;
                t.Tp = null;
                t.NoStopSince = now;
                t.ExitFails++;
                EnsureExits(kv.Key, t);
            }
        }

        /// <summary>Zavretie pozicie trhovym orderom: najprv zrus SL/TP, trhovy vystup ide, az ked su prec
        /// (inak by sa SL mohol vyplnit v tej istej sekunde a trhovy order by otvoril opacnu poziciu).</summary>
        private void RequestClose(string id, Tracked t, string signal)
        {
            if (t.Closing != null) return;
            t.Closing = signal;
            t.ClosingSince = DateTime.UtcNow;
            List<Order> cancel = new List<Order>();
            if (Alive(t.Sl)) cancel.Add(t.Sl);
            if (Alive(t.Tp)) cancel.Add(t.Tp);
            if (cancel.Count == 0) { SubmitCloseMarket(id, t); return; }
            try { _account.Cancel(cancel); }
            catch (Exception e) { Note("error", "zrusenie SL/TP " + id + " zlyhalo - " + e.Message); SubmitCloseMarket(id, t); }
        }

        private void SubmitCloseMarket(string id, Tracked t)
        {
            if (t.CloseSent || t.OpenQty <= 0) return;
            t.CloseSent = true;
            bool isLong = t.Intent.Plan.Direction == TB.Direction.Long;
            try
            {
                Order o = Create(isLong ? OrderAction.Sell : OrderAction.BuyToCover, OrderType.Market, t.OpenQty, 0, 0, "", id + ":" + t.Closing);
                _account.Submit(new Order[] { o });
                Log("EXIT " + id + " market x" + t.OpenQty + " (" + t.Closing + ")");
            }
            catch (Exception e) { CloseFailed(id, t, "trhovy vystup " + id + " sa neposlal - " + e.Message); }
        }

        /// <summary>
        /// Trhovy vystup nepresiel (odmietnuty, neodoslany): dalsi pokus s odstupom 2, 4, 8 ... 60 s, nie kazde 2 s
        /// (audit N-LIVE-2). Od `MaxCloseAttempts`. neuspechu stoja medzi pokusmi SL/TP znova (GuardExits) - pozicia
        /// cez noc bez stopu nesmie ostat; pred dalsim pokusom sa zrusia ako pri prvom.
        /// </summary>
        private void CloseFailed(string id, Tracked t, string message)
        {
            t.CloseSent = false;
            t.CloseFails++;
            int wait = Math.Min(60, 1 << Math.Min(6, t.CloseFails));
            t.CloseRetryAt = DateTime.UtcNow.AddSeconds(wait);
            bool protect = t.CloseFails >= MaxCloseAttempts;
            if (protect && !t.Protect) { t.Protect = true; t.ExitFails = 0; t.NoStopSince = DateTime.MinValue; }
            Note("error", message + " (" + t.CloseFails + ". neuspech, dalsi pokus o " + wait + " s"
                 + (protect ? ", medzitym SL/TP znova" : "") + ")");
        }

        /// <summary>Zatvaranie trhom: zrusenie SL/TP sa nepotvrdilo do limitu - trhovy vystup ide aj tak; odmietnuty
        /// trhovy vystup ide znova po odstupe (pri `Protect` najprv znova zrusit SL/TP).</summary>
        private void CloseTimeouts()
        {
            DateTime now = DateTime.UtcNow;
            foreach (KeyValuePair<string, Tracked> kv in new List<KeyValuePair<string, Tracked>>(_orders))
            {
                Tracked t = kv.Value;
                if (t.Closing == null || t.CloseSent || t.OpenQty <= 0) continue;
                if (now < t.CloseRetryAt) continue;
                if (t.Protect)
                {
                    // SL/TP stoja z GuardExits - dalsi pokus rovnako ako prvy: zrusit, trhovy vystup az ked su prec
                    t.Protect = false;
                    t.ClosingSince = now;
                    List<Order> cancel = new List<Order>();
                    if (Alive(t.Sl)) cancel.Add(t.Sl);
                    if (Alive(t.Tp)) cancel.Add(t.Tp);
                    if (cancel.Count == 0) { SubmitCloseMarket(kv.Key, t); continue; }
                    try { _account.Cancel(cancel); }
                    catch (Exception e) { Note("error", "zrusenie SL/TP " + kv.Key + " zlyhalo - " + e.Message); SubmitCloseMarket(kv.Key, t); }
                    continue;
                }
                bool gone = Gone(t.Sl) && Gone(t.Tp);
                if (!gone && (now - t.ClosingSince).TotalSeconds < CloseCancelTimeoutSeconds) continue;
                if (!gone) Note("warn", "zrusenie SL/TP " + kv.Key + " sa nepotvrdilo do " + CloseCancelTimeoutSeconds + " s - trhovy vystup posielam aj tak");
                SubmitCloseMarket(kv.Key, t);
            }
        }

        private void CancelOrder(Order o)
        {
            if (!Alive(o)) return;
            try { _account.Cancel(new Order[] { o }); }
            catch (Exception e) { Note("error", "zrusenie " + o.Name + " zlyhalo - " + e.Message); }
        }

        /// <summary>Bezi pozicia: vyplneny vstup, odoslany market vstup bez fillu, alebo (cudzia) pozicia uctu.</summary>
        private bool HasOpenPosition()
        {
            foreach (KeyValuePair<string, Tracked> kv in _orders)
            {
                Tracked t = kv.Value;
                if (t.Filled && t.OpenQty > 0) return true;
                if (!t.Filled && !t.Parked && t.Entry != null && t.Intent.OrderType == TB.OrderType.Market && Alive(t.Entry)) return true;
            }
            return AccountPosition() != 0;
        }

        private void ParkOthers(string filledId)
        {
            foreach (KeyValuePair<string, Tracked> kv in _orders)
            {
                Tracked t = kv.Value;
                if (kv.Key == filledId || t.Filled || t.Parked) continue;
                t.Parked = true;
                if (t.Entry != null) CancelOrder(t.Entry);
                Log("ENTRY " + kv.Key + " odlozeny - vyplnil sa " + filledId);
            }
        }

        private void ReleaseParked()
        {
            if (HasOpenPosition() || _controlMode != "enabled") return;
            foreach (KeyValuePair<string, Tracked> kv in new List<KeyValuePair<string, Tracked>>(_orders))
            {
                Tracked t = kv.Value;
                if (!t.Parked || t.Entry != null) continue;
                t.Parked = false;
                SubmitEntry(kv.Key, t);
            }
        }

        /// <summary>
        /// Pozicia zavreta mimo strategie: ucet je na instrumente flat (napr. Chart Trader Close / Flatten zrusi
        /// SL/TP a zavrie poziciu vlastnym orderom „Close“, ktory adapter ako svoj nepozna), ale strategia ma
        /// vyplneny vstup s otvorenym objemom. Bez tohto by si ho drzala navzdy (19. 10. 2026: VWAP ORB tri dni
        /// neobchodovala a hub ukazoval short, ktory u brokera nebol). Ucet musi byt flat aspon 3 s a vstup
        /// vyplneny aspon 10 s (PositionUpdate chodi po fille neskor). Ked ma na instrumente poziciu ina
        /// instancia, ucet flat nie je a toto nezasiahne.
        /// </summary>
        private DateTime _oldContractAt = DateTime.MinValue;
        private string _oldContractWarned = "";

        /// <summary>
        /// Rollover: po zmene symbolu nasadenia (MNQ 12-26 -> MNQ 03-27) ostava pozicia a jej SL/TP na starom kontrakte.
        /// Instancia ich nespravuje (trailing, EOD, strazca SL) a zavriet ich nemoze - prikazy posiela na novy kontrakt,
        /// kde by zatvorenie otvorilo novu poziciu. Preto aspon alarm, kym tam nieco je (audit N-LIVE-22).
        /// </summary>
        private void OldContractCheck()
        {
            if ((DateTime.UtcNow - _oldContractAt).TotalSeconds < 30) return;
            _oldContractAt = DateTime.UtcNow;
            string master = _inst.MasterInstrument.Name;
            List<string> stare = new List<string>();
            lock (_account.Positions)
                foreach (Position p in _account.Positions)
                    if (p.Instrument != null && p.Instrument.MasterInstrument.Name == master && p.Instrument.FullName != _inst.FullName
                        && p.MarketPosition != MarketPosition.Flat)
                        stare.Add(p.Instrument.FullName + " pozicia " + (p.MarketPosition == MarketPosition.Long ? "long " : "short ") + p.Quantity);
            lock (_account.Orders)
                foreach (Order o in _account.Orders)
                    if (o.Instrument != null && o.Instrument.MasterInstrument.Name == master && o.Instrument.FullName != _inst.FullName
                        && Alive(o) && !string.IsNullOrEmpty(o.Name) && o.Name.Contains(":"))
                        stare.Add(o.Instrument.FullName + " order " + o.Name);
            string text = string.Join(", ", stare.ToArray());
            if (text == _oldContractWarned) return;
            _oldContractWarned = text;
            if (text.Length > 0)
                Note("error", "rollover: na starom kontrakte ostalo " + text + " - instancia to nespravuje (SL/TP, trailing, EOD), "
                     + "zavri to rucne v NinjaTraderi");
        }

        private void ReconcileExternal()
        {
            // Pri vypadku spojenia `_account.Positions` chvilu pozicie nema (kym sa ucet nezosynchronizuje) - bez tejto
            // brany by po 3 s vznikol falosny vystup 'close', zrusili by sa SL/TP a po reconnecte by pozicia ostala
            // bez stopu (audit N-LIVE-12).
            if (_account == null || _account.ConnectionStatus != ConnectionStatus.Connected)
            {
                _connectedSince = DateTime.MinValue;
                _extFlatSince = DateTime.MinValue;
                return;
            }
            if (_connectedSince == DateTime.MinValue) _connectedSince = DateTime.UtcNow;
            if ((DateTime.UtcNow - _connectedSince).TotalSeconds < 30) { _extFlatSince = DateTime.MinValue; return; }
            bool open = false;
            foreach (KeyValuePair<string, Tracked> kv in _orders)
                if (kv.Value.Filled && kv.Value.OpenQty > 0 && (DateTime.UtcNow - kv.Value.FilledAt).TotalSeconds >= 10) open = true;
            if (!open || AccountPosition() != 0) { _extFlatSince = DateTime.MinValue; return; }
            if (_extFlatSince == DateTime.MinValue) { _extFlatSince = DateTime.UtcNow; return; }
            if ((DateTime.UtcNow - _extFlatSince).TotalSeconds < 3) return;
            _extFlatSince = DateTime.MinValue;
            bool known = _foreignMs > 0;
            double price = known ? _foreignPrice : _lastClose;
            long ms = known ? _foreignMs : (long)Math.Round((DateTime.UtcNow - Epoch).TotalMilliseconds);
            foreach (KeyValuePair<string, Tracked> kv in new List<KeyValuePair<string, Tracked>>(_orders))
            {
                Tracked t = kv.Value;
                if (!t.Filled || t.OpenQty <= 0) continue;
                Note("warn", "pozicia " + kv.Key + " (" + t.OpenQty + " ks) zavreta mimo strategie (napr. Chart Trader Close / Flatten) - "
                     + "zapisany vystup 'close' @" + price.ToString(CultureInfo.InvariantCulture) + (known ? "" : " (cena posledneho baru)"));
                if (_spool != null) { _spool.Fill(ms, kv.Key, false, "close", price, t.OpenQty, _live); SpoolCheck(); }
                if (Alive(t.Sl)) CancelOrder(t.Sl);
                if (Alive(t.Tp)) CancelOrder(t.Tp);
                _orders.Remove(kv.Key);
            }
            _foreignMs = 0;
        }

        /// <summary>
        /// Engine s koncom dna (EOD) chce byt od 15:58:30 NY flat aj vtedy, ked bar pred 15:59 neprisiel (reconnect,
        /// zamrznuty feed) - zatvorenie podla hodin, nie podla baru (audit N-LIVE-7). Bezne uz zatvoril bar.
        /// </summary>
        private void EodByClock()
        {
            TB.IClockFlatten clock = TB.ClockFlatten.Find(_engine);
            if (clock == null) return;
            long nowMs = (long)Math.Round((DateTime.UtcNow - Epoch).TotalMilliseconds);
            if (!clock.FlattenDue(nowMs)) return;
            bool work = false;
            foreach (KeyValuePair<string, Tracked> kv in _orders)
                if ((kv.Value.Filled && kv.Value.OpenQty > 0 && kv.Value.Closing == null) || (!kv.Value.Filled && kv.Value.Entry != null)) work = true;
            if (!work) return;
            string day = DateTime.UtcNow.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            if (_eodClockDay != day)
            {
                _eodClockDay = day;
                Note("warn", "EOD podla hodin: bar pred 15:59 NY neprisiel (posledny " + LastBarText() + ") - zatvaram a rusim cakajuce vstupy");
            }
            Flatten("tb_session_end");
        }

        private string LastBarText()
        {
            return _lastBarMs > 0 ? Epoch.AddMilliseconds(_lastBarMs + _stepMs).ToString("HH:mm", CultureInfo.InvariantCulture) + " UTC" : "ziadny";
        }

        /// <summary>
        /// Pocas seansy instrumentu (TradingHours) musi kazdy TF prist bar; ked posledny uzavrety je starsi nez 2 TF + 1 min,
        /// feed alebo BarsRequest je mrtvy - `note error` (webapp, Telegram), znova kazdych 15 min, kym bary nezacnu
        /// chodit (audit N-LIVE-7: `hb` ide dalej a webapp by hlasila len „trh zatvoreny").
        /// </summary>
        private void FeedWatch()
        {
            if (_chart == null || _lastBarMs <= 0) return;
            long nowMs = (long)Math.Round((DateTime.UtcNow - Epoch).TotalMilliseconds);
            bool late = nowMs > _lastBarMs + 2 * _stepMs + 60000L;
            if (!late)
            {
                if (_feedStale) { _feedStale = false; Note("info", "bary znova chodia (posledny " + LastBarText() + ")"); }
                return;
            }
            if (!InSession(NinjaTrader.Core.Globals.Now)) return;
            if (_feedStale && (DateTime.UtcNow - _feedNoted).TotalMinutes < 15) return;
            _feedStale = true;
            _feedNoted = DateTime.UtcNow;
            Note("error", "pocas seansy neprisiel bar " + (int)((nowMs - _lastBarMs - _stepMs) / 60000L) + " min (posledny " + LastBarText()
                 + ") - feed alebo pripojenie (" + Deployment.Connection + "), trailing a zatvorenie na bare stoja");
        }

        /// <summary>Cas platformy je v obchodnej seanse instrumentu; ked sa to zistit neda, berie sa ako v seanse (radsej alarm navyse).</summary>
        private bool InSession(DateTime platformNow)
        {
            try
            {
                if (_sessions == null) _sessions = new NinjaTrader.Data.SessionIterator(_inst.MasterInstrument.TradingHours);
                return _sessions.IsInSession(platformNow, true, true);
            }
            catch (Exception e)
            {
                Log("seansa instrumentu sa neda zistit - " + e.Message);
                return true;
            }
        }

        /// <summary>Zrus cakajuce vstupy a zavri, co je otvorene (koniec seansy, flatten).</summary>
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
                else if (t.OpenQty > 0) RequestClose(kv.Key, t, signal);
            }
        }

        private void UpdateTrailing(TB.Bar bar)
        {
            foreach (KeyValuePair<string, Tracked> kv in _orders)
            {
                Tracked t = kv.Value;
                TB.TradePlan plan = t.Intent.Plan;
                if (!t.Filled || t.OpenQty <= 0 || plan == null || plan.Trailing == null || t.Closing != null) continue;
                bool isLong = plan.Direction == TB.Direction.Long;
                double prev = t.Extreme.HasValue ? t.Extreme.Value : plan.Entry;
                double best = isLong ? Math.Max(prev, bar.High) : Math.Min(prev, bar.Low);
                t.Extreme = best;
                double stop = plan.Trailing.StopPrice(plan.Direction, plan.Entry, plan.StopLoss, best);
                bool better = isLong ? stop > t.LastStop : stop < t.LastStop;
                if (!better) continue;
                if (Alive(t.Sl))
                {
                    try
                    {
                        t.Sl.StopPriceChanged = Tick(stop);
                        _account.Change(new Order[] { t.Sl });
                        Log("TRAIL " + kv.Key + " SL -> " + Tick(stop));
                    }
                    // LastStop ostava stara - posun sa skusi na dalsom bare znova (audit N-LIVE-10)
                    catch (Exception e) { Note("error", "posun SL " + kv.Key + " zlyhal - " + e.Message); continue; }
                }
                t.LastStop = stop;   // bez ziveho SL ho s touto cenou polozi GuardExits
                if (_spool != null) { _spool.Modify(bar.Time, kv.Key, Tick(stop), null, "trailing", _live); SpoolCheck(); }
            }
        }

        // ------------------------------------------------------------------ //
        // Udalosti uctu (NT vlakno -> fronta -> vlakno instancie)
        // ------------------------------------------------------------------ //

        private bool Ours(Order o)
        {
            return o != null && o.Instrument != null && o.Instrument.FullName == _inst.FullName && !string.IsNullOrEmpty(o.Name);
        }

        private void OnOrderUpdate(object sender, OrderEventArgs e)
        {
            try
            {
                Order o = e.Order;
                if (!Ours(o)) return;
                OrderState state = e.OrderState;
                ErrorCode error = e.Error;
                string comment = e.Comment;
                Post(delegate { HandleOrder(o, state, error, comment); });
            }
            catch (Exception ex) { Log("OrderUpdate: " + ex.Message); }
        }

        private void HandleOrder(Order o, OrderState state, ErrorCode error, string comment)
        {
            Tracked t;
            string name = o.Name;
            if (_orders.TryGetValue(name, out t))
            {
                // vstup
                if (t.Entry != null && !ReferenceEquals(t.Entry, o)) return;   // neskora sprava o starom orderi s tym istym menom
                if (state == OrderState.Rejected) Note("error", "vstup " + name + " odmietnuty: " + error + " " + comment);
                if ((state == OrderState.Cancelled || state == OrderState.Rejected) && !t.Filled)
                {
                    if (t.Parked && state == OrderState.Cancelled)
                    {
                        t.Entry = null;
                        ReleaseParked();
                    }
                    else _orders.Remove(name);
                }
                return;
            }
            int colon = name.LastIndexOf(':');
            if (colon <= 0) return;
            string id = name.Substring(0, colon);
            string suffix = name.Substring(colon + 1);
            if (!_orders.TryGetValue(id, out t)) return;
            bool exit = suffix == "sl" || suffix == "tp";
            if (state == OrderState.Rejected)
            {
                if (!exit)
                {
                    // trhovy vystup - CloseTimeouts ho posle znova po odstupe
                    CloseFailed(id, t, "vystup " + name + " odmietnuty: " + error + " " + comment);
                    return;
                }
                Note("error", "vystup " + name + " odmietnuty: " + error + " " + comment);
                if (suffix == "sl" && ReferenceEquals(o, t.Sl) && Alive(o))
                {
                    // odmietnuta len ZMENA (posun trailingu) - SL stoji na starej cene; trailing to skusi na dalsom
                    // bare znova (audit N-LIVE-10, N-LIVE-11: zdrava pozicia sa kvoli tomu nezatvara)
                    t.LastStop = o.StopPrice;
                    return;
                }
            }
            if (!exit || (state != OrderState.Cancelled && state != OrderState.Rejected)) return;
            // SL/TP prec mimo zatvarania (odmietnuty, zruseny zvonka) - pozicia bez ochrany: GuardExits ho polozi
            // znova, po MaxExitAttempts zavrie trhom
            if (t.Closing == null || t.Protect) return;
            // oba vystupy prec (zrusene, nie vyplnene) -> trhovy vystup; vyplneny vystup zavrie poziciu sam (HandleExecution)
            if (!t.CloseSent && Gone(t.Sl) && Gone(t.Tp) && t.OpenQty > 0 && DateTime.UtcNow >= t.CloseRetryAt) SubmitCloseMarket(id, t);
        }

        /// <summary>Order je prec bez fillu (zruseny / odmietnuty / nikdy neposlany).</summary>
        private static bool Gone(Order o)
        {
            return o == null || o.OrderState == OrderState.Cancelled || o.OrderState == OrderState.Rejected;
        }

        private void OnExecutionUpdate(object sender, ExecutionEventArgs e)
        {
            try
            {
                if (e.Execution == null) return;
                Order o = e.Execution.Order;
                if (!Ours(o)) return;
                double price = e.Price;
                int qty = e.Quantity;
                DateTime time = e.Time;
                Post(delegate { HandleExecution(o, price, qty, time); });
            }
            catch (Exception ex) { Log("ExecutionUpdate: " + ex.Message); }
        }

        private void HandleExecution(Order o, double price, int qty, DateTime time)
        {
            Tracked t;
            string name = o.Name;
            long execMs = ToMs(time);
            if (_orders.TryGetValue(name, out t))
            {
                // vyplnenie vstupu
                if (t.Entry != null && !ReferenceEquals(t.Entry, o)) return;
                if (!t.Filled) { t.FilledAt = DateTime.UtcNow; t.FilledMs = execMs; }
                t.Filled = true;
                t.Parked = false;
                t.OpenQty += qty;
                Log("FILL in " + name + " @" + price + " x" + qty);
                if (_spool != null) { _spool.Fill(execMs, name, true, "", price, qty, _live); SpoolCheck(); }
                ParkOthers(name);
                EnsureExits(name, t);
                return;
            }
            int colon = name.LastIndexOf(':');
            if (colon <= 0 || !_orders.TryGetValue(name.Substring(0, colon), out t))
            {
                // cudzi order (Chart Trader Close / Flatten, ine okno, ina instancia) - cena pre ReconcileExternal
                _foreignPrice = price;
                _foreignMs = execMs;
                return;
            }
            string id = name.Substring(0, colon);
            string suffix = name.Substring(colon + 1);
            string exitName = ExitName(suffix);
            Log("FILL out " + id + " " + exitName + " @" + price + " x" + qty);
            if (_spool != null) { _spool.Fill(execMs, id, false, exitName, price, qty, _live); SpoolCheck(); }
            t.OpenQty -= qty;
            if (t.OpenQty > 0) return;
            // druhy z OCO dvojice zrusi NT sam; keby nie, stiahni ho
            if (suffix == "sl" && Alive(t.Tp)) CancelOrder(t.Tp);
            if (suffix == "tp" && Alive(t.Sl)) CancelOrder(t.Sl);
            _orders.Remove(id);
            ReleaseParked();

            CountWin(t.Intent.Plan, suffix, price, execMs);
        }

        /// <summary>Pine `dailyWinsCount`: vyhra = uzavrety obchod so ziskom > 0; zavretie koncom seansy / close sa nepocita.</summary>
        private void CountWin(TB.TradePlan plan, string suffix, double price, long execMs)
        {
            if (suffix != "sl" && suffix != "tp") return;
            double move = plan.Direction == TB.Direction.Long ? price - plan.Entry : plan.Entry - price;
            if (move <= 0) return;
            string day = UtcDay(execMs);
            int wins;
            _dailyWins.TryGetValue(day, out wins);
            _dailyWins[day] = wins + 1;
        }

        // ------------------------------------------------------------------ //
        // Control subor (docs/LIVE.md, faza 2): mode + profil; profil sa meni len flat, s prehratim historie
        // ------------------------------------------------------------------ //

        private void ControlEvent(string source)
        {
            _controlEvents++;
            Log("control: rezim " + _controlMode + ", profil '" + (_controlProfile ?? "") + "' (" + source + ")");
            if (_spool != null) { _spool.Control(_controlMode, _controlProfile ?? "", source); SpoolCheck(); }
        }

        private void ControlInit()
        {
            try
            {
                _controlPath = Path.Combine(TradeBotLiveAddOn.ControlDir, _instance + ".json");
                Log("control subor " + _controlPath);
                bool exists = ControlCheck();
                if (_controlEvents == 0) ControlEvent(exists ? "control" : "default");
            }
            catch (Exception e) { Note("error", "control init zlyhal - " + e.Message); }
        }

        private bool ControlCheck()
        {
            if (_controlPath == null) return false;
            try
            {
                if (!File.Exists(_controlPath))
                {
                    if (_controlSeen)
                    {
                        _controlSeen = false;
                        _controlMtime = DateTime.MinValue;
                        ControlApply("enabled", Deployment.Profile, "default");
                    }
                    return false;
                }
                DateTime mtime = File.GetLastWriteTimeUtc(_controlPath);
                if (mtime != _controlMtime)
                {
                    _controlMtime = mtime;
                    _controlSeen = true;
                    Dictionary<string, object> d = TB.Json.ParseObject(File.ReadAllText(_controlPath));
                    string mode = TB.Json.GetString(d, "mode", "enabled");
                    string profile = TB.Json.GetString(d, "profile", "");
                    if (mode != "enabled" && mode != "paused" && mode != "flatten")
                    {
                        Note("error", "control: neznamy mode '" + mode + "' - ignorujem");
                        return true;
                    }
                    ControlApply(mode, string.IsNullOrEmpty(profile) ? _controlProfile : profile, "control");
                }
                else if (_pendingProfile != null)
                {
                    bool ok = TrySwitchProfile();
                    if (ok || _pendingProfile == null) ControlEvent("control");
                }
                return true;
            }
            catch (Exception e)
            {
                Note("error", "control: citanie " + _controlPath + " zlyhalo - " + e.Message);
                return true;
            }
        }

        private void ControlApply(string mode, string profile, string source)
        {
            bool changed = false;
            if (mode != _controlMode)
            {
                string before = _controlMode;
                _controlMode = mode;
                changed = true;
                if (mode == "flatten") { Flatten("tb_flatten"); Log("FLATTEN (control)"); }
                else if (mode == "enabled" && before != "enabled") ReleaseParked();
            }
            string wanted = profile ?? "";
            if (wanted != (_controlProfile ?? ""))
            {
                _pendingProfile = wanted;
                _pendingLogged = false;
                bool ok = TrySwitchProfile();
                if (!ok && _pendingProfile != null)
                {
                    if (changed) ControlEvent(source);
                    return;
                }
                changed = true;
            }
            if (changed || source == "default") ControlEvent(source);
        }

        private bool IsFlat()
        {
            return _orders.Count == 0 && AccountPosition() == 0;
        }

        /// <summary>Vymena profilu, ked je instancia flat: novy engine, novy spool (nova session) a historia
        /// z BarsRequest sa prehra znova - vysledok je ako cerstvy start. Iny informativny TF = novy BarsRequest.</summary>
        private bool TrySwitchProfile()
        {
            string wanted = _pendingProfile;
            if (wanted == null) return false;
            if (!IsFlat())
            {
                if (!_pendingLogged)
                {
                    _pendingLogged = true;
                    Log("control: profil '" + wanted + "' caka, kym bude instancia flat");
                    if (_spool != null) { _spool.Control(_controlMode, wanted, "pending"); SpoolCheck(); }
                }
                return false;
            }
            _pendingProfile = null;
            string path = ResolveProfilePath(Deployment.Strategy, wanted);
            if (path == null)
            {
                Note("error", "control: profil '" + wanted + "' sa nenasiel; bezi dalej '" + _controlProfile + "'");
                return false;
            }
            try
            {
                Dictionary<string, object> cfg = TB.Json.ParseObject(File.ReadAllText(path));
                TB.IEngine fresh = TB.EngineRegistry.Create(Deployment.Strategy, cfg, InstrumentSpec(), Deployment.Tf);
                TB.IHtfFeeder feeder = fresh.CreateHtfFeeder();
                bool setupPhase = _chart == null;   // pred BarsRequest: serie a prehratie spravi Setup s novym enginom
                int oldTf = _htfSeries != null ? _htfSeries.Tf : 0;
                int newTf = feeder != null ? feeder.TfMinutes : 0;
                Series htfSeries = _htfSeries;
                if (!setupPhase && newTf != oldTf)
                {
                    htfSeries = null;
                    if (newTf > 0)
                    {
                        htfSeries = RequestSeries(newTf, HtfBarsBack(Deployment.Tf, newTf, fresh.RequiredHistory * 2 + 5));
                        if (htfSeries == null)
                        {
                            Note("error", "control: BarsRequest " + newTf + "m pre profil '" + wanted + "' zlyhal; bezi dalej '" + _controlProfile + "'");
                            return false;
                        }
                    }
                    if (_htfSeries != null) DisposeSeries(_htfSeries);
                }
                // stary engine konci: stat + bye, novy profil = nova session spoolu
                if (_spool != null) { WriteStats(); _spool.Close("profile_switch"); _spool = null; }
                _engine = fresh;
                _htf = feeder;
                _htfSeries = htfSeries;
                _config = cfg;
                _orders.Clear();
                _dailyWins.Clear();
                _dailyWinsSeen.Clear();
                ReadStats();
                _controlProfile = wanted;
                OpenSpool(wanted);
                Log("control: novy engine z profilu '" + wanted + "' (" + path + "), predhistoria " + _engine.RequiredHistory + " barov"
                    + (setupPhase ? "" : " - prehravam historiu znova"));
                if (setupPhase) return true;
                bool wasLive = _live;
                Replay();
                _live = wasLive;
                if (_spool != null) { _spool.Realtime = _live; SpoolCheck(); }
                return true;
            }
            catch (Exception e)
            {
                Note("error", "control: profil '" + wanted + "' sa nenacital - " + e.Message + "; bezi dalej '" + _controlProfile + "'");
                return false;
            }
        }

        // ------------------------------------------------------------------ //
        // Pamat obchodov cez restart (docs/NINJATRADER.md, "Restart s otvorenymi obchodmi") - zrkadlo MT5 RestoreState
        // ------------------------------------------------------------------ //
        // AddOn sa restartuje pri zmene deploy.json, aktualizacii kodu, restarte NinjaTradera alebo Windows. Pozicia
        // ostava na ucte aj so svojimi SL/TP (GTC), ale bez pamate by ich novy beh nepoznal: ich fill by bral ako cudzi,
        // telemetria by vystup nikdy nedostala a trailing ani koniec seansy by na poziciu nesiahli (16. 10. 2026: VWAP
        // ORB short na MNQ, ktoreho stop sa vyplnil az 21. 10. pod inym behom). Stav sa preto pise pri kazdej zmene a po
        // starte sa zladi s uctom - zdroj pravdy je ucet, stav dodava plan (vstup, TP, trailing), ktory na ucte nie je.

        /// <summary>Obsah stavu: plan a stav sledovanych vstupov, denny limit vyhier a posledny bar.</summary>
        private string StateJson()
        {
            TB.JsonWriter w = new TB.JsonWriter();
            w.BeginObject().Key("v").Value(1).Key("instance").Value(_instance).Key("strategy").Value(Deployment.Strategy)
             .Key("profile").Value(_controlProfile ?? "").Key("bar_ms").Value(_lastBarMs);
            w.Key("wins").BeginObject();
            foreach (KeyValuePair<string, int> kv in _dailyWins) w.Key(kv.Key).Value(kv.Value);
            w.EndObject().Key("wins_seen").BeginObject();
            foreach (KeyValuePair<string, int> kv in _dailyWinsSeen) w.Key(kv.Key).Value(kv.Value);
            w.EndObject().Key("orders").BeginArray();
            foreach (KeyValuePair<string, Tracked> kv in _orders)
            {
                Tracked t = kv.Value;
                TB.TradePlan plan = t.Intent != null ? t.Intent.Plan : null;
                if (plan == null) continue;
                if (t.Filled ? t.OpenQty <= 0 : (t.Parked || !Alive(t.Entry))) continue;   // odlozeny vstup u brokera nie je
                w.BeginObject().Key("id").Value(kv.Key).Key("ot").Value(t.Intent.OrderType.ToString())
                 .Key("filled").Value(t.Filled).Key("filled_ms").Value(t.FilledMs).Key("sent_ms").Value(t.SentMs)
                 .Key("open_qty").Value(t.OpenQty).Key("dir").Value((int)plan.Direction).Key("entry").Value(plan.Entry)
                 .Key("sl").Value(plan.StopLoss).Key("tp").Value(plan.TakeProfit).Key("qty").Value(plan.Qty)
                 .Key("sd").Value(plan.SlDistance);
                // trailing len zakladny (aktivacia + odstup); potomok s vlastnym stopom (stop na VWAP) sa po restarte nevie
                if (plan.Trailing != null && plan.Trailing.GetType() == typeof(TB.TrailingPlan))
                    w.Key("trail").BeginObject().Key("act").Value(plan.Trailing.ActivationPriceDistance)
                     .Key("off").Value(plan.Trailing.OffsetPriceDistance).Key("act_t").Value(plan.Trailing.ActivationTicks)
                     .Key("off_t").Value(plan.Trailing.OffsetTicks).EndObject();
                else w.Key("trail").Null();
                w.Key("extreme").Value(t.Extreme).Key("last_stop").Value(t.LastStop).EndObject();
            }
            return w.EndArray().EndObject().ToString();
        }

        /// <summary>Zapise stav, ked sa zmenil (atomicky: tmp + presun). Chyba instanciu nezhodi - zaloguje sa raz.</summary>
        private void SaveState()
        {
            if (!_live || _statePath == null || _engine == null) return;
            string text;
            try { text = StateJson(); }
            catch (Exception e) { Log("stav: " + e.Message); return; }
            if (text == _stateText) return;
            try
            {
                Directory.CreateDirectory(TradeBotLiveAddOn.StateDir);
                string tmp = _statePath + ".tmp";
                File.WriteAllText(tmp, text);
                if (File.Exists(_statePath)) File.Replace(tmp, _statePath, null);
                else File.Move(tmp, _statePath);
                _stateText = text;
                _stateWarned = false;
            }
            catch (Exception e)
            {
                if (_stateWarned) return;
                _stateWarned = true;
                Note("warn", "stav obchodov sa neda zapisat do " + _statePath + " (" + e.Message + ") - po restarte ich instancia neprevezme");
            }
        }

        private List<Order> WorkingOrders()
        {
            List<Order> list = new List<Order>();
            lock (_account.Orders)
                foreach (Order o in _account.Orders)
                    if (o.Instrument != null && o.Instrument.FullName == _inst.FullName && Alive(o)) list.Add(o);
            return list;
        }

        private List<Execution> AccountExecutions()
        {
            List<Execution> list = new List<Execution>();
            lock (_account.Executions)
                foreach (Execution x in _account.Executions)
                    if (x.Instrument != null && x.Instrument.FullName == _inst.FullName && !string.IsNullOrEmpty(x.Name)) list.Add(x);
            list.Sort(delegate(Execution a, Execution b) { return a.Time.CompareTo(b.Time); });
            return list;
        }

        private static Order Named(List<Order> orders, string name)
        {
            foreach (Order o in orders) if (o.Name == name) return o;
            return null;
        }

        private static TB.OrderIntent IntentFrom(string id, Dictionary<string, object> s)
        {
            TB.Direction dir = TB.Json.GetDouble(s, "dir", 1) < 0 ? TB.Direction.Short : TB.Direction.Long;
            TB.TrailingPlan trail = null;
            Dictionary<string, object> tr = TB.Json.Get(s, "trail") as Dictionary<string, object>;
            if (tr != null)
                trail = new TB.TrailingPlan(TB.Json.GetDouble(tr, "act", 0), TB.Json.GetDouble(tr, "off", 0),
                                            TB.Json.GetDouble(tr, "act_t", 0), TB.Json.GetDouble(tr, "off_t", 0));
            TB.TradePlan plan = new TB.TradePlan(dir, TB.Json.GetDouble(s, "entry", 0), TB.Json.GetDouble(s, "sl", 0),
                                                 TB.Json.GetDouble(s, "tp", 0), TB.Json.GetDouble(s, "qty", 1), TB.Json.GetDouble(s, "sd", 0), trail);
            TB.OrderIntent intent = new TB.OrderIntent(TB.OrderAction.Entry, id, 0, "prevzaty po restarte");
            intent.Direction = dir;
            intent.Plan = plan;
            string ot = TB.Json.GetString(s, "ot", "Market");
            intent.OrderType = ot == "Limit" ? TB.OrderType.Limit : (ot == "Stop" ? TB.OrderType.Stop : TB.OrderType.Market);
            return intent;
        }

        private static void ReadCounts(Dictionary<string, object> root, string key, Dictionary<string, int> into)
        {
            Dictionary<string, object> d = TB.Json.Get(root, key) as Dictionary<string, object>;
            if (d == null) return;
            foreach (KeyValuePair<string, object> kv in d) into[kv.Key] = TB.Json.ToInt(kv.Value);
        }

        /// <summary>Trailing: najlepsia cena z barov grafu, ktore presli od `fromMs` (otvorenie baru, ms UTC).</summary>
        private double? CatchUpExtreme(TB.TradePlan plan, double? extreme, long fromMs)
        {
            if (plan.Trailing == null || _chart == null) return extreme;
            bool isLong = plan.Direction == TB.Direction.Long;
            double best = extreme.HasValue ? extreme.Value : plan.Entry;
            lock (_chart.Gate)
                foreach (Candle c in _chart.Bars)
                    if (c != null && ToMs(c.Time) - _stepMs >= fromMs) best = isLong ? Math.Max(best, c.High) : Math.Min(best, c.Low);
            return best;
        }

        /// <summary>
        /// Po predhistorii: stav spred restartu zladit s uctom. Pozicia stale bezi, ked na ucte ziju jej SL/TP
        /// (`&lt;id&gt;:sl`, `&lt;id&gt;:tp`, OCO) - prevezme sa s planom zo stavu. Co sa pocas vypadku vyplnilo (vstup s menom id,
        /// vystup `&lt;id&gt;:*`), je v exekuciach uctu: ide do spoolu ako fill a SL/TP so ziskom do denneho limitu. Vstup
        /// vyplneny pocas vypadku dostane SL/TP. Cakajuci vstup zo stavu sa u brokera zrusi - engine po predhistorii
        /// o nom nevie a platny vstup posle znova. Ine ordery a pozicie na instrumente (ine instancie, Chart Trader)
        /// sa nemenia.
        /// </summary>
        private void RestoreState()
        {
            if (_statePath == null || !File.Exists(_statePath)) return;
            Dictionary<string, object> root;
            try { root = TB.Json.ParseObject(File.ReadAllText(_statePath)); }
            catch (Exception e)
            {
                Note("warn", "stav " + _statePath + " sa neda precitat (" + e.Message + ") - obchody spred restartu sa neprevezmu");
                return;
            }
            if (TB.Json.GetString(root, "instance", "") != _instance) return;
            long savedBarMs = (long)TB.Json.GetDouble(root, "bar_ms", 0);
            ReadCounts(root, "wins", _dailyWins);
            ReadCounts(root, "wins_seen", _dailyWinsSeen);
            List<object> saved = TB.Json.Get(root, "orders") as List<object>;
            if (saved == null || saved.Count == 0) return;

            List<Order> working = WorkingOrders();
            List<Execution> execs = AccountExecutions();
            int adopted = 0, filledAway = 0, closedAway = 0, cancelled = 0, lost = 0;
            foreach (object item in saved)
            {
                Dictionary<string, object> s = item as Dictionary<string, object>;
                string id = s != null ? TB.Json.GetString(s, "id", "") : "";
                if (id.Length == 0) continue;
                TB.OrderIntent intent = IntentFrom(id, s);
                TB.TradePlan plan = intent.Plan;
                bool filled = TB.Json.GetBool(s, "filled", false);
                long inMs = (long)TB.Json.GetDouble(s, filled ? "filled_ms" : "sent_ms", 0);
                int inQty = filled ? (int)Math.Round(TB.Json.GetDouble(s, "open_qty", 0)) : 0;
                if (!filled)
                {
                    // cakajuci vstup: zvysok u brokera zrusit; co sa z neho vyplnilo pocas vypadku, sa prevezme
                    Order entry = Named(working, id);
                    if (entry != null) { CancelOrder(entry); cancelled++; }
                    double value = 0;
                    long firstMs = 0;
                    foreach (Execution x in execs)
                    {
                        long ms = ToMs(x.Time);
                        if (x.Name != id || ms < inMs - 1000) continue;
                        if (firstMs == 0) firstMs = ms;
                        inQty += x.Quantity;
                        value += x.Price * x.Quantity;
                        if (_spool != null) { _spool.Fill(ms, id, true, "", x.Price, x.Quantity, true); SpoolCheck(); }
                    }
                    if (inQty == 0) continue;
                    inMs = firstMs;
                    filledAway++;
                    Log("RESTORE " + id + ": vstup sa vyplnil pocas vypadku x" + inQty + " @" + (value / inQty));
                }
                // vystupy, ktore prebehli pocas vypadku
                int outQty = 0;
                foreach (Execution x in execs)
                {
                    long ms = ToMs(x.Time);
                    if (!x.Name.StartsWith(id + ":", StringComparison.Ordinal) || ms < inMs - 1000) continue;
                    string suffix = x.Name.Substring(id.Length + 1);
                    outQty += x.Quantity;
                    Log("RESTORE " + id + ": vystup pocas vypadku " + ExitName(suffix) + " @" + x.Price + " x" + x.Quantity);
                    if (_spool != null) { _spool.Fill(ms, id, false, ExitName(suffix), x.Price, x.Quantity, true); SpoolCheck(); }
                    CountWin(plan, suffix, x.Price, ms);
                }
                Order sl = Named(working, id + ":sl"), tp = Named(working, id + ":tp");
                int open = inQty - outQty;
                if (open <= 0)
                {
                    closedAway++;
                    if (sl != null) CancelOrder(sl);   // OCO by ich zrusilo samo; keby nie, nech neotvoria novu poziciu
                    if (tp != null) CancelOrder(tp);
                    continue;
                }
                if (sl == null && tp == null && outQty == 0)
                {
                    // ani SL/TP na ucte, ani vystup v exekuciach (NinjaTrader bol dole, exekucie spred pripojenia nema;
                    // vstup vyplneny pocas vypadku SL/TP este nema a mohol ho niekto zavriet rucne): pozicia uctu
                    // rozhodne, ci obchod este bezi - inak by nove SL/TP na flat ucte otvorili poziciu
                    int pos = AccountPosition();
                    if (Math.Sign(pos) != (int)plan.Direction || Math.Abs(pos) < open)
                    {
                        lost++;
                        Note("warn", "vstup " + id + " (" + (plan.Direction == TB.Direction.Long ? "long" : "short") + " x" + open
                             + ") spred restartu na ucte uz nie je a vystup sa v exekuciach nenasiel - neprebera sa (vystup len v historii uctu)");
                        continue;
                    }
                }
                Tracked t = new Tracked();
                t.Intent = intent;
                t.Filled = true;
                t.OpenQty = open;
                t.FilledMs = inMs;
                t.FilledAt = DateTime.UtcNow.AddMinutes(-1);   // ReconcileExternal smie hned (vyplneny davno)
                object ex = TB.Json.Get(s, "extreme");
                double? extreme = filled && ex != null ? TB.Json.ToDouble(ex) : (double?)null;
                t.Extreme = CatchUpExtreme(plan, extreme, filled && savedBarMs > 0 ? savedBarMs : inMs);
                t.LastStop = sl != null && sl.StopPrice > 0 ? sl.StopPrice : TB.Json.GetDouble(s, "last_stop", plan.StopLoss);
                _orders[id] = t;
                if (sl != null && tp != null && sl.Quantity == open && tp.Quantity == open) { t.Sl = sl; t.Tp = tp; }
                else
                {
                    // chyba jeden z vystupov alebo nesedi objem: polozit dvojicu znova
                    if (sl != null) CancelOrder(sl);
                    if (tp != null) CancelOrder(tp);
                    EnsureExits(id, t);
                }
                adopted++;
                Log("RESTORE " + id + ": prevzaty " + (plan.Direction == TB.Direction.Long ? "long" : "short") + " x" + open
                    + " vstup " + plan.Entry + " SL " + t.LastStop + " TP " + plan.TakeProfit + (plan.Trailing != null ? " s trailingom" : ""));
            }
            if (adopted + filledAway + closedAway + cancelled + lost == 0) return;
            Note("info", "po restarte prevzatych " + adopted + " pozicii (" + filledAway + " vyplnenych pocas vypadku), " + closedAway
                 + " skoncilo pocas vypadku (vystup z exekucii uctu), " + cancelled + " cakajucich vstupov zrusenych, " + lost + " sa nedalo dohladat");
        }

        // ------------------------------------------------------------------ //
        // Koniec
        // ------------------------------------------------------------------ //

        private void WriteStats()
        {
            if (_spool == null) return;
            Dictionary<string, double> stats = new Dictionary<string, double>();
            stats["adapter_chart_bars"] = _chartBars;
            stats["adapter_htf_bars"] = _htfBars;
            stats["adapter_first_bar_ms"] = _firstBarMs;
            stats["adapter_last_bar_ms"] = _lastBarMs;
            if (_engine != null)
            {
                Dictionary<string, double> engineStats = _engine.Stats();
                if (engineStats != null)
                    foreach (KeyValuePair<string, double> kv in engineStats) stats[kv.Key] = kv.Value;
            }
            _spool.Stats(stats);
        }

        private void Teardown(string reason)
        {
            Status = "stopping";
            try
            {
                if (_account != null)
                {
                    if (_orderHandler != null) _account.OrderUpdate -= _orderHandler;
                    if (_executionHandler != null) _account.ExecutionUpdate -= _executionHandler;
                }
            }
            catch (Exception) { }
            // cakajuce vstupy prec; pozicia ostava aj so svojimi SL/TP (GTC ordery na ucte) - flatten je vec control suboru
            int cancelled = 0;
            try
            {
                foreach (KeyValuePair<string, Tracked> kv in _orders)
                {
                    Tracked t = kv.Value;
                    if (!t.Filled && t.Entry != null && Alive(t.Entry)) { CancelOrder(t.Entry); cancelled++; }
                }
            }
            catch (Exception e) { Log("rusenie vstupov: " + e.Message); }
            SaveState();   // otvorene pozicie s planom pre dalsi beh
            DisposeSeries(_chart);
            DisposeSeries(_htfSeries);
            if (_m1Series != _chart) DisposeSeries(_m1Series);
            if (_spool != null)
            {
                try { WriteStats(); _spool.Close(reason); } catch (Exception) { }
                _spool = null;
            }
            Log("koniec (" + reason + "): " + _chartBars + " barov grafu, " + _htfBars + " barov informativneho TF, zrusenych vstupov " + cancelled
                + (_orders.Count > 0 ? ", sledovanych orderov " + _orders.Count : ""));
        }
    }
}
