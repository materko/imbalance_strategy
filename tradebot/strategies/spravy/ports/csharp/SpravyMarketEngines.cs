// SPRÁVY na EUR/USD: ta ista strategia ako `spravynet` (`SpravyEngine`), len vlastny kluc kvoli profilom a nasadeniu
// (pouzivatel 21. 11. 2026). Kalendar je spolocny (aj ECB a ECB_TK s casom New York pre kazdy den).
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.SpravyNet
{
    /// <summary>SPRÁVY na EUR/USD (6E / EURUSD).</summary>
    [TradeBotEngine("spravyeurnet", "SPRÁVY EUR/USD (C# jadro)")]
    public sealed class SpravyEurEngine : SpravyEngine
    {
        public SpravyEurEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }
}
