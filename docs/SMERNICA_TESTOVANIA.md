# SMERNICA V2 — testovanie a schvaľovanie stratégií

*Verzia z 27. 11. 2026: debata Agent A (Prokurátor) a Agent B (Inžinier), finálna kontrola Agent C (Kontrolór, `16_C`),
opravy Z1–Z10 zapracované. **Schválil a podpísal používateľ 27. 11. 2026 — platí od tohto dňa.** Nahrádza `SMERNICA_TESTOVANIA.md` (iCloud aj `docs/`), `SMERNICA_TREND_CFD.md` aj „krok 12
starých rokov“. Podklady sú v `.nightsearch/kritika/01–21`. Otvorené otázky pre používateľa sú v §9.*

## ⛔ Čo nám chýba, aby smernica vôbec fungovala (stav 27. 11. 2026)
| chýba | dôsledok | kto |
|---|---|---|
| NQ, YM, GC 2010+ (máme len MNQ/MYM od 2019, MGC použiteľné od 2020) | **nie je blokér** — §1 má rozdelenie z dát, ktoré máme (kratšie ladenie, slabší dôkaz); legacy bez čistého trezoru okrem C | stiahnutie len voliteľne, rozhoduje používateľ |
| denný stop účtu −4 % v EA a NT (krok 12) | nič nové nesmie ísť naživo | vývoj |
| register pokusov, walk-forward, PBO/DSR brány, fill v2 (§2–4, §10) | automat dnes beží podľa starej smernice | vývoj |
| **počiatočné k trezorov** (`vaults.json` z histórie rodín, štúdií a triedenia) | trezor sa nesmie otvoriť | vývoj |
| **`checkup` len na L** (dnes počíta na referenčných oknách = trezory MNQ/MYM/BTC/6E) | každá analytika otvorí trezor | vývoj |
| **SI, 6B, DAX, Nikkei futures** (krok 8c; DAX/Nikkei máme len ako Dukascopy CFD, ktoré používateľ vylúčil) | negatívny test na príbuznom trhu ide len pre MNQ ↔ ES ↔ MYM a BTC ↔ ETH perp; **zlato a 6E majú najviac 🟡** | stiahnutie schvaľuje používateľ |
| **bid/ask v EA** (spread CFD, krok 3 a 11) | náklad CFD sa nedá zmerať, len odhadnúť | vývoj |
Rozdelenie dát (§1) je použiteľné na všetkých šiestich trhoch. **✅ je dnes reálne len na ES.** MGC a 6E majú bez SI/6B najviac 🟡;
MNQ, MYM, BTC a 6E majú trezor v oknách, na ktorých sa ladilo všetko, takže k ≈ 160, t_req ≈ 3,6 (PF ≳ 1,65 pri ~210 obchodoch).

## Čo sa mení oproti dnešnej smernici (v skratke)
1. **Odložený rok 2025/26 je spálený.** Púšťal sa > 2 300-krát a radilo sa podľa neho. Odteraz je to len negatívna
   kontrola a nikdy sa podľa neho nezoraďuje.
2. **Rozpočet 300 konfigurácií a ≤ 5 parametrov na hypotézu.** Všetky kópie, trhy a filtre sa počítajú
   spolu; hypotéza zo štúdie ide cestou kroku 10 (najviac 🟡). Dnes je to až 82 000 pokusov na stratégiu.
3. **Trezory sa otvárajú raz** a s hranicou zapísanou vopred. Prah t rastie s počtom hypotéz, ktoré trezor kedy
   videli.
4. **DSR, PBO a haircut sú brány**, nie informácia. Walk-forward je povinný a otvára sa len raz.
5. **Plnenie príkazov (body, §3):**
   - **Futures:** limit a TP sa plnia až pri prechode o 1 tick (MNQ/ES 0,25 b, MYM 1 b, MGC 0,10 $, 6E 0,5 pipu);
     sklz na SL, stop vstup a market MNQ/MYM +2 ticky (0,5 b / 2 b), ES a MGC +1 tick, 6E +0,5 ticku.
   - **CFD (graf = bid):** predaj sa spustí pri prechode bidu o 0,25 b (US100) / 0,05 b (US500) / 0,05 $ (XAU),
     nákup až keď bid prejde o celý spread (US100 2,0 b, US500 0,8 b, XAU 0,40 $). Sklz SL US100 1,0 b, US500 0,3 b,
     XAU 0,25 $; market 0,5 b / 0,3 b / 0,15 $. NY open spread ×2, správy ×4–5. Limit za trhom sa neplní.
   - Zlepšenie ceny sa nikdy nepočíta. SL aj TP v jednej minúte → SL.
6. **Prop riziko sa počíta z equity** (MAE, typ DD účtu, súčasné riziko ≤ 1,5 %). **Denný stop účtu −4 %** je priamo
   v EA a NT a funguje aj bez hubu; celkový stop sa nedáva (používateľ 27. 11.).
7. **Demo a ostrá prevádzka si stráži používateľ** (zrušené kroky dema a vypínania, používateľ 27. 11.).
8. **Webapp ukazuje stav a očakávanie po haircute.** Vedľa PF a WR vždy aj **PF po haircute, DSR, PBO a výsledok na iných trhoch**; posledný rok len ako kontrola (§5). ✅ zapisuje len skript z registra
   a prechody stavov podpisuje používateľ.
9. **Zachované bez zmeny:** krok 1 (naživo = história), C# parita, 1m detail, SL pred TP, kontrola dát. `checkup` ostáva, ale **len na L**.
10. **Rozdelenie rokov na trh je pevné (§1), jedno, a trezor leží mimo štúdií.** Minimum ≥ 75 obchodov v každom roku ladenia; v trezore
    rozhoduje t ≥ t_req, nie pevný počet (🟡 od 150, ✅ od 200). Sortino ≥ 1,0 len z WF OOS a trezorov.
11. **Smernica je jedna**, `docs/SMERNICA_TESTOVANIA.md` v repe. iCloud obsahuje len odkaz.

**Čo sa dá od V2 čakať:** číslo, ktoré V2 ukáže ako „očakávanie“, je už očistené o výber, náklady a fill. Naživo
očakávame PF zhruba ±0,1 okolo neho, nie 1,5–1,8 z dnešných titulov. Prejde málo stratégií, a tak to má byť.

---

## 0. Pojmy a nemenné pravidlá

- **Hypotéza** = jedna obchodná myšlienka. Jej trhy, kópie (`…net`, `…eod`, `…mym`, `…es`, `…mgc`, `…btc`, `…eur`),
  filtre a varianty majú **jeden** register a **jeden** rozpočet.
- **Pokus** = každý beh na dátach, ktorý mohol ovplyvniť výber: mriežka, hyperopt, `glwr`/`glrr`, ručný beh,
  susedia v plató, zmena kódu po pozretí výsledkov.
  - **Každá štúdia alebo prieskum** (KLZAKY-STUDIA, EUR-PRIESKUM, výskum SPRÁV, prieskum Nasdaqu…) je pokus a
    **spáli obdobia, ktoré videla**, pre všetky hypotézy, ktoré z nej vzídu.
- **Trezor** = obdobie mimo výberu. Otvára sa **raz na hypotézu**, s hranicou commitnutou vopred, a **nikdy sa podľa
  neho nezoraďuje**.
- **Zmrazenie** = commit pred prvým behom (hlavička, mriežka, hranice). Zmena znamená novú hypotézu.
- **Po živej strate sa na tom období nič neladí.** Buď vypnúť, alebo pokračovať bez zmeny.
- **Stav mení len skript z registra.** Prechody ⏳ → 🟡 demo → ✅ → ostré **podpisuje používateľ** (zápis v registri
  s dátumom). AI agent stav nikdy nemení sám.
- **Obmedzenia používateľa:**
  - RR ani čiastočné výbery nikdy pod 0,5,
  - na MacBookoch sa nepočíta (len Mac mini a hub bez MACBOOK*),
  - Pine nejde do repa,
  - bez trailingu a konca seansy v hľadaní, pokiaľ hypotéza výslovne nehovorí inak.
- Backtest ide vždy cez `python -m tester.webapp.cli …`, s 1m detailom (nikdy na 1m grafe), `--note`, emulátorom
  MultiCharts alebo C# jadrom.

---

## 1. Rozdelenie dát a trezory

**Platné rozdelenie — len z dát, ktoré máme** (schválil používateľ 26. 11. 2026; overené proti súborom
`data/archive/tester/`; **takto sa testuje vždy**, zmena len novým zápisom s dátumom a súhlasom používateľa).
Každý trh má vlastné rozdelenie. Rok A je všade spálený (len negatívna kontrola), C = nové dáta od commitu hraníc (backtest na čerstvých mesiacoch z
`bento_import`); demo a ostrú prevádzku si stráži používateľ.

- **Jedno rozdelenie na trh, žiadne varianty** (návrh A v kole 13, schválil používateľ 27. 11.). Pri dvoch variantoch si autor vyberie ten, ktorý
  mu vyjde, a kumulatívne k na trezore (8b) prestane platiť.
- **Trezor mimo štúdií (návrh A v kole 13, schválil používateľ 27. 11.):** hlavička hypotézy vymenuje štúdie a výskumy, z ktorých vychádza.
  Trezor musí ležať mimo obdobia každej z nich aj mimo všetkých behov rodiny. Ak taký úsek nemá ≥ 2 roky a ≥ 150 obchodov,
  hypotéza dostane najviac **🟡** (rozhodne WF + C). Hlavička bez zoznamu štúdií = automat ju nepustí.
  Obdobia štúdií, ktoré máme (overené 26. 11., opravené podľa C 27. 11.):

  | štúdia (iCloud) | videla |
  |---|---|
  | SP500-ES | US500 2015–2026, ES 2019–2026 |
  | EUR-PRIESKUM | 6E 2016–2026 (charakter trhu 2021–2026) |
  | NASDAQ-STUDIUM, prieskum `nocpon` | MNQ 2019–2026 |
  | ZLATO-PRIESKUM | MGC 2011–9/2026 (TRH_MGC 2020–9/2026, ďalšie časti 2011–2025) |
  | BTC-PRIESKUM | Dukascopy 2017–2026 **a Binance perp 9/2019–9/2026** (teda aj trezor BTC) |
  | KLZAKY-STUDIA | ES a MGC od 2016, MNQ, MYM, BTC od začiatku dát |
  | triedenie starých rokov (26. 11.) | ES 7/2010–9/2021, MNQ/MYM 2019–9/2021, MGC 1/2020–9/2021 (11 rodín) |
  | **referenčné okná ladenia** (`tester/hyperopt.py:56`, `glsearch`, `checkup`) | 10/2021–9/2026 na všetkých trhoch — všetky legacy rodiny |

  Z toho: hypotézy odvodené z týchto štúdií majú na danom trhu najviac 🟡. Čistý trezor majú len hypotézy, ktoré na
  štúdiách trhu nestoja.

| trh (súbor) | ladenie + walk-forward | trezor B (skrytý, raz na hypotézu) | A spálený | čo unesie |
|---|---|---|---|---|
| **ES** (Databento) | **2015-01-01 – 2025-09-03** · 10,7 r · WF 24/6 | **2010-06-06 – 2014-12-31** · 4,6 r · ~460 obch pri 100/rok | 2025-09-04 – 2026-09-03 | ✅ reálne (jediný trh). **Zmenené 27. 11. (Z7, schválil používateľ):** trezor 10/2017–9/2021 ležal v SP500-ES a KLZAKY; 2010–14 videlo len triedenie (~10 profilov → k ≈ 10, t_req ≈ 2,8, pri ~460 obch PF ≳ 1,3). Iný režim (ATR 2011) treba pred otvorením zmerať, bez merania ⏳ |
| **6E** (Databento, len 2016+) | 2016-01-03 – 2021-09-30 · 5,75 r · WF 24/6 | 2021-10-01 – 2025-09-03 · 3,9 r · ~390 | to isté | **najviac 🟡**, kým nie je 6B (8c). Trezor = 4 z 5 referenčných okien → prísne počiatočné k; hypotézy z EUR-PRIESKUM 🟡 |
| **MNQ** (Databento) | 2019-05-05 – 2022-09-30 · 3,4 r · WF 18/6 | 2022-10-01 – 2025-09-03 · 2,9 r · ~290 | to isté | ✅ pri ≥ 200 obch a t ≥ t_req. Trezor = 3 referenčné okná → počiatočné k ≈ 160, t_req ≈ 3,6 → pri ~210 obch PF ≳ 1,65; inak 🟡 |
| **MYM** (Databento) | 2019-06-02 – 2022-09-30 · 3,3 r · WF 18/6 | 2022-10-01 – 2025-09-03 · 2,9 r | to isté | denné ako MNQ; **nočné len 🟡** (noc 2019 a 2024 < 95 %) |
| **BTC** (Binance perp) | 2019-09-08 – 2022-09-30 · 3,1 r · WF 18/6 | 2022-10-01 – 2025-09-03 · 2,9 r · ~290 | to isté | ako MNQ (k ≈ 160, PF ≳ 1,65); trezor videl aj BTC-PRIESKUM → hypotézy z neho 🟡; 8c na ETH perp |
| **MGC** (Databento, len 2020+) | **2023-01-01 – 2025-09-03** · 2,7 r · WF 18/6 (2–3 kúsky, len negatívny filter) | **2020-01-01 – 2022-12-31** · 3,0 r · ~225 pri 75/rok | to isté | **najviac 🟡**, kým nie je SI (8c); lepšie než kúp a drž. Trezor videlo triedenie (11 rodín 1/2020–9/2021), SPRÁVY a ZLATO-PRIESKUM → počiatočné k. **Obrátené 27. 11. (návrh A, schválil používateľ):** 2023–25 je jeden býk (+80 %), trezor 2020–22 má covid, vrchol 8/2020, pokles ~−20 % a range — iný režim splnený merateľne |

- **Počiatočné k trezoru (Z2; predvolene prísne, §9):** pred prvým otvorením sa do `vaults.json` zapíše počet rodín
  a kópií (`tradebot/strategies`), štúdií a triedení, ktoré na danom období kedy bežali. Kým to nie je spočítané a commitnuté,
  trezor sa neotvára. Na MNQ, MYM, BTC a 6E je to dnes najviac ~160 (prísny horný odhad, všetky kľúče; t_req ≈ 3,6), na ES 2010–14 ~10. Štúdia sa do k ráta ako jedna hypotéza
  na každom trezore, ktorého obdobie videla (jej počet behov ide do N pre DSR, nie do k).
- **Daň za kompromis (MNQ, MYM, BTC, MGC):** ladenie len ~3 roky (bližšie jednému režimu), walk-forward len 3–4 kúsky,
  trezor v jednom bloku. Hlavný dôkaz je tam walk-forward + trezor + **C aspoň 2 roky**.
- **Dnešné stratégie (legacy, ladené 10/2021 – 9/2025, staré roky spálené triedením 26. 11.):** v dátach, ktoré máme,
  **nemajú čistý trezor** → najviac **🟡** (demo, malá veľkosť); ✅ najskôr z C (≥ 2 roky, ≥ 200 obchodov a t ≥ t_req).
  Výnimka smie použiť trezor B len vtedy, keď sa **overí v kóde a dokumentoch**, že žiadne ladenie, výskum ani štúdia
  rodiny tie roky nevideli. Vylúčené: `sdeur` (výskum 2011–2026), `noaes` (článok NOA videl SPY 2007–2024).
- **Ak sa niekedy stiahnu NQ, YM, GC 2010+** (rozhoduje používateľ), rozdelenie pre Nasdaq, Dow a zlato sa zmení na schému
  ES (trezor 6/2010–12/2014, ladenie 2015–9/2025) — len novým zápisom s dátumom a s počiatočným k
  (GC 2011–14 videl ZLATO-PRIESKUM, NQ/SPY článok NOA → hypotézy z nich 🟡). Mikro kontrakty potom len na exekúciu.
- Prahy a veľkosť v ATR alebo USD riziku; **objemové prahy len relatívne** (rvol, percentil). Náklad podľa miesta
  obchodovania (§3), nie podľa zdroja dát.
- **C dopĺňať z rovnakého zdroja ako L:** Databento mesačne cez `bento_import`, BTC len z Binance perp. Sviečky z hubu
  `livedata` (MT5, NT) sa na trezor nepoužívajú.
- **„Iný režim“ sa meria vopred:** v trezore je aspoň jeden štvrťrok s mediánom denného ATR % mimo IQR L, alebo
  pokles podkladu > 15 % od vrcholu, ktorý v L nebol. Zapíše sa do hlavičky.
- **Bodové prahy legacy** sa pred trezorom prepočítajú **pomerom mediánu denného ATR(14)** (rok trezoru / L), nie
  pomerom ceny. Ak potom stratégia spadne pod 150 obchodov v trezore, výsledok je ⏳.
- **Kvalita dát (zmerané 26. 11. 2026, `kritika/data_kvalita.json`, `data_noc_roly.json`):**
  - **Hranice:**
    - jadro seansy aj noc (US 23–13 UTC, FX a MGC 0–7 UTC) ≥ 95 % voči najlepšiemu roku trhu,
    - bez duplicít a nelogických sviečok,
    - zlé tiky (skok a hneď späť) ≤ 0,5 % sviečok.
  - **Namerané:**
    - čisté sú ES 2010+, 6E 2016+, MGC 2020+, MNQ 2019+ a BTC perp 9/2019+,
    - MYM v noci 2019 (86,5 %) a 2024 (94,8 %) neprešiel, nočné Dow stratégie preto potrebujú YM,
    - 6E má 2010–15 220–636 zlých tikov za rok a noc 2013–15 85–95 %,
    - MGC pred 2020 má jadro 8–92 % a noc 2–80 % a v januári 2011 prepína kontrakty tam a späť, preto nie.
- **Čistenie 6E 2010–2015** (dnes sa nepoužíva — §1 6E 2010–15 nemá; platí, len ak by sa niekedy zaradilo):
  - zmaže sa len skok, ktorý sa do 1 min vráti z ≥ 80 %, a len mimo ±3 min od správ,
  - pravidlo sa commitne pred prvým behom,
  - počet zmenených sviečok sa zapíše po rokoch (≤ 0,5 %, nad 1 % je rok ⏳),
  - kontrola: 50 náhodných opravených minút sa porovná s Dukascopy EURUSD.
- **Rolovanie** (archív nie je back-adjustovaný, skoky MNQ 0,9 %, ES 0,4 %, MYM 0,5 %, MGC 0,3 % (max 2,1 %),
  6E 0,35 %):
  1. Importér zapisuje deň, kontrakt a skok každého rolovania do `rolls.json`.
  2. **Indikátory naprieč dňami** (PDH/PDL, predošlé zatvorenie, overnight H/L, gap, denné ATR, SMA dní, filter
     špičky) sa počítajú na **ratio back-adjustovanom** rade, obchod a fill na surovom.
  3. Kým to nie je hotové, je **`skipRoll` (deň rolovania + 1 seansa bez vstupov) predvolene zapnutý** pre každú
     stratégiu, ktorá číta predošlú seansu.
  4. Kontrola prepínania: indexy a 6E 4× za rok, GC podľa aktívnych mesiacov. Návrat na predošlý kontrakt = chyba
     dát. Dnes sa to stáva len v MGC 1/2011. **Detektor `dq_night_rolls.py` má chybu** (jednociferný rok kontraktu sa po 10 rokoch
     opakuje → falošné návraty pri ES, 6E, MGC); pred automatickou kontrolou opraviť.
- **Externé kalendáre a dáta** (napr. ForexFactory) sa pred použitím overia proti nášmu kalendáru v prekryve, so
  zhodou dní ≥ 95 % na každý typ udalosti.

**Poučenie zo SPRÁV MGC (26. 11. 2026, `07_SPRAVY_stare_roky.md`) — NIE je to príklad trezoru (Z6):** beh na MGC
10/2010–9/2021 stál na dátach, ktoré §1 zakazuje (MGC pred 2020 jadro 8–77 %), a kalendár ForexFactory mal pri ISM
zhodu ~90 % (< 95 %). Platné sú z neho len okná 2019/20 a 2020/21 (107–143 obchodov, pod 150 → samy o sebe ⏳).
V okne 2020/21 boli všetky tri profily v strate už s poplatkom smernice (PF 0,66 / 0,70 / 0,97), s 1,5 tickom PF 0,52–0,69.
Beh 1/2020–9/2021 zároveň otvoril trezor MGC 2020–22 (pripočíta sa do jeho k).
**Legacy SPRÁVY sú ⚠ legacy s negatívnym signálom** (krok 10, najviac 🟡, dôkaz z C): jediné čisté okno 2020/21 bolo v strate.

---

## 2. Register pokusov a rozpočet

- `.nightsearch/register/<hypotéza>.jsonl` (append-only). Každý pokus zapisuje:
  - čas, kľúč, trh, TF, parametre a obdobie,
  - zdroj (mriežka / hyperopt / ručne / štúdia / plató / WF),
  - **hash commitu kódu stratégie**,
  - PF, obchody a **mesačný PnL**.
- **Hlavička `<hypotéza>.md`** sa commitne **pred prvým behom rodiny**: dôvod edge (3 vety), zdroj, mriežka, trhy,
  L a hranice všetkých brán.
- **Rozpočet:** ≤ 300 konfigurácií na hypotézu spolu, **vrátane susedov v plató** (~30 na kandidáta, teda najviac
  ~5 kandidátov). Vyčerpaný rozpočet = koniec.
- **Hypotéza zo štúdie (Z5):** behy štúdie sa do rozpočtu 300 nerátajú, ale hypotéza ide cestou **kroku 10**
  (DSR, PBO aj haircut len informácia, najviac 🟡, dôkaz z C). Do N pre DSR/haircut ide počet behov štúdie. Navýšenie sa nepripúšťa.
- **≤ 5 voľných parametrov** vrátane TF, bool a typu príkazu. Typ vstupu (market/limit) a filter IBS + pin bar sa vyberú
  **vopred** v hlavičke, neladia sa a do 5 sa nepočítajú (používateľ 27. 11.).
- **Strop:** najviac **10 nových hypotéz za štvrťrok na jeden trezor**.
- **Bonus za ekonomický dôvod** (t_req na trezore −0,3, haircut z ½ N_eff) platí len pri splnení oboch podmienok:
  1. hlavička s dôvodom je commitnutá pred prvým behom rodiny,
  2. dôvod cituje **vonkajší zdroj publikovaný pred naším prvým pohľadom na dáta**, alebo predpovedá **vedľajší
     jav**, ktorý prejde samostatným testom s N = 1 (napr. drift surových výnosov okolo FOMC bez pravidiel
     stratégie).
- **Legacy stratégie** (všetko z webapp k 26. 11. 2026):
  - do registra ide odhad N z `gl_state` + `hyper_state` + `glwr`/`glrr` + štúdií,
  - `GROUPS` a profily sa zmrazia commitom,
  - ďalšie hľadanie na nich sa nepúšťa a cesta ku schváleniu je krok 10.

---

## 3. Náklady a fill model (platí už v ladení)

**Futures (emulátor a C# jadro, prepínač `--fill v2`, predvolený):**

| | MNQ | MYM | ES / MES | MGC | 6E | BTC |
|---|---|---|---|---|---|---|
| náklad na stranu (poplatok + ½ spreadu) | 1,75 ticku | 1,75 ticku | 1 tick | 1,5 ticku | 1 tick | 0,02 % maker / 0,05 % taker |
| sklz: stop, market vstup aj výstup, výstup v čase | +2 ticky (O; NT M medián 1, p75 5) | +2 ticky (O) | +1 tick | +1 tick | +0,5 ticku | +0,02 % |
| tick = bodov | 0,25 b | 1 b | 0,25 b | 0,10 $ | 0,00005 (0,5 pipu) | — |
| **limit / TP: o koľko musí cena prejsť** | 0,25 b | 1 b | 0,25 b | 0,10 $ | 0,5 pipu | 1 tick |
| **sklz v bodoch** | 0,5 b | 2 b | 0,25 b | 0,10 $ | 0,25 pipu | 0,02 % |

- Náklad je v tickoch, nie v % z ceny.
- **Limit vstup a TP:** plnenie až pri prechode o 1 tick (long limit: `low ≤ price − tick`).
- **SL:** `min(stop, open)` − sklz. SL pred TP v jednej minúte (zachované).

**CFD (dohoda B + A, finálna kontrola C 27. 11.; `19_B`, `20_A`, `21_C`):**
Graf brokera aj Dukascopy je **bid**. Nákupná strana (long vstup, short TP, short SL) sa spúšťa na **ask = bid + S**.
M = namerané na živých filloch bez duplikátov Demo/Server3, O = voľba alebo odhad.

| symbol | S hlavná seansa | S mimo seansy | spúšťač predaj / nákup | sklz SL a stop vstup | market | NY open 9:30–9:40 | správy ±5 min |
|---|---|---|---|---|---|---|---|
| US100.cash | 2,0 b (O; M medián 1,4, n=20) | S×2 (O) | bid ≥ L + 0,25 / bid ≤ L − S | 1,0 b (M, n=33) | 0,5 b (M) | S×2, +2 b (O, stres) | S×4, +4 b (O, stres) |
| US500.cash | 0,8 b (O; M 0,2–1,2) | S×2 (O) | L + 0,05 / L − S | 0,3 b (O; M 0,21, n=3) | 0,3 b (O) | S×2, +1 b (O) | S×4, +2 b (O) |
| XAUUSD | 0,40 $ (O) | podľa hodiny (O) | L + 0,05 / L − S | 0,25 $ (O; M 0,15, n=4) | 0,15 $ (O) | S×2, +0,5 $ (O) | S×5, +1,5 $ (O) |
| US30, EURUSD, BTCUSD | odhad `19_B` (bez fillov) | — | 0 / S | O | O | O | O |

- **Limit a TP sa plnia presne na úrovni**, zlepšenie sa nepočíta. **Limit, ktorý je pri odoslaní už za trhom, sa neplní**
  (MT5 ho odmietne `10015`; emulátor ho dnes vyplní na otvorení). SL aj TP v jednej minúte → SL.
- **Market nákup** = bid + S + sklz, **market predaj** = bid − sklz.
- **Spread sa zmeria hneď, nečaká sa na demo:** jednorazový skript z histórie ticku brokera (`CopyTicks` bid/ask, spread M1)
  → p75 podľa hodiny a okolo správ; násobky pre NY open a správy z Dukascopy bid/ask 2021–26. Potom tabuľka nahradí O.
- **EA a NT pri každom fille zapíšu `bid`, `ask`, `spread` a čas v ms (`DEAL_TIME_MSC`)** — dnes EA berie `DEAL_TIME`
  v sekundách (`TradeBotEA.mqh:1887`) a spread M1 zahadzuje (`:1047`).
- **CFD hypotéza je najviac 🟡**, kým: spread nie je nameraný z histórie brokera, EA neloguje bid/ask a ms, a nie sú
  vysvetlené 3 nevyplnené limity na US500 (história terminálu NAS-WIN11).
- **US500 so SL pod 15 b** (NY VA, IBS EZ ES) nedostanú 🟡 ani ✅, kým PF po tomto modeli nie je ≥ 1,15 — náklad 0,06–0,09 R
  zje edge ~0,10 R.
- **Prepočet:** ak sa nameraný spread alebo sklz odchýli od tabuľky o > 0,5 S, kroky 3–11 sa prepočítajú.
- Swap za každú noc. Víkendový gap proti stopu sa rieši pri stratégiách, ktoré držia cez víkend.
- CFD ide len cez emulátor (Python + C#, parita); Freqtrade spread podľa strany nevie.
- **Fill v2 dnes nie je naprogramovaný ani pre futures** (v `emulator.py` ani `McEmulator.cs` nie je spread, sklz ani
  prechod; prepínač `--fill` neexistuje) — „platí už v ladení“ je cieľ, nie stav (⛔).
- **Rýchly filter:** konfigurácia s PF < 1,15 na L pri fill v2 ďalej nejde.

---

## 4. Kroky (každý zapisuje do `register/<hypotéza>.md`, sekcia „Brány“; ❌ = hypotéza uzavretá, nič sa nemaže)

### Krok 1 — Naživo = história (zachované, povinné)
1a 6 rôznych štartov, 1b dáta utnuté po vstupe (50–60 obchodov), 1c utnutie uprostred HTF, 1d výsledok obchodu zo
sviečky. **0 rozdielov**. Pri C# verzii k tomu parita bar po bare (`tester.compare.csharp_parity`), tiež **0 rozdielov**.
Rozdiel → oprava kódu a nové východisko.

### Krok 2 — Hlavička a register
Commit podľa §2. Hlavička obsahuje aj **zoznam štúdií a výskumov**, z ktorých hypotéza vychádza (§1). Bez toho automat hypotézu nepustí.

### Krok 3 — Východisko a logika
Východiskové nastavenie na L pri fill v2 a kontrola kresieb na 2–3 mesiacoch. PF < 0,95 pri ≥ 200 obchodoch → ❌.

### Krok 4 — Hľadanie v rozpočte
- Mriežka alebo Optuna v rozpočte. Cieľ je `break_even` alebo PF a najhorší rok, **nikdy WR**.
- **Obchody:** ≥ 75 v **každom** roku L (schválil používateľ 26. 11.) a pomerne v každom WF kúsku. Hypotéza pod 75 (správy, trend CFD) smie
  ísť ďalej len s výnimkou zapísanou v hlavičke **pred** behom. Vtedy t_req + 0,5 na trezore a ≥ 150 obchodov
  v trezore daného trhu (🟡), pre ✅ ≥ 200. Obchody rôznych trhov sa nikdy nesčítavajú.
- **Rok = kalendárny rok.** Každý neúplný rok L pomerne 75 × mesiace / 12 (ES 2025, MGC 2025: 8 mesiacov; MNQ, MYM 2019
  a 2022; BTC 2019 a 2022; 6E 2021).
- **Kandidát:** PF na L ≥ 1,25, žiadny rok L pod 0,95.
- **Vrchol hľadania sa nikdy nezobrazuje ako očakávanie.**

### Krok 5 — Plató (celý priestor)
- Každý parameter ±1 krok (aj bool a str), plus 20 náhodných susedov so 2 parametrami. Susedia sa počítajú do
  rozpočtu.
- **Medián susedov ≥ 0,85 × PF a minimum ≥ 0,70.**
- Vyberá sa **stred plató** (najlepší medián okolia), nie vrchol.

### Krok 6 — Walk-forward (jednorazový zámok)
- Učenie 24 mesiacov (ES, 6E) alebo 18 mesiacov (MNQ, MYM, BTC, MGC — §1), test 6, posun o 6 mesiacov. Reoptimalizácia tým istým automatom so zmrazenou
  mriežkou a rozpočtom ≤ 300 / počet okien.
- **Hranice:**
  - spojená OOS krivka PF ≥ 1,15,
  - WFE ≥ 0,5,
  - ≥ 75 % kúskov v pluse (pri < 4 kúskoch všetky; WF je tam len negatívny filter),
  - parameter medzi susednými oknami sa nemení o viac ako ½ rozsahu mriežky.
- **WF má zámok ako trezor** (`vaults.json`). Druhý WF = nová hypotéza.
- Behy WF sa zapisujú do registra, nemenia finálnu konfiguráciu a **do N pre DSR sa nepočítajú** (do N idú
  kroky 4 a 5).
- Pri legacy je WF len negatívny filter: neprejde → ❌, prejde → bez váhy dôkazu.

### Krok 7 — Štatistické brány (z registra)
| brána | hranica | metóda (zmrazená) |
|---|---|---|
| N_eff | — | počet zhlukov mesačného PnL pri \|ρ\| > 0,5, podlaha N_eff ≥ N / 50 |
| **DSR** | ≥ 0,95 pri N_eff **a** ≥ 0,50 pri surovom N | Bailey–López de Prado 2014, denný PnL L |
| **PBO** | ≤ 0,20 | CSCV, S = 16 blokov mesačného PnL všetkých konfigurácií v registri |
| **Haircut** | ohaircutovaný SR > 0. **Ohaircutovaný PF < 1,10 → ⏳** (nevyplatí sa) | Harvey–Liu 2015 (BHY), N = N_eff (½ N_eff s bonusom §2) |
| break-even náklad | ≥ 2× náklad z §3 | `checkup` **len na L** (Z3) |
| test proti náhode | > 95 % | `tester.nulltest`, len doplnok |
| **Sortino** (doplnené 26. 11.) | ≥ 1,0 ročne | len z **walk-forward OOS** (krok 6) a trezorov (krok 8), denný PnL na každý pracovný deň (bez obchodu = 0). Sortino z ladenia alebo z roka A sa nepočíta ani neukazuje (dnešná hranica 2,0 v `glaudit.py` platí na in-sample dátach a nič nedokazuje) |

Neprejde DSR, PBO alebo haircut → ❌. **Výnimka:** legacy a hypotézy zo štúdií (krok 10) majú **DSR, PBO aj haircut len
ako informáciu** (Z4, Z5; legacy nemá mesačný PnL všetkých konfigurácií). Rozhodne C.

### Krok 8 — Trezory (raz, hranica z hlavičky)
**8a — rok A (negatívna kontrola):** PF ≥ 1,0, inak ❌.

**8b — trezor B:**
- **Dĺžka trezoru (zmenené 27. 11., používateľ):** aspoň **2 roky alebo 30 % použiteľných dát trhu — platí to dlhšie**
  (dnes: ES 4,6 r = 30 %, 6E 3,9 r = 40 %, MNQ/MYM 2,9 r ≈ 46 %, BTC 2,9 r ≈ 48 %, MGC 3,0 r ≈ 53 % — všetky spĺňajú);
  trezor musí obsahovať
  **iný režim podľa §1** (štvrťrok s mediánom ATR % mimo IQR L alebo pokles > 15 %, ktorý v L nebol).
  Kratší trezor alebo jeden režim → najviac ⏳. Rozhoduje počet obchodov (t), roky len chránia pred jedným režimom.
- **Počet obchodov (dohoda A + B 27. 11., `14_B`, `15_A`; pevné 300 zrušené):** rozhoduje test t ≥ t_req, počet je len
  ochrana pred malou vzorkou. Počíta sa **na trh a trezor**; obchody rôznych trhov sa nesčítavajú.
  - < 150 obchodov → ⏳.
  - **🟡:** ≥ 150 obchodov, t ≥ t_req, PF ≥ 1,10 s nákladmi z §3, ≥ 60 % rokov v pluse.
  - **✅:** ≥ 200 obchodov, t ≥ t_req, PF ≥ 1,15, ≥ 60 % rokov v pluse, žiadny rok pod 0,90.
    Pri šikmosti R < −1 (vysoký WR, malý TP, gapy) až od **250** obchodov a s **t_req + 0,3**.
  - **t = min(t z obchodov, t z mesačného PnL)** — kryje zhluky obchodov (autokorelácia zdvojnásobí falošný poplach).
    Mesačné t len pri ≥ 24 mesiacoch, inak t z obchodov s HAC (Newey–West).
  - **k (jedna definícia):** k trezoru = počiatočné k (§1) + každá hypotéza **a každá kópia rodiny** (na ľubovoľnom trhu), ktorá ho otvorila.
    Kópia = samostatný pokus (Bonferroni: 6 kópií → +6).
  - **Veľkosť:** blokové Monte Carlo z mesačných blokov trezoru, PF_MC = 1 + (PF_obs − 1)/2, kým n < 300
    (prekliatie víťaza); riziko na obchod ≤ 5 % / p95 DD v R; p99 dennej straty všetkých súbežných kópií ≤ 4 %.
    Horizont MC = obchody za rok × 2. **Bez MC → najviac 🟡.**
- **t ≥ t_req**, kde k = **kumulatívny počet hypotéz, ktoré sa kedy pozreli na daný trezor** (počíta
  `vaults.json` podľa jedinej definície k vyššie). Rozhoduje teda história trezoru, nie veľkosť dávky. Test je jednostranný, α = 0,025 s Bonferroniho korekciou na k (zodpovedá obojstrannému 0,05):

  | k | 1 | 5 | 10 | 20 | 50 | 100 | 160 |
  |---|---|---|---|---|---|---|---|
  | t_req | 2,0 | 2,6 | 2,8 | 3,0 | 3,3 | 3,5 | 3,6 |

- Bonus za ekonomický dôvod −0,3, výnimka pod 75 obchodov za rok +0,5.
- t = priemer obchodu v R / σ · √n.
- Pri PF 1,2 dá ~500 obchodov t = 2 len v priemere (sila 50 %); na 80 % silu treba ~1 000 (PF 1,3 ~480, PF 1,5 ~200). Pozorovaný PF, ktorý t_req vynúti sám: 150 obch 1,39 / 1,65 (t 2,0 / 3,0), 210 obch 1,32 / 1,52, 300 obch 1,26 / 1,42; pri k ≥ 50 (t 3,3) a 210 obch ≥ ~1,59, pri k ≈ 160 (t 3,6) ≥ ~1,65. Je to vlastnosť dát, nie chyba brány.

**8c — iný trh** (len v jednotkách ATR alebo %, pri bodových prahoch je výsledok ⏳):
- **pozitívny dôkaz:** iné časové pásmo alebo iná trieda aktív (DAX/Nikkei pri ich otvorení, zlato, FX), bez zmeny
  parametrov, PF ≥ 1,05,
- **negatívny test (povinný):** na príbuznom trhu (MNQ ↔ ES ↔ MYM, BTC ↔ ETH perp, MGC ↔ SI, 6E ↔ 6B) PF ≥ 0,95, inak ❌. Test beží **len na L príbuzného trhu**, nikdy na jeho trezore. Ak
  príbuzný trh v archíve nie je (dnes SI a 6B), je výsledok **najviac 🟡** (Z1),
- Dukascopy CFD je len test zdroja dát, PF ≥ 1,0.

### Krok 9 — Odolnosť
- 2× náklad z §3: PF ≥ 1,05.
- Vstup o sviečku neskôr: PF ≥ 1,05 a ≥ 80 % PF.
- **Režimy:** obchody na tercily podľa ATR(20 dní) v deň vstupu. Žiadny tercil pod PF 0,90 a žiadny nenesie > 60 %
  zisku.
- **Len legacy — fill citlivosť (T2):**
  - TP s `exit == high/low` minúty ≤ 30 %,
  - PF po vyradení dotykov a +1 tick na SL ≥ 1,10.

### Krok 10 — Legacy brána (dnešné stratégie)
1. Kroky 1, 3 (fill v2: PF ≥ 1,15 **na L daného trhu, bez roka A**), 7 (DSR, PBO a haircut **len ako informácia**) a 9 vrátane T2.
   Rovnakou cestou idú hypotézy zo štúdií (§2).
2. **Trezor:** v dátach, ktoré máme, legacy čistý trezor nemá (§1) → bez neho najviac 🟡. Trezor B smie použiť len
   overená výnimka (§1); t ≥ t_req pre k trezoru (počiatočné k z §1). Inak rozhoduje **C ≥ 2 roky, ≥ 200 obchodov a t ≥ t_req**.
3. **C** (nové dáta od commitu) ≥ 2 roky; demo a nasadenie rozhoduje používateľ.

Publikovaná vonkajšia hypotéza s východiskovými parametrami bez hľadania sa testuje ako nová hypotéza, primárne na
období **po publikácii**. Preklad na náš trh urobený človekom sa počíta ako N = 3.

### Krok 11 — Portfólio a prop riziko (všetky stratégie jedného účtu)
- **Overiť pravidlá konkrétneho účtu bez predpokladu** a zapísať ich do registra zo zmluvy alebo od firmy:
  - denný a celkový limit,
  - **typ DD** (statický, trailing EOD, trailing intraday) a od čoho sa počíta,
  - správy, noc, víkend, konzistencia, zakázané techniky.
  Neznáme pravidlo = stratégia na účet nejde.
- Denná equity sa skladá z 1m sviečok a MAE súčasne otvorených pozícií pri skutočných veľkostiach, s presným typom
  DD účtu.
- Blokový bootstrap s blokom 5 obchodných dní, 10 000 ciest × 12 mesiacov. Hranice:
  - **P(denný pokles equity ≥ limit − 1 %) ≤ 2 %**,
  - **P(DD ≥ celkový limit − 2 %) ≤ 5 %**,
  - pri FTMO 5 / 10 % to znamená 4 % a 8 %.
- Veľkosť pozície sa vypočíta z týchto hraníc. Riadi ju **jediné číslo: MC 95 % DD dennej equity portfólia**.
- **Sortino portfólia** z denného PnL (walk-forward OOS a trezory, skutočné veľkosti) ≥ 1,0; ukazuje sa vo webapp
  pri portfóliu účtu namiesto dnešného Sortina z ladenia.
- **Súčasné riziko:** súčet rizika na stopoch všetkých otvorených pozícií + nový obchod ≤ 1,5 % účtu, inak sa vstup
  neodošle.
- Najviac 2 stratégie na index v tom istom časovom okne. Korelácia denného PnL ≤ 0,5. MNQ, MYM a ES/US500 sa
  počítajú ako jeden index.
- **CFD replay:** stratégia bez zmeny na m1 sviečkach brokera zo zrkadla (10–11/2026, len exekúcia). Zhoda signálov
  s futures behom ≥ 90 %, inak sa feed brokera berie ako iný trh (krok 8c).

### Krok 12 — Ochrana účtu v kóde (podmienka pred prvým ostrým obchodom)
*Kroky „Demo“ a „Ostrá prevádzka a vypínanie“ sú zrušené — demo a nasadenie si stráži používateľ (27. 11.).*
- V EA (MT5) a NT, **lokálne, bez závislosti od hubu a Mac mini:**
  - **denný pokles equity −4 %** → flatten + pause všetkých inštancií účtu do ďalšieho dňa (celkový stop sa nedáva),
  - pre-trade kontrola súčasného rizika 1,5 %,
  - pravidlá účtu z kroku 11.
- SL a TP vždy u brokera.
- Heartbeat > 30 min v seanse → Telegram alarm (`agent_plugins/telegram`, hub `watchdog`). Alarm smie závisieť od
  hubu, stop nie.
- Ten istý kľúč a profil na dvoch sčítaných účtoch → štart sa odmietne.

---

## 5. Webapp a stránka
- **Stav:**
  - ✅ schválená V2,
  - 🟡 demo,
  - ⏳ nepotvrdená,
  - ⚠ legacy neobhájená,
  - ❌ zamietnutá (s krokom, kde padla).
  ✅ smie zapísať len skript, ktorý brány prepočíta z registra. Ručné výnimky (dnes `APPROVED = {"spravyeur"}`
  v `glwebvyber.py`) sa rušia.
- **Titul:** ohaircutovaný PF po nákladoch §3, obchody za rok, MC 95 % DD dennej equity. Posledný rok len ako kontrola (stĺpec rok A), nie v titule, bez
  PF z ladenia a bez vrcholu hľadania.
- **Poradie:** stav, potom ohaircutované očakávanie z L/WF. Nikdy rok A ani trezor. Karta Výkon a titul neberú rok A
  do žiadneho súčtu.
- **Pri každej stratégii a v každej tabuľke výsledkov (webapp, stránka, ranná tabuľka 6:00, iCloud) sa vedľa PF a WR
  ukazujú aj štatistické brány** (používateľ 27. 11.):

  | stĺpec | čo znamená | hranica |
  |---|---|---|
  | PF (po nákladoch §3) | zisk / strata | — |
  | **PF po haircute** | čo z PF ostane po započítaní všetkých pokusov — toto čakať naživo | ≥ 1,10 |
  | WR | podiel ziskových obchodov (len informácia, nikdy cieľ) | — |
  | **DSR** | pravdepodobnosť, že Sharpe nie je šťastie z mnohých pokusov | ≥ 0,95 |
  | **PBO** | ako často víťaz výberu zlyhá na nevidených kúskoch histórie | ≤ 0,20 |
  | N / N_eff | počet pokusov / nezávislých pokusov, z ktorých sa vyberalo | — |
  | t (trezor) / t_req | sila výsledku v trezore proti požadovanej | t ≥ t_req |
  | Sortino | len z WF OOS a trezorov | ≥ 1,0 |
  | obchody za rok, MC 95 % DD | — | ≥ 75 / podľa kroku 11 |
  | **iné trhy** (krok 8c) | PF na príbuznom trhu (MNQ↔ES↔MYM, BTC↔ETH) a na inom type trhu, bez zmeny parametrov — či je stratégia použiteľná aj inde | ≥ 0,95 / ≥ 1,05 |
  | posledný rok (rok A) | len kontrola, sivou, **nikdy na zoradenie** | PF ≥ 1,0 |

  Hodnota, ktorá bránu nesplní, je červená; chýbajúca (ešte nespočítaná) sa ukáže ako „—“, nie ako 0. Pri legacy
  a hypotézach zo štúdií sa DSR, PBO a haircut ukazujú tiež (len informácia, krok 10).
- Detail ukazuje navyše WFE, k trezoru, podiel TP dotykov a dátumy spálenia.
- `glaudit`: trieda A = ✅ V2. Pravidlo „odložený rok PF ≥ 1,4“ sa ruší.
- **Ranná `glwebvyber.py --apply` sa vypne**, kým poradie nebude podľa stavov V2 (dnes každé ráno obnovuje poradie
  podľa OOS).

## 6. Automat (.nightsearch)
- `glsearch` / `glhyper`:
  - pustia len hypotézu s commitnutou hlavičkou a zastavia sa na rozpočte,
  - **OOS ani trezory v hľadaní nepúšťajú** (dnes `glsearch.py:864`, `glwr.py:244`, `glrr.py:140`),
  - kandidát = krok 4 + krok 5 → fronta WF,
  - do registra zapisujú mesačný PnL a hash kódu.
- Trezor a WF sa púšťajú samostatným príkazom `--vault B|C` / `--wf`. `checkup` a analytika počítajú len na L (`--windows L`). Druhé spustenie pre tú istú hypotézu
  príkaz odmietne (`register/vaults.json`).
- Ranné nahrávanie publikuje stavy §5.

---

## 7. Prechodné pravidlá (odporúčanie A aj B, rozhoduje používateľ, agenti nič nevypínajú)

- **P1** Zapísať pravidlá účtov FTMO-Server3, FTMO Demo a Tradeify podľa kroku 11, vrátane typu DD. Správy sú podľa
  používateľa na Server3 povolené.
- **P2** Ručný denný stop účtu −4 % equity s alarmom, kým nie je hotový krok 12.
- **P3** Na Server3 odporúčame pozastaviť TKS 1, IBS EZ 11 (legacy, neobhájené, IBS EZ 11 je ladená na živom novembri),
  SPRÁVY profil 3 a ladenú NOA 1 do T3, aspoň cez NFP 4. 12. Demo inštancie nechať bežať ako kontrolu exekúcie.
- **P4** Inventúra: Tradeify NT (posledný signál 19. 11.: otvorená pozícia?), duplicity FTMO Demo a Server3.
- **P5** Zmraziť `GROUPS`, profily a hlavičky k 26. 11. 2026 (commit). Dnes ešte necommitnuté zmeny `PRESIEL_SMERNICAMI_*` (fibomgcnet, nyvaesnet, ibsentryesnet). Na 10–11/2026 nič neladiť.
- **P6** Všetkým profilom vo webapp dať ⚠ legacy. Vypnúť `glwebvyber --apply` a `glsmernice --apply` (28. 11. zablokované jednorazovo cez `dash/.last_morning` — platí, len kým žiadny stavový súbor hľadania nie je novší; testy sú pozastavené `gl_paused`. Trvalé vypnutie čaká).
- **P7** Commitnúť hranice trezoru C do 30. 11. 2026.
- **P8 Rozhodujúce testy (hranice sú zapísané tu):**
  - **T1** IBS EZ MNQ/MYM 6/2019–9/2021, prahy prepočítané: PF ≥ 1,10 a ≥ 2/3 roky na oboch, inak ❌. IBS EZ ES je
    už čisté ❌ (0,75, 3/12, prahy v ATR).
  - **T2** fill citlivosť dnešných živých profilov (krok 9).
  - **T3** NOA naživo v R spárovaná so simuláciou: > 50 % straty v R z nespárovaných obchodov → chyba exekúcie,
    inak platí štatistika.
  - **T4** Williams R 6E na **L 6E 2016-01 – 2021-09** (krok 10.1; trezor 10/2021–9/2025 ani rok A sa nepúšťajú) pri fill v2: PF < 1,05 → ❌, inak ⏳. ✅ len cez C.
  - **T4b** ORB 15/5 ES len na **2015-01 – 2021-09** (L ES; 2010–14 je trezor) s +1 tick na stop a market: PF < 1,0 → ❌, PF 1,00–1,03 → ⏳, PF ≥ 1,03 → ostáva ⚠ legacy (T4b vie len zamietnuť).
  - **T5** ruina dnešných inštancií Server3 podľa kroku 11 so skutočnými lotmi z fill udalostí.
  - **T6** NOA podľa článku (`base_noa.json`, N = 3):
    - primárne MNQ 6/2024–9/2026 (po publikácii): PF ≥ 1,10 a t ≥ 2,0 — **výslovná výnimka z 8a/8b** (publikovaná hypotéza, N = 3); zapíše k + 1 trezoru MNQ,
    - sekundárne NQ 2010–2019 len ak sa stiahne (autori to obdobie na SPY videli): PF ≥ 1,0.

**Stav stratégií k 27. 11. 2026:**

| stratégia | stav V2 | dôvod |
|---|---|---|
| **SPRÁVY MGC profil 1–3 (aj EUR legacy)** | **⚠ legacy, negatívny signál** | krok 10 (najviac 🟡, dôkaz z C). Jediné čisté okno 2020/21 bolo v strate na všetkých troch (PF 0,66–0,97; 107–143 obch, samo o sebe ⏳). MGC 2010–19 sa nepočíta (zlé dáta) |
| **beží naživo proti V2** (Server3, `mirror.sqlite` 27. 11.) | ❌ / ⚠ | TKS_1 a IBS_EZ_11 (❌; IBS EZ 11 ladená na živom novembri, §0), spravynet profil_3 a NOA_1 (⚠); stop účtu v EA chýba, NFP 4. 12. — rozhoduje používateľ |
| SPRÁVY-jadro (nová hypotéza) | otvorená | ≤ 5 parametrov, udalosti vybrané mechanizmom vopred. MGC 2020–22 (trezor) je ich behmi otvorený a 2010–19 sú zlé dáta, ostáva len C alebo iné aktívum (napr. ES/ZN na tých istých správach, ak ich rodina nevidela) |
| Williams R 6E | ⏳ | T4, potom C |
| NOA podľa článku | ⏳ | T6 |
| NOA ladená, Volt Break, ON bias ORB, Daily open | ⚠ legacy | krok 10 (najviac 🟡, dôkaz z C) |
| Noc + pondelok | ⏳ | prieskum videl MNQ 2019–26 → dôkaz len z C (alebo NQ 2010–19, ak sa stiahne) |
| ORB 15/5 ES | ⚠ do T4b | T4b |
| IBS EZ MNQ/MYM (okrem IBS EZ 11) | ⚠ do T1 | T1 |
| IBS EZ ES, TKS, VWAP ORB, NY VA ES, IVB, NOA MGC, Sigma MGC/MYM, NQ Precision MGC, M2 MNQ, CRT, Sweep engulf MNQ, Williams R ES, Flash ORB MNQ, VWAP ADX EOD | ❌ | staré roky PF < 1 alebo medián OOS kandidátov ~1,0 |
| MTK ORB MGC, MTK EMAS | ⏳ | staré roky boli in-sample (ladenie 2010–24, resp. štúdia), ostáva C |
| ostatné ⚠ z triedenia | ⚠ legacy | krok 10 |

---

## 8. Čo ostáva zachované
Krok 1 a C# parita, 1m detail, SL pred TP, kontrola dát Databento, `checkup` (analytika a posudok, **len na L**), hub (výpočty,
pluginy) a ranné nahrávanie s novými stavmi, pravidlo „Pine nie do repa“ a obmedzenie, že MacBooky nepočítajú.

---

## 9. Rozhodnutia používateľa (27. 11. 2026, uzavreté)
1. **Smernica V2 schválená a podpísaná** 27. 11. 2026.
2. **Minimum obchodov:** ≥ 75 v každom roku L; v trezore < 150 ⏳, 🟡 od 150, ✅ od 200 a t ≥ t_req.
3. **Rozdelenie rokov** podľa §1 (ES trezor 2010–14, MGC obrátené); trezor ≥ 2 roky alebo 30 % použiteľných dát (dlhšie).
4. **Server3 a SPRÁVY naživo:** vyriešil používateľ sám (27. 11.).
5. **Dáta:** zatiaľ sa nič nové nesťahuje (SI, 6B, NQ, YM, GC). Zlato a 6E preto najviac 🟡.
6. **WR 70–100 %** zrušené; RR ≥ 0,5 ostáva.
7. **Počiatočné k** prísne z celej histórie.
8. **Posledný rok** v tabuľkách len ako kontrola, nikdy na zoradenie.
9. **„market/limit + IBS + pin bar“:** voľba sa **vyberie vopred** (zapíše sa do hlavičky pred prvým behom) a neladí sa —
   do 5 voľných parametrov sa nepočíta.
10. **Demo a ostrá prevádzka** si stráži používateľ; denný stop účtu −4 %, celkový nie.

---

## 10. Odhad práce na zavedenie

| čo | súbory | odhad |
|---|---|---|
| **Ochrana účtu** (denný stop −4 % z equity, súčasné riziko 1,5 %, pravidlá účtu, duplicity, lokálne) — **najprv** | `tradebot/adapters/mt5/TradeBotEA.mqh`, `deploy/mt5`, `tradebot/adapters/ninjatrader/TradeBotStrategy.cs`, `TradeBotLiveAddOn.cs`; `tester/tests/test_mt5_static_host.py` | 3–5 dní + demo |
| Log `bid/ask/spread` pri fill | EA, NT, hub plugin `livedata`, `tester/live/` | 1 deň |
| Fill v2 a náklady v tickoch | `tradebot/adapters/multicharts/emulator.py` (`_fill`, `_exit_fill`), `tradebot/core/instruments_databento.json`, `tester/fees.py`, C# emulátor v `tradebot/core/ports/csharp` (parita) | 2–3 dni |
| Register, rozpočet, hash kódu, mesačný PnL, vypnutie OOS v hľadaní | `.nightsearch/glsearch.py` (`evaluate`, `main`, `:864`), `glhyper.py`, `glwr.py`, `glrr.py`, nový `register.py` | 2 dni |
| Plató celý priestor + stred | `glsearch.py:804`, CLI plateau | 1 deň |
| Walk-forward so zámkom | nový `tester/walkforward.py`, `tester/webapp/cli/` | 3–4 dni |
| N_eff, PBO, haircut, DSR ako brány, t_req z `vaults.json` | `tester/robust.py`, nový `tester/pbo.py`, `glrobust_missing.py` | 2 dni |
| Trezory a zámky | `register/vaults.json`, príkaz `--vault`, `tester/checkup.py` (len L, bez roka A) | 1 deň |
| Počiatočné k trezorov z histórie (rodiny, kópie, štúdie, triedenie) | `vaults.json`, skript nad `tradebot/strategies`, `gl_state`, iCloud štúdie | 1 deň |
| Ratio back-adjust indikátorov naprieč dňami + `skipRoll` predvolene | `tester/bento_import.py` (`rolls.json` so skokom), Python jadro aj C# (parita) | 3–4 dni |
| Meranie iného režimu, kontrola kalendára, oprava detektora rolovania | `dq_night_rolls.py`, nový skript režimu, plugin `ff_calendar` | 1–2 dni |
| (voliteľné) NQ/YM/GC 2010–2019, prepočet bodových prahov | `tester/bento_import.py`, `tester/timeframes.json`, `tradebot/core/config.py`, konfigy s `"abs"` | 2–3 dni + sťahovanie |
| Portfólio z equity (MAE, typ DD), bootstrap, CFD replay | `tester/prop.py`, `tester/montecarlo.py`, `tester/livesim.py`, `cli portfolio` | 3 dni |
| Webapp a stránka (stavy, tituly, poradie, stĺpce DSR / PBO / haircut / t, zrušenie `APPROVED`) | `.nightsearch/gldash.py:480–490`, `glwebvyber.py`, `glaudit.py`, `glreport.py`, `tester/webapp/static/js/*`, `tester/webapp_vyber.json` | 2 dni |
| Jedna smernica | `docs/SMERNICA_TESTOVANIA.md` (nahradiť), iCloud len odkaz, `README.md` (Kde sme), `CLAUDE.md` (aj „checkup len na L“, krok 3 bez trezorov) | 0,5 dňa |

**Spolu ~28–34 dní (~6–7 týždňov) podľa tabuľky, s rezervou 7–9 týždňov** jedného vývojára. Poradie:
1. P1–P7 hneď (bez kódu),
2. ochrana účtu,
3. log spreadu, fill v2 a počiatočné k trezorov (pred T4) + T2/T4/T4b, checkup len na L,
4. register + vypnutie OOS,
5. T1/T6 (NQ 2010–19 len ak sa stiahne),
6. WF a PBO,
7. webapp.

Výpočet: ~1 200 behov na hypotézu, teda ~2–3 h na Mac mini + hube, čo je ~1 000× menej než dnes.
