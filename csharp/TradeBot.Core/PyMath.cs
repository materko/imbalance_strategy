// Aritmetika presne ako v Pythone - tam, kde sa vstavana funkcia Pythonu lisi od "samozrejmeho" C#.
// C# jadro sa s Python predlohou porovnava na rovnost, takze aj posledny bit musi sediet.
using System;
using System.Collections.Generic;
using System.Globalization;

namespace TradeBot.Core
{
    public static class PyMath
    {
        /// <summary>Python `sum()` nad floatmi. Od Pythonu 3.12 to NIE JE obycajny cyklus zlava doprava,
        /// ale Neumaierova kompenzovana suma (CPython `builtin_sum_impl`) - vysledok sa od cyklu lisi
        /// v poslednych bitoch a porovnanie `>=` na hrane sa potom preklopi. Python engine, ktory
        /// pise `sum(...)`, sa preto v C# prepisuje cez toto; explicitny cyklus v Pythone cez cyklus.</summary>
        public static double Sum(IEnumerable<double> values)
        {
            double f = 0.0, c = 0.0;
            foreach (double x in values)
            {
                double t = f + x;
                if (Math.Abs(f) >= Math.Abs(x)) c += (f - t) + x;
                else c += (x - t) + f;
                f = t;
            }
            // CPython: kompenzaciu nepridavat, ked by nekonecny/preteceny sucet zmenila na NaN
            if (c != 0.0 && !double.IsInfinity(c) && !double.IsNaN(c)) f += c;
            return f;
        }

        /// <summary>Python `f"{x:g}"` - 6 platnych cifier, bez koncovych nul; exponent pri exp &lt; -4 alebo &gt;= 6.
        /// Zaokruhluje sa ako Python (na parne), cez decimal z G17, nie cez .NET format (Mono/.NET Framework
        /// zaokruhluju double inak).</summary>
        public static string FormatG(double x)
        {
            if (double.IsNaN(x)) return "nan";
            if (double.IsInfinity(x)) return x > 0 ? "inf" : "-inf";
            if (x == 0.0) return (1.0 / x) < 0 ? "-0" : "0";
            decimal d;
            if (!decimal.TryParse(x.ToString("G17", CultureInfo.InvariantCulture), NumberStyles.Float,
                                  CultureInfo.InvariantCulture, out d))
                return x.ToString("G6", CultureInfo.InvariantCulture);
            bool neg = d < 0;
            decimal a = Math.Abs(d);
            int e = 0;
            while (a >= Pow10(e + 1)) e++;
            while (a < Pow10(e)) e--;
            decimal r = RoundSig(a, e);
            if (r >= Pow10(e + 1)) { e++; r = RoundSig(a, e); }
            string text;
            if (e >= -4 && e < 6)
            {
                text = r.ToString("F" + Math.Max(0, 5 - e), CultureInfo.InvariantCulture);
                if (text.IndexOf('.') >= 0) text = text.TrimEnd('0').TrimEnd('.');
            }
            else
            {
                string m = (r / Pow10(e)).ToString("F5", CultureInfo.InvariantCulture);
                if (m.IndexOf('.') >= 0) m = m.TrimEnd('0').TrimEnd('.');
                text = m + "e" + (e < 0 ? "-" : "+") + Math.Abs(e).ToString("00", CultureInfo.InvariantCulture);
            }
            return neg ? "-" + text : text;
        }

        private static decimal Pow10(int e)
        {
            decimal p = 1m;
            if (e >= 0) for (int i = 0; i < e; i++) p *= 10m;
            else for (int i = 0; i < -e; i++) p /= 10m;
            return p;
        }

        /// <summary>`a` zaokruhlene na 6 platnych cifier (na parne), `e` = rad najvyssej cifry.</summary>
        private static decimal RoundSig(decimal a, int e)
        {
            int decimals = 5 - e;
            if (decimals >= 0) return Math.Round(a, Math.Min(decimals, 28), MidpointRounding.ToEven);
            decimal scale = Pow10(-decimals);
            return Math.Round(a / scale, 0, MidpointRounding.ToEven) * scale;
        }
    }
}
