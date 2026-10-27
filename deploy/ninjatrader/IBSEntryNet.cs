// IBSEntryNet - IBS Entry Zone s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/csharp/TradeBot.Strategies/IbsEntryNet` nad
// `IbsNet`) a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „IBSEntryNet" na MINUTOVOM grafe.
// Druhu datovu seriu (detekcny TF zon, `zoneDetectionTF` z profilu) si strategia prida sama; zony z FVG
// (5m/15m/30m/1h) si sklada z barov grafu.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class IBSEntryNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "ibsentrynet"; } }

        // futures MNQ 3m
        protected override string DefaultProfile { get { return "multicharts_mnq_3m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "IBSEntryNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy ibsentrynet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
