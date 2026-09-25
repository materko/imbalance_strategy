// IBSNet - IBS Imbalance Breakout s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`csharp/TradeBot.Strategies/IbsNet`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „IBSNet" na MINUTOVOM grafe.
// Druhu datovu seriu (detekcny TF zon, `zoneDetectionTF` z profilu) si strategia prida sama.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class IBSNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "ibsnet"; } }

        // futures MNQ, 1:1 s nastaveniami z TradingView
        protected override string DefaultProfile { get { return "multicharts_mnq_3m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "IBSNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare`). Pred optimalizaciou vypni - kazda iteracia = subor.
                ExportSignals = true;
            }
        }
    }
}
