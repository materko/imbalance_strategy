// NoaNetEod - NOA 1.0 (Noise Area) s jadrom v C# ako strategia NinjaTrader 8.
// EOD: o 15:59 New York (21:59 nasho casu) zavrie vsetko a do 18:00 NY nevstupi - pre prop ucty (`EodCloseEngine`).
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`csharp/TradeBot.Strategies/NoaNet`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „NoaNetEod" na MINUTOVOM grafe.
// Informativny TF strategia nema; VWAP si sklada z barov grafu (treba skutocny objem burzy - CME futures).
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class NoaNetEod : TradeBotStrategy
    {
        protected override string EngineKey { get { return "noaneteod"; } }

        // MNQ futures 5m: pasmo sumu od 9:30 NY, kontroly, vystup cez VWAP / hranicu alebo 16:00
        protected override string DefaultProfile { get { return "mnq_databento_5m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "NoaNetEod";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy noaneteod`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
