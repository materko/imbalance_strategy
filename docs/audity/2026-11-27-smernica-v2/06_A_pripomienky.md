# Agent A (Prokurátor) — 5. kolo: pripomienky k SMERNICA_V2

*26. 11. 2026, len čítanie. V kóde som overil: `glsearch.py:595–606` (`PERIODS` EUR), `.nightsearch/base_nocpon.json`,
`base_noa.json`, `ibsentryesnet/configs/PRESIEL_SMERNICAMI_IBS_EZ_ES_1.json` a formát udalostí `m1` / `order`
v `tester/live/mirror.sqlite`.*

Pán Inžinier, smernicu podporujem v celku. Nižšie sú len úpravy a diery. Kde sa zhodneme, píšem **DOHODA:** so
znením, ktoré navrhujem prevziať.

## 0. Vaše nové tvrdenia: všetky tri sedia, beriem ich
- **Williams R 6E:** `PERIODS["wpreur"] = ("20160101-20211001", "20211001-20260904", …)`. Ladila sa na 2016–9/2021,
  takže ✅ zo starých rokov je tautológia. Dodávam, že ani 10/2021–9/2026 nie je čisté. `gl_state` má pre `wpreur`
  9 OOS behov, z nich 1 prešiel, a profil sa vybral podľa nich. Medián 1,16 je dobrý znak, nie dôkaz.
- **Noc + pondelok:** `base_nocpon.json` píše „z prieskumu Nasdaqu: MNQ 2019–2026“. Prieskum videl všetko vrátane
  roka A, takže **⏳**.
- **IBS EZ ES:** všetky prahy sú `{"unit": "atr"}`. Moja námietka k ES padá a 0,75 (3/12) je čistý negatívny dôkaz.
- Záver, na ktorom sa zhodneme: **dnes nemáme ani jeden čistý pozitívny dôkaz.** ✅ môže vzniknúť len z B′ alebo C.

## 1. Krok po kroku

**§0 Pojmy — súhlas, jedno doplnenie.**
Doplniť vetu: „Každá štúdia alebo prieskum (KLZAKY-STUDIA, EUR-PRIESKUM, výskum SPRÁV, prieskum Nasdaqu) je pokus
a **spáli obdobia, ktoré videla**, pre všetky hypotézy z neho odvodené.“ Dnes je to spomenuté len pri bonuse
v §2. Platí to však všeobecne a práve takto sa spálili `nocpon` aj SPRÁVY.

**§1 Trezory — úprava.**
- **Rok A pre 6E** je 10/2021–9/2026 a je spálený, lebo sa podľa neho vyberalo. **T4 v P7 je teda len negatívna
  kontrola.** DOHODA: „T4 Williams R 6E na 10/2021–9/2026 s fill v2: PF < 1,05 → ❌, inak ⏳. ✅ len cez trezor C.“
- **Trezor B pre nové hypotézy nie je celkom čistý.** Rodiny ORB, IBS, VWAP, NOA, Sigma a IVB na ňom už triedenie
  videlo. DOHODA: „Trezor B je čistý len pre hypotézu, ktorej rodina na ňom ešte nebežala. Pre ostatné je
  negatívnou kontrolou.“
- **Trezor C:** hranice treba zapísať do 30. 11., teda o 4 dni. Ak to nestihneme, C začne až prvým dňom po commite
  hraníc, nie 1. 12. DOHODA v tomto znení.

**§2 Register a rozpočet — súhlas s 300 / 5. Diera v bonuse za ekonomický dôvod.**
Dôvod vie napísať každý a bonus −0,3 t a ½ N_eff si zapíše každý, kto ho chce. DOHODA: „Bonus platí len vtedy, ak
(1) hlavička s dôvodom je commitnutá pred prvým behom rodiny, (2) dôvod cituje vonkajší zdroj publikovaný pred naším
prvým pohľadom na dáta, alebo predpovedá **vedľajší jav**, ktorý sa overí samostatným testom s N = 1 (napr. drift
v surových výnosoch okolo FOMC bez pravidiel stratégie) a ten test prejde.“ Ďalšie doplnenie: susedia v plató
(krok 5, ~30 na kandidáta) sa zarátajú do 300, takže kandidátov bude najviac ~5. Treba to napísať, aby nikto nežiadal
navýšenie.

**§3 Náklady a fill — súhlas s tabuľkou. Pri CFD je diera v meraní.**
Udalosť `m1` v zrkadle má len `o h l c v` a `order`/`fill` len cenu. **Bid, ask ani spread sa nezapisujú**, takže
„p75 spreadu zo zrkadla“ sa zmerať nedá. DOHODA:
- EA a NT pri každom fill zapíšu `bid`, `ask`, `spread` a čas tiku. Do vtedy sa pre CFD berie spread zo zmluvy
  brokera × 1,5.
- Pre stratégie obchodujúce okolo správ sa spread meria **v okne ±5 min okolo správy** zvlášť (na XAU a US100 býva
  pri NFP a CPI násobný). Priemer dňa by SPRÁVY systematicky zvýhodnil.

**§4 Krok 1 — súhlas.** Krok 3 — súhlas.

**Krok 4 — úprava znenia** (spor min. obchodov rieši §2 nižšie). Doplniť: „Vrchol hľadania sa nikdy nezobrazuje ako
očakávanie.“

**Krok 5 plató — súhlas.** Doplniť: „Susedia sa počítajú do rozpočtu.“

**Krok 6 WF — súhlas, dve diery.**
1. **Opakovanie WF:** WF nevyjde, upraví sa mriežka a pustí sa znova. DOHODA: „WF má rovnaký jednorazový zámok ako
   trezor (`vaults.json`). Druhý WF = nová hypotéza.“
2. **Rozpočet:** reoptimalizácia v oknách (≤ 300 / okná) je replay procesu. DOHODA: „Behy WF sa zapisujú do
   registra, nemenia finálnu konfiguráciu a do N pre DSR sa nepočítajú. Do N sa počítajú len pokusy kroku 4 a 5.“

**Krok 7 — súhlas s metódou. Úprava haircutu.** „Ohaircutovaný SR > 0“ je pre zobrazenie očakávania príliš slabé.
DOHODA: „Brána je ohaircutovaný SR > 0. Do titulu ide ohaircutovaný PF. Ak je < 1,10, stav je ⏳ (nevyplatí sa
nákladom na prevádzku).“

**Krok 8b — veľká diera: salámová dávka.** t_req závisí od počtu hypotéz „v dávke“. Kto ich pošle po jednej,
dostane vždy t_req 2,0. DOHODA: „Počet hypotéz pre t_req = **kumulatívny počet hypotéz, ktoré sa kedy pozreli na
daný trezor** (počíta `vaults.json`), nie veľkosť dávky.“ Pre B′ to dnes znamená, že legacy dávka (~18) plus nové
dávajú t_req ≥ 3,0. Jednostranný test by bol obhájiteľný, lebo smer je daný. Obojstranný nechávam ako rezervu na
korelované pokusy.

**Krok 8c — súhlas s vaším N2.** DOHODA (znenie §8 podľa B) s podmienkou: „Prenos na príbuzný trh len v jednotkách
ATR alebo %. Pri bodových prahoch je výsledok ⏳.“ Doplniť: pre 6E nemáme v archíve príbuzný trh (6B, 6J), takže
negatívny test 8c sa nedá urobiť a výsledok je ⏳, nie preskočenie.

**Krok 9 — úprava režimov.** Dnešné znenie sa nedá vyhodnotiť jednoznačne. DOHODA: „Obchody rozdelené na tercily
podľa ATR(20 dní) v deň vstupu. Žiadny tercil nesmie mať PF < 0,90. Ani jeden tercil nesmie niesť > 60 % zisku.“
Fill citlivosť (T2) je pri fill v2 nadbytočná pre nové hypotézy. Nechať ju len pre legacy.

**Krok 10 legacy — súhlas. Diera v N = 1 pre NOA (T6).** Článok Zarattini a kol. vyberal pravidlá na SPY
**2007–2024**. NQ 2010–2019 je teda obdobie, ktoré autori videli, a NQ intraday je so SPY silne korelovaný
(hypotéza ~0,9). T6 na NQ 2010–19 je in-sample autorov. **Čisté je len obdobie po publikácii:** MNQ od 6/2024
s parametrami presne podľa `base_noa.json` (16. 10.), bez výberu medzi variantmi. Máme ho a sú to ~2,4 roka, ~350
obchodov. DOHODA: „T6 = NOA podľa článku na MNQ 6/2024–9/2026 (primárne) a NQ 2010–2019 (sekundárne, len
negatívna kontrola). Hranica: PF ≥ 1,10 a t ≥ 2,0 na primárnom, PF ≥ 1,0 na sekundárnom.“ Pozor: preklad zo SPY
na MNQ (poistka 1 %, 14 dní × 1, kontrola 30 min) urobil človek. Zapíše sa ako N = 3, nie 1.

**Krok 11 portfólio a prop — súhlas, dve doplnenia.**
1. **Trailing DD:** Tradeify (a väčšina futures propiek) má trailing drawdown (EOD alebo intraday), nie statický.
   DOHODA: „Simulácia používa presný typ DD účtu (statický, trailing EOD, trailing intraday) zo zmluvy.“
2. **Súčasné riziko:** pravidlo „2 stratégie na index“ nezabráni trom pozíciám naraz. DOHODA: „Pred každým vstupom
   kontrola: súčet rizika na stopoch všetkých otvorených pozícií účtu + nový obchod ≤ 1,5 % účtu, inak sa vstup
   neodošle.“ Patrí aj do kroku 14 (kód).

**Krok 12 demo — úprava.** Pri ~150 obchodoch za rok trvá 40 obchodov ~13 týždňov. DOHODA: „≥ 8 týždňov **a**
≥ 40 obchodov, platí to, čo nastane neskôr.“ Demo server plní ideálnejšie než ostrý. Doplniť: „Prvých 40 ostrých
obchodov (50 % veľkosti) sa porovná so sklzom dema. Medián sklzu ostrého > 2× demo → pause.“

**Krok 13 — súhlas.** **Krok 14 — súhlas** s −2 % a −6 % plus pre-trade kontrola 1,5 % (krok 11). Doplniť: „Ochrana
musí fungovať aj bez hubu a bez Mac mini (lokálne v EA a NT), lebo výpadok hubu nesmie vypnúť stop.“

**§5 webapp — súhlas.** Doplniť: karta Výkon a titul nesmú brať rok A do žiadneho súčtu. Ranná úloha
`glwebvyber.py --apply` sa vypne, kým neprepne poradie na stavy V2. Dnes každé ráno obnovuje poradie podľa OOS.

**§6 automat — súhlas.** Doplniť, že register musí mať **hash commitu kódu** stratégie pri každom pokuse. Zmena
kódu po pozretí výsledkov sa tak dá dohľadať (§2 ju počíta ako pokus, ale bez hashu ju nikto nezistí).

**§7 prechod — SPRÁVY, úprava.**
- Uznávam ekonomický dôvod. Používateľ potvrdil, že účet smie obchodovať správy, takže argument o NFP sťahujem.
- Podľa vlastného §2 V2 má však dnešný profil (8 pravidiel, ~40–50 parametrov) **> 5 voľných parametrov**. Legacy
  ⚠ preto ostáva bez ohľadu na trezor B.
- DSR 0,959: overiť, s akým N bol počítaný. Výskum mal 2 302 kombinácií + 125 RRR + 3 seedy, a ak bol N menší,
  prepočítať.
- DOHODA: „SPRÁVY = dve veci. (a) Legacy profil_1–4: ⚠, naživo len rozhodnutím používateľa, odporúčanie A: 50 %
  veľkosti, kým nie je trezor B (kalendár 2016–20) a spread pri správach (§3). (b) Nová hypotéza SPRÁVY-jadro:
  ≤ 5 parametrov, typy udalostí vybrané mechanizmom vopred (napr. FOMC drift, CPI), header pred behom, trezor B
  s kalendárom 2016–20 a GC 2010–19, bonus za dôvod podľa §2.“

**§10 odhad — súhlas.** Prioritu ochrany účtu (krok 14) pred fill v2 potvrdzujem.

## 2. Sporné body §8

- **Min. obchodov.** DOHODA: „≥ 100 obchodov v **každom** roku L a pomerne v každom WF kúsku. Hypotéza pod 100 (napr.
  SPRÁVY, trend CFD) len s výnimkou zapísanou v hlavičke **pred** behom. Vtedy t_req + 0,5 na trezore a ≥ 300
  obchodov spolu v trezoroch.“ Dôvod: pri 75 za rok a 4 rokoch je SE PF ≈ ±0,2. Vaše t na trezore štatistiku
  ustráži, ale nezabráni výberu šťastia v kroku 4 pri 300 pokusoch. 150 je pre zlato a 6E zbytočne tvrdé.
- **NOA.** DOHODA: „Ladené profily NOA = ⚠ legacy, na Server3 pozastaviť do T3. NOA podľa článku = nová hypotéza,
  T6 v znení z kroku 10 vyššie (po publikácii primárne). Naživo len po T6 a demo kroku 12.“
- **Iný index (N2).** DOHODA: znenie B + podmienka ATR/% (krok 8c vyššie).
- **ORB 15/5 ES.** DOHODA: T4b, ale trezor B pre ES je spálený triedením, takže **PF < 1,0 → ❌, PF ≥ 1,03 → ⚠
  (nie ✅)**. ✅ len cez C.
- **Denný stop.** DOHODA: −2 % denne a −6 % celkovo z equity, k tomu kontrola súčasného rizika 1,5 % (krok 11 a 14).
  Prehodnotiť po T5.

## 3. Čo v V2 ešte chýba (doplniť)
1. **Jedna smernica, jeden súbor:** platí len `docs/SMERNICA_TESTOVANIA.md` v repe. iCloud obsahuje len odkaz.
   Dnešný rozpor 150 / 75 vznikol z dvoch kópií.
2. **Strop nových hypotéz:** najviac 10 nových hypotéz za štvrťrok na jeden trezor. Inak t_req rastie a „rodiny“
   (B5) sa vrátia oknom.
3. **Brány v kóde, nie v dokumente:** stav ✅ smie zapísať len skript, ktorý brány prepočíta z registra. Ručný
   zápis ✅ je vylúčený (dnes je `APPROVED = {"spravyeur"}` v `glwebvyber.py` presne taká výnimka).
4. **CFD replay:** L beží na futures, ostré na CFD. Pred demom pustiť stratégiu bez zmeny na m1 sviečkach brokera
   zo zrkadla (október–november, len na exekúciu, D4). Zhoda signálov ≥ 90 % proti futures behu, inak sa feed
   brokera berie ako iný trh.
5. **Zodpovednosť:** kto podpisuje prechod ⏳ → demo → ostré (používateľ), zapísané v registri s dátumom. AI agent
   stav nikdy nemení sám.

**Zhrnutie:** V2 s týmito úpravami podpíšem. Ostávajú len sporné body, ktoré sú vyššie vyriešené ako DOHODA.
Žiadny ďalší spor neotváram.
