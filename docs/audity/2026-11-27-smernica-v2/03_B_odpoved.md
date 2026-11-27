# Agent B (Inžinier) — 2. kolo: odpoveď Prokurátorovi

*26. 11. 2026. Všetko som čítal, nič nespúšťal. Tvoje čísla som prepočítal sám z `gl_state.json` a `hyper_state.json`,
kód som prečítal na riadkoch, ktoré citujete, a živé inštancie som prečítal z `tester/live/mirror.sqlite`
(`-readonly`). Pri t-štatistikách ide o môj odhad z PF, počtu obchodov a predpokladaného WR (vzorec je v B1).*

Pán Prokurátor, vo väčšine máte pravdu a v niekoľkých bodoch je to ešte horšie, než píšete. Na troch miestach však
z dôkazu vyvodzujete viac, než unesie, a na dvoch nesedí, čo z neho plynie. Lepšie to opravím ja teraz, než aby to
neskôr urobil trh.

---

## 1. Verdikty A1–A20

| bod | verdikt | čo som overil / kde sa mýlite |
|---|---|---|
| **A1** počet pokusov | **platí** | Súčet `combos` v `gl_state` je 1 551 132 a `hyper_state.trials` 243 436, spolu ≈ 1,79 mil. Pokusy sú silne korelované, takže efektívne N je o 1–2 rády menšie. Aj tak 10³ na stratégiu ďaleko presahuje MinBTL (~45 na 5 rokov, Bailey a kol. 2014). Číslo „najlepšia z 1 000 náhodných dá PF ~1,3“ (KONVERZACIA §5) je len odhad, nikto ho nenasimuloval. Tento čiastkový argument by som nepoužíval ako dôkaz. |
| **A2** odložený rok nie je raz | **platí** | `glsearch.py:864` púšťa OOS pre každého kandidáta. `hyper_state` má 340 OOS kandidátov a `glwr.py:244` aj `glrr.py:140` ďalšie behy. `gldash.py:480` radí `sorted(passed, key=-oos PF)` a riadok `:490` berie `items[:3]`. `glaudit` radí triedu podľa `-oos` a pre A chce OOS ≥ 1,4. Toto je jadro celej veci. |
| **A3** medián OOS ≈ 1,0 | **platí** | Vašu tabuľku som zopakoval presne (TKS 1,42→1,03, top 1,74/1,66/1,57; NOA MGC 0,84; MTK Zone 0,88 atď.). Doplním štatistiku: medián TKS 1,03 pri ~157 obchodoch dáva t ≈ 0,2. Top 1,74 dáva t ≈ 3,3. Maximum z 90 korelovaných behov okolo nuly vychádza práve na +2,5 až +3 σ. Webapp teda dostáva presne to, čo dá šum. |
| **A4** IBS EZ meria režim | **čiastočne** | Záver je správny, dôkaz z MNQ však nie je čistý. IBS EZ má prahy v **bodoch** (`fvgMinSize` 58). Nasdaq bol v rokoch 2019–21 na 8–14 tis., takže prah 58 bodov tam znamenal inú stratégiu (sami to píšete v KONVERZACIA §2). Údaj „0/3 rokov“ na MNQ preto nemôže byť rozsudkom. Čistejší dôkaz je **IBS EZ ES: 0,75, 3 z 12 rokov** a MYM 0,79. Tie stačia aj samy. |
| **A5** brzdy nebrzdia | **platí** | `docs/SMERNICA_TESTOVANIA.md:153` píše, že DSR „nemá vplyv“, a riadok `:168` „ostáva prejdené“. Najvyšší DSR je 0,93. Aj keby N bolo nadhodnotené 100×, NOA, VWAP ORB a TKS by hranicu 0,95 stále nesplnili. Test proti náhode je jeden test bez korekcie na výber, ako píšem v 1. kole. |
| **A6** plató | **platí** | V `glsearch.py:804–818` sa bool a str preskakujú, testuje sa len ±1 krok v aktuálnej skupine a do webapp ide vrchol zoradený podľa OOS, nie stred plató. Hyperopt plató (±10 %) je rovnako lokálne. |
| **A7** staré roky znečistené | **platí** | `PERIODS["mtkorb"] = ("20101101-20240904", …)` je overené. MTK ORB na MGC 2020–21 je preto in-sample a v tabuľke nemá čo robiť. K tomu B1: samotné triedenie je viacnásobný test 44 stratégií. |
| **A8** dve smernice | **platí** | Repo `:94` a `:213` uvádza „150 — tvrdá hranica“, iCloud 75 a kód `MIN_TRADES_YEAR = 75`. `passes_is` aj `score` kontrolujú len priemer `trades / years`. Zákaz pre MTK RANGE („v každom roku“) do kódu nikdy nevošiel. |
| **A9** SPRÁVY | **platí a je to horšie** | `profil_3.json` má 8 pravidiel × (udalosť, od, do, vstup, držanie, stop, RR), teda **~40–50 voľných parametrov pri ~36 obchodoch za rok**. Parametrov je viac než obchodov za rok, čo je učebnicové preladenie. Navyše pravidlo **r3 NFP má `r3Enter: 0`, teda vstup presne v čase správy.** FTMO na Standard funded účte zakazuje otvárať a zatvárať pozície 2 min pred a po vybraných high-impact správach. Vo výzve je to povolené (FTMO FAQ). Či je „FTMO-Server3“ funded alebo výzva, z dát neviem. Treba to overiť **pred** ďalšou NFP. |
| **A10** filter po strate | **čiastočne** | Fakt sedí: `SMERNICE_CS_IBS_Entry_Zone_11.json` má `_comment` z 24. 11., `spikeMax 1,7`, titul „PF 1,61“ namiesto 1,53 a v `instances` beží na Server3. Motív (prah zvolený pozretím na november) je hypotéza, lebo git som podľa pravidiel nečítal. Pri hodnotení to však nehrá rolu: aj úprimne vopred zvolený filter pridáva ďalší stupeň voľnosti stratégii, ktorá staré roky nezvládla. |
| **A11** náklad v % | **čiastočne** | Na MGC, 6E a ES máte pravdu: 1,755e-5 dáva ~0,3–0,4 ticku na stranu, reál je 0,6–1 tick. Na MNQ pri dnešnej cene ~24 000 je to ~0,42 bodu ≈ **1,7 ticku**, teda nad odhadom repa 1,5, a podhodnotené sú len staré roky. Väčší problém ste podcenili: **živé účty sú CFD** (US100.cash, US500.cash, XAUUSD), kde je náklad v spreade a futures model tam vôbec neplatí. Treba to zmerať zo skutočných plnení. Na tom, že sklz na stope chýba úplne, sa zhodneme. |
| **A12** fill pri dotyku | **platí** | `emulator.py:214–220` plní limit pri `low <= price`, TP pri `high >= tp` a SL na presnej cene (sklz len pri medzere na otvorení minúty). SL pred TP je konzervatívne, to uznávam. Pri RR 0,5 a WR 74–76 % je rezerva ~8 p. b. nad break-even 66,7 %. Ak 5 % TP „pri dotyku“ neprejde a stopy dostanú 1 tick, rezerva zmizne. Overiteľné bez nových behov: v obchodoch spočítať TP, kde `tp == high` minúty. |
| **A13** futures vs CFD | **platí** | V `instances` majú všetky živé profily `_instrument mnq_databento`, ale bežia na `.cash`. |
| **A14** živé mimo backtestu | **čiastočne** | Proces zlyhal jednoznačne: pravidlo bolo zapísané a nevykonalo sa. Štatisticky to ešte nie je dôkaz. NOA má WR 4/19, pri očakávaných 41 % je P(≤4) ≈ **6 %**, čo je podozrivé, ale nie rozhodujúce. MC DD 95 % „2 100 $“ (`noanet/ANALYTIKA.md:187`) platí pre 1 MNQ na 60 k, kým živé −2 489 $ je na CFD lotoch, ktorých veľkosť som neoveril. Porovnávate možno jablká s hruškami. Šesť týždňov je pod MinTRL. Silný argument je tu zhoda obchodov 13/17, ktorá ukazuje na problém exekúcie. |
| **A15** jedna stávka | **platí, je to horšie** | Na Server3 som v `instances` našiel 9 inštancií: k NOA, TKS a IBS EZ 11 aj VWAP ORB, IBS EZ ES a NY VA ES (US500 má s US100 koreláciu ~0,9) a Fibo s SPRÁVY na XAU. Najnovší `last_seen` má dnes štvorica SPRÁVY, NOA, TKS a IBS EZ 11. |
| **A16** bez ochrany účtu | **platí** | V `adapters/mt5` je len „denný limit výhier“ (`TradeBotEA.mqh:147`). Na denný limit straty ani DD na equity som nenašiel nič v MT5, NT ani C# jadre. Jedinou „ochranou“ je breach u FTMO, a to je už samotná ruina, nie ochrana. |
| **A17** DD si protirečí | **čiastočne** | 1 080 $ (titul) je historický DD jednej cesty na ladení. 13,3 % (7 980 $) je 95. percentil Monte Carlo na 60 k a 7 150 $ v audite je iné okno. Sú to tri rôzne definície, nie protirečenie. Problém je v tom, že sa ukazujú bez označenia a nikde nie je určené, **ktoré číslo** sa použije na veľkosť pozície. Na sizing má ísť MC 95 % na dennom PnL portfólia (B6). |
| **A18** prevádzka | **platí** | Fakty pochádzajú z KONVERZACIA §1. Ide o prevádzkový bod, nie o príčinu straty edge. |
| **A19** kvalita dát | **čiastočne** | Riedke MGC pred 2020 sa týka len MTK ORB (ladená 2010–24) a MTK EMAS. Ostatné sa ladia od 10/2021 a 6E sa použilo až od 2016. Rozsah je menší, než naznačujete. |
| **A20** webapp ukazuje optimizmus | **platí** | Titul živého profilu ukazuje „posl. rok PF 1,79“, teda vybraný chvost, ako keby to bolo očakávanie. |

**Kde preháňate:** A4 (dôkaz z MNQ je skreslený bodovými prahmi), A14 (štatistika krátkeho live, nerovnaká
veľkosť), A17 (rôzne definície nie sú protirečenie) a A11 na MNQ. **Kde podceňujete:** A9 (počet parametrov SPRÁVY
a vstup na NFP v T+0), A15 (na Server3 bolo deväť inštancií) a CFD náklady v A11.

---

## 2. Čo ste prehliadli

**B1. Aj triedenie na starých rokoch je viacnásobný test.** Triedilo sa 44 stratégií (10 ✅, 15 ⚠, 19 ❌).
Pri ~460 obchodoch a skutočnom PF 1,0 dáva PF ≥ 1,10 t ≈ 1,0, čo nastane náhodou v ~16 % prípadov. Zo 44
stratégií bez edge by teda vyšlo **~5–7 falošných ✅**. Nášho 10 ✅ je len o málo viac, než dá náhoda. Váhu majú len
stratégie s t ≥ 3, čo zodpovedá Bonferroniho korekcii na 44 testov. Pomocou t ≈ m/σ·√n z PF, n a WR (40–50 %):

| ✅ zo starých rokov | PF | obch. | t (odhad) | nad prahom 3? |
|---|---|---|---|---|
| Williams R Long 6E | 1,41 | ~575 | **~4,1** | áno |
| Noc + pondelok MNQ | 1,55 | ~199 | **~3,0** | hranica |
| NOA EOD | 1,38 | ~351 | ~2,9 | takmer |
| ON bias ORB | 1,50 | ~173 | ~2,6 | nie |
| Volt Break | 1,28 | ~288 | ~2,1 | nie |
| NOA | 1,24 | ~351 | ~1,9 | nie |
| Daily open | 1,20 | ~337 | ~1,7 | nie |
| ORB 15/5 ES | 1,06 | ~2 033 | ~1,3 | nie |
| Range BTC | 1,16 | ~291 | ~1,3 | nie |

**B2. Bodové prahy znehodnocujú každý test na iných rokoch a trhoch.** Nejde len o IBS EZ. Každá stratégia
s prahom v bodoch alebo tickoch (nie v ATR či %) je pri inej cenovej hladine iná stratégia. Pred krokom 12 to treba
prepočítať, inak ❌ aj ✅ môžu byť artefakt.

**B3. Máme zadarmo kúsok skutočne nevideného OOS: 4. 9. 2026 až dnes.** Hľadanie končí OOS 4. 9. a archív MNQ ide
do 9. 11., takže sú to ~2 mesiace, ktoré nevidelo žiadne ladenie. Keďže živé sa rovná simulácii, je to aj most
k live. Na rozhodnutie je to krátke (~30 obchodov na stratégiu), ale ako **tretia nezávislá vzorka** pre všetky
profily naraz to použiť ide, raz a s hranicou zapísanou vopred. IBS EZ 11 je na tomto období už znečistená (A10).

**B4. Pásmo WR 70–100 % v pamäti je ladenie na winrate.** Pravidlo „WR 70–100 %, RR 0,5–2,0“ zo zásady testov
ide proti smernici („nikdy neladiť na winrate“). Tlačí hľadanie presne tam, kde fill model najviac klame (A12),
a vyžaduje RR 0,5, kde je break-even WR 66,7 %.

**B5. Výber stratégií je tiež pokus.** 85 stratégií × trhy × verzie (EOD, MYM, ES, BTC, EUR) na tých istých rokoch
tvorí rodinu testov. Každá nová stratégia, ktorá sa pridá „lebo predošlá nevyšla“, zväčšuje N, a nikto ju nepočíta.

**B6. Sizing a ruina sa nepočítajú na portfóliu podľa pravidiel propky.** `tester/prop.py` sám priznáva, že vidí
len uzavreté obchody. Chýba blokový bootstrap **denného** PnL živého portfólia s P(denná strata ≥ limit)
a P(DD ≥ celkový limit) za 12 mesiacov. Bez toho nevieme ani to, koľko lotov je „1 MNQ“ na FTMO.

---

## 3. Otázka (a): ako prestavať optimalizáciu a testovanie

Cieľ nie je, aby backtest vyzeral naživo rovnako. Cieľ je, aby číslo, ktoré ukazujeme, **už bolo očistené**
o výber, náklady a fill, a tak sa dalo naživo čakať. Navrhujem nasledujúci postup s pevnými prahmi. Prah sa mení
len zapísaním nového s dátumom, nikdy podľa výsledku.

**0. Rozdelenie dát raz a navždy (zapísať do repa, commit pred spustením).**
- **Ladenie:** 10/2021–9/2025, ako dnes.
- **Overovanie:** walk-forward vnútri ladenia (bod 3).
- **Trezor A:** 9/2025–9/2026. Odteraz je *spálený* na výber a smie sa len ukazovať.
- **Trezor B:** roky pred 10/2021 (ES 2010+, NQ 2010+ po stiahnutí, 6E 2016+, MGC 2020+).
- **Trezor C:** 9/2026 a ďalej (B3) plus demo.
- Na každý trezor sa pozrieme **raz na stratégiu** (nie na kandidáta), s hranicou zapísanou vopred, a nikdy podľa
  neho nezoraďujeme.

**1. Hypotéza a register pokusov.** Pred hľadaním treba 3 vety o tom, prečo má edge existovať (kto platí). Do
`register.jsonl` sa zapíše **každý** beh: mriežka, hyperopt, `glwr`, `glrr`, ručné behy aj zmeny kódu po pozretí
výsledkov. Ďalej sa počíta efektívne N, napr. počet zhlukov korelácie denných PnL > 0,9.
- **Rozpočet:** najviac 200 konfigurácií a 5 voľných parametrov (vrátane TF a bool) na stratégiu. Je to zámerne
  tvrdé: podľa MinBTL sa na 4 rokoch unesie rádovo 10–50 nezávislých pokusov.

**2. Náklady a fill už v ladení (nie až v strese).**
- **Náklad:** v tickoch podľa trhu (`half_spread_ticks` + poplatok), nie v %. Pre CFD spread nameraný zo živých
  plnení v `mirror.sqlite`.
- **Sklz:** +1 tick na každý stop a market vstup či výstup.
- **Limit a TP:** plnenie až pri **prechode o 1 tick** (`low < price − tick`), nie pri dotyku.
- **Bez cieľa na WR.** Pásmo WR 70–100 % zrušiť (B4) a RR < 0,7 povoliť len s výslovnou výnimkou.

**3. Walk-forward ako hlavná brána (Pardo).** Ladenie 24 mes., test 6 mes., posun o 6 mes., na 10/2021–9/2025
vyjdú 4 testovacie kúsky. V každom okne sa reoptimalizuje **tým istým automatom s tým istým rozpočtom**, aby
walk-forward meral proces, nie jedno nastavenie. Hranice:
- spojená OOS krivka PF ≥ 1,15 po nákladoch zo zásady 2,
- WFE (OOS / IS výkon) ≥ 0,5,
- ≥ 3 zo 4 kúskov v pluse,
- parametre medzi oknami sa nesmú skákať cez celý rozsah (kontrola stability).

**4. Štatistické brány (zo zaregistrovaného N).**
- **PBO cez CSCV** (S = 16 blokov z mesačného PnL všetkých konfigurácií v registri): ≤ 0,20.
- **DSR** pri efektívnom N: ≥ 0,95. Bude to **brána**, nie informácia.
- **Haircut Sharpe** (Harvey–Liu, BHY): na stránke a vo webapp sa ukazuje **ohaircutované** očakávanie a PF
  z ladenia len menším písmom.
- **Sila:** na každom trezore t ≥ 2,0 (pri rodine > 20 stratégií t ≥ 3,0) a ≥ 300 obchodov spolu v trezoroch.
  Pod 300 obchodov je výsledok „⏳ nepotvrdený“, nie ✅.

**5. Trezor B (krok 12) a iné aktívum.** Raz, bez úprav, prahy v ATR alebo % (B2). Hranica:
- PF ≥ 1,10 po nákladoch zo zásady 2,
- ≥ 60 % rokov v pluse,
- t ≥ 2 (resp. 3, ak sa naraz posudzuje celá rodina).

Iné aktívum znamená iný podklad (MNQ → ES, MYM, DAX; MGC → SI; 6E → 6B) bez zmeny parametrov s PF > 1,0. Dukascopy
CFD sa robí len ako test zdroja dát.

**6. Portfólio a prop (pred demom).**
- Blokový bootstrap denného PnL všetkých stratégií, ktoré majú bežať na jednom účte.
- **P(denná strata ≥ 5 %) ≤ 2 % a P(DD ≥ 10 %) ≤ 5 % za 12 mesiacov.** Z toho sa vypočíta veľkosť v lotoch.
- Najviac 2 stratégie na jeden index v tom istom časovom okne.
- Pred správami: kontrola pravidiel účtu (2 min okolo high-impact správ na funded účte).

**7. Tvrdá ochrana v kóde (podmienka, nie odporúčanie).**
- EA a NT: denný stop účtu na equity (napr. 2,5 % pri limite 5 %), celkový stop na 7 % a automatické
  `pause` stratégie pri DD > MC 95 %.
- Alarm, keď inštancia neposlala heartbeat > 30 min alebo sa obchod nezhoduje so simuláciou.

**8. Demo / forward ako trezor C.** Najmenej 8 týždňov a ≥ 40 obchodov na stratégiu na tom istom brokeri a
inštrumente ako ostrý účet. Hranice:
- zhoda obchodov ≥ 95 %,
- priemerný sklz ≤ model zo zásady 2,
- PF dema nie je štatisticky horší ako ohaircutované očakávanie (jednostranný test, p > 0,1).

Vypnutie riadi sekvenčný test (SPRT/PSR) proti očakávaniu, nie pravidlo „PF < 1 po 50 obchodoch“. **Po strate sa
na danom období nič nedolaďuje.** Zmena znamená nový kandidát a nový register.

**Čo z toho čakať:** ak tieto brány prejde stratégia s PF 1,25 po ohaircutovaní, naživo môžeme rozumne čakať
PF 1,1–1,25. Hodnoty 1,5–1,8 z dnešných titulov naživo čakať nemôžeme. Kto chce vidieť PF 1,5 aj naživo, chce
niečo, čo literatúra pri intraday futures a 150 obchodoch za rok takmer nedokladá.

---

## 4. Otázka (b): funguje naozaj niečo?

Váš zoznam kandidátov a mŕtvych z väčšej časti prijímam, s tromi opravami.

**Najsilnejší dôkaz (stále nie „zarába“, ale „stojí za čistý forward“):**
1. **Williams R Long 6E.** Na trezore B má t ≈ 4,1 a 6/6 rokov a sedí s ladením (1,53 vs 1,54). Vyšla z 3 477
   pokusov, čo je málo. Ako správne píšete, na ES (0,67) a MGC (1,08) nefunguje, takže ide o jav eura, nie princíp.
   Chýba jej náklad v tickoch a sklz (6E 1 tick = 6,25 $).
2. **Noc + pondelok MNQ.** Má t ≈ 3,0 a 3/3 roky a jasný dôvod (overnight drift je v literatúre zdokumentovaný).
   **Oprava:** verzia MYM nie je „malý priestor hľadania“. `nocponmym` má 14 785 kombinácií a 29 kandidátov a
   `nocpon` má v `gl_state` 0, teda nevieme, odkiaľ jeho profil je ani koľko pokusov ho stálo. Bez registra
   pokusov tu nemáme ako spočítať DSR.
3. **NOA EOD (t ≈ 2,9) a NOA (t ≈ 1,9).** Sú to jediné živé stratégie s plusom na trezore B. Naživo však WR 21 %
   a zhoda 13/17 znamenajú, že **sme zatiaľ neobchodovali tú stratégiu, ktorú sme testovali.** Najprv treba opraviť
   exekúciu, potom spustiť demo.

**Slabé, len ako hypotéza:** ON bias ORB (t 2,6, ale 0 kandidátov z automatu, takže profil prišiel odinakiaľ),
Volt Break (t 2,1, DSR 0,89, čo je najlepší pomer pokusov a výsledku z MNQ stratégií), Daily open (t 1,7).
**ORB 15/5 ES** má 11 rokov, ale t ≈ 1,3 a PF pred poplatkami 1,22. Sklz +1 tick ju podľa odhadu posunie pod
1,0, takže ju radím k mŕtvym, nie ku kandidátom. **Range BTC** má t ≈ 1,3, čo je šum.

**Mŕtve:** váš zoznam prijímam. IBS EZ na MNQ preradzujem z „isto mŕtvej“ na „mŕtvu, s nečistým dôkazom“ (B2).
Verzia ES (3/12 rokov) a MYM ju však aj tak pochovávajú. TKS a VWAP ORB sú mŕtve: medián OOS ~1,0 a staré roky pod 1.

**SPRÁVY:** sú neoveriteľné **a** nebezpečné (40+ parametrov na 36 obchodov za rok, NFP v T+0 proti pravidlu
FTMO). Na funded účet nepatria, kým sa neoverí typ účtu a trezor B s doplneným kalendárom.

**Odpoveď na otázku (b) jednou vetou:** dnes **nemáme ani jednu stratégiu s dôkazom, že po reálnych nákladoch
naživo zarába.** Dve majú dôkaz, ktorý by obstál pred recenzentom (Williams R 6E, Noc + pondelok MNQ, s výhradou
počtu pokusov), a jedna (NOA) má dôkaz na papieri, ale nie na účte. Všetko ostatné, čo dnes beží naživo (TKS,
IBS EZ 11, SPRÁVY), sa podľa dát nedá obhájiť. Odporúčam ich zastaviť a nechať ďalej bežať len demo.

---

**Zdroje použité v tomto kole:** pozri `02_B_vyskum.md` §4. K tomu pravidlo FTMO o správach (FTMO FAQ „Can I trade
news“, https://ftmo.com/en/faq/can-i-trade-news/; 2 min pred a po správe na funded Standard účte, vo výzve
povolené; presné znenie overiť v aktuálnych podmienkach).
