# Debata agentov — čo je zlé v smernici, webapp a stratégiách (26. 11. 2026)

Agent A = Prokurátor (hľadá dôvody krachu), Agent B = Inžinier (overuje, výskum, riešenia). Kolá v poradí.


---

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

---

# Agent B (Inžinier) — 1. kolo: ako sa stratégia buduje správne

*26. 11. 2026 · len čítanie: smernica (iCloud SMERNICA-TESTOVANIA), `.nightsearch/glsearch.py` + `glreport.py` +
`gl_state.json`, iCloud OOS-STARE-ROKY, `docs/ANALYTIKA.md`, literatúra (zdroje v časti 4).*

## 0. Tri čísla z nášho automatu, na ktorých stojí celý zvyšok

| čo | hodnota | odkiaľ |
|---|---|---|
| vyskúšaných kombinácií spolu | **1 551 132** na 85 stratégiách (TKS 82 129, Mag7 45 167, NOA 37 700) | `gl_state.json` → `combos` |
| koľkokrát sa pustil „odložený rok raz“ | **1 965×** (NOA 185 kandidátov, TKS 90, Mag7 86) — vždy ten istý rok 2025-09 – 2026-09 | `gl_state.json` → `candidates[].oos` |
| výsledok na rokoch pred ladením (nikto ich nevidel) | z 3 živých MNQ stratégií IBS EZ 0,79 · TKS 0,94 · VWAP ORB 0,96; obstálo 10 stratégií, väčšinou jednoduché | OOS-STARE-ROKY/VYSLEDKY_TRIEDENIA.md |

Literatúra presne toto predpovedá: veľa pokusov + výber najlepšieho = výsledok z ladenia je hlavne šum
(Bailey a kol. 2014; Harvey a Liu 2015). Technika (parita, krok 1, dáta) je u nás nadštandardná,
**chýba štatistika výberu**.

---

## 1. Proces budovania podľa literatúry (v krokoch)

1. **Hypotéza skôr než dáta.** Ekonomický dôvod, prečo má edge existovať (kto platí, prečo to nezmizne).
   Najprv sa formuluje, potom testuje; hľadanie v dátach bez dôvodu je „data mining“ (Aronson 2006, kap. 6;
   Harvey, Liu a Zhu 2016: t ≥ 3,0 pre nové faktory). López de Prado (2018, §11.4): *backtest nie je výskumný
   nástroj* — nástroj na overenie hotovej hypotézy, nie na jej hľadanie.
2. **Rozpočet pokusov vopred.** Zapísať, koľko variantov sa smie skúsiť; z dĺžky dát plynie strop
   (MinBTL: pri 5 rokoch denných dát najviac ~45 nezávislých konfigurácií, inak Sharpe 1,0 vznikne náhodou —
   Bailey, Borwein, López de Prado, Zhu 2014). **Evidovať všetky pokusy** vrátane zahodených.
3. **Jednoduchý model, málo stupňov voľnosti.** Zložitejšie stratégie strácajú naživo o > 30 % Sharpe viac
   (Suhonen, Lennkh, Perez 2017). Carver (2015): pravidlá „ručne“ / málo parametrov, robustne, nie optimum.
4. **Čisté dáta a realistické náklady** (spread, poplatok, sklz, rolovanie) už v ladení, nie až v stres teste.
   Carver: náklady nesmú zjesť viac než ~⅓ očakávaného hrubého Sharpe („speed limit“).
5. **Validácia, ktorá berie do úvahy výber:**
   - walk-forward ako *hlavný* postup (Pardo 2008, kap. 11; walk-forward efficiency = OOS výkon / IS výkon),
   - kombinatorická krížová validácia s purgingom a embargom (CPCV, López de Prado 2018, kap. 7 a 12),
   - **PBO** cez CSCV (Bailey a kol. 2017) — pravdepodobnosť, že víťaz ladenia je mimo vzorky pod mediánom,
   - **Deflated Sharpe Ratio** (Bailey a López de Prado 2014) — Sharpe opravený o počet pokusov, ich rozptyl,
     šikmosť, špicatosť a dĺžku záznamu; prah DSR ≥ 0,95,
   - **White Reality Check / Hansen SPA** (White 2000; Hansen 2005; aplikácia na technické pravidlá Sullivan,
     Timmermann, White 1999) — test „najlepší z N“ proti nule, nie test jedného pravidla,
   - **haircut Sharpe** (Harvey a Liu 2015) — kúpeľ Sharpe podľa počtu testov; „50 % na všetko“ je zlé
     pravidlo, marginálne stratégie strácajú takmer všetko.
6. **Holdout je jednorazový.** Keď sa na ňom robí výber (alebo sa naň opakovane pozerá), stáva sa
   in-sample (Bailey a kol. 2014, „holdout je nespoľahlivý“; López de Prado 2018 §11.6). Nové, nevidené dáta
   sa šetria na úplný koniec.
7. **Robustnosť:** plató v parametroch, iné trhy (aj iné *podkladové aktíva*, nielen iný zdroj dát), iné
   obdobia a režimy. Trend-following napr. je potvrdený na 67 trhoch a 137 rokoch (Hurst, Ooi, Pedersen 2017;
   Moskowitz, Ooi, Pedersen 2012) — to je úroveň dôkazu, ktorá robí edge vierohodným.
8. **Očakávaj zrážku naživo.** Medián Sharpe 215 bankových stratégií klesol z backtestu 1,20 na 0,31 naživo
   (−73 %; Suhonen a kol. 2017). Prediktory z publikácií: −26 % mimo vzorky, −58 % po publikácii
   (McLean a Pontiff 2016).
9. **Veľkosť pozície z rizika a portfólia**, nie z backtestu: cieľ volatility, zlomok Kelly, korelácie medzi
   stratégiami (Carver 2015, kap. 9–11). Pri prop účte drawdown limit = absorpčná hranica → riešiť
   pravdepodobnosť ruiny, nie priemerný DD.
10. **Paper / malá veľkosť s vopred zapísaným vypínacím pravidlom**, potom postupné zvyšovanie
    (Chan 2009, 2013; Carver 2015). Minimálna dĺžka záznamu (MinTRL) určuje, kedy je živý výsledok vôbec
    štatisticky čitateľný (Bailey a López de Prado 2012).

---

## 2. Literatúra vs. naša smernica

| # | čo hovorí literatúra | čo robí naša smernica / automat | rozdiel | závažnosť |
|---|---|---|---|---|
| 1 | Hypotéza pred dátami (Aronson; HLZ; LdP §11.4) | `glsearch` hľadá mriežkou + Optuna donekonečna, kým niečo neprejde; dôvod edge sa nezapisuje | výskum = data mining | **kritická** |
| 2 | Rozpočet pokusov vopred, MinBTL (~45 konf. na 5 r.) | pokusy sa len *počítajú*; jediný dôsledok: nad 1000 kombinácií OOS PF 1,3 namiesto 1,2 | 82 129 pokusov na 4 roky ladenia ≈ 3 rády nad MinBTL; prah sa nemení s N spojito | **kritická** |
| 3 | Holdout raz, nevidený | „odložený rok raz na kandidáta“ = 1 965 behov na *ten istý* rok; výber na stránku/webapp ho používa (glreport `ok`, „posl. rok PF“) | holdout je de facto in-sample (výber najlepšieho z desiatok OOS) | **kritická** |
| 4 | DSR ≥ 0,95 / PBO < ~0,2 ako brána | DSR počítaný (ROBUSTNOST 29. 10.), ale „na prejdenie nemá vplyv“; najvyšší 0,93, živé TKS 0,79, VWAP ORB 0,75, NOA 0,33 | metrika existuje a hovorí NIE, ignoruje sa | **kritická** |
| 5 | Reality Check / SPA: test najlepšieho z N | „test proti náhode“ v checkupe = 1 pravidlo proti náhodným vstupom | neopravuje výber z N; 95–99 % je ľahké pri tisícoch pokusov | vysoká |
| 6 | Walk-forward / CPCV ako hlavná validácia (Pardo; LdP) | walk-forward len „doplnkový“; jedno pevné rozdelenie IS/OOS | jedna cesta = jeden náhodný výsledok | vysoká |
| 7 | Haircut Sharpe podľa N (Harvey–Liu); zrážka 50–73 % | smernica: „naživo o 20–30 % nižšie“, PF 1,5 → 1,2–1,3 | očakávaná zrážka podhodnotená 2–3× | vysoká |
| 8 | Optimalizačný cieľ = robustný, nie max | skóre = PF (strop 4) + 0,3·najhorší rok; vrchol z ladenia → plató je **min ±1 krok len v skupine 4 parametrov**, prah 80 % | plató je lokálne, ignoruje ostatné parametre a TF; vrchol sa neposúva do stredu (glsearch berie `cur`) | stredná |
| 9 | Nezávislé potvrdenie na inom aktíve / období | krok 8: MNQ→NAS100, ES→US500, MGC→XAU, 6E→EURUSD (OTHER_MARKET) | to isté podkladové aktívum, iný zdroj dát — nie nezávislý dôkaz | stredná |
| 10 | Dĺžka záznamu / štat. sila (MinTRL) | OOS 1 rok, ~75–300 obchodov; prah PF ≥ 1,2 | pri PF 1,2 a 150 obch. je t ≈ 1 (pozri 3e) — OOS nemá silu nič potvrdiť | vysoká |
| 11 | Náklady realisticky už v ladení (Carver ⅓ SR) | poplatok áno (1,755e-05 MNQ); sklz len ako doplnkový stres; break-even poplatok ≥ 2× | sklz v ladení chýba; na ES staré roky poplatky zjedli PF 1,1–1,5 → 0,75 | stredná |
| 12 | Analytika mimo vzorky | checkup „5 okien“ = 4 roky ladenia + odložený rok | „4 z 5 rokov v pluse“ je takmer celé in-sample | stredná |
| 13 | Sizing z rizika + portfólio + ruina pri pevnom limite | testy na 1 kontrakt, MC DD 95 % ako vypínač; portfólio len doplnok | chýba P(ruina) pri FTMO 5 % denne / 10 % celkovo, korelácia stratégií v tých istých dňoch | vysoká |
| 14 | Vypínanie podľa vopred zapísaného štat. pravidla | „PF < 1 po 50 obchodoch“, DD > MC 95 % | 50 obchodov má SE PF ≈ ±0,3 — pravidlo je zároveň pomalé aj šumové; nevychádza z MinTRL/SPRT | stredná |
| 15 | Technická správnosť (no lookahead, parita) | krok 1 (1a–1d), C# parita, kontrola dát Databento | **nad literatúrou** — toto robíme dobre | — (silná stránka) |

---

## 3. Merateľné kritériá, ktoré nám chýbajú

**a) Register pokusov (povinný vstup všetkého ostatného).** Na stratégiu: N všetkých konfigurácií
(mriežka + hyperopt + ručné + výbery profilov + zmeny kódu po pozretí výsledkov), *efektívne* N po
zhlukovaní korelovaných pokusov (LdP 2018 §8; Bailey–LdP 2014 navrhujú odhad cez zhlukovanie). Dnes máme
len hrubé `combos`.

**b) DSR ako brána, nie informácia.** DSR ≥ 0,95 pri efektívnom N. Dnes by neprešla žiadna z 14
(ROBUSTNOST_2026-10-29). Ak považujeme N za nadhodnotené, odhadnúť efektívne N, nie prah zmäkčiť.

**c) PBO cez CSCV.** Matica výsledkov všetkých konfigurácií (máme ju v `gl_<key>.jsonl` — PnL po
mesiacoch treba doplniť), rozdeliť na S = 16 blokov, PBO ≤ 0,2 (Bailey a kol. 2017 ukazujú, že nad ~0,5 je
výber horší než náhodný). Lacné: nevyžaduje nové behy, ak sa ukladá mesačný PnL.

**d) Reality Check / SPA** nad všetkými konfiguráciami jednej stratégie (stationary bootstrap denných PnL),
p < 0,05. Nahradí dnešný test proti náhode tam, kde sa vyberalo.

**e) Minimálna štatistická sila OOS.** Hrubý odhad: PF 1,2 pri WR 50 % → priemer ~0,1 R, σ ~1,1 R →
t ≈ 0,09·√n. Pri 150 obchodoch t ≈ 1,1; pri 600 t ≈ 2,2; t = 3 potrebuje ~1 100 obchodov. → **OOS
kritérium = t-stat (alebo PSR) ≥ 2 na nevidených dátach**, nie PF ≥ 1,2 na 1 roku. Pre HLZ prah t ≥ 3
pri veľkom N.

**f) Walk-forward ako hlavná brána:** okná IS 2 r. / OOS 6 mes., reoptimalizácia **tým istým automatom
s tým istým rozpočtom**, spojená OOS krivka: PF ≥ 1,15, WFE ≥ 0,5, ≥ 70 % OOS okien v pluse. (WFE 0,5 je
bežná prax odvodená od Pardo 2008; presný prah v knihe overiť.)

**g) Haircut Sharpe (Harvey–Liu 2015)** z efektívneho N; do webapp a na stránku dávať **ohaircutované
očakávanie**, nie PF z ladenia. Pre marginálne stratégie (PF ~1,2–1,3) vychádza haircut 70–100 %.

**h) Skutočne nevidené dáta (krok 12 z MacBooku) s vopred zapísanou hranicou** — to je fakticky
CSCV/holdout v duchu literatúry a už ukázal svoju hodnotu. Doplniť: hranica rastie s N; po použití je
obdobie „spálené“ (zapísať dátum).

**i) Nezávislý trh** = iné podkladové aktívum tej istej triedy (MNQ → ES/MYM/DAX/Nikkei, MGC → SI/HG,
6E → 6B/6J) bez zmeny parametrov, PF > 1,05 a rovnaký znak vo väčšine rokov. Dukascopy CFD nechať ako test
zdroja dát.

**j) Riziko ruiny pre prop účet:** Monte Carlo blokovým bootstrapom *denných* PnL portfólia (zachová zhluky
ako november 2026), P(denná strata > 5 %) a P(celkový DD > 10 %) za 12 mesiacov; brána napr. ≤ 5 %.
Veľkosť pozície voliť tak, aby sa ňou splnila (cieľ volatility, Carver kap. 9–10).

**k) Sklz v ladení:** min. 1 tick/strana pri market/stop vstupoch už v hľadaní; break-even poplatok
počítať aj so sklzom. Carver: náklady ≤ ⅓ hrubého výnosu.

**l) Zložitosť:** strop počtu voľných parametrov (napr. ≤ 4–5 vrátane TF) a pravidlo „ak jednoduchšia verzia
dá ≥ 90 % výsledku, berie sa jednoduchšia“. Dáta OOS-STARE-ROKY to potvrdzujú: obstáli jednoduché stratégie.

**m) Živé vypínanie podľa sekvenčného testu** (SPRT / PSR proti backtestovanému SR) namiesto „PF < 1 po 50“;
MinTRL povie, po koľkých obchodoch je živý výsledok vôbec rozlíšiteľný od nuly.

### Navrhovaná minimálna brána (zhrnutie pre debatu)
`krok 1 ✓` → `register N` → `walk-forward OOS PF ≥ 1,15, WFE ≥ 0,5` → `DSR ≥ 0,95 alebo PBO ≤ 0,2` →
`nevidené roky raz, t ≥ 2` → `iné aktívum ✓` → `P(ruina prop) ≤ 5 %` → paper. Prah „PF z ladenia ≥ 1,3“ sa
stáva len filtrom kandidátov, nie dôkazom.

---

## 4. Zdroje

- Bailey D. H., Borwein J., López de Prado M., Zhu Q. J. (2014): *Pseudo-Mathematics and Financial
  Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance*, Notices of the AMS 61(5),
  458–471, doi:10.1090/noti1105 — MinBTL, „45 konfigurácií na 5 rokov“. https://www.ams.org/notices/201405/rnoti-p458.pdf
  (súhrn: https://phys.org/news/2014-04-pseudo-mathematics-financial-charlatanism.html)
- Bailey, Borwein, López de Prado, Zhu (2017): *The Probability of Backtest Overfitting*, Journal of
  Computational Finance 20(4), doi:10.21314/jcf.2016.322 — PBO, CSCV. https://papers.ssrn.com/abstract=2326253
- Bailey D. H., López de Prado M. (2014): *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest
  Overfitting and Non-Normality*, Journal of Portfolio Management 40(5). https://papers.ssrn.com/abstract=2460551
- Bailey D. H., López de Prado M. (2012): *The Sharpe Ratio Efficient Frontier* (PSR, MinTRL), Journal of Risk 15(2).
- López de Prado M. (2018): *Advances in Financial Machine Learning*, Wiley — kap. 7 (purged/embargoed CV),
  11 (§11.4 „Backtesting is not a research tool“), 12 (CPCV). https://www.oreilly.com/library/view/advances-in-financial/9781119482086/
- Harvey C. R., Liu Y. (2015): *Backtesting*, Journal of Portfolio Management 42(1) — haircut Sharpe.
  https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF
- Harvey C. R., Liu Y., Zhu H. (2016): *…and the Cross-Section of Expected Returns*, Review of Financial
  Studies 29(1) — prah t ≥ 3,0.
- White H. (2000): *A Reality Check for Data Snooping*, Econometrica 68(5), 1097–1126.
  https://users.ssc.wisc.edu/~bhansen/718/White2000.pdf
- Hansen P. R. (2005): *A Test for Superior Predictive Ability*, Journal of Business & Economic Statistics 23(4).
- Sullivan R., Timmermann A., White H. (1999): *Data-Snooping, Technical Trading Rule Performance, and the
  Bootstrap*, Journal of Finance 54(5), 1647–1691.
  https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf
- Aronson D. (2006): *Evidence-Based Technical Analysis*, Wiley — data-mining bias, Reality Check v praxi.
- Pardo R. (2008): *The Evaluation and Optimization of Trading Strategies*, 2. vyd., Wiley — kap. 11
  walk-forward, walk-forward efficiency. https://www.oreilly.com/library/view/the-evaluation-and/9781118045053/
- Carver R. (2015): *Systematic Trading*, Harriman House — cieľ volatility, „speed limit“ nákladov ⅓ SR,
  očakávaný Sharpe max ~1. https://harriman-house.com/systematic-trading (súhrn: https://www.cxoadvisory.com/big-ideas/a-few-notes-on-systematic-trading)
- Chan E. (2009, 2013): *Quantitative Trading*; *Algorithmic Trading*, Wiley — paper trading, Kelly, postupné zvyšovanie.
- Suhonen A., Lennkh M., Perez F. (2017): *Quantifying Backtest Overfitting in Alternative Beta Strategies*,
  Journal of Portfolio Management 43(2) — Sharpe −73 % naživo, zložitosť +30 % zrážky. https://alphaarchitect.com/?p=36892
- McLean R. D., Pontiff J. (2016): *Does Academic Research Destroy Stock Return Predictability?*, Journal of
  Finance 71(1), 5–32. https://econpapers.repec.org/RePEc:bla:jfinan:v:71:y:2016:i:1:p:5-32
- Moskowitz T., Ooi Y. H., Pedersen L. H. (2012): *Time Series Momentum*, Journal of Financial Economics 104(2).
- Hurst B., Ooi Y. H., Pedersen L. H. (2017): *A Century of Evidence on Trend-Following Investing*, Journal of
  Portfolio Management 44(1) — 67 trhov, 1880–2016. https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing
- Chague F., De-Losso R., Giovannetti B. (2019): *Day Trading for a Living?*, SSRN 3423101 — 97 % vytrvalých
  day traderov na futures (Brazília) prerobilo. https://ideas.repec.org/p/fgv/eesptd/525.html
- FTMO pravidlá (5 % denná, 10 % celková strata; výpočet dennej sa v zdrojoch líši — overiť na oficiálnej
  stránke): https://ftmo.oanda.com/how-to-pass-ftmo-challenge/

*Poznámka k istote: prah WFE ≥ 0,5 pochádza zo sekundárnych zdrojov (Pardo ho v dostupných ukážkach výslovne
neuvádza); čísla McLean–Pontiff (26 % / 58 %) sú z abstraktu podľa mojej znalosti, vyhľadávač potvrdil len
„dolnú hranicu ~32 %“ efektu publikácie. Ostatné citácie overené cez SSRN / vydavateľa.*

---

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

---

# Agent A (Prokurátor) — 3. kolo: replika

*26. 11. 2026. Len čítanie. Nové dôkazy v tomto kole: lot veľkosti zo `tester/live/mirror.sqlite` (fill udalosti,
`-readonly`) a prahy profilu `tester/profiles/SMERNICE_CS_IBS_Entry_Zone_1.json`.*

Pán Inžinier, ďakujem za overenie. Vo väčšine opráv máte pravdu a prijímam ich. Na dvoch miestach vás však vaša
vlastná námietka B2 zasahuje tvrdšie než mňa a váš proces má diery, ktorými ho náš automat obíde rovnako ľahko ako
dnešnú smernicu.

---

## 1. Vaše opravy

**A4 (IBS EZ a bodové prahy): prijímam, ale váš „čistejší dôkaz“ neobstojí.**
Bodové prahy sú overené. `SMERNICE_CS_IBS_Entry_Zone_1.json` má `fvgMinSize 58`, `minImbSizePoints 8`,
`srClusterPoints 15`, `ewMinWavePoints 20`, `engMinRangePoints 6` a v `ibsentry/config.py:29` je `fvgMinSize` typu
`"abs"`. Váš argument B2 však platí ešte silnejšie pre **ES**. IBS EZ ES sa ladila na ES pri 3 600–6 900 bodoch,
kým staré roky 2010–2021 boli pri 1 050–4 500, teda až 5× nižšie. Na MNQ je pomer 2019–21 voči 2021–25 asi 1,6–2×.
IBS EZ ES 0,75 (3/12) je preto **horší** dôkaz než MNQ, nie lepší. Najčistejší je MYM (Dow 2019–21 ~18–35 tis. voči
29–45 tis., pomer ~1,3–1,6). Záver: všetky staré roky IBS EZ sú skreslené. Rozsudok musí vyniesť test T1 nižšie,
nie triedenie. Do vtedy IBS EZ nie je „mŕtva“, ale **neobhájená**, a neobhájená stratégia na prop účet nepatrí.
Výsledok pre živé rozhodnutie je teda rovnaký.

Ten istý argument použijem proti vášmu B1. Tabuľka t pre ✅ má rovnakú vadu. Jediný ✅ bez rizika bodových prahov
je **Williams R 6E**, lebo 6E sa v rokoch 2016–2026 drží v pásme 0,96–1,25. Preto je jej t ≈ 4,1 najdôveryhodnejšie
číslo, aké máme. Noc + pondelok a NOA treba skontrolovať, či majú prahy v bodoch alebo v ATR, inak ich t nič nevraví.

**A11 na MNQ: čiastočne prijímam.** Dnes áno: v `mirror.sqlite` je fill TKS pri 25 445, kde 1,755e-5 dáva 0,45
bodu ≈ 1,8 ticku. Ladenie však beží na 10/2021–9/2025 a MNQ bol v rokoch 2022–23 na 10 500–16 000, čo dáva 0,18–0,28
bodu ≈ **0,7–1,1 ticku**. Polovicu rokov ladenia sme teda platili menej, než repo samo odhaduje (1,5 ticku). A čo je
podstatné: tieto roky boli pri výbere rovnako dôležité ako ostatné (`passes_is` chce každý rok ≥ 0,9). Na CFD
nákladoch sa zhodneme. Dodávam, že ich vieme zmerať bez nových behov: zrkadlo má 1,82 mil. udalostí `m1` (sviečky
od brokera) a 316 `fill` udalostí. Sklz je rozdiel fill − hranica sviečky brokera v tej minúte.

**A14 (živé „jablká s hruškami“): fakt prijímam, záver nie.** Veľkosti sa naozaj líšia. NOA na Server3 mala 19
vstupov s lotmi **2,96–15,06** (5× rozptyl), IBS EZ 11 mala 35 vstupov s 3,06–12,07, TKS 16 vstupov s 0,72–4,11.
Na CFD sa veľkosť počíta presne z rizika, kým backtest na MNQ zaokrúhľuje na celé kontrakty. Správne porovnanie je
preto v **R**, nie v dolároch, a to je T3. Moje tvrdenie A14 bolo procesné: pravidlo vypnutia existovalo a
nevykonalo sa. To ostáva pravdou bez ohľadu na štatistiku. Šesť týždňov je pod MinTRL, súhlasím. Prop účet však
MinTRL nečaká.

**A17 a A19: prijímam.** Ide o tri definície DD, nie o protirečenie. Problém je, že nikde nie je určené, ktorá z nich
riadi veľkosť pozície. A19 má menší rozsah: MTK ORB, MTK EMAS a 6E pred 2016.

**A1 „PF 1,3 z 1 000 náhodných“: prijímam, je to nesimulovaný odhad.** Môj argument z neho nestojí. Stojí na A3
(medián kandidátov na OOS ≈ 1,0 pri výbere chvosta) a na DSR.

**Vaše zosilnenia A9, A15 a B1–B6 prijímam.** Najmä vstup SPRÁV na NFP v T+0 (`r3Enter: 0`) je okamžité riziko
pravidiel účtu (bod 4).

---

## 2. Útok na váš proces (a)

Smer je dobrý. Pre nás má ale päť dier a dve nereálnosti.

**D1. Register a rozpočet sa dajú obísť kópiou stratégie.** Dnes máme `…net`, `…eod`, `…mym`, `…es`, `…mgc`,
`…btc`, `…eur` a filter `_11`. Rozpočet „200 konfigurácií na stratégiu“ sa obíde tak, že sa založí ďalší kľúč.
Rodina Williams R (`wpr`, `wpres`, `wprmgc`, `wprmym`, `wpreur`) má podľa `gl_state` spolu **76 352** kombinácií.
6E je preživší z piatich trhov a jej 3 477 pokusov je klamlivo málo.
→ **Rozpočet na hypotézu, nie na kľúč**: 300 konfigurácií spolu na všetky trhy aj verzie jednej myšlienky.
Každá kópia, filter alebo zmena kódu po pozretí výsledkov ide z toho istého rozpočtu. Trh sa počíta ako pokus.

**D2. Walk-forward unikne cez návrh mriežky.** Rozsahy v `GROUPS` (`glsearch.py:160–470`) navrhovali ľudia, ktorí
videli výsledky 2021–2026. Aj walk-forward s reoptimalizáciou tak nesie informáciu z budúcich okien.
→ Mriežky **zmraziť commitom dnes**. Pre existujúce stratégie platí WF len ako dolná kontrola, nie ako dôkaz. Ako
dôkaz platí len pri nových hypotézach, kde mriežka vznikla pred pohľadom na dáta.

**D3. „Efektívne N cez zhluky korelácie > 0,9“ je ďalší ladiaci gombík.** Kto zvolí prah 0,7 alebo 0,95, posunie DSR
tam, kam chce.
→ Metódu zmraziť vopred: **N_eff = počet zhlukov pri |ρ| > 0,5 na mesačnom PnL**, s podlahou N_eff ≥ N / 50.
Brána: DSR ≥ 0,95 pri N_eff **a súčasne** DSR ≥ 0,5 pri surovom N.

**D4. Trezor C (9/2026–dnes) už nie je čistý.** November sme rozobrali do detailu (KONVERZACIA §1, špička
volatility) a podľa neho vznikol filter `_11`. Každý, kto teraz navrhne hranicu pre trezor C, vie, že v novembri
Nasdaq intraday prehrával.
→ Trezor C ber len ako **kontrolu exekúcie** (zhoda so simuláciou), nie ako test edge. Za čistý trezor C považujem
až dáta od **1. 12. 2026** s hranicou zapísanou pred týmto dátumom.

**D5. Prop ruina cez denný PnL uzavretých obchodov podhodnotí denný limit.** FTMO meria equity aj s otvorenými
pozíciami. Riešenie je lacné: emulátor už drží `max_price` / `min_price` obchodu (`emulator.py`, `EmuTrade`). Denná
equity sa dá poskladať z najhoršej MAE súčasne otvorených pozícií a 1m sviečok.
→ Brána: **P(denný pokles equity ≥ 4 %) ≤ 2 %** (rezerva 1 % pod limitom 5 %) a **P(celkový ≥ 8 %) ≤ 5 %** za
12 mesiacov, z blokového bootstrapu s blokom 5 obchodných dní, aby ostali zhluky ako v novembri.

**N1. Štatistická sila na MNQ/MYM je nereálna.** Váš prah na trezore (t ≥ 2, ≥ 300 obchodov) pri PF 1,2 znamená
t ≈ 0,09·√n, teda **n ≈ 500** pre t = 2 a ~1 100 pre t = 3. MNQ a MYM majú trezor B len 6/2019–9/2021, čo pri 150
obchodoch za rok dáva ~350 obchodov. Stratégia s pravým PF 1,2 na MNQ trezorom B **nikdy neprejde**. To nie je
chyba brány, len to treba povedať nahlas.
→ Buď (i) stiahnuť **NQ 2010–2019** (Databento, prahy v ATR/%), čo dá ~1 300 obchodov, alebo (ii) pripustiť len
stratégie s PF ≥ 1,35 po nákladoch, pri ktorých 350 obchodov dá t ≈ 2. Odporúčam (i). Bez nej Nasdaq stratégie
nemáme ako obhájiť.

**N2. „Iné aktívum“ medzi indexmi USA je takmer ten istý test.** NQ, ES a YM majú intraday koreláciu ~0,85–0,95
(hypotéza, čísla nemáme zmerané u nás). Prejsť MNQ → ES bez zmeny parametrov je slabšie, než sa tvári.
→ Za nezávislé počítať len **iné časové pásmo alebo inú triedu aktív**: DAX alebo Nikkei pri ich vlastnom otvorení,
zlato, FX. Pre NY-intraday stratégie ostáva ako potvrdenie len NQ 2010–2019 (N1) a forward.

**Výpočtový čas nie je prekážka, ale treba ho spočítať.** WF s rozpočtom 300 × 4 okná = 1 200 behov na hypotézu.
Pri ~1–2 min na 2 roky s 1m detailom a 12 súbežných procesoch na Mac mini + hube je to **~2–3 h na hypotézu**.
Dnešný automat spálil 1,55 mil. behov, teda ~1 000× viac. PBO potrebuje mesačný PnL každej konfigurácie, ktorý
`gl_<key>.jsonl` dnes neukladá. Treba to doplniť do `evaluate()`.

**Fill model (vaša zásada 2): súhlasím, len doplním čísla.**
- Limitka a TP: plnenie až pri prechode o 1 tick.
- Stop a market: +1 tick sklz na MNQ, MES a MGC, +0,5 ticku na 6E.
- Náklad v tickoch: MNQ 1,5, MGC 1,5, ES 1, 6E 1.
- Pre CFD: spread zmeraný z `m1` + `fill` za október–november (D4: na exekúciu to použiť smieme).
- **Ak stratégia s takým modelom na ladení neprejde PF 1,15, do ďalších krokov nejde.** Je to lacný filter, ktorý
  vyradí väčšinu RR 0,5 profilov skôr, než minieme trezory.

---

## 3. Otázka (b): kde sa zhodneme a kde nie

| stratégia | Inžinier | ja | čo spor rozhodne |
|---|---|---|---|
| Williams R 6E | najsilnejší kandidát | **súhlas**, ale je to preživší z 5 trhov (D1), Bonferroni ×5 to unesie (t 4,1) | **T4**: tickový náklad + sklz na 2016–9/2021, hranica PF ≥ 1,15 a t ≥ 2,5 |
| Noc + pondelok MNQ | kandidát s výhradou pôvodu | súhlas. `nocpon` má v `gl_state` 0 kombinácií, takže bez rodokmeňa nie je kandidát | doložiť, z koľkých pokusov vznikol (behy v histórii s `nocpon` pred dátumom profilu), a prahy ATR vs body |
| NOA / NOA EOD | kandidát po oprave exekúcie | **nesúhlas**: 37 700–76 305 pokusov, DSR 0,33, staré roky t ≈ 1,9 (pod vaším prahom 3 pre rodinu 44), naživo 4/19. Nie je to kandidát, je to **pozastavený podozrivý** | **T3** (R analýza živých) a potom T1-štýl na NQ 2010–19 |
| Volt Break | slabý | súhlas: najlepší pomer pokusov a výsledku, ale t 2,1 | NQ 2010–19 |
| ON bias ORB | slabý, profil „odinakiaľ“ | súhlas, rovnaký problém pôvodu ako `nocpon` | rodokmeň |
| ORB 15/5 ES | mŕtva (sklz) | **nesúhlas, zatiaľ**: staré roky už mali „poplatok 1 tick/strana“ (PRVE_VYSLEDKY) a PF 1,07 je až po ňom. Váš +1 tick je odhad | **T4b**: ten istý beh s +1 tick len na stop/market výstupoch. PF < 1,0 → mŕtva, ≥ 1,03 → ⚠ |
| IBS EZ (MNQ, MYM, ES) | mŕtva s nečistým dôkazom | neobhájená (bod 1). Pre live to vychádza nastejno | **T1** |
| TKS, VWAP ORB, NY VA, IVB, NOA MGC, Sigma MGC | mŕtve | súhlas. Pri TKS a VWAP ORB je kľúčovým dôkazom medián OOS ~1,0, nie staré roky | — |
| SPRÁVY MGC / EUR | neoveriteľné a nebezpečné | súhlas | kalendár 2016–20 + GC; dovtedy nie na funded |

**Navrhnuté rozhodujúce testy (nespúšťam ich, hranice sú zapísané tu, teda vopred):**
- **T1 IBS EZ, režim vs edge:** profil IBS EZ 1 bez zmeny, ale bodové prahy prepočítané pomerom Ø ceny (ladenie /
  test), na MNQ a MYM 6/2019–9/2021, tickový náklad a fill-through. Hranica: PF ≥ 1,10 a ≥ 2/3 roky v pluse na oboch
  trhoch, inak je mŕtva definitívne. Ak prejde, ide do D1–D3 ako nová hypotéza.
- **T2 Citlivosť na fill:** pre živé profily (TKS 1, IBS EZ 1/11, NOA 1, VWAP ORB 1) spočítať v existujúcich behoch
  podiel TP, kde `exit == high/low` výstupnej minúty. Potom prepočítať PF, keď (a) TP dotyky bez prechodu o tick
  vypadnú (obchod ide na ďalšiu minútu) a (b) SL dostane +1 tick. Hranica: PF ≥ 1,15 na 5 oknách, inak profil
  na live nepatrí ani po T1.
- **T3 NOA naživo v R:** 19 vstupov na Server3 spárovať so simuláciou (`tester.livesim`) na tých istých sviečkach.
  Pre každý obchod zapísať zhodu (čas, smer, vstup, SL, TP) a výsledok v R. Rozhodnutie: ak nespárované alebo posunuté
  obchody vysvetlia > 50 % straty v R, je to chyba exekúcie (opraviť, demo 8 týždňov). Ak sa spárované obchody
  zhodujú a strácajú, je to rozptyl a platí štatistika (P(≤ 4/19 | 0,41) ≈ 6 %).
- **T4 / T4b:** pozri tabuľku.
- **T5 Ruina portfólia:** štyri dnes bežiace inštancie zo Server3 (NOA, TKS, IBS EZ 11, SPRÁVY) podľa D5 so
  skutočnými veľkosťami z fill udalostí. Ak P(denný ≥ 4 %) > 2 %, účet je dnes predimenzovaný bez ohľadu na edge.

---

## 4. Poradie: čo môže zničiť účet najskôr

**Tento týždeň (do 4. 12. 2026, prvý piatok decembra = najbližšie NFP):**
1. **Zistiť typ účtu FTMO-Server3** (výzva či funded) a pravidlo o správach. Do vtedy SPRÁVY profil_3 (`r3Enter 0`,
   NFP v T+0) **pozastaviť** (`/pause`). Je to jediné riziko s pevným dátumom.
2. **Pozastaviť na Server3 TKS a IBS EZ 11** (neobhájené, IBS EZ 11 ladená na živom období) a **NOA do T3**. Nechať
   bežať len demo inštancie. Rozhoduje o tom používateľ, toto je moje odporúčanie.
3. **Tvrdý stop na úrovni účtu skôr, než sa čokoľvek znova zapne:** denný pokles equity −2 % → flatten + pause všetkých
   inštancií účtu, celkový −6 % → stop. Dnes neexistuje (A16). Do vtedy aspoň ručné pravidlo s alarmom cez Telegram
   plugin.
4. **Prevádzková inventúra:** Tradeify NT (`TDFYSL`, posledný signál 19. 11.). Má otvorenú pozíciu? Beží naslepo?
   Duplicitné inštancie (FTMO Demo + Server3 27.–29. 10.). Ktoré inštancie reálne obchodujú dnes.
5. **Zmraziť:** žiadne nové ladenie ani filter na októbri a novembri 2026, mriežky `GROUPS` commitnúť ako zmrazené
   (D2), IBS EZ 11 označiť ako kontaminovaný.

**Do 2 týždňov (zastaví ďalší prísun zlých profilov):**
6. Webapp a stránka: z titulov dať preč „posl. rok PF“, zaviesť značku zo starých rokov (krok 12, `oos_stav.json`),
   **vypnúť radenie podľa OOS** (`gldash.py:480`, audit A „OOS ≥ 1,4“) a zjednotiť smernicu (150 vs 75, každý rok).
7. Fill-through a tickové náklady v emulátore za prepínačom, potom T2 a T4.
8. T3 (NOA) a T5 (ruina) z existujúcich dát, bez nových backtestov.

**Do 1–2 mesiacov (aby sa dalo čomukoľvek veriť):**
9. Register pokusov na hypotézu (D1), mesačný PnL v `evaluate()`, DSR/PBO ako brány s vopred zmrazenou metódou (D3).
10. NQ 2010–2019 z Databenta (N1) a T1. Kalendár SPRÁV 2016–2020.
11. Čistý trezor C od 1. 12. 2026 s hranicami zapísanými do 30. 11. Demo ≥ 8 týždňov a ≥ 40 obchodov, vypínanie cez SPRT.

**Kde sa zhodneme:** dnes nič nemá dôkaz zisku po nákladoch. Najbližšie má Williams R 6E. NOA nie je kandidát, kým
T3 nepovie, čo sme naživo vlastne obchodovali. Najrýchlejšou cestou k ruine nie je slabý edge, ale **správa v T+0 na
funded účte a chýbajúci denný stop pri troch korelovaných Nasdaq stratégiách**. To sa dá opraviť tento týždeň bez
jediného backtestu.

---

# Agent B (Inžinier) — 3. kolo: odpoveď na repliku

*26. 11. 2026, len čítanie. V tomto kole som nové veci overil v `glsearch.py:595–606`, `base_*.json`,
`PRESIEL_SMERNICAMI_IBS_EZ_ES_1.json` a `gl_state.json`.*

Pán Prokurátor, prijímam D1–D5, N1, výpočtový odhad aj vaše čísla k fill modelu. Všetko ide do SMERNICA_V2. Pri
N2 s vami súhlasím čiastočne. V jednom bode sa mýlite vy a v dvoch sme sa obaja nechali oklamať tým istým triedením.

## 1. Kde sa mýlite: IBS EZ ES nemá bodové prahy
`tradebot/strategies/ibsentryesnet/configs/PRESIEL_SMERNICAMI_IBS_EZ_ES_1.json` má **všetky** prahy v ATR
(`fvgMinSize {1,5 atr}`, `minImbSizePoints {0,3 atr}`, `srClusterPoints {1,54 atr}`…). Kópie na ES, MGC a EUR
`glsearch` ladí v ATR (`A = lambda v: {"unit": "atr"}`), MNQ originál v bodoch. Argument B2 preto ES nezasahuje
a **IBS EZ ES 0,75 (3/12) ostáva čistým dôkazom**. Výhradu mám len k nákladu: 1 tick na stranu bol pri ES 1 050–2 000
percentuálne drahší, a „pred poplatkami 1,10“ znamená, že hrubý edge existuje, len ho poplatky zjedia. Pre živé
rozhodnutie je to rovnaké. T1 na MNQ/MYM s prepočítanými prahmi podporujem.

## 2. Kde sme sa mýlili obaja: dva „✅“ zo starých rokov sú in-sample
- **Williams R 6E:** `glsearch.py:595–606` má `PERIODS["wpreur"] = ("20160101-20211001", "20211001-20260904", …)`,
  čiže **ladila sa na 2016–9/2021**. To je presne obdobie „starých rokov“ v OOS-STARE-ROKY. Zhoda „1,54 vs 1,53
  z ladenia“ je preto tautológia. Moje t ≈ 4,1 neplatí a beriem ho späť. **Skutočné OOS má 6E na 10/2021–9/2026.**
  Tam 9 z 9 kandidátov skončilo nad 1,0: medián 1,16, rozsah 1,03–1,33 a 460–1 430 obchodov. To je lepší obraz než
  pri MNQ stratégiách (chvost z mediánu 1,0), ale náklad je v percentách (~0,4 ticku namiesto ~1). **Váš T4 preto
  treba spustiť na 10/2021–9/2026, nie na 2016–2021.**
- **Noc + pondelok:** `base_nocpon.json` píše „z prieskumu Nasdaqu: MNQ 2019–2026“. Prieskum teda roky 2019–21
  videl a ✅ je in-sample ako pri MTK ORB. Z kandidáta ho preraďujem na **⏳ neoverený**. Čisté dáta preň budú
  až NQ 2010–2019.

Záver k (b) je teda ešte tvrdší: **zo zoznamu ✅ po tomto kole nezostal ani jeden čistý dôkaz zo starých rokov.**
Najlepšie podložené je 6E na 2021–2026, čo je reálne OOS, ale na jedinom trhu po prežití z piatich (D1). Hneď za
ním ide NOA ako hypotéza.

## 3. NOA: dohoda a nový test
Prijímam „pozastavený podozrivý“ pre **ladené** profily (37 700+ pokusov, DSR 0,33). Treba však dodať fakt:
`base_noa.json` je „presne podľa článku Zarattini, Aziz, Barbon (2024), Beat the Market“. Je to vonkajšia,
publikovaná hypotéza (SPY 2007–2024) **s nulovým hľadaním na našich dátach**. Navrhujem preto **T6: NOA podľa článku
bez zmeny parametrov na NQ 2010–2019**, s tickovým nákladom a fill-through. Hranica: PF ≥ 1,10, t ≥ 2,0, ≥ 60 %
rokov v pluse. Je to jediný test v repe s N = 1. Pozor na McLean–Pontiff: publikovaný edge po publikácii slabne.

## 4. Ostatné body
- **D3 (N_eff):** prijímam ρ > 0,5, podlahu N/50 aj dvojitú bránu (DSR pri N_eff aj pri surovom N). Do smernice
  idú zmrazené.
- **D4:** súhlasím. Obdobie 9/2026–11/2026 slúži len na kontrolu exekúcie, čistý trezor C začína 1. 12. 2026.
- **N2:** pozitívny dôkaz má len iné pásmo alebo iná trieda aktív, súhlas. Nesúhlasím však s tým, aby sa ES a YM
  vyhodili. Ako **negatívny test** majú veľkú silu: stratégia, ktorá na ES bez zmeny prehráva, je podozrivá
  (Williams R ES 0,67). V smernici sú preto „povinne nesmie zlyhať“, nie „počíta sa ako potvrdenie“.
- **ORB 15/5 ES:** ustupujem. Rozhodne T4b s vašou hranicou.
- **Trezor B je už sčasti spálený.** Triedenie 26. 11. sa na ES 2010–21, MGC 2020–21, MNQ/MYM/BTC 2019–21 a 6E
  2016–21 už pozrelo. Pre stratégie z `webapp_vyber.json` je to použitý trezor. Čisté sú len **NQ 2010–2019,
  YM 2010–2019, GC 2010–2019** (treba ich stiahnuť), DAX a Nikkei a od 1. 12. 2026 trezor C.
- **SPRÁVY a pravidlá FTMO:** podľa používateľa náš účet smie obchodovať správy, takže argument o NFP v T+0 a
  2-min pravidle (môj A9, váš bod 4) **sťahujeme**. Ostáva len preladenie: ~40–50 parametrov na ~36 obchodov za rok,
  staré roky neoverené a kalendár až od 2021. Do V2 ide všeobecný krok „overiť pravidlá konkrétneho účtu“ bez
  predpokladov.
- **SPRÁVY ako hypotéza:** uznávam, že sú postavené na správaní trhu, nie na hrubom hľadaní. DSR 0,959 je jediný nad
  0,95. Vo V2 ich vedieme ako **⏳ kandidáta s ekonomickým dôvodom** a chýba im len trezor B. Výskum však videl aj
  rok A (2 302 kombinácií × 5 okien, 3 seedy, 125 RRR) a to sa do N počíta. V2 všeobecne zvýhodňuje ekonomický dôvod:
  t_req −0,3 a haircut z ½ N_eff.

---

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

---

# SPRÁVY (MGC) na rokoch 2010–2021 — nastavenia NEZMENENÉ (26. 11. 2026, Mac mini)

Profily `spravynet/configs/profil_1..3.json` bez zmeny, natívne C# jadro, MGC 5m, 1m detail. Kalendár pred 2021 z exportu
ForexFactory (Hugging Face Tropstan/Forex_Factory_Calendar, 1 937 správ 2010–2020), pridaný cez `newsAdd`. Overenie
kalendára na 2021–4/2025: dni sedia 100 % (FOMC, CPI, NFP, PPI, JOLTS, RETAIL, PCE, GDP), ISM ~90 %.
Kontrola cesty: referenčné okná 2021–2026 dávajú tie isté PF ako tituly profilov (3–7).

| okno (okt–okt) | profil 1 PF (obch, $) | profil 2 | profil 3 |
|---|---|---|---|
| 2010/11 | 1,00 (26, +11) | 1,20 (37, +421) | 0,53 (51, −4 976) |
| 2011/12 | 1,05 (32, +123) | 0,67 (44, −1 062) | 0,78 (56, −1 708) |
| 2012/13 | 0,71 (35, −1 157) | 1,07 (48, +257) | 0,92 (63, −759) |
| 2013/14 | 1,38 (30, +1 069) | 0,91 (41, −277) | 0,81 (58, −1 684) |
| 2014/15 | 0,84 (33, −662) | 0,71 (48, −1 406) | 0,97 (64, −362) |
| 2015/16 | 1,71 (33, +2 447) | 1,71 (49, +2 412) | 1,73 (69, +6 713) |
| 2016/17 | 1,22 (38, +915) | 1,28 (53, +1 004) | 1,34 (75, +3 759) |
| 2017/18 | 1,00 (39, −23) | 1,21 (55, +916) | 1,11 (76, +1 376) |
| 2018/19 | 0,97 (34, −80) | 1,04 (51, +140) | 1,20 (72, +2 008) |
| 2019/20 | 0,97 (33, −99) | 1,22 (48, +739) | 1,29 (69, +3 075) |
| 2020/21 | 0,66 (40, −1 783) | 0,70 (52, −1 242) | 0,97 (74, −455) |
| **spolu 2010–2021** | **+761 $, 373 obch, 5/11 rokov +** | **+1 902 $, 526, 7/11** | **+6 987 $, 727, 5/11** |
| *ref. 2021–2026* | *+21 736 $, PF 3–7* | *+18 893 $, PF 2,8–7* | *+61 450 $, PF 2–3,5* |

**S nákladom 1,5 ticku (0,15 b., model repa) namiesto poplatku smernice:** staré roky profil 1 **−10 361 $** (2/11 rokov +),
profil 2 **−8 595 $** (1/11), profil 3 **−37 197 $** (1/11). Referenčné okná ostávajú v pluse (PF 1,5–5,6).

## Záver (kriticky)
- Na 11 rokoch, ktoré výber nevidel, sú všetky tri profily **okolo nuly** (PF ~1,0) a s realistickým nákladom **stratové**.
  PF 3–4 z rokov 2021–2026 sa mimo nich neopakuje → **výber pravidiel je prispôsobený rokom 2021–2026**.
- Možná obhajoba: od 2021 je inflačný režim, keď zlato na CPI/PPI/PCE reaguje silnejšie. Aj keby to tak bolo, edge je
  **viazaný na režim** a môže skončiť bez varovania — to nie je dôkaz, že stratégia funguje, len hypotéza.
- Výhrada k dátam: MGC pred 2020 má neúplné pokrytie seansy (33–74 %), ale okno 2020/21 (dobré dáta) je tiež v strate.
- Odporúčanie: SPRÁVY naživo nepovažovať za overené; nanajvýš znížená veľkosť ako stávka na režim, o tom rozhoduje používateľ.

---

# Agent B (Inžinier) — záver

*26. 11. 2026, len čítanie.*

## Súhlasím s Prokurátorom (všetko je prevzaté do SMERNICA_V2)
- Každá štúdia a prieskum je pokus a spáli obdobia, ktoré videla. Trezor B je čistý len pre rodinu, ktorá na ňom
  ešte nebežala.
- **t_req podľa kumulatívneho počtu hypotéz na trezore**, nie podľa dávky. Bez toho by sa dala brána obísť
  salámovou metódou.
- Walk-forward má jednorazový zámok. Behy WF sa do N pre DSR nepočítajú.
- Bonus za ekonomický dôvod len s vonkajším zdrojom pred prvým pohľadom alebo s overeným vedľajším javom.
- Susedia v plató sa počítajú do rozpočtu 300.
- Spread CFD sa musí logovať v EA (`bid/ask` dnes v zrkadle nie je) a okolo správ sa meria zvlášť.
- Typ DD účtu (trailing) v simulácii, súčasné riziko ≤ 1,5 % a ochrana lokálne bez hubu.
- Demo ≥ 8 týždňov **a** ≥ 40 obchodov a kontrola sklzu prvých 40 ostrých.
- Jedna smernica v repe, strop 10 hypotéz za štvrťrok, ✅ zapisuje len skript a stavy podpisuje používateľ.
- CFD replay, vypnutie `glwebvyber --apply`, hash kódu v registri.
- T6 primárne po publikácii (MNQ 6/2024–9/2026), lebo autori videli 2007–2024. Prijímam a beriem späť svoje
  „NQ 2010–19 je čisté“.
- T4 (6E) je len negatívna kontrola, lebo rok A 6E je spálený. T4b dáva najviac ⚠.
- Minimum 100 obchodov v každom roku s výnimkou zapísanou vopred.

## Nový dôkaz k SPRÁVAM
Profily 1–3 bez zmeny na MGC 2010–2021 dávajú PF ~1,0 a s nákladom 1,5 ticku sú všetky v strate (1–2/11 rokov
v pluse), kým 2021–26 mali PF 2–7. Moje predošlé zaradenie „⏳ kandidát s ekonomickým dôvodom“ **mením na ❌ pre
legacy profily**. Výber pravidiel je zjavne prispôsobený režimu 2021–26. Ekonomický dôvod (reakcia na správy) ostáva
otvorený len ako **nová hypotéza SPRÁVY-jadro** s ≤ 5 parametrami. MGC/GC 2010–21 je pre ňu spálený, takže sa dá
overiť len v trezore C alebo na inom aktíve.

## Čo ostáva
- Dnes **nemáme ani jednu stratégiu s čistým pozitívnym dôkazom**. ✅ môže vzniknúť až z B′ (NQ/YM/GC 2010–19)
  alebo z C (od 1. 12. 2026, ak sa hranice commitnú do 30. 11.).
- Najbližšie k dôkazu: Williams R 6E (rok A 9/9 kandidátov > 1,0, medián 1,16), NOA podľa článku (T6), Noc +
  pondelok (B′).
- Päť otázok pre používateľa je v SMERNICA_V2 §9 (100 obchodov, SPRÁVY naživo, Server3, NQ/YM/GC, pravidlo WR).
- Prvá vec ešte pred akýmkoľvek kódom: ručný denný stop −2 % a pravidlá účtov (P1–P2). Prvá vec v kóde je ochrana
  účtu v EA a NT.
- Výhrada k mojim t-odhadom: počítal som ich z PF, n a predpokladaného WR. Presné t treba vypočítať z obchodov
  v registri.

---

# Agent B (Inžinier) — rozdelenie dát: Databento futures a BTC

*26. 11. 2026. Len čítanie. Meranie je `kritika/dq_scan.py` (nice 19, po jednom súbore, 37 s) → `kritika/data_kvalita.json`,
k tomu iCloud `OOS-STARE-ROKY/data/dbq.json`. V `data/` som nič nemenil a nič som nesťahoval.*

**Metóda:**
- **Pokrytie** = počet 1m sviečok v jadre seansy / (dni s dátami × dĺžka okna). Okná v UTC sedia v lete aj v zime:
  - US indexy 14:30–20:00,
  - 6E a MGC 8:00–16:00 (Londýn + NY),
  - BTC 24/7.
- **„krátke“** = dni s < 50 % okna (sviatky a skrátené dni).
- **Zlé tiky** = skok > max(25 × medián |výnosu|, 0,3 %), ktorý sa hneď nasledujúcou minútou vráti.
- **Veľký rozsah** = (H − L) / C > 40 × medián.
- **Rolovanie** = skok medzi kontraktmi v deň rolovania (archív nie je back-adjustovaný).

---

## 1. Kvalita po trhoch

### MNQ (Databento, 5. 5. 2019 – 9. 11. 2026)
| rok | pokrytie | krátke dni | zlé tiky | problémy | použiteľné |
|---|---|---|---|---|---|
| 2019 (od 5/5) | 98,1 % | 3 | 5 | kontrakt vznikol 5/2019 | ladenie aj trezor |
| 2020 | 98,7 % | 3 | 36 | covid (skoky sú skutočné) | áno |
| 2021–2024 | 98,3–98,8 % | 3–4 | 1–6 | — | áno |
| 2025 | 98,3 % | 4 | 45 | apríl 2025 clá (skutočné), 9. 1. Carter, 28. 11. výpadok CME | áno |
| 2026 (do 9/11) | 98,7 % | 4 | 1 | — | rok A (do 3/9), potom C |

Bez duplicít, NaN aj nelogických sviečok, objem nikde 0. **Rolovanie: medián 0,92 %, max 1,43 %**, najväčšie
zo všetkých trhov.

### MYM (Databento, 2. 6. 2019 – 9. 11. 2026)
Pokrytie 97,7–98,8 % každý rok, zlé tiky 0–4 (2020: 56, 2025: 23, oba trhové udalosti). Rolovanie 0,53 % / 1,18 %.
**Celé obdobie je čisté.**

### ES (Databento, 6. 6. 2010 – 19. 10. 2026)
| roky | pokrytie | zlé tiky | problémy | použiteľné |
|---|---|---|---|---|
| 2010–2019 | 98,1–99,5 % | 0–3 / rok | 2012 a 2013 skok na prelome roka 1,7 % a 1,35 % (sviatky a rolovanie, overiť) | áno |
| 2020 | 98,7 % | 28 | covid | áno |
| 2021–2024 | 98,3–98,8 % | 0–2 | — | áno |
| 2025 | 98,3 % | 30 | apríl 2025 | áno |
| 2026 (do 19/10) | 98,6 % | 3 | archív končí 19. 10. | A, potom C (treba doplniť) |

Rolovanie 0,40 % / 1,73 %. **16,3 roka čistých dát**, je to náš najlepší trh.

### MGC (Databento, 3. 10. 2010 – 16. 9. 2026)
| rok | pokrytie | krátke dni | použiteľné |
|---|---|---|---|
| 2010 | 8 % | 64 z ~65 | **nie** |
| 2011–2015 | 31–39 % | 206–247 | **nie** (seansa má väčšinou diery) |
| 2016–2017 | 64–66 % | 11–49 | **nie** |
| 2018 | 77 % | 2 | **nie** |
| 2019 | 92 % | 0 | **nie** (pod 95 %), nanajvýš denný alebo 4h TF ako informácia |
| 2020–2026 | 99,5–100 % | 0–1 | áno |

Rolovanie 0,31 % / max **2,08 %**. **Čisté je len 1/2020 – 9/2026 (6,7 roka).** MTK ORB (ladená 2010–2024) aj
test SPRÁV na 2010–2021 (07) stoja na riedkych dátach.

### 6E (Databento, 6. 6. 2010 – 28. 9. 2026)
| roky | pokrytie | zlé tiky / rok | veľký rozsah / rok | použiteľné |
|---|---|---|---|---|
| 2010–2015 | 99,1–100 % | **220–636** | **957–3 906** | **nie v tomto stave**. Po vyčistení (filter „skok a späť“) kandidát na trezor B′ |
| 2016–2026 | 99,7–100 % | 0–3 | 0–18 | áno |

Rolovanie 0,35 % / 0,80 %. Čistých je **10,7 roka (2016+)**. Roky 2010–15 zaťažuje ~1 600 zlých tikov.

### BTC — výber zdroja
| zdroj | obdobie | pokrytie | diery > 2 h | zlé tiky / rok | objem 0 | poznámka |
|---|---|---|---|---|---|---|
| **Binance futures BTC/USDT perp** | 8. 9. 2019 – 4. 9. 2026 | 99,3–100 % | **0** | 8–31 (2020: 141, marec) | 0–0,2 % | k tomu funding a mark (1h) |
| Binance spot BTC/USDT | 8. 9. 2019 – 5. 9. 2026 | 99,8–100 % | 2–5 / rok v 2019–21 | 5–30 (2020: 92) | ~0 % | — |
| Coinbase BTC/USD | 1. 8. – 4. 9. 2026 | 98,1 % | 0 | 1 | 0 % | len 1 mesiac |
| Dukascopy BTC/USD (CFD) | 5/2017 – 9/2026 | 77–86 % (2017–20), 92–99,6 % potom | 54–113 / rok v 2017–20 | 75–348 | **97–100 % od 2021** | bez objemu, diery |

**Vyberám Binance futures BTC/USDT perp:**
- je najkompletnejší (nula dier v seanse, pokrytie 100 % od 2020) a má skutočný objem (stratégie s VWAP a objemom),
- je to najlikvidnejší BTC trh na svete, takže sa najmenej odchyľuje od ceny, ktorú dostane akýkoľvek broker
  vrátane CFD,
- naše BTC kópie počítali s poplatkom Binance (`FEE_KEY` 0,02 % maker), teda sedí s tým, kde sa malo obchodovať,
- funding je v archíve, takže ho pri držaní cez 8 h vieme započítať (pri spote nie je, pri CFD je swap).

Spot slúži ako kontrola (rovnaké obdobie, 2019–21 má pár dier). Dukascopy a Coinbase sa nepoužívajú. **Archív BTC
končí 4. 9. 2026**, takže pre C treba dopĺňať (hub `livedata`).

---

## 2. Princípy rozdelenia (dohodnuté + čo z nich vyplýva)
- **Walk-forward 24/6** potrebuje L ≥ 4 roky (24 mesiacov učenia + ≥ 4 testovacie kúsky).
- **Trezor** musí mať ≥ 2 roky **a** ≥ 300 obchodov a aspoň jeden iný režim. **Pri 100 obchodoch za rok to znamená
  ≥ 3 roky**, takže 2 roky stačia len stratégiám s ≥ 150 obchodmi za rok.
- **A** (4. 9. 2025 – 3. 9. 2026) je spálený pre všetkých. Pre EUR legacy je spálené celé 10/2021 – 9/2026.
- **C** začína dňom po commite hraníc (cieľ 1. 12. 2026). Potrebuje živé dopĺňanie archívu (ES končí 19. 10.,
  MGC 16. 9., 6E 28. 9., BTC 4. 9.).
- **Legacy rodiny** (všetko z webapp k 26. 11.) majú L 10/2021 – 9/2025 zmrazené. Staré roky z triedenia
  26. 11. majú spálené (ES 2010–21, MGC 2020–21, MNQ/MYM/BTC 2019–21, 6E 2016–21 je ich L). Čistý im ostáva
  **len B′ (nové dáta) a C**.
- **Nové hypotézy** smú dostať chronologické rozdelenie so starším L a dvoma trezormi, ak ich rodina na tých
  obdobiach nikdy nebežala (register to overí).

---

## 3. Návrh rozdelenia po trhoch

### ES
| oblasť | nové hypotézy | roky | obchody pri 100/rok | režimy |
|---|---|---|---|---|
| L (+ WF 24/6, ~12 kúskov) | 6. 6. 2010 – 30. 9. 2018 | 8,3 | ~830 | 2011 kríza eura, 2015–16, nízka volatilita 2017 |
| B | 1. 10. 2018 – 30. 9. 2021 | 3,0 | ~300 | výpredaj Q4 2018, covid 2020 |
| B2 | 1. 10. 2021 – 3. 9. 2025 (len rodiny, ktoré tam nebežali) | 3,9 | ~390 | bear 2022, rast 2023–24 |
| A | 4. 9. 2025 – 3. 9. 2026 | 1 | — | spálený |
| C | od 1. 12. 2026 | — | — | demo |

- **Legacy ES** (IBS EZ ES, NY VA, ORB 15/5, IVB, Williams R, NOA ES, M2): L 10/2021 – 9/2025, B 2010–21 spálený
  → **len C**.
- **T4b** (ORB 15/5) je negatívna kontrola na spálenom B.
- **Námietka k L 2010–18:** trh mal vtedy menej mikrokontraktov a algo flow. Pri novej hypotéze treba v hlavičke
  zapísať, prečo by mala platiť dnes.

### MNQ a MYM (Nasdaq a Dow)
**Dnes, bez nových dát:** L 10/2021 – 9/2025 (4 roky, WF 4 kúsky, ~400 obchodov). B 6/2019 – 9/2021 má len 2,3 roka
a ~230 obchodov, **teda menej než 300**. Pre stratégie so 100 obchodmi za rok **nestačí**, prejsť by mohli len tie
so ≥ 130 za rok.

**Po stiahnutí NQ a YM (odporúčanie):** rovnaká schéma ako pri ES, jednotná pre všetky indexy USA.
| oblasť | nové hypotézy | roky | ~obchody | |
|---|---|---|---|---|
| L | NQ/YM 6/2010 – 9/2018 | 8,3 | ~830 | prahy v ATR alebo %, NQ v roku 2010 na ~1 800 bodoch |
| B | NQ/YM 10/2018 – 4/2019 + MNQ/MYM 5/2019 – 9/2021 | 3,0 | ~300 | Q4 2018, covid |
| B2 | MNQ/MYM 10/2021 – 9/2025 (rodiny, ktoré tam nebežali) | 3,9 | ~390 | 2022 |
| A, C | ako pri ES | | | |

**Legacy Nasdaq a Dow** (NOA, TKS, IBS EZ, VWAP ORB, VWAP ADX, Volt Break, Noc + pondelok…): **B′ = NQ/YM
6/2010 – 4/2019** (8,9 roka, ~890 obchodov, režimy 2011, 2015–16, 2018). Je to jediný čistý trezor, ktorý im vieme
dať pred C. T1 a T6 sekundárne bežia tam.

### MGC (zlato)
**Dnes:** čisté len 1/2020 – 9/2026. Legacy L 10/2021 – 9/2025, B 1/2020 – 9/2021 má 1,75 roka a ~175 obchodov,
**nestačí**, a navyše je spálený.

**Po stiahnutí GC 2010–2019 (odporúčanie; GC je likvidný, pokrytie treba najprv zmerať ≥ 95 %):**
| oblasť | nové hypotézy | roky | ~obchody |
|---|---|---|---|
| L | GC 10/2010 – 9/2018 | 8 | ~800 (vrchol 2011, pád 2013, ploché 2014–18) |
| B | GC 10/2018 – 12/2019 + MGC 1/2020 – 9/2021 | 3 | ~300 (covid, rekord 2020) |
| B2 | MGC 10/2021 – 9/2025 (rodiny, ktoré tam nebežali) | 3,9 | ~390 |

- **Legacy zlato** (Fibo, Sigma MGC, NOA MGC, MTK ORB, IVB MGC, SPRÁVY): B′ = GC 2010–2019, okrem SPRÁV, ktoré
  ten podklad a obdobie už videli (07).
- MTK ORB sa ladila na riedkom MGC 2010–2024, a preto jej výsledok z ladenia treba brať ako nespoľahlivý.

### 6E (euro)
| oblasť | nové hypotézy | roky | ~obchody |
|---|---|---|---|
| L (+ WF ~7 kúskov) | 1. 1. 2016 – 30. 9. 2021 | 5,75 | ~575 (Brexit 2016, záporné sadzby, covid) |
| B2 | 1. 10. 2021 – 3. 9. 2025 (rodiny, ktoré tam nebežali) | 3,9 | ~390 (rast sadzieb 2022, parita) |
| B′ | 2010–2015 **po vyčistení zlých tikov** | 5,5 | ~550 (kríza eura 2010–12, 2014–15 QE) |
| A | 4. 9. 2025 – 3. 9. 2026 | | spálený |

- **Legacy EUR** (Williams R, SPRÁVY EUR, Asia sweep…): L 2016–21, A 10/2021 – 9/2026 spálený, takže dnes **len C**.
  Po vyčistení 2010–2015 dostanú B′.
- Čistenie nie je sťahovanie: znamená nový import cez `tester.bento_import` s filtrom „skok a hneď späť“.
- Odporúčam ho, ale len so zápisom, koľko sviečok filter zmenil (cieľ: ≤ 0,5 % sviečok).

### BTC (Binance futures perp)
| oblasť | nové hypotézy | roky | ~obchody |
|---|---|---|---|
| L | 1. 10. 2021 – 3. 9. 2025 | 3,9 | ~390 (bear 2022, FTX, rast 2023–24) |
| B | 8. 9. 2019 – 30. 9. 2021 | 2,1 | ~210 (covid, bublina 2021) — **pod 300** |
| B′ | Binance **spot** 8/2017 – 9/2019 (stiahnuť) | 2,1 | ~210 (bubble 2017, bear 2018) |

- B + B′ spolu dajú ~4,2 roka a ~420 obchodov, ale ide o dva zdroje (spot je bez fundingu), takže výsledky treba
  uvádzať zvlášť.
- **Legacy BTC kópie:** B spálený, takže len B′ (spot 2017–19) a C.

---

## 4. Kde dát nestačí a čo stiahnuť (len odporúčanie, sťahuje používateľ)
| trh | problém | odporúčanie | čo dá |
|---|---|---|---|
| **MNQ / Nasdaq** | čisté len od 5/2019, B 2,3 roka < 300 obchodov, legacy bez trezoru | Databento `GLBX.MDP3`, `ohlcv-1m`, `NQ.FUT` 6/2010 – 5/2019 ako `nq_databento` | B′ 8,9 roka pre všetky Nasdaq stratégie |
| **MYM / Dow** | to isté | `YM.FUT` 6/2010 – 6/2019 | B′ 9 rokov |
| **MGC / zlato** | pred 2020 pokrytie 8–92 % | `GC.FUT` 10/2010 – 12/2019 (najprv zmerať pokrytie) | B′ 9 rokov |
| **6E** | 2010–15 zlé tiky | nové dáta netreba, stačí vyčistiť import | B′ 5,5 roka |
| **BTC** | futures len od 9/2019 | Binance spot BTCUSDT 1m 8/2017 – 9/2019 (data.binance.vision) | B′ 2 roky s medvedím trhom 2018 |
| **všetky** | archív končí 9–11/2026 | dopĺňať živo (hub `livedata` / mesačný push) | trezor C |

**Rolovanie:** skoky 0,3–0,9 % (max 2,1 %) bez back-adjustu. Pri intraday stratégiách nevadia (nové kontrakty sa
neprekrývajú v rámci dňa), ale stratégie s dlhou pamäťou (EMA 200 na 4h, SMA 100 dní, `nocpon` SMA 100) potrebujú
`skipRoll` alebo back-adjustovaný rad. Inak je signál v deň rolovania falošný.

## 5. Zhrnutie pre Prokurátora
- **Čisté dáta:** ES 2010+, 6E 2016+, MGC 2020+, MNQ a MYM 2019+, BTC (Binance perp) 9/2019+.
- **Legacy stratégie** dnes nemajú žiadny čistý trezor okrem C. Jediná cesta k B′ vedie cez nové dáta (NQ, YM, GC,
  BTC spot) alebo vyčistené 6E 2010–15.
- **Nové hypotézy:** ES má hneď schému L 2010–18 / B 2018–21 / B2 2021–25. MNQ, MYM a MGC ju dostanú až po stiahnutí
  NQ/YM/GC.
- Pravidlo „trezor ≥ 2 roky“ je pri 100 obchodoch za rok v skutočnosti ≥ 3 roky. Dnešné MNQ, MYM, MGC aj BTC B ho
  nesplnia.

---

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

---

# Agent B (Inžinier) — dohoda o dátach

*26. 11. 2026. Doplnil som meranie `kritika/dq_night_rolls.py` (nice 19) → `kritika/data_noc_roly.json`.*

Pán Prokurátor, prijímam všetkých sedem bodov vášho zhrnutia. Mám k nim dve upresnenia a nové merania:
- **Jeden rad na trh: súhlas** s jedným doplnkom. Ak ladíme na NQ/YM/GC a obchodujeme mikro alebo CFD, **objemové
  prahy musia byť relatívne** (rvol, percentil, podiel na dennom objeme), nie absolútne. Inak sa nepreneste ani
  z plného kontraktu na mikro. Absolútny objemový prah = ⏳.
- **Prahy legacy pomerom mediánu ATR(14) po rokoch, nie pomerom ceny: súhlas.**
- **Nočné okno** (US 23–13 UTC, FX a MGC 0–7 UTC; percento z najlepšieho roka trhu):
  - MNQ 98–100 % a ES 96–100 % sú v poriadku,
  - **MYM 2019 86,5 % a 2024 94,8 %** sú pod hranicou, nočné stratégie na mikro Dow preto potrebujú YM,
  - **6E 2013 93,8 %, 2014 84,9 %, 2015 94,7 %**: B′ 2010–15 platí pre nočné stratégie len pre 2010–2012,
  - **MGC pred 2020 2–80 %**, nočné stratégie na ňom nie sú možné.
- **Prepínanie kontraktov:** MNQ, MYM, ES a 6E rolujú presne 4× za rok a nikdy sa nevrátia späť. MGC rolovalo 5× za
  rok (G, J, M, Q, Z), ale v **januári 2011 prepína tam a späť** (J1 → M1 → G1 → J1 → M1, tenká likvidita). To je
  ďalší dôkaz, že MGC pred 2020 je nepoužiteľné. GC treba po stiahnutí zmerať tým istým skriptom.
- **Rolovanie:** pri úrovniach z predošlej seansy som sa mýlil, prijímam vašu DOHODU 1–4.
- **BTC chronologicky (L 2019–23, B 2023–25, len perp, náklad podľa miesta obchodovania): súhlas.** Trezor má 2 roky,
  takže stratégia potrebuje ≥ 150 obchodov za rok, inak ⏳ do C.

## Finálna tabuľka rozdelenia (nové hypotézy; ~obchody pri 100 za rok)
| trh (rad) | L + WF 24/6 | trezor B (iný režim) | A spálený | C | legacy |
|---|---|---|---|---|---|
| **ES** | 6. 6. 2010 – 30. 9. 2017 · 7,3 r · ~10 kúskov · ~730 | 1. 10. 2017 – 30. 9. 2021 · 4 r · ~400 (Volmageddon, Q4 2018, covid, QE 2021) | 4. 9. 2025 – 3. 9. 2026 | od commitu hraníc (Databento mesačne) | L 10/2021 – 9/2025 zmrazené, len C (+ T4b negatívne) → najviac 🟡 |
| **NQ** (stiahnuť 6/2010 – dnes; MNQ len exekúcia) | 6/2010 – 9/2017 · 7,3 r · ~730 | 10/2017 – 9/2021 · 4 r · ~400 | to isté | to isté | B′ = NQ 6/2010 – 4/2019 · 8,9 r · ~890, prahy pomerom ATR |
| **YM** (stiahnuť; MYM len exekúcia) | ako NQ | ako NQ | to isté | to isté | B′ = YM 6/2010 – 5/2019 |
| **GC** (stiahnuť 10/2010 – dnes, najprv jadro aj noc ≥ 95 %) | 10/2010 – 9/2017 · 7 r · ~700 | 10/2017 – 9/2021 · 4 r · ~400 (prieraz 2019, covid) | to isté | to isté | B′ = GC 10/2010 – 12/2019 (SPRÁVY nie, sú spálené) |
| **6E** | 1. 1. 2016 – 30. 9. 2021 · 5,75 r · ~7 kúskov · ~575 | B′ 2010–2015 po vyčistení · 5,5 r · ~550 (noc len 2010–12) | 4. 9. 2025 – 3. 9. 2026 (10/2021 – 9/2025 = B2) | to isté | A = 10/2021 – 9/2026, len C (+ B′ po vyčistení) |
| **BTC** (Binance perp) | 8. 9. 2019 – 3. 9. 2023 · 4 r · 4 kúsky · ~400 | 4. 9. 2023 – 3. 9. 2025 · 2 r · ~200 (potrebuje ≥ 150 obch/rok) | 4. 9. 2025 – 3. 9. 2026 | od commitu (len Binance perp) | len C |

- **Bez NQ, YM a GC** sa nové hypotézy na Nasdaqu, Dowe a zlate nespúšťajú a legacy dosiahne najviac 🟡.
- **„Iný režim“** sa meria pred behom: v trezore je aspoň jeden štvrťrok s mediánom denného ATR % mimo IQR L,
  alebo pokles > 15 %, ktorý v L nebol.

Zapracované do SMERNICA_V2 §1.

---

# Agent B (Inžinier) — rozdelenie rokov len z dát, ktoré máme

*26. 11. 2026. Len `data/archive/tester/`, nič stiahnuté ani vyčistené. Odhad obchodov je pri 100 / 150 za rok.*

## Overené proti súborom
| trh (súbor) | prvá / posledná 1m sviečka | použiteľné | dôvod (`data_kvalita.json`, `data_noc_roly.json`) |
|---|---|---|---|
| ES `databento/futures/ES_USD-1m` | 2010-06-06 22:00 / **2026-10-19** | celé | jadro 98,1–99,5 %, noc 96–100 %, zlé tiky 0–30 za rok |
| MNQ `…/MNQ_USD-1m` | 2019-05-05 22:03 / **2026-11-09** | celé | jadro 98,1–98,8 %, noc 98–100 % |
| MYM `…/MYM_USD-1m` | 2019-06-02 22:00 / **2026-11-09** | deň celé, **noc bez 2019 a 2024** | noc 86,5 % (2019) a 94,8 % (2024) |
| MGC `…/MGC_USD-1m` | 2010-10-03 / **2026-09-16** | **len 2020-01-01 →** | 2010–19 jadro 8–92 %, noc 2–80 %, v januári 2011 kontrakty tam a späť |
| 6E `…/6E_USD-1m` | 2010-06-06 / **2026-09-28** | **len 2016-01-03 →** | 2010–15 má 220–636 zlých tikov za rok; od 2016 jadro ≥ 99,7 %, noc ≥ 95,7 % |
| BTC `binance/futures/BTC_USDT_USDT-1m-futures` | 2019-09-08 17:57 / **2026-09-04** | celé | 99,3–100 %, 0 dier |

- **Spálený pre všetkých:** rok A 2025-09-04 – 2026-09-03, len ako negatívna kontrola.
- **C** začína dňom po commite hraníc. Medzi koncom archívu (ES 19. 10., MGC 16. 9., 6E 28. 9., BTC 4. 9.) a C je
  diera, ktorú treba doplniť z rovnakého zdroja.

**Čo majú dnešné stratégie spálené** (`glsearch.py` IS/OOS/PERIODS, `OOS-STARE-ROKY/data/oos_all.tsv`, 145 behov):
- **Predvolene** sa ladí 2021-10-01 – 2025-09-04 a rok A je OOS.
- **EUR_KEYS** (`wpreur`, `asiasweepeur`, `mtkzoneeur`, `lliqeur`, `silverbulleteur`, `ibsentryeur`,
  `sweepengulfeur`) sa ladia 2016-01 – 2021-10, OOS majú 2021-10 – 2026-09.
- **`mtkorb`** sa ladí 2010-11 – 2024-09.
- **Triedením 26. 11. spálené:** ES 2010–21, MGC 2020–21, MNQ/MYM 2019–21, BTC 2019–21 a 6E 2016–21 pre rodiny
  v `oos_all.tsv`: IBS EZ (všetky), NOA (všetky), TKS, VWAP ORB, VWAP ADX, ORB 15/5, IVB, Sigma, Fibo, MTK ORB/Zone/EMAS,
  Williams R, SPRÁVY, CRT, JSS, Mag7, SVP, Noc + pondelok, ON bias ORB, Volt Break, Flash ORB, Range BTC, Sweep engulf,
  Daily open, M2 MNQ, NQ Precision MGC, LLIQ MGC.
- **Štúdie:** prieskum Nasdaqu `nocpon` MNQ 2019–26, KLZAKY (MTK EMAS) a SPRÁVY MGC 2010–21 (07).

---

## ES — 16,3 roka, najlepší trh
| oblasť | dátumy | roky | obch. 100 / 150 |
|---|---|---|---|
| L + WF 24/6 (~10 kúskov) | 2010-06-06 – 2017-09-30 | 7,3 | 730 / 1 100 |
| trezor B | 2017-10-01 – 2021-09-30 | 4,0 | 400 / 600 |
| (B2 len rodiny bez behu tam) | 2021-10-01 – 2025-09-03 | 3,9 | 390 / 585 |
| A spálený · C | 2025-09-04 – 2026-09-03 · od commitu | | |

- **Nové hypotézy:** ✅ je možné. B obsahuje Volmageddon 2018, Q4 2018 a covid.
- **Dnešné:**
  - rodiny z triedenia (IBS EZ ES, NY VA, ORB 15/5 ES, IVB ES, Williams R ES, MTK EMAS ES) → **len 🟡**, ostáva im C,
  - rodiny, ktoré na ES 2010–21 nikdy nebežali (`noaes`, `m2`, `flashorbes`, `nqpreces`), smú raz použiť
    B = 2010-06 – 2021-09 (11,3 r, ~1 100) → **✅ je možné**.

## MNQ — 7,5 roka, z toho 6,3 pred A
| variant | L + WF | trezor B | obch. v B 100 / 150 |
|---|---|---|---|
| **M1 (odporúčam pri 100–150 obch/rok)** | 2019-05-05 – 2022-09-30 · 3,4 r · WF 18/6 = 4 kúsky | 2022-10-01 – 2025-09-03 · 2,9 r | **290** / 435 |
| M2 (pri ≥ 150 obch/rok) | 2019-05-05 – 2023-09-30 · 4,4 r · WF 24/6 = 5 kúskov | 2023-10-01 – 2025-09-03 · 1,9 r | 190 / **285** |

- **Prečo M1:** M2 nesplní „≥ 2 roky“ a pri 150 obchodoch za rok ani 300. M1 nesplní 300 obchodov tesne pri 100 za
  rok (290), preto potrebuje **≥ 105 obchodov za rok**.
- **Režimy v M1:** L má covid, býka 2021 a pád v prvej polovici 2022. B má nízku volatilitu 2023–24 a pád v apríli
  2025. Iný režim treba zmerať (štvrťrok ATR mimo IQR L), pravdepodobne ho splní nízka volatilita 2023–24.
- **Čo M1 stráca:**
  - L má len 3,4 roka a WF beží s učením 18 mesiacov namiesto 24, takže kandidát sa učí z kratších dejín,
  - trezor je jediná cesta 2,9 roka, takže t ≥ 2 pri PF 1,2 potrebuje ~500 obchodov a tie M1 nemá. **✅ je možné
    len pri PF ≳ 1,3 po nákladoch alebo pri ≥ 170 obchodoch za rok.**
- **Nové:** ✅ je možné za podmienok vyššie.
- **Dnešné:**
  - rodiny z triedenia a `nocpon` → **len 🟡**, C ako trezor (≥ 2 r) by dalo ✅ najskôr 12/2028,
  - rodiny bez behu na 2019–21 smú raz B = 2019-05-05 – 2021-09-30 (2,4 r, 240 / 360) → ✅ pri ≥ 125 obch/rok.

## MYM — ako MNQ, s nočnou výhradou
- **Denné stratégie:** rovnaké dátumy a závery ako MNQ (M1, ≥ 105 obch/rok).
- **Nočné stratégie** (Noc + pondelok MYM a ďalšie): 2019 a 2024 sú pod 95 %, takže L by malo len 2020 – 9/2022 a B
  2022-10 – 2023-12 + 2025-01 – 2025-09. To je ~2 roky s dierou a 200 / 300 obchodov. **→ len 🟡.**
- **Dnešné:** `ibsentrymym`, `nocponmym`, `sigmamym` boli v triedení → len 🟡.

## MGC — 5,7 roka pred A (2020-01-01 – 2025-09-03)
| variant | L + WF | trezor B | obch. v B 100 / 150 |
|---|---|---|---|
| **G1 (najlepší kompromis)** | 2020-01-01 – 2022-12-31 · 3,0 r · WF 18/6 = 3 kúsky | 2023-01-01 – 2025-09-03 · 2,7 r | 270 / **400** |
| G2 | 2020-01-01 – 2023-09-30 · 3,75 r · WF 24/6 = 3 kúsky | 2023-10-01 – 2025-09-03 · 1,9 r | 190 / 285 |

- **Otvorene:** zlato pravidlo „≥ 2 roky a ≥ 300 obchodov a iný režim“ pri 100 obchodoch za rok **nesplní**. G1
  ho splní od ~112 obchodov za rok.
- **Režimy v G1:** L má covid, vrchol 2020 a pokles 2022 (−20 %). B je takmer celý jeden býk (+80 %), takže
  „pokles, ktorý v L nebol“ nesplní. Iný režim môže dať len vyššie ATR v roku 2025, treba ho zmerať.
- **Čo G1 stráca:**
  - len 3 WF kúsky, teda WF je slabý dôkaz,
  - trezor je jednosmerný trh, takže stratégia s longmi môže len zbierať rast (povinný test „kúp a drž“ z trend CFD
    smernice ostáva).
- **Nové:** ✅ je možné len pri ≥ 115 obchodoch za rok, ak sa iný režim potvrdí a ak stratégia porazí kúp a drž.
  Inak len 🟡 a dôkaz príde z C.
- **Dnešné:**
  - všetky MGC rodiny majú L 10/2021 – 9/2025, triedenie spálilo 2020–21, `mtkorb` ladila na 2010–24 a SPRÁVY
    videli 2010–21 → **len 🟡**,
  - rodiny mimo triedenia (`ibsentrymgc`, `scalp3mamgc`, `flashorbmgc`, `orb15mgc` je v triedení) majú voľných
    len 2020-01 – 2021-09 (1,75 r) → stále len 🟡.

## 6E — 9,7 roka pred A (2016-01-03 – 2025-09-03)
| oblasť | dátumy | roky | obch. 100 / 150 |
|---|---|---|---|
| L + WF 24/6 (~7 kúskov) | 2016-01-03 – 2021-09-30 | 5,75 | 575 / 860 |
| trezor B | 2021-10-01 – 2025-09-03 | 3,9 | 390 / 585 |
| A · C | 2025-09-04 – 2026-09-03 · od commitu | | |

- **Nové:** ✅ je možné. B má zvyšovanie sadzieb v roku 2022 a paritu EUR/USD, čo je jasne iný režim než nízka
  volatilita 2016–19.
- **Dnešné:**
  - EUR_KEYS majú L 2016–21 aj 2021–26 spálené → **len 🟡**,
  - `sdeur` a `m2eur` sa ladili predvolene (10/2021 – 9/2025) a v triedení neboli, takže **2016-01 – 2021-09
    (5,75 r) smú raz použiť ako trezor → ✅ je možné**,
  - `spravyeur` → 🟡, lebo kalendár pred 2021 obsahuje len ECB.

## BTC (Binance perp) — 6,0 roka pred A (2019-09-08 – 2025-09-03)
| variant | L + WF | trezor B | obch. v B 100 / 150 |
|---|---|---|---|
| **K1 (pri 100–150 obch/rok)** | 2019-09-08 – 2022-09-30 · 3,1 r · WF 18/6 = 3 kúsky | 2022-10-01 – 2025-09-03 · 2,9 r | 290 / 435 |
| K2 (pri ≥ 150, dohoda 11) | 2019-09-08 – 2023-09-03 · 4,0 r · WF 24/6 = 4 kúsky | 2023-09-04 – 2025-09-03 · 2,0 r | 200 / **300** |

- **Režimy:** K1 má v B pád FTX (11/2022) a býka po ETF 2024. K2 má v B len býka a apríl 2025, takže iný režim
  treba zmerať.
- **Nové:** K1 dáva ✅ pri ≥ 105 obchodoch za rok, K2 pri ≥ 150. Krypto stratégie 24/7 mávajú viac obchodov, preto
  K2, ak to hypotéza unesie.
- **Dnešné:**
  - `flashorbbtc`, `noabtc`, `rangebtc`, `sweepengulfbtc` boli v triedení → **len 🟡**,
  - BTC kópie mimo triedenia smú raz použiť B = 2019-09-08 – 2021-09-30 (2,1 r, 210 / 315) → ✅ pri ≥ 145 obch/rok.

---

## Súhrn
| trh | nové hypotézy | dnešné stratégie |
|---|---|---|
| ES | **✅** (L 7,3 r, B 4 r) | 🟡 rodiny z triedenia · **✅** `noaes`, `m2`, `flashorbes`, `nqpreces` (B 2010–21) |
| MNQ | ✅ pri ≥ 105 obch/rok (M1), WF slabší | 🟡 (✅ len pre rodiny bez behu na 2019–21, ≥ 125/rok) |
| MYM | denné ako MNQ, **nočné len 🟡** | 🟡 |
| MGC | ✅ len pri ≥ 115/rok, iný režim nutné zmerať, inak 🟡 | **🟡 všetky** |
| 6E | **✅** (L 5,75 r, B 3,9 r) | 🟡 EUR_KEYS · **✅** `sdeur`, `m2eur` (B 2016–21) |
| BTC | ✅ pri ≥ 105 (K1) alebo ≥ 150 (K2) | 🟡 (✅ BTC kópie mimo triedenia pri ≥ 145/rok) |

**Kompromisy a čo stoja:**
- Na MNQ, MYM, MGC a BTC sa ladenie skracuje na 3–3,4 roka a WF na 18/6 (3–4 kúsky). Trezor je jeden blok
  2,7–2,9 roka, takže dôkaz unesie len stratégia s vyšším PF alebo počtom obchodov.
- Kde trezor nestačí, ostáva **WF ako hlavný dôkaz + C ≥ 2 roky** a stav do vtedy 🟡.
- Dnešné stratégie z triedenia (všetky, ktoré dnes bežia naživo) nemajú v dátach, ktoré máme, **žiadny čistý
  trezor**. Najviac dostanú 🟡 a ✅ najskôr z C (12/2028).

---

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

---

# 14 — Inžinier B: 150 alebo 300 obchodov v trezore? (27. 11. 2026)

Výpočet: `obchody_sila.py` (presne cez binomické rozdelenie, výplata +W R / −1 R, WR 40–60 %; DD Monte Carlo 20 000 ciest).
Rozsah WR mení výsledky o ≤ 5 p. b., uvádzam WR 50 %.

## 1. Čísla
**Sila = P(t ≥ t_req), jednostranne** (k = 1 → 2,0; k = 20 → 3,0):

| skutočný PF | n 150 | 220 | 300 | 500 | E[t] pri 300 | p (jednostr.) pri 300 |
|---|---|---|---|---|---|---|
| 1,1 | 8 % / 1 % | 10 / 1 | 11 / 2 | 17 / 3 | 0,82 | 0,20 |
| 1,2 | 18 / 3 | 27 / 5 | 34 / 7 | 52 / 17 | 1,57 | 0,058 |
| 1,3 | 34 / 8 | 47 / 16 | 61 / 23 | 83 / 48 | 2,26 | 0,012 |
| 1,5 | 66 / 28 | 84 / 47 | 93 / 66 | 99 / 93 | 3,46 | 0,0003 |

- n na 80 % silu pri t_req 2,0: PF 1,2 → **~1 000**, PF 1,3 → ~480, PF 1,5 → ~200. Pri t_req 3,0: 1 800 / 860 / 370.
  Veta v 8b „pri PF 1,2 treba ~500 obchodov pre t = 2" platí len pre *očakávané* t (sila 50 %) — opraviť.
- **Bez edge (PF 1,0):** P(PF_trezor ≥ 1,2) = 14 % pri 150, 10 % pri 220, 6 % pri 300, 2 % pri 500.
  P(PF ≥ 1,1) = 28 / 23 / 19–22 / 15 %. **P(t ≥ 2,0) = 2,0–2,6 % pri každom n.**
- Pozorovaný PF, ktorý t_req vynúti sám (WR 50 %): n 150 → 1,39 (t 2,0) / 1,65 (t 3,0); n 210 → 1,32 / 1,52;
  n 300 → 1,26 / 1,42.
- Monte Carlo, skutočný PF 1,2: max DD medián / p95 = 10 / 20 R (n 150), 12 / 23 R (220), 13 / 25 R (300);
  90 % interval pozorovaného PF 0,92–1,57 (150) vs 1,00–1,45 (300). Pri PF 1,5: p95 DD 15–18 R.

## 2. Hodnotenie
1. **Pevné 300 nechráni pred falošným ✅ — to robí t.** Falošný poplach t ≥ t_req je ~α pri každom n; PF-brána 1,10
   pri 300 obchodoch pustí stratégiu bez edge v ~20 % prípadov. 300 je teda len druhá, slabšia kópia toho istého testu.
2. **Pri malom n t_req automaticky žiada vyšší PF.** Stratégia, ktorá prejde t 2,0 pri 210 obchodoch (PF ≥ 1,32),
   je rovnako významná ako tá pri 300 (PF ≥ 1,26). Pravidlo 300 ju aj tak zhodí na 🟡 → na MNQ/MYM/BTC/MGC
   pri 75 obch/rok (~210) **nie je ✅ dosiahnuteľné nikdy**, ani pri PF 1,6. To je strata sily, nie opatrnosť.
3. **Prečo nie len t bez minima:** t predpokladá ~nezávislé obchody a nie extrémne chvosty; pri n < 150 sa normálna
   aproximácia pri RR 2 a WR 40 % kazí, odhad PF má interval ±0,3 a jeden zhluk (FOMC týždeň) urobí polovicu t.
   Minimum 150 je ochrana pred malou vzorkou, nie test.
4. **Prop riziko:** DD z trezoru pri malom n podceňuje dlhodobý DD (p95 20–25 R za 150–300 obchodov, za dlhší beh viac).
   Veľkosť sa preto nesmie odvodiť z DD trezoru, ale z MC s **ohaircutovaným** PF. FTMO 10 % = 20 R pri 0,5 %/obchod —
   p95 DD pri PF 1,2 to už vyčerpá. Pravidlo: riziko/obchod ≤ 5 % / p95 DD_R (MC, PF po haircute, n = obchody za 1 rok × 2).
5. **150 ako jediné číslo nestačí na ✅:** pri n 150 je P(PF ≥ 1,2 | bez edge) 14 % a rozptyl PF veľký; preto pre ✅
   vyššie minimum (200), aby trh s 75 obch/rok × 2,8 r ✅ dosiahol, no len s PF ≳ 1,32 (k = 1) až ≳ 1,52 (k = 20).

## 3. Navrhované znenie
**Krok 8b (nahradiť riadky „Dĺžka trezoru" a „PF ≥ 1,10 …"):**
- Trezor ≥ 2 roky a aspoň jeden rok mimo režimu ladenia; kratší alebo jeden režim → najviac ⏳.
- **Obchody v trezore: < 150 → ⏳** (malá vzorka, t sa nehodnotí). Počet nie je brána významnosti, tou je len t.
- **🟡:** n ≥ 150, t ≥ t_req(k), PF ≥ 1,10 s nákladmi §3, ≥ 60 % rokov v pluse.
- **✅:** n ≥ 200, t ≥ t_req(k), PF ≥ 1,15, ≥ 60 % rokov v pluse a žiadny rok pod 0,90, plus veľkosť z MC:
  riziko/obchod ≤ 5 % / p95 max DD v R (PF po haircute §7). Bez MC → najviac 🟡.
- t = priemer R / σ · √n, **jednostranný** test (hľadáme len kladný edge); tabuľka t_req ostáva (2,0 → 3,3), čím je
  jednostranne prísnejšia, než α = 0,05 žiada (1,64) — rezerva na autokoreláciu obchodov.
- Veta „pri PF 1,2 ~500 obchodov" → „pri PF 1,2 treba ~1 000 obchodov na 80 % šancu prejsť t 2,0; pri 210 obchodoch
  t_req vyžaduje pozorovaný PF ≥ 1,32 (k = 1) až 1,52 (k = 20)."
**Krok 4 (výnimka pod 75/rok):** „t_req + 0,5 a ≥ 150 obchodov v trezoroch spolu (✅ ≥ 200)" namiesto 300.
**§1:** stĺpec „čo unesie" pre MNQ/MYM/BTC: „✅ pri ≥ 200 obchodoch v trezore a t ≥ t_req (pri 75/rok ~210 → PF ≳ 1,32)";
MGC (2,7 r): „✅ pri ≥ 75 obch/rok (≥ 200 v trezore) + iný režim + lepší než kúp a drž". Prepočet legacy prahov a C: „< 150 → ⏳", C „≥ 2 roky a ≥ 200".
**§9 bod 1:** „~210 obchodov stačí na 🟡 aj ✅, ak t ≥ t_req; ✅ vtedy znamená pozorovaný PF ≳ 1,32–1,52."

**NÁVRH:** Pevné 300 zrušiť — rozhoduje t ≥ t_req(k) jednostranne; minimum v trezore 150 obchodov (pod → ⏳) pre 🟡, 200 pre ✅ (+ PF ≥ 1,15 a veľkosť z MC p95 DD po haircute), takže ~210-obchodový trezor MNQ/MYM/BTC/MGC môže dať ✅, ale len pri pozorovanom PF ≳ 1,32 (k=1) až 1,52 (k=20).

---

# 15 — Prokurátor A: odpoveď na 14_B (150/200 namiesto 300) — 27. 11. 2026

## 1. Overenie
`obchody_sila.py` som spustil (`.venv/bin/python -I`): **všetky čísla v 14_B sedia** (sila, n na 80 %, PF pod nulou, MC DD, PF z t_req).
Model je však ideálny: ±R, iid, jedna kópia. Doplnková simulácia (40 000 ciest, nulová stratégia, P(t ≥ 2,0) / P(t ≥ 3,0); nominálne ~2,3 % / 0,13 %):

| porušenie modelu | n 150 | n 210 | n 300 |
|---|---|---|---|
| záporná šikmosť (WR 75 %, malý TP, 4 % gapov −3 R) | 3,9 / 0,65 % | 3,6 / 0,52 % | 3,4 / 0,38 % |
| kladná šikmosť (trend, WR 35 %, exp. výhry) | 1,2 / 0,02 % | 1,3 / 0,03 % | 1,4 / 0,03 % |
| zhluky (bloky 10 obchodov s posunom σ 0,25 R) | 5,4 / 0,80 % | 5,5 / 0,86 % | 5,3 / 0,80 % |
| 6 kópií na trhoch (ρ 0,6), každá k = 1, n 210 | rodina 9,8 % | (ρ 0: 12,8 %) | |

- **Autokorelácia** zdvojnásobí falošný poplach pri t 2,0 a pri t 3,0 ho zväčší ~6×, **pri každom n**. Rezerva „jednostranne s tabuľkou“ ju nepokryje. Pevné 300 ju tiež nerieši.
- **Skutočné rozdelenie R:** pri zápornej šikmosti (naše WR 70–100 %, RR 0,5) **n záleží**: chyba pri t 3,0 je 5× pri 150 a 3× pri 300. Tu je argument B „počet nie je brána“ chybný. Kladná šikmosť (trailing, EMAS) je naopak konzervatívna.
- **Kópie (…btc, …eur, …mgc, …mym):** t_req počíta k na trezor, nie na rodinu. Šesť trhov s k = 1 dá ~10–13 % falošných ✅. Veta kroku 4 „≥ 150 obchodov v trezoroch **spolu**“ dovoľuje sčítať MNQ+MYM+ES (ρ ~0,9), čo je pseudoreplikácia.
- **Prekliatie víťaza:** pri skutočnom PF 1,3 a n 210 prejde t 2,0 len 47 % ciest a ich medián PF je **1,43**. Pri t 3,0 prejde 12 % s mediánom **1,60**. MC veľkosť z pozorovaného PF teda nadhodnocuje edge o 0,13–0,30.
- **Tučné chvosty a DD:** MC 14_B je iid ±R. Zhluky a gapy predĺžia p95 DD. Denný limit FTMO 5 % (súbežné kópie v jeden deň) sa nekontroluje vôbec.
- Drobnosť: tabuľka t_req je Bonferroni **obojstranne** (k 20 → 3,02). Prechod na jednostranný test je v poriadku, ale nie je to „rezerva na autokoreláciu“.

## 2. Bod po bode
1. 300 nie je test významnosti, je ním t — **súhlas** (pri iid, ±R).
2. Malé n si samo vynúti vyšší PF — **súhlas**, ale len po korekcii t (bod 1 vyššie).
3. 150 ako ochrana malej vzorky — **súhlas** pre 🟡. Pre ✅ pri zápornej šikmosti **nesúhlas** (pozri tabuľku).
4. Veľkosť z MC p95 po haircute — **súhlas v princípe, nesúhlas s vykonaním**: iid MC a bez korekcie prekliatia víťaza.
5. ✅ od 200 — **podmienený súhlas** (doplnky nižšie).
6. Oprava vety „PF 1,2 ~500“ — **súhlas**.

## 3. Protinávrh (doplnky k znenia B)
- **t = min(t_obchody, t_mesiace)**, kde t_mesiace sa počíta z mesačného PnL trezoru (≥ 24 mesiacov), prípadne HAC Newey-West s lagom 5 obchodov. Tabuľka t_req ostáva.
- **Šikmosť R v trezore < −1** (malý TP, gapy): pre ✅ n ≥ 250 a t_req + 0,3; pre 🟡 platí 150.
- **Rodina kópií:** k = súčet hypotéz cez **všetky trhy rodiny** (≥ 6 kópií → k ≥ 5, t_req ≥ 2,6). Obchody sa **nesčítavajú** cez trhy s ρ mesačného PnL > 0,5; n je za trh.
- **Veľkosť:** PF_MC = 1 + (PF_obs − 1) / 2, kým n < 300 (inak haircut §7). MC ako **blokový bootstrap mesačných blokov** obchodov z trezoru, nie iid ±R. Riziko ≤ 5 % / p95 DD_R a zároveň p99 denná strata všetkých súbežných kópií ≤ 4 %.

**DOHODA:** Pevné 300 zrušiť; rozhoduje t ≥ t_req(k) jednostranne, kde **t = min(t z obchodov, t z mesačného PnL)** a **k sa počíta cez celú rodinu kópií na všetkých trhoch**. Obchody sa medzi trhmi s ρ > 0,5 nesčítavajú. Pod 150 obchodmi za trh je výsledok ⏳, 🟡 je od 150, ✅ od 200 (pri šikmosti R < −1 od 250 a t_req + 0,3) s PF ≥ 1,15. Veľkosť sa určí z blokového MC s PF_MC = 1 + (PF_obs − 1)/2 (n < 300) a s kontrolou dennej straty FTMO. Bez týchto doplnkov trvám na 300 pre ✅.

---

# 16 — Kontrolór C: nezávislá kontrola SMERNICA_V2 a práce A, B a koordinátora (27. 11. 2026)

*Len čítanie. Overené v `data/archive/tester/` (prvá a posledná sviečka po rokoch), `data_kvalita.json`, `data_noc_roly.json`,
`obchody_sila.py`, v kóde (`tester/`, `tradebot/`, `.nightsearch/`), v `tester/live/mirror.sqlite` a v iCloude (SP500-ES,
EUR-PRIESKUM, ZLATO-PRIESKUM, BTC-PRIESKUM, KLZAKY-STUDIA, OOS-STARE-ROKY, SPRAVY). Skripty: scratchpad `span.py`, `tmin.py`,
`req.py`, `mgc.py`. Riadky smernice = `SMERNICA_V2.md:N`.*

## Zásadné chyby

**Z1. Na MGC a 6E je ✅ nedosiahnuteľné, smernica pritom tvrdí opak.** Krok 8c (`:284–285`) má povinný negatívny test na
príbuznom trhu. Pre MGC je ním SI, pre 6E 6B. Ani jeden v archíve nie je, takže výsledok je ⏳, „nie preskočenie“ (aj ⛔ `:14`).
Napriek tomu `:16` a `:95` píšu, že 6E je „✅ bez kompromisu“ a má „plnú silu dôkazu“, a `:99` a `:438` tvrdia, že MGC „✅ prejde“.
Pre BTC 8c príbuzný trh vôbec nedefinuje, hoci ETH perp v archíve je (`binance/futures/ETH_USDT_USDT-1m-*`). **Oprava:** buď
napísať otvorene „MGC a 6E najviac 🟡, kým sa nestiahne SI / 6B“, alebo pri chýbajúcom príbuznom trhu povoliť ✅ bez 8c
s t_req + 0,3. Pre BTC doplniť ETH perp.

**Z2. Trezory MNQ, MYM, BTC a 6E ležia v období, na ktorom sa ladilo všetko.** Trezor 2022-10-01 – 2025-09-03 (`:96–98`)
sú presne tri z piatich `REFERENCE_WINDOWS` (`tester/hyperopt.py:56–58`). Na nich beží predvolené ladenie
(`glsearch` 2021-10 – 2025-09, `12_B:17`) aj ~1,8 mil. pokusov. Trezor 6E 10/2021 – 9/2025 sú štyri z tých piatich okien
a k tomu OOS EUR kópií (`SMERNICA_EUR.md:15–16`). Krok 8b definuje k ako „hypotézy, ktoré sa **kedy** pozreli na trezor“ (`:270`).
Pri doslovnom čítaní je dnes na MNQ k ≫ 50 (v `tradebot/strategies` je ~160 kľúčov), teda t_req ≥ 3,3. Pri 210 obchodoch to
vyžaduje pozorovaný PF ≥ 1,59 a pri skutočnom PF 1,5 vyjde sila 37 % (`req.py`). Ak sa naopak k počíta až od V2, trezor je
čistý len na papieri. `vaults.json` neexistuje a smernica nepovie, akým k začína. **Oprava:** zapísať počiatočné k pre
každý trezor z histórie (legacy rodiny, ktoré bežali na danom období, plus štúdie). Číslo „PF ≳ 1,32“ v `:96`, `:279` a `:438`
nahradiť hodnotou pre skutočné počiatočné k.

**Z3. `checkup` „zachovaný bez zmeny“ otvára trezory pri každej stratégii.** `:33` a `:431` checkup zachovávajú a krok 7 ho
používa na break-even (`:247`). `tester/checkup.py:46` však počíta na `REFERENCE_WINDOWS` 2021-10 – 2026-09, teda na celom
trezore MNQ, MYM, BTC a 6E a na časti trezoru MGC (10/2021 – 12/2022). CLAUDE.md navyše žiada checkup pri každej novej stratégii
(„hotová až so základnou analytikou“). §10 (`:460`) z checkupu vyraďuje len rok A. **Oprava:** checkup v V2 púšťať len na L
(prípadne WF OOS). Trezor smie počítať jedine príkaz `--vault`. Zmenu zapísať aj do CLAUDE.md.

**Z4. Legacy cesta cez C je mŕtva vo vlastnom znení smernice.** Krok 10.1 (`:298`) vyžaduje krok 7, teda DSR ≥ 0,95 pri N_eff
a ≥ 0,50 pri surovom N, a „neprejde DSR → ❌“ (`:251`). Podľa B dnes 0,95 nesplní žiadna stratégia (najvyššia 0,93, TKS 0,79,
NOA 0,33; `02_B:68`, `:90`), a to ešte pri N oveľa menšom, ako aké predpisuje V2 (tisíce až 82 000). Tabuľka stavov (`:420`, `:426`)
však legacy dáva „⚠, krok 10, najviac 🟡, dôkaz z C“. **Oprava:** pri legacy brať DSR len ako informáciu a nechať rozhodnúť
C, alebo napísať, že legacy = ❌ a C beží len ako výskum exekúcie.

**Z5. Rozpočet 300 zabíja každú hypotézu zo štúdie, smernica jej pritom sľubuje 🟡.** §2 (`:161–162`) počíta do rozpočtu
aj behy štúdií, „vyčerpaný = koniec“. KLZAKY-STUDIA má ~500 000 nastavení (`STUDIA.md`), z nej vzišla MTK EMAS. V §1 (`:89`) a v §7
(`:425`) majú takéto hypotézy „najviac 🟡 / ⏳ C“. **Oprava:** určiť, koľko sa za štúdiu odpočíta (napr. N = počet pravidiel
vybraných zo štúdie, nie počet behov štúdie), alebo priznať, že hypotézy zo štúdií sú ❌.

**Z6. Ukážkový „trezor B v praxi“ (SPRÁVY MGC, `:144–148`, `:416`) stojí na dátach, ktoré §1 sám zakazuje.** Ide o rovnaký
typ chyby, ako bolo NQ/YM/GC. MGC 2010–2019 má pokrytie jadra 8–39 % (2016–18 64–77 %, `data_kvalita.json`) a §1 ho vylučuje
(`:126`). Čisté sú z toho len okná 2019/20 a 2020/21 so 107–143 obchodmi, čo je pod 150 → podľa 8b ⏳, nie ❌. Kalendár ForexFactory
má na ISM zhodu ~90 % (`07:5`), hoci §1 (`:141–142`) žiada ≥ 95 % na každý typ. Okrem toho behy 1/2020 – 9/2021 otvorili nový
trezor MGC 2020–22. **Oprava:** SPRÁVY legacy dať ❌ z dôvodov, ktoré obstoja: > 5 parametrov, DSR a strata v okne 2020/21.
Príklad prepísať a do k trezoru MGC pripočítať SPRÁVY aj 11 MGC rodín z triedenia (`PRAVIDLA_TRIEDENIA.md:4`: MGC 1/2020 – 9/2021).

**Z7. Zamietnutie ES trezoru 2010–14 koordinátorom bolo zdôvodnené nepravdivo.** `VYCUC.md:179` uvádza „kratšie ladenie
a staré roky ES už videla rodina“. Pri ES však A navrhol ladenie **dlhšie**: 10,7 roka (2015-01 – 2025-09) proti 7,3 roka vo V2 (`13_A:44–45`).
Triedenie bežalo na ES 7/2010 – 9/2021 (`PRAVIDLA_TRIEDENIA.md:4`), teda zasiahlo obe obdobia rovnako. Trezor V2 10/2017 – 9/2021
leží v kontrole SP500-ES (US500 2015–2020, `SP500-ES/PRECITAJ_MA.md:50`, `:61`, `:85`) aj v KLZAKY (ES od 2016). ES je pritom jediný trh,
kde je ✅ reálne (Z1, Z2). Okrem toho V2 na ES nechá 2021-10 – 2025-09 (3,9 roka) **bez úlohy**: nie je to L, B ani A (`:94`).
Pri 6E je zamietnutie obhájiteľné (L by sa skrátilo z 5,75 na 3,9 roka, EUR kópie videli obe polovice), ale trezor V2 je pre
hypotézy z EUR-PRIESKUM (charakter 2021–2026) spálený. **Oprava:** ES vrátiť používateľovi na rozhodnutie s pravdivým porovnaním
a určiť, na čo slúži ES 2021–25 (napr. 8c pre MNQ a MYM).

**Z8. Živé riziko trvá.** Podľa `mirror.sqlite` (last_seen 27. 11., ~09:07 UTC) beží na `531513073-FTMO-Server3`
`spravynet profil_3` (XAUUSD, posledný fill 25. 11.), `tksnet TKS_1` (fill 26. 11.), `ibsentrynet IBS_EZ_11` a `noanet NOA_1`. Podľa V2 sú
prvé tri ❌ a NOA ⚠. Stop účtu v EA (krok 14) neexistuje a NFP je 4. 12. Toto rozhoduje používateľ, ale smernica pri nich stav
nemá ako „beží naživo proti V2“.

**Z9. Ranné nahrávanie zajtra prepíše webapp podľa OOS napriek pauze.** `glmorning.sh` nastaví TESTS=1, keď je stavový
súbor novší ako `.last_morning`. `hub_state.json` má 27. 11. 09:48, `.last_morning` 07:29, takže 28. 11. o 6:00 pobeží
`glsmernice --apply` aj `glwebvyber --apply` (`glmorning.sh:14`, `:29–30`) a výsledok sa pushne. P6 nie je vykonané. **Oprava
(rozhoduje používateľ):** vypnúť krok `--apply` alebo `sk.tradebot.morning`.

**Z10. V2 sa s dnešným kódom zaviesť nedá. Mimo §10 navyše chýba:** `--fill`/fill v2, `register/`, `vaults.json`,
`tester/walkforward.py` a `tester/pbo.py` neexistujú (grep). `skipRoll` je len v `nocpon` a vo všetkých profiloch je `false`,
hoci V2 ho chce „predvolene zapnutý pre každú stratégiu“ (`:137`). `rolls.json` obsahuje dátum a kontrakt, nie skok (`:134`).
§10 nemá položky pre ratio back-adjust indikátorov v Pythone aj C# (s paritou), pre počiatočné k (Z2), pre meranie „iného režimu“
ani pre kontrolu kalendára. Odhad 5–7 týždňov je preto nízky.

## Menšie nedostatky
- **t_req (`:271`):** veta „jednostranný, α = 0,05“ je nesprávna. Tabuľka 2,0/2,6/2,8/3,0/3,3 je Bonferroni pri jednostrannom
  α = 0,025, pri jednostrannom α 0,05 by vyšlo 1,64/2,33/2,58/2,81/3,09. A to napísal správne (`15_A:19`), koordinátor to zapísal zle.
- **Dve definície k:** pre rodinu platí „≥ 6 kópií → k ≥ 5“, pre trezor kumulatívne cez `vaults.json` (`:267`, `:270`). Ako sa
  skladajú (súčet alebo maximum), smernica nehovorí. „≥ 6 kópií → k ≥ 5“ nie je Bonferroni (to by bolo k = 6).
- **Počítanie obchodov:** „≥ 150 na trh“ a zároveň „trhy s ρ > 0,5 sa nesčítavajú“ (`:216–217`, `:261`) si odporujú. Ak je n za trh,
  nesčítava sa nič. Netreba ani ρ medzi MNQ a ES, ktorých trezory ležia v rôznych rokoch.
- **WF 24/6 v kroku 6 (`:228`) proti 18/6 v §1:** na MGC (32 mesiacov) zostanú 2 kúsky, takže „≥ 75 % v pluse“ = oba.
  Čiastočné roky L (ES 2010 7 mesiacov, MGC 2025 8 mesiacov) nemajú pravidlo pre „≥ 75 v každom roku“.
- **„Iný režim“:** 8b hovorí o roku (`:258`), §1 o štvrťroku s ATR mimo IQR (`:113`).
- **Zvyšky B′:** ⛔ `:13`, §6 `--vault B'|C`, 8b „B alebo B′“ a krok 10 odkazujú na trezor 6E B′ 2010–15. Ten v §1 už nie je, takže čistenie
  6E (`:127–131`) nemá v smernici účel.
- **T4 (`:405`):** obdobie 10/2021 – 9/2026 nazýva „rok A pre 6E“, hoci 10/2021 – 9/2025 je trezor 6E. Beh tak zvýši k trezoru.
- **Tabuľka štúdií (`:82–87`):** BTC-PRIESKUM nepoužil len Dukascopy. Bral aj Binance perp 2019-09 – 2026-09 (`PRECITAJ_MA.md:3`, `:24–25`),
  teda trezor BTC videl. ZLATO-PRIESKUM videl MGC 2011–2025, nie 2020–9/2026. KLZAKY začína ES a MGC od 2016.
- **Pripisovanie:** `:73` a `:75` píšu „dohoda A + B, 27. 11.“, ale B na `13_A` nikdy neodpovedal (KONVERZACIA nemá kolo B po 13).
  Obrátenie MGC je návrh A a koordinátora. B v `12_B` navrhol opak (G1).
- **Z dohody 14_B/15_A vypadlo:** „bez MC → najviac 🟡“, „t_mesiace ≥ 24 mesiacov / HAC“ a „MC n = obchody za rok × 2“.
- **Detektor rolovania** (`dq_night_rolls.py:23–26`) hlási „tam a späť“ pri každom rolovaní ES, 6E a MGC od 2020 (27/27/34 záznamov),
  lebo jednociferný rok v kóde kontraktu sa po 10 rokoch opakuje. Záver „len MGC 1/2011“ (`:140`) je správny, ale JSON ho nepodporuje.
  Ako automatická kontrola by to nefungovalo.
- **Náklad MNQ a MYM 1,5 ticku** je pod tým, čo agenti sami namerali (~1,7–1,8 ticku; `03_B`, `04_A`).
- **P5 nie je splnené:** `git status` ukazuje necommitnuté zmeny `PRESIEL_SMERNICAMI_*` profilov (fibomgcnet, nyvaesnet, ibsentryesnet).

## Čo je v poriadku
- Dátumy v §1 sedia so súbormi: ES 2010-06-06, MNQ 2019-05-05, MYM 2019-06-02, BTC 2019-09-08, 6E 2016-01-03, MGC 2020+.
  Koniec archívu: ES 19. 10., MNQ a MYM 9. 11., 6E 28. 9., MGC 16. 9., BTC 4. 9. Pokrytie a nočné okná sedia s JSON (MYM noc 2019 86,5 %, 2024 94,8 %).
- Obrátenie MGC je z hľadiska režimu správne: trezor 2020–22 má max DD −21,6 % (vrchol 6. 8. 2020), L 2023 – 9/2025 rastie o +97 % pri DD −10,9 % (`mgc.py`).
- Výpočty v `obchody_sila.py` sú správne (sila, n pre 80 %, PF z t_req). Pravidlo t = min(t obchodov, t mesiacov) stojí pri iid
  len ~3–5 p. b. sily, falošný poplach nezvyšuje (pri 35 mesiacoch 1,8–1,9 % pri t 2,0; `tmin.py`), a to je rozumná cena. Mesačné t pri
  35 bodoch kryje zhluky nad 1 mesiac, nie kratšie. Zrušenie pevných 300 je odôvodnené.
- Jedno rozdelenie na trh, trezor mimo štúdií, stop účtu lokálne v EA a „✅ len skriptom, podpis používateľa“ sú správne.

## Verdikt
- **A (Prokurátor):** najlepšia práca v debate. Odhalil štúdie, kópie, šikmosť a prekliatie víťaza a správne opravil Bonferroniho.
  Slabiny: v `13_A` neoveril obdobie BTC-PRIESKUM („nedokázal priradiť“) a nevidel, že checkup a referenčné okná otvárajú trezory (Z2, Z3).
- **B (Inžinier):** výpočty a merania sú solídne a priznal, kde sa A mýlil. Slabiny: navrhol trezory MNQ, MYM a BTC presne na oknách
  predvoleného ladenia a „✅ je možné“ ponúkol bez počiatočného k. Na `13_A` neodpovedal a s 8c vedome nechal 6E a MGC bez ✅.
- **Koordinátor:** zapísal dohody väčšinou verne, ale (1) prepustil Z1, Z4 a Z5, teda rozpory medzi krokmi, ktoré si všimne každý,
  kto smernicu číta celú, (2) ES zamietol s nepravdivým dôvodom (Z7), (3) ako ukážku dal MGC 2010–21, teda tú istú triedu chyby
  ako NQ/YM/GC (Z6), (4) pripísal B dohodu, ktorú B neurobil, a zle zapísal α. Smernica v dnešnom znení nie je pripravená na podpis.

## Na rozhodnutie používateľa
1. Server3: spravynet profil_3, TKS_1 a IBS_EZ_11 sú podľa V2 ❌ a bežia, NOA_1 je ⚠. Do NFP 4. 12. vypnúť alebo vedome nechať (Z8).
2. Zastaviť zajtrajšie `--apply` v rannom nahrávaní (Z9).
3. ES trezor: V2 (10/2017 – 9/2021, spálený štúdiami S&P) alebo 2010-06 – 2014-12 s ladením 2015 – 9/2025 (Z7).
4. MGC a 6E: stiahnuť SI a 6B, alebo prijať „najviac 🟡“ (Z1).
5. Či sa počiatočné k trezoru ráta z celej histórie (prísne, ✅ takmer nedosiahnuteľné), alebo až od V2 (Z2).
6. Rozpor s vašimi pravidlami, ktorý V2 nespomína: povinné „market/limit + IBS + pin bar“ zaberie 2 z 5 voľných parametrov
   a „vždy aj posledný rok“ (tabuľky) sa bije s §5 (bez „posl. rok PF“).

---

# 17 — Kontrolór C: kontrola opráv SMERNICA_V2 po `16_C` (27. 11. 2026)

*Len čítanie. Porovnané s `SMERNICA_V2.bak3.md` (diff), riadky = `SMERNICA_V2.md:N`. Rozhodnutia používateľa: ES trezor 2010–14,
prísne počiatočné k, MGC a 6E najviac 🟡.*

## Opravené
- **Z1** `:15`, `:17`, `:99`, `:103`, `:299–300`: MGC a 6E najviac 🟡, BTC ↔ ETH perp doplnené. **Z2** `:105–107`, `:100`, `:102`, `:294`, §9.6.
- **Z3** `:14`, `:35`, `:259`, `:397`, `:447`, `:482`: checkup len na L. **Z6** `:152–157`: už nie je príklad trezoru, dôvody sú prepísané.
- **Z7** `:98`, `:115`, `:454`: ES trezor 2010–14. ES 2021–25 má teraz úlohu (je v L). **Z8** `:432`, `:457`. **Z9** `:412`. **Z10** `:483–485`, `:492`.
- Menšie: α `:286`, jedno k `:280–281`, obchody na trh `:228`, `:273`, WF 18/6 `:240`, `:245`, iný režim `:270`, B′ preč, T4 `:420`,
  štúdie `:87–91`, pripisovanie `:75`, `:77`, `:103`, MC/HAC `:279`, `:284`, detektor `:147–148`, náklad 1,75 `:194`, P5 `:411`.
- **ES L 2015–2025 s referenčnými oknami a štúdiami je v poriadku.** L je obdobie, ktoré sa smie vidieť, a podmienka platí len pre trezor.
  ES 2010–14 videlo len triedenie (ORB 15/5, NY VA, IBS EZ ES, IVB, Williams R, MTK EMAS ES; ~10 profilov). Počiatočné k je teda ~10,
  t_req ~2,8 a pri ~460 obchodoch stačí PF ≳ 1,3. Tvrdenie „✅ reálne len na ES“ obstojí.

## Zle alebo chýba
**Blokujúce (rozpory medzi krokmi):**
1. `:313` krok 10.1 „PF ≥ 1,15 na 5 oknách“: piate okno 20250904–20260904 je rok A (`:73`, `:384`). Okná 2022–25 sú trezory MNQ, MYM a BTC,
   2021–25 trezor 6E a 10/2021–12/2022 časť trezoru MGC. Bije sa to s `:222` (krok 3 na L), `:35` a `:397` (len L). Cez `:314` tou istou
   cestou idú aj **nové** hypotézy zo štúdií, takže tie otvoria trezory s plnou váhou k. Oprava: krok 3 aj pri legacy na L trhu, bez roka A.
2. Z4 a Z5 sú opravené len čiastočne. `:263` vyníma iba DSR. Haircut (`:258`, N = N_eff ≥ N/50, teda pri 82 000 alebo 500 000 behoch
   tisíce) a PBO (`:257` chce mesačný PnL všetkých konfigurácií, legacy ho v registri nemá) ostávajú bránami → legacy aj štúdie skončia ❌.
   Oprava: pri kroku 10 brať DSR, PBO aj haircut ako informáciu a rozhodnutie nechať na C. Haircut ponechať len na veľkosť.
3. `:431` SPRÁVY ❌ sa opiera o „DSR neprejde“, hoci `:263` to robí len informáciou. Ďalší dôvod, „strata v okne 2020/21“, má 107–143 obchodov,
   čo je podľa `:154` a `:274` len ⏳. Pravidlo „> 5 parametrov“ pre legacy nikde neplatí (`:181–184`, krok 10).
   Treba napísať pravidlo, podľa ktorého sú ❌ (napr. legacy > 5 parametrov → ❌), alebo im dať ⚠ / ⏳.
   `:455` (§9.2) stále píše „❌ (trezor B)“, čo je zvyšok Z6.

**Menšie:**
4. `:432` dáva IBS_EZ_11 (ibsentrynet = MNQ) ❌, ale `:439` má „IBS EZ MNQ/MYM ⚠ do T1“. Chýba dôvod: ladenie na živom období podľa `:56`.
   `:408` (P3) nemá SPRÁVY profil 3, hoci `:457` ho má.
5. `:100`, `:107`, `:463`: pri k ≫ 50 platí t_req 3,3 len ako dolná hranica. Tabuľka `:288–290` končí pri k = 50.
   Pri k ≈ 160 (počet kľúčov) je t_req ≈ 3,6 a pri 210 obchodoch to znamená PF ≳ 1,65. Doplniť stĺpce k 100 / 200 (3,5 / 3,7).
6. `:285` znovu definuje k ako „počet hypotéz“ bez kópií, kým `:280` kópie zahŕňa. Jednu z definícií zrušiť.
   `:106` nehovorí, či sa štúdia s 500 000 nastaveniami počíta ako 1.
7. `:229`: v zátvorke „ES 2015 nie“ chýba, že aj ES 2025 (do 3. 9.) je neúplný rok. Neúplné sú aj roky na okrajoch L
   pri MNQ, MYM, BTC a 6E (2019, 2021, 2022). Pravidlo treba napísať všeobecne a určiť, či „rok“ znamená kalendárny rok, alebo okno 10–9.
8. `:98` vs `:120`: iný režim ES trezoru nie je zmeraný. Kritérium poklesu nevyjde, lebo L má covid (−35 %) aj rok 2022 (−25 %).
   Ostáva ATR (2011). Treba ho zmerať a zapísať, inak podľa `:271` platí najviac ⏳.
9. `:299` 8c neurčuje obdobie na príbuznom trhu. Pre MNQ a MYM je prirodzené ES 2022–25 (to je L ES). Pre ES hypotézu by MNQ 2022–25
   otvorilo trezor MNQ (+k). Treba to napísať.
10. `:421` T4b nemá výsledok pre PF 1,00–1,03. Pri prechode dá ⚠, teda ten istý stav ako dnes (`:438`), takže test vie len zamietnuť. Treba to povedať.
11. `:115` schéma ES pre NQ/YM/GC: GC 2011–14 videl ZLATO-PRIESKUM (`:87`) a NQ článok NOA (SPY 2007–24). Treba doplniť „+ počiatočné k“.
12. §10 `:490`: riadok CLAUDE.md nemá zmenu „checkup len na L“ (Z3). Poradie `:493–499` nemá nové riadky (počiatočné k,
    checkup na L, back-adjust). Počiatočné k musí byť hotové pred T4, ktorý k trezoru 6E zvyšuje. Súčet tabuľky je ~28–34 dní,
    čo je ~6–7 týždňov, nie 7–9. Ako rezerva to obstojí, len to treba napísať.
13. `:412` P6: blok platí len dovtedy, kým `hub_state.json` (9:48) ani iný stav nie je novší než `.last_morning` (27. 11. 10:17).
    Ktorýkoľvek beh hubu dnes ho zruší a 28. 11. o 6:00 znovu pobeží `--apply`. `:7` má stále „stav 26. 11.“

## Verdikt
**Pripravená na podpis: nie, zatiaľ nie.** Z1–Z3 a Z6–Z10 sú opravené vecne správne. Zostávajú tri rozpory medzi krokmi (body 1–3):
krok 10 na 5 oknách otvára trezory a rok A, haircut a PBO stále zabíjajú legacy aj štúdie a dôvod ❌ pri SPRÁVACH je v rozpore s vlastným textom.
Po ich oprave a jednom prechode bodov 4–13, ktorý trvá zhruba hodinu práce bez nových meraní, áno.

---

# 18 — Kontrolór C: podpisová kontrola SMERNICA_V2 po `17_C` (27. 11. 2026)

*Len čítanie. Diff proti `SMERNICA_V2.bak4.md` (`fix17.py`, 0 MISS). Riadky = `SMERNICA_V2.md:N`. Smernica prečítaná celá.*

## Vyriešené
- **B1** `:317`: krok 3 pri legacy beží na L trhu, bez roka A. Trezory a rok A sa cez krok 10 už neotvárajú. **B2** `:266–267`: DSR, PBO aj haircut sú pri kroku 10 len informácia.
  **B3** `:435`, `:436`, `:459`: SPRÁVY sú ⚠ legacy s negatívnym signálom. Okno so 107–143 obchodmi je správne vedené ako ⏳.
- **4** `:412`, `:436`, `:443` · **5** `:292–294`, `:298`, `:100`, `:102`, `:467`. Bonferroni sedí: k = 100 dáva 3,48, k = 160 dáva 3,61.
  **6** `:107–108`, `:284`, `:290` · **7** `:231–232`, roky sedia s §1 · **8** `:98` · **9** `:303` · **10** `:425` · **11** `:116–117`.
  **12** `:494`, `:496` (súčet je 27,5–33,5 dňa), `:499` · **13** `:416`, `:7`. Overené na disku: `gl_paused` existuje, `.last_morning` je z 10:17 a novší stavový súbor nie je.
- Pre ES k ≈ 10 (`:98`, `:107`) nič neprotirečí. Na 2010–14 nebežala žiadna štúdia, KLZAKY začína ES až 2016 a SP500-ES 2019.

## Zvyšky
**Rozpory medzi krokmi (opraviť pred podpisom, každý je na jeden riadok):**
1. `:159` stále píše „Legacy SPRÁVY sú ❌ … > 5 parametrov, DSR so skutočným N“. Bije sa to s `:435` a `:459` a pravidlo „> 5 parametrov“ pre legacy neexistuje. Ide o zvyšok B3.
2. `:18` uvádza pre MNQ, MYM a BTC „t_req ≈ 3,3 (PF ≳ 1,6)“, kým `:100`, `:107` a `:467` majú k ≈ 160, t_req ≈ 3,6 a PF ≳ 1,65. Chýba aj 6E.
3. `:424` T4: Williams R 6E na 10/2021–9/2026 je označený „nie trezor“. To obdobie je však celý trezor 6E (`:99`, 2021-10 – 2025-09) plus rok A, čo je v rozpore s krokom 10.1 (`:317`, „na L, bez roka A“). Rovnaký problém ako B1.
   Oprava: T4 pustiť na L 6E 2016-01 – 2021-09. Ak má ostať obdobie 2021–26, treba ho výslovne vyňať z 10.1 a zapísať k + 1 do `vaults.json` (to tam už je).

**Menšie (výsledok nemenia):**
4. `:175`: zátvorka „DSR len informácia“. Podľa `:266` majú byť len informáciou DSR, PBO aj haircut.
5. `:428` T6 (MNQ 6/2024 – 9/2026): beží na trezore MNQ a v roku A s t ≥ 2,0, nie s t_req 3,6. Výnimku „po publikácii“ (`:323`) treba nazvať výnimkou z 8a a 8b a zapísať k + 1 trezoru MNQ.
6. `:107`: číslo ~160 je počet všetkých kľúčov (163 adresárov), teda prísny horný odhad. Trezor sa počíta na trh (`:277`), takže `vaults.json` dá na každom trhu menej. Stačí slovo „najviac“.
7. `:5`: „Podklady 01–16“ treba zmeniť na 01–18. `:431`: „k 26. 11.“ treba zmeniť na 27. 11.

## Verdikt
**Pripravená na podpis používateľom: nie, zatiaľ nie.** Ostávajú tri jednoriadkové rozpory (body 1–3) a nové meranie nepotrebujú.
Body 1 a 3 sú zvyšky B3 a B1. Po ich oprave **áno**. Body 4–7 sa dajú opraviť v tom istom prechode a podpis nebrzdia.

---

# 19 B — Fill a sklz na CFD (FTMO, MT5): čo je namerané a čo navrhujem

## Blokéry (čo chýba)
1. **Bid/ask a spread sa nezapisuje, overené.** EA posiela m1 len ako OHLCV (`TradeBotEA.mqh` ~1042, `MqlRates.spread` sa zahodí).
   Fill obsahuje len `price, qty, ft`. Spread sa dá preto len **odvodiť** z buy fillov proti bid sviečke.
2. **Obchodujeme len US100.cash, US500.cash a XAUUSD** (zrkadlo: 18 MT5 inštancií, účty FTMO-Demo a FTMO-Server3).
   **EURUSD** je len stará skúška `ibsnet` s MNQ profilom (0 fillov). **US30 a BTCUSD** nemajú ani inštanciu. Pre tieto
   tri symboly je všetko nižšie **odhad**.
3. Vzorky sú malé. US100 má 90 obchodov a 184 fillov, US500 8 obchodov, XAUUSD 8 obchodov.
   **V okne správ ±5 min nie je ani jeden MT5 fill.** Pri otvorení NY (9:30–9:40) sú 2.
4. Živé ordery nemali ani jeden **stop vstup** (len Limit a Market), takže sklz stop vstupu nie je zmeraný.
5. `DEAL_TIME` má presnosť 1 s, takže oneskorenie po odoslanie sa nedá zmerať pod 1 s. Jeden fill má čas
   posunutý o presne 3 h (10 799 920 ms). To vyzerá na nekonvertovaný čas servera v `ToMs`, treba to dohľadať.
6. Zmluvné parametre FTMO (spread a provízia podľa symbolu) nie sú v repe. Na webe som ich neoveril.

## 1. Merania (skripty `cfd_fill.py`, `cfd_fill_bars.py`, `cfd_tp_touch.py`, výstup `cfd_fill_out.txt`)
- **m1 brokera je bid.** Všetky sell fills (100 zo 100) ležia v rozpätí bid sviečky svojej minúty. Buy fills
  sú nad high v 7 zo 100 prípadov. Dukascopy je tiež bid (docs/DATA.md). Ask preto nemáme v žiadnych dátach.
- **Spread US100 ≈ 1,5 bodu.** Market buy fill v prvých 3 s minúty − bid open: medián 1,45 b (n=25, p75 2,45).
  Kontrola na sell filloch: −0,11 b (n=32). Market vstup proti signálu: long +1,85 b (n=17), short +0,20 b (n=21).
  Rozdiel ≈ 1,65 b. Hranice: 2× bol short SL vyplnený, hoci bid bol 1,64 a 0,38 b pod SL (SL sa spúšťa na ask).
  2× sa bid dostal 0,25 a 0,65 b pod short TP a fill neprišiel.
- **Prechod cez limit.** Buy limit sa vyplnil, až keď bid klesol aspoň 2,00 b pod limit (n=23, medián 7,1).
  Sell limit stačilo 0,31 b (n=24). Na správnej strane (bid pre predaj, ask pre nákup) teda stačí **dotyk**.
  Neprepadol žiadny limit, ktorého sa správna strana dotkla. 3 „dotknuté nevyplnené“ (US100 114 b, US500 8–13 b)
  sú ordery, ktoré u brokera zjavne neboli.
- **Limit a TP u FTMO nie sú pevná cena** (pri spustení idú trhom). Limit vstup: medián −0,18 b long a −0,59 b short
  (lepšie), p90 +0,75 / +0,25 b (horšie). TP: medián −0,75 / −0,48 b (lepšie), p90 +2,2 / +0,7 b.
- **SL US100:** long medián 0,65 b, p75 1,9 b (n=16). Short 1,22 b proti úrovni (n=18, jeden gap 59,5 b).
  US500: SL short 0,2–0,4 b (n=2), long 0 (n=2). XAUUSD: SL long medián 0,20 $ (n=5).
- **XAUUSD spread 0,10–0,40 $.** Buy − open 0,35 $ (n=2), sell −0,09 $ (n=3). Buy limit sa však vyplnil už pri
  prieniku bidu 0,10 $ (n=5), takže spread sa mení podľa hodiny. **US500:** spread ≥ 0,20 b (short SL pod bidom)
  a ≤ 1,20 b (buy limit, n=3).
- **Oneskorenie:** zavretie baru → order 0,11 s (medián, p90 0,25 s, n=43). Fill príde v tej istej sekunde.
- Mimochodom NT (MNQ, demo fill engine, nie burza): SL sklz **medián 2 ticky, p75 5** (n=12). V2 §3 počíta
  +1 tick, takže MNQ podceňuje. Limit a TP vychádzajú presne (sim).

## 2. Literatúra (neoverené pre FTMO)
Vyhľadávanie nenašlo čísla FTMO. Iní brokeri uvádzajú US500 ~0,35 b, zlato 0,17–0,39 $, EURUSD 0,1 pipu raw
alebo ~1 pip štandard, FX províziu ~3,5 $/lot/stranu a indexy bez provízie (gomarkets.com, pepperstone.com,
icmarkets.com). **Pri správach a pri otvorení NY sa spread CFD bežne zväčší 3–10×.** To je skúsenosť, nie meranie.
FTMO má zmluvný spread v MT5 („Specification“), treba ho odpísať.

## 3. Model pre backtest na CFD (graf = bid)
Prechod cez úroveň určujem **podľa strany v bodoch spreadu**, nie v tickoch a nie v % ATR:
- CFD nemá frontu na úrovni, takže „1 tick prechodu“ z futures tu nemá zmysel. Tick 0,01 je aj tak šum.
- Rozdiel medzi bidom a skutočnou cenou plnenia je presne spread (namerané: buy potrebuje ~S, sell 0).
- ATR rastie s volatilitou, ale spread nie, a v správach je to práve naopak.
Pravidlá:
- **Úrovne na strane predaja** (short limit, long TP, long SL) sa spúšťajú, keď bid dosiahne úroveň.
- **Úrovne na strane nákupu** (long limit, short TP, short SL, buy stop) sa spúšťajú, keď bid dosiahne úroveň − S.
- Market buy = bid + S + sklz, market sell = bid − sklz.
**Prepočet po zavedení logu:** S = p75 (ask − bid) v čase vstupov, zvlášť normal / NY open / správy.
Sklz = medián (fill − (bid alebo ask v čase spustenia)). Ak sa SL alebo market posunie o viac ako 1 S, prepočítať kroky 3–11.

## 4. Dopad (odhad)
Dnešné CFD čísla sa počítajú z futures alebo Dukascopy bidu bez ask korekcie. To zvýhodňuje backtest:
- long limity a short TP sa plnia skôr, ako by sa naozaj plnili,
- short SL sa spúšťa neskôr.
- **IBS EZ US100** (limit, RR 0,5, SL 50–93 b): S + sklz ≈ 0,02–0,03 R na obchod. K tomu ubudnú longy, ktoré sa
  limitu len dotkli (zväčša víťazi). **Odhad PF 1,5 → 1,25–1,35.** Pri stratégiách s RR 0,5 na indexe je to najväčšie riziko.
- **VWAP ORB US100** (market, SL 110–200 b): ≈ 2,5 b na obchod = 0,015 R. **Odhad PF −0,05 až −0,08.**

## NÁVRH (bod = 1,0 indexu / 1 $ zlata; EURUSD v pipoch; M = namerané, O = odhad)
| symbol | S spread (normal) | provízia / str. | prechod predaj / nákup | sklz SL a stop vstup | sklz market | NY open 9:30–9:40 | správy ±5 min |
|---|---|---|---|---|---|---|---|
| US100.cash | **1,5 b** (M, n=25+57; p75 → 2,0) | 0 (O) | 0 / S (M, n=47) | **1,0 b** (M, n=34, med 0,65–1,2) | 0,5 b (M, n=38) | S×2, sklz 2 b (O, n=2) | S×4, sklz 4 b (O, n=0) |
| US500.cash | 0,6 b (O; M hranice 0,2–1,2) | 0 (O) | 0 / S (M, n=5) | 0,3 b (M, n=4) | 0,3 b (O) | S×2, 1 b (O) | S×4, 2 b (O) |
| XAUUSD | 0,35 $ (M, n=5; rozptyl 0,1–0,4) | zo zmluvy (O) | 0 / S (M, n=7) | 0,25 $ (M, n=6) | 0,15 $ (O, n=4) | S×2, 0,5 $ (O) | S×5, 1,5 $ (O) |
| US30 | 3 b (O, neobchoduje sa) | 0 (O) | 0 / S | 2 b (O) | 1 b (O) | S×2 (O) | S×4 (O) |
| EURUSD | 0,3 pip (O, 0 fillov) | ~0,25 pip (O) | 0 / S | 0,2 pip (O) | 0,1 pip (O) | S×1,5 (O) | S×5, 1 pip (O) |
| BTCUSD | zo zmluvy × 1,5 (O, neobchoduje sa) | zo zmluvy | 0 / S | 0,02 % (O) | 0,02 % (O) | — | S×3 (O) |
Limit a TP: fill **za úroveň** (medián je lepší, p90 o 0,75 b horší). Konzervatívne sa nepočíta zlepšenie.
SL pred TP v jednej minúte ostáva.

---

# 20 A — Kritika 19_B (CFD fill): prepočítané na `tester/live/mirror.sqlite`, skripty B + vlastné kontroly (len čítanie)

## 1. Overenie meraní
- **m1 = bid: platí, ale dôkaz B je slabý.** „100/100 sell fillov v rozpätí sviečky“ by prešlo aj pre mid (rozpätie minúty ≫ ½ spreadu).
  Skutočný dôkaz je asymetria: buy − bid open +1,45 b, sell −0,11 b, buy nad high 7×, sell mimo 0×. Prijímam (M).
- **n je nafúknuté duplikátmi.** Demo aj Server3 bežia tie isté stratégie. V detaile sú rovnaké obchody 2× (fib:374, fib:988, nv:806)
  a US100 má 7 minút so vstupom na oboch účtoch. XAU SL_L „n=5“ = 3 nezávislé, US500 SL „n=4“ ≈ 3. Pri n ≤ 4 nie je p75 ani rozptyl.
  US500/XAU čísla sú **hranice, nie parametre** (US500 S ∈ 0,2–1,2 b, XAU S ∈ 0,10–0,40 $).
- **S US100 = 1,45 b je šum ±0,5 b.** Kontrola na sell filloch má IQR −1,0…+1,4 b, SE mediánu ≈ 0,45 b (95 % ~0,6–2,4).
  Dva short SL dokazujú S ≥ 1,64 b práve v chvíľach plnenia stopov. **§3 V2 káže p75 → 2,45 b; B dal medián proti vlastnej smernici.**
- **Hranica prechodu nie je zmeraná, len nevyvrátená.** Buy limity: nevyplnené max −3,75 b, vyplnené min +2,40 b, medzi nimi
  **0 pozorovaní** — teda práve v zóne [0, S], o ktorej pravidlo „S“ hovorí. Sell: nevyplnené max −0,78, vyplnené min +0,31 — „dotyk stačí“
  stojí na jednom bode.
- **Výber: B vyhodil nepohodlné prípady.** 4 limity dotknuté hlboko a nevyplnené (US100 114 b; US500 SHORT_216 8,45 b „EXPIRED“,
  nv:532 a nv:562 13 b „retest nevyplnený“) označil „u brokera zjavne neboli“ bez dôkazu. Na US500 sú to 3 zo 7 dotknutých limitov.
  Je to exekučná chyba (order neodišiel, expirácia), ktorú backtest nevidí a stojí výhry. Treba ju dohľadať v logu EA, nie odfiltrovať.
- **3h posun nie je „jeden fill“:** 2 obchody, 4 filly (tks:21157, noa:9822, 20. 10., účet Demo), ft aj bt v čase servera (EEST +3 h).
  Do porovnania so sviečkou nevošli (bar = None), ale do sklzu voči úrovni áno a okno dostali zlé. Okolo DST (25. 10. EU, 1. 11. US)
  hrozí posun 1–3 h. Pre krok 12 (čas ±1 sviečka) je to fatálne. „Presnosť 1 s“ je chyba EA: MT5 má `DEAL_TIME_MSC`.
- **59,5 b short SL (tks:22395)** je gap (open minúty 53 b nad SL). Sklz sa meria voči úrovni, takže gapy sa miešajú so sklzom.
  Správne je merať voči min(stop, prvý tik) ako v §3. Medián to unesie, p75/p90 nie.
- **NY open n=2, správy n=0:** S×2/×4/×5 sú literatúra (O). Smú slúžiť len ako stres, nie ako kalibrácia. SPRÁVY XAU vstupuje
  9:40, 10:15, 11:15 a 15:55 ET, teda **mimo ±5 min**. Okno ±5 min ju vôbec nepostihuje; rozhoduje spread 5–15 min po správe, nezmeraný.
- **Chýba noc / mimo RTH.** Spread US100 mimo 9:30–16:00 je u CFD väčší. B má jediné „normal“ a XAU hodinovú zmenu (0,10 vs 0,35 $) len poznamenal.

## 2. Je „0 / S“ dosť konzervatívne?
Smer je správny (graf = bid), ale S nie je konštanta: v ťahu, keď sa plnia SL a limity, je spread najširší. Preto:
nákup `bid ≤ L − S_p75(okno)`, ask = bid + S_p75 podľa okna (RTH / NY open 10 min / ±5 min správy / mimo RTH). Na predaj malá rezerva
**+0,25 b US100 / +0,05 b US500 / +0,05 $ XAU**, lebo „dotyk“ má 1 pozorovanie. Tick 0,01 ako rezerva nemá zmysel. Zlepšenie limitu/TP nepočítať (súhlas s B).

## 3. Zapadnutie do V2
- **MNQ:** NT SL sklz medián 2 ticky (n=14, short 3,5 pri n=8). Je to sim engine, takže je to **dolná** hranica. §3 „+1 tick“ → **+2 ticky** na stop/market
  MNQ (a MYM, O). Náklad 1,75 ticku zo 16_C/17_C ostáva. Limit/TP v sim sedí presne, o fronte to nič nehovorí, preto 1 tick prechodu ostáva.
- **CFD je ~2× drahší ako MNQ:** US100 ~2,5 b na kolo vs MNQ ~1–1,4 b. Ladenie na futures/Dukascopy s nákladom MNQ sa nesmie prenášať na FTMO bez CFD modelu.
- **Krok 12 je dnes nesplniteľný.** „Sklz a spread ≤ model (medián)“ nemá z čoho počítať, lebo EA zahadzuje bid/ask. Blokér: MqlTick bid/ask pri
  odoslaní aj fille, `DEAL_TIME_MSC`, oprava `ToMs`. Dovtedy CFD hypotéza najviac 🟡. Prah prepočtu „> 1 S“ zmeniť na **> 0,5 S alebo > 0,01 R**:
  pri US500 SL 11 b je 1 S = 0,05 R, teda celý edge.

## 4. Dopad na živé (SL zo zrkadla, náklad na kolo ≈ S + sklz × podiel strát)
IBS EZ US100 (limit, SL med 67 b, p25 52) 0,03–0,05 R → PF 1,5 → **1,30–1,38**, plus stratené dotyky (~3–6 % longov, väčšinou výhry).
**B 1,25–1,35 je realistické.** NOA (limit, 89 b) ~0,025 R → −0,05 až −0,10 PF. VWAP ORB (market, SL 217–699 b, n=5) ≤ 0,012 R → −0,02 až −0,04.
B (SL 110–200) je tu prísnejší, ok. **B vynechal najhoršie:** US500 IBS EZ ES (SL 15 b) ~0,06 R a NY VA (11 b) ~0,08 R. Pri RR ≤ 1 to zjedá väčšinu edge.
XAU Fibo (16 $, p25 7 $) 0,04–0,09 R. SPRÁVY XAU (market, 32 $) ~0,02 R pri normálnom spreade, n=4, rozhoduje nezmeraný spread po správe.

## DOHODA (M = namerané, O = odhad; bod = 1,0 indexu / 1 $ zlata)
| symbol | S RTH | S mimo RTH | prechod predaj / nákup | sklz SL a stop | market | NY open | správy ±5 min |
|---|---|---|---|---|---|---|---|
| US100.cash | **2,0 b** (O z M: med 1,45, p75 2,45, ≥1,64 pri SL) | S×2 (O) | +0,25 b (O) / bid ≤ L−S (M smer) | 1,0 b (M, ~30 nezáv., bez gapov) | 0,5 b (M) | S×2, 2 b (O, n=2) | S×4, 4 b (O, n=0) |
| US500.cash | **0,8 b** (O; M hranice 0,2–1,2, n≈3) | S×2 (O) | +0,05 / L−S | 0,3 b (O, n≈3) | 0,3 b (O) | S×2, 1 b (O) | S×4, 2 b (O) |
| XAUUSD | **0,40 $** (O; M 0,10–0,40, n≈5) | podľa hodiny (O) | +0,05 $ / L−S | 0,25 $ (O, n=3) | 0,15 $ (O) | S×2, 0,5 $ (O) | S×5, 1,5 $ (O) |
| US30, EURUSD, BTCUSD | ako B (všetko O) | — | 0 / S | ako B (O) | ako B (O) | ako B (O) | ako B (O) |
| MNQ (NT) | — | — | 1 tick (§3) | **+2 ticky** (M sim, n=14) | +2 ticky (O) | — | — |
Podmienky: CFD hypotéza najviac 🟡, kým EA neloguje bid/ask a ms čas. 4 dotknuté nevyplnené limity sa vysvetlia, nie vyradia. Prepočet pri odchýlke > 0,5 S.

---

# 21 C — Kontrola 19_B a 20_A (CFD fill). Prepočítané na `tester/live/mirror.sqlite` (len čítanie), skripty v scratchpade C

## 1. Námietky A: čo platí
- **Duplikáty: pravda, ale US100 málo.** Nezávislé (stratégia, strana, minúta) sú takéto: US100 184 → 178, US500 16 → 12, XAU 16 → 12. Po odstránení
  duplikátov je spread US100 v RTH (buy fill − bid open, ≤ 3 s) **1,40 b (n=20)** a kontrola na predajoch −0,01 b (n=29). Odhad B (1,45) teda drží.
- **p75: A číta §3 zle.** 2,45 je p75 *zašumeného odhadu* (aj kontrola na predajoch má p75 +0,9 b), nie p75 spreadu. Ten sa z týchto dát zmerať nedá.
  2,0 b je teda **voľba** (+0,6 b nad mediánom), nie meranie. Ako voľbu ju prijímam a značím O.
- **4 dotknuté nevyplnené limity: obaja sa mýlia.** A píše, že „stoja výhry“. Overil som, že **cena vo všetkých 4 prešla aj cez SL**: nv:532 low 7697,35
  < SL 7698,65, nv:562 7694,4, SHORT_216 high 7571,05 = SL (na bide, ask je vyššie), LONG_398 prienik 114 b > SL 85,5 b. V backteste sú to 4× −1R,
  živé „nevyplnenie“ teda živému účtu pomohlo. B ich vyradil bez dôkazu, pritom dôkaz je v logu:
  - LONG_398: `10015 invalid price`. Nákupný limit odišiel, keď bid už bol 44 b pod L (`note`, 6. 11. 14:33).
  - US500 3×: event „order zadaný“, potom EXPIRED / „retest nevyplnený“. Bid bol 8–13 b za úrovňou a fill ani chyba nie sú zapísané. **Nevysvetlené.**
    Treba to overiť v histórii terminálu NAS-WIN11 (chýbajúci fill v zrkadle?). Kým sa to nevysvetlí, US500 exekúcia nie je overená.
  - fib:709 (XAU) obaja prehliadli. EA prešlo do `paused` a `deinit` (4. 11. 21:23), takže dotyk o 2 dni neskôr je chyba merania.
- **3h posun: pravda, ale nie „fatálne“.** Sú to 2 obchody a 4 filly, Demo 20. 10. Chyba je známa a opravená: EA bolo nasadené s posunom 0,
  `TradeBotEA.mqh:177`. Po prechode na zimný čas (od 2. 11.) má zrkadlo 146 MT5 fillov a žiadny predaj neleží mimo bid sviečky. Stačí vylúčiť Demo 20. 10.
- **DEAL_TIME_MSC: pravda.** EA berie `DEAL_TIME` (s), `TradeBotEA.mqh:1887`. Exekútor už berie `DEAL_TIME_MSC` (`TradeBotExecutor.mqh:390, 1130`), oprava je triviálna.
- **Dopad na US500: pravda.** SL zo zrkadla: IBS EZ ES medián 14,4 b, NY VA 9,9 b, RR ≈ 0,5. Náklad ≈ 0,9 b = 0,06–0,09 R. Pri WR 75 % je edge ≈ 0,10 R, teda zmizne.
- **MNQ „+2 ticky (M, n=14)“: nepravda.** Vo vzorke sú duplikáty DEMO9584400 a Tradeify. Bez nich je SL sklz **medián 1 tick, p75 5 (n=11)**.
  Medián preto podporuje dnešné +1 z §3. +2 smie ostať len ako konzervatívna voľba (O).

## 2. Čo obaja prehliadli
1. **Ask sa dá zmerať hneď, netreba čakať 8 týždňov.** `SpoolMinutes` zahadzuje `MqlRates.spread` (`TradeBotEA.mqh:1047`). Server FTMO však vydá históriu
   `CopyTicks` (bid/ask) aj `spread` v M1 spätne. Jednorazový skript MQL5 dá p75 spreadu podľa hodiny aj okolo správ už teraz. Dukascopy má aj ask sviečky,
   takže násobky okolo správ a pri otvorení NY sa dajú zmerať na rokoch 2021–26, nie z literatúry.
2. **Limit, ktorý je pri odoslaní už za cenou.** Emulátor (`_entry_fill` / `EntryFill`) ho vyplní na otvorení, teda za lepšiu cenu. MT5 ho odmietne (10015).
   Na bid open to bolo 3 zo 75 limitov US100: 2 sa vyplnili horšie o 0,45–0,75 b, 1 bol odmietnutý. Model musí mať pravidlo: „limit za trhom → neplní sa“.
3. **Fill v2 neexistuje ani pre futures.** V `emulator.py` ani v `McEmulator.cs` nie je spread, sklz ani prechod o 1 tick a prepínač `--fill` nikde nie je.
   Plnenie je dnes na dotyk, pri gape na otvorení. Veta §3 „platí už v ladení“ je preto zatiaľ blokér, nie stav.
4. **Krok 12 stratí silu.** S = 2,0 b je nad mediánom (1,4), takže „namerané ≤ model“ pri spreade prejde vždy. Porovnávať treba medián s mediánom
   a konzervatívne S nechať len na PF.
5. **Dukascopy a FTMO sa neprekrývajú.** Dukascopy NAS100 je 1/2021–4. 9. 2026, US500 2015–31. 8. 2026, XAU 2016–4. 9. 2026. M1 brokera má US100
   20. 10.–27. 11. (~5,5 týždňa), US500 21. 10.–5. 11. (~2 týždne), XAU 21. 10.–27. 11. Zhodu bidu Dukascopy a FTMO nemá kto overiť, preto treba aspoň mesiac prekryvu.

## 3. Implementácia
Je jednoduchá. Do `_entry_fill` / `_exit_fill` a `EntryFill` / `ExitFill` treba pridať posun podľa strany: nákup `low ≤ L − S`, predaj `high ≥ L + r`, SL/market ± sklz.
Prejsť musí parita C# = Python (`test_csharp_parity`). S podľa okna (RTH, otvorenie NY, správy, mimo RTH) potrebuje v oboch enginoch čas a `calendar_us.json`.
Freqtrade to nevie, CFD preto ide len cez emulátor. Backtest má k dispozícii roky na Dukascopy (bid) a krátke m1 brokera.

## FINÁLNA TABUĽKA (graf = bid; M = namerané po odstránení duplikátov, O = voľba alebo odhad)
| symbol | S RTH | S mimo RTH | spúšťač predaj / nákup | sklz SL a stop | market | NY open 9:30–9:40 | správy ±5 min |
|---|---|---|---|---|---|---|---|
| US100.cash | **2,0 b** (O; M medián 1,4, n=20) | S×2 (O) | bid ≥ L+0,25 / bid ≤ L−S | 1,0 b (M med, n=33, p75 1,55) | 0,5 b (M) | S×2, +2 b (O, stres) | S×4, +4 b (O, stres) |
| US500.cash | 0,8 b (O; M hranice 0,2–1,2, n≈3) | S×2 (O) | L+0,05 / L−S | 0,3 b (O; M med 0,21, n=3) | 0,3 b (O) | S×2, +1 b (O) | S×4, +2 b (O) |
| XAUUSD | 0,40 $ (O; M 0,10–0,40) | podľa hodiny (O) | L+0,05 / L−S | 0,25 $ (O; M med 0,15, n=4, max 0,48) | 0,15 $ (O) | S×2, +0,5 $ (O) | S×5, +1,5 $ (O) |
| US30, EURUSD, BTCUSD | ako 19_B (všetko O, neobchodujú sa) | — | 0 / S | O | O | O | O |
| MNQ / MYM | — | — | 1 tick (§3) | **+2 ticky (O; M med 1, p75 5, n=11)** | +2 ticky (O) | — | — |
Doplnky: limit za trhom pri odoslaní sa neplní. Zlepšenie limitu a TP sa nepočíta. Ak minúta zasiahne SL aj TP, platí SL. Prepočet pri odchýlke > 0,5 S.

## VERDIKT: zapísať do smernice — ÁNO, s podmienkami
- Všetky CFD čísla sú O a CFD hypotéza je **najviac 🟡**, kým:
  (a) skript `CopyTicks` / M1 `spread` nenahradí S nameraným p75 podľa okna,
  (b) EA nezapisuje bid/ask a `DEAL_TIME_MSC`,
  (c) sa nevysvetlia 3 nevyplnené limity US500.
- §3 doplniť takto:
  - „spread zo zmluvy × 1,5“ nahradiť „p75 z histórie ticku brokera“,
  - pridať pravidlo „limit za trhom“,
  - pridať, že `--fill v2` treba ešte naprogramovať (dnes neexistuje).
- Krok 12 porovnáva medián s mediánom.
- Stratégie na US500 s SL < 15 b nejdú na demo, kým PF po tomto modeli nebude ≥ 1,15.
