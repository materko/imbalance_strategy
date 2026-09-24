// Aritmetika presne ako v Pythone - tam, kde sa vstavana funkcia Pythonu lisi od "samozrejmeho" C#.
// C# jadro sa s Python predlohou porovnava na rovnost, takze aj posledny bit musi sediet.
using System;
using System.Collections.Generic;

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
    }
}
