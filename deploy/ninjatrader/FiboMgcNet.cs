// FiboMgcNet - Fibo 1.0 na zlate (MGC) s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/csharp/TradeBot.Strategies/FiboNet`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „FiboMgcNet" na MINUTOVOM grafe.
// Informativny TF strategia nema; swingy (swingTF z profilu) si sklada z barov grafu. Futures MGC / GC.
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class FiboMgcNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "fibomgcnet"; } }

        // MGC futures 3m: noha na swingTF, navrat k Fibonacciho urovniam, vstup na imbalance / pin bar, SL za nohou
        protected override string DefaultProfile { get { return "PRESIEL_SMERNICAMI_Fibo_1_0_MGC_1"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "FiboMgcNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy fibomgcnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
