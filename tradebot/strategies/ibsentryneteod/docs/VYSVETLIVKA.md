# IBS Entry Zone (C# jadro EOD) — ako funguje

> V jednej vete: presne tá istá stratégia ako **IBS Entry Zone (C# jadro)**, len o 15:59 New York (21:59 nášho času) zavrie všetky otvorené pozície, zruší čakajúce príkazy a do 18:00 New York (nový obchodný deň CME) nevstúpi — pre prop účty na futures, kde pozícia nesmie prežiť koniec obchodného dňa.

## Koniec obchodného dňa (EOD) — jediný rozdiel oproti IBS Entry Zone (C# jadro)
1. **Zatvorenie:** na poslednej sviečke, ktorá sa zatvára najneskôr o 15:59 New York (21:59 nášho času), sa zavrú
   všetky otvorené pozície za trhovú cenu a zrušia sa čakajúce vstupné príkazy (limitky). Na 3m grafe je to sviečka
   zatvárajúca sa o 15:57, na 5m o 15:55, na 1m o 15:59.
2. **Pauza:** od tej chvíle do 18:00 New York (začiatok nového obchodného dňa CME) stratégia nevstúpi.
3. **Letný čas:** okno sa ráta v čase New York. Pár týždňov v roku, keď sa čas v USA a v Európe prestavuje v iný deň,
   je to u nás 20:59 — vždy skôr, nikdy nie neskôr ako 21:59.
4. Skrátené dni pred sviatkami (burza končí o 13:00 NY) stratégia nepozná — vtedy zavrie až o 15:59 NY, ak sa ešte obchoduje.

Všetko ostatné (vstupy, stop, cieľ, filtre) je rovnaké ako pri predlohe — až po okno EOD sú obchody sviečku po sviečke tie isté.


## Ako vznikne obchod
1. **Zóna.** Na detekčnom TF (napr. 3m alebo 5m) stratégia hľadá štyri sviečky: po sviečke proti smeru prídu sviečky v smere a/alebo medzera (imbalance). Rozsah prvej sviečky, odkiaľ pohyb vyrazil, sa stane **zónou** — pod cenou dopyt (long), nad cenou ponuka (short). Zóna platí len niekoľko hodín (`zoneValidHours`).
2. **Návrat do zóny.** Keď sa cena do zóny vráti, stratégia začne hľadať vstup jedným z troch **vstupných modelov**:
   - **IMB (imbalance breakout)** — v zóne nájde medzeru (imbalance), počká, kým cena zo zóny vyjde, potom na **potvrdenie** (zavretie za telom imbalance sviečky), a nakoniec na **retest** — návrat k otvoreniu imbalance sviečky. Tam položí order.
   - **Pin bar** — keď sa v zóne objaví pin bar v smere obchodu, order sa položí hneď.
   - **Engulfing** — sviečka, ktorá „pohltí“ predošlú, v smere obchodu.
3. **Order** čaká na vyplnenie len pár sviečok (`state5MaxBars`), potom sa zruší.

## Stop a cieľ
- **Stop** za najbližší swing (pri IMB) alebo za knôt pin baru / engulfingu, plus voliteľná rezerva v tickoch.
- **Cieľ** = stop × RR (`rrRatio`). Pri RR 0,5 je cieľ polovičný oproti stopu → vysoký win rate, malé výhry.
- Veľkosť pozície sa počíta tak, aby strata na stope bola `maxLossDollar`.

## Čo všetko sa dá nastaviť (najdôležitejšie)
- **Seansy** — až tri časové okná: kedy sa kreslia zóny a kedy sa smie obchodovať.
- **Zdroje zón** — SD zóny, voliteľne aj S/R úrovne a likvidita.
- **Smer** — oba, len long, len short, alebo podľa indikátorov (Supertrend / ADX na vyššom TF).
- **Filtre** — objem, trhová štruktúra (BOS/CHoCH), max. počet ziskových obchodov za deň.
- **Časovanie IMB modelu** — koľko sviečok sa čaká v každom kroku (state1–state5).

## Čo pribudlo oproti IBS
- **Obchodovať zóny z FVG** — zapína medzery ako zdroj zón; vyberieš, z ktorých TF (5m / 15m / 30m / 1h).
- **Min. veľkosť medzery** — menšie medzery sa ignorujú (napr. 30 bodov na MNQ).
- **IFVG (inverzné FVG)** — medzera, ktorú cena prerazí zatvorením, sa otočí na zónu opačného smeru.

## Na čo je určená
MNQ / NAS100 na 3m grafe. Existuje aj verzia pre TradingView (Pine) s profilom NOCNE TESTY 2 B_stabilny.

## Slovníček
- **SD zóna (supply / demand)** — cenové pásmo, odkiaľ cena predtým silno odišla; dopyt (demand) pod cenou, ponuka (supply) nad cenou.
- **Imbalance (FVG, gap)** — medzera medzi 1. a 3. sviečkou trojice: cena sa pohla tak rýchlo, že časť ceny „preskočila“. Znak silného pohybu.
- **IFVG** — inverzné FVG: medzera, ktorú cena „prerazila“, sa z podpory stane odporom a naopak.
- **Pin bar** — sviečka s malým telom a dlhým knôtom: cena išla jedným smerom, ale bola odmietnutá a zavrela späť.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
