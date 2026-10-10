# SWEEPING ENGULF 1.0 — ako funguje

> V jednej vete: keď nová sviečka najprv vyberie low predošlej sviečky (zoberie stopky) a potom zavrie až nad jej high, trh ukázal manipuláciu smerom dole a pravý smer hore — stratégia kúpi so stopom pod manipuláciou a cieľom 2× stop (short naopak).

Zdroj: video LuxAlgo „I Backtested This Viral Trading Strategy“ (youtube.com/watch?v=oxZj1kSye-g).

## Ako vznikne obchod
1. **Výber** — sviečka (video: 4h) ide pod low predošlej sviečky (long) alebo nad jej high (short).
2. **Pohltenie** — tá istá sviečka zavrie za opačným koncom predošlej sviečky (nad jej high pri longu). Voliteľne stačí za jej telo.
3. **Predošlá sviečka** — predvolene musí ísť smerom manipulácie (pred longom medvedia); vo videu to bolo nastavenie „same direction“ a dávalo lepšie výsledky.
4. **Filter trendu** — EMA 200: long len nad ňou, short len pod ňou (vo videu zapnutý, v profile tiež).
5. **Vstup** — market na zavretí signálnej sviečky. Kým beží obchod, ďalšie signály sa neberú.

## Stop a cieľ
- **Stop** pod low (nad high) signálnej sviečky — tam bola manipulácia. Alebo v násobku ATR od vstupu.
- **Cieľ** 2× stop (nastaviteľné).

## Slovníček
- **Manipulácia / výber** — cena krátko prerazí extrém predošlej sviečky, zoberie stopky a otočí sa.
- **Pohltenie (engulf)** — sviečka zavrie za celým rozsahom predošlej sviečky.
- **EMA 200** — kĺzavý priemer 200 sviečok; ukazuje dlhodobý smer.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe.
