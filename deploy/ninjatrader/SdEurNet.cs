// SdEurNet - SD ZONY EURUSD (6E) s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`csharp/TradeBot.Strategies/SdEurNet`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „SdEurNet" na MINUTOVOM grafe.
// Informativny TF strategia nema; zony (zoneTF z profilu) si sklada z barov grafu (graf 5m). Futures 6E / M6E (CME Euro FX).
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class SdEurNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "sdeurnet"; } }

        // 6E futures 5m: zony 1 h z noci, limitka na hrane pri prvom navrate v Londyne, SL za zonou, ciel RR
        protected override string DefaultProfile { get { return "eurusd_6e_5m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "SdEurNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy sdeurnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
