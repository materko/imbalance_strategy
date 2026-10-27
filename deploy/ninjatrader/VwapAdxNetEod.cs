// VwapAdxNetEod - VWAP ADX Pullback s jadrom v C# ako strategia NinjaTrader 8.
// EOD: o 15:59 New York (21:59 nasho casu) zavrie vsetko a do 18:00 NY nevstupi - pre prop ucty (`EodCloseEngine`).
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/vwapadx/csharp`, ADX z
// `IbsNet`) a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „VwapAdxNetEod" na MINUTOVOM grafe.
// Informativny TF strategia nema; VWAP si sklada z barov grafu (treba skutocny objem burzy - CME futures).
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class VwapAdxNetEod : TradeBotStrategy
    {
        protected override string EngineKey { get { return "vwapadxneteod"; } }

        // MNQ futures 1m: opening range 8:30-9:00 CT, pullback k VWAP, ADX
        protected override string DefaultProfile { get { return "mnq_databento_1m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "VwapAdxNetEod";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy vwapadxneteod`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
