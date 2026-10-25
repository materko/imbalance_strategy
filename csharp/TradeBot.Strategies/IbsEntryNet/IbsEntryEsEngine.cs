// `IbsEntryEsEngine` - IBS EZ ES: IBS Entry Zone na S&P 500 futures (ES / MES) s jadrom v C#. Logika je tá istá ako
// `ibsentrynet` (`IbsEntryEngine`); vlastné sú profily (prahy v násobkoch ATR) a filter trendu / volatility
// (`EntryLayers`, pole `trendFilter` / `volFilter`) - presne ako Python `ibsentryes`. Vlastný kľúč existuje, aby
// NinjaTrader / MT5 a webapp vedeli ES nasadenie oddeliť od NQ.
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.IbsEntryNet
{
    [TradeBotEngine("ibsentryesnet", "IBS EZ ES (C# jadro)")]
    public sealed class IbsEntryEsEngine : EngineLayer
    {
        public IbsEntryEsEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(new IbsEntryEngine(config, inst, chartTfMinutes))
        {
        }

        public override EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            return Inner.OnBar(bar, htf, ctx);
        }
    }
}
