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
        }

        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        /// <summary>Bar je uzavrety, ked jeho cas zatvorenia + tato rezerva uz presiel.</summary>
        private const int CloseGraceSeconds = 1;
        private const int ControlPeriodSeconds = 2;
        /// <summary>Kym sa pri zatvarani pozicie nepotvrdi zrusenie SL/TP, trhovy vystup pocka najviac tolko.</summary>
        private const int CloseCancelTimeoutSeconds = 10;

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
            if (_spool == null || !_spool.Broken || _spoolErrorPrinted) return;
            _spoolErrorPrinted = true;
            Log("live telemetria vypnuta - " + _spool.LastError);
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
                    try { if (_live) ReleaseParked(); }   // pozicia uctu sa vynuluje o chvilu po fille vystupu
                    catch (Exception e) { Note("error", "odlozene vstupy - " + e.Message); }
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

            _chart = RequestSeries(d.Tf, Math.Max(50, _engine.RequiredHistory * 2 + 5));
            if (_chart == null) return false;
            if (_htf != null)
            {
                _htfSeries = RequestSeries(_htf.TfMinutes, HtfBarsBack(_chart.Tf, _htf.TfMinutes, _engine.RequiredHistory * 2 + 5));
                if (_htfSeries == null) return false;
            }

            _orderHandler = OnOrderUpdate;
            _executionHandler = OnExecutionUpdate;
            _account.OrderUpdate += _orderHandler;
            _account.ExecutionUpdate += _executionHandler;

            Replay();
            return true;
        }

        private static int HtfBarsBack(int chartTf, int htfTf, int chartBars)
        {
            return (int)Math.Ceiling((double)chartBars * chartTf / Math.Max(1, htfTf)) + 8;
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
            try
            {
                lock (_account.Positions)
                    foreach (Position p in _account.Positions)
                        if (p.Instrument != null && p.Instrument.FullName == _inst.FullName)
                            return p.MarketPosition == MarketPosition.Long ? p.Quantity : (p.MarketPosition == MarketPosition.Short ? -p.Quantity : 0);
            }
            catch (Exception e) { Log("Positions: " + e.Message); }
            return 0;
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
            try
            {
                if (t.Sl == null)
                {
                    string oco = "tb" + (++_ocoSeq).ToString(CultureInfo.InvariantCulture) + "-" + Guid.NewGuid().ToString("N").Substring(0, 8);
                    t.Sl = Create(action, OrderType.StopMarket, t.OpenQty, 0, Tick(t.LastStop), oco, id + ":sl");
                    t.Tp = Create(action, OrderType.Limit, t.OpenQty, Tick(plan.TakeProfit), 0, oco, id + ":tp");
                    _account.Submit(new Order[] { t.Sl, t.Tp });
                    Log("EXITS " + id + " SL " + Tick(t.LastStop) + " TP " + Tick(plan.TakeProfit) + " qty " + t.OpenQty + " oco " + oco);
                    return;
                }
                // dalsi ciastocny fill: navys objem vystupov
                List<Order> change = new List<Order>();
                if (Alive(t.Sl)) { t.Sl.QuantityChanged = t.OpenQty; change.Add(t.Sl); }
                if (Alive(t.Tp)) { t.Tp.QuantityChanged = t.OpenQty; change.Add(t.Tp); }
                if (change.Count > 0) _account.Change(change);
            }
            catch (Exception e) { Note("error", "vystupy " + id + " sa neposlali - " + e.Message); }
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
            catch (Exception e) { Note("error", "trhovy vystup " + id + " sa neposlal - " + e.Message); t.CloseSent = false; }
        }

        /// <summary>Zrusenie SL/TP sa nepotvrdilo do limitu - trhovy vystup ide aj tak.</summary>
        private void CloseTimeouts()
        {
            foreach (KeyValuePair<string, Tracked> kv in new List<KeyValuePair<string, Tracked>>(_orders))
            {
                Tracked t = kv.Value;
                if (t.Closing == null || t.CloseSent || t.OpenQty <= 0) continue;
                if ((DateTime.UtcNow - t.ClosingSince).TotalSeconds < CloseCancelTimeoutSeconds) continue;
                Note("warn", "zrusenie SL/TP " + kv.Key + " sa nepotvrdilo do " + CloseCancelTimeoutSeconds + " s - trhovy vystup posielam aj tak");
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
                t.LastStop = stop;
                if (Alive(t.Sl))
                {
                    try
                    {
                        t.Sl.StopPriceChanged = Tick(stop);
                        _account.Change(new Order[] { t.Sl });
                        Log("TRAIL " + kv.Key + " SL -> " + Tick(stop));
                    }
                    catch (Exception e) { Note("error", "posun SL " + kv.Key + " zlyhal - " + e.Message); continue; }
                }
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
                Note("error", "vystup " + name + " odmietnuty: " + error + " " + comment);
                if (!exit) { t.CloseSent = false; return; }   // trhovy vystup - CloseTimeouts ho posle znova
            }
            if (!exit || (state != OrderState.Cancelled && state != OrderState.Rejected)) return;
            if (t.OpenQty > 0 && t.Closing == null && state == OrderState.Rejected)
            {
                // pozicia bez ochrany - zavri ju trhovo
                RequestClose(id, t, "tb_close");
                return;
            }
            // oba vystupy prec (zrusene, nie vyplnene) -> trhovy vystup; vyplneny vystup zavrie poziciu sam (HandleExecution)
            if (t.Closing != null && !t.CloseSent && Gone(t.Sl) && Gone(t.Tp) && t.OpenQty > 0) SubmitCloseMarket(id, t);
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
            if (colon <= 0) return;
            string id = name.Substring(0, colon);
            string suffix = name.Substring(colon + 1);
            if (!_orders.TryGetValue(id, out t)) return;
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

            // Pine `dailyWinsCount`: vyhra = uzavrety obchod so ziskom > 0; zavretie koncom seansy / close sa nepocita
            if (suffix != "sl" && suffix != "tp") return;
            TB.TradePlan plan = t.Intent.Plan;
            double move = plan.Direction == TB.Direction.Long ? price - plan.Entry : plan.Entry - price;
            if (move > 0)
            {
                string day = UtcDay(execMs);
                int wins;
                _dailyWins.TryGetValue(day, out wins);
                _dailyWins[day] = wins + 1;
            }
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
            DisposeSeries(_chart);
            DisposeSeries(_htfSeries);
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
