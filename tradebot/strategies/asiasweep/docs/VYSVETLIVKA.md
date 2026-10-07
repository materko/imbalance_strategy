# ASIA SWEEP 1.0 — ako funguje

> V jednej vete: v noci (Ázia) vznikne úzke rozpätie; ráno Londýn „vyberie“ stopky nad ním alebo pod ním, cena sa vráti — a stratégia obchoduje opačným smerom.

Klasický koncept smart money / ICT: nad maximom a pod minimom Ázie ležia stopky (likvidita), veľkí hráči ich v Londýne vyberú a trh potom ide do protismeru. Určená pre EURUSD, 5m graf.

## Ako vznikne obchod
1. **Range Ázie** — najvyššia a najnižšia cena 20:00–00:00 New York.
2. **Sweep v Londýne** (2:00–5:00) — cena prerazí maximum (alebo minimum) Ázie a potom sviečka zavrie **späť v rozpätí**.
3. **Vstup do protismeru** — po vybratí maxima short, po vybratí minima long — do 12 sviečok po sweepe a do 8:00, vstupným modelom: IBS imbalance, pin bar (aj samotná sviečka sweepu), ktorýkoľvek z nich, alebo len zavretie v smere.

## Stop a cieľ
- Stop za extrém sweepu (+ rezerva), cieľ RR (default 2), opačná strana rozpätia, jeho stred, alebo najbližší naked POC. Zatvorenie o 12:00.

## Filter naked POC (voliteľný)
Z volume profilu predošlého dňa (17:00–17:00 NY) sa vezme **POC** — cena s najväčším objemom. Kým sa ho cena nedotkne, je „naked“ (nedotknutý) a trh k nemu často smeruje. S filtrom ide long len keď je naked POC nad cenou, short len keď je pod ňou.

## Slovníček
- **Likvidita** — stopky nad vrcholmi a pod dnami.
- **Sweep** — rýchly prieraz úrovne a návrat späť.
- **POC / naked POC** — cena s najväčším objemom dňa / ktorej sa cena odvtedy nedotkla.
- **Imbalance (FVG)** — medzera medzi 1. a 3. sviečkou trojice: cena sa pohla tak rýchlo, že časť ceny „preskočila“.
- **Pin bar** — sviečka s malým telom a dlhým knôtom: cena bola v jednom smere odmietnutá a zavrela späť.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
