# VWAP ADX Pullback (C# jadro EOD) — ako funguje

> V jednej vete: presne tá istá stratégia ako **VWAP ADX Pullback (C# jadro)**, len o 15:59 New York (21:59 nášho času) zavrie všetky otvorené pozície, zruší čakajúce príkazy a do 18:00 New York (nový obchodný deň CME) nevstúpi — pre prop účty na futures, kde pozícia nesmie prežiť koniec obchodného dňa.

## Koniec obchodného dňa (EOD) — jediný rozdiel oproti VWAP ADX Pullback (C# jadro)
1. **Zatvorenie:** na poslednej sviečke, ktorá sa zatvára najneskôr o 15:59 New York (21:59 nášho času), sa zavrú
   všetky otvorené pozície za trhovú cenu a zrušia sa čakajúce vstupné príkazy (limitky). Na 3m grafe je to sviečka
   zatvárajúca sa o 15:57, na 5m o 15:55, na 1m o 15:59.
2. **Pauza:** od tej chvíle do 18:00 New York (začiatok nového obchodného dňa CME) stratégia nevstúpi.
3. **Letný čas:** okno sa ráta v čase New York. Pár týždňov v roku, keď sa čas v USA a v Európe prestavuje v iný deň,
   je to u nás 20:59 — vždy skôr, nikdy nie neskôr ako 21:59.
4. Skrátené dni pred sviatkami (burza končí o 13:00 NY) stratégia nepozná — vtedy zavrie až o 15:59 NY, ak sa ešte obchoduje.

Všetko ostatné (vstupy, stop, cieľ, filtre) je rovnaké ako pri predlohe — až po okno EOD sú obchody sviečku po sviečke tie isté.


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
