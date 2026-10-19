// `VwapOrbEodEngine` - VWAP ORB 1.5 s koncom obchodneho dna pre prop ucty: ta ista strategia ako `vwaporbnet`
// (`VwapOrbEngine`), len o 15:59 New York (21:59 nasho casu) zavrie vsetko a do 18:00 NY nevstupi (`EodCloseEngine`).
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.VwapOrbNet
{
    [TradeBotEngine("vwaporbneteod", "VWAP ORB 1.5 (C# jadro EOD)")]
    public sealed class VwapOrbEodEngine : EodCloseEngine
    {
        public VwapOrbEodEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(new VwapOrbEngine(config, inst, chartTfMinutes), config, chartTfMinutes)
        {
        }
    }
}
