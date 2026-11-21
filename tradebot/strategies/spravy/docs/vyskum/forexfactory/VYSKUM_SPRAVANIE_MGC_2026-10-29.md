# Správanie zlata (MGC) po červených správach USA — výskum 29. 10. 2026

Dáta: MGC 1m Databento, 10/2021–9/2026, čas New York (na Slovensku +5 h / +6 h; v týždňoch posunu času +5 h aj v zime/lete — pozri VYSVETLIVKA SPRÁVY).
834 udalostí v 12 typoch; keď sú dve správy naraz, udalosť patrí silnejšej (FOMC > CPI > NFP > PCE > GDP > PPI > RETAIL > ISM > JOLTS > zápisnica > CLAIMS).
Pohyby v ATR dňa (14-dňové ATR známe pred dňom), obchody 1 kontrakt (10 oz), poplatok + 2 ticky sklzu.
Skripty: `skripty/news_pattern.py` (1. kolo), `news_pattern2.py` (dráha, volatilita, spätný pohyb, asymetria, režim), `news_pattern3.py` (vzorce ako obchod).

**Pozor na viacnásobné testovanie:** prešlo sa ~45 hypotéz. Pri toľkých by aj náhoda dala 2–3 s t > 2. Za skutočné beriem len to, čo
(a) vyšlo vo viacerých nezávislých meraniach, (b) platí vo väčšine rokov, (c) má ekonomické vysvetlenie.

## 1. Čo platí pre všetky správy
- **Výstrel sa takmer vždy vracia.** Po prvých 15 minútach sa cena do T+60 vráti aspoň o polovicu výstrelu v 72–90 % prípadov,
  celý výstrel späť v 38–60 %. Najmenej sa vracajú CPI (38 %) a NFP (43 %) — tam sú pohyby „skutočné“; najviac PPI, RETAIL, CLAIMS, PCE.
- **Napriek tomu sa do T+60 spravidla urobí nový extrém** v smere výstrelu (60–81 %). Typický tvar: výstrel → spätný pohyb → druhá vlna.
  Pre stop to znamená: stop tesne za začiatkom správy vyhodí, stop za extrémom prvých 15 min tiež často.
- **Volatilita** (5-min sviečka oproti rovnakému času bez správy): FOMC 10× v prvých 5 min a **druhá vlna o 14:30 (tlačovka, 5,4×)**,
  stále 2–3× aj po 2 hodinách. CPI a NFP 5,6–5,8× a do 60 min klesnú na 1,3×. PCE, PPI, JOLTS, ISM, CLAIMS len 1,6–2,5× a po 5 min skoro normál.
  → Pri slabých správach nie je čo chytať; zmysel majú FOMC, CPI, NFP (a podmienene PPI).
- **Veľkosť výstrelu nič nepredpovedá** (kvartily 0,02–0,43 ATR, t pod 1). Veľký výstrel nie je „raketa“ automaticky.
- Smer výstrelu hore/dole, deň v týždni ani trend zlata (MA20) nedávajú spoľahlivý rozdiel (všetko t pod 2, pri malých n).

## 2. Vzorce, ktoré prešli (kandidáti)

| # | vzorec | n | WR | PF | spolu | t | rokov + | posledný rok |
|---|---|---|---|---|---|---|---|---|
| A | **FOMC: proti driftu 13:00→14:00 NY**, vstup 14:00, výstup 16:55 | 46 | 57 % | 3,22 | +6 201 $ | +2,5 | 5/6 | 9 obch, PF 26, +5 383 $ |
| A' | to isté, výstup 14:25 (pred tlačovkou) | 46 | 63 % | 3,43 | +2 622 $ | +2,3 | 5/6 | PF 8,7, +1 745 $ |
| B | **FOMC tlačovka:** smer 14:00→14:25, vstup 14:30, výstup 15:30 | 46 | 63 % | 2,14 | +2 928 $ | +1,8 | 4/6 | PF 36, +3 324 $ |
| C | FOMC noha 14:15→15:00, vstup 15:00 (= dnešná SPRÁVY) | 46 | 57 % | 2,32 | +2 141 $ | +1,7 | 5/6 | PF 2,2, +927 $ |
| D | **PPI: proti výstrelu 0→15**, vstup T+15, výstup T+180 | 66 | 64 % | 2,30 | +2 604 $ | +2,4 | 4/6 | PF 12, +1 771 $ |
| E | **CPI: proti prvej hodine 0→60**, vstup T+60, výstup T+120 | 68 | 59 % | 1,82 | +1 323 $ | +1,9 | **6/6** | PF 1,2, +106 $ |
| F | ISM výroba: v smere 0→15 a v smere MA20, T+15→T+180 | 29 | 52 % | 2,49 | +1 128 $ | +1,6 | 5/6 | 4 obch |

Vysvetlenia:
- **A — drift pred FOMC sa otáča.** V 70 % prípadov ide výstrel o 14:00 proti tomu, kam zlato išlo hodinu pred správou (t −2,7, najsilnejší
  jednotlivý výsledok výskumu). Trh sa pred FOMC pozicionuje a správa pozície vyhodí. Je to známy jav aj na akciách (drift pred FOMC,
  Lucca a Moench 2015) — má teda ekonomickú logiku, nie je to len náhoda v dátach. Na Slovensku: drift **18:00/19:00 → 19:00/20:00**, vstup presne v čase správy.
  Riziko: vstup v okamihu správy = najhorší sklz (10× volatilita); v teste 2 ticky, v skutočnosti môže byť viac → overiť na 1m s horším sklzom.
- **B — tlačovka o 14:30 pokračuje v smere prvých 25 minút** (65 %). Smer vyhlásenia Powell zvyčajne potvrdí, neotočí.
- **D — PPI výstrel sa vracia** (88 % prípadov sa cena vráti na cenu pred správou — najviac zo všetkých). Trh PPI berie ako predzvesť CPI, nie ako fakt.
- **E — CPI prvá hodina sa čiastočne vracia v druhej hodine**, 6 rokov zo 6, ale malý zisk na obchod a posledný rok slabý.

## 3. Čo nefunguje (aby sme to neskúšali znova)
- CLAIMS (každý štvrtok): v smere výstrelu PF 0,56, proti nemá stabilitu (2/6 rokov). Šum.
- NFP: proti prvej hodine PF 0,48 (1/6 rokov) — NFP pohyb sa po hodine **nevracia** (na rozdiel od CPI). V smere výstrelu len PF 1,14.
- PCE, RETAIL, GDP, ISM služby, JOLTS: všetko okolo PF 1 alebo nestabilné po rokoch.
- Veľkosť výstrelu ako filter, deň v týždni, asymetria hore/dole.

## 4. Kedy vstúpiť — séria behov SPRÁVY (webapp, MGC 5m, 1 kontrakt)
(doplnené nižšie)
60 behov v histórii webapp (poznámka „SPRAVY vstup: …“), päť referenčných okien. Noha sa meria od času správy T po T+X, vstup v T+X.

**TREND (FOMC, PCE — v smere nohy, držanie 4 h)**

| vstup | PF po oknách | obch | zisk | max DD | posledný rok |
|---|---|---|---|---|---|
| 5 min | 0,12 · 0,80 · 1,30 · 1,95 · 3,00 | 99 | +3 127 $ | 1 208 $ | 19 obch, WR 58 %, PF 3,00, +3 187 $ |
| 10 min | 0,21 · 0,61 · 1,15 · 1,49 · 2,72 | 97 | +2 750 $ | 967 $ | 20, WR 55 %, PF 2,72, +3 087 $ |
| 15 min | 0,52 · 1,00 · 0,86 · 1,42 · 4,62 | 97 | +4 844 $ | 710 $ | 19, WR 58 %, PF 4,62, +4 893 $ |
| 30 min | 0,24 · 0,75 · 0,88 · 1,29 · 4,34 | 99 | +3 720 $ | 1 015 $ | 20, WR 65 %, PF 4,34, +4 541 $ |
| 45 min | 0,82 · 0,75 · 0,54 · 1,28 · 2,99 | 100 | +2 982 $ | 739 $ | 20, WR 50 %, PF 2,99, +3 605 $ |
| 60 min | 0,46 · 1,02 · 1,12 · 1,24 · 5,08 | 100 | +4 552 $ | 597 $ | 20, WR 65 %, PF 5,08, +4 656 $ |
| *profil SPRÁVY (noha T+15→T+60)* | *1,19 · 1,06 · 2,27 · 2,13 · 3,20* (spolu s FADE) | | | | |

→ Pri TREND **žiadny čas vstupu s nohou od T nefunguje vo všetkých rokoch** — zarábajú len posledné 2 roky (býčí trh zlata).
Noha od T+15 (prvých 15 min sa preskočí, lebo sa výstrel vracia — FOMC medián spätného pohybu 124 %) je lepšia vo všetkých oknách → nechať profil.

**FADE (CPI, PPI, JOLTS — proti nohe, držanie 1 h)**

| vstup | PF po oknách | obch | zisk | max DD | posledný rok |
|---|---|---|---|---|---|
| 5 min | 0,64 · 1,23 · 0,51 · 1,36 · 0,86 | 177 | −734 $ | 1 178 $ | 33, WR 45 %, PF 0,86, −327 $ |
| 10 min | 1,20 · 1,30 · 0,86 · 0,99 · 0,99 | 177 | +261 $ | 832 $ | 33, WR 55 %, PF 0,99, −23 $ |
| 15 min | 1,57 · 1,64 · 1,26 · 0,75 · 1,24 | 177 | +1 199 $ | 1 150 $ | 33, WR 58 %, PF 1,24, +417 $ |
| 30 min | 2,15 · 1,63 · 0,84 · 0,88 · 1,49 | 176 | +1 658 $ | 475 $ | 33, WR 55 %, PF 1,49, +851 $ |
| 45 min | 1,27 · 0,78 · 1,14 · 1,36 · 2,43 | 177 | +2 411 $ | 410 $ | 33, WR 64 %, PF 2,43, +1 875 $ |
| 60 min (profil) | 2,26 · 0,93 · 1,84 · 1,02 · 1,76 | 177 | +2 030 $ | 531 $ | 33, WR 55 %, PF 1,76, +1 061 $ |

→ Proti správe **nikdy hneď** (5–10 min = strata). Čím neskôr, tým lepšie; 45 a 60 min sú rovnocenné (45 min: najviac zisku a najmenší DD,
60 min: viac okien nad PF 1,5). Profil (60 min) nechať, 45 min ako alternatíva.

## 5. Odporúčanie (nič nezmenené, čaká na rozhodnutie)
1. **Nový režim „PRED FOMC“ (vzorec A)** — najsilnejší a ekonomicky vysvetliteľný; do SPRÁVY ako tretí režim popri TREND/FADE
   (vstup o 14:00 NY proti driftu 13:00→14:00, výstup pred tlačovkou alebo 16:55). Najprv overiť sklz pri vstupe v okamihu správy.
2. **Tlačovka FOMC (vzorec B)** — druhý obchod v ten istý deň, 14:30 v smere 14:00→14:25.
3. **PPI presunúť z FADE nohy T→T+60 na „proti výstrelu 0→15, držať 3 h“ (vzorec D).**
4. Zvyšok (CLAIMS, NFP proti, PCE, RETAIL, GDP, ISM služby) nechať bokom.
Všetko spolu by bolo stále len ~25–35 obchodov za rok len z FOMC + PPI → SPRÁVY ostáva stratégia s výnimkou z pravidla 150/rok.
