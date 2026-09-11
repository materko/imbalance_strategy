# IBS na NAS100/USD — 2026-09-11

Zostavené z **21 behov** v histórii; nové backtesty sa nespúšťali. Stratégia `ibs`, trhy `NAS100/USD`, timeframe `3m`.

```bash
python -m tester.webapp.cli paper --runs 20260909-194704-5d0a03,20260909-194712-77e2d1,20260909-194728-5d0a03,20260909-194735-77e2d1,20260909-194901-5d0a03,20260909-194909-77e2d1,20260909-195235-5d0a03,20260909-195243-77e2d1,20260909-195322-5d0a03,20260909-195330-77e2d1,20260909-195412-5d0a03,20260909-195419-77e2d1,20260909-195521-5d0a03,20260909-195529-77e2d1,20260909-195608-5d0a03,20260909-195616-77e2d1,20260909-195631-f8c925,20260910-220626-0c05a9,20260910-220626-68c2e6,20260910-220626-cb296d,20260910-220626-d68bad
```

Konfigurácia: všetky behy majú tú istú konfiguráciu: golden_coinbase_btcusd_3m

## Záver

_Sem patrí jedna veta: čo z čísel dole plynie. Nechávam ju prázdnu zámerne — zhrnutie testov nižšie je zoznam verdiktov, nie záver._

## Zhrnutie testov

| test | verdikt |
|---|---|
| Čo je to za stratégiu | Prerazenie (breakout) |
| Po oknách | kladné v 7 z 7 okien |
| Interval okolo výsledku | +0.0192 až +0.0371 % |
| Odlíšiteľné od náhody? | +6.3 σ |
| Slabne edge? | DRZI |
| Ktorá skupina obchodov kazí výsledok | Najhorsia skupina je 'do 9 h' vlastnosti 'Hodina vstupu… |
| Drží to aj na iných trhoch? | SLABE |
| Cena rizika | TO NIE JE PORTFOLIO |

**V čom je dobrá**

- zisková v 21 z 21 referenčných okien
- 756 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 8.7 %
- odlíšiteľná od náhody (+6.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-04 - 2026-09 na 68. percentile toho, čo stratégia vyrobí sama od seba)

**Kde má chyby**

- náklad na tomto trhu nepoznáme, takže break-even sa proti ničomu neposudzuje — doplň ho do inštrumentu (`half_spread_ticks`)
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'do 9 h' vlastnosti 'Hodina vstupu (UTC)': 211 obchodov (27.9 %), bez nej by break-even bol o +0.0113 lepší (riadi `sess2TradeStartH`)

## Čo je to za stratégiu

**Prerazenie (breakout)** (istota: priemerná)

- vstup po pohybe v smere obchodu (+0.79 ATR za 5 barov)
- medián držania 13.7 barov grafu
- winrate 54.37 %, payoff 1.304
- 0.37 obchodov za deň
- šikmosť výnosov -0.013

| miera | hodnota |
|---|---|
| winrate | 54.4 % |
| payoff (zisk / strata) | 1.30 |
| očakávanie na obchod | +0.0533 % |
| medián držania | 13.7 barov |
| obchodov za deň | 0.37 |
| pohyb pred vstupom | 0.79 ATR |
| teplo pred ziskom (MAE/MFE) | 0.60 |

**Čo je pri tomto type normálne.** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.

**Na čo pozor.** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.

**Čo ladiť.** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

## Po oknách

| okno | obchodov | WR % | PnL % | break-even % | max DD % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 52 | 51.9 | +5.645 | +0.0400 | 2.65 | `20260910-220626-d68bad` |
| 20221001-20231001 | 55 | 54.5 | +1.525 | +0.0106 | 2.40 | `20260910-220626-68c2e6` |
| 20231001-20241001 | 57 | 61.4 | +9.973 | +0.0496 | 1.59 | `20260910-220626-0c05a9` |
| 20240904-20250904 | 66 | 50.0 | +5.258 | +0.0189 | 5.54 | `20260910-220626-cb296d` |
| 20250904-20260904 | 62 | 58.1 | +10.616 | +0.0319 | 5.37 | `20260909-194704-5d0a03` (+7) |
| 20210103-20260904 | 341 | 52.5 | +29.108 | +0.0237 | 5.54 | `20260909-195631-f8c925` |
| 20230904-20250904 | 123 | 57.7 | +17.228 | +0.0362 | 5.54 | `20260909-194712-77e2d1` (+7) |

**Kladné v 7 z 7 okien.** PnL v % závisí od sizingu a peňaženky, break-even nie — preto je rozhodujúci on.

## Interval okolo výsledku

Namerané **+0.0283 %**; preskladaním vlastných obchodov (blokový bootstrap) vyjde medzi **+0.0192** a **+0.0371 %**, medián +0.0283 %.

Náklad na tomto trhu nepoznáme, takže break-even sa tu proti ničomu neposudzuje — doplň ho do inštrumentu (`half_spread_ticks`).

## Odlíšiteľné od náhody?

Tá istá stratégia, ktorá obchoduje rovnako často, rovnakým smerom a s rovnakým stopom aj take profitom — len si nevyberá, **kedy** vstúpiť.

| náhoda | stratégia | náhoda | rozdiel | percentil |
|---|---|---|---|---|
| `anytime` | +0.0283 | +0.0014 ± 0.0043 | +6.29 σ | 100.0 |
| `session` | +0.0283 | +0.0010 ± 0.0045 | +6.09 σ | 100.0 |

Edge je odlisitelny od nahody (6.3 sigma, percentil 100.0).

## Slabne edge?

Úsek takej dĺžky, akú má posledné obdobie, vyjde tej istej stratégii medzi **+0.0013** a **+0.0543 %** už len preskladaním vlastných obchodov. Preto sa posledné obdobie neporovnáva s celkom: je kratšie, teda aj prirodzene rozkolísanejšie.

| obdobie | obchodov | /mes. | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-01 - 2022-06 | 115 | 6.8 | 49.6 | +0.0225 | 38 |
| 2022-06 - 2023-11 | 177 | 10.5 | 55.4 | +0.0257 | 40 |
| 2023-11 - 2025-04 | 241 | 14.2 | 51.5 | +0.0221 | 32 |
| 2025-04 - 2026-09 | 223 | 13.2 | 59.2 | +0.0365 | 68 |

DRZI: posledné obdobie (2025-04 - 2026-09) je na 68. percentile, teda v medziach +0.0013 až +0.0543 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

Percentil je test len pre **posledné** obdobie, lebo to bolo vybraté vopred; percentily ostatných období sú opis.

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 9 h' vlastnosti 'Hodina vstupu (UTC)': 211 obchodov (27.9 %), break-even 0.0001 % oproti 0.0283 % celku. Bez nej by break-even bol 0.0396 % (+0.0113). Filter na to postavit ide, ale najprv skus `sess2TradeStartH` - parameter je lacnejsi a citatelnejsi nez model.

**Hodina vstupu (UTC)** — Rozdelenie po hodinách ukáže, či edge nesie jedna seansa. Na IBS to tak bolo — celý edge bol v NY seanse.

| skupina | obch. | podiel % | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 9 h | 211 | 27.9 | 47.9 | +0.0001 | +0.0396 | +0.0113 |
| 15 h – 16 h | 115 | 15.2 | 56.5 | +0.0200 | +0.0298 | +0.0015 |
| nad 16 h | 97 | 12.8 | 58.8 | +0.0415 | +0.0264 | -0.0019 |
| 9 h – 15 h | 333 | 44.0 | 56.5 | +0.0459 | +0.0148 | -0.0135 |

**Trend alebo rozsah** — Efektivita pohybu za posledných 50 barov: 1 je priamka, 0 pílka okolo jednej úrovne. Prerazenie v rozsahu je falošné častejšie než v trende — a toto je číslo, ktorým sa to dá odfiltrovať.

| skupina | obch. | podiel % | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.157 | 188 | 24.9 | 48.9 | +0.0027 | +0.0371 | +0.0088 |
| 0.0371 – 0.089 | 189 | 25.0 | 56.6 | +0.0237 | +0.0299 | +0.0016 |
| 0.089 – 0.157 | 189 | 25.0 | 50.3 | +0.0250 | +0.0295 | +0.0012 |
| do 0.0371 | 190 | 25.1 | 61.6 | +0.0631 | +0.0170 | -0.0113 |

**Volatilita voči normálu** — ATR pri vstupe delené typickým ATR trhu. 1,0 je bežný deň, 2,0 dvojnásobne rozkolísaný. Náhrada za „pozri sa na VIX“, ktorá funguje na každom trhu.

| skupina | obch. | podiel % | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.856 – 2.553 | 189 | 25.0 | 49.7 | +0.0079 | +0.0353 | +0.0070 |
| do 1.264 | 191 | 25.3 | 52.4 | +0.0138 | +0.0331 | +0.0048 |
| 1.264 – 1.856 | 189 | 25.0 | 56.1 | +0.0281 | +0.0284 | +0.0001 |
| nad 2.553 | 187 | 24.7 | 59.4 | +0.0619 | +0.0164 | -0.0119 |

Delí sa len podľa vlastností, ktoré sú známe **pri vstupe** — inak by to nebol filter, ale pohľad dozadu.

## Drží to aj na iných trhoch?

Matica `20260910-123409-c27d` — 21 behov, okno `20240904-20250904`.

```
trh                      3m
---------------------------
COFFEE/USD           0.1031
COCOA/USD            0.0765
ETH/USD              0.0339
NGAS/USD             0.0246
US500/USD            0.0240
XAU/USD              0.0215
BTC/USDT:USDT        0.0079
EURUSD/USD           0.0045
USDJPY/JPY           0.0041
USDCAD/CAD           0.0034
GBPUSD/USD          -0.0007
GBPJPY/JPY          -0.0013
AUDUSD/USD          -0.0037
ETH/USDT:USDT       -0.0110
CHFJPY/JPY          -0.0161
WTI/USD             -0.0169
BTC/USD              odmiet
JP225/JPY            odmiet
DAX/EUR              odmiet
DJ30/USD             odmiet
NAS100/USD           odmiet
```

SLABE: break-even je nad poplatkom len na 2 z 16 trhov. Skor nahoda nez myslienka.

Prahy v absolútnych bodoch sa prepočítali na ATR referenčného trhu — bez toho by tabuľka nehovorila „na tomto trhu to nefunguje“, ale „profil je tam nezmysel“.

## Cena rizika

| riziko na obchod | zhodnotenie % | ročne (CAGR) % | max DD % | účet na nule |
|---|---|---|---|---|
| 0.2 % | -55.9 | -13.5 | 55.9 | nie |
| 0.5 % | -80.6 | -25.2 | 80.6 | nie |
| 1.0 % | -96.3 | -44.1 | 96.3 | nie |
| 2.0 % | -99.9 | -69.0 | 99.9 | nie |
| 3.0 % | -100.0 | -82.9 | 100.0 | nie |

| rok | obchodov | zhodnotenie % |
|---|---|---|
| 2021 | 41 | -33.8 |
| 2022 | 52 | -40.7 |
| 2023 | 46 | -37.0 |
| 2024 | 63 | -46.9 |
| 2025 | 85 | -57.4 |
| 2026 | 40 | -33.1 |

Nesie to jeden dobrý rok, alebo je to rozložené?

Korelácie mesačných výnosov: priemer **+0.99**, z 8 dvojíc je 8 nad hranicou vysokej korelácie. Portfólio má zmysel len vtedy, keď sa členovia nechovajú rovnako — inak je to jeden beh s väčšou pozíciou a drawdown sa neznižuje, len znásobuje.

> Dvojice behov, ktoré pokrývajú ten istý trh v tom istom čase — sú to alternatívy jednej veci, nie členovia portfólia:

> - 20260909-194704-5d0a03 × 20260909-194728-5d0a03 — NAS100/USD 20250904-20260904 x 20250904-20260904
> - 20260909-194704-5d0a03 × 20260909-194901-5d0a03 — NAS100/USD 20250904-20260904 x 20250904-20260904
> - 20260909-194704-5d0a03 × 20260909-195235-5d0a03 — NAS100/USD 20250904-20260904 x 20250904-20260904
> - 20260909-194704-5d0a03 × 20260909-195322-5d0a03 — NAS100/USD 20250904-20260904 x 20250904-20260904
> - 20260909-194704-5d0a03 × 20260909-195412-5d0a03 — NAS100/USD 20250904-20260904 x 20250904-20260904

TO NIE JE PORTFOLIO: 101 dvojic behov pokryva TEN ISTY trh v tom istom case (napr. NAS100/USD 20250904-20260904 x 20250904-20260904). Su to alternativy jednej veci, nie clenovia portfolia - to iste obdobie sa v sucte zapocitalo viackrat. Vyber behy z roznych trhov (matica trhov) alebo z roznych strategii.

Veľkosť pozície sa prepočítala z rizika (`riziko = zostatok × risk %`), nepreberá sa z behu — inak by sa sčítavali peňaženky, nie stratégie. Súbežné pozície sa nekrátia, takže je to horná hranica toho, čo by šlo.

## Na čo behy nestačili

Toto sa nespočítalo — radšej to nech chýba nahlas, než aby sekcia obsahovala číslo z jedného okna:

- **Nevyrába to náš backtest?** — na porovnanie treba aspoň 3 okná so behom na syntetickom trhu, sú 0. Dobehni ich: python -m tester.webapp.cli run --profile golden_coinbase_btcusd_3m --pair SYNTH/USDT:USDT --timerange <okno> --note "synteticky trh"

## Čo tento dokument nehovorí

- **Je to história, nie budúcnosť.** Všetko dole je popis toho, čo sa stalo. Ani jeden z testov nehovorí, že to tak bude ďalej.
- **Preoptimalizovanie sa z týchto čísel nezistí.** Obchody preladenej konfigurácie naozaj ziskové boli; chyba býva vo výbere najlepšej z dvesto epoch. Proti tomu chránia len dáta, ktoré optimalizátor nevidel — u nás päť referenčných okien.
- **Fill model je backtestový.** Beží sa s 1m detailom, takže sa vie, či prišiel skôr stop alebo take profit, ale sklz, čiastočné plnenie ani hĺbka trhu v tom nie sú.
- **Poplatok je jedno číslo.** Break-even hovorí, koľko smie burza brať; financovanie pozícií cez noc ani zmena sadzby v čase v ňom nie sú.

## Behy, z ktorých je to spočítané

| beh | trh | TF | okno | obchodov | poznámka |
|---|---|---|---|---|---|
| `20260909-194704-5d0a03` | NAS100/USD | 3m | 20250904-20260904 | 62 | tuneL2 |
| `20260909-194712-77e2d1` | NAS100/USD | 3m | 20230904-20250904 | 123 | tuneL2 |
| `20260909-194728-5d0a03` | NAS100/USD | 3m | 20250904-20260904 | 62 | tuneL2 |
| `20260909-194735-77e2d1` | NAS100/USD | 3m | 20230904-20250904 | 123 | tuneL2 |
| `20260909-194901-5d0a03` | NAS100/USD | 3m | 20250904-20260904 | 62 | tuneL2 |
| `20260909-194909-77e2d1` | NAS100/USD | 3m | 20230904-20250904 | 123 | tuneL2 |
| `20260909-195235-5d0a03` | NAS100/USD | 3m | 20250904-20260904 | 62 | tuneL2 |
| `20260909-195243-77e2d1` | NAS100/USD | 3m | 20230904-20250904 | 123 | tuneL2 |
| `20260909-195322-5d0a03` | NAS100/USD | 3m | 20250904-20260904 | 62 | tuneL2 |
| `20260909-195330-77e2d1` | NAS100/USD | 3m | 20230904-20250904 | 123 | tuneL2 |
| `20260909-195412-5d0a03` | NAS100/USD | 3m | 20250904-20260904 | 62 | tuneL2 |
| `20260909-195419-77e2d1` | NAS100/USD | 3m | 20230904-20250904 | 123 | tuneL2 |
| `20260909-195521-5d0a03` | NAS100/USD | 3m | 20250904-20260904 | 62 | tuneL2 |
| `20260909-195529-77e2d1` | NAS100/USD | 3m | 20230904-20250904 | 123 | tuneL2 |
| `20260909-195608-5d0a03` | NAS100/USD | 3m | 20250904-20260904 | 62 | tuneL2 |
| `20260909-195616-77e2d1` | NAS100/USD | 3m | 20230904-20250904 | 123 | tuneL2 |
| `20260909-195631-f8c925` | NAS100/USD | 3m | 20210103-20260904 | 341 | tuneL2 |
| `20260910-220626-0c05a9` | NAS100/USD | 3m | 20231001-20241001 | 57 | doplnenie okna 20231001-20241001 pre analytiku (podľa 202609 |
| `20260910-220626-68c2e6` | NAS100/USD | 3m | 20221001-20231001 | 55 | doplnenie okna 20221001-20231001 pre analytiku (podľa 202609 |
| `20260910-220626-cb296d` | NAS100/USD | 3m | 20240904-20250904 | 66 | doplnenie okna 20240904-20250904 pre analytiku (podľa 202609 |
| `20260910-220626-d68bad` | NAS100/USD | 3m | 20211001-20221001 | 52 | doplnenie okna 20211001-20221001 pre analytiku (podľa 202609 |
