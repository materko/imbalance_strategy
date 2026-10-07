# Range Breakout — ako funguje

> V jednej vete: stratégia kdekoľvek na grafe nájde úzku konsolidáciu (cena chodí do strán) a obchoduje jej prerazenie.

Na rozdiel od ORB nie je range viazaný na otvorenie trhu — hľadá sa priebežne.

## Ako vznikne obchod
1. **Hľadanie.** Posledných N sviečok je range, keď je ich šírka v pásme min.–max. (v ATR).
2. **Nabitie.** Hranice sa zafixujú; príliš starý range sa zahodí.
3. **Prieraz.** Zavretie za hranicou + rezerva; voliteľne druhé zavretie.
4. **Vstup:** hneď (`close`), limitkou na návrat k hranici (`retest`), alebo po reteste ešte potvrdenie (`continuation`).
5. **Zlyhaný prieraz** — keď sa cena vráti do rangu, setup sa zahodí.

## Stop a cieľ
- Stop za druhú stranu rangu / do stredu / v ATR, cieľ RR alebo výška rangu.

## Čo môžeš nastaviť
- Počet sviečok rangu, jeho šírku (ATR), vek, rezervu prierazu, typ vstupu, stop a cieľ.

## Slovníček
- **Konsolidácia (range)** — obdobie, keď cena chodí v úzkom pásme do strán.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
