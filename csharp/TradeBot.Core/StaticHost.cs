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
using System;
using System.Collections.Generic;
using TradeBot.Core;

public static class StaticHost
{
    private sealed class Slot
    {
        public EngineHost Host;
        public IHtfFeeder Htf;
    }

    private static readonly object Lock = new object();
    private static readonly Dictionary<int, Slot> Slots = new Dictionary<int, Slot>();
    private static int _next = 1;
    private static string _lastError = "";

    /// <summary>Posledna chyba (text vynimky) alebo prazdny retazec. Cita sa po -1 / "".</summary>
    public static string LastError() { lock (Lock) { return _lastError; } }

    private static void Fail(Exception e) { lock (Lock) { _lastError = e.GetType().Name + ": " + e.Message; } }

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
    public static int Version() { return 1; }

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
        lock (Lock) { Slots.Remove(handle); }
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
}
