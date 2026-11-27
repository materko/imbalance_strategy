# Agent A (Prokurátor) — rozdelenie rokov len z dát, ktoré máme

*26. 11. 2026, len čítanie. Overené v `tradebot/strategies/*/docs`, `.nightsearch/glsearch.py`,
`OOS-STARE-ROKY/data/oos_all.tsv` (145 behov, 57 kľúčov) a v iCloud priečinkoch SP500-ES, EUR-PRIESKUM,
M2-METODA2, ROBOQUANT-SABLONY, ZLATO-PRIESKUM, NASDAQ-STUDIUM, BTC-PRIESKUM.*

## 1. Výnimky: dve chyby od koordinátora potvrdzujem a pridávam ďalšie
| kľúč | návrh B | čo som našiel | verdikt |
|---|---|---|---|
| `sdeur` | ✅ (B 6E 2016–21) | `sdeur/docs/ANALYTIKA.md:179`: „Predbežný výskum (2011–2026, zóny bez pohľadu dopredu) … 2011–2015 jasne v pluse“ | **🟡**, celé 6E videné |
| `noaes` | ✅ (B ES 2010–21) | `base_noa.json`: „presne podľa Zarattini, Aziz, Barbon (2024)“, autori videli SPY 2007–2024 | **🟡**. Čisté by bolo len obdobie po publikácii (6/2024+), ktoré je pre `noaes` L/A |
| `flashorbes` | ✅ | ROBOQUANT-SABLONY/ZOZNAM.md #7: šablóna. **Rodina Flash ORB** je v triedení (`flashorb`, `flashorbbtc` v `oos_all.tsv`) na MNQ 2019–21, ktoré s ES 2019–21 silno koreluje. SP500-ES/PRECITAJ_MA.md:50, 72–76: výskum meral ORB/momentum na US500 **2015–2020** | ✅ možné len na **ES 2010-06-06 – 2014-12-31** |
| `nqpreces` | ✅ | šablóna #5. Rodina v triedení (`nqprecmgc`, MGC 2020–21) je iný trh. ORB typ zasahuje SP500-ES 2015–20 | ✅ možné len na **ES 2010-06-06 – 2014-12-31** |
| `m2` | ✅ | rodina M2 v triedení (`m2mnq`, MNQ 2019–21). M2-METODA2/PRECITAJ_MA.md: „ES 1m PF 0,80–0,90 … pred poplatkom ~1,03“ | trezor zbytočný, **❌ už v kroku 3** (PF < 0,95). Keby nie, len ES 2010–2018 |
| `m2eur` | ✅ (6E 2016–21) | v triedení nebola. Rodina M2 je inde pod 1 | rovnako: krok 3 rozhodne skôr než trezor. Formálne ✅ možné |

**Nový nález, ktorý mení celé rozdelenie:** podľa V2 §0 spáli štúdia trhu obdobie, ktoré videla, pre všetky
hypotézy, ktoré z nej vychádzajú. Štúdie videli:
- **SP500-ES:** US500 2015–2026 (riadok 50: „2021 – 8/2026, kontrola 2015–2020“) a ES 2019–2026 (riadok 125:
  `SETS=ES:2019:2026`),
- **EUR-PRIESKUM:** „Charakter trhu (6E 2021–2026)“. Odtiaľ je mean reversion, okná London/NY a poradie
  kandidátov,
- **NASDAQ-STUDIUM, prieskum `nocpon`:** MNQ 2019–2026 (súhrn výskytov 2019–2026, 2020–2026),
- **ZLATO-PRIESKUM/TRH_MGC.md:28:** „MGC a MNQ, Databento 1m, 2020 – 2026/09“,
- **BTC-PRIESKUM:** obdobie som nedokázal priradiť (hypotéza: 2019–2026).

## 2. Princíp, na ktorom sa podľa mňa musíme dohodnúť
**DOHODA:** „Hlavička hypotézy vymenuje štúdie a výskumy, z ktorých vychádza. Trezor musí ležať mimo obdobia
každej z nich aj mimo všetkých behov rodiny. Ak taký úsek nie je ≥ 2 roky a ≥ 300 obchodov, hypotéza dostane
najviac 🟡 (WF + C).“

Druhá DOHODA: **jedno rozdelenie na trh**, nie dva varianty (M1/M2, K1/K2, G1/G2). Pri dvoch variantoch si autor
vyberie ten, ktorý mu vyjde. Varianty sa navyše prekrývajú a kumulatívne počítanie hypotéz na trezore (V2 8b) sa
rozpadne.

## 3. Po trhoch (všetky dátumy z dát, ktoré máme)

### ES: protinávrh
Jediný blok, ktorý nevidela žiadna štúdia ani triedenie (to bežalo len na rodinách z `oos_all.tsv`), je
**2010-06-06 – 2014-12-31**.

| oblasť | dátumy | roky | obch. 100 / 150 |
|---|---|---|---|
| trezor B | **2010-06-06 – 2014-12-31** | 4,6 | 460 / 690 |
| L + WF 24/6 (~17 kúskov) | **2015-01-01 – 2025-09-03** | 10,7 | 1 070 / 1 600 |
| A · C | 2025-09-04 – 2026-09-03 · od commitu | | |

- Prečo nie Inžinierove L 2010–17 / B 10/2017–9/2021: jeho trezor leží v obdobiach SP500-ES (2015–20, ES 2019+).
  Každá hypotéza poskladaná „podľa výskumu ES“ by ho mala spálený.
- Režim v trezore: kríza eura 2011 (ES −19 %), QE, nízke ceny a iná mikroštruktúra. Treba ho zmerať (ATR kvartál
  mimo IQR L). Ak meranie nevyjde, trezor nestačí a hypotéza dostane 🟡.
- Výhrada (B): staré roky sú menej podobné dnešku. Pre trezor je to sila, nie slabosť, lebo testuje prenos.
- Legacy z triedenia → 🟡. `flashorbes`, `nqpreces` → trezor 2010–14. `noaes` → 🟡. `m2` → krok 3.

### MNQ: súhlas s M1, s podmienkami
- L **2019-05-05 – 2022-09-30** (3,4 r, WF 18/6 = 3–4 kúsky), B **2022-10-01 – 2025-09-03** (2,9 r).
- L sa nebojím, že by bolo jedným režimom: obsahuje covid, býka 2021 aj medveďa H1 2022 (NQ ~−35 %). Je bohatšie
  na režimy než trezor.
- Trezor má nízku volatilitu 2023–24 a apríl 2025. Iný režim pravdepodobne splní cez ATR, treba ho zmerať.
- **WF 18/6 s 3–4 kúskami je len negatívny filter.** Dôkaz nesie trezor. Hranica ✅ pri kumulatívnom t_req (V2 8b,
  dnes ≥ 3 hypotézy → t ≥ 2,6) a ~300 obchodoch znamená **PF ≳ 1,35 po nákladoch**. Napíšme to do smernice číslom,
  nech nikto nečaká, že prejde PF 1,2.
- **Platí len pre hypotézy, ktoré nevychádzajú z NASDAQ-STUDIUM ani z prieskumu `nocpon`** (obe videli 2019–26).
  Ostatné → 🟡.
- Legacy → 🟡. Rodiny, ktoré na 2019–21 nikdy nebežali → B 2019-05-05 – 2021-09-30 (2,4 r), ✅ pri ≥ 125 obch/rok.

### MYM: súhlas
- Denné stratégie majú dátumy ako MNQ.
- Nočné stratégie → 🟡. Noc 2019 má pokrytie 86,5 % a 2024 94,8 %. Vyraďovanie jednotlivých dní je výber dát,
  preto ho nepovoľujem.

### MGC: protinávrh, otočiť poradie
Inžinierov G1 (L 2020–22, B 2023–9/2025) má trezor, ktorý je **jeden býk (+80 %)**. Pravidlo „aspoň jeden iný režim“
nesplní a stratégia s longmi v ňom len zbiera rast.

| oblasť | dátumy | roky | obch. 100 / 150 |
|---|---|---|---|
| L + WF 18/6 (2–3 kúsky) | **2023-01-01 – 2025-09-03** | 2,7 | — |
| trezor B | **2020-01-01 – 2022-12-31** | 3,0 | 300 / 450 |

- Trezor potom obsahuje covid, vrchol 8/2020, pokles 2021–22 (~−20 %) a rangeový trh. Je to presne režim, ktorý L
  (býk) nemá: pokles > 15 %, ktorý v L nebol. Pravidlo je splnené merateľne.
- Cena: L je len 2,7 roka a WF je slabý, takže je len negatívny filter. Plus povinný test kúp a drž.
- **ZLATO-PRIESKUM videl 2020–9/2026** → hypotézy z neho → 🟡. Legacy → 🟡.

### 6E: protinávrh, otočiť poradie
EUR-PRIESKUM vybral kandidátov podľa správania **2021–2026**. Inžinierov trezor 10/2021 – 9/2025 je preto spálený
pre všetko, čo z výskumu vychádza, teda takmer pre všetky nové EUR nápady.

| oblasť | dátumy | roky | obch. 100 / 150 |
|---|---|---|---|
| L + WF 24/6 (3–4 kúsky) | **2021-10-01 – 2025-09-03** | 3,9 | — |
| trezor B | **2016-01-03 – 2021-09-30** | 5,75 | 575 / 860 |

- Režimy: trezor má nízku FX volatilitu 2017–19, Brexit a covid. L má rast sadzieb 2022 a paritu, čo je jasne
  iný režim.
- Výnimky: EUR_KEYS ladené na 2016–21 aj `sdeur` (2011–26) → 🟡. `m2eur` ✅ formálne možné.

### BTC: súhlas s K1, K2 zrušiť
- L **2019-09-08 – 2022-09-30** (3,1 r: covid, bublina 2021, LUNA, Celsius), B **2022-10-01 – 2025-09-03**
  (2,9 r: FTX 11/2022, zotavenie 2023, býk po ETF, apríl 2025).
- Svoj skorší návrh (L 2019–23 / B 2023–25 = K2) beriem späť: K1 má v trezore viac režimov aj obchodov.
- Platí len pri ≥ 105 obch/rok a len pre hypotézy mimo BTC-PRIESKUM (obdobie treba overiť). Legacy BTC → 🟡.
- **Náklad podľa miesta obchodovania** (CFD vs. Binance) platí naďalej.

## 4. Čo z toho plynie (na dohodu)
1. Čistý trezor z dát, ktoré máme, existuje pre **ES 2010–14** (hypotézy mimo triedených rodín), **6E 2016–21**,
   **MGC 2020–22**, **MNQ/MYM a BTC 10/2022 – 9/2025**. Vždy len pre hypotézy, ktoré nestoja na štúdiách daného
   trhu.
2. **Všetky dnešné stratégie (legacy) a všetko odvodené zo štúdií → najviac 🟡.** Rozhodne WF + C. Smernica to má
   povedať otvorene.
3. ✅ na MNQ, MYM, BTC a MGC je reálne len pri PF ≳ 1,35 po nákladoch. Na ES a 6E pri PF ≳ 1,25 (viac obchodov
   v trezore).
4. Hlavička hypotézy bez zoznamu použitých štúdií = automat ju nepustí (kontrola v registri).
