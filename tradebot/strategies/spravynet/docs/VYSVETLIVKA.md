# SPRÁVY 3.0 (C# jadro) — ako funguje

C# jadro `spravynet` robí bar po bare to isté ako Python predloha `spravy` (parita `tester/tests/test_csharp_parity_spravy.py`); nasadenie cez NinjaTrader 8 alebo MetaTrader 5.

> V jednej vete: každá červená správa USA má na zlate vlastné pravidlo — pred FOMC sa ide proti tomu, kam zlato išlo hodinu pred správou, po PCE v smere pohybu, po CPI, PPI a JOLTS proti prvému pohybu, lebo ten sa zvykne vrátiť.

Výskum 29. 10. 2026 na MGC 2021–2026, 12 typov červených správ USA. Podklady sú v iCloude `SPRAVY/` (výskum `vyskum/VYSKUM_SPRAVANIE_MGC_2026-10-29.md`).

## Verzie
| verzia | dátum | čo priniesla |
|---|---|---|
| 1.0 | 29. 10. 2026 | spoločné skupiny TREND (FOMC, PCE) a FADE (CPI, PPI, JOLTS) |
| 2.0 | 29. 10. 2026 | medzikrok, nevydaný: pravidlá po správach a prepínače, bez cieľa |
| **3.0** | 29. 10. 2026 | 8 pravidiel po správach, prepínače, ktoré správy obchodovať, FOMC pred správou, cieľ RRR pri každom pravidle (predvolene len PPI 1 : 3), kalendár 2027 |

## Kedy sú správy (slovenský čas)
Správy vychádzajú v čase **New York**. U nás sú bežne o **6 hodín neskôr**. V týždňoch, keď USA a Slovensko menia čas
v iné dni, je rozdiel **5 hodín**: v marci (USA druhú marcovú nedeľu, my poslednú) a na prelome októbra a novembra
(my poslednú októbrovú nedeľu, USA prvú novembrovú).

| správa | New York | Slovensko bežne | Slovensko v týždňoch posunu |
|---|---|---|---|
| FOMC (rozhodnutie Fedu) | 14:00 | 20:00 | 19:00 (napr. 28. 10. 2026) |
| CPI, PPI, PCE, NFP, GDP, Retail | 8:30 | 14:30 | 13:30 |
| JOLTS, ISM | 10:00 | 16:00 | 15:00 |

Stratégia počíta v UTC, takže na čase platformy nezáleží. Štítky na grafe ukazujú čas **SK aj NY**.

## Ktoré správy sa obchodujú
Skupina **✅ Obchodované správy** má prepínač pre každý z 12 typov. Pravidlo platí len pre zapnutú správu, takže vypnutím
napr. CPI zmizne každý obchod po CPI bez toho, aby si menil pravidlá. Zapnuté sú FOMC, CPI, PPI, PCE a JOLTS.

## Pravidlá (📰 Pravidlo 1 – 8)
Každé pravidlo má: **správu**, **režim** (trend = v smere nohy, fade = proti), **nohu od – do** (minúty od správy; záporné = pred
správou), **vstup** (T + minúty; najskôr na konci nohy), **držanie** (minúty od vstupu), **stop** (× noha; 0 = za extrémom nohy) a **RRR** (cieľ 1 : N v násobkoch rizika; 0 = bez cieľa).
Keď cena cieľ nedosiahne, obchod sa zavrie po čase držania.
Jedna správa môže mať viac pravidiel; obchod je vždy len jeden naraz.

| # | správa | čo robí | noha | vstup | výstup | RRR | prečo (výskum 29. 10.) |
|---|---|---|---|---|---|---|---|
| 1 | FOMC | **PRED** — proti pohybu hodinu pred správou | −60 → 0 | 14:00 NY (19:00 / 20:00 SK) | 16:55 NY | bez cieľa | v 70 % ide správa proti driftu pred ňou |
| 2 | *(vypnuté)* | tlačovka FOMC v smere 14:00 → 14:25 | 0 → 25 | 14:30 NY | 16:55 NY | bez cieľa | zapni výberom FOMC; prvé okno potom PF 0,95 |
| 3 | CPI | FADE — proti prvej hodine | 0 → 60 | T + 60 | po 1 h | bez cieľa | prvá hodina sa v druhej vracia |
| 4 | PPI | FADE — proti prvým 15 min, stop za extrémom | 0 → 15 | T + 15 | po 3 h | 1 : 3 | 88 % sa vráti na cenu pred správou |
| 5 | PCE | TREND — v smere nohy | 15 → 60 | T + 60 | po 4 h | bez cieľa | prvých 15 min sa preskočí (výstrel sa vracia) |
| 6 | JOLTS | FADE — proti prvej hodine | 0 → 60 | T + 60 | po 1 h | bez cieľa | |
| 7, 8 | *(voľné)* | | | | | bez cieľa | |

- **Stop:** pri CPI, JOLTS a FOMC PRED len poistka 10 × noha (tesný stop návrat vyberie), pri PPI a TREND za opačným koncom nohy + 1 ATR.
- **RRR (test 29. 10., každé pravidlo samostatne, 5 okien):** pri FOMC a PCE cieľ odreže veľké pohyby (FOMC bez cieľa +3 922 $, s 1 : 2 +3 019 $),
  pri PPI so stopom za extrémom a 1 : 3 zisková v 5 z 5 okien (bez cieľa 4 / 5) a menší prepad, pri CPI a JOLTS 1 : 2 nastejno alebo mierne lepšie. Predvolene má cieľ len PPI (rozhodnutie 29. 10.), ostatné ho majú 0 — zapneš ho vo formulári.
- **Veľkosť:** pevný počet kontraktov (profil 1 MGC), alebo riziko na obchod (`riskDollar`, profil `…_riziko500`).
- **Overenie 29. 10.** (MGC 5m, 1 kontrakt, päť okien): PF 1,34 · 1,09 · 1,49 · 1,86 · 3,97, 276 obchodov, +11 114 $
  (bez RRR 1,22 · 1,16 · 1,40 · 1,42 · 5,06, +10 954 $; RRR aj pri CPI a JOLTS 1,34 · 1,12 · 1,49 · 1,86 · 3,97, +11 155 $; SPRÁVY 1.0: 1,19 · 1,06 · 2,27 · 2,13 · 3,20, +9 050 $).
- Staré profily a behy 1.0 (`trendEvents`, `fadeEvents`, `tpR`, …) sa načítajú, staré polia sa ignorujú — beží na nich 2.0.

## Kalendár
- Je v balíku (`calendar.json`), termíny sú z federalreserve.gov, bls.gov a ALFRED. Raz za rok sa doplní ďalší rok
  (test `test_kalendar_pokryva_buducnost` začne padať 21 dní pred posledným termínom niektorej správy).
- Kontrola 29. 10.: na 1m MGC je výbuch volatility presne v čase správy pri 100 % FOMC a NFP, 99 % CPI, žiadna správa nie je o hodinu posunutá.
- Presunutú alebo zrušenú správu (napr. pri shutdowne) opravíš v profile bez zmeny kódu: `newsAdd` = „2026-11-26 08:30 PPI“,
  `newsSkip` = „2026-11-13 PPI“.

## Slovníček
- **FOMC** — zasadnutie Fedu, ktoré rozhoduje o úrokoch. **PCE** — inflácia, ktorú Fed sleduje najviac.
- **CPI / PPI** — inflácia spotrebiteľských / výrobných cien. **JOLTS** — voľné pracovné miesta.
- **Noha** — pohyb ceny v určenom čase okolo správy (napr. od 15. do 60. minúty po nej, alebo hodinu pred ňou).
- **PRED** — pravidlo, ktorého noha celá leží pred správou; obchod sa otvorí v čase správy.
- **Fade** — obchod proti prvému pohybu, so stávkou, že sa vráti.
