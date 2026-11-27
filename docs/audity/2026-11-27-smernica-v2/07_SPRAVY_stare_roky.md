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
