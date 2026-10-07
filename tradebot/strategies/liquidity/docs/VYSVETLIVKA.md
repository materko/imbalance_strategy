# Liquidity — likvidita, sweep a cesta k nej — ako funguje

> V jednej vete: nad vrcholmi a pod dnami ležia stopky ostatných obchodníkov (likvidita); stratégia čaká, kým ich trh „vyberie“, a potom obchoduje otočku — alebo prieraz k ďalšej likvidite.

## Ako vznikne obchod
1. **Značenie.** Z výrazných vrcholov (buy-side) a dien (sell-side) na 5m až 4h sa ťahajú úrovne; rovnaké vrcholy sa zlúčia do silnejšej úrovne.
2. **Spúšťač:**
   - **sweep** — cena úroveň prerazí a zavrie späť → obchod proti (otočka),
   - **breakout** — cena zavrie za úrovňou → pokračovanie k ďalšej likvidite.
3. **Vstup** do pár sviečok vstupným modelom: IBS imbalance, pin bar, jeden z nich, alebo len zavretie v smere; len blízko úrovne.

## Stop a cieľ
- Stop za extrém sweepu / signálnu sviečku / ATR.
- Cieľ pevný RR, alebo najbližšia nevybratá likvidita v smere (v pásme min.–max. RR).

## Čo môžeš nastaviť
- TF úrovní, ich vek a zlučovanie, režim (sweep / breakout), vstupný model, stop, cieľ.

## Slovníček
- **Likvidita** — stopky a čakajúce objednávky nad vrcholmi a pod dnami.
- **Sweep** — rýchly prieraz úrovne a návrat späť („vybratie“ stopiek).
- **Imbalance (FVG)** — medzera medzi 1. a 3. sviečkou trojice: cena sa pohla tak rýchlo, že časť ceny „preskočila“.
- **Pin bar** — sviečka s malým telom a dlhým knôtom: cena bola v jednom smere odmietnutá a zavrela späť.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
