// `IbsEntryMymEngine` - IBS EZ MYM: IBS Entry Zone na Micro Dow futures (MYM / YM) s jadrom v C#. Logika je tá istá ako
// `ibsentrynet` (`IbsEntryEngine`); vlastné sú profily (prahy v násobkoch ATR) a filter trendu / volatility
// (`EntryLayers`, pole `trendFilter` / `volFilter`) - presne ako Python `ibsentrymym`. Vlastný kľúč existuje, aby
// NinjaTrader / MT5 a webapp vedeli MYM nasadenie oddeliť od NQ a ES.
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.IbsEntryNet
{
    [TradeBotEngine("ibsentrymymnet", "IBS EZ MYM (C# jadro)")]
    public sealed class IbsEntryMymEngine : EngineLayer
    {
        public IbsEntryMymEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(new IbsEntryEngine(config, inst, chartTfMinutes))
        {
        }

        public override EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            return Inner.OnBar(bar, htf, ctx);
        }
    }
}
