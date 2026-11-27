# Agent A (Prokurátor) — 1. kolo

Stav k 26. 11. 2026, Mac mini. Všetko len čítané. Čísla z `.nightsearch/gl_state.json` a `hyper_state.json` som
prepočítal sám (skript len na čítanie). „Hypotéza“ = nemám priamy dôkaz.

**Obžaloba v jednej vete:** smernica má poctivú techniku (parita C#, lookahead, 1m detail, SL pred TP), ale
**výber** je postavený tak, že spoľahlivo vyťahuje šťastné nastavenia: ~1,8 mil. pokusov, ten istý „odložený“ rok
pustený vyše 2 300-krát a použitý na **poradie**, brzdy proti viacnásobnému testovaniu sa počítajú, ale nebrzdia.
Na živých účtoch beží korelovaný balík Nasdaq stratégií bez denného stop-lossu účtu. Staré roky (OOS-STARE-ROKY) a
živé výsledky to už potvrdzujú.

---

## Časť I — Preoptimalizovanie (ťažisko)

### A1. Počet pokusov je o rády vyšší, než unesú hranice smernice — kritické
- **Dôkaz:** `gl_state.json`: spolu **1 551 132** kombinácií mriežky na 85 stratégií; `hyper_state.json`: ďalších
  **243 436** pokusov Optuny → **≈ 1,8 mil.** Na jednu stratégiu: TKS 82 129 (ranný priebeh 26. 11. uvádza 103 779 aj
  s hyperoptom), NOA 37 700 (priebeh 76 305), Fibo MGC 43 743 (66 796), Mag7 45 167, MTK Zone 42 589. Ďalšie hľadania
  na tých istých dátach sa do počtu nezarátali: `glwr.py` (top 32 webapp znova, RR 1 → 0,75 → 0,5), `glrr.py`.
- Smernica `docs/SMERNICA_TESTOVANIA.md:98` sprísňuje hranice len raz, pri „nad 1000 kombinácií“: OOS PF 1,3 namiesto
  1,2. Medzi 1 000 a 100 000 pokusmi už nič ďalšie neprituhne.
- **Prečo krach:** maximum z 10⁴–10⁵ korelovaných pokusov pri ~600 obchodoch dá PF 1,3–1,5 aj bez edge. Odhad
  z `OOS-STARE-ROKY/KONVERZACIA_2026-11-26.md` §5 hovorí toto: najlepšia z 1 000 náhodných dá PF ~1,3 len z náhody.
  My máme 10–80× viac pokusov na stratégiu.

### A2. „Odložený rok spustený raz“ v skutočnosti nie je raz. Je to tretia vzorka na výber — kritické
- **Dôkaz:** `glsearch.py:864` pustí `evaluate(key, S["cur"], oos_tr(key))` pre **každého** kandidáta, nie raz pre
  stratégiu. Komentár „raz, nikdy na ladenie“ platí pre jedno nastavenie, nie pre stratégiu. Spočítal som to:
  **1 965** OOS behov v `gl_state` a **340** v `hyper_state`. K tomu `glwr.py:244` a `glrr.py:140` púšťajú `G.OOS`
  ďalej. Spolu teda **> 2 300 behov** na roku 20250904–20260904. Na stratégiu: NOA 185, TKS 90, Sigma MNQ 70,
  NOA BTC 68, IVB 61.
- **Výber podľa OOS:** `gldash.py:480` zoradí prejdené `sorted(passed, key=-oos PF)` a `:490` vezme `items[:3]`.
  Z nich sú PRESIEL_SMERNICAMI_1..3, a tie podľa `glwebvyber.py` (MAP, `page_top`) idú do webapp a do LIVE.
- Audit triedy A (`glaudit.py:79/111`) chce „odložený rok PF ≥ 1,4“. Odložený rok teda rozhoduje aj o triede.
- Pamäť `test-defaults-all-strategies.md` to pomenúva sama: „hlavné je posledný rok … poradie výsledkov podľa
  posledného roka“. Tituly živých profilov nesú „posl. rok PF 1,77 / 1,79 / 1,52“
  (`tester/profiles/SMERNICE_CS_TKS_1.json`, `…IBS_Entry_Zone_11.json`, `…NOA_1.json`).
- **Prečo krach:** odložený rok je de facto in-sample. Už nič neoverovalo, že vybrané nastavenie funguje mimo
  vzorky. Na papieri máme tri vzorky, v skutočnosti nula.

### A3. Výberová zrážka je merateľná: medián kandidátov na OOS ≈ 1,0, do webapp idú chvosty 1,5–1,8 — kritické
Môj prepočet z `gl_state.json` (kandidáti, ktorí prešli ladením aj plató a potom bežali na OOS):

| stratégia | kombinácií | OOS behov | prešlo | medián IS PF | **medián OOS PF** | top 3 OOS (→ webapp) | staré roky (VYSLEDKY_TRIEDENIA) |
|---|---|---|---|---|---|---|---|
| TKS (živá) | 82 129 | 90 | 12 | 1,42 | **1,03** | 1,74 · 1,66 · 1,57 | **0,94 ❌** |
| VWAP ORB (živá) | 17 360 | 39 | 6 | 1,42 | **1,01** | 1,53 · 1,51 · 1,51 | **0,96 ❌** |
| NOA (živá) | 37 700 | 185 | 10 | 1,47 | 1,11 | 1,45 · 1,43 · 1,40 | 1,24 ✅ |
| IBS EZ (živá) | 13 808 | 24 | 12 | 1,35 | 1,26 | 1,79 · 1,77 · 1,74 | **0,79 ❌ (0/3 r.)** |
| VWAP ADX (živá) | 4 861 | 5 | 1 | 1,54 | 1,21 | 1,32 | 1,06 ⚠ |
| IBS EZ ES (živá) | 24 564 | 27 | 1 | 1,35 | 1,14 | 1,40 | **0,75 ❌** |
| NY VA ES (živá) | 12 416 | 17 | 3 | 1,35 | **1,01** | 1,34 · 1,34 · 1,32 | **0,81 ❌** |
| Fibo MGC (živá) | 43 743 | 30 | 11 | 1,34 | 1,27 | 1,46 · 1,46 · 1,42 | 1,06 ⚠ |
| Sigma MNQ | 16 189 | 70 | 3 | 1,49 | **1,01** | 1,67 · 1,51 · 1,35 | 1,04 ⚠ |
| Sigma MGC | 17 336 | 58 | 7 | 1,34 | 1,08 | 1,70 · 1,59 · 1,54 | **0,95 ❌** |
| NOA MGC | 11 857 | 43 | 4 | 1,45 | **0,84** | 1,79 · 1,56 · 1,49 | **0,59 ❌** |
| IVB ES | 33 474 | 45 | 4 | 1,46 | **0,97** | 1,79 · 1,77 · 1,61 | **0,71 ❌** |
| IVB MNQ | 33 035 | 61 | 7 | 1,47 | 1,02 | 1,63 · 1,40 · 1,32 | **0,79 ❌** |
| MTK Zone | 42 589 | 89 | 2 | 1,74 | **0,88** | 1,95 · 1,88 | 1,15 ⚠ |
| Williams R ES | 19 666 | 19 | 7 | 1,44 | 1,15 | 2,01 · 1,99 · 1,44 | **0,67 ❌** |
| Volt Break | 6 116 | 18 | 9 | 1,44 | 1,29 | 1,43 · 1,43 · 1,39 | 1,28 ✅ |
| SVP | 11 177 | 11 | 6 | 1,33 | 1,33 | 1,58 · 1,47 · 1,47 | 1,02 ⚠ |

- **Vzorec:** kde je medián kandidátov na OOS okolo 1,0 (TKS, VWAP ORB, NY VA, Sigma, IVB, NOA MGC, MTK Zone), tam je
  „prešiel“ len pravý chvost tej istej náhody. Staré roky to potvrdili takmer všade. Obstáli hlavne stratégie
  s malým priestorom hľadania (Volt Break 6 116, ON bias ORB 4 896) alebo s jasným dôvodom (noc/pondelok).
- **Prečo krach:** čo je vo webapp a na LIVE, je systematicky to najšťastnejšie z rozdelenia, ktoré má stred ~1,0.
  Po poplatkoch a sklze je očakávanie ≤ 0.

### A4. IBS EZ: aj „celá rodina dobre na OOS“ zlyhala. Jeden odložený rok meria režim, nie edge — kritické
- **Dôkaz:** IBS EZ má najlepší medián kandidátov na OOS (1,26, 12 z 24 prešlo), test proti náhode **+8,5 σ**
  (`tradebot/strategies/ibsentry/docs/ANALYTIKA.md:24`), audit triedy A (`TYZDEN-2026-11/AUDIT_2026-11-26.md`:
  „IBS Entry Zone … 1,81 … ● beží“). Na rokoch 6/2019–9/2021 má PF **0,79, 0 z 3 rokov v pluse**, EOD 0,74, MYM
  0,79, ES 0,75 (`VYSLEDKY_TRIEDENIA.md`).
- **Prečo krach:** rok 9/2025–9/2026 bol pre túto rodinu stratégií priaznivý režim. Jeden rok, rovnaký pre všetkých
  85 kandidátov, nevie odlíšiť edge od režimu. Naživo je to živá stratégia s najväčšou expozíciou (A15).

### A5. Brzdy proti viacnásobnému testovaniu sa vyrábajú, ale o ničom nerozhodujú — kritické
- **Deflated Sharpe:** `ROBUSTNOST_2026-10-29.md` uvádza DSR NOA 0,33 pri 37 700, VWAP ORB 0,75, TKS 0,79, Fibo 0,11,
  NY VA 0,01, CRT 0,01, JSS 0,00 pri hranici ≥ 0,95. **Ani jedna stratégia hranicu nesplnila.** Smernica
  `docs/SMERNICA_TESTOVANIA.md:153`: „Výsledok na prejdenie smernicou nemá vplyv“, riadok `:168`: „Nastavenie ostáva
  prejdené“.
- **Test proti náhode** (`checkup`, napr. TKS +5,5 σ, NOA +5,0 σ, IBS EZ +8,5 σ) sa počíta na tých istých dátach,
  na ktorých sa ladilo, a bez korekcie na počet pokusov. Po výbere z 10⁴ je preto bezcenný. IBS EZ s +8,5 σ zlyhala
  na starých rokoch.
- **Sprísnenie** „nad 1000 kombinácií … test proti náhode lepší než 99 %“ (`SMERNICA:98–99`) automat nekontroluje.
  `gldash.py:465` sprísni len OOS PF na 1,3.
- **PBO** „tu zatiaľ nie je“ (SMERNICA, krok 9).
- **Prečo krach:** jediné nástroje, ktoré by preladenie odhalili, majú v smernici status „len informácia“.

### A6. Plató a „4 parametre naraz“ chránia menej, než sa tvári — vysoké
- **Dôkaz:** `glsearch.py:804–818`: plató = ±1 krok **len** číselných parametrov **aktuálnej skupiny**. Bool a
  reťazcové parametre (entryOrderType, entryConfirm, slMode, tpMode…) sa preskakujú (`isinstance(vals[0], (bool,
  str))`). Ostatné skupiny sa nehýbu. Skupiny sa striedajú dokola (`:830+`), takže výsledok je optimum nad **všetkými**
  ~15–25 parametrami, nie nad štyrmi. Napr. `GROUPS` IBS EZ má aj typ vstupu, potvrdenie, SL režim, TP režim, RR
  0,5–3,0. K tomu „SKOK na nový bod“ s náhodným susedom (`:880+`) a fronta do hyperoptu (`:874`).
- Kandidát vzniká z **každého lokálneho optima** (`:856`), takže kandidátov je stovky (NOA 198, MTK Zone 150).
- **Prečo krach:** plató 80 % na jednej osi pri pevných ostatných osiach nemeria stabilitu v celom priestore.
  Preladený bod v 20-rozmernom priestore prejde.

### A7. Staré roky ako posledná brána: dobrý nápad, ale už znečistený a nezavedený — vysoké
- **MTK ORB MGC** v triedení „⚠ 1,54“: `glsearch.py:27–29` `PERIODS["mtkorb"] = ("20101101-20240904", …)`, teda MTK
  ORB sa **ladila na 2010–2024**. Test „pred ladením“ na MGC 1/2020–9/2021 bol pre ňu **in-sample**. Jej riadok
  v triedení nemá význam a v ⚠ nemá čo robiť.
- MTK EMAS: sami priznávajú, že štúdia mohla vidieť staré roky (`VYSLEDKY_TRIEDENIA.md`, „Len informačne“).
- Pre MNQ/MYM/BTC je to len ~2,3 roka. Výskumník (AI) pozná trhovú históriu, čo je únik priznaný v
  `KONVERZACIA` §6.
- Krok 12, `oos_stav.json` a značky vo webapp sú „ZATIAĽ NEROBENÉ“ (`KONVERZACIA` §9, `POSTUP_MACMINI.md` 1–3).
  Webapp a audit 26. 11. stále ukazujú IBS EZ, TKS a VWAP ORB ako triedu A a „● beží“.
- **Prečo krach:** jediný čistý test, ktorý máme, sa neprenáša do rozhodnutia, čo beží naživo.

### A8. Smernica existuje v dvoch protichodných verziách a automat beží podľa mäkšej — vysoké
- **Dôkaz:** repo `docs/SMERNICA_TESTOVANIA.md:94`: „**Min. 150 obchodov za rok — tvrdá hranica, nikdy pod ňu**“,
  `:213` to isté. iCloud `SMERNICA-TESTOVANIA/SMERNICA_TESTOVANIA.md:89`: „Min. 75 … (8. 11. znížené zo 150)“.
  Automat: `glsearch.py:46 MIN_TRADES_YEAR = 75`.
- Kontrola počtu je len **priemer** za 3,93 roka (`glsearch.py:758`; `gldash.py:469` len `c["is"]["trades"]/years`).
  Počet v jednotlivých rokoch ani počet v odloženom roku sa nekontroluje. Presne kvôli tomu padla MTK RANGE (pamäť
  `mtk-range.md`: „kontrolovať v KAŽDOM roku vrátane odloženého, nie len priemer“). V kóde to opravené nie je.
- Triedu A dostali stratégie s 76–87 obchodmi za rok (nocpon 76, noamgc 87, sweepengulf 85, mtkzone 76).
- **Prečo krach:** s polovičným počtom obchodov sa štatistická neistota PF zväčší ~1,4× a výber z tisícov je ešte
  ľahší. Navyše nevieme, ktorá smernica platí.

### A9. Výnimky: najsilnejšie čísla sú tie najmenej overené — vysoké
- **SPRÁVY MGC:** `spravy/stranka.json`: „PF 3,99 · najhorší rok 3,05 · 36 obch/rok“, profil_2 „PF 4,03“. Vlastná
  smernica (`docs/SMERNICA_TESTOVANIA.md:214`): PF „nad 2,5 (skoro isto preladené)“. Výnimka < 150 obchodov za rok
  je schválená (29. 10.). Pravidlá vzišli z výskumu na 2021–2026, teda **vrátane odloženého roka** (`KONVERZACIA`
  §7: „mäkký výber“). Staré roky test neplatí, lebo kalendár je až od 2021 (`VYSLEDKY_TRIEDENIA` ⏳). Napriek tomu
  beží naživo: `mirror.sqlite` instances: `XAUUSD spravynet profil_3`, last_seen 26. 11.
- **SPRÁVY EUR:** ~72 obch/rok, výnimka < 75 schválená 21. 11. (`stranka.json` „exception“), `no_audit: true`,
  v `glwebvyber.py` je `APPROVED = {"spravyeur"}` mimo auditu, vo webapp navrchu.
- **Hypotéza (overiť v zmluve):** prop firmy obchodovanie okolo high-impact správ obmedzujú alebo zakazujú.
  Stratégia, ktorá žije zo správ, môže porušiť pravidlá účtu.
- **Prečo krach:** PF 4 pri 36 obchodoch za rok a výbere pravidiel na celom období je typický podpis preladenia.

### A10. Dodatočné ladenie na živom období (reakcia na stratu) — vysoké
- **Dôkaz:** commit `5fdde0363` (24. 11. 2026): „Pridaj filter špičky volatility … lebo IBS EZ prehráva najmä
  v dňoch … (november 2026 naživo mimo normy backtestu“. Profil `SMERNICE_CS_IBS_Entry_Zone_11.json`
  (`spikeMax 1,7`, `_comment` 24. 11.) beží na FTMO Server3 (`instances`: `ibsentrynet SMERNICE_CS_IBS_Entry_Zone_11`).
  Filter vznikol pozretím na obdobie, ktoré stratu spôsobilo. Takému filtru zákonite „pomôže“ backtest, ktorý to
  obdobie obsahuje. Prah 1,7 nebol vopred zapísaný (hypotéza: zvolený pozretím na dáta po 9/2026).
- **Prečo krach:** to je ďalší stupeň voľnosti a zároveň začiatok slučky „prehra → filter → prehra → filter“.
  Takto sa prop účty zvyčajne spália.

## Časť II — Ako je smernica postavená: krok po kroku, čo chráni a čo nie

| krok | čo chráni | čo nechráni / kde uniká |
|---|---|---|
| 1 naživo = história (+ `tester.lookahead`) | look-ahead, závislosť od štartu, HTF pred zatvorením. **Silný krok.** | nie fill model (A12), nie dáta zo súborov stratégie (kalendár, Mag7), čo priznáva aj audit 2026-11-09 |
| 2 logika a kresby | chyby implementácie | nič štatistické |
| 3 východisko | zahodí zjavne mŕtve nápady (PF < 0,9) | nápad s PF 1,0 ide ďalej do hľadania, ktoré ho „zachráni“ |
| 4 mriežka + hyperopt | min. obchody, cieľ nie WR | **nemá strop pokusov**; 75 vs 150 (A8); priemer, nie každý rok; sprísnenie len raz pri 1 000 (A1) |
| 5 plató | osamotená špička na jednej osi | ±1 krok jednej skupiny, bool/str sa netestujú (A6) |
| 6 odložený rok | mal chrániť pred A1 | púšťa sa na **každého** kandidáta (2 300+), radí sa podľa neho (A2), jeden rok = jeden režim (A4) |
| 7 checkup (5 okien) | stabilita po rokoch, MC DD | 4 z 5 okien sú in-sample, 5. je OOS, z ktorého sa vyberalo. Okná `20231001-20241001` a `20240904-20250904` sa prekrývajú (priznané v ANALYTIKA „Okná sa prekrývajú“). Test proti náhode bez korekcie (A5) |
| 8 iný trh (NAS100/XAU/US500 CFD) | závislosť od detailu dát | ten istý podklad (NQ ↔ NAS100 je ten istý index, rovnaké obdobie), teda nie nezávislý trh. Pri 1,8 mil. pokusoch prejde aj náhoda, ktorá je spoločná obom feedom |
| 9 robustnosť | 2× poplatok, oneskorenie | „nemá vplyv“; DSR < 0,95 všade (A5) |
| 10 forward 4–8 týždňov | sklz, chyby, repaint | prah „PF najviac o 30 % nižší“ sa nevyhodnocuje automaticky. Živé účty bežia ďalej so stratou (A14) |
| 11 ostrá prevádzka | vypínacie pravidlo MC DD95 / PF < 1 po 50 | nie je implementované v EA ani v hube (A16); NOA ho už prekročila |
| (doplnky) walk-forward, režimy, portfólio | presne to, čo chýba | **voliteľné**, „doplnkové testy“ (`SMERNICA` sekcia Doplnkové). Walk-forward nebeží v automate vôbec |

Zhrnutie: technické kroky (1, 2) sú dobré. Štatistické kroky (4–9) sa dajú obísť počtom pokusov a kroky prevádzky
(10–11) sa nevynucujú.

## Časť III — Fill model, náklady, dáta

### A11. Náklad je percento z ceny, rovnaké pre MNQ, ES, MGC aj 6E, a na zlate a eure je pod vlastným modelom repa — vysoké
- **Dôkaz:** `glsearch.py:20 FEE = 1.755e-05`, `:664–669`: výnimka len pre BTC. Pre MGC, ES a 6E platí to isté
  percento. Repo samo odhaduje náklad (`tradebot/core/instruments_databento.json`): MNQ 1,5 ticku, MGC 1,5 ticku
  (0,15 b.), 6E 1 tick. `half_spread_ticks` sa v emulátore nepoužíva, len v posudku break-even
  (`tester/checkup.py:225`). Prepočet: MGC pri cene 1 800–2 000 (2022) dáva 1,755e-5 × 1 900 ≈ 0,033 b. ≈ **0,3 ticku**
  namiesto 1,5. 6E pri 1,05 je ≈ 0,37 ticku namiesto 1. MNQ pri 11 000 (2022) je 0,19 b. ≈ 0,8 ticku namiesto 1,5.
  Percento navyše skresľuje staré roky (nižšia cena = nižší náklad).
- `OOS-STARE-ROKY/PRVE_VYSLEDKY_ES_MGC_6E.md`: ES stratégie mali „pred poplatkami väčšinou PF 1,1–1,5, poplatky
  (1 tick/strana) ich zjedia“. IBS EZ ES z 1,10 na 0,75.
- **Prečo krach:** zlaté a eurové stratégie (Fibo, Sigma MGC, NOA MGC, MTK ORB, SPRÁVY, Williams R) sú ladené
  s podhodnoteným nákladom. Break-even 0,0228–0,035 % je síce vyšší, ale **sklz na stope sa neráta nikde**
  (`tester/fees.py:30`, `tester/prop.py:37`).

### A12. Fill model je optimistický práve tam, kde žijú naše profily: limit a TP „pri dotyku“, stop bez sklzu — vysoké
- **Dôkaz:** `tradebot/adapters/multicharts/emulator.py:214–220`: limit long sa vyplní, keď `sub.low <= price`,
  teda pri **dotyku**, nie pri prechode o tick. TP `:235` `sub.high >= tp`, tiež pri dotyku. SL `:236`
  `min(stop, sub.open)`: na presnej cene, sklz len pri medzere na otvorení minúty. Plus: SL pred TP v jednej minúte
  (`:245`) je konzervatívne, to treba uznať.
- Profily sú postavené na malom TP a vysokom WR: TKS RR 0,5 a WR 74 %, IBS EZ RR 0,5 a WR 76 %, VWAP ORB WR 74 %,
  IVB ES WR 92 %. Pri RR 0,5 je break-even WR 66,7 %. Rezerva je ~7–9 p. b. Pravidlo používateľa „WR 70–100 %,
  RR od 0,5“ (pamäť `test-defaults-all-strategies.md`) tlačí hľadanie presne do oblasti, kde je model najviac
  optimistický. NOA vstupuje limitkou (`entryOrderType limit, limitOffsetPct 53`).
- Živé: NOA **21 % WR** naživo proti 41 % v backteste a zhoda obchodov len 13/17 (`KONVERZACIA` §1). Pamäť
  `wr-rr-hub-2026-11.md`: „live IBS EZ s RR 0,5 prehráva na stopoch tesne nad knôtom“.
- **Prečo krach:** keď sa nevyplní 5–10 % TP dotykov alebo príde 1 tick sklzu na stope, RR 0,5 a WR 74 % sa otočí
  do záporného očakávania. Hypotéza na overenie: koľko TP v backteste bolo zasiahnutých presne na high/low minúty.

### A13. Ladíme na futures (Databento MNQ, bez back-adjustu), obchodujeme CFD na FTMO — stredné
- **Dôkaz:** všetky živé profily majú `_instrument: mnq_databento`. Bežia na `US100.cash`, `US500.cash` a `XAUUSD`
  (`mirror.sqlite` instances, FTMO-Server3). Front-month podľa objemu, bez back-adjustu, skok pri rolle MNQ ~0,9 %
  (`KONVERZACIA` §2). Krok 8 to kontroluje na Dukascopy, nie na FTMO feede (iný spread, iné seansy, swap).
- **Prečo krach:** iné sviečky = iné signály. Zhoda NOA 13/17 ukazuje, že to nie je teória.

## Časť IV — Riziko účtu a prevádzka

### A14. Živé výsledky už sú mimo backtestu a vypínacie pravidlo sa neuplatnilo — kritické
- **Dôkaz:** `KONVERZACIA` §1: od 15. 10. do 25. 11. ~145 obchodov, **~−5 740 $**. FTMO Server3 82 obchodov
  −6 536 $ (IBS EZ −1 776, NOA −2 489, TKS −589, Fibo −1 002 za 2 obchody). „Backtest čakal Ø november +4 189 $,
  najhorší 2022 −569 $.“ NOA: MC DD 95 % ≈ 2 100 $ (`tradebot/strategies/noanet/docs/ANALYTIKA.md:187`), naživo
  −2 489 $. To je nad hranicou vypnutia podľa kroku 11, a predsa `instances` ukazuje `noanet SMERNICE_CS_NOA_1`
  last_seen 26. 11. 14:51.
- **Prečo krach:** pravidlo, ktoré sa nevykoná, neexistuje. Prop účet zomrie skôr, než o tom rozhodne človek.

### A15. Jedna stávka: živé portfólio je Nasdaq intraday v tom istom okne — kritické
- **Dôkaz:** na FTMO-Server3 bežia súčasne `noanet`, `tksnet` a `ibsentrynet` na `US100.cash` (3m/5m, NY seansa)
  plus SPRÁVY XAU (`instances`). V novembri prehrávali **naraz** (IBS EZ, NOA aj TKS záporné v tom istom mesiaci,
  `KONVERZACIA` §1). Portfóliový test je v smernici len „doplnkový“. `tester/prop.py:28–34` sám priznáva: „zliatie
  trhov robí výsledok optimistickým“, „vidí len uzavreté obchody“ (prop meria equity vrátane otvorených pozícií).
- Riziko na obchod: `maxLossDollar 1000` pri IBS EZ (`SMERNICE_CS_IBS_Entry_Zone_1/11.json`), pri ostatných 500 $
  (pamäť). Tri korelované stratégie × 1–2 stopy za deň dajú 2–4 k$ za deň. Pri bežnom limite 5 % na 100k účte
  (hypotéza o veľkosti účtu) sú to dva zlé dni k dennému limitu.
- **Prečo krach:** séria 8–14 strát (MC 95 %, ANALYTIKA NOA:159, TKS:165) v tých istých dňoch na troch stratégiách
  prekročí denný aj celkový limit propky.

### A16. Žiadna ochrana účtu v kóde: ani denný stop-loss, ani trailing DD, ani automatické vypnutie — kritické
- **Dôkaz:** grep `drawdown | daily loss | denný limit` v `tradebot/adapters/mt5/*.mqh` a `adapters/ninjatrader`
  nenašiel nič. Je tam len „denný limit výhier“ (`docs/MT5.md:83`). `docs/ROUTING.md:312`: exekútor „bez … denného
  limitu (to drží engine v NT)“, „na účte ešte neoverený“. Vypnutie je ručné (`/flatten`, `/pause`, `docs/LIVE.md:581`).
  Hub plugin `watchdog` stráži stroje, nie P&L (hypotéza, plugin som nečítal celý).
- **Prečo krach:** propku zabíja jeden zlý deň. Bez tvrdého denného stopu na úrovni účtu rozhoduje rýchlosť
  človeka.

### A17. Čísla rizika si protirečia a nikto nevie, aký DD čakať — stredné
- **Dôkaz:** IBS EZ: titul profilu „max DD 1 080 $“ (`SMERNICE_CS_IBS_Entry_Zone_1.json`), audit 26. 11. „max DD
  7 150 $“, ANALYTIKA `ibsentry` MC 95 % **2,9 %** a `ibsentrynet` **13,3 %, najhorší 28,3 %** (`ibsentrynet/docs/
  ANALYTIKA.md:163`). IBS EZ ES má v audite max DD 8 517 $.
- **Prečo krach:** veľkosť pozície vzhľadom na limity propky sa nastavuje podľa čísla, ktoré sa medzi pohľadmi líši
  až 7×.

### A18. Prevádzka visí na jednom stroji a ručných zásahoch; výpadky sa zistia po dňoch — stredné
- **Dôkaz:** Tradeify IBS EZ EOD „neposiela dáta od 18.–19. 11.“ (`KONVERZACIA` §1; `instances` NT TDFYSL last_seen
  19. 11.). 7 obchodov (−886 $) je duplicitne pod dvoma účtami (FTMO Demo aj Server3, 27.–29. 10.). V živom zozname
  sa točia profily (`_OPRAVA_KODU`, `_SL500`, `_11`). OOS beh sa pri výpadku hubu (DNS) „stratí“ (`POSTUP_MACMINI`).
  MT5 aj NT bežia na jednom Windows stroji (hypotéza podľa `agent`/`host` v `instances`, nas-win11).
- **Prečo krach:** otvorená pozícia počas výpadku bez SL na strane brokera, alebo stratégia, ktorá ticho stojí či
  beží duplicitne. Pri limitoch propky stačí jeden taký deň.

### A19. Kvalita dát pod niektorými ladeniami — stredné
- **Dôkaz:** MGC pred 2020: pokrytie seansy 33–74 % (`KONVERZACIA` §2). MTK ORB sa ladila od 2010-11 na zlate
  (`glsearch.py:27`). 6E 2010–2015 má ~1 600 zlých tikov. MTK EMAS má falošné kríženia pri rolloch.
- **Prečo krach:** na riedkych dátach sa ľahko nájdu „vzory“, ktoré na živom trhu nie sú.

### A20. Webapp a stránka ukazujú optimizmus ako normu — stredné
- **Dôkaz:** `glwebvyber.py`: navrchu sú top 3 zo stránky, zoradené podľa OOS PF (A2). Tituly profilov nesú
  „PF 1,56 · WR 74 % · posl. rok PF 1,77“. Výkon na 5 oknách obsahuje in-sample roky. Značka „neprešlo starými rokmi“
  vo webapp nie je (A7). Smernica sama píše, že backtest je „horný strop“ a naživo PF o 20–30 % nižší (`:238`). Pri
  vybranom chvoste (A3) je zrážka 30–40 % (ORB 15/5 ES: ladenie 1,40 → 11 rokov 1,07, `KONVERZACIA` §5).
- **Prečo krach:** človek pri výbere do LIVE vidí najlepšie z najlepších bez korekcie a bez varovania.

---

## Top 5 dôvodov krachu do roka

1. **Odložený rok nie je odložený (A2 + A3):** > 2 300 behov na tom istom roku a poradie podľa neho. Do LIVE idú
   chvosty rozdelenia, ktorého medián je ~1,0. Staré roky: IBS EZ 0,79, TKS 0,94, VWAP ORB 0,96, NY VA 0,81,
   IBS EZ ES 0,75.
2. **1,8 mil. pokusov bez brzdy (A1 + A5 + A6):** DSR < 0,95 všade, test proti náhode bez korekcie, plató na jednej
   osi. Výsledok je výber šťastia, nie edge.
3. **Korelované portfólio bez ochrany účtu (A15 + A16):** tri Nasdaq stratégie v tom istom okne, žiadny denný
   stop-loss ani trailing DD v kóde. Prop pravidlo zabije účet za 1–2 zlé dni.
4. **Optimistický fill pri RR 0,5 / WR 74 % (A11 + A12):** TP a limit pri dotyku, stop bez sklzu, náklad na zlate
   a eure ~0,3 ticku. Rezerva 7 p. b. WR zmizne. Naživo NOA 21 % WR namiesto 41 %.
5. **Prevádzka nerešpektuje vlastné pravidlá (A10 + A14 + A7):** naživo −5,7 k$ za 6 týždňov a NOA nad MC DD95
   stále beží. Namiesto vypnutia sa ladí filter na novembri. Krok 12 zo starých rokov nie je zavedený a webapp
   neobstáté stratégie ďalej ukazuje ako triedu A.

---

## Čo podľa mňa môže byť naozaj funkčné (kandidáti) a čo je isto mŕtve

Kritérium prokurátora: verím len tomu, čo obstálo na dátach, ktoré hľadanie **nikdy nevidelo**, alebo čo prešlo
**málo pokusmi** s jasným ekonomickým dôvodom. Čísla z ladenia a z „odloženého“ roka beriem ako dôkaz nula.

**Kandidáti, ktorí si zaslúžia čistý forward test (nie live s plnou veľkosťou):**

| stratégia | dôkaz za | výhrada |
|---|---|---|
| Noc + pondelok (MNQ, MYM) | staré roky PF 1,55 (3/3 r.) aj 1,33 na MYM. Dva trhy, jasný dôvod (overnight drift) | ~2,3 roka OOS, 76 obch/rok, gl_state 0 kombinácií (ladená inde, počet pokusov neznámy) |
| ON bias ORB (MNQ) | staré roky 1,50 (2/3), len 4 896 kombinácií, 0 kandidátov z automatu | málo rokov |
| Williams R Long 6E | 6/6 rokov v pluse (PF 1,54), sedí s ladením 1,53, len 3 477 kombinácií | ten istý index na ES je 0,67 a na MGC 1,08, takže to je jeden trh, nie princíp |
| NOA / NOA EOD (MNQ) | staré roky 1,24 / 1,38, všetky profily 3/3 roky | naživo −2 489 $ a WR 21 %, zhoda 13/17. Najprv vyriešiť exekúciu, inak je kandidát len na papieri |
| Volt Break (MNQ) | 1,28 (3/3), malý priestor (6 116), medián OOS kandidátov 1,29 | DSR 0,89 |
| ORB 15/5 ES | 11 rokov, 2 033 obch., 10/12 rokov | PF 1,07 je tenký. 1 tick sklzu navyše ho pravdepodobne zabije (pred poplatkami 1,22) |

**Isto mŕtve (staré roky PF < 1, zlyhanie mimo ladenia):** IBS EZ (MNQ, MYM, ES, EOD), TKS (+EOD), VWAP ORB (+EOD),
NY VA ES, IVB (MNQ, ES, MGC), NOA MGC, Sigma MGC/MYM, NQ Precision MGC, M2 MNQ, CRT, Sweep engulf MNQ, Williams R ES,
Flash ORB MNQ, VWAP ADX EOD. **Tri z nich (IBS EZ, TKS, VWAP ORB) sú alebo boli naživo.**

**Neoverené = do live nesmú:** SPRÁVY MGC aj EUR (kalendár od 2021, PF 3–4 je podozrivé), MTK ORB MGC (staré roky
boli in-sample, A7), MTK EMAS, všetky ⚠ (VWAP ADX, Fibo MGC, SVP, Mag7, JSS, Sigma MNQ, MTK Zone).

**Odpoveď na otázku (2):** po prísnom čítaní **nemáme ani jednu stratégiu s dôkazom, že naživo zarobí po
nákladoch**. Máme 4–6 kandidátov s reálnym, ale malým jadrom (PF 1,1–1,5 mimo ladenia). Všetko, čo je dnes naživo
okrem NOA, je podľa starých rokov mŕtve.

**K otázke (1), čo zmeniť (návrh do debaty):**
- rozpočet pokusov na stratégiu (napr. ≤ 500, zapísaný vopred) a hranice, ktoré s ním rastú (DSR ≥ 0,95 ako **brána**);
- odložené dáta pustiť **raz na stratégiu**, nie na kandidáta, a nikdy podľa nich nezoraďovať; výber robiť podľa
  ladenia alebo walk-forward;
- walk-forward ako povinný krok, staré roky (krok 12) ako záverečná brána s hranicou zapísanou vopred (commit);
- fill model: limit/TP až pri prechode o 1 tick, 1 tick sklzu na stop a market, náklad v tickoch podľa trhu
  (`half_spread_ticks`), nie percento;
- min. obchodov v **každom** roku, jedna verzia smernice;
- portfólio a prop pravidlá (denný limit, trailing DD na equity) ako brána pred live, tvrdý denný stop účtu v EA,
  automatické vypnutie pri MC DD95 / PF < 1 po 50 obchodoch;
- po živej strate nič nedolaďovať na tom období. Buď vypnúť, alebo pokračovať bez zmeny.
