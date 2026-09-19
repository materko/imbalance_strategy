// Fasada engine-u pre hostitela, ktory nie je .NET (most do Freqtrade): vstupy su jednoduche typy,
// vystup je jeden JSON retazec na bar. Pouziva ju pythonnet (v procese) aj TradeBot.Host.exe (stdio).
//
// Cisla idu DNU ako nativne double (pythonnet) alebo bitovy vzor (stdio) a VON ako G17, takze sa
// cestou nezmeni ani posledny bit - inak by sa porovnanie s Python enginom nedalo robit na rovnost.
using System;
using System.Collections.Generic;

namespace TradeBot.Core
{
    public sealed class EngineHost
    {
        public readonly IEngine Engine;
        public readonly string Key;

        public EngineHost(string key, string configJson, string instrumentJson, int chartTfMinutes)
        {
            Key = key;
            Engine = EngineRegistry.Create(key, Json.ParseObject(configJson),
                                           InstrumentSpec.FromJson(Json.ParseObject(instrumentJson)), chartTfMinutes);
        }

        /// <summary>Zoznam klucov C# strategii v nacitanych assembly.</summary>
        public static string Strategies()
        {
            List<string> keys = new List<string>(EngineRegistry.Known().Keys);
            keys.Sort();
            return string.Join(",", keys.ToArray());
        }

        public string Info()
        {
            JsonWriter w = new JsonWriter();
            w.BeginObject();
            w.Key("key").Value(Key);
            w.Key("required_history").Value(Engine.RequiredHistory);
            w.Key("describe").Value(Engine.Warmup != null ? Engine.Warmup.Describe() : "");
            w.Key("warmup").BeginArray();
            if (Engine.Warmup != null)
            {
                foreach (WarmupNeed n in Engine.Warmup.Needs)
                {
                    w.BeginObject();
                    w.Key("name").Value(n.Name).Key("bars").Value(n.Bars).Key("tf").Value(n.TfMinutes).Key("seeded").Value(n.Seeded);
                    w.EndObject();
                }
            }
            w.EndArray();
            w.EndObject();
            return w.ToString();
        }

        private static Bar[] Bars(long[] times, double[] values)
        {
            if (times == null) return new Bar[0];
            if (values == null || values.Length != times.Length * 5)
                throw new ArgumentException("bary: ocakava sa 5 hodnot (o,h,l,c,v) na kazdy cas");
            Bar[] bars = new Bar[times.Length];
            for (int i = 0; i < times.Length; i++)
            {
                int k = i * 5;
                bars[i] = new Bar(times[i], values[k], values[k + 1], values[k + 2], values[k + 3], values[k + 4]);
            }
            return bars;
        }

        /// <summary>Seeding indikatora s vlastnou predhistoriou; posledny bar je rozpracovana perioda,
        /// ked `hasPartial`. Vrati pocet uzavretych barov.</summary>
        public int Seed(string name, long[] times, double[] values, bool hasPartial)
        {
            WarmupNeed need = Engine.Warmup != null ? Engine.Warmup.FindSeed(name) : null;
            if (need == null) throw new ArgumentException("engine nema seeded indikator '" + name + "'");
            Bar[] all = Bars(times, values);
            int closedCount = hasPartial ? all.Length - 1 : all.Length;
            List<Bar> closed = new List<Bar>(Math.Max(0, closedCount));
            for (int i = 0; i < closedCount; i++) closed.Add(all[i]);
            need.Seed(closed, hasPartial && all.Length > 0 ? all[all.Length - 1] : null);
            return closed.Count;
        }

        /// <summary>Jeden uzavrety bar grafu. `htfTimes`/`htfValues` su okno informativneho TF (4 bary,
        /// najnovsi prvy) alebo null; `openOrderIds` su id vyplnenych orderov oddelene ciarkou.</summary>
        public string OnBar(long time, double open, double high, double low, double close, double volume,
                            long[] htfTimes, double[] htfValues, double htfVolSma,
                            double positionSize, bool dailyWinLimitReached, string openOrderIds)
        {
            HtfWindow htf = null;
            if (htfTimes != null && htfTimes.Length > 0) htf = new HtfWindow(Bars(htfTimes, htfValues), htfVolSma);

            MarketContext ctx = new MarketContext();
            ctx.PositionSize = positionSize;
            ctx.DailyWinLimitReached = dailyWinLimitReached;
            if (!string.IsNullOrEmpty(openOrderIds))
                // `Split(char[])`, nie `Split(',')`: Mono ma navyse pretazenie `Split(char, StringSplitOptions)`,
                // na ktore by `mcs` volanie naviazal - a taka DLL potom na .NET Frameworku nenabehne
                foreach (string id in openOrderIds.Split(new char[] { ',' })) if (id.Length > 0) ctx.OpenOrderIds.Add(id);

            EngineOutput o = Engine.OnBar(new Bar(time, open, high, low, close, volume), htf, ctx);

            JsonWriter w = new JsonWriter();
            w.BeginObject();
            if (o.Orders.Count > 0)
            {
                w.Key("o").BeginArray();
                foreach (OrderIntent i in o.Orders) i.WriteJson(w);
                w.EndArray();
            }
            if (o.Drawings.Count > 0)
            {
                w.Key("d").BeginArray();
                foreach (DrawCommand d in o.Drawings) d.WriteJson(w);
                w.EndArray();
            }
            if (o.Events.Count > 0)
            {
                w.Key("e").BeginArray();
                foreach (StateEvent e in o.Events) e.WriteJson(w);
                w.EndArray();
            }
            if (o.CloseSession) w.Key("cs").Value(true);
            if (o.Clock != null) { w.Key("clk"); o.Clock.WriteJson(w); }
            w.Key("mb").Value(ctx.MarketBias);
            w.EndObject();
            return w.ToString();
        }

        public string FinalDrawings(long time, double open, double high, double low, double close, double volume)
        {
            JsonWriter w = new JsonWriter();
            w.BeginArray();
            foreach (DrawCommand d in Engine.FinalDrawings(new Bar(time, open, high, low, close, volume))) d.WriteJson(w);
            w.EndArray();
            return w.ToString();
        }

        public string Stats()
        {
            JsonWriter w = new JsonWriter();
            w.BeginObject();
            Dictionary<string, double> stats = Engine.Stats();
            if (stats != null)
                foreach (KeyValuePair<string, double> kv in stats) w.Key(kv.Key).Value(kv.Value);
            w.EndObject();
            return w.ToString();
        }
    }
}
