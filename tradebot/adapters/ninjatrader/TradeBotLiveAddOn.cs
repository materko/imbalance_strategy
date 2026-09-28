// TradeBot Live AddOn - beh strategii s C# jadrom v NinjaTraderi 8 bez cloveka (docs/NINJATRADER.md, "Beh bez cloveka").
//
// NinjaScript Strategia sa programovo zapnut neda (ani po restarte NT). AddOn startuje s NinjaTraderom
// sam (a NT ho znova instancuje aj po rekompilacii NinjaTrader.Custom.dll), preto zivy beh bez kliknutia
// ide tadialto. AddOn cita `Documents\NinjaTrader 8\TradeBot\deploy.json`:
//
//   {"instances":[{"deployment":"dep-1","connection":"Simulated Data Feed","account":"Sim101",
//                  "instrument":"MNQ 12-26","tf":3,"strategy":"ibsnet","profile":"multicharts_mnq_3m"}]}
//
// a pre kazdy zaznam drzi jednu `LiveInstance` (TradeBotLiveInstance.cs): pripojenie, ucet, BarsRequest,
// engine, ordery, spool, control subor. Subor sa sleduje podla mtime kazde 2 s (nove zaznamy sa spustia,
// odstranene zastavia, zmenene sa restartuju) a znova pri zmene stavu pripojenia (neuspesne starty sa
// skusaju znova). Profil je `TradeBot\profiles\<strategia>\<profil>.json` alebo `TradeBot\profiles\<profil>.json`
// (tam ich pise `python -m tradebot.adapters.ninjatrader install`); chybajuci profil = zaznam sa preskoci a loguje.
//
// Generacie: po rekompilacii NT nacita novu assembly a instancuje AddOn znova, ale stara instancia so svojim
// vlaknom nezmizne. Kazda generacia si preto zapise token do AppDomain (zdielany cez assembly) a stara sa
// zastavi, len co uvidi cudzi token - inak by bezali dve kopie tej istej instancie.
//
// Log: okno Output (New > NinjaScript Output) a `TradeBot\logs\addon_<cas>.txt`. Nic z AddOnu nesmie
// vyhodit vynimku do UI vlakna NinjaTradera - kazdy vstupny bod je v try/catch.
#region Using declarations
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.NinjaScript;
using TB = TradeBot.Core;
#endregion

namespace NinjaTrader.NinjaScript.AddOns
{
    public class TradeBotLiveAddOn : AddOnBase
    {
        private const string GenerationKey = "TradeBotLiveAddOn.generation";
        private const int DeployPeriodSeconds = 2;
        private const int RetrySeconds = 60;

        private static int _started;
        private static volatile bool _stop;
        private static volatile bool _reconcile;
        private static readonly object _logGate = new object();
        private static StreamWriter _log;
        private static string _generation;

        public static string TradeBotDir { get { return Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "TradeBot"); } }
        public static string ProfilesDir { get { return Path.Combine(TradeBotDir, "profiles"); } }
        public static string SpoolDir { get { return Path.Combine(TradeBotDir, "spool"); } }
        public static string ControlDir { get { return Path.Combine(TradeBotDir, "control"); } }
        public static string DeployPath { get { return Path.Combine(TradeBotDir, "deploy.json"); } }

        protected override void OnStateChange()
        {
            try
            {
                if (State == State.SetDefaults)
                {
                    Name = "TradeBot Live";
                    Description = "TradeBot: beh strategii s C# jadrom bez cloveka podla TradeBot\\deploy.json - docs/NINJATRADER.md";
                }
                else if (State == State.Terminated)
                    _stop = true;
            }
            catch (Exception) { }
        }

        protected override void OnWindowCreated(Window window)
        {
            try
            {
                if (!(window is ControlCenter)) return;
                if (Interlocked.Exchange(ref _started, 1) == 1) return;   // raz na proces (a generaciu)
                Thread t = new Thread(Supervisor);
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

        public static void Say(string text)
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
        // Pripojenie (zdielane instanciami)
        // ------------------------------------------------------------------ //

        private static readonly object _connectGate = new object();

        private static Connection FindConnection(string name)
        {
            lock (Connection.Connections)
                foreach (Connection c in Connection.Connections)
                    if (c.Options != null && c.Options.Name == name) return c;
            return null;
        }

        /// <summary>Pripojenie podla mena z Core.Globals.ConnectOptions je Connected (pripoji, ak treba). Vracia false po timeoute.</summary>
        public static bool EnsureConnected(string name, int seconds)
        {
            lock (_connectGate)
            {
                try
                {
                    Connection existing = FindConnection(name);
                    if (existing != null && existing.Status == ConnectionStatus.Connected) return true;
                    if (existing != null && existing.Status == ConnectionStatus.Connecting)
                        return WaitConnected(name, seconds);
                    ConnectOptions found = null;
                    List<string> names = new List<string>();
                    foreach (ConnectOptions o in NinjaTrader.Core.Globals.ConnectOptions)
                    {
                        names.Add(o.Name);
                        if (o.Name == name) found = o;
                    }
                    if (found == null)
                    {
                        Say("pripojenie '" + name + "' v Core.Globals.ConnectOptions nie je (su: " + string.Join(", ", names.ToArray()) + ")");
                        return false;
                    }
                    Say("Connection.Connect('" + name + "')...");
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
                    return WaitConnected(name, seconds);
                }
                catch (Exception e) { Say("Connect: " + e); return false; }
            }
        }

        private static bool WaitConnected(string name, int seconds)
        {
            for (int i = 0; i < seconds && !_stop; i++)
            {
                Connection c = FindConnection(name);
                if (c != null && c.Status == ConnectionStatus.Connected)
                {
                    Say("pripojenie '" + name + "' Connected (price feed " + c.PriceStatus + ")");
                    return true;
                }
                Thread.Sleep(1000);
            }
            Connection last = FindConnection(name);
            Say("pripojenie '" + name + "' po " + seconds + " s: " + (last == null ? "ziadne" : last.Status.ToString()));
            return false;
        }

        private static void OnConnectionStatus(object sender, ConnectionStatusEventArgs e)
        {
            try
            {
                if (e.Status == e.PreviousStatus) return;
                Say("pripojenie " + (e.Connection != null && e.Connection.Options != null ? e.Connection.Options.Name : "?") + ": "
                    + e.PreviousStatus + " -> " + e.Status + (e.Error != ErrorCode.NoError ? " " + e.Error + " " + e.NativeError : ""));
                _reconcile = true;
            }
            catch (Exception) { }
        }

        // ------------------------------------------------------------------ //
        // deploy.json
        // ------------------------------------------------------------------ //

        private static List<LiveDeployment> ReadDeploy()
        {
            List<LiveDeployment> list = new List<LiveDeployment>();
            Dictionary<string, object> d = TB.Json.ParseObject(File.ReadAllText(DeployPath));
            List<object> items = TB.Json.Get(d, "instances") as List<object>;
            if (items == null) return list;
            foreach (object item in items)
            {
                Dictionary<string, object> entry = item as Dictionary<string, object>;
                if (entry != null) list.Add(LiveDeployment.FromJson(entry));
            }
            return list;
        }

        private static bool IsCurrentGeneration()
        {
            try { return string.Equals(AppDomain.CurrentDomain.GetData(GenerationKey) as string, _generation); }
            catch (Exception) { return true; }
        }

        // ------------------------------------------------------------------ //
        // Supervizor: deploy.json -> instancie
        // ------------------------------------------------------------------ //

        private static void Supervisor()
        {
            Dictionary<string, LiveInstance> running = new Dictionary<string, LiveInstance>();
            List<LiveInstance> stopping = new List<LiveInstance>();
            try
            {
                _generation = Guid.NewGuid().ToString("N");
                try { AppDomain.CurrentDomain.SetData(GenerationKey, _generation); } catch (Exception) { }
                Say("start generacia " + _generation.Substring(0, 8) + " (NinjaTrader " + NinjaTrader.Core.Globals.UserDataDir
                    + ", stroj " + Environment.MachineName + "), deploy " + DeployPath);
                Thread.Sleep(3000);   // Control Center sa este stavia; ucty a pripojenia sa objavia o chvilu
                try { Connection.ConnectionStatusUpdate += OnConnectionStatus; }
                catch (Exception e) { Say("ConnectionStatusUpdate sa neda odoberat: " + e.Message); }

                Dictionary<string, LiveDeployment> desired = new Dictionary<string, LiveDeployment>();
                DateTime deployMtime = DateTime.MinValue;
                bool deploySeen = false;
                bool missingLogged = false;
                DateTime lastCheck = DateTime.MinValue;

                while (!_stop)
                {
                    if (!IsCurrentGeneration())
                    {
                        Say("nova generacia AddOnu (rekompilacia) - tato konci");
                        break;
                    }
                    bool force = _reconcile;
                    if (force || (DateTime.UtcNow - lastCheck).TotalSeconds >= DeployPeriodSeconds)
                    {
                        _reconcile = false;
                        lastCheck = DateTime.UtcNow;
                        try
                        {
                            if (File.Exists(DeployPath))
                            {
                                DateTime mtime = File.GetLastWriteTimeUtc(DeployPath);
                                if (mtime != deployMtime)
                                {
                                    deployMtime = mtime;
                                    deploySeen = true;
                                    List<LiveDeployment> list = ReadDeploy();
                                    desired = new Dictionary<string, LiveDeployment>();
                                    foreach (LiveDeployment dep in list)
                                    {
                                        if (desired.ContainsKey(dep.Key)) { Say("deploy.json: duplicitny zaznam " + dep.Key + " - beriem prvy"); continue; }
                                        desired[dep.Key] = dep;
                                    }
                                    Say("deploy.json: " + desired.Count + " instancii");
                                    foreach (LiveDeployment dep in desired.Values) Say("  " + dep.Describe());
                                }
                            }
                            else if (deploySeen)
                            {
                                Say("deploy.json zmizol - vsetky instancie sa zastavia");
                                deploySeen = false;
                                deployMtime = DateTime.MinValue;
                                desired = new Dictionary<string, LiveDeployment>();
                            }
                            else if (!missingLogged)
                            {
                                missingLogged = true;
                                Say("deploy.json nie je (" + DeployPath + ") - cakam");
                            }
                        }
                        catch (Exception e) { Say("deploy.json sa nenacital: " + e.Message + " - platia predosle instancie"); }

                        Reconcile(running, stopping, desired, force);
                    }
                    Thread.Sleep(1000);
                }
            }
            catch (Exception e) { Say("supervizor spadol: " + e); }
            finally
            {
                try { Connection.ConnectionStatusUpdate -= OnConnectionStatus; } catch (Exception) { }
                StopAll(running, stopping, _stop ? "terminated" : "superseded");
                Say("koniec");
            }
        }

        /// <summary>Zastav odstranene/zmenene, spusti nove, restartuj skoncene (po 60 s, pri zmene pripojenia hned).</summary>
        private static void Reconcile(Dictionary<string, LiveInstance> running, List<LiveInstance> stopping,
                                      Dictionary<string, LiveDeployment> desired, bool force)
        {
            foreach (KeyValuePair<string, LiveInstance> kv in new List<KeyValuePair<string, LiveInstance>>(running))
            {
                LiveInstance inst = kv.Value;
                LiveDeployment want;
                bool keep = desired.TryGetValue(kv.Key, out want) && want.SameAs(inst.Deployment);
                if (!keep && !inst.Finished)
                {
                    Say("instancia " + kv.Key + ": " + (desired.ContainsKey(kv.Key) ? "zmena zaznamu - restart" : "odstranena z deploy.json") + " - zastavujem");
                    inst.Stop(desired.ContainsKey(kv.Key) ? "changed" : "removed");
                    running.Remove(kv.Key);
                    stopping.Add(inst);
                    continue;
                }
                if (!keep && inst.Finished) { running.Remove(kv.Key); continue; }
                if (inst.Finished)
                {
                    double age = (DateTime.UtcNow - inst.FinishedAt).TotalSeconds;
                    if (force || age >= RetrySeconds)
                    {
                        Say("instancia " + kv.Key + " skoncila (" + inst.Status + ") - skusam znova");
                        running.Remove(kv.Key);
                    }
                }
            }
            // zastavene instancie so zmenenym zaznamom: novu spusti az ked stara naozaj skoncila
            foreach (LiveInstance inst in new List<LiveInstance>(stopping))
                if (inst.Finished) stopping.Remove(inst);
            foreach (KeyValuePair<string, LiveDeployment> kv in desired)
            {
                if (running.ContainsKey(kv.Key)) continue;
                bool stillStopping = false;
                foreach (LiveInstance s in stopping)
                    if (s.Deployment.Key == kv.Key) stillStopping = true;
                if (stillStopping) continue;
                LiveInstance inst = new LiveInstance(kv.Value);
                running[kv.Key] = inst;
                inst.Start();
            }
        }

        private static void StopAll(Dictionary<string, LiveInstance> running, List<LiveInstance> stopping, string reason)
        {
            List<LiveInstance> all = new List<LiveInstance>(running.Values);
            all.AddRange(stopping);
            foreach (LiveInstance inst in all)
                try { inst.Stop(reason); } catch (Exception) { }
            DateTime deadline = DateTime.UtcNow.AddSeconds(15);
            foreach (LiveInstance inst in all)
            {
                int ms = (int)Math.Max(100, (deadline - DateTime.UtcNow).TotalMilliseconds);
                inst.Join(ms);
            }
            running.Clear();
            stopping.Clear();
        }
    }
}
