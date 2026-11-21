# SPRÁVY — progres (október 2026)

## 29. 10. 2026 (MacBook)
1. Prieskum MGC, MNQ, ES po FOMC, CPI, NFP → zlato: FOMC trend pokračuje, MNQ: CPI/NFP sa otáča (`vyskum/PRIESKUM_…`).
2. Kalendár rozšírený na 12 typov správ 2021–2026 (FOMC, zápisnica, CPI, NFP, PPI, JOLTS, RETAIL, PCE, GDP, ISM výroba/služby, CLAIMS).
3. Stratégia **SPRÁVY** (Python `spravy` + C# jadro `spravynet`), časy cez America/New_York pre každý deň, zobrazenie v čase Europe/Bratislava,
   opravy kalendára cez profil (`newsAdd`, `newsSkip`), riziko na obchod (`riskDollar`, `sizeMinRisk`). Parita C# = Python aj cez posun času. Analytika 5/5 okien v zisku, +3,6 sigma.
   **Commit 0e9d8191a, pushnuté.**
4. Mac mini: príkaz s výnimkou z pravidla 150 obchodov za rok → nahrať SPRÁVY na stránku výsledkov.
5. Séria **kedy vstúpiť** (5/10/15/30/45/60 min, TREND a FADE zvlášť, 60 behov v histórii webapp, poznámka „SPRAVY vstup: …“):
   FADE najlepšie po 45–60 min, TREND s nohou od T nefunguje v starších rokoch → profil (T+15 → T+60) ostáva.
6. **Výskum správania MGC po správach** (`vyskum/VYSKUM_SPRAVANIE_MGC_2026-10-29.md`): drift pred FOMC sa otáča, tlačovka pokračuje, PPI sa vracia.
7. **SPRÁVY 3.0** (commit 2394a2cee, pushnuté): namiesto skupín TREND / FADE 8 pravidiel po správach (aj pred správou, vstup neskôr ako koniec nohy),
   12 prepínačov, ktoré správy obchodovať, RRR pri každom pravidle. Overenie každého pravidla samostatne a celku (FOMC PRED do 16:55 lepší ako PRED + tlačovka).
   Test RRR (125 behov): pri FOMC a PCE cieľ škodí, pri PPI 1 : 3 so stopom za extrémom 5 / 5 okien → **RRR predvolene len PPI** (rozhodnutie používateľa).
   Výsledok PF 1,34 · 1,09 · 1,49 · 1,86 · 3,97, +11 114 $. Parita C# = Python (10 variantov + MGC), 2 498 testov prešlo, analytika +4,8 sigma.
8. Kalendár: kontrola na 1m MGC (výbuch volatility presne v čase správy) a proti ForexFactory — sedí. Doplnený rok 2027 (FOMC, CPI, NFP, PPI, ISM, CLAIMS); test pripomenie koniec.
9. 283 behov výskumu pushnutých do histórie (commit 950b69f0b).

## 29. 10. 2026 večer (Mac mini)
10. Základná sada testov 3.0 (20 variantov MGC + 6 XAU, natívne C#) a robustnosť: 2× poplatok 2,16, o sviečku neskôr 1,99, DSR 0,959 — všetko prešlo. Výsledky `vyskum/TESTY_MACMINI_2026-10-29.md`.
11. **Ladenie naplánované** (používateľ: štart 22:00, do nedele 1. 11. 18:00, ráno 6:00 priebežne, kritérium PF — „nezabi PF“):
    `.nightsearch/spravy/ladenie.py` — A) každé pravidlo samostatne (trend aj fade, 3 seedy, PF najhoršieho zo 4 okien, plató),
    aj FOMC dvojica pred správou + trend cez noc; B) nové pravidlá (NFP, GDP, ISM, RETAIL, CLAIMS, zápisnica; drift pred CPI/NFP/PCE/PPI);
    C) skladanie po jednom — prijaté len keď PF spolu ≥ 3.0 a najhoršie okno sa nezhorší, pravidlo musí držať odložený rok (≥ 70 % ladenia);
    D) slBuffer, minLeg, atrLen; E) XAU, robustnosť, DSR. Výsledky ráno do `vyskum/LADENIE_<dátum>.md`.
    Do repa pribudlo kritérium hyperoptu `pf` (commit „Pridaj kritérium hyperoptu pf…“).
12. Prieskum na grafe (večer): FOMC trend 15 → 60, vstup 15:00 NY, **držať cez noc (600–1080 min)** — najhoršie okno 1,04–1,27, PF 2,1–2,9;
    dnes ho blokuje FOMC pred (drží do 16:55) → ladí sa ako dvojica. Dlhšie držanie CPI / PCE škodí.
13. **Ladenie spustené 29. 10. o 21:51** (na pokyn používateľa skôr ako 22:00), celé na Mac mini (natívne C#): etapa A (pravidlá 3.0) a B (nové pravidlá)
    bežia naraz, potom C (skladanie), D (spoločné parametre), E (XAU, robustnosť). Hub: jediný prijímajúci agent srvnas je kontajner bez Mono,
    natívny C# hyperopt tam padá — ostatní agenti majú prijímanie vypnuté. Ráno 6:00 výsledky do `vyskum/LADENIE_<dátum>.md` a na stránku výsledkov.

## 30. 10. 2026 (Mac mini) — kolo 2 a 3: cieľ PF ≥ 3 v čo najviac rokoch, riziko 300–500 $
14. Kolo 2: všetky kombinácie pravidiel z ladenia (2 302 × 5 okien) + doplnky (zápisnica FOMC proti, GDP v smere) + veľkosť z rizika.
15. Kolo 3: hľadanie pravidiel pre CPI, PCE, NFP, RETAIL, CLAIMS, ISM výroba (1500 epoch, 3 seedy) a doplnenie: NFP pred správou proti, PCE v smere.
16. Finalisti (profily `SPRAVY_KOLO2_*`, `SPRAVY_KOLO3_*` vo webapp, behy na hube aj Mac mini, na stránke výsledkov):
    - KOLO2_2: 4 pravidlá (PPI, JOLTS, ISM služby, GDP), riziko 500 $ (medián 404 $), PF ≥ 3 všetky roky (3,05–7,38), 36 obch/rok, WR 72 %, +21 736 $ / 5 r.
    - KOLO2_1: 6 pravidiel, riziko 500 $ (medián 280 $), PF 4,03, najhorší rok 2,80, 48 obch/rok, +18 893 $.
    - KOLO3_2: 8 pravidiel, 1 kontrakt (medián rizika 78 $), PF ≥ 3 všetky roky (3,03–4,42), 74 obch/rok, WR 64 %.
    - KOLO3_1: 8 pravidiel, riziko 500 $, PF 3,19, najhorší rok 2,32, 69 obch/rok, +58 579 $ / 5 r., DD 1 344 $.
    Robustnosť kola 2: 2× poplatok aj o sviečku neskôr PF 3,6–4,8 všetky roky. Pozor: výber kombinácií videl aj posledný rok.

## 17. Slepý výber (30. 10. 2026 večer)
Zopakovaný výber kôl 2 / 2c / 2d / 3 len na 4 rokoch ladenia (skript `.nightsearch/spravy/slepy.py`, výsledok `out/slepy.json`).
- PROFIL 1 (C_193) by slepý výber našiel ako 6. z 2302 kombinácií; odložený rok 3,18. Slepá veľkosť M4 by dala 3,26.
- PROFIL 2 (A_266) slepý výber nenašiel — namiesto neho by pridal CPI/PCE pred správou a tá kombinácia má odložený rok **0,95**.
- Kolo 3: filter len na IS pustí 36 doplnkov namiesto 4; ich odložený rok 1,36–3,21 (medián ~2,4).
- Záver: PROFIL 1–4 jednotlivo odloženým rokom prešli, ale celý postup výberu bez odloženého roku by dal odložený PF okolo 2–3 a raz pod 1. Realistické očakávanie naživo PF ~2–2,5, nie 3–4. Forward test nutný.
