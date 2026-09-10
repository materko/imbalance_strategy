# Syntetický trh: chytáme sa vlastného backtestu? — 2026-09-10

Prvé použitie `tester.synthetic`. Otázka nie je „zarába stratégia", ale **„nevyrába tú
výhodu náš backtest?"** — pohľad dopredu, fill model, ktorý sporné bary rozhoduje v náš
prospech, sizing, ktorý zvýhodňuje výhry. Také chyby na skutočných dátach vyzerajú ako
zisk a nič iné v repozitári ich nechytí.

## Ako sa robil trh

Vzali sa **skutočné 1m bary BTC/USDT:USDT** (2021-10 → 2026-09), zapamätal sa tvar každého
baru a **výnosy sa premiešali po blokoch po 60 barov**. Trh je pevný: recept je
v `tradebot/core/instruments_synthetic.json` (seed 20260910, sha256
`b29861a145e0…`) a dá sa z neho vygenerovať bit po bite ten istý.

Čo sa zachovalo presne:

| | BTC 1m | syntetický |
|---|---|---|
| σ výnosu 1m | 0,000747 | 0,000747 |
| špicatosť | 129,8 | 129,8 |
| zhluky volatility (autokorelácia \|r\|) | 0,3899 | 0,3819 |
| konečná cena | 81 230,70 | 81 230,70 |

Rozdelenie výnosov je tá **istá množina čísel**, len v inom poradí — preto sedí aj celkový
drift. Zmizlo len **poradie**.

## Výsledok: engine si nič nevymýšľa

Profil `btcusdt_3m_binance_ny_sl_risk1` na piatich referenčných oknách:

```
okno                 BTC break-even    SYNTH break-even
20211001-20221001         +0.0917           +0.1104
20221001-20231001         +0.0874           -0.0597
20231001-20241001         +0.1210      (0 obchodov)
20240904-20250904         +0.1644           -0.1789
20250904-20260904         +0.1071           +0.1109
                     kladné 5 z 5      kladné 2 zo 4
```

**Na syntetickom trhu edge nie je.** Znamienka sa striedajú a čísla sa motajú okolo nuly —
presne to, čo tam má vyjsť. Keby vyšli súvisle kladné, bol by to nález o nás.

Za povšimnutie stojí, že jedno okno syntetického trhu dalo **+0,1104**, teda viac než to
isté okno na skutočnom BTC. Pri šestnástich obchodoch to nič neznamená — a je to dobrá
pripomienka, prečo sa jedno okno nikdy nečíta samo.

## Vedľajší nález, ktorý je zaujímavejší než hlavný

Signálov je na oboch trhoch rovnako, ale **obchodov nie**:

```
okno                 trh       signálov  obchodov   fill
20211001-20221001    BTC             32        30    94 %
20221001-20231001    BTC             40        34    85 %
20231001-20241001    BTC             37        35    95 %
20240904-20250904    BTC             36        29    81 %
20250904-20260904    BTC             29        21    72 %

20211001-20221001    SYNTH           28        16    57 %
20221001-20231001    SYNTH           37        21    57 %
20231001-20241001    SYNTH           31         0     0 %
20240904-20250904    SYNTH           28         5    18 %
20250904-20260904    SYNTH           42         9    21 %
```

Na skutočnom trhu sa vyplní **72–95 %** signálov, na premiešanom **0–57 %**.

Vysvetlenie, ktoré tomu sedí (a je zatiaľ **hypotéza**, nie zmeraný fakt): stratégia
vstupuje **limitkou na úrovni medzery**, takže obchod vznikne len vtedy, keď sa cena na tú
úroveň vráti. Na skutočnom trhu sa vracia — to je štruktúra. Na premiešanom sa cena po
signáli vydá náhodne a úroveň často už nikdy nenavštívi.

Ak to tak je, je to **argument pre stratégiu**: jej vstup stojí na tom, že úrovne niečo
znamenajú, a nie na tvare jednej sviečky. Overiť sa to dá tak, že sa porovná, ako ďaleko
od signálu sa cena vzdiali, kým limitka čaká — na oboch trhoch.

## Čo toto meranie nehovorí

- **Nedokazuje, že stratégia zarába.** Hovorí len, že to, čo na skutočných dátach
  namerala, nevyrobil backtest sám od seba.
- **Záporné čísla na syntetickom trhu nič nedokazujú** — poplatky a spread berú aj tam.
- **Okno `20231001-20241001` sa nedá použiť**: 31 signálov, 0 obchodov, a to aj
  s peňaženkou 40 miliónov. Podľa hypotézy vyššie je to krajný prípad nevyplnených
  limitiek, ale istota to nie je — patrí sa to pozrieť samostatne.
- Trh je **jeden**. Nie je to Monte Carlo cez veľa náhodných trhov; je pevný zámerne, aby
  sa dva výsledky dali porovnať. Na otázku „aký široký je rozptyl náhody" odpovedá
  `tester.montecarlo` a `tester.nulltest`.
