// Simulator poruch adaptera NinjaTradera (tester/faultsim): skutocny `LiveInstance` bezi nad falosnym brokerom
// (NtStubs.cs) a skriptovanym enginom; scenar (JSON) predpise, co engine chce a co broker pokazi, a simulator
// po kazdom kroku vypise, co je u brokera a co si o tom mysli instancia. Do NinjaTradera sa NEINSTALUJE.
//
//   TradeBot.FaultSim.exe <scenar.json> <pracovny adresar>   ->   JSON na stdout
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Threading;
using NinjaTrader.Cbi;
using NinjaTrader.NinjaScript.AddOns;
using NinjaTrader.Sim;
using TB = TradeBot.Core;

namespace TradeBot.FaultSim
{
    /// <summary>Engine, ktory robi presne to, co mu scenar predpise na danom zivom bare (`bar` = 1 je prvy zivy).</summary>
    [TB.TradeBotEngine("faultsim", "Simulator poruch")]
    public sealed class ScriptedEngine : TB.IEngine
    {
        private readonly TB.InstrumentSpec _inst;
        private readonly int _tf;
        private readonly long _t0;
        private readonly List<object> _script;
        /// <summary>Co adapter enginu povedal o pozicii na kazdom zivom bare (`MarketContext.PositionSize`).</summary>
        public static readonly List<double> SeenPosition = new List<double>();

        public ScriptedEngine(Dictionary<string, object> config, TB.InstrumentSpec inst, int chartTfMinutes)
        {
            _inst = inst;
            _tf = chartTfMinutes;
            _t0 = TB.Json.ToLong(TB.Json.Get(config, "t0"));
            _script = TB.Json.Get(config, "script") as List<object> ?? new List<object>();
        }

        public TB.InstrumentSpec Inst { get { return _inst; } }
        public int ChartTfMinutes { get { return _tf; } }
        public int RequiredHistory { get { return 1; } }
        public TB.Warmup Warmup { get { return null; } }
        public List<TB.DrawCommand> FinalDrawings(TB.Bar bar) { return new List<TB.DrawCommand>(); }
        public TB.IHtfFeeder CreateHtfFeeder() { return null; }
        public Dictionary<string, double> Stats() { return new Dictionary<string, double>(); }

        public TB.EngineOutput OnBar(TB.Bar bar, TB.HtfWindow htf, TB.MarketContext ctx)
        {
            TB.EngineOutput output = new TB.EngineOutput();
            long n = (bar.Time - _t0) / (_tf * 60000L) + 1;
            if (n < 1) return output;
            SeenPosition.Add(ctx.PositionSize);
            foreach (object item in _script)
            {
                Dictionary<string, object> s = item as Dictionary<string, object>;
                if (s == null || TB.Json.ToLong(TB.Json.Get(s, "bar")) != n) continue;
                string action = TB.Json.GetString(s, "action", "entry");
                string id = TB.Json.GetString(s, "id", "");
                if (action == "close_session") { output.CloseSession = true; continue; }
                if (action == "cancel") { output.Orders.Add(new TB.OrderIntent(TB.OrderAction.Cancel, id, 0, "scenar")); continue; }
                if (action == "close") { output.Orders.Add(new TB.OrderIntent(TB.OrderAction.Close, id, 0, "scenar")); continue; }
                TB.Direction dir = TB.Json.GetDouble(s, "dir", 1) < 0 ? TB.Direction.Short : TB.Direction.Long;
                double entry = TB.Json.GetDouble(s, "entry", bar.Close);
                double sl = TB.Json.GetDouble(s, "sl", entry - (int)dir * 5);
                double tp = TB.Json.GetDouble(s, "tp", entry + (int)dir * 10);
                TB.TrailingPlan trail = null;
                if (s.ContainsKey("trail_act"))
                    trail = new TB.TrailingPlan(TB.Json.GetDouble(s, "trail_act", 0), TB.Json.GetDouble(s, "trail_off", 0), 0, 0);
                TB.OrderIntent intent = new TB.OrderIntent(TB.OrderAction.Entry, id, 0, "scenar");
                intent.Direction = dir;
                intent.Plan = new TB.TradePlan(dir, entry, sl, tp, TB.Json.GetDouble(s, "qty", 1), Math.Abs(entry - sl), trail);
                string type = TB.Json.GetString(s, "type", "limit");
                intent.OrderType = type == "market" ? TB.OrderType.Market : (type == "stop" ? TB.OrderType.Stop : TB.OrderType.Limit);
                output.Orders.Add(intent);
            }
            return output;
        }
    }

    public static class Program
    {
        private const BindingFlags Any = BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public;
        private static Account _account;
        private static Instrument _inst;
        private static LiveInstance _live;
        private static DateTime _base;
        private static int _liveBars;
        private static string _error = "";

        public static int Main(string[] args)
        {
            Thread.CurrentThread.CurrentCulture = CultureInfo.InvariantCulture;
            if (args.Length < 2) { Console.Error.WriteLine("pouzitie: TradeBot.FaultSim.exe <scenar.json> <pracovny adresar>"); return 2; }
            Dictionary<string, object> scenario = TB.Json.ParseObject(File.ReadAllText(args[0]));
            TB.JsonWriter w = new TB.JsonWriter();
            w.BeginObject().Key("trace").BeginArray();
            try
            {
                Prepare(scenario, args[1]);
                if (!Start()) throw new InvalidOperationException("instancia sa nerozbehla (Setup)");
                Settle();
                Snapshot(w, "start");
                List<object> steps = TB.Json.Get(scenario, "steps") as List<object> ?? new List<object>();
                foreach (object item in steps)
                {
                    Dictionary<string, object> step = (Dictionary<string, object>)item;
                    Do(step);
                    Snapshot(w, Label(step));
                }
            }
            catch (Exception e)
            {
                Exception inner = e is TargetInvocationException && e.InnerException != null ? e.InnerException : e;
                _error = inner.ToString();
            }
            w.EndArray();
            w.Key("error").Value(_error);
            w.Key("seen_position").BeginArray();
            foreach (double p in ScriptedEngine.SeenPosition) w.Value(p);
            w.EndArray();
            w.Key("requests").BeginArray();
            if (_account != null) foreach (string r in _account.Requests) w.Value(r);
            w.EndArray();
            w.Key("log").BeginArray();
            foreach (string line in World.Log) w.Value(line);
            w.EndArray().EndObject();
            Console.OutputEncoding = new System.Text.UTF8Encoding(false);
            Console.WriteLine(w.ToString());
            return _error.Length == 0 ? 0 : 1;
        }

        private static string Label(Dictionary<string, object> step)
        {
            string label = TB.Json.GetString(step, "do", "?");
            foreach (string key in new string[] { "order", "match", "then", "mode" })
                if (step.ContainsKey(key)) label += " " + TB.Json.GetString(step, key, "");
            if (step.ContainsKey("s")) label += " " + TB.Json.ToInt(step["s"]) + "s";
            return label;
        }

        // ------------------------------------------------------------------ //
        // Svet: adresar, profil enginu, ucet, instrument, predhistoria
        // ------------------------------------------------------------------ //

        private static void Prepare(Dictionary<string, object> scenario, string dir)
        {
            World.Dir = dir;
            _base = World.Now;
            string profiles = Path.Combine(Path.Combine(TradeBotLiveAddOn.ProfilesDir, "faultsim"));
            Directory.CreateDirectory(profiles);
            Directory.CreateDirectory(TradeBotLiveAddOn.ControlDir);
            TB.JsonWriter p = new TB.JsonWriter();
            p.BeginObject().Key("t0").Value((long)Math.Round((_base - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalMilliseconds));
            p.Key("script");
            WriteAny(p, TB.Json.Get(scenario, "engine") ?? new List<object>());
            p.EndObject();
            File.WriteAllText(Path.Combine(profiles, "sim.json"), p.ToString());

            _inst = new Instrument();
            _inst.FullName = "SIM 03-27";
            Instrument.Known[_inst.FullName] = _inst;
            _account = new Account();
            _account.Name = "Sim101";
            Account.All.Add(_account);

            int history = (int)TB.Json.GetDouble(scenario, "history", 60);
            for (int i = 0; i < history; i++) World.AddBar(_base.AddMinutes(-(history - 1 - i)), 100, 100.5, 99.5, 100);
            World.Now = _base.AddSeconds(1);
            LiveClock.Source = delegate { return World.Now; };
        }

        private static void WriteAny(TB.JsonWriter w, object v)
        {
            Dictionary<string, object> d = v as Dictionary<string, object>;
            List<object> l = v as List<object>;
            if (d != null)
            {
                w.BeginObject();
                foreach (KeyValuePair<string, object> kv in d) { w.Key(kv.Key); WriteAny(w, kv.Value); }
                w.EndObject();
            }
            else if (l != null)
            {
                w.BeginArray();
                foreach (object item in l) WriteAny(w, item);
                w.EndArray();
            }
            else w.ValueObject(v);
        }

        private static bool Start()
        {
            Dictionary<string, object> d = new Dictionary<string, object>();
            d["deployment"] = "sim";
            d["account"] = _account.Name;
            d["instrument"] = _inst.FullName;
            d["tf"] = 1.0;
            d["strategy"] = "faultsim";
            d["profile"] = "sim";
            _live = new LiveInstance(LiveDeployment.FromJson(d));
            bool ok = (bool)Call("Setup");
            if (ok) Set("_lastControl", World.Now);
            return ok;
        }

        private static object Call(string method, params object[] args)
        {
            MethodInfo m = typeof(LiveInstance).GetMethod(method, Any);
            if (m == null) throw new MissingMethodException("LiveInstance." + method);
            return m.Invoke(_live, args);
        }

        private static object Get(object target, string field)
        {
            FieldInfo f = target.GetType().GetField(field, Any);
            if (f == null) throw new MissingFieldException(target.GetType().Name + "." + field);
            return f.GetValue(target);
        }

        private static void Set(string field, object value)
        {
            FieldInfo f = typeof(LiveInstance).GetField(field, Any);
            if (f == null) throw new MissingFieldException("LiveInstance." + field);
            f.SetValue(_live, value);
        }

        // ------------------------------------------------------------------ //
        // Kroky scenara
        // ------------------------------------------------------------------ //

        /// <summary>Obeh slucky instancie a dorucenie vsetkeho, co broker medzitym nedrzi - kym sa svet neupokoji.</summary>
        private static void Settle()
        {
            for (int round = 0; round < 50; round++)
            {
                if (_live != null) Call("Step");
                List<Pending> ready = _account.Queue.FindAll(delegate(Pending p) { return !p.Held; });
                if (ready.Count == 0) return;
                foreach (Pending p in ready) { _account.Queue.Remove(p); _account.Deliver(p); }
            }
            throw new InvalidOperationException("svet sa neupokojil ani po 50 obehoch (ordery sa posielaju dookola)");
        }

        private static Order Find(string name, bool alive)
        {
            Order found = null;
            foreach (Order o in _account.Orders)
                if (o.Name == name && (!alive || !o.IsTerminal)) found = o;
            if (found == null) throw new InvalidOperationException("order '" + name + "' u brokera " + (alive ? "nie je zivy" : "nie je"));
            return found;
        }

        private static void Do(Dictionary<string, object> step)
        {
            string what = TB.Json.GetString(step, "do", "");
            if (what == "bar")
            {
                double c = TB.Json.GetDouble(step, "c", World.LastPrice);
                double o = TB.Json.GetDouble(step, "o", World.LastPrice);
                double h = TB.Json.GetDouble(step, "h", Math.Max(o, c));
                double l = TB.Json.GetDouble(step, "l", Math.Min(o, c));
                DateTime close = _base.AddMinutes(++_liveBars);
                World.Now = close.AddSeconds(1);
                World.AddBar(close, o, h, l, c);
                World.RaiseBars(World.Bars.Count - 1);
                Settle();
            }
            else if (what == "advance")
            {
                int seconds = (int)TB.Json.GetDouble(step, "s", 1);
                for (int i = 0; i < seconds; i++) { World.Now = World.Now.AddSeconds(1); Settle(); }
            }
            else if (what == "fill")
            {
                Order o = Find(TB.Json.GetString(step, "order", ""), true);
                double price = TB.Json.GetDouble(step, "price", o.OrderType == OrderType.Limit ? o.LimitPrice : (o.OrderType == OrderType.StopMarket ? o.StopPrice : World.LastPrice));
                _account.QueueFill(o, (int)TB.Json.GetDouble(step, "qty", o.Quantity - o.Filled), price, TB.Json.GetBool(step, "lose_exec", false));
                Settle();
            }
            else if (what == "rule")
            {
                Rule r = new Rule();
                r.On = TB.Json.GetString(step, "on", "");
                r.Match = TB.Json.GetString(step, "match", "");
                r.Then = TB.Json.GetString(step, "then", "");
                r.Times = (int)TB.Json.GetDouble(step, "times", 1);
                World.Rules.Add(r);
            }
            else if (what == "release")
            {
                string match = TB.Json.GetString(step, "match", "");
                foreach (Pending p in _account.Queue)
                    if (match.Length == 0 || p.Order.Name == match) p.Held = false;
                Settle();
            }
            else if (what == "cancel_outside")
            {
                // order zruseny mimo strategie (Chart Trader, broker)
                _account.Cancel(new Order[] { Find(TB.Json.GetString(step, "order", ""), true) });
                Settle();
            }
            else if (what == "foreign")
            {
                // order mimo strategie na tom istom ucte a instrumente (Chart Trader Close, ine okno)
                bool buy = TB.Json.GetString(step, "side", "sell") == "buy";
                Order o = _account.CreateOrder(_inst, buy ? OrderAction.Buy : OrderAction.Sell, OrderType.Market, OrderEntry.Manual, TimeInForce.Gtc,
                                               (int)TB.Json.GetDouble(step, "qty", 1), 0, 0, "", TB.Json.GetString(step, "name", "Close"), DateTime.MaxValue, null);
                _account.Submit(new Order[] { o });
                Settle();
            }
            else if (what == "disconnect")
            {
                _account.ConnectionStatus = ConnectionStatus.ConnectionLost;
                _account.HidePositions = TB.Json.GetBool(step, "hide_positions", true);
                Settle();
            }
            else if (what == "connect")
            {
                _account.ConnectionStatus = ConnectionStatus.Connected;
                // pozicie sa po reconnecte objavia az o chvilu (`positions_after` sekund); 0 = hned
                if (!step.ContainsKey("positions") || TB.Json.GetBool(step, "positions", true)) _account.HidePositions = false;
                Settle();
            }
            else if (what == "positions")
            {
                _account.HidePositions = !TB.Json.GetBool(step, "visible", true);
                Settle();
            }
            else if (what == "session")
            {
                World.InSession = TB.Json.GetBool(step, "open", true);
            }
            else if (what == "control")
            {
                TB.JsonWriter c = new TB.JsonWriter();
                c.BeginObject().Key("mode").Value(TB.Json.GetString(step, "mode", "enabled")).EndObject();
                string path = Path.Combine(TradeBotLiveAddOn.ControlDir, _live.Instance + ".json");
                File.WriteAllText(path, c.ToString());
                File.SetLastWriteTimeUtc(path, DateTime.UtcNow.AddSeconds(_controlWrites++));   // mtime musi rast aj v tej istej sekunde
            }
            else if (what == "crash")
            {
                // pad platformy: ziadny Teardown, udalosti brokera uz nema kto pocuvat
                _account.DropSubscribers();
                foreach (NinjaTrader.Data.BarsRequest r in World.Requests.ToArray()) r.Dispose();
                _live = null;
                Settle();
            }
            else if (what == "stop")
            {
                Call("Teardown", TB.Json.GetString(step, "reason", "terminated"));
                _live = null;
                Settle();
            }
            else if (what == "start")
            {
                if (!Start()) throw new InvalidOperationException("instancia sa po restarte nerozbehla (Setup)");
                Settle();
            }
            else throw new InvalidOperationException("neznamy krok scenara '" + what + "'");
        }

        private static int _controlWrites;

        // ------------------------------------------------------------------ //
        // Vypis: co je u brokera, co si mysli instancia, a ci to spolu sedi
        // ------------------------------------------------------------------ //

        private static void Snapshot(TB.JsonWriter w, string label)
        {
            w.BeginObject().Key("step").Value(label);
            w.Key("t").Value(World.Now.ToString("HH:mm:ss", CultureInfo.InvariantCulture));
            w.Key("position").Value(_account.Net);

            bool stop = false, closing = false, exits = false;
            w.Key("working").BeginArray();
            foreach (Order o in _account.Orders)
            {
                if (o.IsTerminal) continue;
                bool against = _account.Net != 0 && o.IsLong != (_account.Net > 0);
                if (against && o.OrderType == OrderType.StopMarket && o.Quantity - o.Filled >= Math.Abs(_account.Net)) stop = true;
                if (against && o.OrderType == OrderType.Market) closing = true;
                if (o.Name.Contains(":")) exits = true;
                w.BeginObject().Key("name").Value(o.Name).Key("side").Value(o.IsLong ? "buy" : "sell").Key("type").Value(o.OrderType.ToString())
                    .Key("qty").Value(o.Quantity).Key("filled").Value(o.Filled).Key("state").Value(o.OrderState.ToString())
                    .Key("price").Value(o.OrderType == OrderType.Limit ? o.LimitPrice : o.StopPrice).EndObject();
            }
            w.EndArray();
            w.Key("held").Value(_account.Queue.Count);

            int tracked = 0, dying = 0;
            w.Key("tracked").BeginArray();
            if (_live != null)
            {
                foreach (DictionaryEntry kv in (IDictionary)Get(_live, "_orders"))
                {
                    object t = kv.Value;
                    TB.OrderIntent intent = (TB.OrderIntent)Get(t, "Intent");
                    bool filled = (bool)Get(t, "Filled");
                    int open = (int)Get(t, "OpenQty");
                    if (filled && intent.Plan != null) tracked += (intent.Plan.Direction == TB.Direction.Long ? 1 : -1) * open;
                    w.BeginObject().Key("id").Value((string)kv.Key).Key("filled").Value(filled).Key("open").Value(open)
                        .Key("parked").Value((bool)Get(t, "Parked")).Key("closing").Value((string)Get(t, "Closing") ?? "").EndObject();
                }
                dying = ((ICollection)Get(_live, "_dying")).Count;
            }
            w.EndArray();
            w.Key("tracked_position").Value(tracked);
            w.Key("dying").Value(dying);
            // pozicia u brokera bez stopu (a bez trhoveho vystupu na ceste) / vystupy bez pozicie / pozicia, o ktorej instancia nevie
            w.Key("naked").Value(_account.Net != 0 && !stop && !closing);
            w.Key("orphans").Value(_account.Net == 0 && exits);
            w.Key("unknown").Value(_live != null && tracked != _account.Net);
            w.EndObject();
        }
    }
}
