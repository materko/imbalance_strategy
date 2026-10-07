# IBS FVG + IFVG — ako funguje

> V jednej vete: IBS vstupný model, ktorý obchoduje **len zóny z medzier (FVG a IFVG)** na 5m–1h — bez SD zón, S/R a likvidity.

Je to čistý test otázky „funguje IBS vstup na imbalance zónach?“. Logika je tá istá ako IBS Entry Zone, líšia sa len predvolené zdroje zón: SD zóny a engulfing sú vypnuté (dajú sa zapnúť), S/R, likvidita a Elliott nie sú vôbec.

## Ako vznikne obchod
1. Na 5m, 15m, 30m a 1h (skladá sa z grafu) stratégia hľadá **FVG** — medzeru medzi 1. a 3. sviečkou. Býčia medzera = dopyt (long), medvedia = ponuka (short).
2. Voliteľne **IFVG** — keď cena medzeru prerazí zatvorením, otočí sa na zónu opačného smeru.
3. Keď sa cena do zóny vráti, vstup ide IBS modelom: imbalance → výstup zo zóny → potvrdenie → retest, alebo pin bar.

## Stop a cieľ
- Stop za swing alebo knôt pin baru, cieľ = stop × RR, veľkosť z rizika v $.

## Čo môžeš nastaviť
- Ktoré TF medzier (5m / 15m / 30m / 1h), min. veľkosť medzery, FVG / IFVG zapnuté.
- Všetko ostatné ako v IBS (seansy, smer, časovanie modelu, RR).

## Slovníček
- **Imbalance (FVG, gap)** — medzera medzi 1. a 3. sviečkou trojice: cena sa pohla tak rýchlo, že časť ceny „preskočila“. Znak silného pohybu.
- **IFVG** — inverzné FVG: prerazená medzera mení úlohu (podpora → odpor).
- **Pin bar** — sviečka s malým telom a dlhým knôtom: cena išla jedným smerom, ale bola odmietnutá a zavrela späť.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
