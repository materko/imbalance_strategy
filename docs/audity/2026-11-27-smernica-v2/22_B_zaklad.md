# 22 · Inžinier B · Východisko ZAKLAD (27. 11. 2026)

## Návrh znenia — do §4, nový krok 3a (§2 dostane odkaz „východisko podľa kroku 3a“)

**Krok 3a — Východisko = ZAKLAD_<trh>.**
1. Východisko každej hypotézy na trhu M je `tradebot/strategies/<kľúč>/configs/ZAKLAD_<M>.json` (predvolené hodnoty kódu,
   `_timerange` = L trhu M). Hash jeho commitu a hash `config.py` ide do hlavičky pred prvým behom.
2. Mriežka a Optuna (krok 4) majú stred v hodnotách ZAKLAD_<M>; rozsahy sa zapíšu v hlavičke ako násobky alebo kroky
   od tohto stredu. Plató (krok 5) sa meria tiež okolo bodu, ktorý našlo hľadanie z tohto stredu.
3. **Zakázané** ako východisko, stred, hranica rozsahu alebo „inšpirácia“ mriežky: hodnoty z `tester/archive/`,
   `docs/profily_archiv/`, `tester/tests/fixtures/profiles/`, skrytých profilov (golden_*, multicharts_*, PRESIEL_*),
   `.nightsearch/dash/archiv_pred_V2` a z histórie behov. Fixtúry slúžia len paritným testom. Porušenie = nová hypotéza
   cestou kroku 10.
4. Legacy profil (aj najlepší z webapp) sa nesmie vrátiť do hľadania. Smie ísť len cestou kroku 10 ako samostatný zápis
   v registri s odhadom N z histórie; jeho výsledok je **informácia**, nikdy kandidát ani stred mriežky.
5. **Orezané prahy** (komentár „orezané na rozsah Pine“): ZAKLAD_<M> s orezaním nie je platné východisko. Pred krokom 3
   sa buď (a) rozšíri CONSTRAINTS v porte (pole do `PORT_ONLY_FIELDS`, default zhodný s Pine) a profil sa vyrobí
   znova bez orezania, alebo (b) trh M sa pre hypotézu zapíše ako **„netestovateľný bez zmeny kódu“** (nie ❌).
   Prah pod 1 tick trhu sa zaokrúhli na 1 tick a zapíše. Výsledok orezaného profilu sa v bráne nepoužije.
6. **Predvolené hodnoty nie sú nevinné.** Logika a defaulty sa vyvíjali na tých istých dátach (MNQ 2019–2026, štúdie §1).
   Preto: ZAKLAD nemá bonus „bez ladenia“; počiatočné k trezoru aj N pre DSR/haircut sa berú prísne z celej histórie
   rodiny (§9 bod 7), nie od nuly. Ak `git log` ukáže, že default v `config.py` vznikol alebo sa zmenil po behu/štúdii
   (napr. „profil zo štúdie“, kópie MTK EMAS), hypotéza je „zo štúdie“ (§2, Z5) a ide krokom 10.
7. Zmena predvoleného kódu po prvom behu = nová hypotéza (zmrazenie §0); ZAKLAD sa nesmie „opraviť“ podľa výsledku.

## Riziká prepočtu ATR (overené na build.py a 924 súboroch)
- **Domovský trh nebol zistený, len predpokladaný:** všetkých 154/154 stratégií vyšlo MNQ (fallback, detekcia nezabrala
  ani raz). Pri kópiách …es/…mgc/…eur/…btc som overil, že defaulty kódu = defaulty predlohy, takže MNQ sedí; ale ak má
  niektorá stratégia defaulty pôvodne z iného trhu (napr. BTC alebo zlato), je prepočet zlý 5–150×. Treba ručný zoznam
  domovov v hlavičke, nie heuristiku.
- **Orezanie je fatálne na 6E:** 39 profilov v 13 stratégiách. Napr. `ibs/ZAKLAD_6E`: `minImbSizePoints`,
  `srClusterPoints`, `ewMinWavePoints` = 1 pri dennom ATR 0,0065 (≈ 150× ATR) → filter mŕtvy alebo 0 obchodov.
  Taký beh nesmie dať ❌ hypotéze (bod 5).
- **Pod-tick hodnoty:** `ibs/ZAKLAD_6E` `state2ConfirmTicks` = 8e-06 (tick 5e-05) → potvrdenie fakticky vypnuté, mení logiku.
- **Rôzne obdobia v pomere:** ATR MNQ z L 2019–2022, ES z L 2015–2025, MGC 2023–2025 — pomer mieša režimy volatility.
  Pomer cien/ATR v rovnakom kalendári by bol presnejší; rozdiel treba aspoň zapísať.
- **Denný ATR vs. seansa:** 6E, MGC, BTC (24/7, víkendy v dennom resample) majú iný pomer seansa/deň než MNQ;
  intradenné prahy na NY seanse môžu byť posunuté.
- Prepočítajú sa len `SIZE_FIELDS` s jednotkou abs/ticks; bodové polia mimo SIZE_FIELDS ostanú v bodoch MNQ — treba audit polí.
- TF a ATR pochádzajú z L (povolené), ale `default_timeframe` mohol vzniknúť ladením — zaradiť pod bod 6.
