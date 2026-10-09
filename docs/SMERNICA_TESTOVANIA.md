# Smernica testovania stratégií

*Vytvorené 8. 10. 2026, doplnené v ten istý deň: krok 1 „naživo = história“ a doplnkové testy. Platí pre každú stratégiu pred ostrým obchodovaním.*

Cieľ: mať čo najväčšiu dôveru, že čísla z backtestu budú naživo aspoň podobné. Backtest ber ako **horný strop**, naživo
vychádza takmer vždy horšie. Dôvera sa buduje tak, že stratégia prejde sériou skúšok, ktoré ju môžu „zabiť“. Čo neprejde,
ide preč, aj keď vyzerá pekne.

**Poradie je povinné:** krok 1 musí prejsť skôr, než sa čokoľvek ladí. Ladiť stratégiu, ktorá počíta naživo inak
ako na histórii, je zbytočná práca, lebo všetky čísla z nej sú falošné.

Ťažké kroky (1, 4, 5, 8, doplnky) púšťaj na **Mac mini**. Na MacBooku Air púšťaj len jednotlivé behy, lebo sa prehrieva.

---

## Spoločné nastavenie behov (MNQ)

- `--engine multicharts --pair MNQ/USD --fee 1.755e-05`. Poplatok je vždy zapnutý, nikdy nie 0.
- Vždy cez `python -m tester.webapp.cli …`, ku každému behu `--note`, čo testuje.
- **Obdobie na ladenie (in-sample):** `20211001-20250904`.
- **Odložený rok (out-of-sample):** `20250904-20260904`. Na ladenie sa **nikdy** nepoužíva.
- Keď sú dáta kratšie (napr. akcie Mag7 od 10/2023), ladí sa od začiatku dát po 9/2025 a odložený rok ostáva rovnaký.
- Po každej zmene kódu stratégie **prepočítaj profily** a zopakuj krok 1. Názov profilu môže klamať: napr. FPC profil
  „365 obchodov“ po oprave dáva 559.

---

## Postup krok za krokom

### 1. Naživo = história (PRVÝ KROK, bez neho sa nepokračuje)

Overuje sa, že stratégia vo webapp nevidí nič, čo by naživo ešte nevidela, a že jej rozhodnutie nezávisí od toho,
odkiaľ začala počítať. Robí sa s predvoleným profilom na 1 roku (napr. `20250904-20260904`).

**1a. Štart v rôznych dňoch**
- Ten istý profil spusti z celého roka a potom ešte zo 6 iných začiatkov:
  - začiatok mesiaca,
  - stred mesiaca,
  - pondelok aj piatok,
  - **štart uprostred seansy**, napr. 11:00 NY.
- Po rozbehu (warmup) musia byť obchody v prekryve **presne rovnaké**: čas vstupu, smer, cena, stop, cieľ, výstup.
- Zapíš, koľko dní rozbehu stratégia potrebuje. Platí najmä pre priemery z N dní, EMA, ADX, VWAP od otvorenia
  a zóny z minulosti.

**1b. Dáta utnuté hneď po vstupe (ako naživo, budúce sviečky neexistujú)**
- Pre 50–60 obchodov utni dáta na sviečke vstupu a pusti beh znova.
- Vstup musí vzniknúť v tom istom čase, s tou istou cenou, stopom a cieľom.
- Ak sa obchod po utnutí neobjaví alebo je iný, stratégia **pozerá do budúcnosti** (lookahead).

**1c. Utnutie uprostred vyššieho TF**
- Ak stratégia berie niečo z vyššieho TF (15m, 1h, deň), utni dáta uprostred jeho sviečky.
- Rozhodnutie musí byť rovnaké ako pri celých dátach. Vyšší TF sa smie použiť **až po zatvorení** svojej sviečky.

**1d. Závislosť od predošlých obchodov**
- Ak stratégia riadi podľa výsledku obchodu (straty po sebe, pauza, denný limit výhier, max. obchodov), výsledok
  sa musí určiť zo sviečky zavretia: zasiahnutý SL = strata, aj keď sviečka zasiahla aj TP.
- Nesmie sa určovať z toho, ako obchod vyplnil emulátor alebo broker.

**Hodnotenie:**
- **0 rozdielov → pokračuj krokom 2.**
- Akýkoľvek rozdiel → **oprav kód stratégie vo webapp**:
  - pohľad dopredu,
  - neuzavretá sviečka vyššieho TF,
  - stav závislý od začiatku dát,
  - výsledok obchodu z plnenia.
- Po oprave prepočítaj profily a zopakuj krok 1. Až potom ďalej.
- Výsledky prepočítané po oprave sú nové východisko. Staré čísla už neplatia.

**Nástroj:** skripty z kontroly VWAP ORB na Mac mini: `~/IBS/.nightsearch/vwoprestart.py`, `vwoprestart2.py`,
`vwoplive.py`. Cieľ: spraviť z nich príkaz `python -m tester.webapp.cli livecheck --strategy X --profile Y`,
ktorý urobí 1a–1c pre ľubovoľnú stratégiu a vypíše rozdiely.

### 2. Kontrola logiky a kresieb (1 beh, MacBook)
- Jeden beh na 2–3 mesiacoch s predvoleným nastavením a pozrieť graf.
- Kontrolujú sa vstupy, stop, cieľ, časy podľa pravidiel a či sa kreslí len to, čo naozaj prebehlo.

### 3. Východiskový beh na celom období ladenia
```
python -m tester.webapp.cli run --strategy X --profile Y --timerange 20211001-20250904 --note "východisko"
```
- Je to len orientácia. PF pod 0,9 pri dostatku obchodov → nápad pravdepodobne nefunguje a ladením sa nezachráni.

### 4. Hyperopt (Mac mini)
```
python -m tester.webapp.cli hyperopt --strategy X --profile Y --timerange 20211001-20250904 \
    --param slPts=10:40:1 --param rr=1:3:0.25 --min-trades 300 --epochs 200 --goal break_even
```
- Naraz **najviac 3–4 parametre**, ostatné ostávajú.
- **Min. 150 obchodov za rok — tvrdá hranica, nikdy pod ňu** (4 roky → `--min-trades 600`). Nastavenie pod 150/rok nesmie vyhrať ani byť kandidátom.
- `--goal break_even` alebo `profit`. **Nikdy neladiť na winrate**, ten sa dá nafúknuť malým TP a veľkým SL.
- **Zapísať, koľko kombinácií sa skúsilo** (spolu za všetky hyperopty na tej stratégii). Čím viac pokusov, tým
  prísnejšie hranice:
  - nad 1000 kombinácií chceme PF na odloženom roku aspoň 1,3 namiesto 1,2,
  - test proti náhode lepší než 99 %.

#### Ako ide hľadanie, keď poviem „spusti podľa smernice“ (platí pre každý test, od 8. 10. 2026)
Automatické hľadanie (Mac mini, `.nightsearch/glsearch.py` + `glhyper.py`) beží donekonečna, kým nenájdeme, čo hľadáme:
1. **Krok 1 najprv** (naživo = história, `livecheck.py`) — bez neho sa stratégia do hľadania nepridá.
2. **Mriežka po skupinách** — naraz najviac 4 parametre, ostatné na doterajšom najlepšom, skupina po skupine dokola.
3. **Zaseknutie** (okolie bodu je celé preskúšané alebo kolo bez zlepšenia):
   - toto **lokálne optimum ide do hyperoptu** (Optuna TPE, zase najviac 4 parametre naraz, spojité hodnoty v rozsahu
     mriežky rozšírenom o 30 %, štart z optima) — jemné doladenie,
   - hľadanie **medzitým skočí na nové nastavenia** (náhodný sused najlepšieho, 3 parametre z rôznych skupín) a pokračuje odtiaľ.
4. Každý výsledok z mriežky aj z hyperoptu, ktorý prejde ladením (PF ≥ 1,3, ≥ 150 obch/rok, žiadny rok pod PF 0,9) →
   **plató** (≥ 80 %) → **odložený rok raz**. Skúšané kombinácie sa sčítavajú (mriežka + hyperopt) kvôli prísnejším hraniciam.
5. Výsledky: každé ráno 7:00 automaticky (testy sa na čas nahrávania pozastavia) — tabuľka v iCloude PRIEBEH,
   web stránka s výsledkami (až 10 najlepších nastavení na stratégiu, FTMO / Tradeify výzvy), priečinok na ploche.
   Do webapp idú **len nastavenia, ktoré prešli** — ako profily **PREŠIEL SMERNICAMI** + beh v histórii.

### 5. Plató okolo víťaza (Mac mini)
```
python -m tester.webapp.cli plateau <id_hyperoptu>
```
- Susedné hodnoty parametrov musia dávať podobný výsledok, aspoň 80 % PF víťaza
  (napr. SL 25 → 22 / 28, prah 5 → 4,5 / 5,5).
- Víťaz ako osamotená špička → vybrať **stred plató**, nie vrchol.

### 6. Odložený rok, spustený raz
```
python -m tester.webapp.cli run --strategy X --profile Y --timerange 20250904-20260904 --note "OOS"
```
- Ak neprejde, nastavenie ide preč. **Neladiť na tomto roku**, inak už nie je čím overovať.

### 7. Analytika na všetkých 5 oknách
```
python -m tester.webapp.cli checkup --strategy X --profile Y --fee 1.755e-05
```
- Jedným príkazom vyrobí:
  - výsledky po rokoch na 5 referenčných oknách,
  - test proti náhode (1000 náhodných behov),
  - test, či edge časom neslabne,
  - Monte Carlo drawdown,
  - break-even poplatok.
- Výsledok: `tradebot/strategies/<kľúč>/docs/ANALYTIKA.md`.
- Max. drawdown z Monte Carlo (95 %) si zapíš. Je to hranica na vypnutie stratégie v kroku 11.

### 8. Iné dáta a iný trh (Mac mini)
- To isté nastavenie na NAS100 z Dukascopy (`--pair NAS100/USD`) a ak sa dá, aj na ES alebo inom indexe.
- Výsledok nemusí byť rovnaký, ale musí ísť **rovnakým smerom**.
- Funguje len na jednom zdroji dát → výsledok závisí od detailov dát, nie od trhu.

### 9. Parita platforiem (TradingView / MultiCharts)
- Webapp a TradingView (príp. MultiCharts) musia mať **tie isté obchody v tie isté dni** (kontrola na 1–2 mesiacoch).
- V TradingView ten istý test ako krok 1: reštart grafu v iný deň, obchody na tých istých miestach. V tabuľke skriptu
  sleduj „História od“.
- V Pine skontrolovať (už sa reálne stalo):
  - `request.security` z nižšieho TF alebo z neuzavretej sviečky vyššieho TF,
  - riadenie podľa výsledku obchodu,
  - `calc_on_every_tick`,
  - začiatok seansy pri akciách,
  - málo histórie na 1m,
  - limit 500 boxov.

### 10. Forward test 4–8 týždňov
- Paper účet alebo 1 MNQ, aspoň **20–30 obchodov**.
- Každý týždeň porovnať obchody naživo s webapp na tie isté dni, **obchod po obchode**.
  Rozdiely ukážu sklz, chyby v kóde aj repaint.
- Veľkosť sa zvyšuje až keď sa zhodujú.

### 11. Ostrá prevádzka
- Začať s malou veľkosťou.
- Pravidlo na vypnutie nastaviť **vopred**:
  - drawdown nad Monte Carlo 95 % → stratégia sa vypína,
  - PF po 50 obchodoch pod 1,0 → stratégia sa vypína.

---

## Doplnkové testy (pred krokom 10, Mac mini)

Tieto testy zvyšujú dôveru, keď hlavné kroky prešli.

- **Postupné ladenie (walk-forward):** namiesto jedného rozdelenia sa ladí na 2 rokoch a testuje na nasledujúcich
  6 mesiacoch, potom sa okno posunie o 6 mesiacov. Testovacie kúsky spolu musia držať PF ≥ 1,2.
  Ukáže, či nastavenie prežije zmenu trhu.
- **Stres poplatkov a sklzu:**
  - beh s 2× poplatkom (`--fee 3.51e-05`) musí ostať v pluse,
  - 1 tick sklzu navyše na vstup aj výstup nesmie stratégiu otočiť do straty.
- **Režimy trhu:** výsledky rozdelené podľa volatility (pokojné / bežné / divoké dni podľa ATR) a podľa trendu.
  Stratégia nesmie žiť z jedného typu dní, ak tie neprídu pravidelne.
- **Kvalita dát:** pred testom skontroluj, či v dátach nechýbajú dni, neboli posunuté časy (letný čas) a či sa
  nemení kontrakt v divnom čase (rollover). Chyba v dátach dá falošný edge.
- **Portfólio:** keď beží viac stratégií naraz, `python -m tester.webapp.cli portfolio` ukáže spoločný drawdown.
  Stratégie, ktoré prehrávajú v tie isté dni, sa nesčítavajú ako nezávislé.

---

## Čo hľadať (MNQ intraday, vrátane poplatkov)

| Metrika | Minimum | Dobré | Podozrivé |
|---|---|---|---|
| Naživo = história (krok 1) | 0 rozdielov | 0 rozdielov | akýkoľvek rozdiel → oprava kódu |
| Obchody za rok | **150 — tvrdá hranica, nikdy pod** | 150–300 | pod 50 (nedá sa posúdiť) |
| PF na období ladenia | 1,3 | 1,5–2,0 | nad 2,5 (skoro isto preladené) |
| PF na odloženom roku | 1,2 a aspoň 70 % PF z ladenia | 80 %+ PF z ladenia | pod 1,1 → zahodiť |
| Roky v pluse (5 okien) | 4 z 5, žiadny pod PF 0,9 | 5 z 5 | jeden super rok, ostatné okolo nuly |
| Test proti náhode | lepšia než 95 % náhodných behov | 99 % | horšia ako 90 % → nemá edge |
| Break-even poplatok | 2× reálny poplatok | 3× a viac | tesne nad reálnym |
| Zisk / max. drawdown za rok | 1,5 | 2–3 | – |
| Plató (susedné hodnoty) | 80 % PF víťaza | 90 % | pod 60 % (špička) |
| 2× poplatok | PF > 1,0 | PF ≥ 1,2 | strata |
| Forward test oproti backtestu | PF najviac o 30 % nižší | do 20 % | obchody sa nezhodujú s webapp |

**Celkový počet obchodov:** aspoň 200–300 za všetky roky. Pri 40 obchodoch je aj PF 1,13 prakticky šum.

**Winrate nemá samostatnú hranicu**, závisí od pomeru TP : SL. Potrebné minimum (bez poplatkov):

| RR (TP : SL) | potrebný WR |
|---|---|
| 1 : 1 | nad 55 % |
| 1 : 2 | nad 38 % |
| 1 : 4 | nad 23 % |
| 1 : 20 (malý TP, veľký SL) | nad 95 % a extrémne citlivé na sklz |

Vždy pozerať PF a break-even poplatok spolu s WR. Profily s malým TP a veľkým SL (napr. DAILY OPEN TP 5 / SL 100) majú
vysoký WR, ale jedna séria strát zmaže mesiace a na sklz sú najcitlivejšie.

**Rátaj so zrážkou:** naživo býva PF o 20–30 % nižší než v backteste. Z backtestu s PF 1,5 tak naživo očakávaj 1,2–1,3.
Stratégia s PF 1,1–1,2 v backteste naživo pravdepodobne nezarobí.

---

## Kontrolný zoznam (skopíruj si ku každej stratégii)

```
Stratégia: ____________   Profil: ____________   Dátum: ________
[ ] 1. naživo = história: 1a štarty ___ rozdielov, 1b utnutie ___ rozdielov, 1c vyšší TF ___, 1d výsledok obchodu ok
       rozbeh ____ dní; ak rozdiely → oprava kódu (commit ________), profily prepočítané, krok 1 znova
[ ] 2. logika a kresby sedia (beh: ________)
[ ] 3. východisko na ladení: obch ____ PF ____ (beh: ________)
[ ] 4. hyperopt (≤ 4 parametre, min-trades ____, skúsených kombinácií spolu ____): víťaz ________
[ ] 5. plató: susedia ____ % PF víťaza → zvolené nastavenie ________
[ ] 6. odložený rok: obch ____ PF ____ (≥ 1,2 a ≥ 70 % z ladenia?)
[ ] 7. checkup: rokov v pluse __/5, náhoda ____ %, break-even poplatok ____, MC DD 95 % ____
[ ] 8. NAS100 / iný trh: PF ____ (rovnaký smer?)
[ ] 9. TV = webapp na 1–2 mesiacoch, TV reštart = rovnaké obchody
[ ] doplnky: walk-forward PF ____, 2× poplatok PF ____, režimy ok, dáta ok, portfólio DD ____
[ ] 10. forward ____ týždňov, ____ obchodov, PF ____ (≤ 30 % pod backtestom?)
[ ] 11. ostrá prevádzka: veľkosť ____, vypnúť pri DD ____ alebo PF < 1 po 50 obchodoch
```

---

## Stav stratégií podľa smernice (8. 10. 2026)

| Stratégia | Stav |
|---|---|
| VWAP ORB | krok 1 prešiel (8. 10.: 6 štartov + utnutie po vstupe, 0 rozdielov) → ďalej krokom 2 |
| SPX sila (pôvodne Mag7) | krok 1 chýba; podľa čísel neprešla: posledných 10 mesiacov PF 1,06 (3 roky 1,28) |
| FPC | krok 1 chýba (7. 10. opravené hodnotenie výsledku obchodu) → začať krokom 1 |
| IBS Entry Zone | krok 1 vo webapp: 1a + 1b po dňoch PREŠIEL (8. 10., 0 rozdielov); chýba utnutie po sviečke a 1c → potom krok 2 |
| IBS zóny | krok 1 vo webapp: 1a + 1b po dňoch PREŠIEL (8. 10., 0 rozdielov); test proti náhode (D_najstabilnejsi): 5 rokov spolu 7–8 σ, ale edge len v 3 z 5 rokov (22/23, 23/24 ako náhoda, DD 57–60 %) → zatiaľ NEPREŠIEL; ďalej režimy trhu a walk-forward |
| Craig Percoco | čiastočne 1a (štart 15. 7. = tie isté obchody); nedá sa posúdiť: 40 obchodov |
| ASIA SWEEP, DAILY OPEN | začať krokom 1 |
| Záložné (Noise Area, VWAP trend, ORB 5 min, Initial Balance) | neprešli: PF 0,74–1,17 neladené |
| Záložné: Posledná polhodina, Overnight | na hranici (PF 1,17–1,18) → ak ich chceme, začať krokom 1 |
