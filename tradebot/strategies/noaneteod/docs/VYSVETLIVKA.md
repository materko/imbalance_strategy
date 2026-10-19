# NOA 1.0 (C# jadro EOD) — ako funguje

> V jednej vete: presne tá istá stratégia ako **NOA 1.0 (C# jadro)**, len o 15:59 New York (21:59 nášho času) zavrie všetky otvorené pozície, zruší čakajúce príkazy a do 18:00 New York (nový obchodný deň CME) nevstúpi — pre prop účty na futures, kde pozícia nesmie prežiť koniec obchodného dňa.

## Koniec obchodného dňa (EOD) — jediný rozdiel oproti NOA 1.0 (C# jadro)
1. **Zatvorenie:** na poslednej sviečke, ktorá sa zatvára najneskôr o 15:59 New York (21:59 nášho času), sa zavrú
   všetky otvorené pozície za trhovú cenu a zrušia sa čakajúce vstupné príkazy (limitky). Na 3m grafe je to sviečka
   zatvárajúca sa o 15:57, na 5m o 15:55, na 1m o 15:59.
2. **Pauza:** od tej chvíle do 18:00 New York (začiatok nového obchodného dňa CME) stratégia nevstúpi.
3. **Letný čas:** okno sa ráta v čase New York. Pár týždňov v roku, keď sa čas v USA a v Európe prestavuje v iný deň,
   je to u nás 20:59 — vždy skôr, nikdy nie neskôr ako 21:59.
4. Skrátené dni pred sviatkami (burza končí o 13:00 NY) stratégia nepozná — vtedy zavrie až o 15:59 NY, ak sa ešte obchoduje.

Všetko ostatné (vstupy, stop, cieľ, filtre) je rovnaké ako pri predlohe — až po okno EOD sú obchody sviečku po sviečke tie isté.


## Ako vznikne obchod (5m graf NQ / MNQ, seansa New York 9:30–16:00)
1. **Pásmo šumu:** pre každú minútu dňa priemer toho, o koľko sa cena v tom čase vzdiali od otvorenia dňa, za posledných 14 dní.
2. **Hranice:** horná = max(open, včerajšie zavretie) × (1 + pásmo), dolná = min(…) × (1 − pásmo).
3. **Kontroly:** rozhoduje sa len každých 30 minút (10:00, 10:30, …). Zavretie nad hornou hranicou = LONG, pod dolnou = SHORT.
4. **Výstup** tiež len na kontrole: long sa zavrie, keď cena klesne pod vyššiu z (horná hranica, VWAP); short zrkadlovo. O 16:00 sa zatvára všetko.

## Stop a cieľ
- **Stop** je len poistka (1 % z ceny) proti prudkému pohybu medzi kontrolami.
- **Cieľ** nemá — víťazné obchody bežia, kým sa trend neotočí pod VWAP, alebo do 16:00.

## Slovníček
- **Pásmo šumu** — bežný pohyb ceny od otvorenia v danom čase dňa; pohyb za ním je skutočný ťah.
- **VWAP** — priemerná cena dňa vážená objemom.
- **C# jadro** — tá istá logika prepísaná do C#, ktorý vedia spustiť NinjaTrader aj MetaTrader 5.
