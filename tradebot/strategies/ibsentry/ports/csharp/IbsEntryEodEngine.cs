// `IbsEntryEodEngine` - IBS Entry Zone s koncom obchodneho dna pre prop ucty: ta ista strategia ako `ibsentrynet`
// (`IbsEntryEngine`), len o 15:59 New York (21:59 nasho casu) zavrie vsetko a do 18:00 NY nevstupi (`EodCloseEngine`).
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.IbsEntryNet
{
    [TradeBotEngine("ibsentryneteod", "IBS Entry Zone (C# jadro EOD)")]
    public sealed class IbsEntryEodEngine : EodCloseEngine
    {
        public IbsEntryEodEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(new IbsEntryEngine(config, inst, chartTfMinutes), config, chartTfMinutes)
        {
        }
    }
}
