// `TksEodEngine` - TKS 1.0 s koncom obchodneho dna pre prop ucty: ta ista strategia ako `tksnet`
// (`TksEngine`), len o 15:59 New York (21:59 nasho casu) zavrie vsetko a do 18:00 NY nevstupi (`EodCloseEngine`).
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.TksNet
{
    [TradeBotEngine("tksneteod", "TKS 1.0 (C# jadro EOD)")]
    public sealed class TksEodEngine : EodCloseEngine
    {
        public TksEodEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(new TksEngine(config, inst, chartTfMinutes), config, chartTfMinutes)
        {
        }
    }
}
