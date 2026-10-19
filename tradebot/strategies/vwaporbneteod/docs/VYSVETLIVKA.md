# VWAP ORB 1.5 (C# jadro EOD) — ako funguje

> V jednej vete: presne tá istá stratégia ako **VWAP ORB 1.5 (C# jadro)**, len o 15:59 New York (21:59 nášho času) zavrie všetky otvorené pozície, zruší čakajúce príkazy a do 18:00 New York (nový obchodný deň CME) nevstúpi — pre prop účty na futures, kde pozícia nesmie prežiť koniec obchodného dňa.

## Koniec obchodného dňa (EOD) — jediný rozdiel oproti VWAP ORB 1.5 (C# jadro)
1. **Zatvorenie:** na poslednej sviečke, ktorá sa zatvára najneskôr o 15:59 New York (21:59 nášho času), sa zavrú
   všetky otvorené pozície za trhovú cenu a zrušia sa čakajúce vstupné príkazy (limitky). Na 3m grafe je to sviečka
   zatvárajúca sa o 15:57, na 5m o 15:55, na 1m o 15:59.
2. **Pauza:** od tej chvíle do 18:00 New York (začiatok nového obchodného dňa CME) stratégia nevstúpi.
3. **Letný čas:** okno sa ráta v čase New York. Pár týždňov v roku, keď sa čas v USA a v Európe prestavuje v iný deň,
   je to u nás 20:59 — vždy skôr, nikdy nie neskôr ako 21:59.
4. Skrátené dni pred sviatkami (burza končí o 13:00 NY) stratégia nepozná — vtedy zavrie až o 15:59 NY, ak sa ešte obchoduje.

Všetko ostatné (vstupy, stop, cieľ, filtre) je rovnaké ako pri predlohe — až po okno EOD sú obchody sviečku po sviečke tie isté.


Jediné, čo C# verzia nemá: **stop posúvaný s VWAP** (`SL na dotyk VWAP`, `TP na cross VWAP`) — beh s ním odmietne.

## Ako vznikne obchod
1. **Opening range** z New York rangu od 9:30 (15:30 nášho času).
2. **Prieraz:** sviečka zavrie nad high rangu (long) / pod low (short).
3. **Potvrdenie VWAP** podľa nastavenia:
   - `break` — aj VWAP je nad high rangu (pod low),
   - `direction` — VWAP smeruje rovnako ako prieraz.
4. Vstup market na zavretí prvej sviečky, kde platí oboje (voliteľne len na samotnej prerazovacej sviečke).

## Stop a cieľ
- Stop na opačnej strane rangu; voliteľne stop na VWAP, ktorý sa s ním posúva.
- Cieľ RR, alebo držať, kým cena neprerazí VWAP proti obchodu, alebo čo príde skôr; voliteľne TP pri prechode VWAP v zisku.

## Čo môžeš nastaviť
- Všetko z ORB (range, seansy, filtre) plus pravidlo VWAP, stop na VWAP, typ výstupu.

## Slovníček
- **Opening range** — rozpätie prvých minút seansy.
- **VWAP** — priemerná cena dňa vážená objemom (od otvorenia); ukazuje „férovú“ cenu dňa podľa obchodovaného objemu.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
