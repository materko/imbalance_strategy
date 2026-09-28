// Live telemetria: bezaca strategia (NinjaTrader 8, MetaTrader 5) pise bary, zamery engine-u, prechody
// stavov, kresby, vyplnenia a posuny SL/TP adaptera (`Modify`, trailing) do append-only JSONL spoolu
// na lokalnom disku; agent hubu ho odtial
// odosiela do webapp (docs/LIVE.md). Siet z platformy nejde nikdy - ked nic necita, subory cakaju.
//
// Zapis je synchronny v obchodnom vlakne (riadok JSON na uzavrety bar je lacny), ale NIKDY nesmie
// zhodit strategiu: kazda verejna metoda chyta Exception, pri chybe si zapise `LastError`, nastavi
// `Broken` a dalsie volania su no-op. Hostitel si `Broken` precita a vypise, obchoduje dalej.
//
// Identita: adresar `<platform>_<account>_<symbol>_<tf>m_<strategy>` (stabilny cez restarty; to iste
// pocita `tradebot.live.schema.instance_id`), session = 8 hex znakov na jeden start, `seq` od 1 v ramci
// session. Subor `<yyyyMMdd-HHmmss UTC>_<session>.jsonl`; pri zmene UTC dna sa zacne novy subor (hello
// sa zopakuje, seq pokracuje). Schema riadkov: docs/LIVE.md, "Schema udalosti".
//
// Jazyk je zamerne C# 5 a len BCL (csc.exe z .NET Frameworku, NinjaTrader, Mono).
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

namespace TradeBot.Core
{
    public sealed class LiveSpool : IDisposable
    {
        public const int Schema = 1;
        /// <summary>Mimo realtime sa flushuje po tolkych riadkoch (a pri zatvoreni).</summary>
        public const int FlushEvery = 200;

        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        private readonly object _gate = new object();
        private readonly string _root;
        private readonly string _dir;
        private readonly string _platform, _account, _symbol, _strategy, _profile, _host;
        private readonly int _tf;
        private readonly bool _tester;
        private readonly Dictionary<string, object> _config;
        private readonly InstrumentSpec _instrument;

        private StreamWriter _writer;
        private string _path = "";
        private string _fileDay = "";
        private long _seq;
        private int _unflushed;
        private bool _realtime;
        private bool _closed;

        public string Instance { get; private set; }
        public string Session { get; private set; }
        /// <summary>Cesta aktualneho suboru (po rotacii dna sa zmeni).</summary>
        public string Path { get { lock (_gate) { return _path; } } }
        public bool Broken { get; private set; }
        public string LastError { get; private set; }

        /// <summary>Flush po kazdom riadku (nazivo); inak kazdych `FlushEvery` riadkov a pri zatvoreni.</summary>
        public bool Realtime
        {
            get { return _realtime; }
            set
            {
                try
                {
                    lock (_gate)
                    {
                        _realtime = value;
                        if (_writer == null) return;
                        _writer.AutoFlush = value;
                        if (value) { _writer.Flush(); _unflushed = 0; }
                    }
                }
                catch (Exception e) { Break(e); }
            }
        }

        // ------------------------------------------------------------------ //

        /// <summary>`&lt;platform&gt;_&lt;account&gt;_&lt;symbol&gt;_&lt;tf&gt;m_&lt;strategy&gt;`, znaky mimo [A-Za-z0-9._-] -> '-'.
        /// Musi dat to iste, co `tradebot.live.schema.instance_id` (nazov adresara = kluc instancie).</summary>
        public static string InstanceId(string platform, string account, string symbol, int tfMinutes, string strategy)
        {
            return Clean(platform) + "_" + Clean(account) + "_" + Clean(symbol) + "_"
                 + Clean(tfMinutes.ToString(CultureInfo.InvariantCulture) + "m") + "_" + Clean(strategy);
        }

        private static string Clean(string s)
        {
            if (s == null) return "";
            StringBuilder sb = new StringBuilder(s.Length);
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-';
                sb.Append(ok ? c : '-');
            }
            return sb.ToString();
        }

        public LiveSpool(string root, string platform, string account, string symbol, int tfMinutes, string strategy,
                         string profile, bool tester, Dictionary<string, object> config, InstrumentSpec instrument)
        {
            LastError = "";
            _root = root ?? "";
            _platform = platform ?? ""; _account = account ?? ""; _symbol = symbol ?? ""; _strategy = strategy ?? "";
            _profile = profile ?? ""; _tf = tfMinutes; _tester = tester; _config = config; _instrument = instrument;
            Instance = InstanceId(_platform, _account, _symbol, _tf, _strategy);
            Session = Guid.NewGuid().ToString("N").Substring(0, 8);
            _host = "";
            try { _host = Environment.MachineName ?? ""; } catch (Exception) { }
            _dir = "";
            try
            {
                if (_root.Length == 0) throw new ArgumentException("koren spoolu je prazdny");
                _dir = System.IO.Path.Combine(_root, Instance);
                lock (_gate) { OpenFile(DateTime.UtcNow); }
            }
            catch (Exception e) { Break(e); }
        }

        // ------------------------------------------------------------------ //
        // Subor
        // ------------------------------------------------------------------ //

        private static long NowMs() { return (long)Math.Round((DateTime.UtcNow - Epoch).TotalMilliseconds); }

        /// <summary>Otvori (novy) subor session pre dany UTC cas a napise `hello`. Vola sa pod zamkom.</summary>
        private void OpenFile(DateTime utcNow)
        {
            if (_writer != null) { _writer.Flush(); _writer.Dispose(); _writer = null; }
            Directory.CreateDirectory(_dir);
            _fileDay = utcNow.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
            _path = System.IO.Path.Combine(_dir, utcNow.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture) + "_" + Session + ".jsonl");
            // FileShare.ReadWrite: agent hubu subor cita, kym sa don pise (a nesmie tym zapis zablokovat)
            _writer = new StreamWriter(new FileStream(_path, FileMode.Append, FileAccess.Write, FileShare.ReadWrite),
                                       new UTF8Encoding(false));
            _writer.AutoFlush = _realtime;
            _unflushed = 0;
            WriteHello();
            _writer.Flush();
        }

        /// <summary>Zacne riadok `{"seq":N,"t":ms,"k":kind` - objekt ostava otvoreny. Vola sa pod zamkom;
        /// pri zmene UTC dna najprv otoci subor (hello do noveho ide s vlastnym seq).</summary>
        private JsonWriter Begin(string kind)
        {
            DateTime now = DateTime.UtcNow;
            if (kind != "hello" && now.ToString("yyyyMMdd", CultureInfo.InvariantCulture) != _fileDay) OpenFile(now);
            JsonWriter w = new JsonWriter();
            w.BeginObject();
            w.Key("seq").Value(++_seq).Key("t").Value(NowMs()).Key("k").Value(kind);
            return w;
        }

        private void End(JsonWriter w)
        {
            w.EndObject();
            _writer.WriteLine(w.ToString());
            if (!_realtime && ++_unflushed >= FlushEvery) { _writer.Flush(); _unflushed = 0; }
        }

        private void Break(Exception e)
        {
            Broken = true;
            LastError = e.GetType().Name + ": " + e.Message;
            try { if (_writer != null) { _writer.Dispose(); } } catch (Exception) { }
            _writer = null;
        }

        private bool Off() { return Broken || _closed || _writer == null; }

        // ------------------------------------------------------------------ //
        // JSON pomocne
        // ------------------------------------------------------------------ //

        /// <summary>Config engine-u je strom z `Json.Parse` (objekty, polia, skalare) - `ValueObject` pozna len skalare.</summary>
        private static void WriteAny(JsonWriter w, object v)
        {
            Dictionary<string, object> d = v as Dictionary<string, object>;
            if (d != null)
            {
                w.BeginObject();
                foreach (KeyValuePair<string, object> kv in d) { w.Key(kv.Key); WriteAny(w, kv.Value); }
                w.EndObject();
                return;
            }
            List<object> list = v as List<object>;
            if (list != null)
            {
                w.BeginArray();
                foreach (object item in list) WriteAny(w, item);
                w.EndArray();
                return;
            }
            w.ValueObject(v);
        }

        /// <summary>Ten isty tvar ako instrument JSON mostu do Freqtrade (`tradebot/adapters/csharp/engine.py`).</summary>
        private static void WriteInstrument(JsonWriter w, InstrumentSpec i)
        {
            if (i == null) { w.Null(); return; }
            w.BeginObject();
            w.Key("symbol").Value(i.Symbol).Key("venue").Value(i.Venue);
            w.Key("tick_size").Value(i.TickSize).Key("point_value").Value(i.PointValue);
            w.Key("qty_step").Value(i.QtyStep).Key("min_qty").Value(i.MinQty).Key("has_real_volume").Value(i.HasRealVolume);
            w.EndObject();
        }

        private void WriteHello()
        {
            JsonWriter w = Begin("hello");
            w.Key("schema").Value(Schema).Key("platform").Value(_platform).Key("account").Value(_account);
            w.Key("symbol").Value(_symbol).Key("tf").Value(_tf).Key("strategy").Value(_strategy).Key("profile").Value(_profile);
            w.Key("session").Value(Session).Key("host").Value(_host).Key("tester").Value(_tester);
            w.Key("config"); WriteAny(w, _config ?? new Dictionary<string, object>());
            w.Key("instrument"); WriteInstrument(w, _instrument);
            End(w);
        }

        private static void WriteDrawings(JsonWriter w, IList<DrawCommand> drawings)
        {
            w.Key("d").BeginArray();
            foreach (DrawCommand d in drawings) d.WriteJson(w);
            w.EndArray();
        }

        // ------------------------------------------------------------------ //
        // Udalosti
        // ------------------------------------------------------------------ //

        /// <summary>Uzavrety bar grafu: `bar` + `order` na kazdy zamer + `event` na kazdy prechod + `draw`, ked engine kreslil.</summary>
        public void Bar(Bar bar, EngineOutput output, bool ready, int marketBias)
        {
            try
            {
                lock (_gate)
                {
                    if (Off() || bar == null) return;
                    JsonWriter w = Begin("bar");
                    w.Key("bt").Value(bar.Time).Key("o").Value(bar.Open).Key("h").Value(bar.High).Key("l").Value(bar.Low);
                    w.Key("c").Value(bar.Close).Key("v").Value(bar.Volume).Key("ready").Value(ready).Key("mb").Value(marketBias);
                    if (output != null && output.CloseSession) w.Key("cs").Value(true);
                    End(w);
                    if (output == null) return;
                    foreach (OrderIntent i in output.Orders)
                    {
                        w = Begin("order");
                        w.Key("bt").Value(bar.Time).Key("ready").Value(ready);
                        i.WriteFields(w);
                        End(w);
                    }
                    foreach (StateEvent e in output.Events)
                    {
                        w = Begin("event");
                        w.Key("bt").Value(bar.Time);
                        e.WriteFields(w);
                        End(w);
                    }
                    if (output.Drawings.Count > 0)
                    {
                        w = Begin("draw");
                        w.Key("bt").Value(bar.Time);
                        WriteDrawings(w, output.Drawings);
                        End(w);
                    }
                }
            }
            catch (Exception e) { Break(e); }
        }

        /// <summary>Kresby posledneho baru (Pine `barstate.islast`) - `draw` s `final:true`.</summary>
        public void FinalDrawings(Bar bar, IList<DrawCommand> drawings)
        {
            try
            {
                lock (_gate)
                {
                    if (Off() || bar == null || drawings == null || drawings.Count == 0) return;
                    JsonWriter w = Begin("draw");
                    w.Key("bt").Value(bar.Time);
                    WriteDrawings(w, drawings);
                    w.Key("final").Value(true);
                    End(w);
                }
            }
            catch (Exception e) { Break(e); }
        }

        /// <summary>Vyplnenie u brokera (adapter, nie engine): `in` = vstup, `out` = vystup s menom vystupu.</summary>
        public void Fill(long execMs, string id, bool entry, string exitName, double price, double qty, bool ready)
        {
            try
            {
                lock (_gate)
                {
                    if (Off()) return;
                    JsonWriter w = Begin("fill");
                    w.Key("ft").Value(execMs).Key("id").Value(id ?? "").Key("side").Value(entry ? "in" : "out");
                    w.Key("exit").Value(entry ? "" : (exitName ?? "")).Key("price").Value(price).Key("qty").Value(qty).Key("ready").Value(ready);
                    End(w);
                }
            }
            catch (Exception e) { Break(e); }
        }

        /// <summary>Adapter posunul SL/TP pracujuceho orderu (trailing, rucny zasah...): riadok `order`
        /// s `a:"modify"`, `p{sl,tp}` (null = nemenene) a dovodom `r`. Zamery enginu (entry/cancel/close)
        /// idu cez `Bar`; toto je jediny `order` riadok, ktory pise adapter sam.</summary>
        public void Modify(long barMs, string id, double? sl, double? tp, string reason, bool ready)
        {
            try
            {
                lock (_gate)
                {
                    if (Off()) return;
                    JsonWriter w = Begin("order");
                    w.Key("bt").Value(barMs).Key("ready").Value(ready).Key("a").Value("modify").Key("id").Value(id ?? "");
                    w.Key("p").BeginObject().Key("sl").Value(sl).Key("tp").Value(tp).EndObject();
                    w.Key("r").Value(reason ?? "");
                    End(w);
                }
            }
            catch (Exception e) { Break(e); }
        }

        /// <summary>Poznamka adaptera (`info` / `warn` / `error`).</summary>
        public void Note(string level, string text)
        {
            try
            {
                lock (_gate)
                {
                    if (Off()) return;
                    JsonWriter w = Begin("note");
                    w.Key("level").Value(string.IsNullOrEmpty(level) ? "info" : level).Key("text").Value(text ?? "");
                    End(w);
                }
            }
            catch (Exception e) { Break(e); }
        }

        /// <summary>Adapter potvrdzuje rezim z control suboru (faza 2): `mode` enabled/paused/flatten,
        /// `profile` prave nacitany profil, `source` odkial rezim prisiel (control / default).</summary>
        public void Control(string mode, string profile, string source)
        {
            try
            {
                lock (_gate)
                {
                    if (Off()) return;
                    JsonWriter w = Begin("control");
                    w.Key("mode").Value(string.IsNullOrEmpty(mode) ? "enabled" : mode);
                    w.Key("profile").Value(profile ?? "").Key("source").Value(source ?? "");
                    End(w);
                }
            }
            catch (Exception e) { Break(e); }
        }

        /// <summary>`Engine.Stats()` + pocitadla adaptera - pri ukonceni, pred `Close`.</summary>
        public void Stats(Dictionary<string, double> stats)
        {
            try
            {
                lock (_gate)
                {
                    if (Off()) return;
                    JsonWriter w = Begin("stat");
                    w.Key("stats").BeginObject();
                    if (stats != null)
                        foreach (KeyValuePair<string, double> kv in stats) w.Key(kv.Key).Value(kv.Value);
                    w.EndObject();
                    End(w);
                }
            }
            catch (Exception e) { Break(e); }
        }

        /// <summary>`bye` + zatvorenie suboru. Dalsie volania su no-op.</summary>
        public void Close(string reason)
        {
            try
            {
                lock (_gate)
                {
                    if (Off()) { _closed = true; return; }
                    JsonWriter w = Begin("bye");
                    w.Key("reason").Value(reason ?? "");
                    End(w);
                    _writer.Flush();
                    _writer.Dispose();
                    _writer = null;
                    _closed = true;
                }
            }
            catch (Exception e) { Break(e); _closed = true; }
        }

        public void Dispose()
        {
            if (!_closed) Close("dispose");
        }
    }
}
