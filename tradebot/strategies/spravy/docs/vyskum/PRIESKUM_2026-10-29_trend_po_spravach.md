# Trend po červených správach (USA) — prieskum 29. 10. 2026 (MacBook)

**Dáta:** udalosti z `tester/calendar_us.json` (2021–2026, odpísané z federalreserve.gov a bls.gov):
FOMC 14:00 NY (46), CPI 8:30 (≈68), NFP 8:30 (≈66). Sviečky 1m MNQ, ES, MGC (Databento). Poplatok smernice.
Ostatné červené správy (PPI, Retail Sales, ISM, PCE, GDP, JOLTS, Powell) chýbajú, lebo FF exportuje len aktuálny týždeň.
Skripty sú v `skripty/` (news_study, news_fade, news_mgc, news_leg2).

## Hlavné zistenia
| trh | správa | čo sa deje | čísla |
|---|---|---|---|
| **MGC** | **FOMC** | **trend pokračuje** — smer 14:00 → 15:00 drží ďalšie 1–8 h | PF 2,0–3,3 vo všetkých variantoch okolia, 5–6 / 6 rokov v pluse, t ≈ +1,5 až +2,1 (n = 46, ~8 za rok) |
| MGC | CPI / NFP | trend nepokračuje; veľký prvý pohyb (≥ 0,3 ATR dňa) sa skôr vráti do 2–4 h | fade PF 1,5–2,1, t ≈ +1,4 až +2,3, 4–6 / 6 rokov, n = 44–84 |
| MNQ | CPI / NFP | **prvý pohyb sa otočí** (fade), nie trend | vstup o 8:45 proti smeru 8:30–8:45, výstup o 1–2 h: PF 2,0–2,1, **6 / 6 rokov**; t = −3,4 v event study |
| ES | CPI / NFP | to isté ako MNQ, slabšie | fade PF 1,35–1,53 |
| MNQ, ES | FOMC | nič jednoznačné | — |

Kontrola: v rovnakých časoch v dni bez správ sa nič také nedeje (pokračovanie 48–51 %, t pod 2), takže je to vlastnosť správ.

## Pozor
- Udalostí je málo (FOMC 8 za rok, CPI+NFP 24). Na samostatnú stratégiu podľa smernice (150 obchodov za rok) to nestačí. Hodí sa ako **modul** k iným stratégiám alebo ako samostatný „správový“ účet.
- Variant sme skúšali veľa (pri MGC 144 na každú správu). Preto platí len to, čo drží v celom okolí a po rokoch: MGC FOMC trend a MNQ CPI/NFP fade.

## Návrh stratégie „SPRÁVY“
- **MGC FOMC trend:** o 15:00 NY vstup v smere 14:00 → 15:00, stop 2 × prvý pohyb za vstupom, výstup po 2–4 h (alebo trailing).
- **MNQ CPI/NFP fade:** o 8:45 NY vstup proti smeru 8:30 → 8:45, stop 1,5–2 × prvý pohyb, výstup 9:45–10:45.
- Rozšíriť kalendár o PPI, Retail Sales, ISM, PCE a GDP z oficiálnych rozpisov (BLS, Census, ISM, BEA). Zlato na ne reaguje tiež a vzorka sa zväčší niekoľkonásobne.

---

# Zlato (MGC) po všetkých červených správach USA — 29. 10. 2026

**Kalendár rozšírený na 12 typov správ** (`skripty/news_events.py`, 2021–2026):
- FOMC, CPI, NFP;
- PPI a JOLTS (z bls.gov);
- Retail Sales, PCE a GDP (z ALFRED, bez dní revízií);
- ISM výroba a služby (1. a 3. pracovný deň o 10:00);
- zápisnica FOMC (+21 dní) a Claims (štvrtok 8:30).

Keď vyjde viac správ naraz, udalosť patrí najsilnejšej z nich.

**Ako sa rozbehne trend a či pokračuje.** Smer prvej nohy po správe a jeho pokračovanie 1–4 h, 24 variantov na každú správu (`news_gold.csv`):

| správa | medián PF variantov | podiel variantov s PF > 1 | čo to znamená |
|---|---|---|---|
| **FOMC** | **2,11** | **100 %** | trend sa rozbehne a pokračuje |
| **PCE** | **1,51** | 80 % | trend pokračuje (noha 15 → 60 min, potom 2–4 h: PF 2,7, t = +2,6) |
| GDP | 1,28 | 75 % | slabý trend |
| NFP | 1,18 | 71 % | slabý trend |
| ISM výroba / služby | 1,11 / 0,94 | ~50 % | nič |
| Claims, zápisnica FOMC, Retail | 0,82–0,86 | 33–38 % | skôr návrat |
| **CPI** | **0,76** | 12 % | **prvý pohyb sa vráti** |
| **JOLTS** | **0,58** | 25 % | návrat |
| **PPI** | **0,49** | 10 % | **silný návrat** |

**Kombinácie po rokoch (21 · 22 · 23 · 24 · 25 · 26):**
- **TREND FOMC + PCE** (~19 obchodov za rok): smer 15 → 60 min po správe, držať 4 h. PF **2,95**, t = +3,0, 5/6 rokov (1,52 · 1,36 · 0,56 · 5,22 · 3,07 · 8,85).
- **FADE CPI + PPI + JOLTS** (~32 obchodov za rok): proti smeru prvých 60 min, držať 1 h. PF **1,61**, t = +2,1, **6/6 rokov** (2,48 · 1,24 · 1,10 · 1,64 · 1,56 · 1,79).
- Obe spolu dávajú ~50 obchodov za rok, jeden obchod najviac v deň správy.

**Pozor:** skupiny som vybral až po pohľade na výsledky (14 typov × 24 variantov), takže čísla sú optimistické. Dáva to aj ekonomický zmysel: rozhodnutie Fedu a ním sledovaná inflácia (PCE) menia očakávanú politiku, a to je trend. Prvá reakcia na CPI/PPI býva prehnaná a vráti sa. Overenie: rozhodnúť skupiny na 2021–2024 a pustiť raz na 2025–2026, potom stratégia v repozitári a smernica.

## Raketa a odložené obdobie (FOMC + PCE trend, MGC) — 29. 10. 2026
Vstup o T+60 v smere T+15 → T+60. Stop za druhým extrémom tejto nohy (+0,1 ATR). Výsledok v R. Ladenie 2021–2024, odložené 2025–2026 (raz).
- **Ladenie:** najlepšie PF ~1,5 (4 h držanie alebo trailing 0,5–1 ATR, vychádza takmer rovnako), 2022 a 2023 pod 1. Medián všetkých 40 variantov je 0,96.
- **Odložené 2025–26:** víťaz ladenia PF **3,49** (+0,60 R na obchod, 2 rakety ≥ 3 R, najväčšia +5,5 R). Medián všetkých variantov je 2,03.
- **Nie je to len rast zlata:** v 2025–26 zarábajú aj shorty (PF 2,18). FOMC drží v oboch obdobiach (PF 2,60 → 3,47). PCE bolo pri ladení slabšie (1,23), v odloženom období silné (3,30).
- **Rakety:** trailing ani dlhšie držanie (8–48 h) veľké pohyby lepšie nechytí. Zisk robí veľa stredných výhier, rakety ≥ 3 R sú 1–2 za obdobie.

## Stav 29. 10. 2026
- Stratégia **SPRÁVY** je v repozitári a pushnutá (commit 0e9d8191a): Python `spravy` (ZLATO › TRENDOVÉ) a C# jadro `spravynet` (ZLATO › LIVE — dá sa nasadiť cez NinjaTrader / MT5 / most).
- Profily: `mgc_databento_5m` (1 kontrakt) a `mgc_databento_5m_riziko500` (riziko 500 $ na obchod, parameter `riskDollar`).
- Časy: kalendár v čase New York, prevod na UTC pre každý deň zvlášť; zobrazenie v slovenskom čase (Europe/Bratislava). Parita C# = Python overená aj cez posun času.
- Mac mini dostal príkaz (MACMINI-PRIKAZY/PRIKAZY.md): nahrať SPRÁVY na stránku výsledkov ako výnimku z pravidla 150 obchodov za rok.
- Ostáva: kalendár na rok 2027; porovnanie s pluginom ForexFactory na hube (presunutá / chýbajúca správa).
