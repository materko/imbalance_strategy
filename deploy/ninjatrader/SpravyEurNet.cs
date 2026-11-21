// SpravyEurNet - SPRAVY (EUR/USD po spravach ECB a USA) s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/spravy/ports/csharp`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „SpravyEurNet" na MINUTOVOM grafe.
// Informativny TF strategia nema. Graf 5m, futures 6E. Cas sprav je v kalendari jadra (New York, prevod pre kazdy den).
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class SpravyEurNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "spravyeurnet"; } }

        // 6E 5m: pre kazdu spravu vlastne pravidlo (ECB, FOMC, CPI, PPI, JOLTS ...), vystup v case
        protected override string DefaultProfile { get { return "6e_databento_5m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "SpravyEurNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy spravyeurnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
