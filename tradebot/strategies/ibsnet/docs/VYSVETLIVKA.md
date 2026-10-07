# IBSNet Imbalance Breakout (C# jadro) — ako funguje

> V jednej vete: presne tá istá stratégia ako **IBS Imbalance Breakout**, len jej jadro je napísané v C#, aby bežala natívne v NinjaTraderi a MetaTraderi 5.

Obchody dáva sviečku po sviečke rovnaké ako IBS (overuje to test parity). Vo webapp ju použiješ rovnako; zmysel má hlavne vtedy, keď chceš stratégiu nasadiť do NinjaTradera alebo MT5.

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

## Pozor
- Výsledky majú byť zhodné s IBS — ak sa líšia, je to chyba a treba ju nahlásiť.

## Slovníček
- **SD zóna (supply / demand)** — cenové pásmo, odkiaľ cena predtým silno odišla; dopyt (demand) pod cenou, ponuka (supply) nad cenou.
- **Imbalance (FVG, gap)** — medzera medzi 1. a 3. sviečkou trojice: cena sa pohla tak rýchlo, že časť ceny „preskočila“. Znak silného pohybu.
- **Pin bar** — sviečka s malým telom a dlhým knôtom: cena išla jedným smerom, ale bola odmietnutá a zavrela späť.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
