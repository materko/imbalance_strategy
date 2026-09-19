// Minimalny JSON parser a zapisovac - jadro nesmie mat ziadnu zavislost (NinjaTrader bezi
// na .NET Framework 4.8, Freqtrade most cez pythonnet/mono/dotnet), takze ziadny NuGet.
//
// Jazyk je zamerne C# 5: jadro sa da prelozit aj `csc.exe` z .NET Frameworku, ktory je
// na kazdom Windows, a NinjaTrader ho prelozi tiez.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace TradeBot.Core
{
    public sealed class JsonException : Exception
    {
        public JsonException(string message) : base(message) { }
    }

    /// <summary>JSON -> Dictionary&lt;string, object&gt; / List&lt;object&gt; / string / double / bool / null.</summary>
    public static class Json
    {
        public static object Parse(string text)
        {
            if (text == null) throw new JsonException("prazdny JSON");
            int pos = 0;
            object value = ParseValue(text, ref pos);
            SkipWs(text, ref pos);
            if (pos != text.Length) throw new JsonException("text za koncom JSON na pozicii " + pos);
            return value;
        }

        public static Dictionary<string, object> ParseObject(string text)
        {
            Dictionary<string, object> d = Parse(text) as Dictionary<string, object>;
            if (d == null) throw new JsonException("ocakaval sa JSON objekt");
            return d;
        }

        private static void SkipWs(string s, ref int pos)
        {
            while (pos < s.Length && (s[pos] == ' ' || s[pos] == '\t' || s[pos] == '\n' || s[pos] == '\r')) pos++;
        }

        private static object ParseValue(string s, ref int pos)
        {
            SkipWs(s, ref pos);
            if (pos >= s.Length) throw new JsonException("neocakavany koniec JSON");
            char c = s[pos];
            if (c == '{') return ParseObj(s, ref pos);
            if (c == '[') return ParseArr(s, ref pos);
            if (c == '"') return ParseStr(s, ref pos);
            if (Match(s, ref pos, "true")) return true;
            if (Match(s, ref pos, "false")) return false;
            if (Match(s, ref pos, "null")) return null;
            if (Match(s, ref pos, "NaN")) return double.NaN;
            return ParseNum(s, ref pos);
        }

        private static bool Match(string s, ref int pos, string word)
        {
            if (string.CompareOrdinal(s, pos, word, 0, word.Length) != 0) return false;
            pos += word.Length;
            return true;
        }

        private static Dictionary<string, object> ParseObj(string s, ref int pos)
        {
            Dictionary<string, object> d = new Dictionary<string, object>();
            pos++;
            SkipWs(s, ref pos);
            if (pos < s.Length && s[pos] == '}') { pos++; return d; }
            while (true)
            {
                SkipWs(s, ref pos);
                if (pos >= s.Length || s[pos] != '"') throw new JsonException("ocakaval sa kluc na pozicii " + pos);
                string key = ParseStr(s, ref pos);
                SkipWs(s, ref pos);
                if (pos >= s.Length || s[pos] != ':') throw new JsonException("ocakavala sa ':' na pozicii " + pos);
                pos++;
                d[key] = ParseValue(s, ref pos);
                SkipWs(s, ref pos);
                if (pos >= s.Length) throw new JsonException("neukonceny objekt");
                if (s[pos] == ',') { pos++; continue; }
                if (s[pos] == '}') { pos++; return d; }
                throw new JsonException("ocakavala sa ',' alebo '}' na pozicii " + pos);
            }
        }

        private static List<object> ParseArr(string s, ref int pos)
        {
            List<object> list = new List<object>();
            pos++;
            SkipWs(s, ref pos);
            if (pos < s.Length && s[pos] == ']') { pos++; return list; }
            while (true)
            {
                list.Add(ParseValue(s, ref pos));
                SkipWs(s, ref pos);
                if (pos >= s.Length) throw new JsonException("neukoncene pole");
                if (s[pos] == ',') { pos++; continue; }
                if (s[pos] == ']') { pos++; return list; }
                throw new JsonException("ocakavala sa ',' alebo ']' na pozicii " + pos);
            }
        }

        private static string ParseStr(string s, ref int pos)
        {
            StringBuilder sb = new StringBuilder();
            pos++;
            while (true)
            {
                if (pos >= s.Length) throw new JsonException("neukonceny retazec");
                char c = s[pos++];
                if (c == '"') return sb.ToString();
                if (c != '\\') { sb.Append(c); continue; }
                if (pos >= s.Length) throw new JsonException("neukonceny escape");
                char e = s[pos++];
                switch (e)
                {
                    case 'n': sb.Append('\n'); break;
                    case 't': sb.Append('\t'); break;
                    case 'r': sb.Append('\r'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'u':
                        if (pos + 4 > s.Length) throw new JsonException("neuplny \\u escape");
                        sb.Append((char)int.Parse(s.Substring(pos, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture));
                        pos += 4;
                        break;
                    default: sb.Append(e); break;
                }
            }
        }

        private static object ParseNum(string s, ref int pos)
        {
            int start = pos;
            while (pos < s.Length)
            {
                char c = s[pos];
                if ((c >= '0' && c <= '9') || c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E') pos++;
                else break;
            }
            if (start == pos) throw new JsonException("neocakavany znak '" + s[start] + "' na pozicii " + start);
            return double.Parse(s.Substring(start, pos - start), NumberStyles.Float, CultureInfo.InvariantCulture);
        }

        // -- citanie hodnot ------------------------------------------------- //

        public static double ToDouble(object v)
        {
            if (v is double) return (double)v;
            if (v is bool) throw new JsonException("ocakavalo sa cislo, nie bool");
            return Convert.ToDouble(v, CultureInfo.InvariantCulture);
        }

        public static long ToLong(object v) { return (long)Math.Round(ToDouble(v)); }

        public static int ToInt(object v) { return (int)Math.Round(ToDouble(v)); }

        public static object Get(Dictionary<string, object> d, string key)
        {
            object v;
            return d.TryGetValue(key, out v) ? v : null;
        }

        public static string GetString(Dictionary<string, object> d, string key, string dflt)
        {
            object v = Get(d, key);
            return v == null ? dflt : Convert.ToString(v, CultureInfo.InvariantCulture);
        }

        public static double GetDouble(Dictionary<string, object> d, string key, double dflt)
        {
            object v = Get(d, key);
            return v == null ? dflt : ToDouble(v);
        }

        public static bool GetBool(Dictionary<string, object> d, string key, bool dflt)
        {
            object v = Get(d, key);
            return v == null ? dflt : (bool)v;
        }
    }

    /// <summary>Zapisovac JSON. Cisla idu ako G17 - presne sa vratia do toho isteho double.</summary>
    public sealed class JsonWriter
    {
        private readonly StringBuilder _sb = new StringBuilder(256);
        private bool _needComma;

        public override string ToString() { return _sb.ToString(); }

        private void Sep()
        {
            if (_needComma) _sb.Append(',');
            _needComma = true;
        }

        public JsonWriter BeginObject() { Sep(); _sb.Append('{'); _needComma = false; return this; }
        public JsonWriter EndObject() { _sb.Append('}'); _needComma = true; return this; }
        public JsonWriter BeginArray() { Sep(); _sb.Append('['); _needComma = false; return this; }
        public JsonWriter EndArray() { _sb.Append(']'); _needComma = true; return this; }

        public JsonWriter Key(string name)
        {
            Sep();
            WriteString(name);
            _sb.Append(':');
            _needComma = false;
            return this;
        }

        public JsonWriter Value(string v)
        {
            Sep();
            if (v == null) _sb.Append("null"); else WriteString(v);
            return this;
        }

        public JsonWriter Value(bool v) { Sep(); _sb.Append(v ? "true" : "false"); return this; }
        public JsonWriter Value(long v) { Sep(); _sb.Append(v.ToString(CultureInfo.InvariantCulture)); return this; }
        public JsonWriter Value(int v) { Sep(); _sb.Append(v.ToString(CultureInfo.InvariantCulture)); return this; }

        public JsonWriter Value(double v)
        {
            Sep();
            if (double.IsNaN(v) || double.IsInfinity(v)) { _sb.Append("null"); return this; }
            string s = v.ToString("G17", CultureInfo.InvariantCulture);
            _sb.Append(s);
            // cele cislo by druha strana precitala ako int - double ostava double
            if (s.IndexOf('.') < 0 && s.IndexOf('E') < 0) _sb.Append(".0");
            return this;
        }

        public JsonWriter Null() { Sep(); _sb.Append("null"); return this; }

        public JsonWriter Value(double? v) { return v.HasValue ? Value(v.Value) : Null(); }
        public JsonWriter Value(long? v) { return v.HasValue ? Value(v.Value) : Null(); }
        public JsonWriter Value(int? v) { return v.HasValue ? Value(v.Value) : Null(); }

        /// <summary>Hodnota, ktoru stratégia da do `DrawUpdate` - cislo, retazec, bool alebo null.</summary>
        public JsonWriter ValueObject(object v)
        {
            if (v == null) return Null();
            if (v is string) return Value((string)v);
            if (v is bool) return Value((bool)v);
            if (v is int) return Value((int)v);
            if (v is long) return Value((long)v);
            if (v is double) return Value((double)v);
            return Value(Convert.ToString(v, CultureInfo.InvariantCulture));
        }

        private void WriteString(string s)
        {
            _sb.Append('"');
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                switch (c)
                {
                    case '"': _sb.Append("\\\""); break;
                    case '\\': _sb.Append("\\\\"); break;
                    case '\n': _sb.Append("\\n"); break;
                    case '\r': _sb.Append("\\r"); break;
                    case '\t': _sb.Append("\\t"); break;
                    default:
                        if (c < 0x20 || c > 0x7e) _sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                        else _sb.Append(c);
                        break;
                }
            }
            _sb.Append('"');
        }
    }
}
