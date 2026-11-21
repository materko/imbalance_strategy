// IB RETRACE 1.0 na MGC a MYM: ta ista strategia ako `ibretnet` (`IbRetEngine`), len vlastny kluc kvoli profilom a nasadeniu
// (pouzivatel 21. 11. 2026). Urovne su zlomky sirky IB, takze trhu sa prisposobia samy.
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.IbRetNet
{
    /// <summary>IB RETRACE na zlate (MGC / GC).</summary>
    [TradeBotEngine("ibretmgcnet", "IB RETRACE 1.0 MGC (C# jadro)")]
    public sealed class IbRetMgcEngine : IbRetEngine
    {
        public IbRetMgcEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }

    /// <summary>IB RETRACE na Micro Dow (MYM / YM).</summary>
    [TradeBotEngine("ibretmymnet", "IB RETRACE 1.0 MYM (C# jadro)")]
    public sealed class IbRetMymEngine : IbRetEngine
    {
        public IbRetMymEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }
}
