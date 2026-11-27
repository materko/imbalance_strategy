# 26 · Inžinier B · Oprava generátora ZAKLAD (27. 11. 2026)

Generátor je `docs/audity/2026-11-27-smernica-v2/zaklad_profily/build.py --apply`. Vymazal som 924 starých profilov a vyrobil 924 nových
(154 stratégií × 6 trhov). pytest (test_config, test_webapp_vyber, test_webapp_catalog) prešiel 55/55, `ruff check .` je čistý. Nič som necommitoval.

## Zmeny
- **Domov (C6, bod 6′):** generátor berie domov z `domov.json`, čo je kópia `25_B_domovsky_trh.json` uložená vedľa skriptu, a heuristiku vyhodil.
  Dôkaz a istota idú do `_comment`. Pri istote „nízka“ (60 profilov: orb15/mtkorb, flashorb, sweepfvg) je v `_comment` „Domov je ODVODENÝ … krok 10“.
  Pri `bez_bodov` (94 stratégií, 564 profilov) sa nič neprepočítava.
- **C4:** pribudol výslovný `PRICE_FIELDS` {kľúč: {pole: abs|ticks|usd}} pre 65 stratégií. Regex mien je preč.
- **C2:** voltbreak a voltbreaknet majú `tpUsd`/`slUsd` ako „usd“. Body (= $/usdPerPoint) sa prepočítajú pomerom ATR a zaokrúhlia na tick M.
  Nový **$** sa zapíše pri pevnom `usdPerPoint=20`. Dôvod: usdPerPoint ostáva tým, čo hovorí komentár v kóde (NQ $/bod, pre ktorý sú $ písané), a TP aj SL vychádzajú presne na ticky.
  ~~Zmena usdPerPoint by na 6E aj tak padla na rozsahu (0,01–1000).~~ Toto tvrdenie bolo nesprávne (A 27/1), oprava je v kole 2.
  Logiku nemení ani jedna cesta, lebo pole sa používa len v tp/sl_points.
- **C3:** `mag7.slOpenBuf` (a `minMove`, slPts) je v zozname. Napr. na ES: 2 → 0,25 b.
- **asiasweep:** domov je 6E, takže na 6E ostáva `vpRowTicks` 10 a na ostatné trhy sa prepočíta.
- **C1:** odchýlka zaokrúhlenia nad 50 % ide do `_comment` aj vtedy, keď sa výsledok rovná defaultu. Takú poznámku má 59 profilov.
  Pole sa vtedy nezapíše, lebo test only_overrides to nedovolí.
- **C5:** zapnutý trailing alebo koniec seansy/dňa (closeAtSessionEnd, closeAtEnd, useCloseAtEnd, useEodClose, enableTrailing, trailVwap, useTimeExit, trailAtr>0)
  dostane vetu „hlavička musí výslovne povoliť, inak vypnúť (§0)“. Má ju 396 profilov a hodnoty som nemenil.
- **C6:** do `_comment` ide pomer ATR s hodnotami a obdobiami oboch trhov. `atr.json` má nový kľúč `_meta` (metóda a obdobia) a `atr.py` zapisuje vedľa seba.

## Neplatné základy: 25, všetky na 6E
Pole je mimo rozsahu Pine aj po prepočte a nemá jednotku ticks, preto je trh „netestovateľný bez zmeny kódu“, nie ❌:
- tks ×13: slPoints 0,00125 < 1
- orb15/mtkorb ×5: targetPoints < 0,1
- flashorb ×4: trail* < 0,1
- voltbreak ×2: slUsd 0,048 $ < 1
- mag7: slPts < 0,1

Väčšina týchto polí je pri defaulte neaktívna (slMode=swing/open, targetMode=0, trailing vypnutý). Prísne podľa 5′ ich však aj tak počítam ako neplatné.

## Čo sa ešte nedá (stav po kole 3)
- **23 profilov na 6E** (tks ×13, orb15/mtkorb ×5, flashorb ×4, mag7) potrebuje zmenu kódu: širšie CONSTRAINTS ako PORT_ONLY, alebo pole v SIZE_FIELDS s jednotkou ticks.
- Domovy s istotou „nízka“ (roboquant šablóny, sweepfvg) by potvrdil len doklad. Dovtedy je to krok 10.
- Pre MNQ↔MGC a 6E↔MGC chýba spoločné L, takže pomer ATR mieša rôzne režimy volatility. Je to zapísané, ale nedá sa to opraviť bez porušenia §1.
  ATR je denné, nie seansové (6E/MGC/BTC majú iný pomer seansa/deň).
- `scalp3ma` má domov 6E, ale webapp ju zaraďuje pod NASDAQ.

## Kolo 2 (nálezy A 27)
Znova som vyrobil 924 profilov a **neplatných je 23** (všetky na 6E). pytest prešiel 55/55 a ruff je čistý.
1. **voltbreak a voltbreaknet, 6E sú platné.** Pri poli „usd“ `build.py` najprv skúsi pevné usdPerPoint. Keď $ vyjde mimo rozsahu, skúsi krajnú hodnotu usdPerPoint v rozsahu Pine (všeobecne, funkcia `scale_usd`).
   Na 6E vyšlo usdPerPoint 1000, tpUsd 1,35 a slUsd 2,5 (27 a 50 tickov). Od A (1,25 / 2,4) sa to líši len novým pomerom ATR (bod 4).
2. **EXIT_FLAGS** som rozšíril o `useCloseAfter`, `useExit`, `useExitTime`, `useTimeClose`, `useCloseTime` a `closeEOD`.
   Veta §0 je teraz v 444 profiloch (pribudli fpc, dailyopen ×2, asiasweep ×2, nqprec ×3). Iný zapnutý časový spínač som v 154 configoch nenašiel.
   tmr (exitDay/exitHour) a nocpon (nightExit/monExit) majú časový výstup ako jadro pravidla, nie ako koniec seansy, preto vetu nedostali.
3. **Časové výstupy bez spínača: nález neplatí.**
   - silverbullet ×3 a sweepfvg (`exitH`) majú spínač `useExitTime=False`.
   - nyvaes ×2 (`closeH`) majú `useCloseTime=False`.
   - vwapop (`flatTime`) má `closeEOD=False`.
   - onbiasorb ×2 (`exitHHMM`) majú `useTimeExit=True` a ten už je v EXIT_FLAGS.

   ~~`FIXED_EXITS` je preto prázdny.~~ Platí len pre vymenované stratégie, oprava je v kole 3 (N1).
4. **Pomer ATR v spoločnom okne.** `atr.py` počíta 15 párov domov→M (domovy MNQ, ES a 6E), okno je prienik L. Pod 1 rok berie prienik celých dát; týka sa to MNQ↔MGC a 6E↔MGC (56 profilov).
   - `atr.json` → `pairs` obsahuje pomer, obe ATR, okno, zdroj, počet dní a pre porovnanie pomer z rôznych L.
   - `_comment` uvádza okno aj odchýlku proti starému pomeru.
   - Nový pomer voči starému: ES +30 %, MGC −25 %, BTC −9 %, 6E +4 %, MYM −2 %.

## Kolo 3 (nálezy C 28)
Znova som vyrobil 924 profilov, neplatných je 23. pytest (4 súbory vrátane test_csharp_parity_voltbreak) prešiel 70/70 a ruff je čistý.
- **N1:** `FIXED_EXITS` má 15 kľúčov, teda 90 profilov s vetou „koniec seansy je v kóde bez prepínača … (§0)“, s časom a súborom:riadok.
  - noa ×10 zatvára o 16:00 (`noa/engine.py:126`, C# `NoaEngine.cs:228`).
  - Päť *eod zatvára o 15:59 (`EodClose.cs:54`), noaneteod má oboje.
  - Ostatné časové výstupy vo všetkých enginoch majú prepínač. tmr, nocpon a spravy majú čas ako jadro pravidla a maxHold* sú limity držania.
- **N2:** pri pároch bez spoločného L (MNQ↔MGC, 6E↔MGC, 56 profilov) má každý trh ATR zo svojho L a celé dáta sa už nepoužívajú. Dôvod (§1 trezor, rok A) je v `_comment` aj v `atr.json` (`zdroj`, `okno`, `_meta.metoda`).
  Pri pároch so spoločným L ostáva spoločné L. Výsledok MNQ→MGC je 0,1379, predtým 0,1033.
- **N3:** pri voltbreak a voltbreaknet na 6E `_comment` uvádza, že „$“ pri usdPerPoint 1000 nie sú skutočné doláre (6E má 125 000 $/bod), ide len o prepočet bodov.
