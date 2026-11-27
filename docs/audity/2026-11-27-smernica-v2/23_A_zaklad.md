# 23 · Prokurátor A · Východisko ZAKLAD (27. 11. 2026)

## 1. Návrh B bod po bode
- 1, 2, 3, 4, 7: **súhlas.** K bodu 2 doplniť, že rozsah mriežky pre prah v jednotke `ticks`/`pct` sa píše v tej istej jednotke.
- 5: súhlas s (a)/(b), ale „1 tick“ nie je oprava, keď default bol viac než 1 tick (napr. `slBufferTicks` 2 → 1). Zapísať ako odchýlku.
- 6: súhlas. `default_timeframe` a domovský trh patria sem.

## 2. Oprava koordinátora (build.py, ZAKLAD_*.json) — chyby
- **A1 `pct` mení logiku.** `resolve(price=bar.close)` dáva prah, ktorý sa hýbe s cenou. Predloha má prah pevný v cene. BTC v L 2019–2022 išiel ~4k→69k, takže prah sa pohne ~17×. ES 2015–2025 ~3×, 6E ±12 %. Vzniká iná stratégia, nie základ. Pevný ekvivalent existuje: `{"value": nv/tick, "unit": "ticks"}`. Jednotka je iná než Pine, takže `_generic_problems` rozsah Pine preskočí (rovnako ako pri `pct`) a cena ostane pevná. **`pct` zamietam, nahradiť `ticks`.**
- **A2 Chyba vetvenia pre polia `ticks`.** Podmienka `unit == "abs" and lo<=nv<=hi` posiela **každé** pole s jednotkou `ticks` nad 1 tick do `pct`, aj keď je v rozsahu. Príklad: `imbMaxDistTicks` na ES, MGC, MYM aj BTC je `pct`, hoci ES vychádza ~18 tickov. Má to byť `round(nv/tick_inst)` v `ticks`.
- **A3 Bodové polia mimo SIZE_FIELDS sa neprepočítali vôbec.** Overil som to na 154 configoch: `slPoints`/`maxSlPoints` (tks rodina ~13–15), `targetPoints` (orb15, mtkorb: 40 b.), `trailActivatePoints`/`trailBufferPoints` (flashorb: 50/20), `vaMin/MaxPoints`, `slBufferTicks` (nyvaes), `imbMaxDistTicks`/`st2ConfTicks`/`slBufTicks`/`maxRiskTicks`/`minGap`/`maxDist` (mtkzone), `slTicks` (m2), `rowTicks`/`vpRowTicks` (svp, asiasweep). `tks/ZAKLAD_6E` nemá žiadny prepočet, takže `slPoints` = 40 EUR. Dnes nič nerobí (default `slMode=swing`), ale v mriežke ožije. Na 6E/BTC je to fatálne, na ES ~5× mimo. Treba buď presunúť pole do SIZE_FIELDS (s paritou), alebo prepočítať podľa mena poľa so zoznamom v hlavičke, alebo zapísať „netestovateľné bez zmeny kódu“.
- **A4 Domovský trh = MNQ pre 154/154 je fallback, nie zistenie.** Heuristika `copy` nikdy nezabrala. Treba ručný zoznam domovov s odkazom na Pine/zadanie (hlavne …btc, …mgc, …eur, ktorých defaulty mohli vzniknúť na inom trhu).
- **A5 TF:** jeden `_timeframe` pre všetkých 6 trhov. Ak vznikol ladením na MNQ, je to ladený parameter (bod 6). Pri 24h trhoch (6E, BTC) sa limity `*MaxBars` v baroch na inej seanse správajú inak. Zapísať to, nemeniť.
- **A6 ATR/cena z rôznych kalendárov** (MNQ 2019–22, ES 2015–25, MGC 2023–25): pomer mieša režimy. Zapísať pomer a obdobie do `_comment` každého profilu.
- Drobnosť: `round(nv, 6)` a abs prahy pod 2 ticky (`pbMinRangePoints` 6E = 1,28 ticku) nie sú zarovnané na tick.

## DOHODA (prijímam toto znenie kroku 3a)
Body 1–4 a 7 podľa B. Bod 5 a 6 takto:
**5′.** Prepočet ZAKLAD_<M> = hodnota × ATR_M/ATR_domov a zapisuje sa **v pevnej cene trhu M**: abs v rozsahu Pine ako abs, inak `ticks` (round, min 1). Polia `ticks` sa zapisujú v tickoch M. **`pct` ani `atr` nie sú povolené** (menia logiku). Ak sa hodnota zaokrúhli na 1 tick nad prepočet o viac než 50 %, je to odchýlka, ktorá ide do `_comment` a do hlavičky. Bodové a tickové polia mimo SIZE_FIELDS sa prepočítajú rovnako podľa zoznamu polí v hlavičke. Ak sa nedajú prepočítať bez zmeny kódu, trh M je pre hypotézu „netestovateľný bez zmeny kódu“ (nie ❌). Orezaný alebo neprepočítaný profil v bráne neplatí.
**6′.** Podľa B, a k tomu: domovský trh každej stratégie je v ručnom zozname s dôkazom (Pine/zadanie/git). Fallback MNQ bez dôkazu = hypotéza „zo štúdie“. `_timeframe`, pomer ATR a obdobia ATR sa zapisujú do hlavičky.
Kým sa nepregenerujú profily podľa 5′ (A1–A3), ZAKLAD_* okrem MNQ **nie sú platné východisko**.
