# IBS EZ ES — ako funguje

> V jednej vete: rovnaká stratégia ako IBS Entry Zone na Nasdaqu, len na S&P 500 futures (ES) — všetky prahy, ktoré sú na NQ v bodoch, sú tu v násobkoch ATR, aby sedeli k ES, ktorý sa hýbe asi 4,5× menej bodov ako NQ.

## Čo robí (rovnako ako IBS Entry Zone)
1. Hľadá zóny dopytu a ponuky a veľké medzery po prudkom pohybe (FVG) na vyšších timeframoch.
2. Keď sa cena do zóny vráti, čaká na vstupný model IBS — imbalance, pin bar alebo engulfing.
3. Vstup limitkou, stop za zónou, cieľ v pomere k riziku (RR).

## Stop a cieľ
- **Stop** za zónou (spodok dopytovej / vrch ponukovej zóny) s rezervou, najmenej `minSlDistance` % ceny.
- **Cieľ** = RR × vzdialenosť stopu (IBS EZ 1: RR 0,5).

## Čím sa líši
- **Trh:** ES (E-mini S&P 500, CME), 1 bod = 50 $, tick 0,25 = 12,50 $. Medián ATR 3m 2,16 bodu (MNQ 9,74); imbalance medián 0,34 ATR (MNQ 0,28); najviac objemu 9–11 a 15–16 h NY.
- **Prahy v ATR:** veľkosť imbalance, pin baru, engulfingu, zhluk S/R, FVG a vzdialenosti v tickoch sú prepočítané z IBS EZ 1 (prešiel smernicou na MNQ) cez medián ATR 3m na MNQ (9,74 bodu). Napríklad imbalance 8 bodov = 0,82 ATR.
- **Stratégie na NQ sa nemenia** — toto je samostatná kópia s vlastnými profilmi.

## Stav
Východiskový profil je len štart hľadania podľa smernice na ES; nastavenia pre ES vznikajú hľadaním (ladenie 10/2021 – 9/2025, odložený rok 9/2025 – 9/2026).
