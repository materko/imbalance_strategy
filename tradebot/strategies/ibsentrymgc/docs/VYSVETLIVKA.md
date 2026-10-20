# IBS EZ MGC — ako funguje

> V jednej vete: rovnaká stratégia ako IBS Entry Zone na Nasdaqu, len na zlate (MGC) — všetky prahy, ktoré sú na NQ v bodoch, sú tu v násobkoch ATR, aby sedeli k zlatu pri cene 1 800 $ aj 4 000 $.

## Čo robí (rovnako ako IBS Entry Zone)
1. Hľadá zóny dopytu a ponuky a veľké medzery po prudkom pohybe (FVG) na vyšších timeframoch.
2. Keď sa cena do zóny vráti, čaká na vstupný model IBS — imbalance, pin bar alebo engulfing.
3. Vstup limitkou, stop za zónou, cieľ v pomere k riziku (RR).

## Stop a cieľ
- **Stop** za zónou (spodok dopytovej / vrch ponukovej zóny) s rezervou, najmenej `minSlDistance` % ceny.
- **Cieľ** = RR × vzdialenosť stopu (IBS EZ 1: RR 0,5).

## Čím sa líši
- **Trh:** MGC (Micro Gold futures, CME), 1 bod = 10 $, tick 0,1 = 1 $.
- **Prahy v ATR:** veľkosť imbalance, pin baru, engulfingu, zhluk S/R, FVG a vzdialenosti v tickoch sú prepočítané z IBS EZ 1 (prešiel smernicou na MNQ) cez medián ATR 3m na MNQ (9,74 bodu). Napríklad imbalance 8 bodov = 0,82 ATR.
- **Stratégie na NQ sa nemenia** — toto je samostatná kópia s vlastnými profilmi.

## Stav
Východiskový profil je len štart hľadania podľa smernice na zlate; nastavenia pre zlato vznikajú hľadaním (ladenie 10/2021 – 9/2025, odložený rok 9/2025 – 9/2026).
