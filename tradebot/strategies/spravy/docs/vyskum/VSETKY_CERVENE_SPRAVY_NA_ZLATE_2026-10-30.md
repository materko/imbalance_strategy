# Všetky červené správy (aj mimo USD) na zlate — výskum 30. 10. 2026 (MacBook)

**Záver: mimo USD sa nenašlo nič, čo by prežilo odložený rok. SPRÁVY ostávajú na amerických správach.**

## Dáta
- Historický kalendár: dataset ForexFactory z Hugging Face (`Tropstan/Forex_Factory_Calendar`, MIT, 2007 – 7. 4. 2025, 83 427 riadkov),
  stiahnutý mimo repozitára (len výskum, nešíriť). Skripty v `skripty/ff_*.py`.
- **Dve chyby v datasete, opravené:** (1) čas 00:00 = čas chýba (FF ho pri správach v rovnakom čase nepíše) → doplnený časom najbližšieho
  známeho vydania tej istej správy v miestnom čase krajiny; (2) od 2023 je v lete posun +04:30 (Irán zrušil letný čas, skript to nevedel)
  → všetky letné časy 2023 – 2025 boli o hodinu skôr. Po oprave sedí náš oficiálny kalendár USD s datasetom 235 / 239 (2022 – 2025 na 100 %).
- 29 typov červených správ iných mien (ECB, BoE, BoJ, SNB, BoC, RBA, RBNZ, CPI / zamestnanosť / HDP / PMI krajín, Čína), bez prejavov
  guvernérov; vyradené udalosti do 5 min od americkej správy (Kanada 8:30 NY = často spolu s USA: zamestnanosť 73 %, HDP 54 %, CPI 47 %).

## Výber (2021 – 3/2025), 7 hypotéz na typ, 179 skúšok
Náhoda by dala |t| > 2 asi 8×, vyšlo 19× — štruktúra existuje, ale veľká časť je ten istý jav z oboch strán.
Kontrola „ten istý obchod o týždeň skôr / neskôr bez správy“ dala PF ~1 → efekty sú od správ, nie od hodiny.
Najlepšie: ECB tlačovka v smere prvých 15 min (WR 83 %, PF 5,7, 5/5 rokov), ECB noha 15 → 60 (PF 2,1, 4/5), kanadská zamestnanosť mimo dní NFP
proti pohybu (PF 6 – 12, len 13 – 14 udalostí), UK zamestnanosť (proti pohybu pred správou, trend 15 → 60 zlý 0/4 roky), CA HDP, RBNZ (drift pred správou pokračuje).

## Odložený rok (4/2025 – 9/2026, oficiálne termíny ECB)
| pravidlo | výber | odložené (12 zasadnutí) |
|---|---|---|
| ECB tlačovka 14:45, v smere prvých 15 min | WR 83 %, PF 5,74 | **WR 33 %, PF 0,14, −1 580 $** |
| ECB 14:15, v smere nohy 15 → 60 | WR 65 %, PF 2,11 | **WR 25 %, PF 0,29, −1 670 $** |

Najsilnejší kandidát na odloženom roku úplne zlyhal → výber z 179 skúšok bol hlavne šum. Pri ostatných kandidátoch (UK zamestnanosť, CA HDP,
RBNZ) je menej udalostí a slabšie čísla — nečakám iné. Na overenie by treba oficiálne termíny ONS / StatCan / RBNZ 4/2025 – 9/2026.

## Poučenie
Pri USD drží výsledok aj na XAU, pri dvojnásobnom poplatku aj vstupe o sviečku neskôr a má ekonomické vysvetlenie (Fed a americká inflácia
hýbu dolárom a reálnymi úrokmi, teda zlatom). Pri iných menách je reakcia zlata slabá (výbuch volatility 1,4 – 3× oproti 6 – 20× pri FOMC / CPI / NFP)
a „vzorce“ z minulosti sa neopakujú.
