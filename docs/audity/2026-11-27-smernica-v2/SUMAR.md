# Sumár auditu (26. 11. 2026, Mac mini) — na čo sme prišli

Podklady: KONVERZACIA.md (celá debata), VYCUC.md (body z každého kola), SMERNICA_V2.md (návrh), 07_SPRAVY_stare_roky.md.

## 1. Hlavný záver
**Nemáme ani jednu stratégiu s čistým dôkazom, že po reálnych nákladoch zarába.** Čísla vo webapp (PF 1,5–1,8, posl. rok
PF 1,5–1,8) sú vybrané chvosty z rozdelenia, ktorého stred je ~1,0. Obaja agenti sa na tom zhodli a každý bod overili v kóde.

## 2. Prečo (preoptimalizovanie)
1. **~1,8 mil. pokusov** (TKS 82 tis., NOA 38 tis.); literatúra pri 5 rokoch dát unesie desiatky.
2. **Odložený rok nie je odložený:** > 2 300 behov na tom istom roku 2025/26 a stránka aj webapp **zoraďujú podľa neho**
   (`gldash.py:480–490` → top 3 → webapp → LIVE).
3. **Medián kandidátov na odloženom roku ≈ 1,0** (TKS 1,03, VWAP ORB 1,01, NY VA 1,01, IVB 0,97, NOA MGC 0,84).
4. **Brzdy sa počítajú, ale nebrzdia:** DSR < 0,95 všade („nemá vplyv“), test proti náhode bez korekcie na výber,
   plató len ±1 krok jednej skupiny (bool/str netestované).
5. **Staré roky (MacBook) a SPRÁVY 2010–2021 (Mac mini) to potvrdili:** IBS EZ ES 0,75, TKS 0,94, VWAP ORB 0,96, NY VA 0,81;
   SPRÁVY PF 3–7 → **~1,0**, s nákladom 1,5 ticku v strate.

## 3. Prečo by sme do roka mohli skrachovať (poradie podľa rýchlosti)
1. **Žiadna ochrana účtu v kóde** — žiadny denný stop ani DD na equity v EA/NT; vypína sa ručne.
2. **Jedna stávka:** na Server3 9 inštancií, väčšina Nasdaq/US500 intraday v tom istom okne — prehrávajú naraz.
3. **Vypínacie pravidlo sa nevykonáva:** naživo ~−5,7 k$ za 6 týždňov, NOA nad MC DD95 a beží; po strate sa doladil filter na novembri.
4. **Optimistický fill pri RR 0,5 / WR ~74 %:** limit a TP pri dotyku, stop bez sklzu, náklad na zlate/eure ~0,3 ticku
   — rezerva 7–9 p. b. WR zmizne pri 1 ticku sklzu.
5. **Ladíme na futures, obchodujeme CFD** — iné sviečky, spread, swap; zhoda NOA 13/17.

## 4. Čo je kandidát (nie dôkaz) a čo mŕtve
- **Najbližšie k dôkazu:** Williams R Long 6E, NOA podľa pôvodného článku (test na období po publikácii), Noc + pondelok MNQ.
  Ani jedna nemá čistý trezor — ✅ môže vzniknúť až z NQ/YM/GC 2010–2019 (treba stiahnuť) alebo z dát od 1. 12. 2026.
- **Mŕtve:** IBS EZ (MNQ, ES, MYM, EOD), TKS, VWAP ORB, NY VA, IVB, NOA MGC, Sigma MGC/MYM, CRT, Williams R ES, SPRÁVY legacy profily.
- **Naživo dnes beží viac mŕtvych** (TKS, IBS EZ 11, SPRÁVY profil 3).

## 5. Nová smernica (SMERNICA_V2 — návrh, platí až po schválení)
Rozpočet 300 konfigurácií a ≤ 5 parametrov na **hypotézu** (všetky kópie spolu) · trezory otvárané raz, nikdy na poradie ·
odložený rok 2025/26 spálený · walk-forward povinný · DSR, PBO, haircut ako brány · náklady v tickoch + sklz, fill pri prechode
o tick · min. 100 obchodov v každom roku · prop riziko z equity, stop účtu −2 % / −6 % v kóde · demo 8 týždňov / 40 obch,
zhoda ≥ 95 % · webapp ukazuje očakávanie po haircute, nie „posl. rok PF“. Zachované: naživo = história, C# parita, 1m detail.
Zavedenie ~5–7 týždňov; **prvé je ochrana účtu v EA a NT**.

## 6. Rozhodnutia, ktoré sú na tebe (§9 smernice)
1. Minimum 100 obchodov v každom roku?
2. SPRÁVY naživo — pozastaviť, alebo vedome nechať ako stávku na režim so zníženou veľkosťou?
3. Server3 — pozastaviť TKS 1, IBS EZ 11, ladenú NOA 1?
4. Stiahnuť NQ, YM, GC 2010–2019 z Databenta?
5. Zrušiť pravidlo „WR 70–100 %“ (je to ladenie na winrate; RR ≥ 0,5 ostáva)?
Plus: kým radí podľa odloženého roka, vypnúť ranné `glwebvyber --apply` a smernicu na hube (ibretmgc, ibretmym, wpreur,
ibsentryeur) brať ako starú — jej „prešiel“ trpí tým istým výberom.

## 7. Kriticky k samotnému auditu
- Agenti len čítali kód a dáta; nové behy som spravil len ja (SPRÁVY 2010–2021). Ich t-odhady sú hrubé (z PF, n a WR).
- Dáta zlata pred 2020 sú neúplné; staré roky Nasdaqu skresľujú bodové prahy (IBS EZ MNQ).
- Literatúra je o akciových/makro stratégiách a bankových produktoch; intraday futures nemusí sedieť 1:1 — smer však áno.
