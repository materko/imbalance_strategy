// NoaEsNet - NOA 1.0 ES (C# jadro) ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/noa/ports/csharp`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „NoaEsNet" na MINUTOVOM grafe. Futures ES / MES.
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class NoaEsNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "noaesnet"; } }

        protected override string DefaultProfile { get { return "es_databento_5m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "NoaEsNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy noaesnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
