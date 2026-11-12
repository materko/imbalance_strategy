// NOA 1.0 na ES, MGC a MYM: ta ista strategia ako `noanet` (`NoaEngine`), len vlastny kluc kvoli profilom a nasadeniu
// (pouzivatel 11. 11. 2026, MYM 12. 11. 2026). Pasmo sumu aj poistka su v percentach z ceny, takze trhu sa prisposobia samy.
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.NoaNet
{
    /// <summary>NOA na S&amp;P 500 (ES / MES).</summary>
    [TradeBotEngine("noaesnet", "NOA 1.0 ES (C# jadro)")]
    public sealed class NoaEsEngine : NoaEngine
    {
        public NoaEsEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }

    /// <summary>NOA na zlate (MGC / GC).</summary>
    [TradeBotEngine("noamgcnet", "NOA 1.0 MGC (C# jadro)")]
    public sealed class NoaMgcEngine : NoaEngine
    {
        public NoaMgcEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }

    /// <summary>NOA na Micro Dow (MYM / YM).</summary>
    [TradeBotEngine("noamymnet", "NOA 1.0 MYM (C# jadro)")]
    public sealed class NoaMymEngine : NoaEngine
    {
        public NoaMymEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }
}
