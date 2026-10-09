# VWAP ADX Pullback — ako funguje

> V jednej vete: keď cena po otvorení prerazí ranný range nahor, počká sa na návrat k VWAP a vstúpi sa long, keď trend (ADX) prestane zrýchľovať.

## Ako vznikne obchod (len long, 1m graf NQ / MNQ)
1. **Opening range:** high a low od 8:30 do 9:00 CT (9:30–10:00 New York).
2. **Nabitá:** po 9:00 zavrie sviečka nad high rangu.
3. **Pullback:** cena sa potom dotkne VWAP (low sviečky siahne na VWAP alebo pod neho).
4. **Potvrdenie:** sviečka zavrie znova nad VWAP.
5. **ADX:** je nad 20 a nestúpa oproti predošlej sviečke. Kým ADX ešte rastie, čaká sa.
6. Vstup market na otvorení ďalšej sviečky. Kroky 2–4 môžu nastať aj v jednej sviečke.

## Stop, cieľ a koniec dňa
- **Cieľ** = najvyšší high posledných 5 sviečok, **stop** = najnižší low posledných 20 sviečok. Obe úrovne sú pevné.
- Cieľ býva často len kúsok nad vstupom — veľa obchodov skončí rýchlo s malým ziskom, a preto na výsledok veľmi vplývajú poplatky.
- O 15:55 CT sa otvorená pozícia zatvorí. Jeden obchod za deň.

## Pôvod
Doslovný prepis Pine skriptu podľa videa „Hedge Fund Manager TOP 3 Strategies" (Matteo Conti / IQ Capital).

## Slovníček
- **Opening range** — rozpätie ceny v prvých minútach seansy; jeho prerazenie ukazuje smer dňa.
- **VWAP** — priemerná cena dňa vážená objemom (od 8:30 CT); „férová" cena podľa toho, kde sa naozaj obchodovalo.
- **ADX** — sila trendu (0–100). Nad 20 je trend; keď prestane stúpať, prvý ťah sa upokojil a pullback je lepší vstup.
- **Pullback** — návrat ceny proti trendu predtým, než trend pokračuje.
