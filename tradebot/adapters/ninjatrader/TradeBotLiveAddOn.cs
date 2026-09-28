// TradeBot Live AddOn - sonda, ci NinjaTrader 8 vie bezat bez cloveka (docs/NINJATRADER.md, "Beh bez cloveka").
//
// NinjaScript Strategia sa programovo zapnut neda (ani po restarte NT). AddOn startuje s NinjaTraderom
// sam, takze zivy beh bez kliknutia musi ist cez AddOn. Tento subor engine este NEPOUZIVA - je to
// overenie schopnosti, kazda v try/catch, nic nesmie vyhodit vynimku do UI vlakna NinjaTradera:
//
//   1. zoznam uctov (`Account.All`: meno, pripojenie, stav)
//   2. pripojenie z kodu (`Connection.Connect` na `Core.Globals.ConnectOptions` podla mena)
//   3. bary z kodu (`BarsRequest`, 1m, poslednych 50 + `Update` nazivo 2 minuty)
//   4. order z kodu (`Account.CreateOrder` + `Account.Submit`, market 1 kontrakt; po 20 s zavriet)
//      s udalostami `OrderUpdate` / `ExecutionUpdate`
//   5. control subor `Documents\NinjaTrader 8\TradeBot\control\addon.json` (mtime kazdych 5 s)
//
// Konfiguracia: `Documents\NinjaTrader 8\TradeBot\addon.json`
//   {"connection": "Simulated Data Feed", "account": "Sim101", "instrument": "MNQ 12-26", "tf": 1, "test_order": false}
// Bez suboru sa spravi len bod 1 a 5. Log: okno Output (New > NinjaScript Output) a
// `Documents\NinjaTrader 8\TradeBot\logs\addon_<cas>.txt`.
#region Using declarations
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.NinjaScript;
using TB = TradeBot.Core;
#endregion

namespace NinjaTrader.NinjaScript.AddOns
{
    public class TradeBotLiveAddOn : AddOnBase
    {
        private static int _started;
        private static volatile bool _stop;
        private static readonly object _logGate = new object();
        private static StreamWriter _log;

        public static string TradeBotDir { get { return Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "TradeBot"); } }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "TradeBot Live";
                Description = "TradeBot: sonda behu bez cloveka (ucty, pripojenie, bary, order, control subor) - docs/NINJATRADER.md";
            }
        }

        protected override void OnWindowCreated(Window window)
        {
            try
            {
                if (!(window is ControlCenter)) return;
                if (Interlocked.Exchange(ref _started, 1) == 1) return;   // raz na proces
                Thread t = new Thread(Worker);
                t.IsBackground = true;
                t.Name = "TradeBotLiveAddOn";
                t.Start();
            }
            catch (Exception e) { Say("start zlyhal: " + e); }
        }

        protected override void OnWindowDestroyed(Window window)
        {
            try
            {
                if (window is ControlCenter) _stop = true;
            }
            catch (Exception) { }
        }

        // ------------------------------------------------------------------ //
        // Log
        // ------------------------------------------------------------------ //

        private static void Say(string text)
        {
            string line = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture) + " " + text;
            try { NinjaTrader.Code.Output.Process("TradeBot addon: " + text, PrintTo.OutputTab1); } catch (Exception) { }
            try
            {
                lock (_logGate)
                {
                    if (_log == null)
                    {
                        string dir = Path.Combine(TradeBotDir, "logs");
                        Directory.CreateDirectory(dir);
                        _log = new StreamWriter(Path.Combine(dir, "addon_" + DateTime.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture) + ".txt"),
                                                false, new UTF8Encoding(false));
                        _log.AutoFlush = true;
                    }
                    _log.WriteLine(line);
                }
            }
            catch (Exception) { }
        }

        // ------------------------------------------------------------------ //
        // Sonda
        // ------------------------------------------------------------------ //

        private sealed class Cfg
        {
            public string Connection = "";
            public string Account = "Sim101";
            public string Instrument = "";
            public int Tf = 1;
            public bool TestOrder;
        }

        private static Cfg ReadCfg()
        {
            Cfg c = new Cfg();
            try
            {
                string path = Path.Combine(TradeBotDir, "addon.json");
                if (!File.Exists(path)) { Say("addon.json nie je (" + path + ") - len ucty a control subor"); return c; }
                Dictionary<string, object> d = TB.Json.ParseObject(File.ReadAllText(path));
                c.Connection = TB.Json.GetString(d, "connection", "");
                c.Account = TB.Json.GetString(d, "account", "Sim101");
                c.Instrument = TB.Json.GetString(d, "instrument", "");
                c.Tf = (int)TB.Json.GetDouble(d, "tf", 1);
                c.TestOrder = TB.Json.GetBool(d, "test_order", false);
                Say("addon.json: connection='" + c.Connection + "' account='" + c.Account + "' instrument='" + c.Instrument
                    + "' tf=" + c.Tf + " test_order=" + c.TestOrder);
            }
            catch (Exception e) { Say("addon.json sa nenacital: " + e.Message); }
            return c;
        }

        private static void Worker()
        {
            try
            {
                Say("start (NinjaTrader " + NinjaTrader.Core.Globals.UserDataDir + ", stroj " + Environment.MachineName + ")");
                Thread.Sleep(3000);   // Control Center sa este stavia; ucty a pripojenia sa objavia o chvilu
                ListAccounts("pri starte");
                Cfg cfg = ReadCfg();

                Account account = null;
                if (!string.IsNullOrEmpty(cfg.Connection))
                {
                    Connect(cfg.Connection);
                    account = WaitAccount(cfg.Account, 60);
                    ListAccounts("po pripojeni");
                }
                else
                    Say("connection nie je zadane - nepripajam");

                if (account != null && !string.IsNullOrEmpty(cfg.Instrument))
                {
                    Instrument inst = null;
                    try { inst = Instrument.GetInstrument(cfg.Instrument); } catch (Exception e) { Say("GetInstrument: " + e.Message); }
                    if (inst == null) Say("instrument '" + cfg.Instrument + "' NinjaTrader nepozna");
                    else
                    {
                        Say("instrument " + inst.FullName + " tick " + inst.MasterInstrument.TickSize + " bod " + inst.MasterInstrument.PointValue);
                        BarsRequest req = RequestBars(inst, cfg.Tf);
                        if (cfg.TestOrder) TestOrder(account, inst);
                        Thread.Sleep(120000);   // 2 minuty zivych barov
                        if (req != null)
                        {
                            try { req.Update -= OnBarsUpdate; req.Dispose(); } catch (Exception) { }
                            Say("BarsRequest zatvoreny, zivych aktualizacii: " + _liveUpdates);
                        }
                    }
                }
                ControlLoop();
            }
            catch (Exception e) { Say("worker spadol: " + e); }
            finally { Say("koniec"); }
        }

        private static void ListAccounts(string when)
        {
            try
            {
                List<string> lines = new List<string>();
                lock (Account.All)
                    foreach (Account a in Account.All)
                        lines.Add(a.Name + " [" + (a.Connection != null && a.Connection.Options != null ? a.Connection.Options.Name : "-")
                                  + " " + a.ConnectionStatus + "]");
                Say("ucty " + when + " (" + lines.Count + "): " + string.Join(", ", lines.ToArray()));
                List<string> conns = new List<string>();
                lock (Connection.Connections)
                    foreach (Connection c in Connection.Connections)
                        conns.Add((c.Options != null ? c.Options.Name : "?") + "=" + c.Status + "/" + c.PriceStatus);
                Say("pripojenia (" + conns.Count + "): " + string.Join(", ", conns.ToArray()));
            }
            catch (Exception e) { Say("ucty: " + e.Message); }
        }

        private static Connection FindConnection(string name)
        {
            lock (Connection.Connections)
                foreach (Connection c in Connection.Connections)
                    if (c.Options != null && c.Options.Name == name) return c;
            return null;
        }

        private static void Connect(string name)
        {
            try
            {
                Connection existing = FindConnection(name);
                if (existing != null && existing.Status == ConnectionStatus.Connected)
                {
                    Say("pripojenie '" + name + "' uz je Connected");
                    return;
                }
                ConnectOptions found = null;
                List<string> names = new List<string>();
                foreach (ConnectOptions o in NinjaTrader.Core.Globals.ConnectOptions)
                {
                    names.Add(o.Name);
                    if (o.Name == name) found = o;
                }
                Say("nakonfigurovane pripojenia: " + string.Join(", ", names.ToArray()));
                if (found == null) { Say("pripojenie '" + name + "' v Core.Globals.ConnectOptions nie je"); return; }
                Say("Connection.Connect('" + name + "') z pozadia...");
                Connection conn = null;
                Exception err = null;
                try { conn = Connection.Connect(found); }
                catch (Exception e) { err = e; }
                if (err != null)
                {
                    // niektore volania NT chcu UI vlakno - skus cez dispatcher
                    Say("Connect z pozadia zlyhal (" + err.Message + "), skusam cez RandomDispatcher");
                    NinjaTrader.Core.Globals.RandomDispatcher.Invoke(new Action(delegate
                    {
                        try { conn = Connection.Connect(found); }
                        catch (Exception e2) { Say("Connect cez dispatcher zlyhal: " + e2.Message); }
                    }));
                }
                Say("Connect vratil " + (conn == null ? "null" : conn.Status.ToString()));
                for (int i = 0; i < 30; i++)
                {
                    Connection c = conn ?? FindConnection(name);
                    if (c != null && c.Status == ConnectionStatus.Connected)
                    {
                        Say("pripojenie '" + name + "' Connected po " + i + " s (price feed " + c.PriceStatus + ")");
                        return;
                    }
                    Thread.Sleep(1000);
                }
                Connection last = conn ?? FindConnection(name);
                Say("pripojenie '" + name + "' po 30 s: " + (last == null ? "ziadne" : last.Status.ToString()));
            }
            catch (Exception e) { Say("Connect: " + e); }
        }

        private static Account WaitAccount(string name, int seconds)
        {
            for (int i = 0; i < seconds; i++)
            {
                try
                {
                    lock (Account.All)
                        foreach (Account a in Account.All)
                            if (a.Name == name && a.ConnectionStatus == ConnectionStatus.Connected)
                            {
                                Say("ucet " + name + " je Connected (" + (a.Connection != null && a.Connection.Options != null ? a.Connection.Options.Name : "-") + ")");
                                return a;
                            }
                }
                catch (Exception e) { Say("WaitAccount: " + e.Message); }
                Thread.Sleep(1000);
            }
            Say("ucet " + name + " sa do " + seconds + " s nepripojil");
            return null;
        }

        // ------------------------------------------------------------------ //
        // Bary
        // ------------------------------------------------------------------ //

        private static int _liveUpdates;
        private static readonly ManualResetEvent _barsDone = new ManualResetEvent(false);

        private static BarsRequest RequestBars(Instrument inst, int tf)
        {
            try
            {
                BarsRequest req = new BarsRequest(inst, 50);
                BarsPeriod period = new BarsPeriod();
                period.BarsPeriodType = BarsPeriodType.Minute;
                period.Value = tf < 1 ? 1 : tf;
                req.BarsPeriod = period;
                req.TradingHours = inst.MasterInstrument.TradingHours;
                req.MergePolicy = MergePolicy.DoNotMerge;
                req.Update += OnBarsUpdate;
                _barsDone.Reset();
                req.Request(new Action<BarsRequest, ErrorCode, string>(delegate(BarsRequest r, ErrorCode code, string msg)
                {
                    try
                    {
                        if (code != ErrorCode.NoError || r.Bars == null)
                            Say("BarsRequest chyba " + code + " " + msg);
                        else
                        {
                            int n = r.Bars.Count;
                            Say("BarsRequest " + inst.FullName + " " + period.Value + "m: " + n + " barov"
                                + (n > 0 ? ", posledny " + r.Bars.GetTime(n - 1).ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture)
                                           + " c=" + r.Bars.GetClose(n - 1) : ""));
                        }
                    }
                    catch (Exception e) { Say("BarsRequest callback: " + e.Message); }
                    finally { _barsDone.Set(); }
                }));
                if (!_barsDone.WaitOne(60000)) Say("BarsRequest bez odpovede 60 s");
                return req;
            }
            catch (Exception e) { Say("BarsRequest: " + e); return null; }
        }

        private static void OnBarsUpdate(object sender, BarsUpdateEventArgs e)
        {
            try
            {
                _liveUpdates++;
                if (_liveUpdates > 400) return;   // ticky na Simulated Data Feed chodia 2x za sekundu; staci ukazka
                BarsSeries s = e.BarsSeries;
                for (int i = e.MinIndex; i <= e.MaxIndex; i++)
                    if (_liveUpdates <= 20 || i == e.MaxIndex && s.GetTime(i).Second == 0 && _liveUpdates % 50 == 0)
                        Say("bar update #" + _liveUpdates + " idx " + i + " " + s.GetTime(i).ToString("HH:mm:ss", CultureInfo.InvariantCulture)
                            + " o=" + s.GetOpen(i) + " h=" + s.GetHigh(i) + " l=" + s.GetLow(i) + " c=" + s.GetClose(i) + " v=" + s.GetVolume(i));
            }
            catch (Exception ex) { Say("bar update: " + ex.Message); }
        }

        // ------------------------------------------------------------------ //
        // Order
        // ------------------------------------------------------------------ //

        private static void OnOrderUpdate(object sender, OrderEventArgs e)
        {
            try
            {
                Order o = e.Order;
                Say("OrderUpdate " + (o != null ? o.Name + " " + o.OrderAction + " " + o.OrderType + " x" + o.Quantity : "?")
                    + " -> " + e.OrderState + " filled " + e.Filled + " @" + e.AverageFillPrice
                    + (e.Error != ErrorCode.NoError ? " CHYBA " + e.Error : ""));
            }
            catch (Exception ex) { Say("OrderUpdate: " + ex.Message); }
        }

        private static void OnExecutionUpdate(object sender, ExecutionEventArgs e)
        {
            try
            {
                Say("ExecutionUpdate " + e.MarketPosition + " x" + e.Quantity + " @" + e.Price + " order " + e.OrderId
                    + " " + e.Time.ToString("HH:mm:ss", CultureInfo.InvariantCulture));
            }
            catch (Exception ex) { Say("ExecutionUpdate: " + ex.Message); }
        }

        private static void TestOrder(Account account, Instrument inst)
        {
            try
            {
                account.OrderUpdate += OnOrderUpdate;
                account.ExecutionUpdate += OnExecutionUpdate;
                Order buy = account.CreateOrder(inst, OrderAction.Buy, OrderType.Market, OrderEntry.Automated, TimeInForce.Day,
                                                1, 0, 0, "", "tb_addon_test", NinjaTrader.Core.Globals.MaxDate, null);
                Say("Submit BUY market 1 " + inst.FullName + " na " + account.Name);
                account.Submit(new Order[] { buy });
                Thread.Sleep(20000);
                Say("stav po 20 s: order " + buy.OrderState + " filled " + buy.Filled + " @" + buy.AverageFillPrice);
                int qty = 0;
                lock (account.Positions)
                    foreach (Position p in account.Positions)
                        if (p.Instrument == inst) { Say("pozicia " + p.MarketPosition + " x" + p.Quantity + " @" + p.AveragePrice); if (p.MarketPosition == MarketPosition.Long) qty = p.Quantity; }
                if (buy.OrderState == OrderState.Working || buy.OrderState == OrderState.Accepted || buy.OrderState == OrderState.Submitted)
                {
                    Say("vstup sa nevyplnil - rusim");
                    account.Cancel(new Order[] { buy });
                }
                if (qty > 0)
                {
                    Order sell = account.CreateOrder(inst, OrderAction.Sell, OrderType.Market, OrderEntry.Automated, TimeInForce.Day,
                                                     qty, 0, 0, "", "tb_addon_flat", NinjaTrader.Core.Globals.MaxDate, null);
                    Say("Submit SELL market " + qty + " (zavretie)");
                    account.Submit(new Order[] { sell });
                    Thread.Sleep(10000);
                    Say("stav zavretia: " + sell.OrderState + " filled " + sell.Filled + " @" + sell.AverageFillPrice);
                }
                else Say("bez pozicie, nie je co zavriet");
            }
            catch (Exception e) { Say("TestOrder: " + e); }
        }

        // ------------------------------------------------------------------ //
        // Control subor
        // ------------------------------------------------------------------ //

        private static void ControlLoop()
        {
            string path = Path.Combine(TradeBotDir, "control", "addon.json");
            Say("control subor " + path + " (mtime kazdych 5 s)");
            DateTime seen = DateTime.MinValue;
            string mode = "";
            while (!_stop)
            {
                try
                {
                    if (File.Exists(path))
                    {
                        DateTime mtime = File.GetLastWriteTimeUtc(path);
                        if (mtime != seen)
                        {
                            seen = mtime;
                            Dictionary<string, object> d = TB.Json.ParseObject(File.ReadAllText(path));
                            string m = TB.Json.GetString(d, "mode", "enabled");
                            if (m != mode)
                            {
                                Say("control: mode '" + mode + "' -> '" + m + "' profil '" + TB.Json.GetString(d, "profile", "") + "' by " + TB.Json.GetString(d, "by", ""));
                                mode = m;
                            }
                        }
                    }
                    else if (mode != "")
                    {
                        Say("control: subor zmizol -> enabled");
                        mode = "";
                        seen = DateTime.MinValue;
                    }
                }
                catch (Exception e) { Say("control: " + e.Message); }
                Thread.Sleep(5000);
            }
        }
    }
}
