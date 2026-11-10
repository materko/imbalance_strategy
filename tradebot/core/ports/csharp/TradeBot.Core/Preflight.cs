// Kontrola pred zivym startom (audit 9. 11. 2026, vylepsenie 6): engine, ktory vie, ze o chvilu ticho prestane
// obchodovat (kalendar sprav konci, data s datumom platnosti), to povie adapteru pri starte a ten to posle do hubu
// ako `note warn` - namiesto tichej degradacie, na ktoru sa pride az podla chybajucich obchodov.
//
// Jadro ani adaptery nepoznaju strategiu menom: engine (alebo jeho vrstva) implementuje `IPreflight`, adapter vola
// `Preflight.Run` (NinjaTrader) alebo `StaticHost.Preflight` (MT5). Engine bez rozhrania = ziadne upozornenia.
using System;
using System.Collections.Generic;

namespace TradeBot.Core
{
    public interface IPreflight
    {
        /// <summary>Upozornenia k casu `nowMs` (UTC); prazdny zoznam = vsetko v poriadku. Nesmie menit stav enginu.</summary>
        List<string> Preflight(long nowMs);
    }

    public static class Preflight
    {
        /// <summary>Upozornenia vsetkych vrstiev enginu (zvonka dnu). Vynimka z jednej vrstvy je tiez upozornenie.</summary>
        public static List<string> Run(IEngine engine, long nowMs)
        {
            List<string> all = new List<string>();
            for (IEngine e = engine; e != null; )
            {
                IPreflight p = e as IPreflight;
                if (p != null)
                {
                    try
                    {
                        List<string> own = p.Preflight(nowMs);
                        if (own != null) all.AddRange(own);
                    }
                    catch (Exception ex) { all.Add("kontrola pred startom zlyhala - " + ex.Message); }
                }
                EngineLayer layer = e as EngineLayer;
                e = layer != null ? layer.Inner : null;
            }
            return all;
        }
    }
}
