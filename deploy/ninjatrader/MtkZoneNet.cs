// MtkZoneNet - MTK ZONE s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/mtkzone/ports/csharp`, vyssie TF
// z IbsEntryNet) a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „MtkZoneNet" na 3m (2m) grafe.
// Informativny TF strategia nema; zony 5m / 15m si sklada z barov grafu (treba skutocny objem burzy - CME futures).
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MtkZoneNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "mtkzonenet"; } }

        // MNQ futures 3m: SD zony z 5m (min. 2 potvrdenia), limit na zonu, RR 1
        protected override string DefaultProfile { get { return "mnq_databento_3m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "MtkZoneNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy mtkzonenet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
