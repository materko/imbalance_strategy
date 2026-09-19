// Kontrakt engine-u strategie - jedno volanie na uzavrety bar grafu (zrkadlo `tradebot/core/engine.py`).
// Adaptery (NinjaTrader, most do Freqtrade) pracuju len s tymto rozhranim a strategiu nepoznaju
// menom: engine sa hlada v registri podla kluca, ktory si strategia zapise atributom.
using System;
using System.Collections.Generic;
using System.Reflection;

namespace TradeBot.Core
{
    /// <summary>Co engine na danom bare zistil. Nic z toho sam nevykonava.</summary>
    public class EngineOutput
    {
        public List<OrderIntent> Orders = new List<OrderIntent>();
        public List<DrawCommand> Drawings = new List<DrawCommand>();
        public List<StateEvent> Events = new List<StateEvent>();
        /// <summary>Na tomto bare sa zatvorilo vsetko otvorene (koniec seansy a pod.).</summary>
        public bool CloseSession;
        /// <summary>Stav seans; null = strategia bez seans obchoduje vzdy.</summary>
        public ClockState Clock;
    }

    /// <summary>Okno informativneho (vyssieho) TF, ktore engine dostane na bare, kde sa uzavrela perioda.</summary>
    public sealed class HtfWindow
    {
        public const int RequiredBars = 4;
        /// <summary>dlzka 4: Pine [1], [2], [3], [4] - Bars[0] je posledny UZAVRETY bar</summary>
        public readonly Bar[] Bars;
        /// <summary>ta.sma(volume, volSmaLen)[1]</summary>
        public readonly double VolSma;

        public HtfWindow(Bar[] bars, double volSma)
        {
            if (bars == null || bars.Length != RequiredBars)
                throw new ArgumentException("HtfWindow potrebuje presne " + RequiredBars + " barov");
            Bars = bars; VolSma = volSma;
        }
    }

    /// <summary>Zdroj okna informativneho TF: adapter mu dava uzavrete bary toho TF po jednom.</summary>
    public interface IHtfFeeder
    {
        int TfMinutes { get; }
        void Feed(Bar closedHtfBar);
        HtfWindow WindowFor(long chartBarOpenMs);
    }

    /// <summary>Bar-by-bar engine. `OnBar` sa vola presne raz na kazdy uzavrety bar grafu. Engine je cisty:
    /// ziadne I/O, ziadny globalny stav.</summary>
    public interface IEngine
    {
        InstrumentSpec Inst { get; }
        int ChartTfMinutes { get; }
        /// <summary>Kolko barov grafu treba, kym su signaly platne.</summary>
        int RequiredHistory { get; }
        Warmup Warmup { get; }
        EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx);
        /// <summary>Objekty, ktore sa kreslia az na poslednom bare (Pine `barstate.islast`).</summary>
        List<DrawCommand> FinalDrawings(Bar bar);
        /// <summary>Feeder informativneho TF, alebo null ked ho strategia nema.</summary>
        IHtfFeeder CreateHtfFeeder();
        /// <summary>Volne pomenovane cisla pre adapter a logy (pocet zon, denny limit vyhier...).</summary>
        Dictionary<string, double> Stats();
    }

    /// <summary>Oznaci triedu engine-u klucom strategie. Trieda musi mat konstruktor
    /// `(Dictionary&lt;string, object&gt; config, InstrumentSpec inst, int chartTfMinutes)`.</summary>
    [AttributeUsage(AttributeTargets.Class, AllowMultiple = false)]
    public sealed class TradeBotEngineAttribute : Attribute
    {
        public readonly string Key;
        public readonly string Title;

        public TradeBotEngineAttribute(string key, string title) { Key = key; Title = title; }
    }

    /// <summary>Register engine-ov - hlada triedy s `[TradeBotEngine]` vo vsetkych nacitanych assembly,
    /// takze jadro ani adapter nepoznaju ziadnu strategiu menom.</summary>
    public static class EngineRegistry
    {
        private static Dictionary<string, Type> _types;
        private static readonly object Gate = new object();

        public static Dictionary<string, Type> Known()
        {
            lock (Gate)
            {
                if (_types != null) return _types;
                Dictionary<string, Type> found = new Dictionary<string, Type>();
                foreach (Assembly asm in AppDomain.CurrentDomain.GetAssemblies())
                {
                    Type[] types;
                    try { types = asm.GetTypes(); }
                    catch (ReflectionTypeLoadException e) { types = e.Types; }
                    catch (Exception) { continue; }
                    foreach (Type t in types)
                    {
                        if (t == null || !t.IsClass || t.IsAbstract || !typeof(IEngine).IsAssignableFrom(t)) continue;
                        object[] attrs = t.GetCustomAttributes(typeof(TradeBotEngineAttribute), false);
                        if (attrs.Length == 0) continue;
                        found[((TradeBotEngineAttribute)attrs[0]).Key] = t;
                    }
                }
                _types = found;
                return _types;
            }
        }

        /// <summary>Zabudne najdene triedy (NinjaTrader po rekompilacii nacita novu assembly).</summary>
        public static void Reset() { lock (Gate) { _types = null; } }

        public static IEngine Create(string key, Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
        {
            Type t;
            if (!Known().TryGetValue(key, out t))
            {
                List<string> keys = new List<string>(Known().Keys);
                keys.Sort();
                throw new ArgumentException("neznama C# strategia '" + key + "'; zname: " + string.Join(", ", keys.ToArray()));
            }
            try
            {
                return (IEngine)Activator.CreateInstance(t, new object[] { config, inst, chartTfMinutes });
            }
            catch (TargetInvocationException e)
            {
                throw e.InnerException ?? e;
            }
        }
    }
}
