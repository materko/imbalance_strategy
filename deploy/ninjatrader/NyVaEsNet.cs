// NyVaEsNet - NY VA BREAKOUT ES s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/nyva/ports/csharp`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „NyVaEsNet" na MINUTOVOM grafe.
// Informativny TF strategia nema; volume profile prvej hodiny NY si sklada z barov grafu (treba skutocny objem burzy - CME futures ES / MES).
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class NyVaEsNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "nyvaesnet"; } }

        // ES futures 3m: profil 9:30-10:30 NY, prieraz nad VAH / pod VAL (retest), SL za POC, TP v RR
        protected override string DefaultProfile { get { return "PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "NyVaEsNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy nyvaesnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
