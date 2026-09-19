// Predhistoria (warmup) - zrkadlo `tradebot/core/warmup.py`.
// `Warmup.Add` = bary grafu pred prvym signalom, `AddSeeded` = indikator na vlastnom vyssom TF,
// ktory svoje bary dostane pred prvym barom grafu (adapter ich poskladá a zavola `Seed`).
using System;
using System.Collections.Generic;
using System.Globalization;

namespace TradeBot.Core
{
    public static class WarmupMath
    {
        /// <summary>Vaha startovacej hodnoty rekurzivneho priemeru, pod ktoru musi klesnut (5 %).</summary>
        public const double SeedWeight = 0.05;
        public const int SeedSlackDays = 4;

        public static int DecayBars(double alpha)
        {
            if (alpha >= 1.0) return 0;
            if (alpha <= 0.0) throw new ArgumentException("alpha musi byt kladna");
            return (int)Math.Ceiling(Math.Log(SeedWeight) / Math.Log(1.0 - alpha));
        }

        public static int SmaBars(int length) { return Math.Max(1, length); }

        public static int RmaBars(int length)
        {
            int n = Math.Max(1, length);
            return n + DecayBars(1.0 / n);
        }

        public static int EmaBars(int length)
        {
            int n = Math.Max(1, length);
            return n + DecayBars(2.0 / (n + 1));
        }

        public static int OnChart(int bars, int tfMinutes, int chartTfMinutes)
        {
            bars = Math.Max(0, bars);
            int chart = Math.Max(1, chartTfMinutes);
            int tf = Math.Max(chart, tfMinutes);
            if (tf == chart) return bars;
            return (bars + 1) * (int)Math.Ceiling((double)tf / chart);
        }
    }

    /// <summary>`seed(uzavrete bary TF indikatora, rozpracovany bar alebo null)` - raz, pred prvym barom.</summary>
    public delegate void SeedFn(IList<Bar> closed, Bar partial);

    public sealed class WarmupNeed
    {
        public readonly string Name;
        public readonly int Bars;
        public readonly int TfMinutes;
        public readonly SeedFn Seed;

        public WarmupNeed(string name, int bars, int tfMinutes, SeedFn seed)
        {
            Name = name; Bars = bars; TfMinutes = tfMinutes; Seed = seed;
        }

        public bool Seeded { get { return Seed != null; } }

        public int ChartBars(int chartTfMinutes) { return WarmupMath.OnChart(Bars, TfMinutes, chartTfMinutes); }
    }

    public sealed class Warmup
    {
        public readonly int ChartTfMinutes;
        public readonly List<WarmupNeed> Needs = new List<WarmupNeed>();

        public Warmup(int chartTfMinutes) { ChartTfMinutes = chartTfMinutes; }

        public Warmup Add(string name, int bars)
        {
            Needs.Add(new WarmupNeed(name, bars, ChartTfMinutes, null));
            return this;
        }

        public Warmup AddSeeded(string name, int bars, int tfMinutes, SeedFn seed)
        {
            Needs.Add(new WarmupNeed(name, bars, tfMinutes, seed));
            return this;
        }

        /// <summary>`required_history` - kolko barov GRAFU treba, kym su signaly platne.</summary>
        public int ChartBars
        {
            get
            {
                int best = 0;
                bool any = false;
                foreach (WarmupNeed n in Needs)
                {
                    if (n.Seeded) continue;
                    any = true;
                    best = Math.Max(best, n.ChartBars(ChartTfMinutes));
                }
                return any && best > 0 ? best : 1;
            }
        }

        public WarmupNeed FindSeed(string name)
        {
            foreach (WarmupNeed n in Needs)
                if (n.Seeded && n.Name == name) return n;
            return null;
        }

        public string Describe()
        {
            List<string> parts = new List<string>();
            foreach (WarmupNeed n in Needs)
            {
                if (n.Seeded) parts.Add(string.Format(CultureInfo.InvariantCulture, "{0} @{1}m: {2} vlastnych", n.Name, n.TfMinutes, n.Bars));
                else parts.Add(string.Format(CultureInfo.InvariantCulture, "{0}: {1}", n.Name, n.Bars));
            }
            return string.Join("; ", parts.ToArray());
        }
    }
}
