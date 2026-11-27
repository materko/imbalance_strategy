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
