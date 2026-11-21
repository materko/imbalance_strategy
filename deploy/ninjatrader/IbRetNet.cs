// IbRetNet - IB RETRACE 1.0 (prieraz Initial Balance, vstup na navrate do IB) s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/ibret/ports/csharp`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „IbRetNet" na MINUTOVOM grafe.
// Informativny TF strategia nema; IB (9:30-10:30 NY) si sklada z barov grafu.
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class IbRetNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "ibretnet"; } }

        // MNQ futures 5m: IB 9:30-10:30 NY, po prieraze limitka na navrate do IB, stop za urovnou max retracementu
        protected override string DefaultProfile { get { return "mnq_databento_5m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "IbRetNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy ibretnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
