// IBSEntryNetEod - IBS Entry Zone s jadrom v C# ako strategia NinjaTrader 8.
// EOD: o 15:59 New York (21:59 nasho casu) zavrie vsetko a do 18:00 NY nevstupi - pre prop ucty (`EodCloseEngine`).
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/ibsentry/csharp` nad
// `IbsNet`) a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „IBSEntryNetEod" na MINUTOVOM grafe.
// Druhu datovu seriu (detekcny TF zon, `zoneDetectionTF` z profilu) si strategia prida sama; zony z FVG
// (5m/15m/30m/1h) si sklada z barov grafu.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class IBSEntryNetEod : TradeBotStrategy
    {
        protected override string EngineKey { get { return "ibsentryneteod"; } }

        // futures MNQ 3m
        protected override string DefaultProfile { get { return "multicharts_mnq_3m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "IBSEntryNetEod";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy ibsentryneteod`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
