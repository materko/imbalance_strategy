# 24 · Kontrolór C · ZAKLAD po oprave (27. 11. 2026)

## 1. DOHODA 5′ — čo sedí (strojovo, všetkých 924 profilov, vzorka ibs/tks/orb15/flashorb/mtkzone/nyvaes × ES/6E/BTC/MGC)
- `pct`/`atr` nikde (78 dict polí: 65 `ticks`, 13 `abs`). Všetky profily sa načítajú, int pole nikde nedostalo float.
- Každé zapísané pole = prepočet ±50 % alebo má poznámku „o X % viac“. Ticky sa počítajú v tickoch M (TICK v build.py = `tick_size` inštrumentu, BTC 0,1). C# `SizeSpec` pozná `abs`/`ticks`.
- 23 × 6E „NEPLATNÝ ZÁKLAD“ súhlasí (slPoints/targetPoints/trail*/slPts pod dolnou hranicou Pine).

## 2. Nové chyby (C1–C4 blokujú zápis profilov ako platných)
- **C1 Stratené odchýlky (72 prípadov).** `prm.pop`, keď sa výsledok po zaokrúhlení rovná defaultu, zmaže pole aj poznámku. Default 1 tick
  (`state2ConfirmTicks` 13 stratégií, `slTicks` m2×4, `entryOffsetTicks` nb) na ES/MYM/MGC/6E ostáva 1 tick, hoci prepočet je 0,05–0,5 ticku (+110 až +530 %).
  Hodnota je správne (min 1 tick), ale 5′ žiada odchýlku v `_comment` a v hlavičke. Teraz tam nie je.
- **C2 voltbreak, voltbreaknet: aktívny stop/cieľ sa neprepočítal (10 profilov).** `tpUsd`/`slUsd` ÷ `usdPerPoint` (20) = TP 40, SL 75 bodov na každom trhu.
  ES 5× širšie, MGC 7×, BTC 7× užšie, 6E absurdné (75 bodov EUR). Regex mien to nechytil a profil nie je označený ako neplatný.
- **C3 mag7: `slOpenBuf` = 2,0 bodu sa neprepočítal**, a pritom default `slMode=OPEN` ho používa. ES 5,4× (0,37), MGC 7×, BTC 0,15×, MYM 0,5×.
  Profily ES/MYM/MGC/BTC sú neoznačené a zlé.
- **C4 Výber polí podľa mena nestačí** (to isté, čo A3). Treba explicitný zoznam cenových polí na každú stratégiu v hlavičke alebo v kóde (`PRICE_FIELDS`),
  nie regex. Ostatné nájdené mimo regexu sú násobky alebo bary (`r*Stop`, `minAnchorGap`): v poriadku.
- **C5 Konflikt s §0.** ZAKLAD = defaulty, a tie majú `closeAtSessionEnd` (21 stratégií vrátane ibs), `trailVwap` (11 noa), `useEodClose` (flashorb×4), `enableTrailing` (divergence).
  §0 povoľuje trailing a koniec seansy v hľadaní len keď to hypotéza výslovne povie. Hlavička to musí zapísať, inak to porušuje §0.
- **C6 Dôsledok 6′.** Domov je MNQ pri 154/154 len predpoklad. Fallback = „zo štúdie“ = krok 10 = najviac 🟡 pre všetko. Ručný zoznam domovov je preto blokér, nie poznámka.
  Pomer ATR a jeho obdobia nie sú v `_comment` ani v `atr.json` (obdobia sú len v `MK` v build.py).
- Drobné: 6E `tks` je neplatný kvôli `slPoints`, ktorý pri `slMode=swing` nič nerobí. Je to prísne, ale v súlade s 5′ (v mriežke by ožil).

## 3. Konzistencia so SMERNICOU V2
- B 1–4, 7 + 5′/6′ sedia s §0 (zmrazenie), §2 (legacy → krok 10, Z5), §9 bod 7 (prísne k) a s krokom 3 („netestovateľný“ ≠ ❌). Chýba len C5 (§0) a jednotka rozsahov (A k bodu 2).

## FINÁLNE ZNENIE kroku 3a
**Krok 3a — Východisko = ZAKLAD_<M>.** (1) Východisko hypotézy na trhu M je `configs/ZAKLAD_<M>.json` (defaulty kódu, `_timerange` = L trhu M). Hash commitu a `config.py` ide do hlavičky.
(2) Stred mriežky a Optuny = ZAKLAD_<M>. Rozsahy sú v hlavičke v jednotke poľa (abs/ticks M) a plató sa meria okolo nájdeného bodu.
(3) Zakázané ako východisko, stred, hranica alebo inšpirácia: `tester/archive/`, `docs/profily_archiv/`, fixtúry (len parita), skryté profily, `archiv_pred_V2`, história behov. Porušenie = krok 10.
(4) Legacy profil ide len krokom 10 ako samostatný zápis s N z histórie. Je to informácia, nikdy kandidát ani stred.
(5) Prepočet = hodnota × ATR_M/ATR_domov v pevnej cene M: abs v rozsahu Pine ako abs, inak `ticks` (round, min 1). `pct`/`atr` sú zakázané.
Odchýlka zaokrúhlenia > 50 % ide do `_comment` aj do hlavičky, **aj keď sa výsledok rovná defaultu**. Prepočítajú sa **všetky cenové polia zo zoznamu v hlavičke**
(aj mimo SIZE_FIELDS, aj polia v $ cez `usdPerPoint`). Čo sa nedá bez zmeny kódu, je „netestovateľný bez zmeny kódu“ (nie ❌). Orezaný, neprepočítaný alebo neoznačený profil v bráne neplatí.
(6) Defaulty nie sú nevinné: nedostanú bonus, k a N sú prísne z celej histórie rodiny. Domovský trh je v ručnom zozname s dôkazom (Pine/zadanie/git), inak hypotéza „zo štúdie“ (krok 10).
`_timeframe`, pomer ATR a jeho obdobia idú do hlavičky. Trailing a koniec seansy z defaultu musí hlavička výslovne povoliť (§0), inak sa vypnú ako zapísaná odchýlka.
(7) Zmena defaultu po prvom behu = nová hypotéza. ZAKLAD sa podľa výsledku neopravuje.

## VERDIKT
Znenie kroku 3a: **zapísať áno.** Profily ZAKLAD_* okrem MNQ: **ako platné východisko nie.** Najprv opraviť C1–C3, potom pregenerovať a overiť C4.
