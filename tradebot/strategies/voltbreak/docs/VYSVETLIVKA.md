# Volt Break — ako funguje

> V jednej vete: keď cena cez deň vystúpi nad „hluk" okolo polnočného otvorenia a zároveň nad VWAP, kúpi sa — v nádeji, že ide o skutočný ťah, nie náhodné kolísanie.

## Ako vznikne obchod (len long, 30m graf NQ / MNQ)
1. **Open o polnoci** (čas Chicaga) je východisko dňa.
2. **Noise Up** = open + 30 % priemerného denného pohybu (priemer ATR za posledných 15 seáns). Pohyb pod touto hranicou berieme ako bežný hluk.
3. **Signál:** 30-minútová sviečka zavrie nad Noise Up **aj** nad VWAP (od polnoci), medzi 10:00 a 14:30 CT.
4. Vstup na otvorení ďalšej sviečky. Po výstupe môže prísť ďalší vstup, najviac 3 za deň.

## Stop, cieľ a koniec dňa
- Cieľ 800 $ a stop 1 500 $ na jeden kontrakt NQ (40 a 75 bodov). Cieľ je bližšie než stop — stratégia stavia na vysokej úspešnosti.
- O 14:30 CT sa otvorená pozícia zatvorí.

## Pôvod
Doslovný prepis Pine skriptu podľa videa „Hedge Fund Manager TOP 3 Strategies" (Matteo Conti / IQ Capital).

## Slovníček
- **ATR** — priemerný rozsah (pohyb) za deň; meria, ako veľmi sa trh hýbe.
- **VWAP** — priemerná cena dňa vážená objemom; nad ním sú kupujúci v zisku.
- **Noise (hluk)** — bežné kolísanie ceny, ktoré ešte neznamená smer.
