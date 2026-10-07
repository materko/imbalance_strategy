# Demo Donchian Breakout — ako funguje

> V jednej vete: ukážková stratégia — kúpi, keď cena zavrie nad najvyššou cenou posledných N sviečok, predá, keď zavrie pod najnižšou.

Slúži na overenie, že rámec (webapp, Freqtrade, MultiCharts) funguje s viacerými stratégiami. **Nie je to obchodné odporúčanie.**

## Ako vznikne obchod
1. **Donchian kanál** = najvyššie high a najnižšie low posledných N sviečok.
2. Zavretie nad horným okrajom → long, pod dolným → short.
3. Opačný prieraz zavrie otvorenú pozíciu.

## Stop a cieľ
- Stop v násobku ATR, cieľ = stop × RR.

## Čo môžeš nastaviť
- Dĺžku kanála, ATR a jeho násobok pre stop, RR.

## Slovníček
- **Donchian kanál** — pásmo medzi najvyšším a najnižším bodom za posledných N sviečok.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe. Prahy v ATR fungujú rovnako na pokojnom aj divokom trhu.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
