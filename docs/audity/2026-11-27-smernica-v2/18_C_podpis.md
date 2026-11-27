# 18 — Kontrolór C: podpisová kontrola SMERNICA_V2 po `17_C` (27. 11. 2026)

*Len čítanie. Diff proti `SMERNICA_V2.bak4.md` (`fix17.py`, 0 MISS). Riadky = `SMERNICA_V2.md:N`. Smernica prečítaná celá.*

## Vyriešené
- **B1** `:317`: krok 3 pri legacy beží na L trhu, bez roka A. Trezory a rok A sa cez krok 10 už neotvárajú. **B2** `:266–267`: DSR, PBO aj haircut sú pri kroku 10 len informácia.
  **B3** `:435`, `:436`, `:459`: SPRÁVY sú ⚠ legacy s negatívnym signálom. Okno so 107–143 obchodmi je správne vedené ako ⏳.
- **4** `:412`, `:436`, `:443` · **5** `:292–294`, `:298`, `:100`, `:102`, `:467`. Bonferroni sedí: k = 100 dáva 3,48, k = 160 dáva 3,61.
  **6** `:107–108`, `:284`, `:290` · **7** `:231–232`, roky sedia s §1 · **8** `:98` · **9** `:303` · **10** `:425` · **11** `:116–117`.
  **12** `:494`, `:496` (súčet je 27,5–33,5 dňa), `:499` · **13** `:416`, `:7`. Overené na disku: `gl_paused` existuje, `.last_morning` je z 10:17 a novší stavový súbor nie je.
- Pre ES k ≈ 10 (`:98`, `:107`) nič neprotirečí. Na 2010–14 nebežala žiadna štúdia, KLZAKY začína ES až 2016 a SP500-ES 2019.

## Zvyšky
**Rozpory medzi krokmi (opraviť pred podpisom, každý je na jeden riadok):**
1. `:159` stále píše „Legacy SPRÁVY sú ❌ … > 5 parametrov, DSR so skutočným N“. Bije sa to s `:435` a `:459` a pravidlo „> 5 parametrov“ pre legacy neexistuje. Ide o zvyšok B3.
2. `:18` uvádza pre MNQ, MYM a BTC „t_req ≈ 3,3 (PF ≳ 1,6)“, kým `:100`, `:107` a `:467` majú k ≈ 160, t_req ≈ 3,6 a PF ≳ 1,65. Chýba aj 6E.
3. `:424` T4: Williams R 6E na 10/2021–9/2026 je označený „nie trezor“. To obdobie je však celý trezor 6E (`:99`, 2021-10 – 2025-09) plus rok A, čo je v rozpore s krokom 10.1 (`:317`, „na L, bez roka A“). Rovnaký problém ako B1.
   Oprava: T4 pustiť na L 6E 2016-01 – 2021-09. Ak má ostať obdobie 2021–26, treba ho výslovne vyňať z 10.1 a zapísať k + 1 do `vaults.json` (to tam už je).

**Menšie (výsledok nemenia):**
4. `:175`: zátvorka „DSR len informácia“. Podľa `:266` majú byť len informáciou DSR, PBO aj haircut.
5. `:428` T6 (MNQ 6/2024 – 9/2026): beží na trezore MNQ a v roku A s t ≥ 2,0, nie s t_req 3,6. Výnimku „po publikácii“ (`:323`) treba nazvať výnimkou z 8a a 8b a zapísať k + 1 trezoru MNQ.
6. `:107`: číslo ~160 je počet všetkých kľúčov (163 adresárov), teda prísny horný odhad. Trezor sa počíta na trh (`:277`), takže `vaults.json` dá na každom trhu menej. Stačí slovo „najviac“.
7. `:5`: „Podklady 01–16“ treba zmeniť na 01–18. `:431`: „k 26. 11.“ treba zmeniť na 27. 11.

## Verdikt
**Pripravená na podpis používateľom: nie, zatiaľ nie.** Ostávajú tri jednoriadkové rozpory (body 1–3) a nové meranie nepotrebujú.
Body 1 a 3 sú zvyšky B3 a B1. Po ich oprave **áno**. Body 4–7 sa dajú opraviť v tom istom prechode a podpis nebrzdia.
