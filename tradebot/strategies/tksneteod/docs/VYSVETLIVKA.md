# TKS 1.0 (C# jadro EOD) — ako funguje

> V jednej vete: presne tá istá stratégia ako **TKS 1.0 (C# jadro)**, len o 15:59 New York (21:59 nášho času) zavrie všetky otvorené pozície, zruší čakajúce príkazy a do 18:00 New York (nový obchodný deň CME) nevstúpi — pre prop účty na futures, kde pozícia nesmie prežiť koniec obchodného dňa.

## Koniec obchodného dňa (EOD) — jediný rozdiel oproti TKS 1.0 (C# jadro)
1. **Zatvorenie:** na poslednej sviečke, ktorá sa zatvára najneskôr o 15:59 New York (21:59 nášho času), sa zavrú
   všetky otvorené pozície za trhovú cenu a zrušia sa čakajúce vstupné príkazy (limitky). Na 3m grafe je to sviečka
   zatvárajúca sa o 15:57, na 5m o 15:55, na 1m o 15:59.
2. **Pauza:** od tej chvíle do 18:00 New York (začiatok nového obchodného dňa CME) stratégia nevstúpi.
3. **Letný čas:** okno sa ráta v čase New York. Pár týždňov v roku, keď sa čas v USA a v Európe prestavuje v iný deň,
   je to u nás 20:59 — vždy skôr, nikdy nie neskôr ako 21:59.
4. Skrátené dni pred sviatkami (burza končí o 13:00 NY) stratégia nepozná — vtedy zavrie až o 15:59 NY, ak sa ešte obchoduje.

Všetko ostatné (vstupy, stop, cieľ, filtre) je rovnaké ako pri predlohe — až po okno EOD sú obchody sviečku po sviečke tie isté.



## NQ Kompas
Číslo 0–100 počas seansy New York (9:30–16:00) z toho, čo na 6 rokoch MNQ predpovedalo trend dňa: o koľko je pohyb od otvorenia nad bežným pre túto minútu, kde je cena v nočnom range, či kupujúci alebo predávajúci tlačia (kde sviečky zatvárajú × objem) a koľko času je cena nad VWAP.

## Ako vznikne obchod
1. Kompas zavrie **pod spodnou hranicou** (napr. 35) **3 sviečky po sebe** → **short** market.
2. Zrkadlovo **nad hornou hranicou** (napr. 65) → **long**.
3. Ďalší signál až keď Kompas od hranice odíde; vždy len jedna pozícia.

## Stop, cieľ a koniec dňa
- **Stop** na najbližší swing high (short) / swing low (long) za cenou.
- **Cieľ** = RR × vzdialenosť stopu (zadanie 1:1).
- Pozícia sa drží do stopu alebo cieľa (voliteľne zavrieť o 16:00).

## Slovníček
- **Swing high / low** — lokálny vrchol / dno potvrdené sviečkami na oboch stranách.
- **VWAP** — priemerná cena dňa vážená objemom.
