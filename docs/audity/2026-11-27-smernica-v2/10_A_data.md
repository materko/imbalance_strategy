# Agent A (Prokurátor) — dáta po trhoch: pripomienky k 09_B_data

*26. 11. 2026, len čítanie. Kontrolný skript je v scratchpade (nice 19, 7 súborov), nie v repe.*

## 0. Overenie merania
- **Pomery pokrytia sedia.** Moja hrubšia metóda (delí všetkými kalendárnymi dňami s dátami vrátane nedeľného
  otvorenia, preto vychádzajú nižšie absolútne čísla):
  - MGC 2019 vs 2023 v okne 8–16 UTC: 76,2 % vs 82,9 %, pomer 0,92. Inžinier má 92 % vs 99,5 %, teda rovnaký pomer.
  - Noc (0–6 UTC) MNQ 2019 / 2023 80 % / 83 %, MYM 2020 81 %, MGC 2021 81 %, 6E 2017 80 %. Noc je zhruba rovnako
    pokrytá vo všetkých rokoch.
- **Doplnok:** Inžinier meral pokrytie len v jadre seansy. Stratégie nocpon, ON bias, Asia/London sweep žijú
  v noci. DOHODA: v `data_kvalita.json` doplniť aj nočné okno (US 22–13 UTC, FX/MGC 0–7 UTC). Hranica ≥ 95 %
  relatívne k najlepšiemu roku trhu.
- **6E 2012:** skokov > max(25 × medián, 0,3 %) som napočítal 1 270. Výrazne zlé dáta potvrdzujem.
- **ES prelom 2012 → 2013, +1,35 %:** nie je to chyba dát. Je to dohoda o „fiscal cliff“ (1. 1. 2013) a skutočný
  gap 2. 1. 2013. Prelom 2013 → 2014 má −0,46 %. Bod „overiť“ uzatváram ako skutočný pohyb trhu.

## 1. Spoločné pravidlo, ktoré meniť navrhujem: jeden rad na trh, nie zošívanie
Inžinier skladá trezor z NQ (do 4/2019) a MNQ (od 5/2019), rovnako pri YM/MYM a GC/MGC. Ceny sú rovnaké, ale
**objem je iný rádovo**. Na mieste zošitia sa preto rozbije každá stratégia s objemom (VWAP, volume profile, rvol,
`volLookback`, SVP, MTK Zone).

**Protinávrh:** stiahnuť **NQ, YM a GC za celé obdobie 6/2010 – dnes** a výskum, ladenie aj trezory robiť na jednom
rade (plný kontrakt). Mikro (MNQ, MYM, MGC) sa použije len na exekúciu a demo. Prahy aj veľkosť pozície v ATR alebo
v USD riziku sa medzi plným a mikro kontraktom prenášajú 1 : 1. Platí to aj pre ES, kde sa už dnes ladí na ES.

## 2. Po trhoch

### ES — úprava dátumov
- **Súhlas** s „nové hypotézy na ES hneď“.
- **Protinávrh:** L 6. 6. 2010 – 30. 9. 2017 (7,3 roka) a B 1. 10. 2017 – 30. 9. 2021 (4,0 roka).
- Prečo:
  - B potom obsahuje **štyri rôzne režimy**: Volmageddon 2/2018, výpredaj Q4 2018, covid 3/2020 a QE býk 2021.
  - Trezor má ~400 obchodov pri 100 obchodoch za rok a 300 už pri 75 za rok. S rezervou splní pravidlo
    používateľa (≥ 2 roky, ≥ 300 obchodov, iný režim).
  - L 2010–17 je takmer celé nízka volatilita a QE. Trezor tým naozaj testuje iný svet.
- WF 24/6 na L 7,3 roka dá ~10 kúskov.
- B2 (2021–25) považujem za prakticky mŕtvy. Na 10/2021–9/2025 sa ladilo všetkých 85 rodín, takže „rodina, ktorá
  tam nebežala“ bude výnimka. Nech ostane v smernici, ale nikto s ním nemá počítať.
- DOHODA: ES nové = L 2010-06-06 – 2017-09-30 · B 2017-10-01 – 2021-09-30 · A spálený · C od commitu hraníc.
  Legacy ES = len C a T4b ako negatívna kontrola.

### MNQ a MYM — kým nie je NQ/YM
- **Súhlas:** B 6/2019 – 9/2021 (2,3 roka) pri 100 obchodoch za rok nesplní 300 obchodov.
- **Protinávrh pre prechodné obdobie:** nové hypotézy na Nasdaq a Dow sa nespúšťajú, kým nie je NQ/YM. Výnimka:
  hypotéza so **≥ 150 obchodmi za rok** smie mať L 6/2019 – 9/2023 (4,3 roka, WF 4 kúsky) a B 10/2023 – 3. 9. 2025
  (1,9 roka). Tá **nesplní ≥ 2 roky**, preto žiadna výnimka a čakať na NQ.
- Záver: **bez NQ a YM nemá Nasdaq ani Dow pre žiadnu hypotézu čistý trezor.** Stiahnutie NQ/YM je preto
  podmienkou, nie odporúčaním.
- **Po NQ/YM (celý rad 2010–2026):** rovnaké dátumy ako ES (L 2010–9/2017, B 10/2017–9/2021).
- **Legacy Nasdaq a Dow:** B′ = NQ/YM 6/2010 – 4/2019. Súhlas, s jednou úpravou.
  - Bodové prahy (IBS EZ: `fvgMinSize 58` a ďalšie) sa neprepočítavajú **pomerom ceny**, ale **pomerom mediánu
    denného ATR(14)** po rokoch (rok B′ / L). NQ mal v roku 2017 extrémne nízku volatilitu, takže pomer ceny by
    prahy skreslil o desiatky percent.
  - Ak legacy stratégia s bodovými prahmi po prepočte ATR spadne pod 300 obchodov, výsledok je ⏳, nie ❌.

### MGC — súhlas s GC, rovnaká úprava ako NQ
- **Súhlas:** čisté je len MGC 2020+. MTK ORB sa ladila na riedkych dátach.
- **Protinávrh:** **GC 10/2010 – dnes** ako jediný rad. Pokrytie treba najprv zmerať tým istým `dq_scan`
  (hranica ≥ 95 % jadro aj noc). Ak GC nesplní 2010–2012, začať od prvého roka, ktorý splní.
- Po GC nové: L 10/2010 – 9/2017, B 10/2017 – 9/2021 (plochý trh 2018, prieraz 2019, covid 2020 a pád 8/2020).
- Legacy zlato: B′ = GC 10/2010 – 12/2019. SPRÁVY ostávajú pre GC 2010–21 spálené (07).
- **Bez GC** ostáva zlato len s C (legacy aj nové). MGC L 1/2020 – 9/2023 a B 10/2023 – 9/2025 by mal ~2 roky, ale
  2023–25 je jediný býk. Pravidlo „iný režim“ nesplní.

### 6E — súhlas s rozdelením, podmienky na čistenie
- **Súhlas:** L 2016 – 9/2021 pre nové (WF ~7 kúskov) a B′ 2010–2015 po vyčistení. Nízka FX volatilita 2016–19
  oproti kríze eura 2010–12 dáva jasne iný režim.
- **Diera v čistení:** filter „skok > 0,3 % a hneď späť“ zmaže aj **skutočné** vrcholy pri správach (ECB a NFP vedia
  na minúte urobiť 30+ pipov a čiastočne sa vrátiť). Odstránenie skutočných knôtov zvýhodní stratégie s tesným
  stopom, čo je presne naša chyba fill modelu.
- DOHODA pre čistenie:
  - zmazať len skok, ktorý sa **do 1 min vráti z ≥ 80 %**, a len **mimo ±3 min od správ** z `calendar.json`,
  - pravidlo zapísať a commitnúť pred prvým behom stratégie na 2010–15,
  - zapísať počet zmenených sviečok po rokoch (cieľ ≤ 0,5 %; nad 1 % je rok ⏳).
- Ako kontrolu (nie zdroj) navrhujem porovnať 50 náhodných opravených minút s Dukascopy EURUSD. Dáta máme
  v archíve, nič sa nesťahuje.
- Legacy EUR = len C, kým nie je B′. Súhlas.

### BTC — zdroj áno, dátumy nie
- **Zdroj: súhlas** s Binance futures perp ako jediným zdrojom (pokrytie, objem, funding).
- **Podmienka:** náklad sa určuje podľa **miesta obchodovania**, nie podľa zdroja dát. Ak BTC pôjde naživo cez
  FTMO CFD, platí spread a swap CFD (§3 V2), nie 0,02 % maker Binance. Inak sa zopakuje chyba futures vs. CFD.
- **Nesúhlas s B′ = Binance spot 2017–19:**
  1. Používateľ chce **jeden zdroj BTC**.
  2. Binance spot vznikol 7/2017. Prvé mesiace mal tenkú likviditu a v rokoch 2017–18 sporný objem (wash trading),
     takže pre stratégie s objemom sú to neplatné dáta.
  3. Spot nemá funding a short.
  - DOHODA: BTC bez B′.
- **Dátumy:** Inžinierovo L 2021–25 a B 2019–21 dávajú trezor 2,1 roka a ~210 obchodov, teda pod 300. Navrhujem
  chronologické rozdelenie, aby bol trezor bližšie k dnešnému trhu:
  - L 8. 9. 2019 – 3. 9. 2023 (4,0 roka: covid, býk 2021, medveď 2022, FTX), WF 24/6 = 4 kúsky,
  - B 4. 9. 2023 – 3. 9. 2025 (2,0 roka: býk po ETF, apríl 2025),
  - požiadavka ≥ 150 obchodov za rok, inak B nedá 300 a výsledok je ⏳ do C.
  - Legacy BTC = len C (videla 2021–25 aj 2019–21).

## 3. Rolovanie — nesúhlas s „pri intraday nevadí“
Pri intraday vstupoch skok nevadí, ale **pri úrovniach z predošlej seansy áno.** PDH, PDL, predošlé zatvorenie,
overnight high/low, gap od včerajška, denné ATR, SMA 100 denných zavretí (nocpon), filter špičky 5/60 dní: v deň
rolovania sa všetky tieto úrovne počítajú zo starého kontraktu. Na MNQ je posun 0,9 % ≈ 200 bodov a na indexoch
nastáva 4× ročne. Stratégie s gapom a PDH (ON bias ORB, Daily open, NY VA, CRT, IB retrace) sú tým zasiahnuté
systematicky.

DOHODA:
1. Importér zapíše deň a skok každého rolovania do `rolls.json`.
2. Indikátory naprieč dňami (denné úrovne, ATR, SMA) sa počítajú na **ratio back-adjustovanom** rade, obchod a fill
   na surovom.
3. Kým to nie je hotové, platí `skipRoll` (deň rolovania + 1 seansa bez vstupov), predvolene zapnutý pre každú
   stratégiu, ktorá číta predošlú seansu.
4. Kontrola, že importér neprepína kontrakty tam a späť: počet prepnutí za rok má byť 4 pri indexoch a 6E a pri GC
   podľa aktívnych mesiacov. Viac znamená chybu. Inžinier to zmeria v `dq_scan`.

## 4. Dnešné stratégie (legacy)
- **Súhlas:** majú len B′ (po nových dátach) a C.
- Upresnenie: ak C slúži ako trezor, pravidlo „≥ 2 roky, ≥ 300 obchodov“ platí aj preň. Legacy bez B′ by sa ✅
  dočkala najskôr 12/2028.
- DOHODA: „Bez B′ dosiahne legacy najviac 🟡 (demo, malá veľkosť). C v prvých 8 týždňoch / 40 obchodoch slúži len na
  kontrolu exekúcie.“ Aj z toho dôvodu stiahnutie NQ, YM a GC rozhoduje o všetkom ostatnom.

## 5. Pomer L / trezor a WF 24/6
| trh | L (roky) | WF kúsky | trezor (roky) | ~obch. pri 100/r | iný režim v trezore |
|---|---|---|---|---|---|
| ES, NQ, YM nové | 7,3 | ~10 | 4,0 | ~400 | Volmageddon, Q4 2018, covid |
| GC nové | 7,0 | ~9 | 4,0 | ~400 | prieraz 2019, covid |
| 6E nové | 5,75 | ~7 | B′ 5,5 | ~550 | kríza eura vs. nízka vol. |
| BTC nové | 4,0 | 4 | 2,0 | ~200–300 | len pri ≥ 150 obch/rok |
| legacy (všetky) | 4,0 (zmrazené) | 4 | B′ / C | — | — |

**„Iný režim“ treba merať, nie tvrdiť.** DOHODA: trezor má aspoň jeden štvrťrok, v ktorom je medián denného ATR
podkladu (v %) mimo medzikvartilového rozpätia L, **alebo** pokles podkladu > 15 % od vrcholu, ktorý v L nebol.
Počíta sa pred behom stratégie a zapíše sa do hlavičky.

## 6. Dopĺňanie archívu pre C
- Archív dnes končí takto: ES 19. 10., MGC 16. 9., 6E 28. 9., BTC 4. 9., MNQ/MYM 9. 11.
- **Zdroj C musí byť ten istý ako zdroj L:** Databento mesačne pre futures, Binance perp pre BTC. Sviečky z hubu
  `livedata` sú z MT5 (CFD) alebo z feedu NT. Na trezor C **sa nepoužívajú**, slúžia len na kontrolu exekúcie.
  Iný feed by bol iný trh.
- DOHODA: mesačné dopĺňanie Databento (a NQ/YM/GC, keď budú) do `data/archive/tester/` po uzavretí mesiaca, ten istý
  `bento_import`. Diera medzi koncom archívu a štartom C sa doplní raz, slúži len na exekúciu.
- Pri BTC nesmie skript stiahnuť dáta mimo Binance perp.

## 7. Zhrnutie dohody
1. Jeden rad na trh (NQ, YM, GC, ES, 6E, Binance perp), mikro len na exekúciu.
2. Nové hypotézy: L do 9/2017, trezor 10/2017 – 9/2021 (ES hneď, NQ, YM a GC po stiahnutí). 6E: L 2016–21, B′
   2010–15 vyčistené. BTC: L 9/2019 – 9/2023, B 9/2023 – 9/2025.
3. Bez NQ, YM a GC nemá Nasdaq, Dow ani zlato čistý trezor. Stiahnutie je podmienka.
4. Rolovanie: `rolls.json`, back-adjust pre indikátory naprieč dňami, `skipRoll` do vtedy.
5. Legacy bez B′ dosiahne najviac 🟡. „Iný režim“ sa meria vopred.
