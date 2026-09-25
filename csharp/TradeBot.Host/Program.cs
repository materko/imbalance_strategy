// TradeBot.Host.exe - C# engine ako samostatny proces, riadeny riadkami JSON cez stdin/stdout.
// Pouzije ho most do Freqtrade tam, kde nie je pythonnet (macOS/Linux: `mono TradeBot.Host.exe`).
// Jeden riadok = jedna poziadavka, jeden riadok = odpoved; double ide dnu ako 16 hex znakov bitoveho
// vzoru (IEEE 754), aby sa cestou nezmenil ani posledny bit.
//
//   {"op":"create","key":"ibsnet","config":{...},"instrument":{...},"tf":3}
//   {"op":"bar","t":1756200000000,"b":["40f3...", o,h,l,c,v],"htf":{"t":[...4],"v":[...20],"sma":"..."},
//    "pos":"0000000000000000","dl":false,"ids":"LONG_3,SHORT_7"}
//   {"op":"seed","name":"Supertrend 10","t":[...],"v":[...],"partial":true}
//   {"op":"final","t":...,"b":[...]}   {"op":"info"}   {"op":"stats"}   {"op":"strategies"}
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using TradeBot.Core;

namespace TradeBot.Host
{
    public static class Program
    {
        private static double Bits(object hex)
        {
            return BitConverter.Int64BitsToDouble(long.Parse((string)hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture));
        }

        private static long[] Times(object raw)
        {
            List<object> list = raw as List<object>;
            if (list == null) return null;
            long[] t = new long[list.Count];
            for (int i = 0; i < t.Length; i++) t[i] = Json.ToLong(list[i]);
            return t;
        }

        private static double[] Values(object raw)
        {
            List<object> list = raw as List<object>;
            if (list == null) return null;
            double[] v = new double[list.Count];
            for (int i = 0; i < v.Length; i++) v[i] = Bits(list[i]);
            return v;
        }

        private static string Error(Exception e)
        {
            JsonWriter w = new JsonWriter();
            w.BeginObject().Key("error").Value(e.GetType().Name + ": " + e.Message).EndObject();
            return w.ToString();
        }

        public static int Main(string[] args)
        {
            // strategie mozu byt aj v dalsich DLL vedla hostitela
            foreach (string arg in args) Assembly.LoadFrom(arg);

            Stream stdin = Console.OpenStandardInput();
            Stream stdout = Console.OpenStandardOutput();
            StreamReader reader = new StreamReader(stdin, new UTF8Encoding(false));
            StreamWriter writer = new StreamWriter(stdout, new UTF8Encoding(false));
            writer.NewLine = "\n";

            EngineHost host = null;
            string line;
            while ((line = reader.ReadLine()) != null)
            {
                if (line.Length == 0) continue;
                string reply;
                try
                {
                    Dictionary<string, object> req = Json.ParseObject(line);
                    string op = Json.GetString(req, "op", "");
                    if (op == "quit") break;
                    reply = Handle(op, req, line, ref host);
                }
                catch (Exception e)
                {
                    reply = Error(e);
                }
                writer.WriteLine(reply);
                writer.Flush();
            }
            return 0;
        }

        private static string Handle(string op, Dictionary<string, object> req, string line, ref EngineHost host)
        {
            if (op == "strategies")
            {
                JsonWriter w = new JsonWriter();
                w.BeginObject().Key("strategies").Value(EngineHost.Strategies()).EndObject();
                return w.ToString();
            }
            if (op == "create")
            {
                // config a instrument sa posielaju ako vnorene JSON retazce - parser ich nemusi vediet vratit spat
                host = new EngineHost(Json.GetString(req, "key", ""), (string)req["config"], (string)req["instrument"],
                                      Json.ToInt(req["tf"]));
                return host.Info();
            }
            if (host == null) throw new InvalidOperationException("najprv 'create'");

            switch (op)
            {
                case "info": return host.Info();
                case "stats": return host.Stats();
                case "bar":
                {
                    double[] b = Values(req["b"]);
                    long[] htfT = null;
                    double[] htfV = null;
                    double sma = 0.0;
                    Dictionary<string, object> htf = Json.Get(req, "htf") as Dictionary<string, object>;
                    if (htf != null)
                    {
                        htfT = Times(htf["t"]);
                        htfV = Values(htf["v"]);
                        sma = Bits(htf["sma"]);
                    }
                    return host.OnBar(Json.ToLong(req["t"]), b[0], b[1], b[2], b[3], b[4], htfT, htfV, sma,
                                      Bits(req["pos"]), Json.GetBool(req, "dl", false), Json.GetString(req, "ids", ""));
                }
                case "final":
                {
                    double[] b = Values(req["b"]);
                    return host.FinalDrawings(Json.ToLong(req["t"]), b[0], b[1], b[2], b[3], b[4]);
                }
                case "seed":
                {
                    int n = host.Seed(Json.GetString(req, "name", ""), Times(req["t"]), Values(req["v"]),
                                      Json.GetBool(req, "partial", false));
                    JsonWriter w = new JsonWriter();
                    w.BeginObject().Key("closed").Value(n).EndObject();
                    return w.ToString();
                }
            }
            throw new ArgumentException("neznama operacia '" + op + "'");
        }
    }
}
