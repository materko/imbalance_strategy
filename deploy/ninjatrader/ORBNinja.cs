// ORBNinja - ORB (Opening Range Breakout) s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`csharp/TradeBot.Strategies/OrbNinja`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „ORBNinja" na MINUTOVOM grafe.
// Informativny TF strategia nema - na grafe staci jedna seria (plus jemna seria na plnenie orderov).
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class ORBNinja : TradeBotStrategy
    {
        protected override string EngineKey { get { return "orbninja"; } }

        // NAS100 / Nasdaq-100 futures: New York cash open, 15-minutovy range
        protected override string DefaultProfile { get { return "nas100_dukascopy_3m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "ORBNinja";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy orbninja`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
