// Vstup do nativneho backtestu pre hostitelov mimo .NET (pythonnet, neskor CLI a hyperopt):
// kluc strategie, config a instrument ako JSON (tie iste, co dostava most), 1m data zo suboru
// feather. Vysledok je JSON - obchody s presnymi cenami (G17), pocet barov, nerozhodnutelne minuty.
using System;
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Backtest
{
    public static class NativeBacktest
    {
        private static readonly object Gate = new object();
        private static readonly Dictionary<string, Candles> Cache = new Dictionary<string, Candles>();

        /// <summary>1m sviecky zo suboru - nacitane raz za proces (hyperopt bezi nad tymi istymi datami).</summary>
        public static Candles LoadM1(string path)
        {
            lock (Gate)
            {
                Candles c;
                if (!Cache.TryGetValue(path, out c))
                {
                    c = Feather.ReadCandles(path);
                    Cache[path] = c;
                }
                return c;
            }
        }

        public static void ClearCache() { lock (Gate) { Cache.Clear(); } }

        /// <summary>`fromMs`/`toMs` &lt; 0 = bez hranice (ako prazdna strana timerange).</summary>
        public static EmuResult Run(string key, string configJson, string instrumentJson, Candles m1, int chartTf,
                                    long fromMs, long toMs, double fee)
        {
            Dictionary<string, object> config = Json.ParseObject(configJson);
            InstrumentSpec inst = InstrumentSpec.FromJson(Json.ParseObject(instrumentJson));
            IEngine engine = EngineRegistry.Create(key, config, inst, chartTf);
            return McEmulator.Run(engine, config, m1, chartTf,
                                  fromMs < 0 ? long.MinValue : fromMs, toMs < 0 ? long.MaxValue : toMs, fee);
        }

        /// <summary>Dávka behov tej istej strategie nad tymi istymi datami - kazdy config na jednom vlakne
        /// (`threads` &lt;= 0 = vsetky jadra). Data sa pripravia raz, engine ma kazdy beh vlastny. Vrati JSON
        /// vysledku na kazdy config v tom istom poradi; beh, ktory spadne, vrati `{"error": "..."}`.</summary>
        public static string[] RunBatchJson(string key, string[] configJsons, string instrumentJson, string m1Path,
                                            int chartTf, long fromMs, long toMs, double fee, int threads)
        {
            EmuData data = EmuData.Prepare(LoadM1(m1Path), chartTf,
                                           fromMs < 0 ? long.MinValue : fromMs, toMs < 0 ? long.MaxValue : toMs);
            InstrumentSpec inst = InstrumentSpec.FromJson(Json.ParseObject(instrumentJson));
            string[] results = new string[configJsons.Length];
            int next = -1;
            int workers = threads > 0 ? threads : Environment.ProcessorCount;
            workers = Math.Max(1, Math.Min(workers, configJsons.Length));
            System.Threading.Thread[] pool = new System.Threading.Thread[workers];
            for (int w = 0; w < workers; w++)
            {
                pool[w] = new System.Threading.Thread(delegate ()
                {
                    while (true)
                    {
                        int i = System.Threading.Interlocked.Increment(ref next);
                        if (i >= configJsons.Length) return;
                        try
                        {
                            Dictionary<string, object> config = Json.ParseObject(configJsons[i]);
                            IEngine engine = EngineRegistry.Create(key, config, inst, chartTf);
                            results[i] = ToJson(McEmulator.Run(engine, config, data, fee));
                        }
                        catch (Exception e)
                        {
                            JsonWriter w2 = new JsonWriter();
                            w2.BeginObject().Key("error").Value(e.GetType().Name + ": " + e.Message).EndObject();
                            results[i] = w2.ToString();
                        }
                    }
                }, 64 * 1024 * 1024);
                pool[w].IsBackground = true;
                pool[w].Start();
            }
            foreach (System.Threading.Thread t in pool) t.Join();
            return results;
        }

        public static string RunFileJson(string key, string configJson, string instrumentJson, string m1Path, int chartTf,
                                         long fromMs, long toMs, double fee)
        {
            return ToJson(Run(key, configJson, instrumentJson, LoadM1(m1Path), chartTf, fromMs, toMs, fee));
        }

        public static string ToJson(EmuResult r)
        {
            JsonWriter w = new JsonWriter();
            w.BeginObject();
            w.Key("bars").Value(r.Bars).Key("ambiguous").Value(r.Ambiguous);
            w.Key("first_ms").Value(r.FirstMs).Key("last_ms").Value(r.LastMs);
            w.Key("first_close").Value(double.IsNaN(r.FirstClose) ? (double?)null : r.FirstClose);
            w.Key("last_close").Value(double.IsNaN(r.LastClose) ? (double?)null : r.LastClose);
            w.Key("log").Value(r.Log);
            w.Key("trades").BeginArray();
            foreach (EmuTrade t in r.Trades)
            {
                w.BeginObject();
                w.Key("order_id").Value(t.OrderId).Key("dir").Value((int)t.Direction).Key("qty").Value(t.Qty);
                w.Key("entry").Value(t.Entry).Key("open_ms").Value(t.OpenMs);
                w.Key("stop_initial").Value(t.StopInitial).Key("take_profit").Value(t.TakeProfit);
                w.Key("market").Value(t.Market).Key("stop_last").Value(t.StopLast);
                w.Key("exit").Value(t.Exit).Key("close_ms").Value(t.CloseMs).Key("reason").Value(t.Reason);
                w.Key("max_price").Value(t.MaxPrice).Key("min_price").Value(t.MinPrice);
                w.EndObject();
            }
            w.EndArray();
            w.EndObject();
            return w.ToString();
        }
    }
}
