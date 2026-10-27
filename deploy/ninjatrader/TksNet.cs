// TksNet - TKS 1.0 (NQ Kompas) s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/tks/csharp`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „TksNet" na MINUTOVOM grafe.
// Informativny TF strategia nema; Kompas (VWAP, tlak) si sklada z barov grafu (treba skutocny objem burzy - CME futures).
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class TksNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "tksnet"; } }

        // MNQ futures 3m: NQ Kompas v seanse 9:30-16:00 NY, vstup po N sviecok za hranicou, SL swing, TP v RR
        protected override string DefaultProfile { get { return "mnq_databento_3m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "TksNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy tksnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
