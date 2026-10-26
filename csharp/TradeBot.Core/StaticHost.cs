// Staticka fasada engine-u pre hostitelov, ktori vedia volat len STATICKE metody s jednoduchymi typmi -
// dnes MetaTrader 5 (`#import "TradeBot.dll"`: MQL5 si z .NET assembly sam vygeneruje obal, ale len pre
// verejne staticke metody s int/long/double/bool/string a ich poliami; instancie ani struktury nepozna).
//
// Engine sa preto drzi v tabulke pod celociselnym handle. Vstupy su tie iste ako v `EngineHost`, vystup
// ten isty JSON na bar - takze parita s Python predlohou aj export signalov su rovnake ako v NinjaTraderi
// a v moste do Freqtrade. Okno informativneho TF si fasada sklada sama z uzavretych HTF barov (`FeedHtf`),
// presne ako adapter NinjaTrader: hostitel nemusi vediet, co je vo vnutri okna.
//
// Vynimky cez hranicu .NET -> MQL5 nechodia spolahlivo, preto kazda metoda chybu chyti, odlozi do
// `LastError()` a vrati -1 / prazdny retazec. Hostitel po kazdom volani, ktore vrati -1 alebo "", precita
// `LastError()`.
//
// Trieda je ZAMERNE v globalnom namespace (jedina v jadre): MetaEditor (overene 25. 9. 2026, build 5xxx)
// generuje obaly len pre triedy bez namespace - `TradeBot.Core.StaticHost` by v MQL5 nebolo vidiet vobec.
// V MQL5 sa vola `StaticHost::Metoda(...)`; z pythonnet `clr.StaticHost` / `import StaticHost`.
//
// Live telemetria (docs/LIVE.md): `SpoolOpen` otvori `LiveSpool` pre slot (kluc, TF, config a instrument
// pozna zo slotu), `SpoolBar` napise posledny bar z `OnBar`, `SpoolFill`/`SpoolModify` (posun SL/TP
// adapterom, napr. trailing)/`SpoolNote`/`SpoolClose` zvysok;
// `Destroy` zavrie spool, ak ostal otvoreny. Chyba spoolu strategiu nezhodi: -1 a text v `LastError()`.
//
// Verzia 3: `SpoolOpenSlot`/`InstanceIdSlot` - slot nasadenia v id instancie (viac nasadeni tej istej strategie
// na tom istom ucte, symbole a TF s roznymi profilmi, docs/MT5.md). Nove mena, nie pretazenie: MQL5 aj reflexia
// v testoch hladaju metodu podla mena.
//
// Verzia 4: `SpoolMinute` - uzavrety 1m bar symbolu (`m1`) do telemetrie, z ktoreho sa sklada sklad zivych sviecok.
//
// `Bridge*` (bez zmeny verzie, ako `SpoolHeartbeat`): MT5 exekutor pre ordery strategie, ktora bezi v inej platforme
// (docs/ROUTING.md); vstupy v `OnBar` mozu niest `life` (`OrderLife`), EA strategii ho ignoruje.
using System;
using System.Collections.Generic;
using TradeBot.Core;

public static class StaticHost
{
    private sealed class Slot
    {
        public EngineHost Host;
        public IHtfFeeder Htf;
        public LiveSpool Spool;
    }

    private static readonly object Lock = new object();
    private static readonly Dictionary<int, Slot> Slots = new Dictionary<int, Slot>();
    private static int _next = 1;
    /// <summary>Chyba za vlakno: kazde EA v MT5 bezi vo vlastnom vlakne a cez jednu spolocnu premennu by si
    /// EA strategii a exekutor chybu navzajom prepisali skor, nez ju volajuci precita.</summary>
    [ThreadStatic] private static string _lastError;

    /// <summary>Posledna chyba (text vynimky) alebo prazdny retazec. Cita sa po -1 / "".</summary>
    public static string LastError() { return _lastError ?? ""; }

    private static void Fail(Exception e) { _lastError = e.GetType().Name + ": " + e.Message; }

    private static Slot Get(int handle)
    {
        lock (Lock)
        {
            Slot s;
            if (!Slots.TryGetValue(handle, out s)) throw new ArgumentException("neznamy handle engine-u " + handle);
            return s;
        }
    }

    /// <summary>Verzia fasady - hostitel si ju overi, kym zacne (zmena kontraktu = ina verzia).</summary>
    public static int Version() { return 5; }

    /// <summary>Zivy EA: engine s koncom dna (EOD) chce byt v `nowMs` (UTC) bez pozicie aj bez barov - zatvorenie
    /// podla hodin, ked bar pred 15:59 NY neprisiel (audit N-LIVE-7). 1 ano, 0 nie (alebo engine bez EOD), -1 chyba.</summary>
    public static int EodDue(int handle, long nowMs)
    {
        try
        {
            IClockFlatten clock = ClockFlatten.Find(Get(handle).Host.Engine);
            return clock != null && clock.FlattenDue(nowMs) ? 1 : 0;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Kluce C# strategii v tejto assembly, oddelene ciarkou.</summary>
    public static string Strategies()
    {
        try { return EngineHost.Strategies(); }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>Vytvori engine; vrati handle > 0, alebo -1 (chyba v `LastError`).</summary>
    public static int Create(string key, string configJson, string instrumentJson, int chartTfMinutes)
    {
        try
        {
            EngineRegistry.Reset();   // hostitel mohol DLL znovu nacitat
            Slot s = new Slot();
            s.Host = new EngineHost(key, configJson, instrumentJson, chartTfMinutes);
            s.Htf = s.Host.Engine.CreateHtfFeeder();
            lock (Lock)
            {
                int h = _next++;
                Slots[h] = s;
                _lastError = "";
                return h;
            }
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    public static void Destroy(int handle)
    {
        Slot s = null;
        lock (Lock)
        {
            if (Slots.TryGetValue(handle, out s)) Slots.Remove(handle);
        }
        try { if (s != null && s.Spool != null) { s.Spool.Close("destroy"); s.Spool = null; } }
        catch (Exception e) { Fail(e); }
    }

    /// <summary>`{"key","required_history","describe","warmup":[...]}` - ako `EngineHost.Info`.</summary>
    public static string Info(int handle)
    {
        try { return Get(handle).Host.Info(); }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>Kolko barov grafu treba, kym su signaly platne; -1 pri chybe.</summary>
    public static int RequiredHistory(int handle)
    {
        try { return Get(handle).Host.Engine.RequiredHistory; }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Kolko barov grafu prehrat pred startom nazivo, aby sa rozbehli aj indikatory na vlastnom TF
    /// (filter trendu na 60m, ADX/Supertrend) - zivy adapter ich nesieje (`Warmup.LiveChartBars`); -1 pri chybe.</summary>
    public static int LiveHistory(int handle)
    {
        try
        {
            IEngine e = Get(handle).Host.Engine;
            return Math.Max(e.RequiredHistory, e.Warmup != null ? e.Warmup.LiveChartBars : 0);
        }
        catch (Exception ex) { Fail(ex); return -1; }
    }

    /// <summary>TF informativnej serie v minutach; 0 = strategia ju nema; -1 chyba.</summary>
    public static int HtfTfMinutes(int handle)
    {
        try { Slot s = Get(handle); return s.Htf != null ? s.Htf.TfMinutes : 0; }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Jeden UZAVRETY bar informativneho TF (cas otvorenia v ms UTC). Vola sa pred barom grafu,
    /// s ktorym sa uzavrel; okno pre bar grafu si engine vyberie sam podla casu.</summary>
    public static int FeedHtf(int handle, long time, double open, double high, double low, double close, double volume)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Htf == null) return 0;
            s.Htf.Feed(new Bar(time, open, high, low, close, volume));
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Jeden uzavrety bar grafu (cas otvorenia v ms UTC). Vrati JSON ako `EngineHost.OnBar`
    /// (`o` ordery, `d` kresby, `e` udalosti, `cs` koniec seansy, `mb` bias) alebo "" pri chybe.</summary>
    public static string OnBar(int handle, long time, double open, double high, double low, double close, double volume,
                               double positionSize, bool dailyWinLimitReached, string openOrderIds)
    {
        try
        {
            Slot s = Get(handle);
            HtfWindow w = s.Htf != null ? s.Htf.WindowFor(time) : null;
            long[] ht = null; double[] hv = null; double sma = 0;
            if (w != null)
            {
                ht = new long[w.Bars.Length]; hv = new double[w.Bars.Length * 5]; sma = w.VolSma;
                for (int i = 0; i < w.Bars.Length; i++)
                {
                    Bar b = w.Bars[i];
                    ht[i] = b.Time; hv[i * 5] = b.Open; hv[i * 5 + 1] = b.High; hv[i * 5 + 2] = b.Low;
                    hv[i * 5 + 3] = b.Close; hv[i * 5 + 4] = b.Volume;
                }
            }
            return s.Host.OnBar(time, open, high, low, close, volume, ht, hv, sma,
                                positionSize, dailyWinLimitReached, openOrderIds ?? "");
        }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>Seeding indikatora vlastnou predhistoriou (`values` = 5 hodnot o,h,l,c,v na kazdy cas).
    /// Vrati pocet uzavretych barov alebo -1.</summary>
    public static int Seed(int handle, string name, long[] times, double[] values, bool hasPartial)
    {
        try { return Get(handle).Host.Seed(name, times, values, hasPartial); }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Kresby, ktore patria az na posledny bar (Pine `barstate.islast`), ako JSON pole.</summary>
    public static string FinalDrawings(int handle, long time, double open, double high, double low, double close, double volume)
    {
        try { return Get(handle).Host.FinalDrawings(time, open, high, low, close, volume); }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>Volne pomenovane cisla engine-u (`max_daily_wins`, pocty zon...) ako JSON objekt.</summary>
    public static string Stats(int handle)
    {
        try { return Get(handle).Host.Stats(); }
        catch (Exception e) { Fail(e); return ""; }
    }

    // -- live telemetria (docs/LIVE.md) ------------------------------------------------------- //

    private static void FailSpool(LiveSpool sp) { _lastError = "LiveSpool: " + sp.LastError; }

    /// <summary>Otvori spool `root/instance/start_session.jsonl` a napise `hello`. Kluc strategie, TF,
    /// config a instrument berie zo slotu. Vrati 1, alebo -1 (chyba v `LastError`; engine bezi dalej).</summary>
    public static int SpoolOpen(int handle, string root, string platform, string account, string symbol, string profile, bool tester)
    {
        return SpoolOpenSlot(handle, root, platform, account, symbol, profile, tester, "");
    }

    /// <summary>`SpoolOpen` so slotom nasadenia v id instancie (prazdny = bez neho).</summary>
    public static int SpoolOpenSlot(int handle, string root, string platform, string account, string symbol, string profile,
                                    bool tester, string slot)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool != null) { s.Spool.Close("reopen"); s.Spool = null; }
            LiveSpool sp = new LiveSpool(root, platform, account, symbol, s.Host.Engine.ChartTfMinutes, s.Host.Key,
                                         profile, tester, s.Host.Config, s.Host.Instrument, slot ?? "");
            if (sp.Broken) { FailSpool(sp); return -1; }
            s.Spool = sp;
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Nazivo: flush po kazdom riadku. 1 ok, 0 spool nie je otvoreny, -1 chyba.</summary>
    public static int SpoolRealtime(int handle, bool realtime)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null) return 0;
            s.Spool.Realtime = realtime;
            if (s.Spool.Broken) { FailSpool(s.Spool); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Napise posledny bar z `OnBar` (bar + order* + event* + draw). 1 ok, 0 bez baru alebo bez spoolu, -1 chyba.</summary>
    public static int SpoolBar(int handle, bool ready)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null || s.Host.LastBar == null) return 0;
            s.Spool.Bar(s.Host.LastBar, s.Host.LastOutput, ready, s.Host.LastBias);
            if (s.Spool.Broken) { FailSpool(s.Spool); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Uzavrety 1m bar symbolu (cas otvorenia v ms UTC) - riadok `m1`. 1 ok, 0 bez spoolu, -1 chyba.</summary>
    public static int SpoolMinute(int handle, long barMs, double open, double high, double low, double close, double volume)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null) return 0;
            s.Spool.Minute(barMs, open, high, low, close, volume);
            if (s.Spool.Broken) { FailSpool(s.Spool); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Vyplnenie u brokera (cas exekucie v ms UTC; `entry` = vstup, inak vystup s menom `exitName`).</summary>
    public static int SpoolFill(int handle, long execMs, string id, bool entry, string exitName, double price, double qty, bool ready)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null) return 0;
            s.Spool.Fill(execMs, id, entry, exitName, price, qty, ready);
            if (s.Spool.Broken) { FailSpool(s.Spool); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Adapter posunul SL/TP pracujuceho orderu (trailing...): riadok `order` s `a:"modify"`.
    /// MQL nema nullable, preto `sl`/`tp` &lt;= 0 znamena "nemenene" a ide ako null.</summary>
    public static int SpoolModify(int handle, long barMs, string id, double sl, double tp, string reason, bool ready)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null) return 0;
            s.Spool.Modify(barMs, id, sl > 0 ? sl : (double?)null, tp > 0 ? tp : (double?)null, reason, ready);
            if (s.Spool.Broken) { FailSpool(s.Spool); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Poznamka adaptera (`info` / `warn` / `error`).</summary>
    public static int SpoolNote(int handle, string level, string text)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null) return 0;
            s.Spool.Note(level, text);
            if (s.Spool.Broken) { FailSpool(s.Spool); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Id instancie (nazov adresara spoolu) - hostitel podla neho najde svoj control subor.</summary>
    public static string SpoolInstance(int handle)
    {
        try { Slot s = Get(handle); return s.Spool != null ? s.Spool.Instance : ""; }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>To iste bez spoolu (Strategy Tester, telemetria vypnuta): id z tych istych poli.</summary>
    public static string InstanceId(string platform, string account, string symbol, int tfMinutes, string strategy)
    {
        return InstanceIdSlot(platform, account, symbol, tfMinutes, strategy, "");
    }

    /// <summary>`InstanceId` so slotom nasadenia (prazdny = bez neho).</summary>
    public static string InstanceIdSlot(string platform, string account, string symbol, int tfMinutes, string strategy, string slot)
    {
        try { return LiveSpool.InstanceId(platform, account, symbol, tfMinutes, strategy, slot ?? ""); }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>Potvrdenie rezimu z control suboru (`enabled`/`paused`/`flatten`), profil a zdroj.</summary>
    public static int SpoolControl(int handle, string mode, string profile, string source)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null) return 0;
            s.Spool.Control(mode, profile, source);
            if (s.Spool.Broken) { FailSpool(s.Spool); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Ping `hb` hned (spool ho inak pise sam casovacom kazdu minutu; toto je pre `OnTimer`
    /// a testy). Nepridava `seq`. 1 ok, 0 bez spoolu, -1 chyba. Nova metoda, verzia fasady sa nemeni.</summary>
    public static int SpoolHeartbeat(int handle)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null) return 0;
            s.Spool.Heartbeat();
            if (s.Spool.Broken) { FailSpool(s.Spool); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Pozicia u brokera do pingu `hb` (`LiveSpool.Broker`): podpisane loty, priemerna cena, `scope` (`magic`).
    /// Pise len zmenu. 1 ok, 0 bez spoolu, -1 chyba. Nova metoda, verzia fasady sa nemeni.</summary>
    public static int SpoolBroker(int handle, double qty, double avgPrice, string scope)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null) return 0;
            s.Spool.Broker(qty, avgPrice, scope);
            if (s.Spool.Broken) { FailSpool(s.Spool); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Napise `stat` (Engine.Stats()) a `bye` a subor zavrie. 1 ok, 0 bez spoolu, -1 chyba.</summary>
    public static int SpoolClose(int handle, string reason)
    {
        try
        {
            Slot s = Get(handle);
            if (s.Spool == null) return 0;
            LiveSpool sp = s.Spool;
            s.Spool = null;
            sp.Stats(s.Host.Engine.Stats());
            sp.Close(reason);
            if (sp.Broken) { FailSpool(sp); return -1; }
            return 1;
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Cesta aktualneho suboru spoolu; "" bez spoolu alebo pri chybe.</summary>
    public static string SpoolPath(int handle)
    {
        try
        {
            Slot s = Get(handle);
            return s.Spool != null ? s.Spool.Path : "";
        }
        catch (Exception e) { Fail(e); return ""; }
    }

    // -- smerovanie prikazov: MT5 exekutor (docs/ROUTING.md) -------------------------------------- //
    // Exekutor nema engine - ma vlastnu tabulku handle. Prikazy idu von ako JSON pole (MQL5 ich cita
    // `TradeBotJson.mqh`), udalosti dnu typovanymi parametrami (MQL nema nullable: 0 / "" = pole sa nepise).

    private static readonly Dictionary<int, BridgeExecutor> Execs = new Dictionary<int, BridgeExecutor>();

    private static BridgeExecutor Exec(int handle)
    {
        lock (Lock)
        {
            BridgeExecutor x;
            if (!Execs.TryGetValue(handle, out x)) throw new ArgumentException("neznamy handle exekutora " + handle);
            return x;
        }
    }

    /// <summary>`mt5exec_&lt;login&gt;-&lt;server&gt;`.</summary>
    public static string BridgeExecutorId(long login, string server)
    {
        try { return Bridge.ExecutorId(login, server); }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>Otvori exekutor nad `root` (`Common\Files\TradeBot`); handle &gt; 0, alebo -1 - aj ked exekutor
    /// s tym istym id uz bezi (`BridgeExecutor.Lock`).</summary>
    public static int BridgeExecOpen(string root, string executorId)
    {
        try
        {
            BridgeExecutor x = new BridgeExecutor(root, executorId);
            x.Lock();
            lock (Lock)
            {
                int h = _next++;
                Execs[h] = x;
                _lastError = "";
                return h;
            }
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    public static void BridgeExecClose(int handle)
    {
        BridgeExecutor x;
        lock (Lock)
        {
            if (!Execs.TryGetValue(handle, out x)) return;
            Execs.Remove(handle);
        }
        x.Unlock();
    }

    /// <summary>Route urcene tomuto exekutorovi ako JSON pole objektov `route.json` s doplnenym `id` (adresar route);
    /// "" pri chybe (prazdny zoznam je "[]").</summary>
    public static string BridgeRoutes(int handle)
    {
        try
        {
            JsonWriter w = new JsonWriter();
            w.BeginArray();
            foreach (KeyValuePair<string, RouteSpec> kv in Exec(handle).Routes())
            {
                RouteSpec r = kv.Value;
                w.BeginObject().Key("id").Value(kv.Key).Key("symbol").Value(r.Symbol).Key("price").Value(r.Price);
                w.Key("scale").Value(r.Scale).Key("qty_mode").Value(r.QtyMode).Key("lots").Value(r.Lots);
                w.Key("magic").Value(r.Magic).Key("instance").Value(r.Instance).Key("deployment").Value(r.Deployment);
                w.Key("nt_symbol").Value(r.NtSymbol).Key("nt_point_value").Value(r.NtPointValue).Key("nt_tick").Value(r.NtTick);
                w.Key("nt_currency").Value(r.NtCurrency ?? "");
                w.Key("tf").Value(r.Tf).EndObject();
            }
            w.EndArray();
            return w.ToString();
        }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>Nove, este nevykonane prikazy route ako JSON pole; "" pri chybe.</summary>
    public static string BridgePoll(int handle, string routeId)
    {
        try { return "[" + string.Join(",", Exec(handle).Poll(routeId).ToArray()) + "]"; }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>Prikaz `cid` je vybaveny (vykonany aj odmietnuty) - po restarte sa nezopakuje. 1 ok, -1 chyba.</summary>
    public static int BridgeDone(int handle, string routeId, string cid)
    {
        try { Exec(handle).Done(routeId, cid); return 1; }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Udalost exekutora do `evt.jsonl`: `kind` ack/reject/placed/fill/modified/cancelled/closed/pos/order/
    /// snapshot/note; `side` in/out pri fille a smer pri `pos`; ceny a objemy 0 = nepisat. Vrati `seq` alebo -1.</summary>
    public static long BridgeEmit(int handle, string routeId, long nowMs, string kind, string cid, string id, string side,
                                  double price, double priceNt, double qty, double lots, long execMs, string exitName,
                                  string text)
    {
        try
        {
            return Exec(handle).Emit(routeId, nowMs, delegate(JsonWriter w)
            {
                w.Key("k").Value(kind ?? "");
                if (!string.IsNullOrEmpty(cid)) w.Key("cid").Value(cid);
                if (!string.IsNullOrEmpty(id)) w.Key("id").Value(id);
                if (!string.IsNullOrEmpty(side)) w.Key("side").Value(side);
                if (price != 0) w.Key("price").Value(price);
                if (priceNt != 0) w.Key("price_nt").Value(priceNt);
                if (qty != 0) w.Key("qty").Value(qty);
                if (lots != 0) w.Key("lots").Value(lots);
                if (execMs != 0) w.Key("ft").Value(execMs);
                if (!string.IsNullOrEmpty(exitName)) w.Key("exit").Value(exitName);
                if (!string.IsNullOrEmpty(text)) w.Key("text").Value(text);
            });
        }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Odlozi `evt.jsonl` route, ked je velky a master ho cely potvrdil. 1 odlozeny, 0 nie, -1 chyba.</summary>
    public static int BridgeRotateEvents(int handle, string routeId)
    {
        try { return Exec(handle).RotateEvents(routeId, Bridge.RotateBytes) ? 1 : 0; }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Zmaze adresar route, ktorej master mlci dlhsie nez `keepMs` (exekutor na nej nesmie nic drzat).
    /// 1 zmazany, 0 nie, -1 chyba.</summary>
    public static int BridgePruneRoute(int handle, string routeId, long nowMs, long keepMs)
    {
        try { return Exec(handle).PruneRoute(routeId, nowMs, keepMs) ? 1 : 0; }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Vek heartbeatu mastera route v ms; -1 = nikdy neprisiel, -2 = chyba.</summary>
    public static long BridgeMasterAge(int handle, string routeId, long nowMs)
    {
        try { return Exec(handle).MasterAgeMs(routeId, nowMs); }
        catch (Exception e) { Fail(e); return -2; }
    }

    /// <summary>Session mastera z jeho heartbeatu; "" = ziadny (alebo chyba v `LastError`).</summary>
    public static string BridgeMasterSession(int handle, string routeId)
    {
        try { return Exec(handle).MasterSession(routeId); }
        catch (Exception e) { Fail(e); return ""; }
    }

    /// <summary>Heartbeat exekutora: `BridgeHbBegin`, `BridgeHbSymbol`*, `BridgeHbRoute`*, `BridgeHbWrite`. 1 ok, -1 chyba.</summary>
    public static int BridgeHbBegin(int handle, long nowMs, long login, string server, string marginMode, bool connected,
                                    bool tradeAllowed, string version)
    {
        try { Exec(handle).HeartbeatBegin(nowMs, login, server, marginMode, connected, tradeAllowed, version); return 1; }
        catch (Exception e) { Fail(e); return -1; }
    }

    public static int BridgeHbSymbol(int handle, string name, double tick, double tickValue, double volMin, double volStep,
                                     double volMax, int tradeMode, double bid, double ask)
    {
        try { Exec(handle).HeartbeatSymbol(name, tick, tickValue, volMin, volStep, volMax, tradeMode, bid, ask); return 1; }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Namiesto `BridgeHbSymbol`*: symboly z posledneho heartbeatu, ktory ich mal. 1 ok, -1 chyba.</summary>
    public static int BridgeHbSymbolsKeep(int handle)
    {
        try { Exec(handle).HeartbeatSymbolsKeep(); return 1; }
        catch (Exception e) { Fail(e); return -1; }
    }

    /// <summary>Cas UTC v ms (MQL `TimeGMT` ma len sekundy - `exp`, `life` a hb by boli orezane).</summary>
    public static long BridgeNowMs() { return Bridge.NowMs(); }

    /// <summary>Ako `BridgeHbRoute` aj s cistou poziciou route u brokera v kontraktoch mastera (`net`).</summary>
    public static int BridgeHbRouteNet(int handle, string routeId, string state, string detail, double netNt)
    {
        try { Exec(handle).HeartbeatRoute(routeId, state, detail, netNt); return 1; }
        catch (Exception e) { Fail(e); return -1; }
    }

    public static int BridgeHbRoute(int handle, string routeId, string state, string detail)
    {
        try { Exec(handle).HeartbeatRoute(routeId, state, detail); return 1; }
        catch (Exception e) { Fail(e); return -1; }
    }

    public static int BridgeHbWrite(int handle)
    {
        try { Exec(handle).HeartbeatWrite(); return 1; }
        catch (Exception e) { Fail(e); return -1; }
    }

    // ciste vypocty (RouteMath) - MQL ich nepise druhy raz

    public static double BridgeMapPrice(double price, double refNt, double refExec, double scale, double tick)
    {
        return RouteMath.MapPrice(price, refNt, refExec, scale, tick);
    }

    public static double BridgeToNtPrice(double execPrice, double refNt, double refExec, double scale)
    {
        return RouteMath.ToNtPrice(execPrice, refNt, refExec, scale);
    }

    public static double BridgeReanchor(double fill, double plannedEntry, double level, double scale, double tick)
    {
        return RouteMath.Reanchor(fill, plannedEntry, level, scale, tick);
    }

    public static double BridgeLots(double contracts, double ntPointValue, double scale, double tickValue, double tickSize,
                                    double volMin, double volStep, double volMax, string mode, double fixedLots)
    {
        return RouteMath.Lots(contracts, ntPointValue, scale, tickValue, tickSize, volMin, volStep, volMax, mode ?? "value", fixedLots);
    }

    /// <summary>"cancel" / "close" / "" podla `OrderLife` (odklad `RouteMath.LifeGraceMs`).</summary>
    public static string BridgeLifeAction(long cancelAtMs, long closeAtMs, long holdMs, bool filled, long fillMs, long nowMs)
    {
        return RouteMath.LifeAction(cancelAtMs, closeAtMs, holdMs, filled, fillMs, nowMs, RouteMath.LifeGraceMs);
    }

    /// <summary>Zalozny trailing exekutora (master prec): stop podla `TrailingPlan.StopPrice`, vzdialenosti v cenach exekutora.</summary>
    public static double BridgeTrailStop(int direction, double entry, double baseStop, double extreme, double activation, double offset)
    {
        TrailingPlan p = new TrailingPlan(activation, offset, 0, 0);
        return p.StopPrice(direction > 0 ? Direction.Long : Direction.Short, entry, baseStop, extreme);
    }
}
