// TKS 1.0 na ES, MGC, MYM, BTC a 6E: ta ista strategia ako `tksnet` (`TksEngine`), len vlastny kluc kvoli profilom
// a nasadeniu (pouzivatel 17. 11. 2026). NQ Kompas je pomerovy a skala tlaku vychadza na tychto trhoch ako na MNQ,
// takze sa kod nemeni.
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.TksNet
{
    /// <summary>TKS na S&amp;P 500 (ES / MES).</summary>
    [TradeBotEngine("tksesnet", "TKS 1.0 ES (C# jadro)")]
    public sealed class TksEsEngine : TksEngine
    {
        public TksEsEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }

    /// <summary>TKS na zlate (MGC / GC).</summary>
    [TradeBotEngine("tksmgcnet", "TKS 1.0 MGC (C# jadro)")]
    public sealed class TksMgcEngine : TksEngine
    {
        public TksMgcEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }

    /// <summary>TKS na Micro Dow (MYM / YM).</summary>
    [TradeBotEngine("tksmymnet", "TKS 1.0 MYM (C# jadro)")]
    public sealed class TksMymEngine : TksEngine
    {
        public TksMymEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }

    /// <summary>TKS na BTCUSDT.P (Binance futures).</summary>
    [TradeBotEngine("tksbtcnet", "TKS 1.0 BTC (C# jadro)")]
    public sealed class TksBtcEngine : TksEngine
    {
        public TksBtcEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }

    /// <summary>TKS na Euro FX (6E / M6E).</summary>
    [TradeBotEngine("tkseurnet", "TKS 1.0 6E (C# jadro)")]
    public sealed class TksEurEngine : TksEngine
    {
        public TksEurEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : base(config, inst, chartTfMinutes)
        {
        }
    }
}
