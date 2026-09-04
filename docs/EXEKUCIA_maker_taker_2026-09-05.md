# Koľko z príkazov by ležalo v knihe (2026-09-05)

Ladenie parametrov je vyčerpané ([HYPEROPT_uzky_2026-09-04.md](HYPEROPT_uzky_2026-09-04.md)):
edge stratégie je ~0,05 % na stranu, čo je presne toľko, koľko berie Binance ako
taker. Pri takom pomere prestáva byť exekúcia detail — rozdiel medzi maker (0,02 %)
a taker (0,05 %) poplatkom je rozdielom medzi nulou a ziskom.

Meria to `python -m ibs.tools.fees`.

## Ako sa to rozhoduje

**Vstup** je limitka na cene medzery. Je pasívna vtedy, keď v okamihu zadania leží
na správnej strane trhu — pre LONG pod aktuálnou cenou. Porovnáva sa s otváracou
cenou sviečky, na ktorej bol príkaz zadaný; presne tú dostane `custom_entry_price()`
ako `proposed_rate`, takže je to tá istá informácia, akú má stratégia v reálnom čase.
Žiadny pohľad dopredu.

**Výstup** podľa dôvodu: `roi` (take profit) je odpočívajúca limitka, teda maker;
`stop_loss` aj `session_end` idú trhom, teda taker.

## Výsledok

Profil `btcusdt_3m_binance_struct`, päť rokov, 478 obchodov:

| okno | obchodov | vstup maker | hrubý zisk | break-even | **čistý (zmiešaný)** | čistý (len taker) |
|---|---|---|---|---|---|---|
| 2021-10 → 2022-10 | 87 | 54,0 % | +10 018 | 0,1398 % | **+7 212** | +6 436 |
| 2022-10 → 2023-10 | 107 | 55,1 % | −355 | −0,0032 % | −4 877 | −5 963 |
| 2023-10 → 2024-10 | 106 | 62,3 % | +2 049 | 0,0156 % | −3 084 | −4 514 |
| 2024-09 → 2025-09 | 96 | 60,4 % | +7 359 | 0,0397 % | **+48** | −1 914 |
| 2025-09 → 2026-09 | 82 | 40,2 % | +8 323 | 0,0568 % | **+2 321** | +993 |
| **spolu** | **478** | **55,0 %** | **+27 393** | **0,0423 %** | **+1 620** | **−4 961** |

**55 % vstupov by ležalo v knihe**, ale výstupov len **16,5 %** — výstupy ovláda
`stop_loss`, ktorý ide vždy trhom. Zmiešaný poplatok preto vyjde **0,0398 %** na
stranu namiesto 0,05 %, teda o pätinu nižší.

To stačí na obrátenie znamienka: **−4 961 → +1 620 USDT** naprieč piatimi rokmi,
a tri z piatich rokov skončia v pluse.

## Prečo to napriek tomu nie je obchodovateľné

Rozdiel medzi edge (0,0423 %) a nákladom (0,0398 %) je **0,0025 % na stranu**. To je
pätina jedného ticku na BTC. Čokoľvek, čo model neuvažuje, tú maržu zmaže:

**Post-only by 45 % vstupov odmietlo.** Tu sa počítajú ako taker, čo je
konzervatívne — reálne by tie obchody nevznikli vôbec, aj s ich ziskami.

**Slippage nie je v modeli vôbec.** Stop-loss ide trhom v pohybe, teda presne tam,
kde je slippage najväčší, a tvorí väčšinu výstupov.

## Vyplniteľnosť limitiek: obava sa nepotvrdila

Najväčšia výhrada voči maker modelu bola, že backtest vyplní limitku vždy, keď ju
sviečka preťala — v knihe sa ale príkaz na *dotknutej* úrovni nemusí vyplniť vôbec.
Order-book dáta nemáme, ale z 1m sviečok sa dá zistiť, ako hlboko cena za limitku
prešla. Keď prejde hlboko, na fronte v knihe nezáleží — vyplní sa isto.

`python -m ibs.tools.fees --fill-check`, 263 maker-spôsobilých vstupov:

| hĺbka prieniku | vstupov | |
|---|---|---|
| len dotyk (< 1 tick) | 6 | 2,3 % |
| 1–5 tickov | 4 | 1,5 % |
| 5–50 tickov | 60 | 22,8 % |
| **> 50 tickov** | **193** | **73,4 %** |

**96 % vstupov má prienik aspoň 5 tickov** a tri štvrtiny viac než 50 tickov (5 USD).
Vstupy sú na cenách medzier, cez ktoré trh prechádza, nie na úrovniach, ktorých sa
len obtrie. Pochybných vyplnení je šesť — a keď sa zahodia, výsledok sa **zlepší**
(+1 620 → +2 033 USDT), lebo boli mierne stratové.

Táto výhrada teda padá. Zostávajú dve:

## Poplatková trieda pomáha viac než čokoľvek iné

| trieda | maker / taker | zmiešaný | čistý za 5 rokov |
|---|---|---|---|
| VIP 0 | 0,020 / 0,050 | 0,0398 % | +1 620 |
| VIP 0 + BNB | 0,018 / 0,045 | 0,0358 % | **+4 197** |
| VIP 1 | 0,016 / 0,040 | 0,0319 % | **+6 775** |
| VIP 2 | 0,014 / 0,035 | 0,0279 % | **+9 352** |

Samotná zľava za platenie poplatkov v BNB (10 %) pridá viac než celý štruktúrny
filter. To hovorí hlavne o tom, ako tesne je stratégia na hranici.

## Záver

1. Maker vstupy **obrátia znamienko**, ale marža je 0,0025 % na stranu — v rámci
   trhového šumu.
2. Väčšinu poplatkov nezaplatia vstupy, ale **stop-lossy**, a tie sa maker urobiť
   nedajú. Zníženie počtu stop-outov je zároveň jediná cesta k nižším poplatkom aj
   k vyššiemu edge — je to ten istý problém so vstupmi ako doteraz.
3. **Vyplniteľnosť limitiek nie je problém** — 96 % vstupov má prienik aspoň päť
   tickov. Order-book dáta na túto otázku netreba.
4. Čo zostáva nezmerané, je **slippage na stop-lossoch**. Tie idú trhom v pohybe,
   tvoria väčšinu výstupov a v modeli sú za nulovú cenu. Na to by už bolo treba
   aspoň `aggTrades` (nie celú knihu) — a stačili by minúty okolo výstupov.

```bash
python -m ibs.tools.fees                       # posledny backtest
python -m ibs.tools.fees --maker 0.018 --taker 0.045
```
