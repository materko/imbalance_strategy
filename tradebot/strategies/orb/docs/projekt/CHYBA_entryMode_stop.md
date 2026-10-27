# Chyba v ORB stratégii — typ vstupu „stop" vždy spadne

Nájdené 17. 9. 2026. **Neopravil som to** — je to tvoj kód a je to rozhodnutie, ktoré patrí tebe.

## Čo sa deje

Každý backtest s `entryMode = stop` skončí chybou:

    AttributeError: type object 'OrderType' has no attribute 'STOP'

Padne vždy, na každom trhu, pri každom nastavení. Z prvej mriežky to zožralo tretinu pokusov,
kým som na to prišiel. Odvtedy testujem len `close` a `retest`.

## Kde to je

`tradebot/strategies/orb/engine.py`, riadok 304:

    order_type = OrderType.MARKET if cfg.entryMode is EntryMode.CLOSE else OrderType.STOP

Lenže `tradebot/core/types.py` definuje `OrderType` len s dvoma hodnotami:

    LIMIT, MARKET

Žiadne `STOP` tam nie je. Config aj číselník `EntryMode` pritom hodnotu `stop` ponúkajú,
takže sa dá vybrať vo webappe aj v profile — a beh spadne.

## Možnosti, ako to vyriešiť

**1. Doplniť STOP do číselníka a naučiť emulátor stop objednávky.**
Najpoctivejšie a významovo správne: stop vstup má vyplniť pri prerazení hranice, teda
pri cene `st.break_level`, nie na close sviečky. V `adapters/multicharts/emulator.py`
by funkcia `_entry_fill` potrebovala tretiu vetvu — dnes rieši len market (plní na otvorení)
a limit (plní, keď cena dosiahne úroveň). Stop je zrkadlový k limitu: pre long sa plní,
keď cena vystúpi **nad** úroveň, pre short keď klesne **pod** ňu.

**2. Mapovať stop na market.**
Jednoriadková zmena, ale mení význam — vstupovalo by sa na otvorení nasledujúcej sviečky
namiesto na úrovni prerazenia. Výsledky by boli o niečo horšie než realita pri pokojnom trhu
a o dosť lepšie pri medzere. Nepovažujem to za dobrý nápad, len za rýchly.

**3. Nechať tak a zakázať `stop` vo výbere.**
Ak stop vstup nepotrebuješ, najčistejšie je vyhodiť ho z `EntryMode`, aby sa nedal vybrať
a nepadalo to. Testovanie tým nestratí nič — `close` aj `retest` fungujú.

## Čo to znamená pre doterajšie výsledky

Nič, čo by ich znehodnotilo. Všetky pokusy s `stop` skončili chybou, takže sa do výsledkov
nedostali — len sa na nich premrhal čas. Ak sa stop vstup opraví, oplatí sa ladenie zopakovať,
lebo pri ORB je vstup na prerazení prirodzenejší než vstup na zavretí sviečky.
