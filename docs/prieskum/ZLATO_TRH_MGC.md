# Zlato (MGC) — ako trh funguje, čo dodržiava, čo nie (MacBook, 21. 10. 2026)

Podklad na skladanie stratégií na MGC. **(A)** rešerš z internetu, **(B)** naše merania na **1m Databento MGC** (len kvalitné dni,
viď B0) vedľa **MNQ** z toho istého zdroja, **(C)** čo z toho plynie a čo odporúčam stavať, **(D)** ako to zopakovať.
Skripty: `skripty_trh/` (najprv `python qa.py MGC` a `python qa.py MNQ`, potom `g1.py` … `g4.py`; na Mac mini sa repo `~/IBS` nájde samo).

---

## A. Rešerš (internet)
- **Kontrakt MGC:** 10 oz, tick 0,10 $ = **1 $** na kontrakt (GC = 100 oz, tick 10 $; MGC sa vyrovnáva podľa GC). Globex ne 18:00 – pi 17:00 ET,
  denná prestávka **17:00–18:00 ET**. Mesiace: aktívne **február, apríl, jún, august, december** (október je základný, nie aktívny);
  ukončenie obchodovania tretí posledný pracovný deň mesiaca dodania; obchodníci **rolujú 1–2 dni pred prvým dňom oznámenia (FND)**,
  lebo GC je fyzicky dodávaný. → Pri backteste vyhodiť dni rolovania (náš archív ich má v `MGC_USD-1m.rolls.json`).
- **Kľúčové časy (ET):** 18:00 otvorenie (Ázia), ~20–21 h Šanghaj (SGE), 3:00 Londýn, **LBMA Gold Price aukcie 10:30 a 15:00 Londýn
  = ~5:30 a ~10:00 ET** (pri rozdielnom letnom čase o hodinu inak), **8:20 otvorenie COMEX pit / 8:30 makro dáta USA**, 9:30 akcie,
  13:30 koniec hlavnej seansy COMEX, 14:00 FOMC.
- **Čo hýbe zlatom:** reálne úroky (výnos dlhopisov mínus inflácia z TIPS) a dolár — horúce CPI / NFP / jastrabí Fed = vyššie reálne úroky
  = zlato dole a naopak; pri FOMC rozhoduje skôr výhľad ako samotné rozhodnutie. Okolo správ prudké výkyvy a otočky. Od 2025–26
  často prebíja tento kanál geopolitika (útočisko) a nákupy centrálnych bánk.
- **Ázia vs USA:** viacero zdrojov (diplomová práca CBS, komentáre 2026) tvrdí, že zlato **rastie počas ázijských hodín a klesá v amerických**;
  akademické štúdie COMEX sa nezhodujú v znamienku noc vs deň (závisí od obdobia). Naše dáta: viď B3.
- **London Fix:** štúdia Abrantes-Metz (2014) našla podozrivé (väčšinou poklesové) pohyby okolo popoludňajšieho fixu 2004–2013; od 2015
  je fix elektronická aukcia ICE, novšie dôkazy chýbajú.
- **Stratégie:** rigorózny dôkaz, či na zlate cez deň funguje trend alebo návrat, chýba. Akademicky: momentum prvej polhodiny na čínskych
  kovových futures (staré dáta); praktici tvrdia, že zlato robí presvedčivé prierazy, ktoré sa za pár hodín otočia (zlé pre trendové
  systémy), a že backtesty zlata klamú, ak nepokryjú obdobie, ktoré stratégiu zabije → testovať na viacerých režimoch.

## B. Naše merania (MGC a MNQ, Databento 1m, 2020 – 2026/09)

### B0. Kvalita dát — POZOR
| rok | minút / deň (medián, max ~1380) | ploché sviečky | % dní, ktoré prejdú kontrolou |
|---|---|---|---|
| 2010–2016 | 66–700 | 49–83 % | 0–1 % |
| 2017–2018 | 746–902 | 49–53 % | 0 % |
| 2019 | 1 230 | 30 % | 49 % |
| **2020–2026** | 1 355–1 380 | 0–8 % | **90–98 %** |
**MGC pred rokom 2019 je nepoužiteľné** (mikro kontrakt sa takmer neobchodoval), 2019 polovičné. Všetko nižšie je len 2020 – 2026/09 a len dni,
ktoré prejdú kontrolou (≥ 1 100 minút, < 30 % plochých sviečok, žiadny skok > 1 % za minútu, nie deň rolovania). Pozor: náš skorší prieskum
(`PRECITAJ_MA.md`, 21. 10. ráno) bral aj 2017–2018 — tie roky sú zlé; profily z víkendového hľadania (roky 21/22–25/26) sú na dobrých dátach.

### B1. Veľkosť pohybov
| | p10 | p25 | **medián** | p75 | p90 |
|---|---|---|---|---|---|
| MGC celý deň (body) | 16 | 21 | **30** | 48 | 86 |
| MGC celý deň (%) | 0,80 | 1,05 | **1,42** | 1,93 | 2,63 |
| MGC COMEX 8:20–13:30 (body) | 10 | 14 | **21** | 32 | 51 |
| MGC COMEX (%) | 0,54 | 0,69 | **0,94** | 1,29 | 1,77 |
| MNQ celý deň (%) | 0,88 | 1,21 | 1,74 | 2,46 | 3,30 |
Po rokoch (medián dňa, body / %): 2020 28 / 1,57 · 2021 22 / 1,22 · 2022 24 / 1,33 · 2023 22 / 1,10 · 2024 31 / 1,27 · **2025 52 / 1,57 · 2026 103 / 2,27**
— v bodoch sa rozpätie od 2024 zdvojnásobilo (cena 1 520 → 4 520) → **všetky prahy v ATR alebo %, nie v bodoch.**
Dni v týždni: po 1,36 % · ut 1,42 · st 1,35 · št 1,44 · **pi 1,47** (piatok najväčší, NFP).

### B2. Kedy sa zlato hýbe a kedy sa obchoduje
- **Aktivita (rozpätie 5m sviečky, 100 = priemer):** 8 h **156** · 9 h **179** · 10 h **173** · 11 h 130 · 12 h 101 · 13 h 94 · 14 h 88 · 15 h 82 · 16 h 58 ·
  18 h 88 · 19 h 73 · 20 h 100 · 21 h **110** · 22 h 84 · 23 h 67 · 0 h 67 · 1 h 86 · 2 h 96 · 3 h **103** · 4 h 96 · 5 h 87 · 6 h 87 · 7 h 96.
- **Objem (podiel dňa):** 8 h 8,1 % · **9 h 11,0 % · 10 h 10,8 %** · 11 h 7,0 % · 12 h 4,7 % · Ázia 20–21 h 4,1–4,8 % · Londýn 2–4 h ~3,5–3,8 %/h;
  najtichšie 16–19 h a 23–1 h. **8:00–11:00 ET = ~30 % denného objemu.** (MNQ: 9–11 h = 31 %, Ázia skoro nič.)
- **High / low dňa:** 10 % pri otvorení 18 h, 8–9 % v každej z hodín 8, 9, 10 h; inak rozptýlené. (MNQ: 15–16 h 22 %.)
- **Seansy (2020–26, súčet výnosu):** Ázia 18–3 h **+47 %** · Londýn 3–8:20 +15 % · COMEX 8:20–13:30 **−17 %** · poobede 13:30–17 +20 %.
  Po rokoch Ázia: +9,6 · +5,5 · −9,9 · +3,2 · +4,0 · +17,6 · +17,0 % (**6/7 rokov v pluse**); COMEX: −1,8 · −4,0 · +1,4 · −4,7 · −5,8 · +2,9 · −5,1 % (5/7 v mínuse).
  → „Ázia kupuje, USA predáva“ v dátach je, ale časť je rast zlata; samostatne testovať (C4).

### B3. Trend alebo návrat
| | variance ratio celý deň 5/15/30/60 min | v hlavnej seanse | 1. polhodina seansy → zvyšok | ORB 30 min seansy: +1R pred opačnou stranou | Londýn ORB 3:00 | prieraz rangu Ázie |
|---|---|---|---|---|---|---|
| **MGC** | **0,94 / 0,93 / 0,93 / 0,94** | 0,97–0,99 | +0,013 | 56 % | 56 % | 53 % |
| MNQ | 1,00 / 1,00 / 1,00 / 0,99 | 0,98–1,01 | +0,051 | 57 % | 54 % | 51 % |
- **Zlato je mierne návratové** (VR < 1 na všetkých horizontoch, najmä mimo COMEX); momentum dňa takmer žiadne. Prierazy rangov
  dosiahnu 1R pred opačnou stranou v 53–56 % — s nákladmi takmer nula (náš skorší test ORB / NOA na MGC: PF < 1).
- **VWAP COMEX seansy:** po prvej odchýlke o 1 / 2 / 3 sd sa cena v tej istej seanse vráti k VWAP v **95 / 89 / 75 %** (MNQ 92 / 82 / 68 %)
  → zlato sa k VWAP vracia častejšie ako Nasdaq. Pozor: skorší test „fade od VWAP so stopom 1 sd“ prerobil (cena často ide najprv ďalej) —
  použiteľné len s širokým stopom / časovým výstupom, treba otestovať.
- **Noc po červenej COMEX seanse:** +7,9 bps vs +6,2 po zelenej → filter červeného dňa na zlate takmer nič (na MNQ 9,7 vs 3,3).
- **Nedeľný gap** (piatok 17 h → nedeľa 18 h) vyplnený do pondelka 17 h: < 0,1 % **98 %** · 0,1–0,3 % **88 %** · 0,3–1 % 49 % · > 1 % 0 % (n 7).

### B4. FVG (celý deň, odraz o 1× veľkosť pred prerazením vs náhodná úroveň rovnakej veľkosti)
| TF | počet / deň | medián (body / % / × ATR) | **odraz** | náhodná | veľké FVG ≥ 1 ATR | náhodná |
|---|---|---|---|---|---|---|
| 1m | 389 | 0,20 b. / 0,008 % / 0,47 | 67 % | 64 % | 61 % | 63 % |
| 3m | 102 | 0,40 b. / 0,016 % / 0,34 | **72 %** | 66 % | 64 % | 60 % |
| 5m | 57 | 0,40 b. / 0,016 % / 0,30 | **72 %** | 66 % | 65 % | 58 % |
| 15m | 17 | 0,80 b. / 0,033 % / 0,27 | 71 % | 66 % | **60 %** | **50 %** |
- FVG na zlate o **+6 p. b.** nad náhodou (ES +3, MNQ +6); rovnako vo všetkých seansách (Ázia 73 vs 66, Londýn 71 vs 67, COMEX 72 vs 65).
- **Sú drobné:** medián 3m/5m FVG = 0,4 b. = **4 ticky** (1m 2 ticky) → samé o sebe neobchodovateľné (náklady ~0,3–0,45 b./obch).
  Zmysel má **veľké 15m FVG (≥ 1 ATR): +10 p. b.** alebo FVG v zóne.

### B5. SD zóny (báza 1–3 malé sviečky ≤ 0,6 ATR + impulz ≥ 1,5 ATR zavretý za bázou; prvý návrat do 3 dní)
| TF | zón / deň | výška × ATR | návrat | **odraz 2× výška pred prerazením** | náhodná báza |
|---|---|---|---|---|---|
| **5m** | 3,16 | 0,55 | 97 % | **63 %** | 34 % |
| **15m** | 0,76 | 0,57 | 94 % | **59 %** | 33 % |
| MNQ 5m / 15m | 2,39 / 0,70 | 0,56 | 97 / 94 % | 56 / 57 % | 31 / 30 % |
| ES (US500) 5m / 15m | 0,59 / 0,19 | 0,56 | 93 / 89 % | 50 / 50 % | 30 / 30 % |
**→ Najsilnejší jav, aký sme na zlate našli: SD zóny o ~+26–29 p. b. nad náhodou — viac ako na Nasdaqu aj S&P.**

### B6. Objem
- Sviečka s objemom ≥ 3× (≥ 5×) bežného pre ten čas: o 30 / 60 min v jej smere **±0,1 bps, pokračuje 47–48 %** → objemový výbuch sám
  nepovie nič o smere (rovnako MNQ). Len v COMEX seanse +1,0 bps (zanedbateľné).
- Objem je dôležitý **kde** (zóny, VWAP), nie **ako veľký** na jednej sviečke.

### B7. Volume profile — VAH, VAL, POC predošlého dňa a nahé úrovne (NPOC, NVAH, NVAL)
Profil z objemu 1m sviečok rozloženého po tickoch (0,1 b.), value area 70 %, pre celý obchodný deň (18–17 h) a zvlášť pre COMEX seansu.
Reakcia pri prvom dotyku nasledujúci deň: cena prejde **k × ATR(15m)** v smere odrazu skôr, ako 1m sviečka zavrie k × ATR za úrovňou.
Porovnanie s **náhodnou úrovňou** v rozpätí predošlého dňa (náhodná je nad 50 %, lebo zlato je návratové a cieľ ráta knôt, stop zavretie —
rozhoduje rozdiel proti nej). Skript `skripty_trh/vp.py`.
| úroveň (MGC) | k = 0,5 | k = 1,0 | | MNQ k = 0,5 | MNQ k = 1,0 |
|---|---|---|---|---|---|
| POC COMEX predošlého dňa | 64,3 % | **61,6 %** | | 59,1 % | 57,8 % |
| VAH COMEX | 59,9 % | 56,9 % | | 55,5 % | 51,6 % |
| VAL COMEX | 57,8 % | 57,7 % | | 57,2 % | 56,0 % |
| *náhodná (COMEX)* | *62,3 %* | *56,7 %* | | *56,8 %* | *52,7 %* |
| POC celého dňa | 64,9 % | 57,7 % | | 57,4 % | 55,4 % |
| VAH celého dňa | 64,1 % | 58,4 % | | 54,4 % | 52,3 % |
| VAL celého dňa | 62,1 % | 58,0 % | | 55,4 % | 50,9 % |
| *náhodná (deň)* | *61,8 %* | *60,7 %* | | *53,6 %* | *54,9 %* |
| NPOC (nahý POC, do 4 týždňov) | | 59,2 % (n 377) | | | 49,6 % |
| NVAH | | 57,1 % (n 459) | | | 55,8 % |
| NVAL | | 59,0 % (n 461) | | | 54,2 % |
| *náhodná (nahé)* | | *55,5 %* | | | *51,9 %* |
- **Úrovne profilu na zlate takmer nič nepridávajú:** VAH/VAL ≈ náhodná úroveň (± 2 p. b., na hranici šumu; n ~1 000 → chyba ~1,5 p. b.).
  Jediné mierne plus: **POC COMEX seansy pri k = 1 (+5 p. b.)** a nahé úrovne (+2–4 p. b., malá vzorka). Na MNQ podobne slabé.
- **POC predošlého dňa ako magnet:** cena sa ho v nasledujúci deň dotkne v **69 %** dní (MNQ 70 %).
- **Pravidlo 80 %** (otvorenie mimo včerajšej VA, potom 2 polhodiny vnútri → prejde na druhú hranicu VA v ten deň): na MGC len **43 %**
  (n 388), MNQ 55 % — „80 %“ sa na našich dátach nepotvrdzuje.
- Porovnanie: **SD zóny +26–29 p. b. nad náhodou** vs úrovne profilu 0–5 p. b. → na zlate stavať na zónach, profil len ako doplnok
  (napr. POC COMEX ako cieľ / magnet), nie ako signál.

### B8. Test stratégie VWAP × POC (21. 10. 2026) — NEFUNGUJE
Pravidlo: keď VWAP dňa (od 18:00) prekríži priebežný POC dňa na zavretí 5m, obchod v smere VWAP; 1 MGC, náklady 0,45 b.
- 2024-09 – 2025-09, celý deň: PF 0,95–1,02 (SL POC ∓1–3 b., RR 1:1 / 1:2), ~1 000 obchodov — vybíjačky okolo POC.
- Filter smeru (EMA 200 5m, 100 15m, 50 / 200 1h, 20 / 50 denná): pomohla len EMA 200 · 5m (PF 1,04–1,08); pomalé EMA nie.
- Umiestnenie SL (POC ∓ body / ATR, swing, signálna sviečka, pevné body, ATR od vstupu) + len NY (8:20–13:30 aj 9:30–16:00):
  úzke stopy prehrávajú (signálna sviečka PF 0,4–0,7), najlepší „vstup ∓ 2 ATR(15m), RR 1:1,5–1:2“ PF 1,11–1,24 — ale vybrané zo 168 nastavení.
- **Overenie na 2021-10 – 2024-09: PF 0,73–1,02 vo všetkých nastaveniach** → výsledok 2024/25 bola náhoda (silný trend zlata 2025).
Záver: VWAP × POC na zlate nemá náskok; súhlasí s B3 a B7 (zlato návratové, úrovne profilu ≈ náhoda). Skripty `vwappoc*.py`.

### B9. Test mechanickej stratégie na SD zónach (21. 10. 2026) — NEFUNGUJE (v tejto podobe)
Zóna ako v B5 (báza 1–3 sviečky ≤ 0,6 ATR, impulz ≥ 1,5 / 2 ATR), vstup limitkou na bližšej hrane pri prvom návrate, RR 1 / 1,5 / 2,
5m / 15m / 30m / 1h, celý deň vs živé hodiny (8:00–13:30 + 20:00–22:00), filter EMA 200 · 5m; ladenie 2021-10 – 2024-09, overenie 2024-09 – 2025-09.
- **Pevný stop za zónou (+0,25–1 ATR):** priemer PF brutto 15m 1,32 / 30m 1,00 / 1h 0,70; po nákladoch (0,2 b.) 1,11 / 0,89 / 0,65; 5m < 1.
  Najlepšie nastavenia (15m, impulz 2 ATR, živé hodiny, trend) PF 1,5–2,3 pri **26–29 obchodoch za 3 roky** → overenie PF 0,0–1,24 (5–26 obchodov).
- **Stop až na zavretí sviečky za zónou (+ núdzový 1 ATR), zóna platí 24 h:** 5m brutto PF 1,0–1,35, po nákladoch < 1; 15m opäť len 17 obchodov
  za 3 roky (PF 2,6) → overenie PF 0,24–0,75.
- **Prečo meranie (63 % vs 34 %) nedáva zisk:** zóny sú malé (5m ~0,8 b., 15m ~1,7 b.) → náklady 0,2–0,45 b. sú 15–50 % rizika; veľké zóny
  (impulz ≥ 2 ATR na 15m+) sú zriedkavé (0,1–0,2 / deň) a meranie počítalo dotyk do 3 dní a cieľ bez nákladov.
Záver: holá SD zóna nie je samostatná stratégia na MGC; zóny ako súčasť logiky (IBS EZ MGC: zóna + imbalance / pin bar) alebo ako filter
treba testovať v celej stratégii. Skripty `sd_mgc*.py`, `sd_val.py`, `sd_close.py`.

---

## C. Čo z toho plynie — čo odporúčam stavať na MGC
1. **Zónové stratégie (SD zóny)** — jav je v dátach (B5), ale holá mechanická verzia nefunguje (B9); zóny len v celej stratégii (IBS EZ MGC) / ako filter. Jediný silný štrukturálny jav (63 % vs 34 % náhoda na 5m). Kandidáti: **IBS EZ MGC**
   (Mac mini, zóny + imbalance), **SD Zones** a **JSS** preložené na MGC s prahmi v ATR, vstup pri prvom návrate do zóny 5m/15m, cieľ 1–2× výška zóny,
   stop za zónou. Obchodovať hlavne **8:00–11:00 ET** a **Ázia 20–22 h** (najviac pohybu a objemu).
2. **Návrat k VWAP v COMEX seanse** (89 % návrat po 2 sd) — fade 2–3 sd s cieľom VWAP, ale so **širokým stopom alebo časovým výstupom**
   (úzky stop sme už prerobili); filter: nie v prvých 30 min, nie okolo 8:30 / 10:00 / 14:00 správ.
3. **Overené profily z víkendového hľadania (v zisku 5/5 rokov, bez nákladov):** Scalping 3MA (MGC) 15m — WK 159, 161, 169, 156 (3m RR 2);
   Fibo 1.0 (MGC) 3m — WK 155, 166. → prepočet s nákladmi + smernica (dáta 2021+ sú kvalitné).
4. **Ázijský drift (long 18:00 → 3:00 ET):** +47 % za 2020–26, 6/7 rokov; priemer ~2,8 bps za noc, náklady ~1–2 bps → tenké; skúsiť s filtrom
   trendu (nad SMA denných zavretí) a porovnať s „long celý deň“ (aby to nebol len rast zlata).
5. **Nedeľný gap < 0,3 %** sa vyplní v 88–98 % do pondelka 17 h — malá doplnková stratégia (raz týždenne).
6. **Volume profile** (VAH/VAL/POC, nahé úrovne, pravidlo 80 %) ako samostatný signál nie — takmer ako náhoda (B7); POC len ako cieľ / magnet.
7. **Čomu sa vyhnúť:** prierazom a ORB (53–56 % pri 1:1 = po nákladoch nula, potvrdil aj skorší test), momentu prvej polhodiny (+0,01),
   objemovým výbuchom ako signálu, holým malým FVG (2–4 ticky, náklady), filtru „noc po červenom dni“.
8. **Všeobecne:** prahy v ATR / %, nie bodoch (rozpätie sa od 2024 zdvojnásobilo); SL aspoň ~5 b. (aby náklady boli < 10 % rizika);
   ladenie len na 2021-10 – 2025-09 (kvalitné dáta), odložený rok 2025/26 raz na konci; dni rolovania von.

## D. Zopakovanie / doplnenie
```
cd skripty_trh
python qa.py MGC && python qa.py MNQ     # kontrola kvality → qa_MGC.pkl, qa_MNQ.pkl (v tomto priečinku)
python g1.py   # veľkosti, profil dňa, high/low, seansy
python g2.py   # trend vs návrat, ORB, seansy po rokoch, noc, nedeľný gap
python g3.py   # FVG a SD zóny vs náhoda (dlhšie, ~10 min)
python g4.py   # objem, objemové výbuchy, VWAP, dni v týždni
python vp.py MGC   # volume profile: POC / VAH / VAL predošlého dňa, nahé úrovne, pravidlo 80 % (aj vp.py MNQ)
```
Doplniť neskôr: dni správ (CPI, NFP, FOMC — kalendár ForexFactory je v hube), okolie LBMA aukcií (5:30 a 10:00 ET), dni pred rolovaním,
zóny podľa seansy, v ktorej vznikli, a ich výsledok podľa toho, kedy sa cena vráti.

## Zdroje
CME Micro Gold: https://cmegroup.com/markets/metals/precious/e-micro-gold.contractSpecs.options.html ·
CME Micro Gold & Silver prehľad: https://cmegroup.com/education/lessons/micro-gold-and-micro-silver-futures-product-overview.html ·
CME notice aktívne mesiace GC: https://www.cmegroup.com/content/dam/cmegroup/notices/ser/2026/06/ser-9637r.pdf ·
Rolovanie (NexusFi): https://nexusfi.com/showthread.php?p=586456 ·
LBMA Gold Price: https://www.lbma.org.uk/lbma-prices-summary · Abrantes-Metz o fixe: https://www.lbma.org.uk/alchemist/issue-73/has-there-been-a-decade-of-london-pm-gold-fixing-manipulation ·
Bloomberg 2014: https://www.bloomberg.com/news/articles/2014-02-28/gold-fix-study-shows-signs-of-decade-of-bank-manipulation ·
Gold Around the Clock (CBS): https://research.cbs.dk/en/studentProjects/gold-price-dynamics-around-the-clock/ ·
Ázia vs Západ 2026: https://www.moneymetals.com/news/2026/07/12/a-strange-dichotomy-gold-up-on-the-year-in-asian-markets-down-big-in-the-west-005059 ·
Night effect (čínske futures): https://ideas.repec.org/a/eee/glofin/v64y2025ics1044028325000110.html ·
Reálne úroky a NFP (FXCM): https://www.fxcm.com/uk/insights/nfp-data-pushed-up-real-yield-which-rippled-through-to-the-usdollar-and-gold/ ·
FOMC a zlato (Saxo): https://home.saxo/content/articles/commodities/what-next-for-gold-after-hefty-reaction-to-fomc-meeting-17062021 ·
Volatilita okolo správ (BullionVault): https://www.bullionvault.com/gold-news/gold-trading-price-013120234 ·
Gold a EA archetypy (MQL5): https://www.mql5.com/en/blogs/post/774959 · Unger Academy (trend vs návrat na GC): https://blog2.ungeracademy.com/exploring-gold-futures-with-trend-following-and-mean-reverting-strategies/ ·
What moves the gold market (Cai a kol.): https://scholars.hkbu.edu.hk/en/publications/what-moves-the-gold-market/
