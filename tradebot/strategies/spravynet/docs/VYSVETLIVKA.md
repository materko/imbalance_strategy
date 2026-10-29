# SPRÁVY 1.0 — ako funguje

> V jednej vete: po rozhodnutí Fedu (FOMC) a inflácii PCE sa na zlate ide v smere, ktorý trh nabral v prvej hodine, a po CPI, PPI a JOLTS proti prvému pohybu, lebo ten sa zvykne vrátiť.

Prieskum 29. 10. 2026 na MGC 2021–2026, 12 typov červených správ USA. Podklady sú v iCloude `SPRAVY-FOREXFACTORY`.

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

## Obchod
- **TREND** (FOMC, PCE): pohyb od 15. do 60. minúty po správe určí smer a vstúpi sa trhom v jeho smere. Stop je za
  opačným koncom tohto pohybu, výstup po 4 hodinách.
- **FADE** (CPI, PPI, JOLTS): pohyb prvých 60 minút po správe sa obchoduje opačne. Výstup po 1 hodine, stop len ako
  poistka (10 × veľkosť pohybu). Tesný stop trh pri návrate vyberie.
- Na jednu správu je jeden obchod. Kým beží predošlý, nový sa nezačne.
- **Veľkosť:** pevný počet kontraktov (profil 1 MGC). Veľkosť počítaná z rizika by pri tesnom stope nafúkla pozíciu.

## Kalendár
- Je v balíku (`calendar.json`), termíny sú z federalreserve.gov, bls.gov a ALFRED. Raz za rok sa doplní ďalší rok.
- Presunutú alebo zrušenú správu (napr. pri shutdowne) opravíš v profile bez zmeny kódu: `newsAdd` = „2026-11-26 08:30 PPI“,
  `newsSkip` = „2026-11-13 PPI“.

## Slovníček
- **FOMC** — zasadnutie Fedu, ktoré rozhoduje o úrokoch. **PCE** — inflácia, ktorú Fed sleduje najviac.
- **CPI / PPI** — inflácia spotrebiteľských / výrobných cien. **JOLTS** — voľné pracovné miesta.
- **Noha** — pohyb ceny v určenom čase po správe (napr. od 15. do 60. minúty).
- **Fade** — obchod proti prvému pohybu, so stávkou, že sa vráti.
