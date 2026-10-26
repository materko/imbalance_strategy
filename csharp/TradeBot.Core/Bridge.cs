// Smerovanie prikazov (docs/ROUTING.md): strategia bezi v jednej platforme (NinjaTrader 8 - "master"), ordery
// vykonava druha na tom istom stroji (MetaTrader 5 - `TradeBotExecutor`). Kanal su subory, nie siet - ako spool
// a control (docs/LIVE.md): prezije pad ktorejkolvek strany a da sa precitat pri ladeni.
//
//   <root>\bridge\<instancia>\route.json   master: kam (id exekutora), symbol, mapovanie cien a objemu
//   <root>\bridge\<instancia>\cmd.jsonl    master, append: entry / cancel / close / modify / flatten / sync
//   <root>\bridge\<instancia>\evt.jsonl    exekutor, append: ack / reject / placed / fill / cancelled / closed / pos / snapshot ...
//   <root>\bridge\<instancia>\nt.hb        master kazdu sekundu: {t, session, mode}
//   <root>\bridge\<instancia>\nt.cursor    master: kam docital evt.jsonl
//   <root>\bridge\<instancia>\exec.state   exekutor: kam docital cmd.jsonl + vykonane cid (idempotencia cez restart)
//   <root>\exec\<id exekutora>.hb.json     exekutor kazdu sekundu: ucet, spojenie, symboly, prijate route
//   <root>\exec\<id exekutora>.lock        exekutor ho drzi otvoreny vyhradne - druha instancia s tym istym id sa neotvori
//
// <root> je `Common\Files\TradeBot` terminalu MT5 (`%APPDATA%\MetaQuotes\Terminal\Common\Files\TradeBot`): MQL5
// sandbox tam vidi cez FILE_COMMON a NinjaTrader tam smie pisat. Obe strany pouzivaju tento isty kod (NinjaTrader
// zo zdrojakov jadra, MT5 cez `StaticHost.Bridge*`), takze protokol je napisany raz.
//
// Riadok JSONL sa cita az ked konci '\n' - druha strana moze byt prave v polovici zapisu. Male subory
// (route.json, hb, stavy) sa pisu atomicky (tmp + presun) a citaju s FileShare.ReadWrite | Delete.
//
// Jazyk je zamerne C# 5 a len BCL (csc.exe z .NET Frameworku, NinjaTrader, Mono).
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

namespace TradeBot.Core
{
    /// <summary>Kam smeruje jedna instancia strategie a ako sa prepocitaju ceny a objem (`route.json`).</summary>
    public sealed class RouteSpec
    {
        public const int Version = 1;

        /// <summary>id exekutora (`Bridge.ExecutorId`)</summary>
        public string To = "";
        /// <summary>id instancie mastera = nazov adresara route</summary>
        public string Instance = "";
        public string Deployment = "";
        /// <summary>symbol u brokera exekutora</summary>
        public string Symbol = "";
        /// <summary>`basis` (prepocet od aktualnej ceny, SL/TP od fillu) alebo `same` (ceny bez zmeny)</summary>
        public string Price = "basis";
        /// <summary>pomer cien exekutor / master (1 pre NQ - NAS100)</summary>
        public double Scale = 1.0;
        /// <summary>`value` (rovnaka hodnota bodu) alebo `fixed` (`Lots` lotov na kontrakt)</summary>
        public string QtyMode = "value";
        public double Lots;
        public long Magic;
        public string NtSymbol = "";
        public double NtPointValue;
        public double NtTick;
        public int Tf;

        public string ToJson()
        {
            JsonWriter w = new JsonWriter();
            w.BeginObject();
            w.Key("v").Value(Version).Key("to").Value(To).Key("instance").Value(Instance).Key("deployment").Value(Deployment);
            w.Key("symbol").Value(Symbol).Key("price").Value(Price).Key("scale").Value(Scale);
            w.Key("qty").BeginObject().Key("mode").Value(QtyMode);
            if (QtyMode == "fixed") w.Key("lots").Value(Lots);
            w.EndObject();
            w.Key("magic").Value(Magic).Key("nt_symbol").Value(NtSymbol).Key("nt_point_value").Value(NtPointValue);
            w.Key("nt_tick").Value(NtTick).Key("tf").Value(Tf);
            w.EndObject();
            return w.ToString();
        }

        public static RouteSpec FromDict(Dictionary<string, object> d)
        {
            RouteSpec r = new RouteSpec();
            r.To = Json.GetString(d, "to", "");
            r.Instance = Json.GetString(d, "instance", "");
            r.Deployment = Json.GetString(d, "deployment", "");
            r.Symbol = Json.GetString(d, "symbol", "");
            r.Price = Json.GetString(d, "price", "basis");
            r.Scale = Json.GetDouble(d, "scale", 1.0);
            Dictionary<string, object> q = Json.Get(d, "qty") as Dictionary<string, object>;
            if (q != null)
            {
                r.QtyMode = Json.GetString(q, "mode", "value");
                r.Lots = Json.GetDouble(q, "lots", 0.0);
            }
            r.Magic = (long)Json.GetDouble(d, "magic", 0.0);
            r.NtSymbol = Json.GetString(d, "nt_symbol", "");
            r.NtPointValue = Json.GetDouble(d, "nt_point_value", 0.0);
            r.NtTick = Json.GetDouble(d, "nt_tick", 0.0);
            r.Tf = (int)Json.GetDouble(d, "tf", 0.0);
            return r;
        }
    }

    /// <summary>Ciste vypocty smerovania - bez suborov, rovnake v NinjaTraderi aj v MT5 (cez fasadu).</summary>
    public static class RouteMath
    {
        /// <summary>Exekutor odklada terminy z `OrderLife` o tolko: ked master zije, jeho vlastny prikaz pride skor.</summary>
        public const long LifeGraceMs = 5000;

        /// <summary>Zaokruhli na najblizsi tick (tick &lt;= 0 = bez zaokruhlenia).</summary>
        public static double RoundToTick(double price, double tick)
        {
            if (!(tick > 0)) return price;
            double n = Math.Round(price / tick, MidpointRounding.AwayFromZero);
            // spat cez decimal: 0.1 * 3 nema byt 0.30000000000000004
            return (double)((decimal)n * (decimal)tick);
        }

        /// <summary>Cena mastera -> cena exekutora: zachova vzdialenost od aktualnej ceny (`basis`).
        /// `refNt` = posledna cena mastera v case prikazu, `refExec` = aktualna cena exekutora (mid).</summary>
        public static double MapPrice(double price, double refNt, double refExec, double scale, double tick)
        {
            return RoundToTick(refExec + (price - refNt) * scale, tick);
        }

        /// <summary>Cena exekutora -> cena mastera (fill do enginu a telemetrie), bez zaokruhlenia.</summary>
        public static double ToNtPrice(double execPrice, double refNt, double refExec, double scale)
        {
            return refNt + (execPrice - refExec) / (scale > 0 ? scale : 1.0);
        }

        /// <summary>SL/TP po vyplneni: skutocny fill + planovana vzdialenost uroven - vstup (v cenach mastera).</summary>
        public static double Reanchor(double fill, double plannedEntry, double level, double scale, double tick)
        {
            return RoundToTick(fill + (level - plannedEntry) * scale, tick);
        }

        /// <summary>Kontrakty mastera -> loty exekutora. `value`: rovnaka hodnota bodu (riziko v $ ako v backteste),
        /// `fixed`: `fixedLots` na kontrakt. Zaokruhluje NADOL na krok; pod minimom vrati 0 (prikaz sa odmietne,
        /// nezvacsi sa), nad maximom maximum.</summary>
        public static double Lots(double contracts, double ntPointValue, double scale, double tickValue, double tickSize,
                                  double volMin, double volStep, double volMax, string mode, double fixedLots)
        {
            double raw;
            if (mode == "fixed") raw = contracts * fixedLots;
            else
            {
                if (!(tickValue > 0) || !(tickSize > 0) || !(ntPointValue > 0)) return 0;
                // hodnota jedneho bodu mastera na 1 lot exekutora: bod mastera = `scale` bodov exekutora
                double perLot = (scale > 0 ? scale : 1.0) * tickValue / tickSize;
                raw = contracts * ntPointValue / perLot;
            }
            if (volStep > 0) raw = Math.Floor(raw / volStep + 1e-9) * volStep;
            raw = (double)Math.Round((decimal)raw, 8);
            if (raw <= 0 || (volMin > 0 && raw < volMin - 1e-12)) return 0;
            if (volMax > 0 && raw > volMax) raw = volMax;
            return raw;
        }

        /// <summary>Co ma exekutor urobit s orderom sam podla `OrderLife`: "cancel" (nevyplneny vstup), "close"
        /// (otvorena pozicia) alebo "" (nic). Terminy plati s odkladom `graceMs`.</summary>
        public static string LifeAction(long cancelAtMs, long closeAtMs, long holdMs, bool filled, long fillMs,
                                        long nowMs, long graceMs)
        {
            if (closeAtMs > 0 && nowMs >= closeAtMs + graceMs) return filled ? "close" : "cancel";
            if (!filled && cancelAtMs > 0 && nowMs >= cancelAtMs + graceMs) return "cancel";
            if (filled && holdMs > 0 && fillMs > 0 && nowMs >= fillMs + holdMs + graceMs) return "close";
            return "";
        }
    }

    /// <summary>Stav route, ako ho vidi master (docs/ROUTING.md, "Zivost").</summary>
    public static class RouteStatus
    {
        public const string Ok = "ok";
        public const string NoExecutor = "no_executor";
        public const string Stale = "stale";
        public const string Disconnected = "disconnected";
        public const string TradeDisabled = "trade_disabled";
        public const string SymbolMissing = "symbol_missing";
        public const string AccountMismatch = "account_mismatch";
        public const string NettingUnsupported = "netting_unsupported";
        public const string Pending = "route_pending";

        /// <summary>Heartbeat exekutora starsi nez toto = exekutor nebezi.</summary>
        public const long StaleMs = 3000;

        /// <summary>Stav route z heartbeatu exekutora (`hb` null = subor neexistuje). `detail` = text pre cloveka.</summary>
        public static string Evaluate(Dictionary<string, object> hb, RouteSpec spec, string routeId, long nowMs, out string detail)
        {
            detail = "";
            if (hb == null) { detail = "exekutor " + spec.To + " nebezi (ziadny heartbeat)"; return NoExecutor; }
            long t = (long)Json.GetDouble(hb, "t", 0.0);
            if (nowMs - t > StaleMs)
            {
                detail = "heartbeat exekutora je stary " + ((nowMs - t) / 1000).ToString(CultureInfo.InvariantCulture) + " s";
                return Stale;
            }
            string id = Json.GetString(hb, "id", "");
            if (id != spec.To) { detail = "exekutor hlasi ucet " + id + ", route chce " + spec.To; return AccountMismatch; }
            if (Json.GetString(hb, "margin_mode", "") != "hedging")
            {
                detail = "ucet exekutora je " + Json.GetString(hb, "margin_mode", "?") + ", podporovany je len hedging";
                return NettingUnsupported;
            }
            if (!Json.GetBool(hb, "connected", false)) { detail = "terminal exekutora nie je pripojeny k brokerovi"; return Disconnected; }
            if (!Json.GetBool(hb, "trade_allowed", false)) { detail = "v terminali exekutora je vypnuty AutoTrading"; return TradeDisabled; }
            bool found = false;
            List<object> symbols = Json.Get(hb, "symbols") as List<object>;
            if (symbols != null)
            {
                foreach (object o in symbols)
                {
                    Dictionary<string, object> s = o as Dictionary<string, object>;
                    if (s == null || Json.GetString(s, "name", "") != spec.Symbol) continue;
                    found = Json.GetDouble(s, "trade_mode", 0.0) == 4;   // SYMBOL_TRADE_MODE_FULL
                    if (!found) { detail = "symbol " + spec.Symbol + " sa na ucte exekutora neda obchodovat oboma smermi"; return SymbolMissing; }
                }
            }
            if (!found) { detail = "ucet exekutora nema symbol " + spec.Symbol; return SymbolMissing; }
            List<object> routes = Json.Get(hb, "routes") as List<object>;
            if (routes != null)
            {
                foreach (object o in routes)
                {
                    Dictionary<string, object> r = o as Dictionary<string, object>;
                    if (r == null || Json.GetString(r, "id", "") != routeId) continue;
                    string state = Json.GetString(r, "state", "");
                    detail = Json.GetString(r, "detail", "");
                    return state == "" ? Pending : state;
                }
            }
            detail = "exekutor route este neprevzal";
            return Pending;
        }
    }

    /// <summary>Spolocne veci oboch stran: cesty, atomicky zapis, citanie zdielanych suborov, cas.</summary>
    public static class Bridge
    {
        public const string BridgeDir = "bridge";
        public const string ExecDir = "exec";
        public const string RouteFile = "route.json";
        public const string CommandFile = "cmd.jsonl";
        public const string EventFile = "evt.jsonl";
        public const string MasterHeartbeatFile = "nt.hb";
        public const string MasterCursorFile = "nt.cursor";
        public const string ExecStateFile = "exec.state";
        /// <summary>Heartbeat mastera starsi nez toto = master je prec (exekutor nic neruší, len to zapise a prevezme trailing).</summary>
        public const long MasterLostMs = 30000;

        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false);

        /// <summary>`Common\Files\TradeBot` terminalov MT5; env `TRADEBOT_BRIDGE_ROOT` ho presmeruje (testy).</summary>
        public static string DefaultRoot()
        {
            string env = Environment.GetEnvironmentVariable("TRADEBOT_BRIDGE_ROOT");
            if (!string.IsNullOrEmpty(env)) return env;
            string appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            return Path.Combine(Path.Combine(Path.Combine(Path.Combine(Path.Combine(appData, "MetaQuotes"), "Terminal"), "Common"), "Files"), "TradeBot");
        }

        /// <summary>`mt5exec_&lt;login&gt;-&lt;server&gt;` - ta ista identita uctu ako v id instancie (docs/LIVE.md).</summary>
        public static string ExecutorId(long login, string server)
        {
            string s = "mt5exec_" + login.ToString(CultureInfo.InvariantCulture) + "-" + (server ?? "");
            StringBuilder sb = new StringBuilder(s.Length);
            foreach (char c in s)
            {
                bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-';
                sb.Append(ok ? c : '-');
            }
            return sb.ToString();
        }

        public static string RouteDir(string root, string instance) { return Path.Combine(Path.Combine(root, BridgeDir), instance); }

        public static string ExecHeartbeatPath(string root, string executorId)
        {
            return Path.Combine(Path.Combine(root, ExecDir), executorId + ".hb.json");
        }

        public static string ExecLockPath(string root, string executorId)
        {
            return Path.Combine(Path.Combine(root, ExecDir), executorId + ".lock");
        }

        public static long NowMs() { return (long)(DateTime.UtcNow - Epoch).TotalMilliseconds; }

        public static string NewSession() { return Guid.NewGuid().ToString("N").Substring(0, 8); }

        /// <summary>Zapise subor celý naraz: tmp vedla ciela a presun. Citatel (druha platforma) moze mat ciel otvoreny -
        /// vtedy sa to par raz skusi znova.</summary>
        public static void AtomicWrite(string path, string text)
        {
            string dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            string tmp = path + "." + Guid.NewGuid().ToString("N").Substring(0, 6) + ".tmp";
            File.WriteAllText(tmp, text, Utf8);
            for (int attempt = 0; ; attempt++)
            {
                try
                {
                    if (File.Exists(path)) File.Replace(tmp, path, null);
                    else File.Move(tmp, path);
                    return;
                }
                catch (IOException)
                {
                    if (attempt >= 20) { try { File.Delete(tmp); } catch (IOException) { } throw; }
                    System.Threading.Thread.Sleep(5);
                }
                catch (UnauthorizedAccessException)
                {
                    if (attempt >= 20) { try { File.Delete(tmp); } catch (IOException) { } throw; }
                    System.Threading.Thread.Sleep(5);
                }
            }
        }

        /// <summary>Cely subor ako text, aj ked ho druha strana prave drzi otvoreny; null = neexistuje.</summary>
        public static string ReadShared(string path)
        {
            if (!File.Exists(path)) return null;
            for (int attempt = 0; ; attempt++)
            {
                try
                {
                    using (FileStream fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                    using (StreamReader r = new StreamReader(fs, Utf8))
                        return r.ReadToEnd();
                }
                catch (FileNotFoundException) { return null; }
                catch (IOException)
                {
                    if (attempt >= 20) throw;
                    System.Threading.Thread.Sleep(5);
                }
            }
        }

        /// <summary>Maly JSON subor (hb, route, stav); null = neexistuje alebo je prave rozpisany.</summary>
        public static Dictionary<string, object> ReadJsonFile(string path)
        {
            string text = ReadShared(path);
            if (string.IsNullOrEmpty(text)) return null;
            try { return Json.ParseObject(text); }
            catch (JsonException) { return null; }
        }
    }

    /// <summary>Append-only JSONL s vlastnym `seq` od 1 (pokracuje po restarte od posledneho riadku suboru).</summary>
    public sealed class JsonlLog
    {
        private readonly string _path;
        private long _seq;

        public JsonlLog(string path)
        {
            _path = path;
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            _seq = LastSeq(path);
        }

        public string FilePath { get { return _path; } }
        public long Seq { get { return _seq; } }

        private static long LastSeq(string path)
        {
            if (!File.Exists(path)) return 0;
            using (FileStream fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                long start = Math.Max(0, fs.Length - 65536);
                fs.Seek(start, SeekOrigin.Begin);
                byte[] buf = new byte[fs.Length - start];
                int n = 0;
                while (n < buf.Length) { int k = fs.Read(buf, n, buf.Length - n); if (k <= 0) break; n += k; }
                string[] lines = Encoding.UTF8.GetString(buf, 0, n).Split('\n');
                for (int i = lines.Length - 1; i >= 0; i--)
                {
                    string line = lines[i].Trim();
                    if (line.Length == 0) continue;
                    try
                    {
                        Dictionary<string, object> d = Json.ParseObject(line);
                        return (long)Json.GetDouble(d, "seq", 0.0);
                    }
                    catch (JsonException) { }   // rozpisany riadok na konci (pad pocas zapisu) alebo orezany zaciatok okna
                }
            }
            return 0;
        }

        /// <summary>Prida riadok `{"seq":n,"t":ms, ...polia}` a vrati jeho `seq`. Flush hned (druha strana caka).</summary>
        public long Append(long nowMs, Action<JsonWriter> fields)
        {
            long seq = _seq + 1;
            JsonWriter w = new JsonWriter();
            w.BeginObject();
            w.Key("seq").Value(seq).Key("t").Value(nowMs);
            fields(w);
            w.EndObject();
            byte[] bytes = new UTF8Encoding(false).GetBytes(w.ToString() + "\n");
            using (FileStream fs = new FileStream(_path, FileMode.Append, FileAccess.Write, FileShare.ReadWrite | FileShare.Delete))
            {
                fs.Write(bytes, 0, bytes.Length);
                fs.Flush(true);
            }
            _seq = seq;
            return seq;
        }
    }

    /// <summary>Citanie JSONL od bajtoveho offsetu; vracia len cele riadky (konciace '\n').</summary>
    public sealed class JsonlCursor
    {
        private readonly string _path;
        public long Offset;

        public JsonlCursor(string path, long offset)
        {
            _path = path;
            Offset = offset;
        }

        /// <summary>Jeden novy riadok: text a offset za nim.</summary>
        public struct Line
        {
            public string Text;
            public long End;
        }

        public List<Line> ReadNew()
        {
            List<Line> outp = new List<Line>();
            if (!File.Exists(_path)) return outp;
            using (FileStream fs = new FileStream(_path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                if (fs.Length < Offset) Offset = 0;   // subor niekto zmazal a zacal znova
                if (fs.Length == Offset) return outp;
                fs.Seek(Offset, SeekOrigin.Begin);
                byte[] buf = new byte[fs.Length - Offset];
                int n = 0;
                while (n < buf.Length) { int k = fs.Read(buf, n, buf.Length - n); if (k <= 0) break; n += k; }
                int start = 0;
                for (int i = 0; i < n; i++)
                {
                    if (buf[i] != (byte)'\n') continue;
                    string text = Encoding.UTF8.GetString(buf, start, i - start).Trim();
                    start = i + 1;
                    if (text.Length == 0) continue;
                    Line l = new Line();
                    l.Text = text;
                    l.End = Offset + start;
                    outp.Add(l);
                }
                Offset += start;
            }
            return outp;
        }
    }

    /// <summary>Strana strategie (NinjaTrader AddOn): pise prikazy, cita udalosti exekutora, hlasi zivost.</summary>
    public sealed class BridgeMaster
    {
        private readonly string _root;
        private readonly string _dir;
        private readonly JsonlLog _cmd;
        private readonly JsonlCursor _evt;
        private readonly string _cursorPath;

        public readonly RouteSpec Spec;
        public string Session { get; private set; }
        public string Instance { get { return Spec.Instance; } }
        public string Dir { get { return _dir; } }

        public BridgeMaster(string root, RouteSpec spec)
        {
            if (spec == null || string.IsNullOrEmpty(spec.Instance)) throw new ArgumentException("route bez instancie");
            if (string.IsNullOrEmpty(spec.To)) throw new ArgumentException("route bez exekutora (`to`)");
            _root = root;
            Spec = spec;
            Session = Bridge.NewSession();
            _dir = Bridge.RouteDir(root, spec.Instance);
            Directory.CreateDirectory(_dir);
            Bridge.AtomicWrite(Path.Combine(_dir, Bridge.RouteFile), spec.ToJson());
            _cmd = new JsonlLog(Path.Combine(_dir, Bridge.CommandFile));
            _cursorPath = Path.Combine(_dir, Bridge.MasterCursorFile);
            Dictionary<string, object> cur = Bridge.ReadJsonFile(_cursorPath);
            _evt = new JsonlCursor(Path.Combine(_dir, Bridge.EventFile), cur != null ? (long)Json.GetDouble(cur, "offset", 0.0) : 0);
        }

        private string Send(long nowMs, string action, Action<JsonWriter> fields)
        {
            string cid = Session + "-" + (_cmd.Seq + 1).ToString(CultureInfo.InvariantCulture);
            _cmd.Append(nowMs, delegate(JsonWriter w)
            {
                w.Key("cid").Value(cid);
                if (fields != null) fields(w);
                else w.Key("a").Value(action);
            });
            return cid;
        }

        /// <summary>Vstup z enginu. `refPrice` = posledna cena mastera, `expMs` = dokedy sa smie poslat brokerovi.</summary>
        public string Entry(long nowMs, OrderIntent intent, double refPrice, long expMs)
        {
            if (intent.Action != OrderAction.Entry || intent.Plan == null) throw new ArgumentException("Entry chce vstup s planom");
            return Send(nowMs, "entry", delegate(JsonWriter w)
            {
                intent.WriteFields(w);
                w.Key("ref").Value(refPrice).Key("exp").Value(expMs);
            });
        }

        public string Cancel(long nowMs, string id, string reason)
        {
            return Send(nowMs, "cancel", delegate(JsonWriter w)
            {
                w.Key("a").Value("cancel").Key("id").Value(id);
                if (!string.IsNullOrEmpty(reason)) w.Key("r").Value(reason);
            });
        }

        public string Close(long nowMs, string id, string reason)
        {
            return Send(nowMs, "close", delegate(JsonWriter w)
            {
                w.Key("a").Value("close").Key("id").Value(id);
                if (!string.IsNullOrEmpty(reason)) w.Key("r").Value(reason);
            });
        }

        /// <summary>Posun SL/TP (trailing) v cenach mastera; null = nemenene. `refPrice` na prepocet basis.</summary>
        public string Modify(long nowMs, string id, double? sl, double? tp, double refPrice, string reason)
        {
            return Send(nowMs, "modify", delegate(JsonWriter w)
            {
                w.Key("a").Value("modify").Key("id").Value(id).Key("sl").Value(sl).Key("tp").Value(tp).Key("ref").Value(refPrice);
                if (!string.IsNullOrEmpty(reason)) w.Key("r").Value(reason);
            });
        }

        /// <summary>Zrusit vsetky vstupy a zavriet vsetky pozicie route (control `flatten`).</summary>
        public string Flatten(long nowMs, string reason)
        {
            return Send(nowMs, "flatten", delegate(JsonWriter w)
            {
                w.Key("a").Value("flatten");
                if (!string.IsNullOrEmpty(reason)) w.Key("r").Value(reason);
            });
        }

        /// <summary>Po starte a po kazdom navrate spojenia: exekutor vrati `pos`/`order` riadky a `snapshot` s tymto cid.</summary>
        public string Sync(long nowMs)
        {
            return Send(nowMs, "sync", null);
        }

        /// <summary>Zivost mastera (`nt.hb`), raz za sekundu.</summary>
        public void Heartbeat(long nowMs, string mode)
        {
            JsonWriter w = new JsonWriter();
            w.BeginObject().Key("t").Value(nowMs).Key("session").Value(Session).Key("mode").Value(mode ?? "").EndObject();
            Bridge.AtomicWrite(Path.Combine(_dir, Bridge.MasterHeartbeatFile), w.ToString());
        }

        /// <summary>Nove udalosti exekutora (kazda raz; kurzor sa ulozi hned).</summary>
        public List<Dictionary<string, object>> Poll()
        {
            return Poll(true);
        }

        /// <summary>Nove udalosti exekutora. S `commit = false` sa kurzor na disk neulozi - master ho potvrdi
        /// `CommitCursor()` az po spracovani a zapise vlastneho stavu, aby pad medzi citanim a spracovanim udalosti
        /// nestratil (po restarte sa precitaju znova; spracovanie musi byt idempotentne).</summary>
        public List<Dictionary<string, object>> Poll(bool commit)
        {
            List<Dictionary<string, object>> outp = new List<Dictionary<string, object>>();
            List<JsonlCursor.Line> lines = _evt.ReadNew();
            if (lines.Count == 0) return outp;
            foreach (JsonlCursor.Line l in lines)
            {
                try { outp.Add(Json.ParseObject(l.Text)); }
                catch (JsonException) { }   // poskodeny riadok sa preskoci, nesmie zablokovat zvysok
            }
            _uncommitted = true;
            if (commit) CommitCursor();
            return outp;
        }

        private bool _uncommitted;

        /// <summary>Ulozi kurzor evt.jsonl na disk (po `Poll(false)`); bez nicoho noveho nerobi nic.</summary>
        public void CommitCursor()
        {
            if (!_uncommitted) return;
            JsonWriter w = new JsonWriter();
            w.BeginObject().Key("offset").Value(_evt.Offset).EndObject();
            Bridge.AtomicWrite(_cursorPath, w.ToString());
            _uncommitted = false;
        }

        /// <summary>Stav route podla heartbeatu exekutora.</summary>
        public string Status(long nowMs, out string detail)
        {
            Dictionary<string, object> hb = Bridge.ReadJsonFile(Bridge.ExecHeartbeatPath(_root, Spec.To));
            return RouteStatus.Evaluate(hb, Spec, Spec.Instance, nowMs, out detail);
        }
    }

    /// <summary>Strana vykonavaca (MT5 `TradeBotExecutor`): najde route urcene jemu, cita prikazy (kazdy cid raz,
    /// aj cez restart), pise udalosti a heartbeat.</summary>
    public sealed class BridgeExecutor
    {
        /// <summary>Kolko vykonanych cid si pamata kvoli idempotencii.</summary>
        public const int DoneKeep = 2000;

        private sealed class RouteState
        {
            public string Dir;
            public JsonlCursor Cmd;
            public JsonlLog Evt;
            public long Committed;
            public readonly List<KeyValuePair<string, long>> Inflight = new List<KeyValuePair<string, long>>();
            public readonly HashSet<string> InflightDone = new HashSet<string>();
            public readonly HashSet<string> Done = new HashSet<string>();
            public readonly LinkedList<string> DoneOrder = new LinkedList<string>();
        }

        private readonly string _root;
        private readonly Dictionary<string, RouteState> _routes = new Dictionary<string, RouteState>();
        private JsonWriter _hb;
        private bool _hbSymbols, _hbRoutes;

        public readonly string Id;

        private FileStream _lock;

        public BridgeExecutor(string root, string executorId)
        {
            _root = root;
            Id = executorId;
        }

        /// <summary>Vyhradny zamok `exec\&lt;id&gt;.lock` na cely beh: EA s tym istym id na druhom grafe alebo v druhom
        /// terminali nad tym istym Common\Files by citalo ten isty cmd.jsonl vlastnym kurzorom a kazdy vstup poslalo
        /// dvakrat. Zamok drzi operacny system, takze po pade procesu zmizne sam. Ked ho drzi iny, vyhodi vynimku.</summary>
        public void Lock()
        {
            if (_lock != null) return;
            string path = Bridge.ExecLockPath(_root, Id);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            try { _lock = new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
            catch (IOException)
            {
                throw new InvalidOperationException("exekutor " + Id + " uz bezi (iny graf alebo terminal s tym istym uctom) - druhu instanciu odmietam");
            }
        }

        /// <summary>Uvolni zamok z `Lock()`.</summary>
        public void Unlock()
        {
            if (_lock == null) return;
            try { _lock.Dispose(); } catch (IOException) { }
            _lock = null;
        }

        /// <summary>Route (id = nazov adresara) s `route.json` adresovanym tomuto exekutorovi.</summary>
        public Dictionary<string, RouteSpec> Routes()
        {
            Dictionary<string, RouteSpec> outp = new Dictionary<string, RouteSpec>();
            string dir = Path.Combine(_root, Bridge.BridgeDir);
            if (!Directory.Exists(dir)) return outp;
            string[] dirs = Directory.GetDirectories(dir);
            Array.Sort(dirs, StringComparer.Ordinal);
            foreach (string d in dirs)
            {
                Dictionary<string, object> raw = Bridge.ReadJsonFile(Path.Combine(d, Bridge.RouteFile));
                if (raw == null) continue;
                RouteSpec spec = RouteSpec.FromDict(raw);
                if (spec.To != Id) continue;
                outp[Path.GetFileName(d)] = spec;
            }
            return outp;
        }

        private RouteState Route(string routeId)
        {
            RouteState s;
            if (_routes.TryGetValue(routeId, out s)) return s;
            s = new RouteState();
            s.Dir = Bridge.RouteDir(_root, routeId);
            Directory.CreateDirectory(s.Dir);
            Dictionary<string, object> st = Bridge.ReadJsonFile(Path.Combine(s.Dir, Bridge.ExecStateFile));
            if (st != null)
            {
                s.Committed = (long)Json.GetDouble(st, "offset", 0.0);
                List<object> done = Json.Get(st, "done") as List<object>;
                if (done != null)
                    foreach (object o in done)
                    {
                        string cid = Convert.ToString(o, CultureInfo.InvariantCulture);
                        if (s.Done.Add(cid)) s.DoneOrder.AddLast(cid);
                    }
            }
            s.Cmd = new JsonlCursor(Path.Combine(s.Dir, Bridge.CommandFile), s.Committed);
            s.Evt = new JsonlLog(Path.Combine(s.Dir, Bridge.EventFile));
            _routes[routeId] = s;
            return s;
        }

        /// <summary>Nove prikazy route ako text riadkov JSON - bez tych, ktore uz boli vykonane (`Done`). Prikaz, ktory
        /// exekutor precital, ale pred padom nestihol oznacit `Done`, pride po restarte znova.</summary>
        public List<string> Poll(string routeId)
        {
            RouteState s = Route(routeId);
            List<string> outp = new List<string>();
            foreach (JsonlCursor.Line l in s.Cmd.ReadNew())
            {
                string cid;
                try { cid = Json.GetString(Json.ParseObject(l.Text), "cid", ""); }
                catch (JsonException) { cid = ""; }
                if (cid == "" || s.Done.Contains(cid))
                {
                    // poskodeny alebo uz vykonany: posunie sa aj potvrdeny offset, ked pred nim nic necaka
                    s.Inflight.Add(new KeyValuePair<string, long>("", l.End));
                    continue;
                }
                s.Inflight.Add(new KeyValuePair<string, long>(cid, l.End));
                outp.Add(l.Text);
            }
            Advance(s);
            return outp;
        }

        /// <summary>Prikaz vykonany (alebo odmietnuty) - po restarte sa uz nezopakuje.</summary>
        public void Done(string routeId, string cid)
        {
            RouteState s = Route(routeId);
            if (string.IsNullOrEmpty(cid) || s.Done.Contains(cid)) return;
            s.Done.Add(cid);
            s.DoneOrder.AddLast(cid);
            while (s.DoneOrder.Count > DoneKeep) { s.Done.Remove(s.DoneOrder.First.Value); s.DoneOrder.RemoveFirst(); }
            s.InflightDone.Add(cid);
            Advance(s);
            Save(s);
        }

        private static void Advance(RouteState s)
        {
            while (s.Inflight.Count > 0)
            {
                KeyValuePair<string, long> head = s.Inflight[0];
                if (head.Key != "" && !s.InflightDone.Contains(head.Key)) break;
                s.InflightDone.Remove(head.Key);
                s.Committed = head.Value;
                s.Inflight.RemoveAt(0);
            }
        }

        private static void Save(RouteState s)
        {
            JsonWriter w = new JsonWriter();
            w.BeginObject().Key("offset").Value(s.Committed).Key("done").BeginArray();
            foreach (string cid in s.DoneOrder) w.Value(cid);
            w.EndArray().EndObject();
            Bridge.AtomicWrite(Path.Combine(s.Dir, Bridge.ExecStateFile), w.ToString());
        }

        /// <summary>Udalost do `evt.jsonl` route; vrati jej `seq`.</summary>
        public long Emit(string routeId, long nowMs, Action<JsonWriter> fields)
        {
            return Route(routeId).Evt.Append(nowMs, fields);
        }

        /// <summary>Ako stary je heartbeat mastera route (ms); -1 = nikdy neprisiel.</summary>
        public long MasterAgeMs(string routeId, long nowMs)
        {
            Dictionary<string, object> hb = Bridge.ReadJsonFile(Path.Combine(Bridge.RouteDir(_root, routeId), Bridge.MasterHeartbeatFile));
            if (hb == null) return -1;
            return Math.Max(0, nowMs - (long)Json.GetDouble(hb, "t", 0.0));
        }

        /// <summary>Session mastera z jeho heartbeatu ("" = ziadny) - nova session = master sa restartoval.</summary>
        public string MasterSession(string routeId)
        {
            Dictionary<string, object> hb = Bridge.ReadJsonFile(Path.Combine(Bridge.RouteDir(_root, routeId), Bridge.MasterHeartbeatFile));
            return hb == null ? "" : Json.GetString(hb, "session", "");
        }

        // -- heartbeat exekutora: Begin, Symbol*, Route*, Write ---------------------------------- //

        public void HeartbeatBegin(long nowMs, long login, string server, string marginMode, bool connected, bool tradeAllowed, string version)
        {
            _hb = new JsonWriter();
            _hb.BeginObject();
            _hb.Key("t").Value(nowMs).Key("id").Value(Id).Key("v").Value(version ?? "");
            _hb.Key("login").Value(login).Key("server").Value(server ?? "").Key("margin_mode").Value(marginMode ?? "");
            _hb.Key("connected").Value(connected).Key("trade_allowed").Value(tradeAllowed);
            _hbSymbols = _hbRoutes = false;
        }

        public void HeartbeatSymbol(string name, double tick, double tickValue, double volMin, double volStep, double volMax,
                                    int tradeMode, double bid, double ask)
        {
            if (_hb == null) throw new InvalidOperationException("HeartbeatBegin nebol zavolany");
            if (_hbRoutes) throw new InvalidOperationException("symboly idu pred route");
            if (!_hbSymbols) { _hb.Key("symbols").BeginArray(); _hbSymbols = true; }
            _hb.BeginObject().Key("name").Value(name).Key("tick").Value(tick).Key("tick_value").Value(tickValue);
            _hb.Key("vol_min").Value(volMin).Key("vol_step").Value(volStep).Key("vol_max").Value(volMax);
            _hb.Key("trade_mode").Value(tradeMode).Key("bid").Value(bid).Key("ask").Value(ask).EndObject();
        }

        public void HeartbeatRoute(string routeId, string state, string detail)
        {
            if (_hb == null) throw new InvalidOperationException("HeartbeatBegin nebol zavolany");
            if (_hbSymbols && !_hbRoutes) _hb.EndArray();
            if (!_hbSymbols) { _hb.Key("symbols").BeginArray().EndArray(); _hbSymbols = true; }
            if (!_hbRoutes) { _hb.Key("routes").BeginArray(); _hbRoutes = true; }
            _hb.BeginObject().Key("id").Value(routeId).Key("state").Value(state ?? "");
            if (!string.IsNullOrEmpty(detail)) _hb.Key("detail").Value(detail);
            _hb.EndObject();
        }

        public void HeartbeatWrite()
        {
            if (_hb == null) throw new InvalidOperationException("HeartbeatBegin nebol zavolany");
            if (!_hbSymbols) { _hb.Key("symbols").BeginArray().EndArray(); _hbSymbols = true; }
            else if (!_hbRoutes) _hb.EndArray();
            if (!_hbRoutes) _hb.Key("routes").BeginArray().EndArray();
            else _hb.EndArray();
            _hb.EndObject();
            Bridge.AtomicWrite(Bridge.ExecHeartbeatPath(_root, Id), _hb.ToString());
            _hb = null;
        }
    }
}
