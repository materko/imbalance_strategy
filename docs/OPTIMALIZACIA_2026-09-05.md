# Optimalizácia po opravách adaptéra: tri hypotézy na BTC a overenie na ETH (2026-09-05)

Východisko: profil `btcusdt_3m_binance_ny` po opravách z
[OPRAVY_adapter_2026-09-05.md](OPRAVY_adapter_2026-09-05.md) — 215 obchodov za päť
rokov, break-even 0,0879 % na stranu, +17,0 % s poplatkami.

Pravidlo z predchádzajúcich meraní ostáva: ladenie prahov na ~40 obchodoch ročne
overfituje, prežívajú len **binárne rozhodnutia s mechanizmom**. Každá hypotéza sa preto
najprv overila post-hoc na existujúcich obchodoch (rozdelenie do košov, po rokoch) a až
keď mala mechanizmus a znamienko sedelo naprieč rokmi, implementovala sa do enginu
a prebehla ako skutočný backtest.

## 1. Filter tesného SL — funguje

**Mechanizmus.** Hrubý zisk obchodu rastie s veľkosťou R (vzdialenosť SL), poplatok je
vždy percento z nominálu. Obchod s SL 0,1 % od vstupu má TP 0,5 % a platí rovnaký
poplatok ako obchod s SL 0,5 % a TP 2,5 %. Tesné SL teda majú najhorší pomer edge
k poplatku — a navyše ich šum vyráža častejšie.

**Post-hoc.** 215 obchodov NY profilu rozdelených na kvartily podľa `SL / vstup`:

| kvartil | medián SL | WR | priem. R | break-even |
|---|---|---|---|---|
| Q1 najtesnejší | 0,12 % | 18,5 % | +0,04 | **−0,0015 %** |
| Q2 | 0,21 % | 31,5 % | +0,36 | 0,0444 % |
| Q3 | 0,37 % | 37,7 % | +0,77 | 0,1476 % |
| Q4 najširší | 0,62 % | 48,1 % | +0,50 | 0,1736 % |

Najtesnejší kvartil je na nule **ešte pred poplatkami**. Vzťah je monotónny a struct
profil (494 obchodov, obe seansy) ukazuje to isté.

**Skutočný backtest.** Do enginu pribudlo pole `minSlDistance` (rozšírenie portu,
defaultne 0 = vypnuté, dôvod SKIP „SL PRILIS TESNY"). Odstránenie obchodu v engine
uvoľní miesto inému, takže čísla sa od post-hoc odhadu líšia — smer ale drží:

| prah | obchodov | hrubý zisk (1 BTC) | break-even | čistý len taker |
|---|---|---|---|---|
| bez filtra | 215 | +22 221 | 0,0879 % | +9 575 |
| 0,15 % | 175 | +21 285 | 0,1103 % | +11 636 |
| **0,20 %** | **149** | **+22 907** | **0,1410 %** | **+14 785** |
| 0,25 % | 125 | +22 414 | 0,1602 % | +15 416 |

O tretinu menej obchodov pri **rovnakom hrubom zisku** — filter odrezáva obchody,
ktoré nič nezarábajú, len platia. Povrch je plató, nie špička; 0,20 % je stred.

Po rokoch, prah 0,20 %:

| okno | obchodov | break-even pred → po | čistý s poplatkami pred → po | max DD |
|---|---|---|---|---|
| 2021-10 → 2022-10 | 28 | 0,2072 → **0,3109** | +11,09 → **+12,54 %** | 3,59 % |
| 2022-10 → 2023-10 | 34 | 0,0568 → **0,0592** | +1,83 → **+1,37 %** | 4,07 % |
| 2023-10 → 2024-10 | 37 | −0,0023 → −0,0075 | −3,37 → **−3,10 %** | 6,65 % |
| 2024-09 → 2025-09 | 28 | 0,0820 → **0,1572** | +1,48 → **+4,49 %** | 3,72 % |
| 2025-09 → 2026-09 | 22 | 0,1332 → **0,2349** | +5,92 → **+7,88 %** | 2,38 % |
| **spolu** | **149** | 0,0879 → **0,1410** | +17,0 → **+23,2 %** | max 7,1 → **6,7 %** |

Štyri z piatich rokov lepšie, piaty (2023-24) ostáva na nule v oboch verziách — ten rok
stratégia edge jednoducho nemá a filter na tom nič nemení. Break-even je teraz
**2,8-násobok** taker poplatku Binance.

So zmiešaným poplatkom (vstup limitkou ako maker, kde leží pod trhom; viď
[EXEKUCIA_maker_taker_2026-09-05.md](EXEKUCIA_maker_taker_2026-09-05.md)): podiel
maker vstupov stúpol z 52 % na 66 %, čistý za päť rokov +16 686 namiesto +11 937 USDT.

Profil: `ibs/configs/btcusdt_3m_binance_ny_sl.json`.

**Upozornenie.** Pri risk-based sizingu (`maxLossDollar`, nie 1 BTC) je efekt ešte
väčší, lebo tesný SL znamená väčší nominál a teda väčší poplatok pri rovnakom riziku.
Tu sa meralo s `legacyPineSizing`, aby boli čísla porovnateľné s predchádzajúcimi.

## 2. Regime filter z vyššieho TF — trend nie, volatilita možno

Post-hoc na tých istých 215 obchodoch, hodnoty z poslednej **uzavretej** hodinovej
resp. dennej sviečky pred otvorením obchodu:

| filter | skupina | n | break-even | roky so správnym znamienkom |
|---|---|---|---|---|
| 1h close > EMA50 | áno / nie | 132 / 83 | 0,050 / **0,160** | 3 z 5 |
| 1h close > EMA100 | áno / nie | 112 / 103 | 0,071 / 0,109 | 3 z 5 |
| 1h close > EMA200 | áno / nie | 112 / 103 | 0,093 / 0,081 | mieša sa |
| 1D close > EMA20 | áno / nie | 107 / 108 | 0,081 / 0,095 | mieša sa |
| včera zelený deň | áno / nie | 105 / 110 | 0,070 / 0,108 | mieša sa |
| **1h ATR v hornom kvartile (30 dní)** | áno / nie | 53 / 162 | **−0,003 / 0,116** | **3 z 5 záporné, 2 slabo kladné** |
| 1h ATR v dolnom kvartile | áno / nie | 32 / 183 | 0,024 / 0,099 | mieša sa |

**Trendové filtre zahadzujem.** Znamienko rozdielu sa mení rok od roka (napr. EMA50:
2022 lepšie „nad", 2023 lepšie „pod"), a keď už niečo, tak stratégia funguje lepšie
*pod* rýchlou EMA — je to mean-reversion na pullbacku, nie trend-following. Filter
„len v smere HTF trendu" by ju zhoršil.

**Volatilita je kandidát, nie záver.** V hornom kvartile ATR je edge nula (53 obchodov),
mechanizmus dáva zmysel (v prudkom pohybe sa gap neplní, ale prebehne), ale dva
z piatich rokov sú slabo kladné a je to už druhý filter na tých istých dátach —
každý ďalší zvyšuje riziko, že ladíme šum. Odložené: overiť samostatne, ideálne na
inom nástroji, skôr než sa implementuje.

## 3. Časový stop — nefunguje

Hypotéza z [HYPOTEZA_koniec_seansy_2026-09-04.md](HYPOTEZA_koniec_seansy_2026-09-04.md):
straty vznikajú v prvých 30 minútach, tak ich možno utnúť skôr. Meranie na 1m dátach:

| po N minútach | medián MAE víťazi | medián MAE porazení | víťazov s MAE < −0,5R | porazených |
|---|---|---|---|---|
| 5 | −0,20 R | −0,47 R | 19 % | 48 % |
| 15 | −0,27 R | −0,87 R | 29 % | 65 % |
| 30 | −0,32 R | −1,04 R | 33 % | 73 % |

Porazení síce klesajú hlbšie, ale **tretina víťazov je po 30 minútach tiež pod −0,5R**.
Politika „po N minútach zavri, ak si pod −kR" pre N ∈ {5…45} a k ∈ {0,3; 0,5; 0,7}:
najlepší variant dá +94,5 R proti +89,3 R baseline (+6 %) pri zásahu 21 obchodov,
susedné varianty sú horšie než baseline a poradie po rokoch je náhodné. Nie je tu nič,
čo by prežilo — víťazi a porazení sa skoro oddeliť nedajú.

## 4. Overenie na ETH/USDT.P — obe zistenia prežili

`main` medzitým dostal celé ETH/USDT futures dáta a profil `ethusdt_3m_binance_ny`
(tá istá stratégia, prahy prepočítané na ATR — viď komentár v profile). Na ETH sa
**nič neladilo**: NY seansa aj prah `minSlDistance 0,20 %` sú prevzaté z BTC. Je to
teda skutočný out-of-sample test na inom nástroji, nie na inom roku toho istého.

Break-even (% na stranu), bez poplatkov, `--pairs ETH/USDT:USDT`:

| okno | bez filtra | | s filtrom 0,20 % | |
|---|---|---|---|---|
| | obchodov | break-even | obchodov | break-even |
| 2021-10 → 2022-10 | 29 | 0,0403 | 26 | **0,0612** |
| 2022-10 → 2023-10 | 50 | 0,0402 | 36 | **0,1085** |
| 2023-10 → 2024-10 | 43 | 0,0680 | 33 | **0,1224** |
| 2024-09 → 2025-09 | 45 | 0,0668 | 42 | 0,0658 |
| 2025-09 → 2026-09 | 36 | 0,0702 | 27 | **0,1342** |
| **spolu** | **203** | **0,0561** | **164** | **0,0957** |

**NY seansa má edge aj na ETH** — kladný vo všetkých piatich rokoch, hoci menší než na
BTC (0,056 % proti 0,088 %) a tesne nad taker poplatkom. Rok 2023-24, ktorý je na BTC
nulový, je na ETH normálny; slabý rok teda nie je vlastnosť stratégie, ale trhu.

**Filter tesného SL funguje aj na ETH**: štyri roky lepšie, piaty rovnaký, žiadny horší,
a opäť pri **rovnakom hrubom zisku** (+794 proti +751 USDT pri 1 ETH). Odreže menej
obchodov než na BTC (19 % proti 31 %), lebo ETH má širšie stopy (medián SL 0,43 %
ceny proti 0,28 %). Najtesnejší kvartil je aj tu na nule (−0,001 %).

S poplatkami 0,05 %: bez filtra 3 z 5 rokov ziskové (−0,18 / −0,40 / +0,43 / +0,40 /
+0,54 %), s filtrom **5 z 5** (+0,13 / +0,71 / +1,30 / +0,35 / +1,18 %). Percentá sú
malé, lebo `legacyPineSizing` dáva na ETH pozíciu 1–2 ETH (~3 000 USDT) na účte 10 000;
porovnateľné číslo je break-even, nie percento.

Profil: `ibs/configs/ethusdt_3m_binance_ny_sl.json`.

**Volatilitný filter sa na ETH nepotvrdil.** Horný kvartil hodinovej ATR má na ETH
break-even −0,047 %, ale po rokoch −0,34 / **+0,21** / −0,21 / −0,01 / **+0,07** — dva
z piatich rokov výrazne kladné, rovnako ako na BTC. Šesť z desiatich nástroj-rokov
záporných nie je mechanizmus, je to hod mincou s ťažkými chvostmi. Zahadzujem.

## Kde to sme

| krok | BTC break-even | BTC obch./rok | ETH break-even | ETH obch./rok |
|---|---|---|---|---|
| RR 5, štruktúra, bez trailingu, obe seansy | 0,0423 | 96 | — | — |
| + len NY seansa | 0,0879 | 43 | 0,0561 | 41 |
| **+ minSlDistance 0,20 %** | **0,1410** | **30** | **0,0957** | **33** |
| *Binance taker* | *0,0500* | | *0,0500* | |

Každý krok zdvojnásobil edge tým, že odobral obchody, nie že pridal. Tridsať obchodov
ročne je málo na štatistiku a veľa na to, aby jeden zlý rok (2023-24) zmizol — ten
ostáva na nule vo všetkých verziách.

## Čo ďalej

1. ~~Iný nástroj~~ — hotové, viď bod 4. Obe zistenia prežili.
2. ~~Volatilitný filter~~ — na ETH sa nepotvrdil, zahodený.
3. **Risk sizing.** `maxLossDollar 350` na 10k je 3,5 % na obchod; na nasadenie 1 %.
   Edge nemení, drawdown áno. S `minSlDistance` sa navyše zúži rozptyl nominálu medzi
   obchodmi, takže risk-based sizing prestane robiť extrémne pozície pri tesnom SL.

## Ako to zopakovať

```bash
IBS_PROFILE=btcusdt_3m_binance_ny_sl .venv/Scripts/python.exe -m freqtrade backtesting \
  --config platforms/freqtrade/config.binance.json \
  --userdir platforms/freqtrade/user_data --strategy IBSImbalanceStrategy \
  --timeframe-detail 1m --timerange 20250904-20260904 --cache none
```

Pre break-even pridaj `--fee 0 --dry-run-wallet 400000` a `python -m ibs.tools.fees`.
