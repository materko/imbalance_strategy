# NOC + PONDELOK 1.0 — ako funguje

> V jednej vete: keď je Nasdaq v rastovom trende, stratégia kúpi večer o 15:55 New York a predá o 3:00 ráno, a v pondelok kúpi aj pri otvorení o 9:30 a predá o 15:55.

## Prečo by to malo fungovať
- **Zisk Nasdaqu vzniká hlavne mimo dňa.** Na MNQ 2019–2026 urobila noc (16:00 → 9:30) +147 %, deň (9:30 → 16:00) len +63 %. Rovnaký jav je zdokumentovaný na QQQ aj SPY za 30 rokov.
- **Výsledky veľkých firiem prichádzajú po 16:00**, takže veľké pohyby sú večer a v Ázii. Úsek 3:00–9:30 (Londýn) už nepridáva — preto výstup o 3:00.
- **Pondelok** je jediný deň s jasne kladným priemerom seansy (61 % pondelkov v pluse).
- **Filter trendu** (denné zavretie nad priemerom 100 dní) vypína obdobia, keď trh dlho padá — napríklad rok 2022.

## Ako vznikne obchod
1. **Denné zavretie:** o 15:55 NY sa zapamätá cena; z posledných 100 takých cien sa počíta priemer (SMA).
2. **Noc:** po–pi o 15:55, keď je cena nad SMA → kúpa. Výstup o 3:00 NY ďalší obchodný deň (z piatku v pondelok o 3:00).
3. **Pondelok:** o 9:30, keď bolo piatkové zavretie nad SMA → kúpa, výstup o 15:55. Keď o 15:55 platí aj noc, pozícia sa len podrží do 3:00.
4. **Roll kontraktu:** v marci, júni, septembri a decembri sa od 7. do 16. dňa noci vynechajú (v dátach je v noc rollu umelý skok medzi kontraktmi).

## Stop a cieľ
- Bez cieľa a predvolene bez stopu — obchod vždy končí v čase. Voliteľná poistka `stopPct` v % ceny (proti veľkému gapu).

## Výsledky z prieskumu (MNQ 5/2019 – 9/2026, 1 kontrakt, poplatok 1 bod)
209 obchodov za rok, winrate 57 %, PF 1,47, najväčší pokles 3 455 $. Okná smernice: 1,19 / 1,27 / 1,52 / 1,45, posledný rok 1,38.
Pozor: posledný rok bol pri prieskume viditeľný, nie je to čistý odložený rok — rozhoduje forward test.

## Slovníček
- **SMA** — jednoduchý priemer posledných N cien.
- **RTH** — hlavná seansa 9:30–16:00 New York.
- **Roll** — prechod z končiaceho kontraktu futures na ďalší (štvrťročne).
