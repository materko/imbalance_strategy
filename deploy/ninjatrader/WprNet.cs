// WprNet - WILLIAMS %R LONG 1.0 (C# jadro) ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/wpr/ports/csharp`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „WprNet" na MINUTOVOM grafe. Futures MNQ / NQ.
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class WprNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "wprnet"; } }

        protected override string DefaultProfile { get { return "PRESIEL_SMERNICAMI_WILLIAMS_R_MNQ_1"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "WprNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy wprnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
