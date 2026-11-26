// MTK EMAS na dalsich trhoch (26. 11. 2026, studia Mac mini): vlastne kluce C# nad tym istym `MtkEmasEngine`,
// aby NinjaTrader / MT5 a webapp videli kazdy trh zvlast (profily trhu v `tradebot/strategies/mtkemas<trh>net/configs`).
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.MtkEmasNet
{
    [TradeBotEngine("mtkemasmgcnet", "MTK EMAS 1.0 MGC (C# jadro)")]
    public sealed class MtkEmasMgcEngine : MtkEmasEngine
    {
        public MtkEmasMgcEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes) : base(config, inst, chartTfMinutes) { }
    }

    [TradeBotEngine("mtkemasesnet", "MTK EMAS 1.0 ES (C# jadro)")]
    public sealed class MtkEmasEsEngine : MtkEmasEngine
    {
        public MtkEmasEsEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes) : base(config, inst, chartTfMinutes) { }
    }

    [TradeBotEngine("mtkemasmymnet", "MTK EMAS 1.0 MYM (C# jadro)")]
    public sealed class MtkEmasMymEngine : MtkEmasEngine
    {
        public MtkEmasMymEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes) : base(config, inst, chartTfMinutes) { }
    }

    [TradeBotEngine("mtkemasbtcnet", "MTK EMAS 1.0 BTC (C# jadro)")]
    public sealed class MtkEmasBtcEngine : MtkEmasEngine
    {
        public MtkEmasBtcEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes) : base(config, inst, chartTfMinutes) { }
    }
}
