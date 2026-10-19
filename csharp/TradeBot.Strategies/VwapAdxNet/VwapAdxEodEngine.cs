// `VwapAdxEodEngine` - VWAP ADX Pullback s koncom obchodneho dna pre prop ucty: ta ista strategia ako `vwapadxnet`
// (`VwapAdxEngine`), len o 15:59 New York (21:59 nasho casu) zavrie vsetko a do 18:00 NY nevstupi (`EodCloseEngine`).
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.VwapAdxNet
{
    [TradeBotEngine("vwapadxneteod", "VWAP ADX Pullback (C# jadro EOD)")]
    public sealed class VwapAdxEodEngine : EodCloseEngine
    {
        public VwapAdxEodEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(new VwapAdxEngine(config, inst, chartTfMinutes), config, chartTfMinutes)
        {
        }
    }
}
